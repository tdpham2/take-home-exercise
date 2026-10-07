"""Contract and control-flow tests. Synthetic verdicts do not measure LLM accuracy."""
import copy
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from org_memory import BuildConfig, RecallIndex, build_memory, get_item, validate_memory
from org_memory.evidence import index_graph
from org_memory.hosted import CompatibleClient, ProviderConfig
from org_memory.judged import prepare
from org_memory.review import ReviewIncomplete, administrative, make_packet, validate_judgments
from test_candidates import edge, graph


def response_for(task):
    # No semantic claims: deliberately explicit synthetic choices.
    return {
        "episode_judgments": [{"id": cid, "supported": True, "worth_remembering": True, "reason": "Fixture: coherent useful event."}
                              for cid in task["requested_ids"]["episode_judgments"]],
        "fact_judgments": [{"id": p["id"], "is_fact": False, "kind": "not_a_fact",
                           "reason": "Fixture: no selected durable fact."} for p in task["fact_proposals"]],
        "outcome_judgments": [{"id": p["id"], "observed": False, "valence": "unknown", "impact": "unknown",
                              "reason": "Fixture: no observed result selected."} for p in task["outcome_proposals"]],
    }


def client_for(path, responder=response_for):
    def transport(endpoint, payload):
        task = json.loads(payload["messages"][1]["content"])["task"]
        return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(responder(task))}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 5}}
    return CompatibleClient(ProviderConfig(api_key="fixture", cache_dir=str(path)), transport=transport)


def build(data, path, responder=response_for, **kwargs):
    return build_memory(data, BuildConfig(mode="hosted", **kwargs), client=client_for(path, responder))


def accept_facts(task, kind="requirement"):
    out = response_for(task)
    for f in out["fact_judgments"]:
        f.update(is_fact=True, kind=kind, reason="Fixture: useful scoped source statement.")
    return out


def test_fixed_grouping_raw_archive_recall_and_no_semantic_rules(tmp_path):
    data = graph([edge(text="The service failed."), edge("d2", "r2", record="R2")])
    supplied = index_graph(data)
    original = copy.deepcopy(supplied)
    with patch("org_memory.evidence.classify_evidence", side_effect=AssertionError), patch("org_memory.evidence.quality_flags", side_effect=AssertionError):
        m = build_memory(data, BuildConfig(mode="hosted"), client=client_for(tmp_path), index=supplied)
    assert supplied == original
    assert m["schema_version"] == "3.0" and m["build_metadata"]["judging_contract"] == "judge-v1"
    assert validate_memory(m)["passed"] and len(m["episodes"]) == 2
    assert not m["patterns"] and "review_units" not in m
    assert [e["raw_edge"] for e in m["evidence"].values()] == data["graph"]
    assert {c["status"] for ep in m["episodes"] for c in ep["claims"]} == {"source_excerpt"}
    result = RecallIndex(m).recall("service failed")["results"][0]
    assert get_item(m, result["item_id"])["evidence"]


def test_retain_compress_reject_and_fact_independent_of_episode(tmp_path):
    data = graph([edge("d1", text="The service failed."), edge("d2", record="R2", text="Operators must inspect the queue."),
                  edge("d3", record="R3", text="Minor housekeeping happened.")])
    def respond(task):
        out = accept_facts(task)
        by_id = {c["id"]: c["decision_ids"][0] for c in task["candidates"]}
        for j in out["episode_judgments"]:
            d = by_id[j["id"]]
            j.update(supported=d != "d2", worth_remembering=d == "d1")
        return out
    m = build(data, tmp_path, respond)
    assert len(m["episodes"]) == 2 and len(m["archived_candidates"]) == 1 and len(m["facts"]) == 3
    compressed = next(e for e in m["episodes"] if e["retention"] == "compressed")
    assert compressed["claims"] and get_item(m, compressed["id"])["evidence"]
    assert compressed["id"] not in RecallIndex(m).by_id
    assert compressed["id"] in RecallIndex(m, include_compressed=True).by_id
    assert any("R2" in f["record_ids"] for f in m["facts"])


