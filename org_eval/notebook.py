"""Read-only presentation helpers for the Task 2 submission notebook."""
from collections import Counter
import json
from pathlib import Path

from org_agent.runtime import walk
from .common import read_json
from .runner import load_experiment, read_answer


def claim_rows(answer):
    """Keep confidence, route and exact evidence attached to each individual claim."""
    return [{"claim": c["id"], "statement": c["statement"], "kind": c["kind"],
             "route": c["source_mode"], "records": ", ".join(c["record_ids"]),
             "memory_items": ", ".join(c["memory_ids"]) or "none",
             "confidence": c["confidence"], "confidence_reason": c["confidence_reason"],
             "verification_note": c.get("verification_note", ""),
             "exact_citations": "\n\n".join(
                 f"{r['evidence_id']} [{r['start']}:{r['start'] + len(r['quote'])}]: {r['quote']}"
                 for r in c["citations"])} for c in answer["claims"]]


def trace_rows(answer):
    """Every model decision and tool exchange; ranking exclusions are summarized separately."""
    rows = []
    for event in answer["trace"]:
        kind = event["kind"]
        if kind == "model" and event.get("action"):
            a = event["action"]
            rows.append({"sequence": event["sequence"], "event": "action", "operation": a["tool_name"],
                         "detail": a["arguments_json"], "items_or_evidence": ", ".join(a.get("pin_evidence_ids", [])),
                         "reason": a["purpose"]})
        elif kind in {"model_started", "tool_started", "context"} or kind == "model":
            rows.append({"sequence": event["sequence"], "event": kind,
                         "operation": event.get("name", str(event.get("call_number", event.get("model_call", "")))),
                         "detail": json.dumps({k: event[k] for k in
                             ("arguments", "status", "serialized_chars", "included_tool_call_ids") if k in event}, ensure_ascii=False),
                         "items_or_evidence": ", ".join(event.get("pinned_evidence_ids", [])),
                         "reason": event.get("error", event.get("error_type", ""))})
        elif kind == "tool":
            result = event.get("result", {})
            cards = {r["item_id"]: r.get("title", r.get("preview", ""))
                     for r in walk(result) if "item_id" in r and "title_origin" in r}
            evidence = sorted({r["evidence_id"] for r in walk(result) if "evidence_id" in r})
            rows.append({"sequence": event["sequence"], "event": kind, "operation": event["name"],
                         "detail": json.dumps(event.get("arguments", {}), ensure_ascii=False),
                         "items_or_evidence": "\n".join([*[f"{iid}: {title}" for iid, title in cards.items()], *evidence]),
                         "reason": ("Tool error: " + json.dumps(result, ensure_ascii=False)
                                    if event.get("error") else "Returned evidence; see full JSONL for text and ranking.")})
        elif kind in {"item_discard", "context_item_eviction", "context_eviction", "claim_support", "stopped",
                      "invalid_selection", "citation_repair", "action_repair"}:
            ids = [event["item_id"]] if "item_id" in event else event.get("item_ids", [])
            ids = [*ids, *event.get("memory_ids", []), *event.get("evidence_ids", [])]
            rows.append({"sequence": event["sequence"], "event": kind,
                         "operation": event.get("claim_id", event.get("call_id", "")),
                         "detail": event.get("source_mode", "") or json.dumps(event.get("errors", []), ensure_ascii=False),
                         "items_or_evidence": ", ".join(ids),
                         "reason": event.get("reason", event.get("verification_note", ""))})
    return rows


def ranking_exclusions(answer):
    counts = Counter(e.get("reason", "unspecified") for e in answer["trace"] if e["kind"] == "retrieval_discard")
    return [{"ranking_exclusion_reason": reason, "events": count} for reason, count in sorted(counts.items())]


def load_saved_results(output):
    """Never run providers or synthesize results, and reject stale or synthetic reports."""
    output = Path(output)
    if not (output / "manifest.json").exists():
        return None, None, None
    manifest, _, benchmark = load_experiment(output)
    if manifest["synthetic_provider"]:
        raise ValueError("Submission notebook requires real runs; synthetic results cannot substitute for them")
    for job in manifest["schedule"]:
        if (output / "runs" / job["run_id"] / "answer.json").exists():
            read_answer(output, job["run_id"])
    path = output / "report" / "report.json"
    result = read_json(path) if path.exists() else None
    if result:
        if result.get("synthetic") or result["manifest_fingerprint"] != manifest["fingerprint"]:
            raise ValueError("Report does not describe this real experiment")
        for row in result["rows"]:
            ap = output / "runs" / row["run_id"] / "answer.json"
            status = read_answer(output, row["run_id"])["status"] if ap.exists() else "not_run"
            if row["status"] != status:
                raise ValueError("Report is stale after new answers; regenerate it before displaying results")
        if result.get("audit"):
            from .audit import audit_basis
            if result["audit"]["basis_fingerprint"] != audit_basis(output):
                raise ValueError("Report audit is stale")
    return manifest, benchmark, result
