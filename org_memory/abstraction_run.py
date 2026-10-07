"""Resumable, bounded execution of frozen abstraction packets and inspection reports."""
import copy
import json
from pathlib import Path
import time

from .abstraction import (PROMPT, RESPONSE_SCHEMA, VERSION, SCHEMA_VERSION, LIMITATION,
                          fingerprint, make_plan, materialize, require_base, serialized)
from .evidence import stable_id
from .hosted import BudgetExceeded, _check_schema
from .judged import call_summary
from .recall import RecallIndex
from .storage import atomic_json

# Evaluation questions are separate from routing cues; results are an inspection aid,
# not a held-out relevance benchmark or an automatic semantic correctness judgment.
RECALL_QUESTIONS = [
    "What evidence would help an engineering lead assess whether a completed step delivered the expected user result?",
    "Where should we investigate if different representations of the same information disagree?",
    "Which operational activities were requested, and which were actually reported as performed?",
    "What should be checked when a user action fails to change the visible state?",
]
PREVIEW_NOTICE = ("Provisional test of reviewed evidence from a frozen checkpoint. "
                  "This is not the completed-memory pilot; its calls do not transfer to production.")


def load_preview_memory(source, out):
    """Freeze once, then resume that snapshot even as the original build advances."""
    if not str(source).strip():
        raise ValueError("--memory is empty. Pass the checkpoint path directly.")
    source, out = Path(source).resolve(), Path(out).resolve()
    if source.parent == out:
        raise ValueError("Preview output must differ from the base memory directory")
    checkpoint = out / "checkpoint.json"
    if checkpoint.exists() and json.loads(checkpoint.read_text())["metadata"].get("execution_scope") != "preview":
        raise ValueError("Output contains a production/pilot run; use a separate preview output directory")
    snapshot = out / "preview_input.json"
    if snapshot.exists():
        envelope = json.loads(snapshot.read_text())
        if envelope["source_path"] != str(source):
            raise ValueError("Preview source path changed; use a new --output directory for a new snapshot")
        base = envelope["memory"]
        if fingerprint(base) != envelope["base_fingerprint"]:
            raise ValueError("Frozen preview input fingerprint changed")
    else:
        base = json.loads(source.read_text())
    require_base(base, preview=True)
    if not snapshot.exists():
        atomic_json(snapshot, {"source_path": str(source), "base_fingerprint": fingerprint(base),
                               "notice": PREVIEW_NOTICE, "memory": base})
    return base


def settings_for(client):
    return {"provider": getattr(client, "provider", "compatible"), "model": client.config.model,
            "reasoning_effort": getattr(client.config, "reasoning_effort", None),
            "base_url": getattr(client.config, "base_url", None),
            "response_format": getattr(client.config, "response_format", None),
            "adapter_version": 1 if getattr(client, "provider", "") == "codex" else None}


def pilot_packets(plan):
    """One packet per first three configured areas, from the full frozen plan."""
    result = []
    for area in plan["areas"][:3]:
        first = next((p["id"] for p in plan["packets"] if p["question_id"] == area["id"]), None)
        if first:
            result.append(first)
    return result


def coverage_report(plan, reviews):
    done = {r["packet_id"] for r in reviews}
    processed = sorted({b for p in plan["packets"] if p["id"] in done for b in p["primary_bundle_ids"]})
    context = sorted({b for p in plan["packets"] if p["id"] in done for b in p["context_bundle_ids"]})
    return {k: v for k, v in plan.items() if k not in {"packets", "bundles"}} | {
        "planned_packets": len(plan["packets"]), "processed_packets": len(done),
        "processed_bundle_ids": processed, "processed_context_bundle_ids": context,
        "unprocessed_selected_bundle_ids": sorted(set(plan["selected_bundle_ids"]) - set(processed)),
        "remaining_packet_ids": [p["id"] for p in plan["packets"] if p["id"] not in done]}


