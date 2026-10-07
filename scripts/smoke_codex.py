"""Opt-in live subscription smoke test; at most three SDK review turns.

Uses synthetic source passages, not the assignment graph or a quality benchmark.
"""
# Direct execution needs the project root before importing its package.
# ruff: noqa: E402
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from org_memory import BuildConfig, build_memory, save_memory, validate_memory
from org_memory.hosted import create_client, default_output_dir, load_env
from org_memory.review import ReviewIncomplete
from run_task1 import checkpoint_build, report_progress, save_build_reports, save_incomplete_build


def smoke_graph():
    edges = []
    for decision, record, text in [
        ("incident", "SMOKE-1", "On September 1, 2026, the Atlas API returned errors for 20 minutes. Recovery was not verified."),
        ("runbook", "SMOKE-2", "The Atlas API runbook requires operators to check the health endpoint twice daily. This requirement does not establish that the checks were performed."),
    ]:
        edges.append({"source": {"id": decision, "type": "decision", "label": decision},
                      "target": {"id": "atlas", "type": "resource", "label": "Atlas API"},
                      "relation": {"type": "AFFECTS", "record_id": record,
                                   "provenance": json.dumps({"kind": "extracted", "record_id": record, "source_span": text})}})
    return {"graph": edges, "id2embeddings": {node: [0.0] * 512 for node in ("incident", "runbook", "atlas")}}


def main():
    load_env(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--output")
    args = parser.parse_args()
    config = BuildConfig(mode="hosted", llm_max_calls=3, llm_batch_size=2, llm_max_patterns=0)
    with create_client("codex", model=args.model, max_calls=3) as client:
        out = Path(args.output) if args.output else default_output_dir("hosted", client) / "smoke"
        out.mkdir(parents=True, exist_ok=True)
        # A previous success is historical; the summary always describes this run.
        summary = {"fixture": "synthetic episode and requirement", "model": args.model,
                   "status": "incomplete", "max_new_turns": 3}
        try:
            memory = build_memory(smoke_graph(), config, client=client, progress=report_progress,
                                  checkpoint=lambda m: checkpoint_build(m, out, client))
            validation = validate_memory(memory, raise_on_error=True)
            if not any("incident" in ep["decision_ids"] and ep["retention"] == "retained" for ep in memory["episodes"]):
                raise ValueError("Smoke judgment did not retain the incident")
            if not any(f["kind"] in {"requirement", "documented_routine"}
                       and f["entity_ids"] == ["atlas"] for f in memory["facts"]):
                raise ValueError("Smoke review did not retain the scoped runbook requirement")
            save_memory(memory, out / "memory.json")
            save_build_reports(memory, out, client)
            (out / "validation.json").write_text(json.dumps(validation, indent=2) + "\n")
            before = client.calls
            client.call_limit = 0
            resumed = build_memory(smoke_graph(), config, client=client)
            if client.calls != before or resumed["episodes"] != memory["episodes"] or resumed["facts"] != memory["facts"]:
                raise ValueError("Smoke cache replay did not reproduce the review without new turns")
            summary.update(status="passed", new_turns=before, replay_new_turns=client.calls - before,
                           episodes=len(memory["episodes"]), facts=len(memory["facts"]))
            save_build_reports(resumed, out / "replay", client)
        except ReviewIncomplete as exc:
            save_incomplete_build(exc, out, client)
            summary["reason"] = str(exc)
        except ValueError as exc:
            summary.update(status="failed", reason=str(exc))
        finally:
            (out / "smoke_result.json").write_text(json.dumps(summary, indent=2) + "\n")
        report_progress(summary)
        return 0 if summary["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
