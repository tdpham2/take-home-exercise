"""Build a synthetic fixture offline, then optionally exercise the live Task 2 adapter.

No production artifacts are read or rebuilt. --live permits at most six model calls.
Fixture judgments are scripted and are not evidence of extraction/model accuracy.
"""
# Direct script execution adds the project root.
# ruff: noqa: E402
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from org_agent import AgentConfig, OrganizationalAgent, save_result
from org_memory import BuildConfig, build_memory
from org_memory.hosted import CompatibleClient, ProviderConfig, load_env
from org_memory.storage import atomic_json
from scripts.smoke_codex import smoke_graph


def make_fixture(output):
    """Use the real Task 1 builder with explicitly synthetic judgments, no hosted calls."""
    def transport(endpoint, payload):
        task = json.loads(payload["messages"][1]["content"])["task"]
        excerpts = {row["id"]: row["text"] for row in task["excerpts"]}
        response = {
            "episode_judgments": [{"id": cid, "supported": True, "worth_remembering": True,
                                   "reason": "Synthetic fixture grouping."} for cid in task["requested_ids"]["episode_judgments"]],
            "fact_judgments": [{"id": row["id"], "is_fact": True,
                                "kind": "documented_routine" if "runbook" in excerpts[row["excerpt_id"]] else "historical_statement",
                                "reason": "Synthetic fixture classification."} for row in task["fact_proposals"]],
            "outcome_judgments": [],
        }
        return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(response)}}]}

    graph_path, memory_path = output / "graph.json", output / "memory.json"
    data = smoke_graph()
    with CompatibleClient(ProviderConfig(api_key="synthetic", cache_dir=str(output / "fixture-cache")), transport=transport) as client:
        memory = build_memory(data, BuildConfig(mode="hosted"), client=client)
    atomic_json(graph_path, data)
    atomic_json(memory_path, memory)
    return graph_path, memory_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Run one bounded Codex integration smoke; otherwise only create/validate the fixture")
    parser.add_argument("--output", default="artifacts/task2/smoke")
    parser.add_argument("--timeout", type=float, default=90)
    args = parser.parse_args(argv)
    output = Path(args.output)
    gp, mp = make_fixture(output / "fixture")
    agent = OrganizationalAgent.from_artifacts(gp, mp, AgentConfig(
        max_model_calls=6, max_tool_calls=4, timeout=args.timeout, cache_dir=str(output / "cache")))
    summary = {"fixture": "synthetic source records and scripted Task 1 judgments", "live_requested": args.live,
               "status": "fixture_validated", "max_model_calls": 6}
    if args.live:
        load_env(ROOT / ".env")
        result = agent.answer("For this integration check, recall Atlas API memory, inspect useful items, and check their original graph evidence. "
                              "What incident was reported, was recovery verified, and were the routine checks actually reported as performed? "
                              "Cite the records and distinguish requirements from execution.",
                              trace_path=output / "answer" / "trace.jsonl")
        save_result(result, output / "answer")
        summary.update(status=result.status, claims=len(result.claims), usage=result.usage, stop_reason=result.stop_reason,
                       checked_memory_and_graph=any(c.source_mode == "memory_confirmed_by_graph" for c in result.claims),
                       limitation="One integration smoke, not a semantic evaluation or performance comparison.")
    atomic_json(output / "smoke_result.json", summary)
    print(json.dumps(summary, indent=2))
    return 0 if summary["status"] in {"fixture_validated", "complete"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
