"""Reproducible development inspection, never an invented semantic accuracy score."""
PILOT_RECORDS = ("KEP-6373", "KEP-6782", "KEP-7049", "KEP-6672", "KEP-6644", "KEP-6661")
CASE_NOTES = {
    "KEP-6373": "Epic association/headings alone should not justify prominent memory.",
    "KEP-6782": "Design heading and epic linkage are not durable technical facts by themselves.",
    "KEP-7049": "Resolve/re-run instructions are prescriptions, not evidence that fixes passed.",
    "KEP-6672": "'Successfully' adding an unconfigured hashtag describes a restriction defect, not a beneficial fix.",
    "KEP-6644": "Inspect the reported product crashes; ensure a supported useful incident is not suppressed.",
    "KEP-6661": "BrightData migration intent is mixed with current Serp limitations; Done does not establish migration success.",
}


def judgment_report(memory):
    meta = memory["build_metadata"]
    cov = meta["coverage"]
    usage = meta["usage_summary"]
    cumulative = meta["cumulative_usage_summary"]
    by_candidate = {j["id"]: j for j in memory["episode_judgments"]}
    by_fact = {j["id"]: j for j in memory["fact_judgments"]}
    by_outcome = {j["id"]: j for j in memory["outcome_judgments"]}
    cases = []
    for record, note in CASE_NOTES.items():
        refs = {eid for eid, e in memory["evidence"].items() if e["record_id"] == record}
        if not refs:
            continue
        cases.append({
            "record_id": record, "development_inspection_note": note,
            "evidence": [{"id": eid, "text": memory["evidence"][eid]["source_span"],
                          "source_id": memory["evidence"][eid]["source_id"], "target_id": memory["evidence"][eid]["target_id"],
                          "relation": memory["evidence"][eid]["relation"], "provenance": memory["evidence"][eid]["provenance"]}
                         for eid in sorted(refs)],
            "candidate_judgments": [{"candidate": c, "judgment": by_candidate.get(c["id"])}
                                    for c in memory["candidates"] if refs & set(c["evidence_ids"])],
            "fact_judgments": [{"proposal": p, "judgment": by_fact.get(p["id"])}
                               for p in memory["proposals"]["fact_judgments"] if refs & set(p["evidence_ids"])],
            "outcome_judgments": [by_outcome[eid] for eid in sorted(refs) if eid in by_outcome],
        })
    reviewed = cov["reviewed_packets"]
    return {"scope": meta["scope"], "status": meta["status"], "usage_this_run": usage, "usage_across_resumes": cumulative,
            "coverage": cov, "retention_and_selection": meta["counts"],
            "selection_rates": {
                "rejected_episode_fraction": len(memory["archived_candidates"]) / len(memory["episode_judgments"])
                    if memory["episode_judgments"] else None,
                "rejected_fact_fraction": len(memory["archived_facts"]) / len(memory["fact_judgments"])
                    if memory["fact_judgments"] else None,
                "limitation": "Selection/rejection rates measure decisions, not correctness."},
            "accuracy": {"measured": False, "score": None,
                         "reason": "Requires independent inspection of support, boundaries, scope and value; schema validity is not accuracy."},
            "planning_estimate": {
                "nominal_full_graph_batches_at_six_candidates": (cov["eligible_candidates"] + 5) // 6,
                "full_graph_provider_seconds_at_observed_rate":
                    cumulative["elapsed_provider_seconds"] / reviewed * cov["eligible_candidates"] if reviewed else None,
                "limitation": "Rough linear extrapolation from reviewed packets, including corrections. Selected cases are not representative; packet splitting, cache, failures and local I/O change elapsed time."},
            "cases": cases}
