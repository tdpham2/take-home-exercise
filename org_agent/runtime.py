"""Per-question audit state and bounded projection of LangChain message history."""
from collections import Counter
import json
import time

from langchain_core.messages import AIMessage, ToolMessage

from .tools import text_of


def serialized(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def payload(message):
    try:
        return json.loads(message.content) if isinstance(message.content, str) else message.content
    except (ValueError, TypeError):
        return None


class ContextExceeded(RuntimeError):
    pass


class RunLedger:
    def __init__(self, config, artifacts, question, event_sink=None):
        self.config, self.artifacts, self.question = config, artifacts, question
        self.event_sink = event_sink
        self.events = []
        self.model_calls = self.tool_calls = self.no_gain = 0
        self.returned = set()
        self.visible_items = set()
        self.visible_spans = []
        self.discarded = {}
        self.pinned = set()
        self.evicted_calls = set()
        self.projected_discards = set()
        self.last_draft = None
        self.stop_reason = None
        self.started = time.monotonic()

    def log(self, kind, **fields):
        event = {"sequence": len(self.events) + 1, "kind": kind, **fields}
        self.events.append(event)
        if self.event_sink:
            self.event_sink(event)
        return event

    def identities(self, value):
        items, evidence, nodes = set(), set(), set()
        for row in walk(value):
            if "title_origin" in row and "item_id" in row:
                items.add(row["item_id"])
            if "evidence_id" in row:
                evidence.add(row["evidence_id"])
            if row.get("id") in self.artifacts.index["nodes"]:
                nodes.add(row["id"])
        return items, evidence, nodes

    def tool_result(self, name, arguments, call_id, value, latency, error=False):
        identities = set().union(*self.identities(value))
        # Reading a new page of the same source is useful progress too.
        identities |= {f"span:{r['evidence_id']}:{r['start']}:{r['end']}" for r in walk(value)
                       if all(k in r for k in ("evidence_id", "quote", "start", "end"))}
        new = identities - self.returned
        self.returned |= identities
        self.no_gain = 0 if new else self.no_gain + 1
        self.log("tool", name=name, arguments=arguments, call_id=call_id, result=value,
                 latency_seconds=latency, error=error, new_ids=sorted(new))
        for discard in value.get("trace", {}).get("discarded", []) if isinstance(value, dict) else []:
            self.log("retrieval_discard", **discard)

    def present(self, messages):
        """Only excerpts actually included in a model request can support its claims."""
        for message in messages:
            if not isinstance(message, ToolMessage):
                continue
            value = payload(message)
            self.visible_items |= self.identities(value)[0]
            route = "memory" if message.name in {"recall_memory", "inspect_memory", "list_patterns", "list_outcomes", "memory_timeline"} else "graph"
            if message.name == "retrieve_text":
                route = "text"
            for row in walk(value):
                if all(k in row for k in ("evidence_id", "quote", "start", "end")):
                    span = {k: row[k] for k in ("evidence_id", "quote", "start", "end")}
                    span.update(route=route, call_id=message.tool_call_id)
                    if span not in self.visible_spans:
                        self.visible_spans.append(span)

    def select(self, discarded, pinned):
        for selection in discarded:
            iid = selection["item_id"]
            if iid in self.visible_items:
                self.discarded[iid] = selection["reason"]
                self.log("item_discard", item_id=iid, reason=selection["reason"], origin="model relevance decision")
            else:
                self.log("invalid_selection", item_id=iid, reason="Cannot discard an unseen item")
        seen = {s["evidence_id"] for s in self.visible_spans}
        for eid in pinned:
            if eid in seen:
                self.pinned.add(eid)
            else:
                self.log("invalid_selection", evidence_id=eid, reason="Cannot pin unseen evidence")

    def project(self, messages, size):
        """Evict complete exchanges, preserving pins, question, and newest exchange."""
        messages = self._project_tool_content(messages)
        groups = []
        for message in messages:
            if isinstance(message, ToolMessage):
                if not groups or not isinstance(groups[-1][0], AIMessage):
                    raise ValueError("Orphan tool result in conversation")
                groups[-1].append(message)
            else:
                groups.append([message])
        for group in groups:
            if isinstance(group[0], AIMessage) and group[0].tool_calls:
                if {c["id"] for c in group[0].tool_calls} != {m.tool_call_id for m in group[1:] if isinstance(m, ToolMessage)}:
                    raise ValueError("Incomplete tool-call/result exchange")

        def refs(group):
            items, evidence = set(), set()
            for message in group:
                if isinstance(message, ToolMessage):
                    i, e, _ = self.identities(payload(message))
                    items |= i
                    evidence |= e
            return items, evidence

        def remove(group, reason):
            call_ids = [c["id"] for m in group if isinstance(m, AIMessage) for c in m.tool_calls]
            items, evidence = refs(group)
            for call_id in call_ids:
                if call_id not in self.evicted_calls:
                    self.evicted_calls.add(call_id)
                    self.log("context_eviction", call_id=call_id, item_ids=sorted(items),
                             evidence_ids=sorted(evidence), reason=reason)

        retained, signatures = [], set()
        # Visit newest first, so repeated exchanges retain their most recent result.
        for group in reversed(groups):
            if not isinstance(group[0], AIMessage):
                retained.append(group)
                continue
            items, evidence = refs(group)
            pinned = bool(evidence & self.pinned)
            calls = group[0].tool_calls
            signature = serialized([{k: c[k] for k in ("name", "args")} for c in calls])
            prior_evicted = any(c["id"] in self.evicted_calls for c in calls)
            if prior_evicted and not pinned:
                continue
            if items and items <= self.discarded.keys() and not pinned:
                remove(group, "all returned memory items explicitly discarded by model")
            elif calls and signature in signatures and not pinned:
                remove(group, "duplicate tool request; newest exchange retained")
            else:
                retained.append(group)
                if calls:
                    signatures.add(signature)
        retained.reverse()

        def flat():
            return [m for g in retained for m in g]

        while size(flat()) > self.config.max_request_chars:
            exchanges = [g for g in retained if isinstance(g[0], AIMessage)]
            candidates = [g for g in exchanges[:-1] if not (refs(g)[1] & self.pinned)]
            if not candidates:
                raise ContextExceeded("Question, tool schemas, pinned evidence, and newest exchange exceed context budget")
            group = candidates[0]
            remove(group, "context character budget: oldest unpinned exchange")
            retained.remove(group)
        selected = flat()
        selected_items, selected_evidence, selected_calls = set(), set(), []
        for message in selected:
            if isinstance(message, ToolMessage):
                items, evidence, _ = self.identities(payload(message))
                selected_items |= items
                selected_evidence |= evidence
                selected_calls.append(message.tool_call_id)
        self.log("context", model_call=self.model_calls + 1, serialized_chars=size(selected),
                 message_count=len(selected), pinned_evidence_ids=sorted(self.pinned),
                 visible_item_ids=sorted(selected_items), visible_evidence_ids=sorted(selected_evidence),
                 included_tool_call_ids=selected_calls)
        return selected

    def _project_tool_content(self, messages):
        """Remove selected cards from mixed results; full original results stay in the audit ledger."""
        def project(value, removed):
            if isinstance(value, list):
                return [row for child in value if (row := project(child, removed)) is not None]
            if not isinstance(value, dict):
                return value
            iid = value.get("item_id")
            if "title_origin" in value and iid in self.discarded and not (set(value.get("evidence_ids", [])) & self.pinned):
                removed.add(iid)
                return None
            result = {k: project(v, removed) for k, v in value.items()}
            # Ranking exclusions are fully logged but need not consume the model's context.
            trace = result.get("trace")
            if isinstance(trace, dict) and len(trace.get("discarded", [])) > 20:
                trace["discarded_total"] = len(trace["discarded"])
                trace["discarded"] = trace["discarded"][:20]
                trace["discarded_truncated_for_context"] = True
            return result

        result = []
        for message in messages:
            if not isinstance(message, ToolMessage) or not isinstance(payload(message), dict):
                result.append(message)
                continue
            removed = set()
            projected = project(payload(message), removed)
            if projected is None:
                projected = {"context_discarded_item_ids": sorted(removed), "reason": "explicit relevance decision"}
            elif removed:
                projected["context_discarded_item_ids"] = sorted(removed)
            for iid in removed:
                key = (message.tool_call_id, iid)
                if key not in self.projected_discards:
                    self.projected_discards.add(key)
                    self.log("context_item_eviction", call_id=message.tool_call_id, item_id=iid, reason=self.discarded[iid])
            result.append(message.model_copy(update={"content": serialized(projected)}))
        return result

    def usage(self):
        model = [e for e in self.events if e["kind"] == "model"]
        calls = [e for e in model if not e.get("provider", {}).get("cached", False)]
        tokens = Counter()
        for entry in calls:
            u = entry.get("provider", {}).get("usage") or {}
            tokens["input_tokens"] += u.get("input_tokens", u.get("prompt_tokens", 0))
            tokens["output_tokens"] += u.get("output_tokens", u.get("completion_tokens", 0))
            tokens["cached_input_tokens"] += u.get("cached_input_tokens", (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0))
            tokens["reasoning_output_tokens"] += u.get("reasoning_output_tokens", (u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0))
        return {"model_calls": self.model_calls, "data_tool_calls": self.tool_calls,
                "cache_replays": sum(bool(e.get("provider", {}).get("cached")) for e in model),
                "reported_new_call_tokens": dict(tokens),
                "calls_without_usage": sum(not e.get("provider", {}).get("usage") for e in calls),
                "model_elapsed_seconds": sum(e["latency_seconds"] for e in model),
                "provider_elapsed_seconds": sum(e.get("provider", {}).get("latency_seconds", 0) for e in calls),
                "tool_elapsed_seconds": sum(e["latency_seconds"] for e in self.events if e["kind"] == "tool"),
                "total_elapsed_seconds": time.monotonic() - self.started,
                "estimated_cost_usd": None,
                "limitation": "Cached-input and reasoning tokens are subsets; do not add them to input/output totals. Subscription dollars unknown."}


def validate_answer(draft, ledger, items):
    """Validate access and exact provenance, not natural-language entailment."""
    from .models import Claim
    from org_memory.review import administrative
    valid, errors = [], []
    for number, claim in enumerate(draft.claims, 1):
        failures, records, graph_checks = [], set(), []
        memory_refs = set()
        for iid in claim.memory_ids:
            if iid not in ledger.visible_items or iid not in items:
                failures.append(f"unseen memory item {iid}")
            else:
                refs = set(items[iid]["evidence_ids"]) | set(items[iid].get("counterevidence_evidence_ids", []))
                memory_refs |= refs
                if not refs & {c.evidence_id for c in claim.citations}:
                    failures.append(f"memory item {iid} does not link to the cited evidence")
        extracted_support = False
        for citation in claim.citations:
            eid = citation.evidence_id
            e = ledger.artifacts.index["evidence"].get(eid)
            if e is None:
                failures.append(f"unknown evidence {eid}")
                continue
            end = citation.start + len(citation.quote)
            if text_of(e)[citation.start:end] != citation.quote:
                failures.append(f"quotation/offset mismatch for {eid}")
            spans = [s for s in ledger.visible_spans if s["evidence_id"] == eid and s["start"] <= citation.start
                     and end <= s["end"] and s["quote"][citation.start-s["start"]:end-s["start"]] == citation.quote]
            if not spans:
                failures.append(f"cited text was not shown to the model: {eid}")
            graph_seen = any(s["route"] == "graph" for s in spans)
            graph_checks.append(graph_seen)
            text_seen = any(s["route"] == "text" for s in spans)
            if not graph_seen and not text_seen and eid not in memory_refs:
                failures.append(f"memory-only citation requires a linked memory ID: {eid}")
            extracted_support |= (e["provenance"]["kind"] == "extracted" and bool(citation.quote.strip()) and not administrative(citation.quote))
            if e["record_id"]:
                records.add(e["record_id"])
        if not extracted_support:
            failures.append("claim needs substantive extracted source support; labels, inference, and administrative closure are insufficient")
        if claim.kind == "hypothesis" and claim.confidence != "low":
            failures.append("hypotheses must carry low confidence")
        if failures:
            errors.extend(f"Claim {number}: {f}" for f in failures)
            continue
        mode = "memory_confirmed_by_graph" if claim.memory_ids and all(graph_checks) else ("memory" if claim.memory_ids else "graph")
        if not claim.memory_ids and not any(graph_checks):
            mode = "text"
        result = Claim(**claim.model_dump(), id=f"C{number}", record_ids=sorted(records), source_mode=mode)
        valid.append(result)
    return valid, errors
