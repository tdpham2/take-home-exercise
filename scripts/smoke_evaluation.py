"""Exercise all 54 runs and judging offline. Every answer/verdict/review is SYNTHETIC."""
# ruff: noqa: E402
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from org_agent import AgentConfig
from org_agent.artifacts import SourceArtifacts
from org_memory.storage import atomic_json
from org_eval.benchmark import SLOTS, freeze, write_review_template
from org_eval.common import read_json
from org_eval.corpus import TextCorpus
from org_eval.runner import run_matrix, run_judging
from org_eval.audit import export_audit, import_audit
from org_eval.report import report
from scripts.smoke_agent import make_fixture


QUESTION = "What Atlas API incident was reported, was recovery verified, and were routine checks actually performed?"


class SyntheticClient:
    def __init__(self, responder):
        self.responder, self.trace, self.calls = responder, [], 0

    def json(self, system, packet, schema, purpose):
        self.calls += 1
        result = self.responder(packet, self.calls, purpose)
        self.trace.append({"cached": False, "status": "completed", "usage": {
            "input_tokens": 100, "output_tokens": 40, "cached_input_tokens": 10, "reasoning_output_tokens": 5},
            "latency_seconds": .01, "synthetic": True})
        return result, f"synthetic-{self.calls}"

    def close(self):
        pass


def synthetic_benchmark(gp, directory):
    directory = Path(directory)
    corpus = TextCorpus(SourceArtifacts.load(gp))
    incident = next(p for r in corpus.records for p in r["passages"] if r["record_id"] == "SMOKE-1")
    routine = next(p for r in corpus.records for p in r["passages"] if r["record_id"] == "SMOKE-2")
    def ref(p):
        return {k: p[k] for k in ("evidence_id", "quote", "start")}
    descriptions = ["Errors were reported on September 1, 2026 for 20 minutes.", "Recovery was not verified.",
                    "The runbook requires twice-daily health checks.", "The requirement does not establish execution."]
    facets = [{"id": f"F{i+1}", "description": text, "kind": "fact" if i % 2 == 0 else "uncertainty",
               "evidence": [ref(incident if i < 2 else routine)], "evidence_rule": "any", "rationale": "Synthetic quoted fixture."}
              for i, text in enumerate(descriptions)]
    questions = [{**s, "text": QUESTION,
                  "paraphrase": "What does the Atlas API history establish about its outage, recovery, and actual health-check execution?",
                  "facets": facets, "cautions": [{"statement": "Do not assert verified recovery or actual twice-daily execution.",
                      "evidence": [ref(incident), ref(routine)], "rationale": "The fixture explicitly denies this evidence."}],
                  "reference_limitations": ["Synthetic plumbing fixture, not a real benchmark."],
                  "source_pool_record_ids": ["SMOKE-1", "SMOKE-2"]} for s in SLOTS]
    draft = {"version": "benchmark-v1", "graph_hash": corpus.source.identity["graph_hash"],
             "corpus_fingerprint": corpus.fingerprint, "status": "draft", "generation": {"synthetic": True}, "questions": questions}
    dp, rp, fp = directory / "draft.json", directory / "synthetic_review.json", directory / "frozen.json"
    atomic_json(dp, draft)
    write_review_template(dp, rp)
    review = read_json(rp)
    review["reviewer"] = "SYNTHETIC FIXTURE — no human review occurred"
    for r in review["questions"]:
        r.update(approved=True, notes="Synthetic control-flow test only.")
    atomic_json(rp, review)
    if not fp.exists():
        freeze(corpus, dp, rp, fp)
    return fp