def test_exact_whole_excerpts_deduplicated_by_subject_with_all_provenance(tmp_path):
    text = "The API requires a signed request."
    data = graph([edge(target="r1", text=text), edge("d2", target="r1", record="R2", text=text),
                  edge("d3", target="r2", record="R3", text=text)])
    m = build(data, tmp_path, accept_facts, llm_batch_size=1)
    assert len(m["proposals"]["fact_judgments"]) == len(m["facts"]) == 2
    assert {tuple(f["entity_ids"]) for f in m["facts"]} == {("r1",), ("r2",)}
    shared = next(f for f in m["facts"] if f["entity_ids"] == ["r1"])
    assert len(shared["evidence_ids"]) == len(shared["claims"][0]["anchors"]) == 2
    assert shared["statement"] == text and shared["kind"] == "requirement"
    judged_ids = [r["id"] for review in m["reviews"] for r in review["output"]["fact_judgments"]]
    assert len(judged_ids) == len(set(judged_ids)) == 2
    owners = [j["id"] for j in m["judge_jobs"] if shared["proposal_id"] in j["fact_ids"]]
    containing = [c["id"] for c in m["candidates"] if set(c["evidence_ids"]) & set(shared["evidence_ids"])]
    assert owners == [min(containing)]


@pytest.mark.parametrize("kind", ["historical_statement", "documented_routine", "requirement"])
def test_fact_types_are_not_episodes_or_current_truth(tmp_path, kind):
    m = build(graph([edge(text="The API uses a five minute timeout.")]), tmp_path, lambda t: accept_facts(t, kind))
    assert m["facts"][0]["kind"] == kind
    assert "current state" in m["facts"][0]["uncertainties"][0]


def test_mixed_passage_rejected_whole_and_inferred_context_never_proposed(tmp_path):
    text = "The job failed. We might move it tomorrow."
    m = build(graph([edge(text=text), edge(kind="inferred", text="The job was fixed.")]), tmp_path)
    assert not m["facts"] and len(m["archived_facts"]) == 1
    assert m["proposals"]["fact_judgments"][0]["text"] == text
    assert all("inferred" != m["evidence"][eid]["provenance"]["kind"]
               for p in m["proposals"]["fact_judgments"] for eid in p["evidence_ids"])
    assert m["episodes"][0]["inferred_link_ids"]


@pytest.mark.parametrize("text", ["status: Done", "resolution: Done | status: Done", "epic_link_key: KEP-6373", "parent_key: KEP-6216", "is_root: true"])
def test_exact_admin_fields_cannot_become_facts_or_success(tmp_path, text):
    assert administrative(text)
    def respond(task):
        out = response_for(task)
        assert not task["fact_proposals"] and not task["outcome_proposals"]
        for j in out["episode_judgments"]:
            j["worth_remembering"] = False
        return out
    m = build(graph([edge(target="o", target_type="outcome", relation="PRODUCES", text=text)]), tmp_path, respond)
    assert not m["facts"] and m["episodes"][0]["retention"] == "compressed"
    assert m["outcome_assessments"][0]["valence"] == "unknown"
    assert m["outcome_assessments"][0]["signed_impact"] is None


@pytest.mark.parametrize("text", ["status: Done. The API now rejects unsigned requests.",
                                  "epic_link_key: KEP-6373\nThe service crashed.",
                                  "Marking this as done. Merged to staging.", "Design: useful technical constraint"])
def test_admin_guard_does_not_discard_mixed_prose(tmp_path, text):
    assert not administrative(text)
    m = build(graph([edge(text=text)]), tmp_path)
    assert len(m["reviews"][0]["output"]["fact_judgments"]) == 1
    assert m["episodes"][0]["claims"][0]["text"] == text


def test_empty_and_inferred_only_candidates_are_archived(tmp_path):
    def respond(task):
        out = response_for(task)
        for j in out["episode_judgments"]:
            j.update(supported=False, worth_remembering=False)
        return out
    m = build(graph([edge(text=""), edge("d2", kind="inferred", record="R2")]), tmp_path, respond)
    assert not m["episodes"] and not m["facts"]
    assert len(m["archived_candidates"]) == 1
    assert len(m["build_metadata"]["coverage"]["ineligible_candidates"]) == 1
    assert validate_memory(m)["passed"]


def test_outcome_semantics_no_keyword_valence_and_ordinal_impact(tmp_path):
    text = "The user successfully added a forbidden hashtag despite the configured restriction."
    def respond(task):
        out = response_for(task)
        for j in out["outcome_judgments"]:
            j.update(observed=True, valence="harmful", impact="local", reason="Restriction bypass reported.")
        return out
    m = build(graph([edge(target="o", target_type="outcome", relation="PRODUCES", text=text)]), tmp_path, respond)
    outcome = m["outcome_assessments"][0]
    assert outcome["signed_impact"] == -1 and outcome["anchors"][0]["quote"] == text
    assert outcome["observed"] and "causality" in outcome["causal_attribution"]


