import copy
import json
from pathlib import Path

import pytest

from org_memory import BuildConfig, RecallIndex, build_memory, index_graph, validate_memory
from org_memory.evidence import date_mentions
from org_memory.patterns import independent_support
from org_memory.recall import entity_timeline


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def data():
    return json.loads((ROOT / "KEP_2026.json").read_text())


@pytest.fixture(scope="module")
def memory(data):
    return build_memory(data)


def record_edges(memory, record):
    return [e for e in memory["evidence"].values() if e["record_id"] == record]


def episode_for(memory, record, decision=None):
    return next(e for e in memory["episodes"] if record in e["record_ids"] and
                (decision is None or decision in e["decision_ids"]))


def test_graph_counts_and_all_original_evidence(memory):
    assert len(memory["nodes"]) == 3098
    assert len(memory["evidence"]) == 4051
    assert validate_memory(memory)["passed"]


def test_build_does_not_mutate_input(data):
    original = copy.deepcopy(data)
    build_memory(data)
    assert data == original


def test_frozen_build_is_reproducible(data, memory):
    assert build_memory(data) == memory


def test_parallel_edges_and_provenance_survive(data):
    changed = copy.deepcopy(data)
    parallel = copy.deepcopy(changed["graph"][0])
    parallel["relation"]["type"] = "AFFECTS"
    changed["graph"].append(parallel)
    index = index_graph(changed)
    assert len(index["evidence"]) == 4052
    matches = [e for e in index["evidence"].values() if e["source_id"] == parallel["source"]["id"]
               and e["target_id"] == parallel["target"]["id"]]
    assert {e["relation"] for e in matches} >= {"REFERENCES", "AFFECTS"}


def test_duplicate_edges_do_not_inflate_evidence(data):
    changed = {**data, "graph": data["graph"] + [data["graph"][0]]}
    index = index_graph(changed)
    assert len(index["evidence"]) == 4051
    assert any(len(e["raw_positions"]) == 2 for e in index["evidence"].values())


def test_argonaut_is_not_attributed_to_timeout_increase(memory):
    edges = record_edges(memory, "KEP-6969")
    assert len(edges) == 7
    harmful = next(e for e in edges if e["relation"] == "PRODUCES")
    assert "causal_attribution_requires_review" in harmful["quality_flags"]
    ep = episode_for(memory, "KEP-6969")
    assert any("recovery is unverified" in u for u in ep["uncertainties"])
    assert ep["outcomes"][0]["valence"] == "harmful"
    assert ep["outcomes"][0]["signed_impact"] == -3
    assert ep["outcomes"][0]["causal_attribution"].startswith("unverified")
    assert any("our alarms caught it but no action was taken" in c["text"] for c in ep["claims"])


def test_planned_backfill_not_promoted_to_recovery(memory):
    e = next(e for e in record_edges(memory, "KEP-6970") if e["target_id"] == "outcome_99bbc87c")
    assert e["status"] == "intended"
    assert "intended_outcome_is_not_observed" in e["quality_flags"]
    outcomes = [o for ep in memory["episodes"] for o in ep["outcomes"] if o["outcome_node_id"] == "outcome_99bbc87c"]
    assert outcomes and all(o["signed_impact"] is None and o["valence"] == "unknown" for o in outcomes)


def test_done_is_administrative(memory):
    outcomes = [o for ep in memory["episodes"] for o in ep["outcomes"] if o["evidence_status"] == "administrative"]
    assert len(outcomes) >= 569
    assert all(o["valence"] == "unknown" and o["signed_impact"] is None for o in outcomes)


def test_retests_do_not_prove_supersession_or_independent_incidents(memory):
    for record in ["KEP-5480", "KEP-5737"]:
        e = next(e for e in record_edges(memory, record) if e["relation"] == "SUPERSEDES_DECISION")
        assert "retest_does_not_establish_supersession" in e["quality_flags"]
        assert e["status"] == "verification_request"
    pruning = next(p for p in memory["patterns"] if p["title"].startswith("Pruning state"))
    assert not {"KEP-5480", "KEP-5737"} & set(pruning["record_ids"])


def test_specifications_are_not_observations(memory):
    upstream = next(t for t in memory["traces"] if t.get("hypothesis") == "Upstream success without downstream completion")
    assert upstream["decision"] == "reject_insufficient_independent_support"
    assert upstream["independent_count"] == 1
    assert all(e["status"] != "source_report" for e in record_edges(memory, "KEP-6958")
               if e["source_span"].startswith(("Design", "Define")))


