"""Synthetic contract/control-flow tests; no model accuracy claims or hosted calls."""
import copy
import json
from dataclasses import replace

import pytest

from org_memory import RecallIndex, validate_memory
from org_memory.abstraction import (base_view, construct_proposal, evidence_bundles, fingerprint,
                                    make_plan, materialize, require_base, serialized)
from org_memory.abstraction_run import run_abstraction
from org_memory.hosted import CompatibleClient, ProviderConfig
from test_candidates import edge, graph
from test_review import accept_facts, build

QUESTIONS = [{"id": "reliability", "question": "What varies between the service reports?", "cues": ["service"]}]


def memory(tmp_path, n=3, responder=accept_facts, edges=None):
    return build(graph(edges or [edge(f"d{i}", f"r{i}", record=f"R{i}", text=f"The service failed in zone {i}.")
                                 for i in range(n)]), tmp_path / "base", responder)


def historical(task):
    return accept_facts(task, "historical_statement")


def proposal(packet, kind="hypothesized_mechanism", basis="uncertain"):
    # Fixtures intentionally test only citations/shape, not natural-language truth.
    return {"statement": "The service reports suggest a shared failure mode.", "kind": kind,
            "support": [{"passage_id": p["id"], "basis": basis} for p in packet["passages"][:2]],
            "comparison_insight": "The reports concern different zones.",
            "differences_counterevidence": "Different zones; no successful case appears in this packet.",
            "counterevidence_ids": [], "uncertainty": "Mechanism unverified.", "usefulness": "Compare recovery behavior."}


def synthesis_client(tmp_path, responder=None, max_calls=40):
    def transport(endpoint, payload):
        packet = json.loads(payload["messages"][1]["content"])["task"]
        result = responder(packet) if responder else {"proposals": [proposal(packet)]}
        return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(result)}}],
                "usage": {"prompt_tokens": 80, "completion_tokens": 20}}
    return CompatibleClient(ProviderConfig(api_key="fixture", cache_dir=str(tmp_path / "synthesis"),
                                            model="gpt-5.6-luna", reasoning_effort="medium", max_calls=max_calls), transport=transport)


def test_full_completed_base_required(tmp_path):
    m = memory(tmp_path)
    require_base(m)
    for key, value in [("status", "incomplete"), ("scope", "pilot")]:
        bad = copy.deepcopy(m)
        bad["build_metadata"][key] = value
        with pytest.raises(ValueError, match="completed full_graph"):
            require_base(bad)


def test_passages_dedup_preserve_refs_exclude_only_exact_admin(tmp_path):
    edges = [edge("d1", record="R1", text="The service failed."),
             edge("d2", record="R2", text="The service failed."),
             edge("d3", record="R3", text="status: Done"),
             edge("d4", record="R4", text="status: Done. The service recovered."),
             edge("d1", kind="inferred", text="UNVERIFIED INFERRED SECRET LABEL")]
    def respond(task):
        result = accept_facts(task)
        by_id = {c["id"]: c for c in task["candidates"]}
        for row in result["episode_judgments"]:
            if by_id[row["id"]]["decision_ids"] == ["d3"]:
                row["worth_remembering"] = False
        return result
    m = memory(tmp_path, edges=edges, responder=respond)
    bundles, passages, excluded = evidence_bundles(m)
    p = next(p for p in passages.values() if p["text"] == "The service failed.")
    assert len(p["evidence_ids"]) == 2 and set(p["record_ids"]) == {"R1", "R2"}
    assert excluded["exact_administrative"] == 1 and excluded["inferred"] == 1
    assert any(p["text"].startswith("status: Done.") for p in passages.values())
    plan = make_plan(m, QUESTIONS)
    assert "UNVERIFIED" not in serialized(plan["packets"])
    assert "decision_ids" not in serialized(plan["packets"])
    assert all(b["passage_ids"] for b in bundles)


