"""Discover question-focused abstractions from a completed, frozen hosted memory."""
import argparse
from dataclasses import replace
import json
from pathlib import Path

from org_memory.abstraction_run import load_preview_memory, pilot_packets, run_abstraction
from org_memory.hosted import create_client, load_env


def checked_memory_path(value):
    if not value.strip():
        raise ValueError("--memory is empty. Set ABSTRACTION_BASE in this shell or pass the memory.json path directly.")
    path = Path(value)
    if path.is_dir():
        raise ValueError(f"--memory requires a JSON file; received a directory: {path}")
    if not path.is_file():
        detail = "Supply the completed full-graph hosted memory.json."
        try:
            progress = json.loads((path.parent / "build_progress.json").read_text())
            coverage = progress.get("coverage", {})
            detail = (f"Base build status: {progress.get('status', 'unknown')}; reviewed candidates "
                      f"{coverage.get('reviewed_candidates', '?')}/{coverage.get('selected_candidates', '?')}. "
                      "Run abstraction after the base build has written memory.json.")
        except (OSError, ValueError, AttributeError):
            pass
        raise ValueError(f"Memory file does not exist: {path}. {detail}")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory", required=True)
    parser.add_argument("--questions", default=str(Path(__file__).parent / "config/abstraction_questions.json"))
    parser.add_argument("--output", default=None)
    parser.add_argument("--provider", choices=["codex", "compatible"], default="codex")
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--pilot", action="store_true", help="One packet from each of the first three areas in the full frozen plan")
    parser.add_argument("--preview", action="store_true", help="Freeze an in-progress full-graph checkpoint and test up to three packets provisionally")
    parser.add_argument("--max-calls", type=int, default=None, help="Maximum new calls including repair (default: 40; preview: 6)")
    args = parser.parse_args()
    args.output = args.output or ("artifacts/abstraction-preview" if args.preview else "artifacts/abstraction")
    args.max_calls = args.max_calls if args.max_calls is not None else (6 if args.preview else 40)
    if args.max_calls < 0:
        parser.error("--max-calls must be nonnegative")
    try:
        if args.preview:
            base = load_preview_memory(args.memory, args.output)
            memory_path = Path(args.memory)
        else:
            memory_path = checked_memory_path(args.memory)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    if memory_path.resolve().parent == Path(args.output).resolve():
        parser.error("--output must differ from the base memory directory")
    client = None
    try:
        if not args.preview:
            base = json.loads(memory_path.read_text())
        questions = json.loads(Path(args.questions).read_text())
        # Validate before opening a provider, including for --dry-run.
        from org_memory.abstraction import require_base
        require_base(base, preview=args.preview)
        if not args.dry_run:
            load_env()
            client = create_client(args.provider, model=args.model, max_calls=args.max_calls)
            client.config = replace(client.config, reasoning_effort="medium")
        memory, plan = run_abstraction(base, questions, args.output, client, max_calls=args.max_calls,
                                      pilot=args.pilot, dry_run=args.dry_run, preview=args.preview,
                                      progress=lambda event: print(json.dumps(event), flush=True))
        status = "dry_run" if memory is None else memory["abstraction_metadata"]["status"]
        print(json.dumps({"status": status, "initial_calls": len(plan["packets"]),
                          "selected_initial_calls": len(pilot_packets(plan)) if args.preview or args.pilot else len(plan["packets"]),
                          "execution_scope": "preview" if args.preview else ("pilot" if args.pilot else "production"),
                          "oversized_bundles": len(plan["oversized_bundles"]), "output": args.output,
                          **({"preview_status": memory["abstraction_metadata"]["preview_status"]} if status == "preview" else {})}))
        success = status in {"dry_run", "complete"} or (status == "preview" and memory["abstraction_metadata"]["preview_status"] == "complete")
        return 0 if success else 2
    except (ValueError, OSError, KeyError) as exc:
        parser.error(str(exc))
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