def recall_comparison(base, enriched):
    without, with_patterns = RecallIndex(base), RecallIndex(enriched)
    patterns = {p["id"]: p for p in enriched["patterns"]}
    rows = []
    for question in RECALL_QUESTIONS:
        baseline = without.recall(question, 8)
        augmented = with_patterns.recall(question, 8)
        retrieved = {r["item_id"] for r in augmented["results"]}
        checks = [{"pattern_id": pid, "statement": patterns[pid]["statement"],
                   "supporting_episode_ids": patterns[pid]["supporting_episode_ids"],
                   "retrieved_supporting_episode_ids": sorted(retrieved & set(patterns[pid]["supporting_episode_ids"])),
                   "retrieved_supporting_fact_ids": sorted(retrieved & set(patterns[pid]["supporting_fact_ids"])),
                   "semantic_inspection": "pending human/agent inspection of cited passages"}
                  for pid in sorted(retrieved & patterns.keys())]
        rows.append({"question": question, "without_abstractions": baseline, "with_abstractions": augmented,
                     "returned_pattern_checks": checks})
    return {"questions_fingerprint": stable_id("recall_questions", RECALL_QUESTIONS), "results": rows,
            "limitation": "Additional inspection questions, not labeled ground truth. Retrieval changes alone do not establish helpfulness or correctness."}


def inspection_examples(plan, reviews, materialized):
    packets = {p["id"]: p for p in plan["packets"]}
    rows = []
    for review in reviews:
        p = packets[review["packet_id"]]
        cited = {s["passage_id"] for row in review["output"]["proposals"] for s in row["support"]}
        cited |= {pid for row in review["output"]["proposals"] for pid in row["counterevidence_ids"]}
        rows.append({**review, "question": p["question"],
                     "cited_passages": [s for s in p["passages"] if s["id"] in cited],
                     "inspection_status": "pending semantic inspection; structural admission is not correctness"})
    return {"packets": rows, **{k: v for k, v in materialized.items() if k != "patterns"},
            "review_checklist": ["Does every statement follow from the cited passages?", "Does comparison add useful insight?",
                                 "Are prescriptions kept distinct from execution?", "Are differences and counterevidence represented?",
                                 "Do recalled patterns help retrieve their supporting episodes?"], "limitation": LIMITATION}


