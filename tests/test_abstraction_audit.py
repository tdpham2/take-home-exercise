"""Audit contracts and controlled failure cases, not a model-accuracy benchmark."""
import copy
from dataclasses import replace
import json

import pytest

from org_memory.abstraction import serialized
from org_memory.abstraction_audit import (DIMENSIONS, audit_plan, evidence_map, load_run,
                                        run_audit, validate_response)
from org_memory.abstraction_run import run_abstraction
from org_memory.hosted import CompatibleClient, ProviderConfig, ProviderUnavailable
from test_abstraction import QUESTIONS, historical, memory, proposal, synthesis_client
from test_candidates import edge


def frozen_run(tmp_path, *, n=3, areas=1, responder=None, edges=None):
    base = memory(tmp_path, n=n, responder=historical, edges=edges)
    questions = [{**QUESTIONS[0], "id": f"area{i}"} for i in range(areas)]
    enriched, source_plan = run_abstraction(base, questions, tmp_path / "source",
                                          synthesis_client(tmp_path, responder))
    return enriched, source_plan


def assessment(task):
    evidence = list(evidence_map(task))[:2]
    return {"verdicts": [{"proposal_id": row["proposal_id"], "verdict": "supported", "recommendation": "keep",
                          "explanation": "Synthetic response for contract tests only.",
                          "checks": {d: "Fixture assessment." for d in DIMENSIONS},
                          "evidence_ids": evidence, "issues": [], "revisions": []}
                         for row in task["proposals"]]}


def reviewer(tmp_path, responder=assessment):
    def transport(endpoint, payload):
        assert payload["reasoning_effort"] == "high"
        task = json.loads(payload["messages"][1]["content"])["task"]
        output = responder(task)
        return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(output)}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 40}}
    return CompatibleClient(ProviderConfig(api_key="fixture", model="gpt-6.1-sol", reasoning_effort="high",
                                          cache_dir=str(tmp_path / "audit-cache")), transport=transport)


def test_load_replays_judgments_and_verifies_packets(tmp_path):
    enriched, plan = frozen_run(tmp_path)
    loaded, rebuilt = load_run(tmp_path / "source")
    assert loaded == enriched and rebuilt == plan
    path = tmp_path / "source/packets.json"
    saved = json.loads(path.read_text())
    saved["packets"][0]["passages"][0]["text"] = "Fabricated replacement"
    path.write_text(json.dumps(saved))
    with pytest.raises(ValueError, match="Frozen packets differ"):
        load_run(tmp_path / "source")


def test_rejected_and_retained_blinded_complete_plan_preserves_source(tmp_path):
    def generate(packet):
        valid = proposal(packet)
        invalid = copy.deepcopy(valid)
        invalid["support"][0]["passage_id"] = "fake"
        return {"proposals": [valid, invalid]}
    enriched, source_plan = frozen_run(tmp_path, areas=4, responder=generate)
    original = copy.deepcopy(enriched)
    plan = audit_plan(enriched, source_plan)
    assert len(plan["proposals"]) == 8 and len(plan["pilot_task_ids"]) == 4
    assert {r["structural_status"] for r in plan["proposals"]} == {"retained", "rejected", "duplicate"}
    for task in plan["tasks"]:
        sent = serialized(task["input"])
        assert "structural_status" not in sent and "gpt-5.6-luna" not in sent
        assert "structural_reason" not in sent and "raw_edge" not in sent
    result = run_audit(plan, tmp_path / "audit", reviewer(tmp_path))
    assert result["status"] == "complete" and len(result["verdicts"]) == 8
    assert result["summary"]["rejected"]["potential_recovery_candidates"] == 4
    assert enriched == original
    assert not (tmp_path / "audit/memory.json").exists()
    assert all(r["anchors"] for r in result["verdicts"])


