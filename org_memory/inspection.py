"""Explicit analyst inspection notes on the offline baseline and source evidence.

These notes were written after reading the named source passages. They are
development audits, not independent gold answers or a hosted-model evaluation.
"""
import json
from pathlib import Path

from .evidence import stable_id


def _interpretations(memory, refs, quote=None):
    claims = []
    for kind in ("episodes", "facts"):
        for item in memory.get(kind, []):
            for claim in item["claims"]:
                if claim["status"] in {"source_excerpt", "unreviewed"}:
                    continue  # Group acceptance is not semantic classification of each passage.
                anchors = [a for a in claim.get("anchors", []) if a["evidence_id"] in refs
                           and (quote is None or quote in a["quote"] or a["quote"] in quote)]
                if anchors:
                    claims.append({"item_id": item["id"], "text": claim["text"], "status": claim["status"], "anchors": anchors})
    return claims


def reference_table(memory, path):
    references = json.loads(Path(path).read_text())
    rows = []
    for case in references["cases"]:
        for statement in case.get("statements", []):
            matches = [e for e in memory["evidence"].values()
                       if e["provenance"]["kind"] == "extracted" and e["record_id"] == statement["record_id"]
                       and statement["quote_contains"] in (e["source_span"] or "")]
            if not matches:
                raise ValueError(f"Reference passage absent: {case['case_id']}")
            refs = {e["id"] for e in matches}
            claims = _interpretations(memory, refs, statement["quote_contains"])
            statuses = sorted({c["status"] for c in claims} or {e["status"] for e in matches if "status" in e})
            episodes = [ep for ep in memory.get("episodes", []) if refs & set(ep["evidence_ids"])]
            rows.append({"case": case["case_id"], "statement": statement["statement"],
                         "record_id": statement["record_id"], "evidence_ids": sorted(refs),
                         "matched_quote": min((e["source_span"] for e in matches), key=len),
                         "expected_status": statement["status"], "actual_statuses": statuses,
                         "comparison": "pending interpretation" if not statuses else (
                             "agrees on classification" if statement["status"] in statuses else "classification disagreement; inspect source"),
                         "matching_episode_ids": [e["id"] for e in episodes], "matching_claims": claims,
                         "candidate_ids": sorted({cid for ep in episodes for cid in ep.get("candidate_ids", [])}),
                         "inspection_note": case.get("inspection_note", "Development source example; not independent validation."),
                         "unknowns": case.get("unknowns", [])})
    return rows