def test_facts_outside_retained_episodes_are_bundled(tmp_path):
    def respond(task):
        out = historical(task)
        for j in out["episode_judgments"]:
            j.update(supported=False, worth_remembering=False)
        return out
    m = memory(tmp_path, responder=respond)
    bundles, _, _ = evidence_bundles(m)
    assert not m["episodes"] and len(bundles) == 3
    assert all(b["facts"] and not b["episode_ids"] for b in bundles)
    plan = make_plan(m, QUESTIONS)
    pattern = construct_proposal(m, plan["packets"][0], proposal(plan["packets"][0]), bundles)
    assert pattern["supporting_fact_ids"] and not pattern["supporting_episode_ids"]


@pytest.mark.parametrize("change,error", [
    (lambda r: r["support"].append(copy.deepcopy(r["support"][0])), "duplicate"),
    (lambda r: r["support"][0].update(passage_id="fabricated"), "Fabricated"),
    (lambda r: r["counterevidence_ids"].append("fabricated"), "Fabricated"),
    (lambda r: r["support"].pop(), "independent"),
])
def test_invalid_support_rejected(tmp_path, change, error):
    m = memory(tmp_path)
    plan = make_plan(m, QUESTIONS)
    p = plan["packets"][0]
    row = proposal(p)
    change(row)
    with pytest.raises(ValueError, match=error):
        construct_proposal(m, p, row, plan["bundles"])


@pytest.mark.parametrize("overlap", ["record", "decision", "passage"])
def test_dependent_occurrences_do_not_inflate_counts(tmp_path, overlap):
    edges = [edge("d1", record="R1", text="The service failed in east."),
             edge("d1" if overlap == "decision" else "d2", record="R1" if overlap == "record" else "R2",
                  text="The service failed in east." if overlap == "passage" else "The service failed in west.")]
    m = memory(tmp_path, edges=edges)
    plan = make_plan(m, QUESTIONS)
    with pytest.raises(ValueError, match="independent"):
        construct_proposal(m, plan["packets"][0], proposal(plan["packets"][0]), plan["bundles"])


@pytest.mark.parametrize("target_type", ["risk", "resource"])
def test_shared_generic_nodes_do_not_imply_dependence(tmp_path, target_type):
    edges = [edge(f"d{i}", "shared", target_type=target_type, record=f"R{i}", text=f"The service failed in zone {i}.") for i in range(2)]
    m = memory(tmp_path, edges=edges)
    plan = make_plan(m, QUESTIONS)
    row = construct_proposal(m, plan["packets"][0], proposal(plan["packets"][0]), plan["bundles"])
    assert row["independent_support_count"] == 2


def test_prescriptions_cannot_be_promoted_to_execution(tmp_path):
    m = memory(tmp_path)
    plan = make_plan(m, QUESTIONS)
    p = plan["packets"][0]
    with pytest.raises(ValueError, match="execution"):
        construct_proposal(m, p, proposal(p, "reported_recurrence", "reported_occurrence"), plan["bundles"])
    row = construct_proposal(m, p, proposal(p, "prescribed_routine", "prescription"), plan["bundles"])
    assert row["kind"] == "prescribed_routine"


def test_deterministic_packets_limits_context_and_no_truncation(tmp_path):
    m = memory(tmp_path, n=39)
    plan = make_plan(m, QUESTIONS)
    assert plan == make_plan(m, QUESTIONS)
    assert len(plan["packets"]) == 3
    assert all(len(p["primary_bundle_ids"]) <= 18 and len(p["context_bundle_ids"]) <= 2 for p in plan["packets"])
    assert sum(len(p["primary_bundle_ids"]) for p in plan["packets"]) == 39
    split = make_plan(m, QUESTIONS, max_chars=2500)
    assert len(split["packets"]) > 3 and not split["oversized_bundles"]
    assert all(len(serialized(p)) <= 2500 for p in split["packets"])
    tiny = make_plan(m, QUESTIONS, max_chars=20)
    assert len(tiny["oversized_bundles"]) == 39 and not tiny["packets"]


