"""Tables, per-question differences, audit status, and cost without fabricated precision."""
from collections import defaultdict
from pathlib import Path
import csv
import html
import io
import statistics

from org_memory.storage import atomic_json, atomic_text
from .audit import audit_basis
from .common import fingerprint, read_json
from .benchmark import review_basis
from .metrics import score_answer, consistency_metrics, usage_metrics
from .runner import APPROACHES, load_experiment, read_answer


def mean(values):
    values = [v for v in values if v is not None]
    return statistics.mean(values) if values else None


def csv_text(rows):
    if not rows:
        return ""
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def cost_from_trace(trace):
    answer = {"trace": [{"kind": "model", "provider": e} for e in trace],
              "usage": {"model_calls": len(trace)}}
    return usage_metrics(answer)


def build_cost(setup):
    """Use saved provider traces; never infer missing build tokens as zero."""
    base, abstraction = setup.get("memory_build_metadata", {}), setup.get("abstraction_metadata", {})
    base_trace = base.get("hosted_call_history") or base.get("hosted_call_trace")
    # Different builder versions expose different metadata. Show raw summaries too.
    abstract_trace = abstraction.get("call_history", abstraction.get("call_trace", abstraction.get("hosted_call_trace")))
    if not abstraction:
        abstract_trace = []  # Schema 3.0 actually has no abstraction build.
    stages = {}
    for name, trace, metadata in (("memory", base_trace, base), ("abstraction", abstract_trace, abstraction)):
        stages[name] = {"usage": cost_from_trace(trace) if isinstance(trace, list) else None,
                        "reported_summary": metadata.get("cumulative_usage_summary", metadata.get("usage_summary")),
            "elapsed_seconds": metadata.get("cumulative_usage_summary", metadata.get("usage_summary", {})).get(
                "elapsed_provider_seconds", metadata.get("build_elapsed_seconds", metadata.get("elapsed_seconds")))}
    return stages


