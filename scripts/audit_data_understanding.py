"""Read-only audit of data-understanding examples; never calls a model.

Run from the repository root:
    python scripts/audit_data_understanding.py

Writes a separate report, leaving all memory outputs and provider caches untouched.
The interpretations are development inspection notes, not independent gold labels.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from org_memory.build import build_aliases
from org_memory.candidates import build_candidates
from org_memory.evidence import index_graph, normalize
from org_memory.review import administrative, make_proposals
from org_memory.storage import atomic_json


CASES = [
    {
        "id": "provenance_is_not_truth",
        "finding": "An inferred cross-record explanation is not a source excerpt.",
        "evidence_ids": ["ev_5bae6c7471a558ea"],
        "interpretation": "The linking pass relates backfill to a hotfix using shared initiative and hierarchy signals. Its rationale, including dates and quoted-looking text, is not a separately identified source record.",
        "implemented_response": "Inferred links are context only: no candidate joins, standalone facts or observed outcomes are derived from them.",
        "limitation": "Useful associations can remain outside fixed episode boundaries; inferred context can still influence the judge.",
    },
    {
        "id": "likely_duplicate_api",
        "finding": "Two resource IDs normalize to the same API name.",
        "evidence_ids": ["ev_772db264a54b7b34", "ev_9e36bd97f8c61197"],
        "interpretation": "Narrative accounts API and Narrative-accounts API are plausible duplicate identities, not independently confirmed to be the same endpoint/version.",
        "implemented_response": "Preserve both IDs and their record scopes; shared resources never merge episodes.",
        "limitation": "No general entity resolution or alias for this API is implemented, so shared-entity recall can fragment.",
    },
    {
        "id": "same_family_different_environment",
        "finding": "DocDB terminology overlaps across explicitly different environments.",
        "evidence_ids": ["ev_91f7d0f41e78cd1a", "ev_dbf2559333195d81"],
        "interpretation": "Development and staging cluster upgrades should not be treated as one deployed configuration.",
        "implemented_response": "DocumentDB terminology metadata records separate node IDs and development/staging environments with identity_merge=false.",
        "limitation": "Alias metadata is not wired into recall and does not resolve generic DocDB versus DocumentDB identities.",
    },
    {
        "id": "routine_documentation_is_not_execution",
        "finding": "Repeated KT passages prescribe monitoring, while an outcome label asserts execution.",
        "evidence_ids": ["ev_b7d02e50dd8e299e", "ev_d891ec727c04c897", "ev_72bcaf2a50c998b3", "ev_738c1cf46a0f036a"],
        "interpretation": "Frequency and instructions support a documented routine, not observed runs. Done/Done alone does not support the label Vendor API runs executed with test results logged.",
        "implemented_response": "Whole-excerpt facts distinguish prescriptions from historical statements; exact text/subject duplicates share judgment. The closure-only outcome is deterministically unobserved/unknown.",
        "limitation": "KT is not hard-coded as a source class, and a shared decision node cannot prove independent occurrences or actual compliance.",
    },
    {
        "id": "community_summary_conflicts_with_test",
        "finding": "A source labeled extracted contains cross-record synthesis and overstates recovery.",
        "evidence_ids": ["ev_78a40f71d667b59d", "ev_907c29b234390e7e", "ev_fa632ce9d7630c2e", "ev_92143bb5cd43292d"],
        "interpretation": "Community_1355 calls KEP-6672 confirmation of a fix, but that ticket reports no restriction or validation and states a validation requirement. The excerpt does not establish deployed recovery.",
        "implemented_response": "Outcome judgments require observed results in their own passage; graph labels do not establish success. The saved batch-1 pilot marks the closure/version outcome unobserved/unknown.",
        "limitation": "There is no source-reliability hierarchy: this extracted Community DEPENDS_ON edge actually joins the two decisions before review. The judge cannot undo that merge.",
    },
    {
        "id": "retest_is_not_supersession",
        "finding": "Extracted SUPERSEDES_DECISION relations overstate retest titles.",
        "evidence_ids": ["ev_a32b77a8b393b409", "ev_c603df7dbfb1d1d3"],
        "interpretation": "A retest request does not establish that the earlier decision was replaced or that its defect was resolved.",
        "implemented_response": "SUPERSEDES_DECISION is not a grouping rule and does not automatically erase older memory. Offline quality flags identify this concern.",
        "limitation": "The original edge remains archived; hosted indexing deliberately bypasses the offline flags, so no general semantic edge repair is performed.",
    },
]


def source_family(record_id):
    if record_id.startswith("Community_"):
        return "Community"
    return record_id.split("-")[0] if "-" in record_id else "other"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "KEP_2026.json")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/data_understanding/audit.json")
    args = parser.parse_args()
    index = index_graph(json.loads(args.input.read_text()), annotate_offline=False)
    candidates, _, traces = build_candidates(index, include_review_units=False)
    labels = defaultdict(list)
    for node in index["nodes"].values():
        labels[(node["type"], normalize(node["label"]))].append(node["id"])
    collisions = [
        {"node_type": kind, "normalized_label": label, "node_ids": sorted(ids)}
        for (kind, label), ids in sorted(labels.items()) if len(ids) > 1
    ]
    cases = []
    for definition in CASES:
        ids = definition["evidence_ids"]
        evidence = [index["evidence"][eid] for eid in ids]
        nodes = sorted({n for e in evidence for n in (e["source_id"], e["target_id"])})
        cases.append({
            **definition,
            "node_ids": nodes,
            "record_ids": sorted({e["record_id"] for e in evidence if e["record_id"]}),
            "nodes": [index["nodes"][n] for n in nodes],
            "evidence": evidence,
            "grouping_links": [t for t in traces if set(t["evidence_ids"]) & set(ids)],
            "administrative_guard": {
                e["id"]: administrative(e["source_span"] or "")
                for e in evidence if e["provenance"]["kind"] == "extracted"
            },
        })
    frequency = next(
        p for p in make_proposals(index)["fact_judgments"]
        if p["text"] == "Frequency: Twice Daily (Morning and Evening)"
        and p["subject_id"] == "rule_281d3f33"
    )
    report = {
        "input": str(args.input),
        "graph_hash": index["graph_hash"],
        "review_scope": "Development inspection of supplied graph excerpts, not original complete records, independent human labels, or external operational verification.",
        "summary": {
            "nodes": len(index["nodes"]),
            "edges": index["raw_edge_count"],
            "provenance_counts": dict(Counter(e["provenance"]["kind"] for e in index["evidence"].values())),
            "record_family_counts": dict(sorted(Counter(source_family(r) for r in index["by_record"]).items())),
            "edge_family_counts": dict(sorted(Counter(source_family(e["record_id"]) for e in index["evidence"].values() if e["record_id"]).items())),
            "normalized_label_collision_groups": len(collisions),
            "candidate_count": len(candidates),
            "eligible_candidates": sum(c["eligible"] for c in candidates),
        },
        "label_collision_method": "Group by node type and case-folded label after replacing punctuation with spaces and collapsing whitespace. A collision proposes review; it does not establish entity identity or count all duplicates.",
        "label_collisions": collisions,
        "cases": cases,
        "repeated_frequency_proposal": frequency,
        "environment_alias_examples": [
            a for a in build_aliases(index)
            if a["node_id"] in {"resource_85d8e84e", "resource_7947dd8e"}
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(args.output, report)
    print(json.dumps(report["summary"], indent=2))
    print(f"Resolved all references for {len(cases)} cases. Report: {args.output}")


if __name__ == "__main__":
    main()