def inspection_rows(memory):
    rows = []
    episodes = [
        ("KEP-6969", "decision_689ff4ca", "supported with limits",
         "The excerpt preserves the initial detection failure and later alarm-without-action distinction. Recovery is unverified; harmful PRODUCES attribution is flagged."),
        ("KEP-6970", "decision_91e6819f", "supported with limits",
         "Backfill, deployment and callback prerequisite share a substantive dependency bundle. Required backfill remains intended. Separate staging/MR packets show the boundary is incomplete."),
        ("KT-267", "decision_543399bc", "supported with limits",
         "The three KT passages document one routine. The shared node does not prove repeated observed executions; Done is administrative."),
        ("KEP-5342", "decision_164e73bc", "supported with limits",
         "The source describes narratives remaining hidden after rule deletion. KEP-4019 closure does not independently establish this bug's recovery."),
        ("KEP-6688", "decision_d4a54c90", "partially supported",
         "The bundle includes the KEP-6696 follow-up reporting completed jobs and no data loss. The source also contains a likely-cause hypothesis; episode grouping and cause strength remain provisional."),
    ]
    for record, decision, verdict, note in episodes:
        for item in memory["episodes"]:
            if record in item["record_ids"] and decision in item["decision_ids"]:
                rows.append(_row(item, verdict, note, memory))
    facts = [
        ("pruning should only be applicable", "supported", "Faithfully stores a requirement, not proof that deployed pruning enforces it."),
        ("Frequency: Twice Daily", "supported", "Prescribes a routine. No actual run-frequency claim is made."),
        ("Notify the QA group", "supported", "The conditional escalation instruction is a requirement, not a historical notification event."),
        ("the processing timeout was increased", "supported with limits", "The change is explicit; it is historical and does not establish the current timeout or successful recovery."),
        ("Alert on message count > 0", "supported with limits", "The threshold is preserved as a proposed alerting requirement. Its operational effectiveness is not demonstrated."),
    ]
    for prefix, verdict, note in facts:
        for item in memory["facts"]:
            if any((memory["evidence"][eid]["source_span"] or "").startswith(prefix) for eid in item["evidence_ids"]):
                rows.append(_row(item, verdict, note, memory))
    notes = {
        "Processing failures with detection or response gaps": "Two distinct incidents support this limited synthesis. Their technical causes differ, and Argonaut alarms eventually fired. Prevalence is unknown.",
        "Incomplete or inconsistent stored data": "Two sparse passages establish a symptom family. They do not establish a shared root cause or confirm fixes; the pattern correctly retains that limitation.",
        "Pruning state fails to propagate to the user interface": "Rule-list refresh and narrative restoration are distinct user-visible state problems. Retests and token-check failures were excluded from independent support.",
        "Different views expose inconsistent statistics": "Count/view discrepancies recur in distinct report bundles. Structural independence is a conservative proxy, and some reports may still concern related defects.",
        "State crosses network boundaries": "Chat command persistence, starter prompts, and history account addition supply separate examples. The shared symptom does not prove one bug or a security breach.",
    }
    for p in memory["patterns"]:
        if p["title"] in notes:
            rows.append(_row(p, "tentative synthesis", notes[p["title"]], memory))
    return rows


def _row(item, verdict, note, memory):
    if memory["build_metadata"]["mode"] != "offline":
        verdict = "needs fresh semantic review of hosted claims"
        note = "Offline reference note only: " + note
    return {"item_id": item["id"], "type": item["type"], "title": item["title"],
            "record_ids": item["record_ids"], "evidence_ids": item["evidence_ids"],
            "candidate_ids": item.get("candidate_ids", []), "claims": item["claims"],
            "verdict": verdict, "inspection_note": note,
            "review_scope": "coding-assistant inspection of supplied passages; not independent human review or external operational verification"}


def sampled_inspection(memory, path):
    """Fixed, reproducible development sample with source-authored audit notes."""
    config = json.loads(Path(path).read_text())["sample_inspections"]
    selected = sorted((e for e in memory["evidence"].values()
                       if e["provenance"]["kind"] == "extracted" and e["source_span"]),
                      key=lambda e: stable_id("sample", [config["seed"], e["id"]]))[:config["count"]]
    notes = {n["evidence_id"]: n for n in config["notes"]}
    rows = []
    for e in selected:
        note = notes.get(e["id"])
        claims = _interpretations(memory, {e["id"]})
        statuses = {c["status"] for c in claims} or ({e["status"]} if "status" in e else set())
        dispositions = {c["disposition"] for r in memory.get("reviews", []) for c in r.get("proposal", {}).get("coverage", [])
                        if c["excerpt_id"] == stable_id("excerpt", ["extracted", e["source_span"]])}
        rows.append({"evidence_id": e["id"], "record_id": e["record_id"], "quote": e["source_span"],
                     "seed": config["seed"], "expected_statuses": note["expected_statuses"] if note else [],
                     "actual_statuses": sorted(statuses), "review_dispositions": sorted(dispositions),
                     "matching_episode_ids": [ep["id"] for ep in memory.get("episodes", []) if e["id"] in ep["evidence_ids"]],
                     "claims": claims, "inspection_note": note["note"] if note else "Changed dataset: needs fresh source inspection.",
                     "comparison": "pending interpretation" if not statuses and not dispositions else (
                         "agrees on classification" if note and set(note["expected_statuses"]) <= statuses | dispositions
                         else "classification disagreement; inspect source"),
                     "limitation": "Development inspection of supplied passages, not independent human labels or a held-out benchmark."})
    return rows