@pytest.mark.parametrize("failure", ["missing", "duplicate", "boolean", "extra_quote", "inconsistent_kind", "unobserved"])
def test_partial_acceptance_retries_only_invalid_rows(tmp_path, failure):
    tasks = []
    data = graph([edge(), edge("d2", target="o", target_type="outcome", relation="PRODUCES", record="R2")])
    def respond(task):
        tasks.append(copy.deepcopy(task))
        out = response_for(task)
        if "validation_feedback" not in task:
            if failure == "missing":
                out["episode_judgments"].pop()
            elif failure == "duplicate":
                out["episode_judgments"].append(copy.deepcopy(out["episode_judgments"][0]))
            elif failure == "boolean":
                out["episode_judgments"][0]["supported"] = 1
            elif failure == "extra_quote":
                out["fact_judgments"][0]["quote"] = "invented"
            elif failure == "inconsistent_kind":
                out["fact_judgments"][0]["kind"] = "requirement"
            else:
                out["outcome_judgments"][0]["valence"] = "beneficial"
        return out
    snapshots = []
    m = build_memory(data, BuildConfig(mode="hosted"), client=client_for(tmp_path, respond),
                     checkpoint=lambda m: snapshots.append(copy.deepcopy(m)))
    assert len(tasks) == 2 and sum(map(len, tasks[1]["requested_ids"].values())) == 1
    assert len(m["episodes"]) == 2 and validate_memory(m)["passed"]
    assert len(snapshots) >= 3 and snapshots[1]["reviews"]
    assert m["build_metadata"]["usage_summary"]["reported_new_call_tokens"]["input_tokens"] == 40
    assert m["build_metadata"]["usage_summary"]["calls_with_rejected_judgments"] == 1


def test_failed_correction_can_resume_without_replaying_poisoned_cache(tmp_path):
    cfg = BuildConfig(mode="hosted")
    invalid = client_for(tmp_path, lambda _: {"invalid": "response"})
    with pytest.raises(ReviewIncomplete) as error:
        build_memory(graph([edge()]), cfg, client=invalid)
    assert invalid.calls == 2 and not error.value.memory["reviews"]
    m = build_memory(graph([edge()]), cfg, client=client_for(tmp_path))
    assert m["build_metadata"]["hosted_calls"] == 1 and validate_memory(m)["passed"]
    replay = client_for(tmp_path, lambda _: pytest.fail("Validated resume must not call transport"))
    replay.call_limit = 0
    again = build_memory(graph([edge()]), cfg, client=replay)
    assert replay.calls == 0 and again["episodes"] == m["episodes"]
    assert len(again["traces"]) >= 2


def test_budget_preserves_rows_and_resume_only_unresolved(tmp_path):
    data = graph([edge(), edge("d2", record="R2", text="Another incident.")])
    cfg = BuildConfig(mode="hosted", llm_max_calls=1, llm_batch_size=1)
    with pytest.raises(ReviewIncomplete) as error:
        build_memory(data, cfg, client=client_for(tmp_path))
    assert len(error.value.memory["episodes"]) == 1
    assert error.value.memory["build_metadata"]["status"] == "incomplete"
    m = build_memory(data, cfg, client=client_for(tmp_path))
    assert len(m["episodes"]) == 2 and m["build_metadata"]["hosted_calls"] == 1


def test_oversized_batch_splits_without_truncating_and_singleton_fails(tmp_path):
    data = graph([edge(text="x" * 600), edge("d2", "r2", record="R2", text="y" * 600)])
    index = index_graph(data, False)
    c, p, jobs, _ = prepare(index)
    limit = max(len(json.dumps({**make_packet(index, [j], c, p), "attempt": 0}, ensure_ascii=False)) for j in jobs) + 3
    m = build(data, tmp_path, llm_max_packet_chars=limit)
    assert m["build_metadata"]["hosted_calls"] == 2
    assert all(len(ep["claims"][0]["text"]) == 600 for ep in m["episodes"])
    with pytest.raises(ReviewIncomplete, match="No evidence was truncated"):
        build(data, tmp_path / "small", llm_max_packet_chars=10)


def test_interrupt_and_network_failure_checkpoint_prior_acceptance(tmp_path):
    for failure in (KeyboardInterrupt, TimeoutError):
        calls = []
        def respond(task):
            calls.append(task)
            if len(calls) > 1:
                raise failure()
            return response_for(task)
        snapshots = []
        with pytest.raises(ReviewIncomplete) as error:
            build_memory(graph([edge(), edge("d2", record="R2")]), BuildConfig(mode="hosted", llm_batch_size=1),
                         client=client_for(tmp_path / failure.__name__, respond),
                         checkpoint=lambda m: snapshots.append(copy.deepcopy(m)))
        assert len(error.value.memory["episodes"]) == 1
        assert snapshots[-1]["build_metadata"]["status"] == "incomplete"


