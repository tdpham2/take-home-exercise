"""Materialize judge verdicts using deterministic text, IDs, citations and scope."""
from collections import Counter
from dataclasses import asdict
import math
import statistics
import time

from .build import _reviewed_scope, build_aliases
from .candidates import build_candidates
from .evidence import stable_id
from .review import (CONTRACT_VERSION, ROW_SCHEMAS, ReviewIncomplete, automatic_judgments,
                     judge_candidates, make_jobs, make_proposals, requested_ids)


def prepare(index, max_decisions=8, record_ids=()):
    candidates, _, traces = build_candidates(index, max_decisions, include_review_units=False)
    proposals = make_proposals(index)
    jobs = make_jobs(index, candidates, proposals)
    if record_ids:
        available = {e["record_id"] for e in index["evidence"].values()}
        if set(record_ids) - available:
            raise ValueError("Requested pilot records are absent: " + ", ".join(sorted(set(record_ids) - available)))
        jobs = [j for j in jobs if any(index["evidence"][eid]["record_id"] in record_ids for eid in j["evidence_ids"])]
        for field, ids in (("fact_judgments", "fact_ids"), ("outcome_judgments", "outcome_ids")):
            selected = {pid for j in jobs for pid in j[ids]}
            proposals[field] = [p for p in proposals[field] if p["id"] in selected]
    return candidates, proposals, jobs, traces


def verdicts(proposals, reviews):
    result = {f: [{**r, "review_request_id": None, "method": "exact_administrative_guard"}
                   for r in rows] for f, rows in automatic_judgments(proposals).items()}
    for review in reviews:
        for field, rows in review["output"].items():
            result[field].extend({**r, "review_request_id": review["request_id"], "method": "llm_judgment"} for r in rows)
    return {f: sorted(rows, key=lambda r: r["id"]) for f, rows in result.items()}


def anchors(index, refs):
    return [{"evidence_id": eid, "quote": index["evidence"][eid]["source_span"]}
            for eid in refs if index["evidence"][eid]["provenance"]["kind"] == "extracted"
            and (index["evidence"][eid]["source_span"] or "").strip()]