def test_empty_response_and_no_matching_evidence_complete_without_patterns(tmp_path):
    m = memory(tmp_path)
    client = synthesis_client(tmp_path, lambda p: {"proposals": []})
    enriched, _ = run_abstraction(m, QUESTIONS, tmp_path / "out", client)
    assert validate_memory(enriched)["passed"] and not enriched["patterns"]
    empty, _ = run_abstraction(m, [{**QUESTIONS[0], "cues": ["absentterm"]}], tmp_path / "empty", client)
    assert empty["abstraction_metadata"]["status"] == "complete"
    assert empty["abstraction_metadata"]["coverage"]["omitted_bundle_ids"]
    assert client.calls == 1


def test_base_replay_schema_links_and_tamper_detection(tmp_path):
    m = memory(tmp_path, responder=historical)
    saved = copy.deepcopy(m)
    enriched, _ = run_abstraction(m, QUESTIONS, tmp_path / "out", synthesis_client(tmp_path))
    assert m == saved and base_view(enriched) == saved
    assert validate_memory(m)["passed"] and validate_memory(enriched)["passed"]
    p = enriched["patterns"][0]
    index = RecallIndex(enriched)
    assert set(p["supporting_episode_ids"] + p["supporting_fact_ids"]) <= set(index.links[p["id"]])
    enriched["patterns"][0]["claims"][0]["anchors"][0]["quote"] = "fabrication"
    assert not validate_memory(enriched)["passed"]
    bad = copy.deepcopy(saved)
    bad["reviews"][0]["output"]["episode_judgments"][0]["worth_remembering"] = False
    assert not validate_memory(bad)["passed"]


def test_budget_resume_cache_reuse_and_output_identity(tmp_path):
    m = memory(tmp_path, n=20)
    client = synthesis_client(tmp_path)
    partial, _ = run_abstraction(m, QUESTIONS, tmp_path / "out", client, max_calls=1)
    assert partial["abstraction_metadata"]["status"] == "incomplete" and client.calls == 1
    assert not (tmp_path / "out/memory.json").exists()
    client2 = synthesis_client(tmp_path)
    done, _ = run_abstraction(m, QUESTIONS, tmp_path / "out", client2)
    assert done["abstraction_metadata"]["status"] == "complete" and client2.calls == 1
    assert done["abstraction_metadata"]["usage_summary"]["measured_requests"] == 2
    client3 = synthesis_client(tmp_path)
    again, _ = run_abstraction(m, QUESTIONS, tmp_path / "out", client3, max_calls=0)
    assert again["patterns"] == done["patterns"] and client3.calls == 0
    assert not (tmp_path / "out/memory.incomplete.json").exists()
    with pytest.raises(ValueError, match="different frozen"):
        run_abstraction(m, [{**QUESTIONS[0], "question": "Changed question"}], tmp_path / "out", client3)
    changed = synthesis_client(tmp_path)
    changed.config = replace(changed.config, model="different-model")
    run_abstraction(m, QUESTIONS, tmp_path / "different_model", changed)
    assert changed.calls == 2


def test_one_repair_across_budget_and_restarts(tmp_path):
    m = memory(tmp_path)
    def respond(packet):
        return {} if client.calls == 1 else {"proposals": []}
    client = synthesis_client(tmp_path, respond)
    partial, _ = run_abstraction(m, QUESTIONS, tmp_path / "out", client, max_calls=1)
    assert partial["abstraction_metadata"]["status"] == "incomplete"
    good = synthesis_client(tmp_path, lambda p: {"proposals": []})
    done, _ = run_abstraction(m, QUESTIONS, tmp_path / "out", good)
    assert done["abstraction_metadata"]["status"] == "complete" and good.calls == 1
    calls = done["abstraction_metadata"]["call_history"]
    assert len(calls) == 2 and calls[1]["repair"]


def test_exhausted_repair_does_not_loop_on_resume(tmp_path):
    m = memory(tmp_path)
    bad = synthesis_client(tmp_path, lambda p: {})
    partial, _ = run_abstraction(m, QUESTIONS, tmp_path / "out", bad)
    assert bad.calls == 2 and partial["abstraction_metadata"]["status"] == "incomplete"
    again = synthesis_client(tmp_path, lambda p: {})
    run_abstraction(m, QUESTIONS, tmp_path / "out", again)
    assert again.calls == 0