def answer_factory(job, config):
    def respond(packet, step, purpose):
        if purpose == "evaluation_text_rag":
            passages = [p for r in packet["records"] for p in r["passages"]]
        else:
            if job.get("approach") == "memory_graph":
                recalled = [m for m in packet["messages"] if m.get("name") == "recall_memory"]
                inspected = [m for m in packet["messages"] if m.get("name") == "inspect_memory"]
                if not recalled:
                    return action("recall_memory", {"cue": "Atlas API"})
                if not inspected:
                    item = json.loads(recalled[-1]["content"])["results"][0]["item_id"]
                    return action("inspect_memory", {"item_id": item})
            tools = [m for m in packet["messages"] if m.get("name") == "search_graph"]
            if not tools:
                return action("search_graph", {"query": "Atlas API", "mode": "records"})
            passages = json.loads(tools[-1]["content"])["records"]["results"]
        claims = [{"statement": p["quote"], "kind": "source_report" if p["record_id"] == "SMOKE-1" else "prescription",
                   "citations": [{k: p[k] for k in ("evidence_id", "quote", "start")}], "memory_ids": [],
                   "confidence": "high", "confidence_reason": "Synthetic direct quotation.", "verification_note": "Fixture."}
                  for p in passages]
        if job.get("approach") == "memory_graph":
            item = json.loads(inspected[-1]["content"])
            for claim in claims:
                if claim["citations"][0]["evidence_id"] in item["evidence_ids"]:
                    claim["memory_ids"] = [item["item_id"]]
        draft = {"claims": claims, "unanswered": [], "limitations": ["Synthetic answer."]}
        return draft if purpose == "evaluation_text_rag" else action("DraftAnswer", draft)
    return SyntheticClient(respond)


def action(name, args):
    return {"tool_name": name, "arguments_json": json.dumps(args), "purpose": "Synthetic retrieval check.",
            "discarded_items": [], "pin_evidence_ids": []}


def judge_factory():
    def respond(packet, step, purpose):
        if purpose == "evaluation_consistency":
            return {"comparable_pairs": [{"left_claim_id": c["id"], "right_claim_id": c["id"], "relation": "agreement",
                                           "rationale": "Synthetic same-claim comparison."} for c in packet["left"]["claims"]],
                    "review_flags": []}
        claims = packet["answer"]["claims"]
        return {"claims": [{"claim_id": c["id"], "atomic_statement": c["statement"], "verdict": "supported",
                            "evidence_ids": [r["evidence_id"] for r in c["citations"]], "rationale": "Synthetic judgment."} for c in claims],
                "facets": [{"facet_id": f["id"], "score": 1, "claim_ids": [c["id"] for c in claims],
                            "rationale": "Synthetic coverage."} for f in packet["reference_facets"]],
                "specificity": {"score": 4, "rationale": "Synthetic anchor."}, "internal_contradictions": [],
                "reference_omissions": [], "review_flags": []}
    return SyntheticClient(respond)


def smoke(output):
    output = Path(output)
    gp, mp = output / "fixture" / "graph.json", output / "fixture" / "memory.json"
    if not gp.exists() or not mp.exists():
        gp, mp = make_fixture(output / "fixture")
    benchmark = synthetic_benchmark(gp, output / "benchmark")
    experiment = output / "experiment"
    run_matrix(gp, mp, benchmark, experiment, AgentConfig(), client_factory=answer_factory)
    run_judging(experiment, AgentConfig(model="gpt-6-sol"), client_factory=judge_factory)
    export_audit(experiment)
    review = read_json(experiment / "audit.template.json")
    review["reviewer"] = "SYNTHETIC FIXTURE — no human review occurred"
    for r in review["items"]:
        r.update(reviewed=True, notes="Synthetic audit import test only.")
    atomic_json(experiment / "audit.synthetic.json", review)
    import_audit(experiment, experiment / "audit.synthetic.json")
    result = report(experiment)
    return {"synthetic": True, "status": result["status"], "answers": len(result["rows"]),
            "consistency_pairs": len(result["consistency"]), "report": str(experiment / "report" / "report.html"),
            "limitation": "Scripted answers, usage and judgments verify the pipeline only, not model quality or speed."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="artifacts/evaluation/synthetic_smoke")
    print(json.dumps(smoke(parser.parse_args().output), indent=2))