def test_documented_routine_does_not_claim_repeated_execution(memory):
    ep = episode_for(memory, "KT-267")
    assert ep["kind"] == "documented_routine"
    assert {"KT-267", "KT-334", "KT-292"} <= set(ep["record_ids"])
    f = next(f for f in memory["facts"] if f["statement"] == "Frequency: Twice Daily (Morning and Evening)")
    assert f["kind"] == "documented_routine"
    assert any("consistent execution" in s for s in f["uncertainties"])


def test_pattern_independence_rejects_duplicate_episode(memory):
    ep = episode_for(memory, "KEP-6969")
    refs = [e for e in ep["evidence_ids"] if memory["evidence"][e]["status"] == "source_report"]
    copied = {**ep, "id": "copied_episode"}
    selected, rejected = independent_support(memory, [(ep, refs), (copied, refs)])
    assert len(selected) == 1 and len(rejected) == 1


def test_two_independent_incidents_support_processing_pattern(memory):
    p = next(p for p in memory["patterns"] if p["title"].startswith("Processing failures"))
    assert p["independent_support_count"] == 2
    assert p["confidence"] == "low"
    assert p["record_ids"] == ["KEP-6969", "KEP-6970"]


def test_patterns_do_not_match_accounts_as_counts_or_network_builder_as_cross_network(memory):
    p = next(p for p in memory["patterns"] if p["title"].startswith("Different views"))
    assert not {"KEP-5834", "KEP-6467", "KEP-6922", "KEP-5668", "KEP-4271"} & set(p["record_ids"])
    p = next(p for p in memory["patterns"] if p["title"].startswith("State crosses"))
    assert "KEP-6990" not in p["record_ids"]


def test_requirements_remain_requirements(memory):
    facts = [f for f in memory["facts"] if "KEP-5757" in f["record_ids"]]
    assert facts and all(f["kind"] == "requirement" for f in facts)
    notify = next(f for f in memory["facts"] if f["statement"].startswith("Notify the QA"))
    assert notify["kind"] == "requirement"


def test_dates_do_not_invent_years_or_recovery(memory):
    assert date_mentions("Apr 19–29", "ev_test", "source_report")[0]["date"] is None
    assert date_mentions("April 19, 2026", "ev_test", "source_report")[0]["date"] == "2026-04-19"
    assert date_mentions("2026-02-30", "ev_test", "source_report") == []
    inferred = date_mentions("2026-03-12", "ev_test", "inferred")[0]
    assert inferred["status"] == "tentative_inference"
    t = entity_timeline(memory, "resource_a0bea208")
    assert t["unplaced"]
    assert all(x["status"] == "explicit_date_mention" for x in t["dated_mentions"])


def test_family_aliases_keep_environments_and_ids(memory):
    aliases = [a for a in memory["entity_aliases"] if a["family"] == "DocumentDB"]
    assert {"development", "staging", "unspecified"} <= {a["environment"] for a in aliases}
    assert all(a["identity_merge"] is False for a in aliases)
    assert len({a["node_id"] for a in aliases}) == len(aliases)


def test_faded_items_keep_evidence_but_leave_default_recall(memory):
    compressed = [e for e in memory["episodes"] if e["retention"] == "compressed"]
    index = RecallIndex(memory)
    assert compressed and all(e["evidence_ids"] for e in compressed)
    assert not {e["id"] for e in compressed} & set(index.by_id)


def test_partial_cue_and_association_are_explainable(memory, data):
    index = RecallIndex(memory, data["id2embeddings"])
    result = index.recall("Jobs keep retrying but users see no output", 6)
    assert "KEP-6969" in result["results"][0]["record_ids"]
    pattern = next(r for r in result["results"] if r["title"].startswith("Processing failures"))
    assert pattern["association"] and len(pattern["association"]["path"]) <= 3
    assert result["trace"]["anchor_nodes"]
    assert "not direct semantic query encoding" in result["trace"]["mode"]
    assert index.recall("qzxvplmnbasdf", 4)["results"] == []
    with pytest.raises(ValueError):
        index.recall("", 4)


def test_dangling_citations_are_rejected(memory):
    changed = copy.deepcopy(memory)
    changed["facts"][0]["claims"][0]["evidence_ids"] = ["made_up"]
    assert not validate_memory(changed)["passed"]


def test_hosted_mode_does_not_silently_fall_back(data):
    with pytest.raises(ValueError, match="requires a configured client"):
        build_memory(data, BuildConfig(mode="hosted"))


def test_offline_accepts_unannotated_index_without_mutation(data, memory):
    supplied = index_graph(data, annotate_offline=False)
    original = copy.deepcopy(supplied)
    assert build_memory(data, index=supplied) == memory
    assert supplied == original
