"""Generate an unexecuted offline or hosted walkthrough; never starts a model call."""
import argparse
import json
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[1]


def notebook(mode):
    cells = []

    def md(source):
        cells.append({"cell_type": "markdown", "metadata": {}, "source": textwrap.dedent(source).strip() + "\n"})

    def code(source):
        source = textwrap.dedent(source).strip() + "\n"
        compile(source, "notebook cell", "exec")
        cells.append({"cell_type": "code", "metadata": {}, "source": source, "execution_count": None, "outputs": []})

    md(f"""
    # Task 1 — {"Hosted fixed-proposal judgments" if mode == "hosted" else "Offline extractive baseline"}

    Focus: (1) episodes, (2) durable facts and outcome valuation, (5) fading.
    Hosted schema 3.0 / judge-v1 keeps deterministic boundaries and asks for small
    judgments. Code constructs quotations, IDs, scope and provenance. Patterns
    are deferred in hosted mode; offline rules and declared patterns are unchanged.
    The existing recall interface supports both. Task 2 remains separate work.

    This notebook is unexecuted. Generating it makes no model calls. The delivered
    executed baseline is in task1_offline.ipynb.
    """)
    md("""
    ## Configuration

    Install requirements.txt in the shared project environment. Hosted Codex also
    needs a local ChatGPT Codex login. Keep credentials in your environment/.env.
    Hosted execution below defaults to the six-case pilot, at most four new turns
    and three candidates per batch. Set PILOT=False and MAX_CALLS=200 for the full graph.
    Outputs use a judge-v1 directory, preserving earlier hosted artifacts.
    """)
    code(f"""
    import json
    import os
    from pathlib import Path
    import pandas as pd
    from org_memory import BuildConfig, RecallIndex, build_memory, get_item, index_graph, save_memory, validate_memory
    from org_memory.hosted import create_client, default_output_dir, load_env
    from org_memory.judged import prepare
    from org_memory.judge_report import PILOT_RECORDS, judgment_report
    from org_memory.review import ReviewIncomplete, make_packet
    from run_task1 import checkpoint_build, report_progress, save_build_reports, save_incomplete_build

    load_env()
    MODE = {mode!r}
    PROVIDER = os.getenv("MEMORY_PROVIDER") or "codex"
    MODEL = os.getenv("MEMORY_MODEL") or ("gpt-5.6-luna" if PROVIDER == "codex" else None)
    PILOT = MODE == "hosted"
    MAX_CALLS = 4 if PILOT else 200
    BATCH_SIZE = 3 if PILOT else 6
    config = BuildConfig(mode=MODE, llm_max_calls=MAX_CALLS, llm_batch_size=BATCH_SIZE, llm_max_patterns=0)
    data = json.loads(Path("KEP_2026.json").read_text())
    index = index_graph(data, annotate_offline=MODE == "offline")
    print({{"mode": MODE, "pilot": PILOT, "records": len(index["by_record"]), "edges": index["raw_edge_count"]}})
    """)
    md("""
    ## Fixed proposals

    Start at each decision and collect all incoming/outgoing evidence across records.
    Join nonempty extracted DEPENDS_ON/CAUSES links between decisions and decisions
    sharing an event within a record. Cap groups at eight; skip events connecting
    more than eight decisions. Shared resources and inferred links never join groups.
    A candidate is eligible if it has an extracted edge.

    The full graph has 825 candidates / 816 eligible. Fixed grouping bounds cost:
    six candidates per batch gives 136 initial requests before packet splitting or
    corrections. A global decision can conflate events and one incident can span
    groups. Rejected boundaries remain archived; the judge does not repair them.

    Fact proposals are exact whole excerpts scoped to the edge target, deduplicated
    by (text, target) with every reference retained. Mixed passages can be rejected,
    even when a smaller useful fact exists inside; this is an explicit recall trade-off.
    """)
    code("""
    candidates, proposals, jobs, _ = prepare(index, config.max_episode_decisions, PILOT_RECORDS if PILOT else ())
    assert len(candidates) == 825 and sum(c["eligible"] for c in candidates) == 816
    print({"selected_packets": len(jobs), "whole_excerpt_fact_proposals": len(proposals["fact_judgments"]),
           "outcome_proposals": len(proposals["outcome_judgments"])})
    packet = make_packet(index, jobs[:1], candidates, proposals)
    display(pd.DataFrame(packet["fact_proposals"]))
    display(pd.DataFrame(packet["excerpts"])[["id", "text", "provenance_kind"]])
    """)
    md("""
    ## Build and checkpoint

    Executing the next cell in hosted mode makes live calls up to MAX_CALLS.
    The judge returns support/value for episodes, fact acceptance/type, and
    observed/valence/impact for outcomes, each with a short reason.
    Valid rows survive a partially invalid response. Only unresolved IDs receive
    one correction; oversized packets split without truncating evidence.
    Rerunning revalidates and reuses accepted verdicts. Rejected transport
    responses remain auditable but do not prevent a fresh unresolved request.
    """)
    code("""
    client = create_client(PROVIDER, model=MODEL, max_calls=MAX_CALLS) if MODE == "hosted" else None
    out = default_output_dir(MODE, client)
    if PILOT:
        out = out / "pilot"
    try:
        memory = build_memory(data, config, client=client, index=index, progress=report_progress,
                              checkpoint=lambda m: checkpoint_build(m, out, client),
                              record_ids=PILOT_RECORDS if PILOT else ())
        validation = validate_memory(memory, raise_on_error=True)
        save_memory(memory, out / "memory.json")
        save_build_reports(memory, out, client)
    except ReviewIncomplete as exc:
        save_incomplete_build(exc, out, client)
        raise
    finally:
        if client is not None:
            client.close()
    print(validation)
    print(memory["build_metadata"]["counts"])
    """)
    md("""
    ## Accuracy, time and token inspection

    Structural validation establishes fidelity and consistency, not semantic accuracy.
    Inspect the source alongside the verdict: support, usefulness, grouping, subject
    scope, prescription versus history, and whether an outcome was actually reported.
    Development case notes are not independent gold labels. No accuracy percentage
    is computed automatically.

    Call logs include elapsed seconds and reported input/output tokens for each call.
    Summary statistics distinguish this run from cumulative usage across resumes.
    Failed calls may omit token usage. Subscription dollar costs remain unknown.
    """)
    code("""
    if MODE == "hosted":
        report = judgment_report(memory)
        display(pd.DataFrame(memory["build_metadata"]["hosted_call_history"]))
        print(json.dumps(report["usage_across_resumes"], indent=2))
        print(json.dumps(report["planning_estimate"], indent=2))
        for case in report["cases"]:
            print(case["record_id"], case["development_inspection_note"])
            display(pd.DataFrame(case["fact_judgments"]))
        print("Full evidence and verdicts:", out / "judge_inspection.json")
    else:
        from org_memory.inspection import reference_table
        display(pd.DataFrame(reference_table(memory, "examples/reference_cases.json")))
    """)
    md("""
    ## Fading and recall

    Supported, valuable groups are retained. Supported low-value groups are compressed
    and excluded from default recall, while keeping all excerpts. Unsupported groups
    are archived with reasons. Facts are judged independently, so a useful fact can
    survive a rejected group. Exact administrative fields cannot become facts or
    successful outcomes; mixed prose is not removed by substring matching.
    Nothing deletes the raw archive. Lower prominence can reduce recall; opt into
    compressed items or inspect the archive when needed.
    """)
    code("""
    retriever = RecallIndex(memory, data["id2embeddings"])
    result = retriever.recall("Product crashes while sharing the screen in Chrome", limit=6)
    display(pd.DataFrame(result["results"]))
    if result["results"]:
        display(get_item(memory, result["results"][0]["item_id"]))
    display(pd.DataFrame([{"id": e["id"], "title": e["title"], "retention": e["retention"],
                          "reason": e["retention_reason"]} for e in memory["episodes"]]))
    """)
    md("""
    ## Limits and next step

    Episode claims are uninterpreted source_excerpt text; accepting a group does not
    verify each excerpt or graph label. Historical facts are not necessarily current.
    Requirements/routines do not establish execution. Outcome scores use an ordinal
    sign × impact scope (1 local, 2 service, 3 customer); unknown/mixed values remain
    unscored, and PRODUCES does not prove causality.

    Finish semantic inspection of the pilot before deciding whether to run all hosted.
    Patterns can then synthesize accepted episodes/facts with independent support.
    They are deferred here, not claimed complete. A pilot marked complete covers only
    its selected packets, not the full graph. Existing recall has not been redesigned
    or evaluated on unseen cues by this change.
    """)
    for i, cell in enumerate(cells):
        cell["id"] = f"{mode}-{i:03d}"
    return {"nbformat": 4, "nbformat_minor": 5,
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                         "language_info": {"name": "python", "version": "3.12"}}, "cells": cells}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["offline", "hosted"], default="offline")
    parser.add_argument("--output")
    args = parser.parse_args()
    path = Path(args.output) if args.output else ROOT / ("task1_hosted.ipynb" if args.mode == "hosted" else "task1_memory.ipynb")
    nb = notebook(args.mode)
    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
    print(f"Created {path.name} with {len(nb['cells'])} cells; no cells executed.")


if __name__ == "__main__":
    main()
