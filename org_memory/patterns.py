"""Declared, falsifiable mechanism hypotheses for the offline baseline.

These are analyst-designed candidate detectors, not claims of open-ended LLM
discovery. Each is admitted only if original excerpts in independent episode
groups support every required signal. Hosted abstraction is deferred in schema 3.0.
"""
import re

from .evidence import normalize, stable_id


HYPOTHESES = [
    {
        "name": "Processing failures with detection or response gaps",
        "signals": [r"job|processing|queue|pipeline", r"killed|backup|backlog|stopped|degraded|failing|failure",
                    r"no (?:automated )?alarm|no alert|not caught|no action was taken"],
        "statement": "Independent incidents describe stalled or repeatedly failing processing alongside gaps in automated detection or response.",
        "limits": "This does not establish one technical cause or claim that alarms never fired in every incident.",
    },
    {
        "name": "Incomplete or inconsistent stored data",
        "signals": [r"docdb|documentdb|elasticsearch", r"incomplete|uneven|drift|inconsisten|data gaps|mismatch"],
        "statement": "Independent decision bundles report incomplete or inconsistent stored data; the evidence does not establish a single common root cause.",
        "limits": "A storage symptom is shared; cursor handling and partial updates remain distinct candidate mechanisms.",
    },
    {
        "name": "Pruning state fails to propagate to the user interface",
        "signals": [r"prun|hidden narrative", r"refresh|sync|reappear|remains? hidden",
                    r"does not|not refresh|not reappear|remains hidden|not sync|persist"],
        "statement": "Independent pruning-related bundles report user-visible state that fails to update after a rule or visibility change.",
        "limits": "Reports may be related regressions; exact chronology and independence require review of the original tickets.",
    },
    {
        "name": "Different views expose inconsistent statistics",
        "signals": [r"\b(?:counts?|statistics?|stats|views)\b", r"mismatch|discrepan|inconsisten|does not match"],
        "statement": "Independent bundles report inconsistent counts or statistics across views or data representations.",
        "limits": "The records do not show that every discrepancy comes from the same aggregation or synchronization defect.",
    },
    {
        "name": "State crosses network boundaries",
        "signals": [r"\bnetwork\b", r"\bwrong network\b|\bacross networks\b|\banother network\b|\bdifferent network\b|\bcross[- ]network\b"],
        "statement": "Independent bundles describe state or actions carrying across network boundaries where isolation is expected.",
        "limits": "This is a tentative grouping of symptoms, not a claim of a common implementation bug.",
    },
    {
        "name": "Upstream success without downstream completion",
        "signals": [r"upload|\bapi\b|response|\bs3\b", r"success|uploaded|\b200\b",
                    r"not.*(?:start|ingest|process)|no.*(?:response|message)|fail", r"downstream|ingest|sqs|dagster|pipeline"],
        "statement": "Independent bundles describe successful upstream steps accompanied by missing or failed downstream processing.",
        "limits": "Successful upstream responses alone do not establish end-to-end pipeline health; root causes can differ.",
    },
]


def independent_support(memory, candidates):
    """Conservative independence: no shared decisions, cited substantive records,
    or identical substantive excerpts. Administrative parent records do not
    make otherwise distinct reports dependent.
    """
    selected, rejected = [], []
    seen_decisions, seen_records, seen_spans, seen_events = set(), set(), set(), set()
    for episode, eids in sorted(candidates, key=lambda p: p[0]["id"]):
        records = {memory["evidence"][eid]["record_id"] for eid in eids}
        spans = {normalize(memory["evidence"][eid]["source_span"] or "") for eid in eids}
        decisions = set(episode["decision_ids"])
        # A retest that points at an existing fix does not supply a new incident.
        decisions |= {n for eid in eids for n in [memory["evidence"][eid]["source_id"], memory["evidence"][eid]["target_id"]]
                      if memory["nodes"][n]["type"] == "decision"}
        events = {n for eid in eids for n in [memory["evidence"][eid]["source_id"], memory["evidence"][eid]["target_id"]]
                  if memory["nodes"][n]["type"] in {"event", "risk"}}
        if decisions & seen_decisions or records & seen_records or spans & seen_spans or events & seen_events:
            rejected.append({"episode_id": episode["id"], "reason": "overlapping decision, source record, risk/event, or repeated excerpt"})
            continue
        selected.append((episode, sorted(eids)))
        seen_decisions |= decisions
        seen_records |= records
        seen_spans |= spans
        seen_events |= events
    return selected, rejected


def build_patterns(memory, min_support=2):
    patterns, traces = [], []
    for h in HYPOTHESES:
        candidates = []
        for ep in memory["episodes"]:
            if ep["retention"] != "retained" or ep["kind"] == "documented_routine":
                continue
            rows = [memory["evidence"][eid] for eid in ep["evidence_ids"]
                    if memory["evidence"][eid]["status"] == "source_report"]
            text = " ".join(e["source_span"] or "" for e in rows)
            if all(re.search(pattern, text, re.I) for pattern in h["signals"]):
                used = [e["id"] for e in rows if any(re.search(p, e["source_span"] or "", re.I) for p in h["signals"])]
                candidates.append((ep, used))
        support, rejected = independent_support(memory, candidates)
        trace = {"action": "assess_pattern_hypothesis", "hypothesis": h["name"],
                 "method": "declared_signal_rules", "candidate_count": len(candidates),
                 "independent_count": len(support), "discarded": rejected,
                 "candidates": [{"episode_id": ep["id"], "evidence_ids": refs} for ep, refs in candidates],
                 "supporting_episode_ids": [ep["id"] for ep, _ in support],
                 "decision": "admit" if len(support) >= min_support else "reject_insufficient_independent_support"}
        traces.append(trace)
        if len(support) < min_support:
            continue
        evidence_ids = sorted({eid for _, eids in support for eid in eids})
        pid = stable_id("pattern", [h["name"], [ep["id"] for ep, _ in support]])
        confidence = "low" if len(support) == 2 else "medium"
        patterns.append({
            "id": pid, "type": "pattern", "kind": "candidate_mechanism",
            "title": h["name"], "statement": h["statement"], "summary": h["statement"],
            "claims": [{"text": h["statement"], "evidence_ids": evidence_ids,
                        "status": "inferred", "method": "cross_episode_synthesis",
                        "role": "pattern", "confidence": confidence}],
            "supporting_episode_ids": [ep["id"] for ep, _ in support],
            "support_by_episode": {ep["id"]: eids for ep, eids in support},
            "independent_support_count": len(support), "evidence_ids": evidence_ids,
            "record_ids": sorted({memory["evidence"][eid]["record_id"] for eid in evidence_ids}),
            "entity_ids": sorted({n for ep, _ in support for n in ep["entity_ids"]}),
            "node_ids": sorted({n for ep, _ in support for n in ep["node_ids"]}),
            "confidence": confidence, "retention": "retained",
            "retention_reason": "Cross-episode synthesis with independently counted source support.",
            "uncertainties": [h["limits"], "No systematic absence-of-pattern counterexample search; frequency is not a failure rate."],
            "construction": "declared_signal_rules",
        })
    return sorted(patterns, key=lambda p: p["id"]), traces