def report(output):
    output = Path(output)
    manifest, corpus, benchmark = load_experiment(output)
    questions = {q["id"]: q for q in benchmark["questions"]}
    audit_path = output / "audit.json"
    audit = read_json(audit_path) if audit_path.exists() else None
    if audit and (audit["basis_fingerprint"] != audit_basis(output) or audit["fingerprint"] != fingerprint({k: v for k, v in audit.items() if k != "fingerprint"})):
        raise ValueError("Imported audit no longer matches this experiment")
    decisions = {(i["kind"], i["id"]): i for i in audit["items"]} if audit else {}
    rows, details, judgments = [], {}, {}
    for job in manifest["schedule"]:
        rid = job["run_id"]
        ap, jp = output / "runs" / rid / "answer.json", output / "judgments" / f"{rid}.json"
        answer = read_answer(output, rid) if ap.exists() else None
        saved = read_json(jp) if jp.exists() else None
        judgment = saved["result"] if saved and saved.get("status") == "complete" else None
        if ("answer", rid) in decisions:
            judgment = decisions[("answer", rid)]["result"]
        if judgment:
            judgments[rid] = judgment
        metrics = score_answer(questions[job["question_id"]], answer, judgment, corpus) if answer and judgment else None
        if metrics:
            details[rid] = metrics
        cost = metrics["cost"] if metrics else usage_metrics(answer) if answer else {}
        rows.append({"run_id": rid, "question_id": job["question_id"], "approach": job["approach"], "variant": job["variant"],
                     "status": answer["status"] if answer else "not_run", "judged": judgment is not None,
                     "human_audited": ("answer", rid) in decisions,
                     **{k: metrics[k] if metrics else None for k in ("coverage", "groundedness", "specificity", "citation_validity", "internal_contradictions")},
                     **{k: cost.get(k) for k in ("input_tokens", "output_tokens", "model_calls", "tool_calls", "latency_seconds", "cache_replays", "fresh_measurement")}})
    consistency = []
    for job in manifest["schedule"]:
        if job["variant"] == "original":
            continue
        rid = job["run_id"]
        left_id = f"{job['question_id']}__original__{job['approach']}"
        cp = output / "consistency" / f"{rid}.json"
        if not cp.exists() or rid not in judgments or left_id not in judgments:
            continue
        saved = read_json(cp)
        if saved.get("status") != "complete":
            continue
        result = decisions.get(("consistency", rid), {}).get("result", saved["result"])
        consistency.append({"question_id": job["question_id"], "approach": job["approach"], "comparison": job["variant"],
                            **consistency_metrics(judgments[left_id], judgments[rid], result)})
    aggregates, paired = [], []
    metric_names = ("coverage", "groundedness", "specificity", "input_tokens", "output_tokens", "model_calls", "tool_calls", "latency_seconds")
    for arm in APPROACHES:
        selected = [r for r in rows if r["approach"] == arm]
        # Average variants within each question first; six questions remain six units.
        per_question = defaultdict(list)
        for r in selected:
            per_question[r["question_id"]].append(r)
        cost_metrics = {"input_tokens", "output_tokens", "model_calls", "tool_calls", "latency_seconds"}
        values = {m: [mean([r[m] for r in group if m not in cost_metrics or r["fresh_measurement"]])
                      for group in per_question.values()] for m in metric_names}
        aggregates.append({"approach": arm, "questions": len(per_question), "scheduled_runs": len(selected),
                           "finished_runs": sum(r["status"] != "not_run" for r in selected),
                           "failed_runs": sum(r["status"] == "failed" for r in selected),
                           "judged_runs": sum(r["judged"] for r in selected),
                           "fresh_cost_runs": sum(r["fresh_measurement"] is True for r in selected),
                           "answers_with_grounding_score": sum(r["groundedness"] is not None for r in selected),
                           **{m: mean(v) for m, v in values.items()}})
    for qid in dict.fromkeys(r["question_id"] for r in rows):
        for comparator in ("text_rag", "graph_only"):
            arms = {arm: [r for r in rows if r["question_id"] == qid and r["approach"] == arm]
                    for arm in (comparator, "memory_graph")}
            for metric in metric_names:
                a, b = [mean([r[metric] for r in arms[arm] if metric not in cost_metrics or r["fresh_measurement"]])
                        for arm in ("memory_graph", comparator)]
                paired.append({"question_id": qid, "comparison": f"memory_graph - {comparator}", "metric": metric,
                               "difference": a - b if a is not None and b is not None else None})
    setup = read_json(output / "setup.json")
    construction = build_cost(setup)
    stages = [s["usage"] for s in construction.values()]
    build_tokens = (sum(s["input_tokens"] + s["output_tokens"] for s in stages)
                    if all(s and s["input_tokens"] is not None and s["output_tokens"] is not None for s in stages) else None)
    full = next(a for a in aggregates if a["approach"] == "memory_graph")
    per_query = (full["input_tokens"] + full["output_tokens"]
                 if full["input_tokens"] is not None and full["output_tokens"] is not None else None)
    amortized = [{"questions": n, "tokens_per_question": build_tokens / n + per_query
                  if build_tokens is not None and per_query is not None else None} for n in (10, 100, 1000)]
    overhead = {}
    for name in ("answer", "judge"):
        p = output / f"{name}_calls.json"
        if p.exists():
            overhead[name] = cost_from_trace([a.get("provider", {}) for a in read_json(p)["attempts"]])
    all_judged = all(r["judged"] for r in rows)
    expected_pairs = 36 if manifest["split"] == "final" else 0
    complete = all_judged and len(consistency) == expected_pairs
    result = {"status": "audited" if complete and audit else "automated_only" if complete else "incomplete",
              "synthetic": manifest["synthetic_provider"], "manifest_fingerprint": manifest["fingerprint"],
              "benchmark_review_basis": review_basis(benchmark["review"]),
              "rows": rows, "aggregates": aggregates, "paired_differences": paired, "consistency": consistency,
              "details": details, "construction_cost": construction, "amortization": amortized,
              "stage_usage": overhead, "setup_seconds": setup["index_and_validation_seconds"] + setup.get("approach_index_seconds", 0),
              "answers_reused_from": manifest.get("answers_reused_from"),
              "audit": {k: v for k, v in audit.items() if k != "items"} if audit else None,
              "limitations": ["Six known-corpus final questions; development overlap is disclosed per question.",
                 "Means ignore undefined values; inspect per-run missingness and completion counts before interpreting them.",
                 "Consistency measures stability, not correctness. Identical wrong answers can agree.",
                 "Missing construction or provider usage remains unknown; dollars are not inferred from subscription access.",
                 "Comparisons are against BM25 text RAG and the configured graph-only agent, not all possible retrieval systems.",
                 "Synthetic-provider reports verify plumbing only and do not establish model quality."]}
    if result["benchmark_review_basis"] == "user_assumption":
        result["limitations"].insert(0, "Reference criteria were accepted by explicit user assumption; no human source review is attested.")
    report_dir = output / "report"
    atomic_json(report_dir / "report.json", result)
    atomic_text(report_dir / "runs.csv", csv_text(rows))
    atomic_text(report_dir / "paired_differences.csv", csv_text(paired))
    atomic_text(report_dir / "consistency.csv", csv_text(consistency))
    def table(data):
        if not data:
            return "<p>No measurements yet.</p>"
        keys = list(data[0])
        def val(v):
            return "unknown" if v is None else f"{v:.3f}" if isinstance(v, float) else str(v)
        return "<table><tr>" + "".join(f"<th>{html.escape(k)}</th>" for k in keys) + "</tr>" + "".join(
            "<tr>" + "".join(f"<td>{html.escape(val(row[k]))}</td>" for k in keys) + "</tr>" for row in data) + "</table>"
    sections = [f"<h1>Organizational memory evaluation</h1><p>Status: {result['status']}. Synthetic: {result['synthetic']}. "
                f"Reference basis: {result['benchmark_review_basis']}.</p>",
                '<p><img src="quality.png" alt="Quality comparison" style="max-width:100%"><img src="cost.png" alt="Online cost comparison" style="max-width:100%"></p>',
                "<h2>Question-level means</h2>", table(aggregates), "<h2>Individual measurements</h2>", table(rows),
                "<h2>Repeat and paraphrase consistency</h2>", table(consistency)]
    for q in benchmark["questions"]:
        if q["split"] != manifest["split"]:
            continue
        sections.append(f"<h2>{html.escape(q['text'])}</h2><p>{html.escape(q['exposure'])}</p>")
        for arm in APPROACHES:
            ap = output / "runs" / f"{q['id']}__original__{arm}" / "answer.json"
            if ap.exists():
                from org_agent.models import AnswerResult
                answer = AnswerResult.model_validate(read_json(ap))
                sections.append(f"<h3>{arm}</h3><pre>{html.escape(answer.markdown())}</pre>")
    sections.append("<h2>Interpretation limits</h2><ul>" + "".join(f"<li>{html.escape(s)}</li>" for s in result["limitations"]) + "</ul>")
    atomic_text(report_dir / "report.html", "<!doctype html><meta charset='utf-8'><title>Evaluation report</title>"
                "<style>body{font:15px system-ui;max-width:1500px;margin:40px auto;padding:20px}table{border-collapse:collapse;display:block;overflow:auto}td,th{padding:8px;border:1px solid #ddd;text-align:left}pre{white-space:pre-wrap;background:#f6f7f8;padding:16px}th{background:#eef2f6}</style>" + "".join(sections))
    render_charts(result, report_dir)
    return result