def construct_items(index, candidates, proposals, reviews):
    judged = verdicts(proposals, reviews)
    fact_by_id = {p["id"]: p for p in proposals["fact_judgments"]}
    outcome_by_id = {p["id"]: p for p in proposals["outcome_judgments"]}
    candidate_by_id = {c["id"]: c for c in candidates}
    facts, outcomes, episodes = [], [], []
    lineage = {c["id"]: [] for c in candidates}
    archived_candidates, archived_facts = [], []
    for j in judged["fact_judgments"]:
        p = fact_by_id[j["id"]]
        if not j["is_fact"]:
            archived_facts.append({"proposal_id": p["id"], "reason": j["reason"]})
            continue
        refs, text = p["evidence_ids"], p["text"]
        fid = stable_id("fact", [p["id"], j["kind"]])
        claim = {"id": stable_id("claim", [fid, refs]), "text": text, "evidence_ids": refs[:],
                 "anchors": anchors(index, refs), "status": "source_report" if j["kind"] == "historical_statement" else j["kind"],
                 "role": j["kind"], "method": "judged_whole_excerpt", "confidence": "medium"}
        facts.append({"id": fid, "type": "fact", "proposal_id": p["id"], "kind": j["kind"],
                      "title": text, "statement": text, "summary": text, **_reviewed_scope(refs, index),
                      "entity_ids": [p["subject_id"]], "claims": [claim],
                      "retention": "retained", "retention_reason": j["reason"], "confidence": "medium",
                      "review_request_id": j["review_request_id"], "construction": "judged_whole_excerpt",
                      "uncertainties": ["Source-supported historical knowledge; not independently verified current state.",
                                        "Requirements and routines do not establish execution."]})
    for j in judged["outcome_judgments"]:
        p = outcome_by_id[j["id"]]
        magnitude = {"local": 1, "service-level": 2, "customer-level": 3}.get(j["impact"])
        sign = {"harmful": -1, "beneficial": 1}.get(j["valence"])
        outcomes.append({"id": stable_id("valuation", p["id"]), "outcome_node_id": p["outcome_node_id"],
                         **_reviewed_scope(p["evidence_ids"], index), "anchors": anchors(index, p["evidence_ids"]),
                         "observed": j["observed"], "evidence_status": "source_report" if j["observed"] else "unresolved",
                         "valence": j["valence"], "impact": j["impact"],
                         "signed_impact": sign * magnitude if sign is not None and magnitude is not None else None,
                         "reason": j["reason"], "review_request_id": j["review_request_id"], "method": j["method"],
                         "causal_attribution": "Unverified; a PRODUCES edge does not establish causality.",
                         "limitation": "Ordinal source-based scope, not measured utility; unknown and mixed results are unscored."})
    for j in judged["episode_judgments"]:
        c = candidate_by_id[j["id"]]
        if not j["supported"]:
            archived_candidates.append({"candidate_id": c["id"], "reason": j["reason"]})
            continue
        refs = c["evidence_ids"]
        passages = {}
        for a in anchors(index, refs):
            passages.setdefault(a["quote"], []).append(a["evidence_id"])
        claims = [{"id": stable_id("claim", ["source_excerpt", text, ids]), "text": text, "evidence_ids": ids,
                   "anchors": anchors(index, ids), "status": "source_excerpt", "role": "uninterpreted_source_excerpt",
                   "method": "verbatim_excerpt", "confidence": "medium"} for text, ids in sorted(passages.items())]
        scope = _reviewed_scope(refs, index)
        episode_id = stable_id("episode", c["decision_ids"])
        lineage[c["id"]] = [episode_id]
        episodes.append({"id": episode_id, "type": "episode", "kind": "fixed_evidence_bundle",
                         "candidate_ids": [c["id"]], "decision_ids": c["decision_ids"], **scope,
                         "entity_ids": [n for n in scope["node_ids"] if index["nodes"][n]["type"] == "resource"],
                         "title": " / ".join(index["nodes"][d]["label"] for d in c["decision_ids"][:2]),
                         "title_origin": "unverified graph decision labels",
                         "summary": "\n".join(c["text"] for c in claims), "claims": claims,
                         "outcomes": [o for o in outcomes if set(o["evidence_ids"]) & set(refs)],
                         "time_evidence": [d for eid in refs if index["evidence"][eid]["provenance"]["kind"] == "extracted"
                                           for d in index["evidence"][eid]["dates"]],
                         "inferred_link_ids": [eid for eid in refs if index["evidence"][eid]["provenance"]["kind"] == "inferred"],
                         "retention": "retained" if j["worth_remembering"] else "compressed",
                         "retention_reason": j["reason"], "confidence": "medium", "construction": "fixed_candidate_judgment",
                         "review_request_id": j["review_request_id"],
                         "uncertainties": ["Accepted grouping does not verify every excerpt, graph label or causal claim.",
                                           "Fixed boundaries can conflate occurrences or omit related context; no automatic repair.",
                                           "Compression reduces default recall prominence; all source excerpts remain available."]})
    return {"episodes": sorted(episodes, key=lambda e: e["id"]), "facts": sorted(facts, key=lambda f: f["id"]),
            "outcome_assessments": sorted(outcomes, key=lambda o: o["id"]), "candidate_episode_lineage": lineage,
            "archived_candidates": archived_candidates, "archived_facts": archived_facts, **judged}


def coverage(candidates, proposals, jobs, reviews):
    required = requested_ids(jobs, proposals)
    done = {f: {r["id"] for review in reviews for r in review["output"][f]} for f in ROW_SCHEMAS}
    remaining = {f: sorted(set(required[f]) - done[f]) for f in ROW_SCHEMAS}
    return {"total_candidates": len(candidates), "eligible_candidates": sum(c["eligible"] for c in candidates),
            "selected_candidates": len(required["episode_judgments"]),
            "reviewed_candidates": len(done["episode_judgments"]), "total_judge_packets": len(jobs),
            "reviewed_packets": sum(all(set(ids) <= done[f] for f, ids in requested_ids([j], proposals).items()) for j in jobs),
            "fact_proposals": len(proposals["fact_judgments"]), "outcome_proposals": len(proposals["outcome_judgments"]),
            "automatic_judgments": {f: len(v) for f, v in automatic_judgments(proposals).items()},
            "unreviewed_ids": remaining,
            "ineligible_candidates": [c["id"] for c in candidates if not c["eligible"]]}


def call_summary(trace):
    """Usage actually reported by transports; cached reads are not new token cost."""
    calls = [t for t in trace if not t.get("cached") and t.get("usage") is not None]
    latency = [t["latency_seconds"] for t in trace if not t.get("cached") and "latency_seconds" in t]
    tokens = Counter()
    for t in calls:
        u = t.get("usage") or {}
        tokens["input_tokens"] += u.get("input_tokens", u.get("prompt_tokens", 0))
        tokens["output_tokens"] += u.get("output_tokens", u.get("completion_tokens", 0))
        tokens["cached_input_tokens"] += u.get("cached_input_tokens", (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0))
    costs = [t.get("estimated_this_run_cost_usd") for t in trace if not t.get("cached")]
    return {"reported_new_call_tokens": dict(tokens), "measured_requests": len(latency),
            "elapsed_provider_seconds": round(sum(latency), 4),
            "median_call_seconds": statistics.median(latency) if latency else None,
            "p95_call_seconds": sorted(latency)[max(0, math.ceil(.95 * len(latency)) - 1)] if latency else None,
            "estimated_this_run_cost_usd": sum(costs) if costs and all(c is not None for c in costs) else None,
            "calls_with_rejected_judgments": sum(bool(t.get("judgment_errors")) for t in trace),
            "malformed_response_rate": sum(bool(t.get("judgment_errors")) for t in trace) / len(latency) if latency else None,
            "failed_requests": sum(t.get("status") == "failed" for t in trace),
            "limitation": "Reported token usage only. Failed-call usage can be missing; subscription dollars are unknown."}