def test_interruption_preserves_accepted_packets_and_reports_usage(tmp_path):
    m = memory(tmp_path, n=20)
    def interrupted(p):
        if client.calls == 2:
            raise KeyboardInterrupt()
        return {"proposals": [proposal(p)]}
    client = synthesis_client(tmp_path, interrupted)
    partial, _ = run_abstraction(m, QUESTIONS, tmp_path / "out", client)
    assert partial["abstraction_metadata"]["coverage"]["processed_packets"] == 1
    assert partial["abstraction_metadata"]["usage_summary"]["failed_requests"] == 1
    client2 = synthesis_client(tmp_path)
    done, _ = run_abstraction(m, QUESTIONS, tmp_path / "out", client2)
    assert done["abstraction_metadata"]["status"] == "complete" and client2.calls == 1


def test_dry_run_no_client_calls_and_pilot_reuses_full_plan(tmp_path):
    m = memory(tmp_path, n=20)
    questions = [{**QUESTIONS[0], "id": f"area{i}"} for i in range(4)]
    client = synthesis_client(tmp_path)
    result, plan = run_abstraction(m, questions, tmp_path / "out", dry_run=True)
    assert result is None and client.calls == 0 and len(plan["packets"]) == 8
    pilot, pilot_plan = run_abstraction(m, questions, tmp_path / "out", client, pilot=True)
    assert pilot_plan == plan and client.calls == 3
    assert pilot["abstraction_metadata"]["status"] == "incomplete"
    done, _ = run_abstraction(m, questions, tmp_path / "out", client)
    assert client.calls == 8 and done["abstraction_metadata"]["status"] == "complete"


def test_exact_duplicates_removed_possible_duplicates_flagged(tmp_path):
    m = memory(tmp_path)
    plan = make_plan(m, QUESTIONS)
    p = plan["packets"][0]
    row = proposal(p)
    related = {**row, "statement": "The service reports suggest a recurring failure mode."}
    review = {"packet_id": p["id"], "request_id": "fixture", "output": {"proposals": [row, copy.deepcopy(row), related]}}
    result = materialize(m, plan, [review])
    assert len(result["patterns"]) == 2 and len(result["exact_duplicates"]) == 1 and result["possible_duplicates"]


def test_oversized_single_bundle_reported_and_prevents_completion(tmp_path):
    m = memory(tmp_path, n=1)
    client = synthesis_client(tmp_path)
    partial, plan = run_abstraction(m, QUESTIONS, tmp_path / "out", client, max_chars=20)
    assert plan["oversized_bundles"] and not plan["packets"] and client.calls == 0
    assert partial["abstraction_metadata"]["status"] == "incomplete"
    assert fingerprint(m) == partial["abstraction_metadata"]["base_fingerprint"]


def test_shared_record_hidden_in_duplicate_source_references_is_dependent(tmp_path):
    edges = [edge("d1", record="R1", text="The service failed in east."),
             edge("d2", record="R2", text="The service failed in west."),
             edge("d3", record="R2", text="The service failed in east.")]
    m = memory(tmp_path, edges=edges)
    plan = make_plan(m, QUESTIONS)
    with pytest.raises(ValueError, match="independent"):
        construct_proposal(m, plan["packets"][0], proposal(plan["packets"][0]), plan["bundles"])


def test_incomplete_enrichment_cannot_be_published_via_legacy_save(tmp_path):
    from org_memory import save_memory
    m = memory(tmp_path)
    partial, _ = run_abstraction(m, QUESTIONS, tmp_path / "out", synthesis_client(tmp_path), max_calls=0)
    with pytest.raises(ValueError, match="checkpoint"):
        save_memory(partial, tmp_path / "memory.json")


def test_malformed_citations_are_saved_as_rejections_not_repaired(tmp_path):
    m = memory(tmp_path)
    def fabricate(p):
        row = proposal(p)
        row["support"][0]["passage_id"] = "fabricated"
        return {"proposals": [row]}
    client = synthesis_client(tmp_path, fabricate)
    enriched, _ = run_abstraction(m, QUESTIONS, tmp_path / "out", client)
    assert client.calls == 1 and not enriched["patterns"]
    assert enriched["abstraction_metadata"]["status"] == "complete"
    assert "Fabricated" in json.loads((tmp_path / "out/rejected_proposals.json").read_text())[0]["reason"]