def render_charts(result, output):
    """Static, exportable figures; no undefined values are silently plotted as zero."""
    import os
    import tempfile
    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "org-eval-matplotlib"))
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    output = Path(output)
    rows = result["aggregates"]
    labels = [r["approach"].replace("_", " ") for r in rows]
    colors = ["#65758b", "#147d92", "#a0583d"]
    prefix = "SYNTHETIC PIPELINE CHECK — " if result["synthetic"] else ""
    for name, metrics in (("quality", [("coverage", "Coverage", 1), ("groundedness", "Groundedness", 1),
                                        ("specificity", "Specificity", 4)]),
                           ("cost", [("input_tokens", "Input tokens", None), ("tool_calls", "Tool calls", None),
                                     ("latency_seconds", "Answer latency (s)", None)])):
        fig = Figure(figsize=(11, 4.2), layout="constrained")
        FigureCanvasAgg(fig)
        axes = fig.subplots(1, 3)
        for ax, (key, title, ymax) in zip(axes, metrics):
            for i, row in enumerate(rows):
                if row[key] is not None:
                    ax.bar(i, row[key], color=colors[i])
                else:
                    ax.text(i, .05, "unknown", ha="center", transform=ax.get_xaxis_transform(), rotation=90)
            ax.set_xticks(range(3), labels, rotation=20, ha="right", fontsize=8)
            ax.set_title(title, fontsize=11)
            ax.set_ylim(bottom=0, top=ymax)
            ax.spines[["top", "right"]].set_visible(False)
        fig.suptitle(prefix + ("Quality by approach" if name == "quality" else "Online cost by approach"), fontsize=12)
        fig.supxlabel("Means across questions; repetitions averaged within each question. " + result["status"], fontsize=9)
        fig.savefig(output / f"{name}.png", dpi=150)