def test_raw_final_judgment_and_scope_tampering_detected(tmp_path):
    m = build(graph([edge()]), tmp_path, accept_facts)
    for mutate in (
        lambda x: x["episodes"][0].update(claims=[]),
        lambda x: x["facts"][0].update(entity_ids=["invented"]),
        lambda x: x["proposals"]["fact_judgments"][0].update(text="changed"),
        lambda x: x["reviews"].append(copy.deepcopy(x["reviews"][0])),
        lambda x: next(iter(x["evidence"].values())).update(status="source_report"),
        lambda x: x["build_metadata"]["coverage"].update(reviewed_candidates=999),
    ):
        changed = copy.deepcopy(m)
        mutate(changed)
        assert not validate_memory(changed)["passed"]


def test_orphan_extracted_evidence_gets_fact_judgment_without_episode(tmp_path):
    m = build(graph([edge(source="r0", source_type="resource", text="The API requires TLS.")]), tmp_path, accept_facts)
    assert not m["episodes"] and len(m["facts"]) == 1 and validate_memory(m)["passed"]


def test_full_graph_coverage_without_semantic_model_calls(tmp_path):
    data = json.loads((Path(__file__).resolve().parents[1] / "KEP_2026.json").read_text())
    def respond(task):
        out = response_for(task)
        for j in out["episode_judgments"]:
            j.update(supported=False, worth_remembering=False, reason="Synthetic rejection, not a quality evaluation.")
        return out
    with patch("org_memory.evidence.classify_evidence", side_effect=AssertionError):
        m = build(data, tmp_path, respond)
    c = m["build_metadata"]["coverage"]
    assert (c["total_candidates"], c["eligible_candidates"], c["reviewed_candidates"]) == (825, 816, 816)
    assert c["fact_proposals"] == 2911 and not any(c["unreviewed_ids"].values())
    assert len(m["evidence"]) == 4051 and len(m["nodes"]) == 3098
    assert validate_memory(m)["passed"]
    assert not m["episodes"] and not m["facts"] and not m["patterns"]


def test_pilot_preserves_complete_graph_and_marks_partial_scope(tmp_path):
    data = graph([edge(), edge("d2", record="R2", text="Separate event.")])
    m = build_memory(data, BuildConfig(mode="hosted"), client=client_for(tmp_path), record_ids=["R1"])
    assert len(m["evidence"]) == 2 and len(m["episodes"]) == 1
    assert m["build_metadata"]["scope"] == "pilot" and validate_memory(m)["passed"]


def test_batch_size_changes_reuse_judgments_and_preserve_call_accounting(tmp_path):
    data = graph([edge(), edge("d2", record="R2", text="Another event.")])
    cfg = BuildConfig(mode="hosted", llm_max_calls=1, llm_batch_size=1)
    with pytest.raises(ReviewIncomplete):
        build_memory(data, cfg, client=client_for(tmp_path))
    m = build_memory(data, replace(cfg, llm_batch_size=6), client=client_for(tmp_path))
    meta = m["build_metadata"]
    assert meta["hosted_calls"] == 1 and len(meta["hosted_call_history"]) == 2
    assert meta["cumulative_usage_summary"]["reported_new_call_tokens"]["input_tokens"] == 40
    assert meta["usage_summary"]["reported_new_call_tokens"]["input_tokens"] == 20
    cache = next((tmp_path / "judge-v1").glob("judgments_*.json"))
    state = json.loads(cache.read_text())
    state["reviews"][0]["output"]["episode_judgments"][0]["supported"] = "corrupted"
    cache.write_text(json.dumps(state))
    client = client_for(tmp_path, lambda _: pytest.fail("Corrupt accepted cache must fail before transport"))
    with pytest.raises(ReviewIncomplete):
        build_memory(data, cfg, client=client)
    assert client.calls == 0


