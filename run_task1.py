"""Build Task 1 artifacts: python run_task1.py [--mode hosted]."""
import argparse
import json
import os
from pathlib import Path

from org_memory import BuildConfig, RecallIndex, build_memory, save_memory, validate_memory
from org_memory.hosted import create_client, default_output_dir, load_env
from org_memory.inspection import inspection_rows, reference_table, sampled_inspection
from org_memory.review import ReviewIncomplete
from org_memory.storage import atomic_json, atomic_text
from org_memory.judge_report import PILOT_RECORDS, judgment_report


DEMO_CUES = [
    "Jobs keep retrying but users see no output",
    "Pruning rules deleted but narratives remain hidden",
    "Data differs between stores",
    "DocDB Elasticsearch incomplete storage and drift",
    "Routine API health checks",
]


def report_progress(event):
    print(json.dumps(event, ensure_ascii=False), flush=True)


def save_build_reports(memory, out, client=None):
    """Persist progress/traces even when no completed memory can be published."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    atomic_json(out / "build_progress.json", memory["build_metadata"])
    atomic_text(out / "build_trace.jsonl", "".join(json.dumps(t, ensure_ascii=False) + "\n" for t in memory["traces"]))
    if client:
        history = memory["build_metadata"].get("hosted_call_history")
        calls = history + [t for t in client.trace if t["purpose"] != "memory_judgment"] if history is not None else client.trace
        atomic_json(out / "hosted_calls.json", calls)
    if memory.get("schema_version") == "3.0":
        atomic_json(out / "judge_inspection.json", judgment_report(memory))


def checkpoint_build(memory, out, client):
    if memory["build_metadata"]["status"] == "incomplete":
        save_memory(memory, Path(out) / "memory.incomplete.json")
    save_build_reports(memory, out, client)


def save_incomplete_build(error, out, client):
    memory = error.memory
    if memory is not None:
        save_memory(memory, Path(out) / "memory.incomplete.json")
        save_build_reports(memory, out, client)
    report_progress({"status": "incomplete", "reason": str(error), "output": str(out),
                     "resume": "Rerun with the same provider/model/cache; validated judgments are reused and only unresolved IDs are requested.",
                     "publication": "No completed memory.json written by this run."})


def main():
    load_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="KEP_2026.json")
    parser.add_argument("--output", default=None)
    parser.add_argument("--mode", choices=["offline", "hosted"], default="offline")
    parser.add_argument("--provider", choices=["compatible", "codex"], default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-calls", type=int, default=int(os.getenv("MEMORY_MAX_CALLS", "200")))
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("MEMORY_REVIEW_BATCH_SIZE", "6")))
    parser.add_argument("--max-pattern-calls", type=int, default=int(os.getenv("MEMORY_MAX_PATTERN_CALLS", "20")))
    parser.add_argument("--max-packet-chars", type=int, default=int(os.getenv("MEMORY_MAX_PACKET_CHARS", "100000")))
    parser.add_argument("--dense", action="store_true", help="Use configured hosted embedding encoder for recall")
    parser.add_argument("--pilot", action="store_true", help="Judge six development cases with full graph context; use --max-calls 4 --batch-size 3")
    args = parser.parse_args()
    if args.dense and args.mode != "hosted":
        parser.error("--dense requires --mode hosted")
    if args.pilot and args.mode != "hosted":
        parser.error("--pilot requires --mode hosted")
    if args.max_calls < 1 or not 1 <= args.batch_size <= 6 or args.max_pattern_calls < 0 or args.max_packet_chars < 1:
        parser.error("Positive call/packet limits, batch size 1..6, and nonnegative pattern limit required")
    try:
        client = create_client(args.provider, model=args.model, max_calls=args.max_calls, dense=args.dense) if args.mode == "hosted" else None
    except ValueError as exc:
        parser.error(str(exc))
    try:
        return run(args, client)
    finally:
        if client is not None:
            client.close()


def run(args, client):
    data = json.loads(Path(args.input).read_text())
    config = BuildConfig(mode=args.mode, llm_max_calls=args.max_calls, llm_batch_size=args.batch_size,
                         llm_max_patterns=args.max_pattern_calls, llm_max_packet_chars=args.max_packet_chars)
    out = Path(args.output) if args.output else default_output_dir(args.mode, client)
    if args.pilot and not args.output:
        out = out / "pilot"
    report_progress({"stage": "indexing", "mode": args.mode})
    try:
        memory = build_memory(data, config, client=client, progress=report_progress,
                              checkpoint=lambda m: checkpoint_build(m, out, client),
                              record_ids=PILOT_RECORDS if args.pilot else ())
    except ReviewIncomplete as exc:
        save_incomplete_build(exc, out, client)
        return 2
    validation = validate_memory(memory, raise_on_error=True)
    save_memory(memory, out / "memory.json")
    save_build_reports(memory, out, client)
    (out / "validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    references = Path(__file__).resolve().parent / "examples/reference_cases.json"
    # Reference cases belong to the supplied assignment graph, not arbitrary inputs.
    if Path(args.input).resolve() == Path(__file__).resolve().parent / "KEP_2026.json":
        for name, rows in [("memory_inspection", inspection_rows(memory)), ("reference_checks", reference_table(memory, references)),
                           ("sampled_inspection", sampled_inspection(memory, references))]:
            (out / f"{name}.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    try:
        index = RecallIndex(memory, data["id2embeddings"], encoder=client if args.dense else None)
        recalls = [index.recall(cue, 6) for cue in DEMO_CUES]
        (out / "recall_examples.json").write_text(json.dumps(recalls, indent=2, ensure_ascii=False) + "\n")
    except (RuntimeError, ValueError, OSError) as exc:
        save_build_reports(memory, out, client)
        report_progress({"status": "memory_complete_recall_incomplete", "reason": type(exc).__name__, "output": str(out)})
        return 3
    save_build_reports(memory, out, client)
    report_progress({"status": "complete", "mode": args.mode, "counts": memory["build_metadata"]["counts"],
                     "validation": validation, "output": str(out)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
