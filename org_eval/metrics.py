"""Deterministic metrics with explicit undefined values and usage completeness."""
from collections import Counter

from org_agent.runtime import walk
from org_agent.tools import text_of


def shown_spans(answer):
    tools = {e["call_id"]: e for e in answer["trace"] if e["kind"] == "tool"}
    shown = []
    for event in answer["trace"]:
        if event["kind"] != "context":
            continue
        for call_id in event.get("included_tool_call_ids", []):
            for row in walk(tools.get(call_id, {}).get("result", {})):
                if all(k in row for k in ("evidence_id", "quote", "start", "end")):
                    if row["evidence_id"] in event.get("visible_evidence_ids", []):
                        shown.append(row)
    return shown


def reference_shown(ref, spans, corpus):
    aliases = corpus.aliases(ref["evidence_id"])
    end = ref["start"] + len(ref["quote"])
    return any(s["evidence_id"] in aliases and s["start"] <= ref["start"] and end <= s["end"]
               and s["quote"][ref["start"]-s["start"]:end-s["start"]] == ref["quote"] for s in spans)


def usage_metrics(answer):
    events = [e for e in answer["trace"] if e["kind"] == "model"]
    new = [e for e in events if not e.get("provider", {}).get("cached", False)]
    inputs, outputs, cached, reasoning = 0, 0, 0, 0
    missing = max(0, answer["usage"].get("model_calls", len(events)) - len(events))
    if not events and answer.get("status") == "failed":
        missing = max(missing, 1)
    for e in new:
        u = e.get("provider", {}).get("usage") or {}
        i, o = u.get("input_tokens", u.get("prompt_tokens")), u.get("output_tokens", u.get("completion_tokens"))
        if i is None or o is None:
            missing += 1
        inputs += i or 0
        outputs += o or 0
        cached += u.get("cached_input_tokens", (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0)) or 0
        reasoning += u.get("reasoning_output_tokens", (u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)) or 0
    replays = len(events) - len(new)
    return {"input_tokens": inputs if not missing else None, "output_tokens": outputs if not missing else None,
            "reported_input_tokens_lower_bound": inputs, "reported_output_tokens_lower_bound": outputs,
            "cached_input_tokens_subset": cached, "reasoning_output_tokens_subset": reasoning,
            "calls_without_complete_usage": missing, "cache_replays": replays,
            "fresh_measurement": replays == 0, "model_calls": answer["usage"].get("model_calls", len(events)),
            "tool_calls": answer["usage"].get("data_tool_calls", 0),
            "latency_seconds": answer["usage"].get("total_elapsed_seconds"),
            "estimated_cost_usd": None}


def score_answer(question, answer, judgment, corpus):
    spans = shown_spans(answer)
    citations = [c for claim in answer["claims"] for c in claim["citations"]]
    valid_citations = 0
    for c in citations:
        e = corpus.source.index["evidence"].get(c["evidence_id"])
        if e is None:
            continue
        end = c["start"] + len(c["quote"])
        exact = text_of(e)[c["start"]:end] == c["quote"]
        shown = any(s["evidence_id"] == c["evidence_id"] and s["start"] <= c["start"] and end <= s["end"]
                    and s["quote"][c["start"]-s["start"]:end-s["start"]] == c["quote"] for s in spans)
        valid_citations += bool(exact and shown)
    verdicts = Counter(v["verdict"] for v in judgment["claims"])
    count = sum(verdicts.values())
    facets = {f["facet_id"]: f for f in judgment["facets"]}
    visibility = []
    for f in question["facets"]:
        seen = [reference_shown(r, spans, corpus) for r in f["evidence"]]
        available = all(seen) if f["evidence_rule"] == "all" else any(seen)
        visibility.append({"facet_id": f["id"], "evidence_shown": available,
                           "coverage": facets[f["id"]]["score"],
                           "diagnosis": ("covered" if facets[f["id"]]["score"] == 1 else
                                         "available_evidence_not_fully_used" if available else "reference_evidence_not_fully_shown")})
    return {"coverage": sum(f["score"] for f in judgment["facets"]) / len(question["facets"]),
            "groundedness": verdicts["supported"] / count if count else None,
            "grounding_counts": dict(verdicts), "atomic_claims": count,
            "specificity": judgment["specificity"]["score"],
            "citation_validity": valid_citations / len(citations) if citations else None,
            "invalid_delivered_citations": len(citations) - valid_citations,
            "excluded_claim_validation_errors": answer["validation_errors"],
            "internal_contradictions": len(judgment["internal_contradictions"]),
            "facet_visibility": visibility, "cost": usage_metrics(answer)}


def consistency_metrics(left_judgment, right_judgment, consistency):
    left = {f["facet_id"] for f in left_judgment["facets"] if f["score"] == 1}
    right = {f["facet_id"] for f in right_judgment["facets"] if f["score"] == 1}
    pairs = consistency["comparable_pairs"]
    n = sum(p["relation"] == "contradiction" for p in pairs)
    return {"supported_facet_jaccard": len(left & right) / len(left | right) if left | right else None,
            "comparable_pairs": len(pairs), "contradictions": n,
            "contradiction_rate": n / len(pairs) if pairs else None,
            "review_flags": consistency["review_flags"]}


def failure_judgment(question):
    return {"claims": [], "facets": [{"facet_id": f["id"], "score": 0, "claim_ids": [],
                                      "rationale": "No structured answer was produced."} for f in question["facets"]],
            "specificity": {"score": 0, "rationale": "Failed run has no answer."},
            "internal_contradictions": [], "reference_omissions": [], "review_flags": ["failed_answer"]}