def test_compatible_provider_sends_medium_reasoning(tmp_path):
    received = []
    def transport(endpoint, payload):
        received.append(payload)
        return {"choices": [{"finish_reason": "stop", "message": {"content": '{"proposals": []}'}}]}
    m = memory(tmp_path)
    client = synthesis_client(tmp_path)
    client.transport = transport
    run_abstraction(m, QUESTIONS, tmp_path / "out", client)
    assert received[0]["reasoning_effort"] == "medium"


def test_shared_incident_event_is_conservatively_dependent(tmp_path):
    edges = [edge(f"d{i}", "incident", target_type="event", record=f"R{i}",
                  text=f"The service failed in zone {i}.") for i in range(2)]
    m = memory(tmp_path, edges=edges)
    plan = make_plan(m, QUESTIONS)
    with pytest.raises(ValueError, match="independent"):
        construct_proposal(m, plan["packets"][0], proposal(plan["packets"][0]), plan["bundles"])


@pytest.mark.parametrize('input_kind,expected', [
    ('empty', '--memory is empty'),
    ('directory', 'requires a JSON file'),
    ('missing', 'reviewed candidates 580/816'),
])
def test_cli_explains_missing_base_before_creating_provider(tmp_path, monkeypatch, capsys, input_kind, expected):
    import run_abstraction as cli
    (tmp_path / 'build_progress.json').write_text(json.dumps({
        'status': 'incomplete', 'coverage': {'reviewed_candidates': 580, 'selected_candidates': 816}}))
    value = {'empty': '', 'directory': str(tmp_path), 'missing': str(tmp_path / 'memory.json')}[input_kind]
    monkeypatch.setattr('sys.argv', ['run_abstraction.py', '--memory', value, '--pilot'])
    def forbidden(*args, **kwargs):
        pytest.fail('Invalid memory input must not create a provider')
    monkeypatch.setattr(cli, 'create_client', forbidden)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    assert expected in capsys.readouterr().err


def partial_memory(tmp_path):
    from org_memory.judged import construct_items, coverage
    base = memory(tmp_path, n=20, responder=historical)
    base['reviews'] = base['reviews'][:1]
    base.update(construct_items(base, base['candidates'], base['proposals'], base['reviews']))
    base['build_metadata']['status'] = 'incomplete'
    base['build_metadata']['coverage'] = coverage(base['candidates'], base['proposals'], base['judge_jobs'], base['reviews'])
    return base


def test_partial_validation_replays_available_judgments_without_claiming_completion(tmp_path):
    from org_memory.validation import validate_checkpoint
    base = partial_memory(tmp_path)
    saved = copy.deepcopy(base)
    assert validate_checkpoint(base)['passed']
    assert not validate_memory(base)['passed']
    require_base(base, preview=True)
    assert base == saved
    with pytest.raises(ValueError, match='completed full_graph'):
        require_base(base)
    base['episodes'][0]['summary'] = 'fabricated'
    assert not validate_checkpoint(base)['passed']
    with pytest.raises(ValueError, match='differ from validated judgments'):
        require_base(base, preview=True)


def test_preview_uses_three_packets_and_never_publishes_production_memory(tmp_path):
    from org_memory.abstraction import validate_enriched
    from org_memory import save_memory
    base = partial_memory(tmp_path)
    questions = [{**QUESTIONS[0], 'id': f'area{i}'} for i in range(4)]
    client = synthesis_client(tmp_path)
    enriched, plan = run_abstraction(base, questions, tmp_path / 'out', client, preview=True)
    assert len(plan['packets']) == 4 and client.calls == 3
    meta = enriched['abstraction_metadata']
    assert meta['status'] == 'preview' and meta['preview_status'] == 'complete'
    assert meta['base_coverage'] == base['build_metadata']['coverage']
    assert base_view(enriched) == base
    assert validate_enriched(enriched, preview=True)['passed']
    assert not validate_memory(enriched)['passed']
    assert (tmp_path / 'out/memory.preview.json').is_file()
    assert not (tmp_path / 'out/memory.json').exists()
    for name in ('inspection_examples', 'coverage', 'recall_comparison'):
        assert json.loads((tmp_path / f'out/{name}.json').read_text())['execution_scope'] == 'preview'
    with pytest.raises(ValueError, match='checkpoint'):
        save_memory(enriched, tmp_path / 'memory.json')


