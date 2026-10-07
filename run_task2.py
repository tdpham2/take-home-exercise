"""Answer one engineering-history question; provisional inputs require explicit --preview."""
import argparse
import json
from pathlib import Path

from org_memory.hosted import load_env


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", default="KEP_2026.json")
    parser.add_argument("--memory", required=True)
    parser.add_argument("--question")
    parser.add_argument("--preview", action="store_true", help="Explicitly test a finished provisional abstraction preview")
    parser.add_argument("--validate-only", action="store_true", help="Validate input and build tool indexes without any model calls")
    parser.add_argument("--output", default="artifacts/task2/latest")
    parser.add_argument("--provider", choices=["codex", "compatible"], default="codex")
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--reasoning-effort", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--max-model-calls", type=int, default=12)
    parser.add_argument("--max-tool-calls", type=int, default=10)
    parser.add_argument("--max-request-chars", type=int, default=200_000,
                        help="Serialized application-input character cap (default: 200000; not tokens)")
    parser.add_argument("--cache-dir", default="artifacts/cache-task2")
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args(argv)
    if not args.validate_only and not args.question:
        parser.error("--question is required unless --validate-only is used")
    try:
        from org_agent import AgentConfig, OrganizationalAgent, save_result
        config = AgentConfig(provider=args.provider, model=args.model, reasoning_effort=args.reasoning_effort,
                             max_model_calls=args.max_model_calls, max_tool_calls=args.max_tool_calls,
                             max_request_chars=args.max_request_chars, cache_dir=args.cache_dir, timeout=args.timeout)
        agent = OrganizationalAgent.from_artifacts(args.graph, args.memory, config, preview=args.preview)
        if args.validate_only:
            print(json.dumps({"status": "validated", **agent.artifacts.identity,
                              "counts": {k: len(agent.artifacts.memory[k]) for k in
                                         ("episodes", "facts", "patterns", "outcome_assessments")},
                              "model_calls": 0}, indent=2))
            return 0
        load_env()
        result = agent.answer(args.question, trace_path=Path(args.output) / "trace.jsonl")
        save_result(result, args.output)
        print(result.markdown())
        print(json.dumps({"status": result.status, "provisional": result.provisional, "output": args.output, "usage": result.usage}))
        return {"complete": 0, "partial": 2, "failed": 3}[result.status]
    except ImportError as exc:
        parser.error(f"Agent dependency unavailable ({exc.name}); install requirements.txt")
    except (ValueError, OSError, KeyError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