def run_abstraction(base, questions, out, client=None, *, max_calls=40, pilot=False, dry_run=False,
                    max_chars=100000, progress=None, preview=False):
    require_base(base, preview=preview)
    if max_calls < 0:
        raise ValueError("Call budget must be nonnegative")
    plan = make_plan(base, questions, max_chars=max_chars)
    out = Path(out)
    if not preview and (out / "preview_input.json").exists():
        raise ValueError("Output contains a provisional preview; choose a separate production --output directory")
    base_hash = fingerprint(base)
    if dry_run:
        atomic_json(out / "dry_run.json", {"base_fingerprint": base_hash, "initial_calls": len(plan["packets"]),
                                           "pilot_packet_ids": pilot_packets(plan), "max_new_calls": max_calls,
                                           "execution_scope": "preview" if preview else "production",
                                           "preview_notice": PREVIEW_NOTICE if preview else None,
                                           "selected_initial_calls": len(pilot_packets(plan)) if preview or pilot else len(plan["packets"]),
                                           "base_coverage": base["build_metadata"]["coverage"],
                                           "coverage": coverage_report(plan, []),
                                           "packet_sizes": [{"id": p["id"], "characters": len(serialized(p))}
                                                            for p in plan["packets"]],
                                           "note": "No model calls made; repairs consume additional budget. Oversized bundles prevent completion."})
        return None, plan
    if client is None:
        raise ValueError("A hosted client is required except for --dry-run")
    settings = settings_for(client)
    prompt_hash = stable_id("prompt", [PROMPT, RESPONSE_SCHEMA])
    identity = {"base_fingerprint": base_hash, "questions": questions,
                "packet_ids": [p["id"] for p in plan["packets"]],
                "prompt_fingerprint": prompt_hash, "settings": settings, "version": VERSION}
    if preview:
        identity["preview"] = True
    run_id = stable_id("abstraction", identity)
    checkpoint_path = out / "checkpoint.json"
    if checkpoint_path.exists() and json.loads(checkpoint_path.read_text())["run_id"] != run_id:
        raise ValueError("Output contains a different frozen run; choose a new --output directory")
    selected = set(pilot_packets(plan) if pilot or preview else identity["packet_ids"])
    caches, paths = {}, {}
    for packet in plan["packets"]:
        key = stable_id("synthesis", {"base_fingerprint": base_hash, "packet": packet,
                                      "prompt": prompt_hash, "settings": settings, **({"preview": True} if preview else {})})
        path = Path(client.config.cache_dir) / VERSION / f"{key}.json"
        paths[packet["id"]] = path
        envelope = json.loads(path.read_text()) if path.exists() else {"key": key, "packet_id": packet["id"], "attempts": [], "review": None}
        if envelope.get("key") != key or envelope.get("packet_id") != packet["id"]:
            raise ValueError("Abstraction cache identity mismatch")
        caches[packet["id"]] = envelope
    start_calls, prior_limit = client.calls, client.call_limit
    client.call_limit = min(prior_limit, start_calls + max_calls)
    run_trace = []
    reason = "Pilot selected from the full frozen plan" if pilot else "Pending packets"
    enriched = None

    def update():
        nonlocal enriched
        reviews = [caches[p["id"]]["review"] for p in plan["packets"] if caches[p["id"]]["review"] is not None]
        result = materialize(base, plan, reviews)
        calls = [a["call"] for p in plan["packets"] for a in caches[p["id"]]["attempts"] if "call" in a]
        complete = len(reviews) == len(plan["packets"]) and not plan["oversized_bundles"]
        enriched = {**base, "schema_version": SCHEMA_VERSION, "patterns": result["patterns"],
                    "abstraction_metadata": {**identity, "run_id": run_id, "max_packet_chars": max_chars,
                        "status": "complete" if complete else "incomplete", "incomplete_reason": None if complete else reason,
                        "execution_scope": "pilot" if pilot else "production", "reviews": reviews,
                        **{k: v for k, v in result.items() if k != "patterns"},
                        "coverage": coverage_report(plan, reviews), "new_calls_this_run": client.calls - start_calls,
                        "call_history": calls, "usage_summary": call_summary(calls), "this_run_usage": call_summary(run_trace),
                        "semantic_inspection": "pending; inspect every pilot proposal before freezing configuration",
                        "offline_baseline": "artifacts/offline/memory.json; declared hypotheses, not hosted discoveries",
                        "limitations": [LIMITATION, "Question-focused selection is not exhaustive. Requirements do not establish execution."]}}
        meta = enriched["abstraction_metadata"]
        if preview:
            oversized = any(b["question_id"] in {a["id"] for a in plan["areas"][:3]}
                            for b in plan["oversized_bundles"])
            finished = selected <= {r["packet_id"] for r in reviews} and not oversized
            meta.update(status="preview", execution_scope="preview", preview_notice=PREVIEW_NOTICE,
                        preview_status="complete" if finished else "incomplete",
                        preview_packet_ids=pilot_packets(plan), base_coverage=base["build_metadata"]["coverage"],
                        incomplete_reason=None if finished else reason)
            meta["limitations"].append(PREVIEW_NOTICE)
        meta["coverage"]["execution_scope"] = meta["execution_scope"]
        measured = [c["latency_seconds"] for c in calls if not c.get("cached") and c.get("status") != "failed"]
        remaining = len(selected - {r["packet_id"] for r in reviews}) if preview else len(plan["packets"]) - len(reviews)
        meta["forecast"] = {"measured_calls": len(measured),
                            "remaining_initial_call_seconds": (sum(measured) / len(measured) * remaining) if measured else None,
                            "limitation": "Based on measured packet calls only; packet sizes, repairs and failures can change runtime. Subscription dollars unknown."}
        atomic_json(checkpoint_path, {"run_id": run_id, "status": meta["status"], "metadata": meta})
        atomic_json(out / ("memory.preview.json" if preview else "memory.incomplete.json"), enriched)
        atomic_json(out / "coverage.json", meta["coverage"])
        atomic_json(out / "hosted_calls.json", calls)
        atomic_json(out / "rejected_proposals.json", result["rejected_proposals"])
        atomic_json(out / "rejected_responses.json", [
            {"packet_id": p["id"], **a} for p in plan["packets"]
            for a in caches[p["id"]]["attempts"] if a["status"] in {"malformed", "failed"}])
        atomic_json(out / "inspection_examples.json", {
            **inspection_examples(plan, reviews, result), "execution_scope": meta["execution_scope"],
            "preview_notice": PREVIEW_NOTICE if preview else None})
        if progress:
            progress({"status": meta["status"], "processed_packets": len(reviews), "planned_packets": len(plan["packets"]),
                      "patterns": len(result["patterns"]), "new_calls": client.calls - start_calls,
                      **({"preview_status": meta["preview_status"], "preview_packets": len(selected)} if preview else {})})

    try:
        atomic_json(out / "packets.json", {"base_fingerprint": base_hash, "packets": plan["packets"]})
        update()  # Revalidate cached proposals before any new call.
        for packet in plan["packets"]:
            cache = caches[packet["id"]]
            if packet["id"] not in selected or cache["review"] is not None:
                continue
            malformed = sum(a.get("status") == "malformed" for a in cache["attempts"])
            terminal = None
            if malformed >= 2:
                reason = "A packet exhausted its single format repair; inspect rejected responses"
            while malformed < 2 and cache["review"] is None:
                system = PROMPT + "\nFrozen base: " + base_hash
                if preview:
                    system += "\n" + PREVIEW_NOTICE
                if malformed:
                    feedback = next(a["error"] for a in cache["attempts"] if a["status"] == "malformed")
                    system += "\nOne format repair: return the complete required schema, at most three proposals. Previous error: " + feedback
                before_trace, before_calls = len(client.trace), client.calls
                started = time.monotonic()
                attempt = {"repair": bool(malformed), "status": "pending"}
                cache["pending_request"] = {"system_fingerprint": stable_id("prompt", system), "repair": bool(malformed)}
                atomic_json(paths[packet["id"]], cache)
                terminal = None
                try:
                    output, request_id = client.json(system, packet, RESPONSE_SCHEMA, "memory_abstraction")
                    attempt["output"] = output
                    _check_schema(output, RESPONSE_SCHEMA)
                    if len(output["proposals"]) > 3:
                        raise ValueError("At most three proposals per packet")
                    cache["review"] = {"packet_id": packet["id"], "request_id": request_id, "output": output}
                    attempt["status"] = "completed"
                except BudgetExceeded:
                    terminal = "New-call budget exhausted; rerun to resume unchanged cached work"
                except ValueError as exc:
                    attempt.update(status="malformed", error=str(exc))
                    malformed += 1
                except (RuntimeError, OSError, KeyboardInterrupt) as exc:
                    attempt.update(status="failed", error_type=type(exc).__name__)
                    terminal = f"{type(exc).__name__}: provider execution interrupted; rerun to resume"
                finally:
                    traces = client.trace[before_trace:]
                    if traces and (client.calls > before_calls or any(t.get("cached") for t in traces)):
                        # Current providers make exactly one transport request per json call.
                        attempt["call"] = copy.deepcopy(traces[-1])
                        attempt["call"].update(packet_id=packet["id"], repair=bool(attempt["repair"]))
                        if attempt["status"] == "malformed":
                            attempt["call"]["judgment_errors"] = [attempt["error"]]
                        run_trace.append(attempt["call"])
                    attempt["elapsed_seconds"] = round(time.monotonic() - started, 4)
                    if attempt["status"] != "pending":
                        cache["attempts"].append(attempt)
                    cache.pop("pending_request", None)
                    atomic_json(paths[packet["id"]], cache)
                    if terminal:
                        reason = terminal
                    elif malformed >= 2:
                        reason = "A packet exhausted its single format repair; inspect rejected responses"
                    update()
                if terminal:
                    break
            if terminal:
                break
        update()
        meta = enriched["abstraction_metadata"]
        atomic_json(out / "recall_comparison.json", {**recall_comparison(base, enriched),
                    "execution_scope": meta["execution_scope"], "preview_notice": PREVIEW_NOTICE if preview else None})
        if preview:
            from .abstraction import validate_enriched
            atomic_json(out / "preview_validation.json", {**validate_enriched(enriched, preview=True),
                        "notice": PREVIEW_NOTICE})
        elif meta["status"] == "complete":
            from .validation import validate_memory
            atomic_json(out / "validation.json", validate_memory(enriched, raise_on_error=True))
            atomic_json(out / "memory.json", enriched)
            (out / "memory.incomplete.json").unlink(missing_ok=True)
        return enriched, plan
    finally:
        client.call_limit = prior_limit