def build_judged_memory(index, config, client, *, progress=None, checkpoint=None, record_ids=()):
    from .validation import validate_memory
    if config.llm_max_calls < 1:
        raise ValueError("Hosted call limit must be positive")
    candidates, proposals, jobs, traces = prepare(index, config.max_episode_decisions, record_ids)
    memory = {"schema_version": "3.0", "patterns": [], "evidence": index["evidence"], "nodes": index["nodes"],
              "entity_aliases": build_aliases(index), "candidates": candidates, "proposals": proposals,
              "judge_jobs": jobs, "reviews": [], "traces": traces,
              "build_metadata": {"mode": "hosted", "status": "incomplete", "config": asdict(config),
                                 "judging_contract": CONTRACT_VERSION, "selection_record_ids": sorted(set(record_ids)),
                                 "scope": "pilot" if record_ids else "full_graph",
                                 "pattern_analysis": {"status": "deferred", "reason": "Focus on episodes, facts and fading (1, 2, 5)."},
                                 "graph_hash": index["graph_hash"], "raw_edge_count": index["raw_edge_count"],
                                 "node_count": len(index["nodes"]), "hosted_provider": getattr(client, "provider", "compatible"),
                                 "hosted_model": client.config.model,
                                 "hosted_reasoning_effort": getattr(client.config, "reasoning_effort", None),
                                 "limitations": ["Fixed grouping trades boundary recall for predictable cost; rejected grouping is not a false event.",
                                                 "Whole-excerpt facts can miss useful statements inside mixed passages.",
                                                 "Exact citations and structural checks cannot establish semantic accuracy.",
                                                 "Confidence is a fixed retrieval heuristic, not calibrated probability."]}}
    previous_limit, starting_calls, starting_trace = client.call_limit, client.calls, len(client.trace)
    started = time.monotonic()
    client.call_limit = min(previous_limit, client.calls + config.llm_max_calls)

    def update(persist=True):
        memory.update(construct_items(index, candidates, proposals, memory["reviews"]))
        trace = client.trace[starting_trace:]
        history = [t["call"] for t in traces if t["action"] == "judgment_provider_call"]
        memory["build_metadata"].update({
            "hosted_calls": client.calls - starting_calls, "hosted_call_trace": trace[:],
            "build_elapsed_seconds": round(time.monotonic() - started, 4),
            "usage_summary": call_summary(trace), "coverage": coverage(candidates, proposals, jobs, memory["reviews"]),
            "hosted_call_history": history, "cumulative_usage_summary": call_summary(history),
            "counts": {"episodes": len(memory["episodes"]), "facts": len(memory["facts"]), "patterns": 0,
                       "outcome_assessments": len(memory["outcome_assessments"]),
                       "episode_retention": dict(Counter(e["retention"] for e in memory["episodes"])),
                       "archived_candidates": len(memory["archived_candidates"]), "archived_facts": len(memory["archived_facts"]),
                       "fact_decisions": dict(Counter("accepted" if j["is_fact"] else "rejected" for j in memory["fact_judgments"]))}})
        if checkpoint and persist:
            checkpoint(memory)

    try:
        if progress:
            progress({"stage": "candidates", "eligible_candidates": sum(c["eligible"] for c in candidates),
                      "judge_packets": len(jobs), "pattern_analysis": "deferred"})
        judge_candidates(index, candidates, proposals, jobs, client, config, memory["reviews"], traces, update, progress)
        memory["build_metadata"]["status"] = "complete"
        update(persist=False)
        validate_memory(memory, raise_on_error=True)
        if checkpoint:
            checkpoint(memory)
    except (ReviewIncomplete, ValueError, KeyError, TypeError, OSError, KeyboardInterrupt) as exc:
        reason = str(exc) if isinstance(exc, (ReviewIncomplete, ValueError)) else type(exc).__name__
        memory["build_metadata"].update(status="incomplete", incomplete_reason=reason)
        update()
        raise ReviewIncomplete(reason, memory) from exc
    finally:
        client.call_limit = previous_limit
    return memory