def test_preview_freezes_input_and_can_resume_after_live_checkpoint_changes(tmp_path):
    from org_memory.abstraction_run import load_preview_memory
    source = tmp_path / 'live.json'
    base = partial_memory(tmp_path)
    source.write_text(json.dumps(base))
    out = tmp_path / 'preview'
    first = load_preview_memory(source, out)
    source.write_text('new, even temporarily invalid, live checkpoint')
    assert load_preview_memory(source, out) == first == base
    source.unlink()
    assert load_preview_memory(source, out) == first
    client = synthesis_client(tmp_path)
    run_abstraction(first, QUESTIONS, out, client, preview=True)
    replay, _ = run_abstraction(load_preview_memory(source, out), QUESTIONS, out, client, preview=True, max_calls=0)
    assert client.calls == 1 and replay['abstraction_metadata']['preview_status'] == 'complete'
    with pytest.raises(ValueError, match='source path changed'):
        load_preview_memory(tmp_path / 'different.json', out)
    snapshot = json.loads((out / 'preview_input.json').read_text())
    snapshot['memory']['episodes'][0]['summary'] = 'edited'
    (out / 'preview_input.json').write_text(json.dumps(snapshot))
    with pytest.raises(ValueError, match='fingerprint changed'):
        load_preview_memory(source, out)


def test_preview_cache_and_outputs_stay_separate_even_for_completed_base(tmp_path):
    from org_memory.abstraction_run import load_preview_memory
    base = memory(tmp_path, responder=historical)
    source = tmp_path / 'live.json'
    source.write_text(json.dumps(base))
    preview = tmp_path / 'preview'
    load_preview_memory(source, preview)
    client = synthesis_client(tmp_path)
    run_abstraction(base, QUESTIONS, preview, client, preview=True)
    with pytest.raises(ValueError, match='provisional preview'):
        run_abstraction(base, QUESTIONS, preview, client)
    run_abstraction(base, QUESTIONS, tmp_path / 'production', client)
    assert client.calls == 2
    with pytest.raises(ValueError, match='production/pilot'):
        load_preview_memory(source, tmp_path / 'production')


def test_preview_budget_resume(tmp_path):
    base = partial_memory(tmp_path)
    questions = [{**QUESTIONS[0], 'id': f'area{i}'} for i in range(4)]
    client = synthesis_client(tmp_path)
    incomplete, _ = run_abstraction(base, questions, tmp_path / 'out', client, preview=True, max_calls=1)
    assert client.calls == 1 and incomplete['abstraction_metadata']['preview_status'] == 'incomplete'
    done, _ = run_abstraction(base, questions, tmp_path / 'out', client, preview=True, max_calls=2)
    assert client.calls == 3 and done['abstraction_metadata']['preview_status'] == 'complete'


def test_preview_cli_dry_run_freezes_partial_base_without_provider(tmp_path, monkeypatch, capsys):
    import run_abstraction as cli
    source = tmp_path / 'live.json'
    source.write_text(json.dumps(partial_memory(tmp_path)))
    out = tmp_path / 'out'
    monkeypatch.setattr('sys.argv', ['run_abstraction.py', '--memory', str(source), '--output', str(out), '--preview', '--dry-run'])
    def forbidden(*args, **kwargs):
        pytest.fail('Dry run must not create a provider')
    monkeypatch.setattr(cli, 'create_client', forbidden)
    assert cli.main() == 0
    report = json.loads((out / 'dry_run.json').read_text())
    assert report['execution_scope'] == 'preview' and report['max_new_calls'] == 6
    assert (out / 'preview_input.json').is_file()
    assert 'dry_run' in capsys.readouterr().out
