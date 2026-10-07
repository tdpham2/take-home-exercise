"""Audit existing abstraction proposals without changing the source memory."""
import argparse
from dataclasses import replace
import json
from pathlib import Path

from org_memory.abstraction_audit import audit_plan, load_run, run_audit
from org_memory.hosted import create_client, load_env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Completed abstraction output directory")
    parser.add_argument("--output", default="artifacts/abstraction-audit-sol")
    parser.add_argument("--provider", choices=["codex", "compatible"], default="codex")
    parser.add_argument("--model", default="gpt-6.1-sol")
    parser.add_argument("--reasoning-effort", choices=["low", "medium", "high", "xhigh", "max"], default="high")
    parser.add_argument("--max-calls", type=int, default=40, help="Maximum new calls this invocation, including repairs")
    parser.add_argument("--pilot", action="store_true", help="First nonempty packet in every investigation area")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and plan without a provider")
    args = parser.parse_args()
    if args.max_calls < 0:
        parser.error("--max-calls must be nonnegative")
    source, out = Path(args.run).resolve(), Path(args.output).resolve()
    if source == out or source in out.parents or out in source.parents:
        parser.error("--output must be separate from the source run directory")
    if (out / "memory.json").exists():
        parser.error("--output contains a memory run; choose a separate audit directory")
    client = None
    try:
        memory, source_plan = load_run(args.run)
        plan = audit_plan(memory, source_plan)
        if not args.dry_run:
            load_env()
            client = create_client(args.provider, model=args.model, max_calls=args.max_calls)
            client.config = replace(client.config, reasoning_effort=args.reasoning_effort)
        report = run_audit(plan, out, client, max_calls=args.max_calls, pilot=args.pilot,
                           dry_run=args.dry_run, progress=lambda event: print(json.dumps(event), flush=True))
        print(json.dumps({"status": report["status"], "initial_calls": len(plan["tasks"]),
                          "proposals": len(plan["proposals"]), "output": str(out),
                          "incomplete_reason": report.get("incomplete_reason")}))
        return 0 if args.dry_run or report["status"] == "complete" or (args.pilot and report["scope_complete"]) else 2
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