def test_real_data_pilot_cli_inspection_and_no_fabricated_accuracy(tmp_path, monkeypatch):
    import run_task1
    from org_memory.judge_report import PILOT_RECORDS
    # Semantic choices are deliberately supplied by a fixture, not a model-quality test.
    def respond(task):
        out = response_for(task)
        candidates = {c["id"]: c for c in task["candidates"]}
        for j in out["episode_judgments"]:
            if set(candidates[j["id"]]["record_ids"]) & {"KEP-6373", "KEP-6782"}:
                j["worth_remembering"] = False
        return out
    monkeypatch.setattr(run_task1, "create_client", lambda *a, **kw: client_for(tmp_path / "cache", respond))
    out = tmp_path / "out"
    source = Path(__file__).resolve().parents[1] / "KEP_2026.json"
    monkeypatch.setattr("sys.argv", ["run_task1.py", "--mode", "hosted", "--pilot",
                                    "--input", str(source), "--output", str(out), "--max-calls", "4", "--batch-size", "3"])
    assert run_task1.main() == 0
    report = json.loads((out / "judge_inspection.json").read_text())
    assert report["scope"] == "pilot" and not report["accuracy"]["measured"] and report["accuracy"]["score"] is None
    assert {c["record_id"] for c in report["cases"]} == set(PILOT_RECORDS)
    assert len(json.loads((out / "hosted_calls.json").read_text())) == 2
    assert json.loads((out / "validation.json").read_text())["passed"]
    assert all("source_excerpt" not in r["actual_statuses"] for r in json.loads((out / "sampled_inspection.json").read_text()))
    sast = next(c for c in report["cases"] if c["record_id"] == "KEP-7049")
    assert any(p["proposal"]["text"] == "Re-run SAST pipelines to confirm fixes" for p in sast["fact_judgments"])
    brightdata = next(c for c in report["cases"] if c["record_id"] == "KEP-6661")
    assert any("currently using the serp" in p["proposal"]["text"] and "migration" in p["proposal"]["text"] for p in brightdata["fact_judgments"])
    assert all(not j["observed"] for j in brightdata["outcome_judgments"])
    # Pure linkage is archived as a non-fact; headings are still judged.
    admin = next(c for c in report["cases"] if c["record_id"] == "KEP-6782")
    assert any(j["proposal"]["text"].startswith("epic_link_key:") and j["judgment"]["method"] == "exact_administrative_guard"
               for j in admin["fact_judgments"])


def test_cli_incomplete_writes_checkpoint_and_progress(tmp_path, monkeypatch):
    import run_task1
    source, out = tmp_path / "input.json", tmp_path / "out"
    source.write_text(json.dumps(graph([edge(), edge("d2", record="R2", text="Other incident.")])))
    monkeypatch.setattr(run_task1, "create_client", lambda *a, **kw: client_for(tmp_path / "cache"))
    monkeypatch.setattr("sys.argv", ["run_task1.py", "--mode", "hosted", "--input", str(source), "--output", str(out),
                                    "--max-calls", "1", "--batch-size", "1"])
    assert run_task1.main() == 2 and not (out / "memory.json").exists()
    assert (out / "memory.incomplete.json").exists() and (out / "hosted_calls.json").exists()
    assert json.loads((out / "build_progress.json").read_text())["status"] == "incomplete"
    from org_memory import save_memory
    with pytest.raises(ValueError, match="checkpoint"):
        save_memory(json.loads((out / "memory.incomplete.json").read_text()), out / "memory.json")


def test_in_process_notebook_enforces_timeout():
    import signal
    import subprocess
    import sys
    if not hasattr(signal, 'setitimer'):
        pytest.skip('POSIX timers required for in-process execution')
    # Isolate the IPython kernel lifecycle from pytest's own process.
    script = '''
from scripts.execute_notebook import in_process
nb = {"metadata": {}, "cells": [{"cell_type": "code", "source": "import time; time.sleep(5)"}]}
try:
    in_process(nb, cell_timeout=1)
except RuntimeError as error:
    assert "TimeoutError" in str(error), str(error)
else:
    raise AssertionError("deadline was not enforced")
'''
    result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr


def test_standard_notebook_method_receives_configurable_timeout(tmp_path, monkeypatch):
    import scripts.execute_notebook as runner
    notebook = {'nbformat': 4, 'nbformat_minor': 5, 'metadata': {}, 'cells': []}
    (tmp_path / 'task1_memory.ipynb').write_text(json.dumps(notebook))
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr('sys.argv', ['execute_notebook.py', '--cell-timeout', '17'])
    monkeypatch.chdir(tmp_path)
    with patch('nbclient.NotebookClient') as client:
        runner.main()
    assert client.call_args.kwargs['timeout'] == 17
    client.return_value.execute.assert_called_once()
    assert json.loads((tmp_path / 'task1_memory.ipynb').read_text())['metadata']['task1_execution']['cell_timeout_seconds'] == 17