def test_adds_same_record_context_including_omitted_fix_no_inferences(tmp_path):
    edges = [edge(f"d{i}", f"r{i}", record=f"R{i}", text=f"The service failed in zone {i}.") for i in range(3)]
    edges += [edge("d30", "r30", record="R0", text="Remediation deployed; checks subsequently passed."),
              edge("d31", "r31", record="R0", kind="inferred", text="INFERRED SECRET")]
    def generate(packet):
        row = proposal(packet)
        row['support'] = [{'passage_id': p['id'], 'basis': 'uncertain'} for p in packet['passages']
                          if 'service failed' in p['text']]
        return {'proposals': [row]}
    enriched, source_plan = frozen_run(tmp_path, edges=edges, responder=generate)
    # Simulate an extracted fix outside the original packet while retaining it in
    # the frozen base archive, so the augmentation path itself is exercised.
    for packet in source_plan['packets']:
        packet['passages'] = [p for p in packet['passages'] if 'Remediation deployed' not in p['text']]
    plan = audit_plan(enriched, source_plan)
    # All extracted non-administrative same-record passages are available even if not selected.
    checked = False
    for task in plan["tasks"]:
        q = task["input"]
        cited = {s["passage_id"] for r in q["proposals"] for s in r["proposal"]["support"]}
        cited_records = {rid for p in q["packet"]["passages"] if p["id"] in cited for rid in p["record_ids"]}
        all_passages = q["packet"]["passages"] + q["additional_record_passages"]
        if "R0" in cited_records:
            checked = True
            assert any("Remediation deployed" in p["text"] for p in all_passages)
            assert any("Remediation deployed" in p["text"] for p in q["additional_record_passages"])
        assert "INFERRED SECRET" not in serialized(q)
    assert checked


@pytest.mark.parametrize("corruption", ["missing", "duplicate", "extra", "fabricated", "duplicate_evidence", "revision"])
def test_invalid_verdict_coverage_and_citations(tmp_path, corruption):
    enriched, source_plan = frozen_run(tmp_path)
    task = audit_plan(enriched, source_plan)["tasks"][0]["input"]
    output = assessment(task)
    row = output["verdicts"][0]
    if corruption == "missing":
        output["verdicts"] = []
    elif corruption == "duplicate":
        output["verdicts"].append(copy.deepcopy(row))
    elif corruption == "extra":
        row["proposal_id"] = "unknown"
    elif corruption == "fabricated":
        row["evidence_ids"] = ["ev_fabricated"]
    elif corruption == "duplicate_evidence":
        row["evidence_ids"] *= 2
    else:
        row["recommendation"] = "revise"
    with pytest.raises(ValueError):
        validate_response(output, task)


def test_budget_resume_pilot_four_areas_cache_reuse_and_identity(tmp_path):
    enriched, source_plan = frozen_run(tmp_path, n=20, areas=4)
    plan = audit_plan(enriched, source_plan)
    client = reviewer(tmp_path)
    partial = run_audit(plan, tmp_path / "out", client, pilot=True, max_calls=2)
    assert partial["status"] == "incomplete" and not partial["scope_complete"]
    pilot = run_audit(plan, tmp_path / "out", client, pilot=True, max_calls=2)
    assert pilot["scope_complete"] and pilot["status"] == "incomplete" and client.calls == 4
    complete = run_audit(plan, tmp_path / "out", client)
    assert complete["status"] == "complete" and client.calls == len(plan["tasks"])
    replay = run_audit(plan, tmp_path / "other", client, max_calls=0)
    assert replay["status"] == "complete" and client.calls == len(plan["tasks"])
    client.config = replace(client.config, model="different")
    with pytest.raises(ValueError, match="different frozen audit"):
        run_audit(plan, tmp_path / "out", client)


