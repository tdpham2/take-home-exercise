"""One retrieval followed by one answer, with at most one provenance/format repair."""
import json
from pathlib import Path
import time

from langchain_core.messages import ToolMessage
from pydantic import ValidationError

from org_agent.models import AgentConfig, AnswerResult, DraftAnswer
from org_agent.prompts import SOURCE_PROMPT
from org_agent.runtime import RunLedger, serialized, validate_answer, ContextExceeded
from org_memory.hosted import BudgetExceeded, ProviderUnavailable
from org_memory.storage import atomic_text
from .common import client_for, strict_schema
from .corpus import TextCorpus


TEXT_PROMPT = SOURCE_PROMPT + """
Answer using only the supplied retrieved record passages. Return DraftAnswer JSON directly.
Use empty memory_ids. Do not use outside knowledge to fill organizational history gaps.
"""


class TextRAG:
    def __init__(self, source, config=None, *, client_factory=None, top_k=20, corpus=None):
        self.source = source
        self.config = config or AgentConfig()
        self.client_factory = client_factory
        self.top_k = top_k
        self.corpus = corpus or TextCorpus(source)

    def answer(self, question, *, trace_path=None):
        if not isinstance(question, str) or not question.strip() or len(question) > 8000:
            raise ValueError("Question must be nonempty text of at most 8000 characters")
        event_sink = None
        if trace_path is not None:
            trace_path = Path(trace_path)
            atomic_text(trace_path, "")

            def event_sink(event):
                with trace_path.open("a") as stream:
                    stream.write(json.dumps(event, ensure_ascii=False) + "\n")
                    stream.flush()

        ledger = RunLedger(self.config, self.source, question, event_sink)
        ledger.log("input_scope", **self.source.identity)
        draft, valid, errors, client = None, [], [], None
        schema = strict_schema(DraftAnswer)
        packet = {"question": question, "records": []}
        started = time.monotonic()
        candidates = self.corpus.search(question, self.top_k)
        omitted = []
        for record in candidates:
            # Alias IDs are retained in the corpus for audit matching, not exposed as
            # independently shown citations. The model cites each displayed canonical ID.
            record = {**record, "passages": [{k: v for k, v in p.items() if k != "equivalent_evidence_ids"}
                                              for p in record["passages"]]}
            proposed = {**packet, "records": [*packet["records"], record]}
            if len(serialized({"system": TEXT_PROMPT, "packet": proposed, "schema": schema})) <= self.config.max_request_chars:
                packet = proposed
            else:
                omitted.append(record["record_id"])
        ledger.tool_calls = 1
        ledger.tool_result("retrieve_text", {"query": question, "top_k": self.top_k}, "text_1",
                           {"records": packet["records"], "omitted_record_ids": omitted}, time.monotonic() - started)
        ledger.present([ToolMessage(content=serialized(packet), name="retrieve_text", tool_call_id="text_1")])
        try:
            client = client_for(self.config, factory=self.client_factory)
            for attempt in range(2):
                size = len(serialized({"system": TEXT_PROMPT, "packet": packet, "schema": schema}))
                if size > self.config.max_request_chars:
                    raise ContextExceeded("Baseline request including repair exceeds context cap")
                ledger.log("context", model_call=attempt + 1, serialized_chars=size,
                           visible_evidence_ids=sorted({s["evidence_id"] for s in ledger.visible_spans}),
                           included_tool_call_ids=["text_1"])
                started, before = time.monotonic(), len(client.trace)
                ledger.model_calls += 1
                entry = {"call_number": ledger.model_calls, "status": "started"}
                ledger.log("model_started", **entry)
                try:
                    raw, request_id = client.json(TEXT_PROMPT, packet, schema, "evaluation_text_rag")
                    entry.update(status="complete", request_id=request_id, draft=raw)
                    draft = DraftAnswer.model_validate(raw)
                    valid, errors = validate_answer(draft, ledger, {})
                except (ValueError, ValidationError) as exc:
                    entry.update(status="invalid", error=str(exc)[:1200])
                    errors = [str(exc)[:1200]]
                except BaseException as exc:
                    entry.update(status="failed", error_type=type(exc).__name__)
                    raise
                finally:
                    entry["latency_seconds"] = time.monotonic() - started
                    if len(client.trace) > before:
                        entry["provider"] = client.trace[-1].copy()
                    ledger.log("model", **entry)
                if not errors:
                    break
                ledger.log("citation_repair", errors=errors)
                packet = {**packet, "correction": errors[:12]}
        except (BudgetExceeded, ProviderUnavailable, ContextExceeded, ValueError, RuntimeError, KeyboardInterrupt) as exc:
            ledger.stop_reason = f"{type(exc).__name__}: {str(exc)[:600]}"
            ledger.log("stopped", reason=ledger.stop_reason)
        finally:
            if client:
                client.close()
        unanswered = list(draft.unanswered) if draft else ["No structured answer was produced."]
        if not valid and not unanswered:
            unanswered.append("No validated claims were established.")
        for c in valid:
            ledger.log("claim_support", claim_id=c.id, record_ids=c.record_ids, memory_ids=[],
                       evidence_ids=[r.evidence_id for r in c.citations], source_mode="text")
        return AnswerResult(question=question,
            status="failed" if draft is None else ("partial" if errors or unanswered or ledger.stop_reason else "complete"),
            claims=valid, unanswered=unanswered, limitations=[*(draft.limitations if draft else []),
                "BM25 over extracted record text; exact citations do not establish semantic correctness."],
            validation_errors=errors, stop_reason=ledger.stop_reason, trace=ledger.events, usage=ledger.usage(),
            manifest={**self.source.identity, "approach": "text_rag", "top_k": self.top_k,
                      "corpus_fingerprint": self.corpus.fingerprint, "configuration": self.config.model_dump()})