def test_format_repair_survives_budget_boundary_and_exhausts_once(tmp_path):
    enriched, source_plan = frozen_run(tmp_path)
    plan = audit_plan(enriched, source_plan)
    calls = []
    def respond(task):
        calls.append(task)
        return {"verdicts": []} if len(calls) == 1 else assessment(task)
    client = reviewer(tmp_path, respond)
    first = run_audit(plan, tmp_path / "out", client, max_calls=1)
    assert first["status"] == "incomplete" and client.calls == 1
    done = run_audit(plan, tmp_path / "out", client, max_calls=1)
    assert done["status"] == "complete" and client.calls == 2
    trace = json.loads((tmp_path / "out/hosted_calls.json").read_text())
    assert [c["repair"] for c in trace] == [False, True]
    broken = reviewer(tmp_path / "broken", lambda task: {"verdicts": []})
    bad = run_audit(plan, tmp_path / "bad", broken)
    assert bad["status"] == "incomplete" and broken.calls == 2
    again = run_audit(plan, tmp_path / "bad", broken)
    assert again["status"] == "incomplete" and broken.calls == 2
    assert "exhausted" in again["incomplete_reason"]


def test_interrupted_execution_retries_only_unfinished_task(tmp_path):
    enriched, source_plan = frozen_run(tmp_path, areas=4)
    plan = audit_plan(enriched, source_plan)
    seen = []
    def respond(task):
        seen.append(task)
        if len(seen) == 2:
            raise KeyboardInterrupt()
        return assessment(task)
    client = reviewer(tmp_path, respond)
    first = run_audit(plan, tmp_path / "out", client)
    assert first["coverage"]["completed_tasks"] == 1
    done = run_audit(plan, tmp_path / "out", client)
    assert done["status"] == "complete" and client.calls == 5
    assert seen[1] == seen[2]
    assert sum(x == seen[0] for x in seen) == 1


def test_provider_preflight_error_is_actionable_and_cached_verdicts_revalidate(tmp_path):
    enriched, source_plan = frozen_run(tmp_path)
    plan = audit_plan(enriched, source_plan)
    client = reviewer(tmp_path)
    def unavailable(*args):
        raise ProviderUnavailable('Selected model is not in the account catalog.')
    original = client.json
    client.json = unavailable
    failed = run_audit(plan, tmp_path / 'out', client)
    assert failed['new_calls_this_run'] == 0
    assert 'account catalog' in failed['incomplete_reason']
    client.json = original
    done = run_audit(plan, tmp_path / 'out', client)
    assert done['status'] == 'complete'
    cache_path = next((tmp_path / 'audit-cache/abstraction-audit-v1').glob('*.json'))
    cache = json.loads(cache_path.read_text())
    cache['review']['output']['verdicts'][0]['evidence_ids'] = ['ev_invented']
    cache_path.write_text(json.dumps(cache))
    with pytest.raises(ValueError, match='Fabricated'):
        run_audit(plan, tmp_path / 'out', client)


def test_identical_passages_preserve_each_source_and_anchor_record(tmp_path):
    edges = [edge('d1', 'r1', record='R1', text='The service failed in east.'),
             edge('d2', 'r2', record='R2', text='The service failed in east.'),
             edge('d3', 'r3', record='R3', text='The service failed in west.')]
    enriched, source_plan = frozen_run(tmp_path, edges=edges)
    plan = audit_plan(enriched, source_plan)
    passages = plan['tasks'][0]['input']['packet']['passages']
    shared = next(p for p in passages if 'east' in p['text'])
    assert shared['record_ids'] == ['R1', 'R2'] and len(shared['evidence_ids']) == 2
    def respond(task):
        result = assessment(task)
        for row in result['verdicts']:
            row['evidence_ids'] = shared['evidence_ids']
        return result
    report = run_audit(plan, tmp_path / 'out', reviewer(tmp_path, respond))
    anchors = report['verdicts'][0]['anchors']
    assert {tuple(a['record_ids']) for a in anchors} == {('R1',), ('R2',)}


def test_split_preserves_entire_packet_and_oversized_never_truncates(tmp_path):
    def generate(packet):
        return {"proposals": [dict(proposal(packet), statement=f"Comparison {i}.") for i in range(3)]}
    enriched, source_plan = frozen_run(tmp_path, responder=generate)
    original = audit_plan(enriched, source_plan)
    first_input = original["tasks"][0]["input"]
    singleton = {**first_input, "proposals": first_input["proposals"][:1]}
    cap = len(serialized(singleton)) + 10
    split = audit_plan(enriched, source_plan, max_chars=cap)
    assert len(split["tasks"]) == 3 and not split["oversized_proposals"]
    assert len(split["pilot_task_ids"]) == 3
    assert all(t["input"]["packet"] == first_input["packet"] for t in split["tasks"])
    oversized = audit_plan(enriched, source_plan, max_chars=10)
    assert not oversized["tasks"] and len(oversized["oversized_proposals"]) == 3
    client = reviewer(tmp_path)
    report = run_audit(oversized, tmp_path / "out", client)
    assert report["status"] == "incomplete" and client.calls == 0


def test_empty_proposals_complete_without_hosted_calls(tmp_path):
    enriched, source_plan = frozen_run(tmp_path, responder=lambda packet: {"proposals": []})
    plan = audit_plan(enriched, source_plan)
    client = reviewer(tmp_path)
    report = run_audit(plan, tmp_path / "out", client)
    assert report["status"] == "complete" and client.calls == 0


@pytest.mark.parametrize("case,issue,quote", [
    ("prescription", "prescription_as_execution", "Verify the upload backend end-to-end with mocked S3 + Mongo + Redis."),
    ("prevalence", "unsupported_prevalence", "Download report lacked text content, though the preview report showed all data."),
    ("filtering", "topic_conflation", "It only searches the platforms that have been added to that network."),
    ("duplicate", "dependent_sources", "The service failed in zone 1."),
    ("remediation", "omitted_counterevidence", 'Data-service alerting for long-running batches has been implemented.'),
])
def test_semantic_inspection_cases_preserve_findings_without_editing_memory(tmp_path, case, issue, quote):
    # These are curated review scenarios, NOT assertions that a mocked model detects errors.
    edges = [edge("d1", "r1", record="R1", text=quote),
             edge("d2", "r2", record="R2", text="The service failed in zone 2.")]
    enriched, source_plan = frozen_run(tmp_path, edges=edges)
    original = copy.deepcopy(enriched)
    plan = audit_plan(enriched, source_plan)
    def respond(task):
        out = assessment(task)
        for row in out["verdicts"]:
            refs = row["evidence_ids"]
            row.update(verdict="partly_supported", recommendation="revise",
                       issues=[{"code": issue, "explanation": f"Curated {case} inspection finding.", "evidence_ids": refs}],
                       revisions=[{"statement": "A narrower source-reported observation.",
                                   "kind": "hypothesized_mechanism", "evidence_ids": refs}])
        return out
    result = run_audit(plan, tmp_path / "out", reviewer(tmp_path, respond))
    assert result["verdicts"][0]["issues"][0]["code"] == issue
    assert result["structural_semantic_disagreements"]
    assert enriched == original


def test_cli_dry_run_never_opens_provider_and_rejects_source_output(tmp_path, monkeypatch):
    import run_abstraction_audit as cli
    frozen_run(tmp_path)
    def forbidden(*args, **kwargs):
        pytest.fail("Dry run must not open provider")
    monkeypatch.setattr(cli, "create_client", forbidden)
    monkeypatch.setattr("sys.argv", ["audit", "--run", str(tmp_path / "source"),
                                     "--output", str(tmp_path / "audit"), "--dry-run"])
    assert cli.main() == 0
    assert json.loads((tmp_path / "audit/dry_run.json").read_text())["initial_calls"] == 1
    monkeypatch.setattr("sys.argv", ["audit", "--run", str(tmp_path / "source"), "--output", str(tmp_path / "source")])
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 2
