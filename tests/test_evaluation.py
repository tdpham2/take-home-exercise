"""Evaluation contracts and accounting. Scripted judges do not establish semantic accuracy."""
import copy
import json
from unittest.mock import patch

import pytest

pytest.importorskip("langchain", minversion="1.0")

from org_agent import AgentConfig, OrganizationalAgent
from org_agent.artifacts import SourceArtifacts
from org_agent.tools import DatasetTools
from org_eval.audit import export_audit, import_audit
from org_eval.baseline import TextRAG
from org_eval.benchmark import freeze, write_review_template, load_frozen, validate_reference, draft_model
from org_eval.common import CallBudget, checked_call, read_json
from org_eval.corpus import TextCorpus
from org_eval.judge import judge_answer, judge_packet, validate_judgment
from org_eval.metrics import score_answer, usage_metrics, consistency_metrics, reference_shown
from org_eval.models import Judgment
from org_eval.report import report
from org_eval.runner import run_matrix, run_judging, make_schedule, fork_scoring
from org_memory.hosted import BudgetExceeded, CompatibleClient, ProviderConfig
from org_memory.storage import atomic_json
from scripts.smoke_evaluation import (SyntheticClient, synthetic_benchmark, answer_factory, judge_factory, QUESTION)
from scripts.smoke_agent import make_fixture
from test_candidates import edge, graph


@pytest.fixture
def fixture(tmp_path):
    gp, mp = make_fixture(tmp_path / "fixture")
    source = SourceArtifacts.load(gp)
    corpus = TextCorpus(source)
    bp = synthetic_benchmark(gp, tmp_path / "benchmark")
    return gp, mp, source, corpus, bp


def test_graph_only_is_physically_memory_free(fixture):
    gp, _, source, _, _ = fixture
    with patch("org_agent.artifacts.Artifacts.load", side_effect=AssertionError("Read memory")), \
         patch("org_agent.tools.RecallIndex", side_effect=AssertionError("Built memory index")):
        agent = OrganizationalAgent.from_artifacts(gp, "does-not-exist.json", tool_profile="graph_only",
                                                   client_factory=lambda: answer_factory({}, AgentConfig()))
        assert agent.dataset.memory is None and not agent.dataset.items and not agent.dataset.recall_indexes
        assert {t.name for t in agent.dataset.registered()} == {"search_graph", "graph_neighborhood", "graph_paths", "get_evidence"}
        assert agent.dataset.expand("DocDB") == "DocDB"
        result = agent.answer(QUESTION)
    assert result.status == "complete"
    assert all(c.source_mode == "graph" for c in result.claims)
    with pytest.raises(ValueError):
        DatasetTools(source, tool_profile="invented")


def test_corpus_deduplicates_within_record_without_graph_text(tmp_path):
    edges = [edge("d1", record="R1", text="The API failed."), edge("d2", record="R1", text="The API failed."),
             edge("d3", record="R2", text="The API failed."), edge("d4", kind="inferred", text="SECRET INFERENCE")]
    gp = tmp_path / "graph.json"
    atomic_json(gp, graph(edges))
    c = TextCorpus(SourceArtifacts.load(gp))
    assert len(c.records) == 2 and len(c.by_record["R1"]["passages"]) == 1
    assert len(c.by_record["R1"]["passages"][0]["equivalent_evidence_ids"]) == 2
    assert "SECRET INFERENCE" not in json.dumps(c.records)
    assert not c.search("SECRET INFERENCE")


def test_text_baseline_cites_only_shown_sources_and_counts_retrieval(fixture):
    _, _, source, corpus, _ = fixture
    packets = []
    inner = answer_factory({}, AgentConfig())
    def respond(packet, step, purpose):
        packets.append(packet)
        assert "reference_facets" not in packet and "memory" not in packet
        return inner.responder(packet, step, purpose)
    result = TextRAG(source, client_factory=lambda: SyntheticClient(respond), corpus=corpus).answer(QUESTION)
    assert result.status == "complete" and result.usage["model_calls"] == 1
    assert result.usage["data_tool_calls"] == 1
    assert {c.source_mode for c in result.claims} == {"text"}
    assert all(not c.memory_ids for c in result.claims)
    assert all(e["serialized_chars"] <= AgentConfig().max_request_chars for e in result.trace if e["kind"] == "context")


def test_baseline_repairs_at_most_once_and_rejects_unseen_quotes(fixture):
    _, _, source, _, _ = fixture
    client = SyntheticClient(lambda packet, *_: {"claims": [{"statement": "Made up", "kind": "source_report",
        "citations": [{"evidence_id": "missing", "quote": "Not shown", "start": 0}], "memory_ids": [],
        "confidence": "high", "confidence_reason": "Fixture", "verification_note": ""}], "unanswered": [], "limitations": []})
    answer = TextRAG(source, client_factory=lambda: client).answer(QUESTION)
    assert client.calls == 2 and not answer.claims and answer.validation_errors and answer.status == "partial"


def test_baseline_flushes_trace_before_provider_and_preserves_interruption(fixture, tmp_path):
    _, _, source, corpus, _ = fixture
    path = tmp_path / "answer" / "trace.jsonl"
    def interrupt(*_):
        events = [json.loads(line) for line in path.read_text().splitlines()]
        assert events[-1]["kind"] == "model_started"
        assert any(e["kind"] == "tool" and e["name"] == "retrieve_text" for e in events)
        assert any(e["kind"] == "context" for e in events)
        raise KeyboardInterrupt()
    client = SyntheticClient(interrupt)
    with patch.object(client, "close", wraps=client.close) as close:
        result = TextRAG(source, corpus=corpus, client_factory=lambda: client).answer(QUESTION, trace_path=path)
    assert result.status == "failed" and "KeyboardInterrupt" in result.stop_reason
    assert [json.loads(line) for line in path.read_text().splitlines()] == result.trace
    close.assert_called_once()


def test_matrix_streams_every_approach_before_provider_completion(fixture, tmp_path):
    gp, mp, _, _, bp = fixture
    output = tmp_path / "streamed"
    observed = set()
    def factory(job, cfg):
        inner = answer_factory(job, cfg)
        def respond(packet, step, purpose):
            trace = output / "runs" / job["run_id"] / "trace.jsonl"
            events = [json.loads(line) for line in trace.read_text().splitlines()]
            assert events[-1]["kind"] == "model_started"
            assert not (trace.parent / "answer.json").exists()
            observed.add(job["approach"])
            return inner.responder(packet, step, purpose)
        return SyntheticClient(respond)
    result = run_matrix(gp, mp, bp, output, AgentConfig(), split="pilot", client_factory=factory)
    assert result["status"] == "complete"
    assert observed == {"text_rag", "graph_only", "memory_graph"}
    for path in (output / "runs").glob("*/answer.json"):
        events = [json.loads(line) for line in (path.parent / "trace.jsonl").read_text().splitlines()]
        assert events == read_json(path)["trace"]


def test_matrix_preserves_flushed_events_when_system_raises(fixture, tmp_path):
    from org_memory.storage import atomic_text
    gp, mp, _, _, bp = fixture
    output = tmp_path / "escaped"
    events = [{"sequence": 1, "kind": "model_started", "call_number": 1}]
    def fail(question, *, trace_path=None):
        atomic_text(trace_path, json.dumps(events[0]) + "\n")
        raise OSError("Synthetic escaped provider error")
    with patch.object(TextRAG, "answer", side_effect=fail), patch.object(OrganizationalAgent, "answer", side_effect=fail):
        run_matrix(gp, mp, bp, output, AgentConfig(), split="pilot", client_factory=answer_factory, max_runs=1)
    answer = read_json(next((output / "runs").glob("*/answer.json")))
    assert answer["status"] == "failed" and answer["trace"] == events
    assert usage_metrics(answer)["calls_without_complete_usage"] == 1


@pytest.mark.parametrize("flags,expected", [([], 200000), (["--max-request-chars", "60000"], 60000)])
def test_evaluation_cli_passes_context_limit_to_all_systems(fixture, tmp_path, flags, expected):
    from run_evaluation import main
    gp, mp, _, _, bp = fixture
    configs = []
    def factory(job, cfg):
        configs.append((job["approach"], cfg.max_request_chars))
        return answer_factory(job, cfg)
    def run(*args, **kwargs):
        return run_matrix(*args, **kwargs, client_factory=factory)
    output = tmp_path / "context_limit"
    with patch("run_evaluation.run_matrix", side_effect=run):
        status = main(["run", "--split", "pilot", "--graph", str(gp), "--memory", str(mp),
                       "--benchmark", str(bp), "--output", str(output), *flags])
    assert status == 0
    assert set(configs) == {(approach, expected) for approach in ("text_rag", "graph_only", "memory_graph")}
    assert read_json(output / "manifest.json")["answer_configuration"]["max_request_chars"] == expected


def test_failed_provider_preflight_is_saved(fixture, tmp_path):
    from run_evaluation import main
    from org_memory.hosted import ProviderUnavailable
    gp, mp, _, _, _ = fixture
    output = tmp_path / "preflight"
    client = SyntheticClient(lambda *_: None)
    with patch("run_evaluation.client_for", return_value=client), \
         patch("run_evaluation.checked_call", side_effect=ProviderUnavailable("Synthetic transport failure")):
        status = main(["preflight", "--graph", str(gp), "--memory", str(mp), "--check-provider",
                       "--judge-model", "gpt-6.1-sol", "--output", str(output)])
    result = read_json(output / "preflight.json")
    assert status == 2 and result["production_memory_ready"]
    assert result["provider_checked"] is False and result["provider_probe"]["status"] == "failed"
    assert result["provider_probe"]["model"] == "gpt-6.1-sol"


def test_notebook_preserves_claim_evidence_and_discard_reasons(fixture):
    from org_eval.notebook import claim_rows, trace_rows, ranking_exclusions
    _, _, source, _, _ = fixture
    answer = TextRAG(source, client_factory=lambda: answer_factory({}, AgentConfig())).answer(QUESTION).model_dump()
    c = claim_rows(answer)[0]
    assert c["confidence"] == answer["claims"][0]["confidence"]
    assert c["route"] == "text" and c["confidence_reason"]
    assert answer["claims"][0]["citations"][0]["quote"] in c["exact_citations"]
    answer["trace"] += [
        {"sequence": 100, "kind": "item_discard", "item_id": "item_1", "reason": "Different tenant"},
        {"sequence": 101, "kind": "context_eviction", "call_id": "call_1", "item_ids": ["item_1"],
         "evidence_ids": ["ev_1"], "reason": "context character budget: oldest unpinned exchange"},
        {"sequence": 102, "kind": "retrieval_discard", "item_id": "item_2", "reason": "below limit"}]
    rows = trace_rows(answer)
    assert any(r["event"] == "item_discard" and r["reason"] == "Different tenant" for r in rows)
    assert any(r["event"] == "context_eviction" and "ev_1" in r["items_or_evidence"] for r in rows)
    assert ranking_exclusions(answer) == [{"ranking_exclusion_reason": "below limit", "events": 1}]


def test_submission_notebook_does_not_run_models_or_substitute_synthetic_results(tmp_path):
    import ast
    from scripts.create_evaluation_notebook import build_notebook
    from org_eval.notebook import load_saved_results
    nb = build_notebook()
    assert nb.metadata["task2"]["artifact_only"]
    assert load_saved_results(tmp_path / "missing") == (None, None, None)
    calls = set()
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        for node in ast.walk(ast.parse(cell.source)):
            if isinstance(node, ast.Call):
                calls.add(node.func.id if isinstance(node.func, ast.Name) else
                          node.func.attr if isinstance(node.func, ast.Attribute) else "")
    assert not {"run_matrix", "run_judging", "create_client", "client_for", "answer", "smoke", "report"} & calls


def test_submission_loader_rejects_synthetic_experiment(fixture, tmp_path):
    from org_eval.notebook import load_saved_results
    gp, mp, _, _, bp = fixture
    output = tmp_path / "synthetic"
    run_matrix(gp, mp, bp, output, AgentConfig(), split="pilot", client_factory=answer_factory, max_runs=1)
    with pytest.raises(ValueError, match="synthetic results cannot substitute"):
        load_saved_results(output)


def test_benchmark_review_is_bound_to_content_and_source(fixture, tmp_path):
    _, _, _, corpus, bp = fixture
    b = load_frozen(bp, corpus)
    assert len(make_schedule(b)) == 54 and len(make_schedule(b, "pilot")) == 6
    directory = bp.parent
    draft = read_json(directory / "draft.json")
    draft["questions"][0]["text"] += " Changed."
    atomic_json(directory / "changed.json", draft)
    with pytest.raises(ValueError, match="does not match"):
        freeze(corpus, directory / "changed.json", directory / "synthetic_review.json", tmp_path / "frozen.json")
    q = draft_model(draft["questions"][0])
    q.facets[0].evidence[0].quote = "Fabricated"
    with pytest.raises(ValueError, match="quote/offset"):
        validate_reference(q, corpus)


def test_explicit_user_assumption_is_distinct_from_human_review(fixture, tmp_path):
    from org_eval.benchmark import review_basis
    gp, mp, _, corpus, bp = fixture
    review = read_json(bp.parent / "synthetic_review.json")
    review.update(review_basis="user_assumption", reviewer="User instruction (synthetic test)",
                  authorization="Let's assume they are correct")
    rp, fp = tmp_path / "assumption.json", tmp_path / "assumed_frozen.json"
    atomic_json(rp, review)
    freeze(corpus, bp.parent / "draft.json", rp, fp)
    assert review_basis(load_frozen(fp, corpus)["review"]) == "user_assumption"
    output = tmp_path / "assumed_run"
    run_matrix(gp, mp, fp, output, AgentConfig(), split="pilot", client_factory=answer_factory)
    run_judging(output, AgentConfig(model="gpt-6-sol"), client_factory=judge_factory)
    result = report(output)
    assert result["benchmark_review_basis"] == "user_assumption"
    assert "no human source review" in result["limitations"][0]
    review.pop("authorization")
    atomic_json(rp, review)
    with pytest.raises(ValueError, match="explicit user instruction"):
        freeze(corpus, bp.parent / "draft.json", rp, tmp_path / "unauthorized.json")


def test_empty_answer_is_not_perfect_grounding_or_consistency(fixture):
    _, _, _, corpus, bp = fixture
    q = read_json(bp)["questions"][0]
    answer = {"question": q["text"], "claims": [], "unanswered": ["Unknown"], "limitations": [],
              "trace": [], "usage": {}, "validation_errors": []}
    from org_eval.metrics import failure_judgment
    j = failure_judgment(q)
    scores = score_answer(q, answer, j, corpus)
    assert scores["coverage"] == 0 and scores["groundedness"] is None and scores["citation_validity"] is None
    c = consistency_metrics(j, j, {"comparable_pairs": [], "review_flags": []})
    assert c["supported_facet_jaccard"] is None and c["contradiction_rate"] is None


def test_exact_citation_does_not_force_semantic_credit(fixture, tmp_path):
    _, _, source, corpus, bp = fixture
    q = read_json(bp)["questions"][0]
    a = TextRAG(source, client_factory=lambda: answer_factory({}, AgentConfig())).answer(QUESTION).model_dump()
    a["claims"][0]["statement"] = "The outage was permanently fixed and every check was performed."
    def reject(packet, *_):
        j = judge_factory().responder(packet, 1, "evaluation_judgment")
        for c in j["claims"]:
            c["verdict"] = "contradicted"
            c["rationale"] = "Fixture deliberately asserts recovery from text saying recovery unverified."
        for f in j["facets"]:
            f["score"] = 0
            f["claim_ids"] = []
        j["specificity"]["score"] = 0
        return j
    j = judge_answer(SyntheticClient(reject), q, a, corpus, tmp_path / "judgment.json", {"model": "synthetic"})
    scores = score_answer(q, a, j.model_dump(), corpus)
    assert scores["citation_validity"] == 1 and scores["groundedness"] == 0 and scores["coverage"] == 0
    packet = judge_packet(q, a, corpus)
    assert "source_mode" not in json.dumps(packet) and "memory_ids" not in json.dumps(packet)
    bad = j.model_copy(deep=True)
    bad.claims[0].verdict = "supported"
    bad.claims[0].evidence_ids = ["unknown"]
    with pytest.raises(ValueError, match="Unknown evidence"):
        validate_judgment(bad, q, a, {s["evidence_id"] for s in packet["sources"]})


def test_visible_span_checks_offsets_not_just_evidence_ids(fixture):
    _, _, _, corpus, bp = fixture
    ref = read_json(bp)["questions"][0]["facets"][0]["evidence"][0]
    span = {**ref, "quote": ref["quote"][:10], "end": 10}
    assert not reference_shown(ref, [span], corpus)


def test_tokens_missing_and_cached_subsets_are_not_added():
    answer = {"trace": [{"kind": "model", "provider": {"usage": {"input_tokens": 100, "output_tokens": 20,
                "cached_input_tokens": 40, "reasoning_output_tokens": 8}}}], "usage": {"model_calls": 1}}
    cost = usage_metrics(answer)
    assert cost["input_tokens"] + cost["output_tokens"] == 120
    answer["trace"].append({"kind": "model", "provider": {"status": "failed"}})
    cost = usage_metrics(answer)
    assert cost["input_tokens"] is None and cost["reported_input_tokens_lower_bound"] == 100
    answer["trace"][1]["provider"] = {"cached": True}
    assert not usage_metrics(answer)["fresh_measurement"]


def test_stage_budget_persists_attempts(tmp_path):
    b = CallBudget(tmp_path / "calls.json", 1)
    row = b.reserve("fixture")
    b.finish(row, status="failed")
    with pytest.raises(BudgetExceeded):
        CallBudget(tmp_path / "calls.json", 1).reserve("retry")
    assert CallBudget(tmp_path / "calls.json", 2).reserve("retry")["number"] == 2


def test_full_matrix_resume_judge_audit_and_report(fixture, tmp_path):
    gp, mp, _, _, bp = fixture
    output = tmp_path / "experiment"
    caches, calls = [], []
    def factory(job, cfg):
        caches.append(cfg.cache_dir)
        calls.append(job["run_id"])
        return answer_factory(job, cfg)
    first = run_matrix(gp, mp, bp, output, AgentConfig(), client_factory=factory, max_runs=2)
    assert first["status"] == "incomplete" and first["finished"] == 2
    final = run_matrix(gp, mp, bp, output, AgentConfig(), client_factory=factory)
    assert final["status"] == "complete" and len(calls) == 54 and len(set(caches)) == 54
    run_matrix(gp, mp, bp, output, AgentConfig(), client_factory=factory)
    assert len(calls) == 54
    progress = run_judging(output, AgentConfig(model="gpt-6-sol"), client_factory=judge_factory)
    assert progress["status"] == "complete" and progress["consistency_judged"] == 36
    result = report(output)
    assert result["status"] == "automated_only" and result["synthetic"]
    export_audit(output)
    review = read_json(output / "audit.template.json")
    assert len(review["items"]) >= 18
    for item in review["items"]:
        item.update(reviewed=True, notes="Synthetic review test")
    review["reviewer"] = "SYNTHETIC TEST REVIEWER"
    atomic_json(output / "review.json", review)
    import_audit(output, output / "review.json")
    result = report(output)
    assert result["status"] == "audited"
    assert len(result["rows"]) == 54 and len(result["aggregates"]) == 3
    assert all(a["questions"] == 6 for a in result["aggregates"])
    assert (output / "report" / "report.html").exists()
    # Altering evidence after audit invalidates the report, not the audit history.
    p = next((output / "runs").glob("*/answer.json"))
    a = read_json(p)
    a["claims"][0]["statement"] += " Tampered."
    atomic_json(p, a)
    with pytest.raises(ValueError, match="audit"):
        report(output)


def test_repeated_baseline_requests_use_distinct_response_caches(fixture, tmp_path):
    _, _, source, _, _ = fixture
    count = []
    def transport(endpoint, payload):
        count.append(1)
        return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({
            "claims": [], "unanswered": ["Synthetic abstention"], "limitations": []})}}],
            "usage": {"prompt_tokens": 30, "completion_tokens": 10}}
    for n in range(2):
        cfg = AgentConfig(cache_dir=str(tmp_path / f"repetition-{n}"))
        result = TextRAG(source, cfg, client_factory=lambda: CompatibleClient(
            ProviderConfig(api_key="fixture", cache_dir=cfg.cache_dir), transport=transport)).answer(QUESTION)
        assert result.usage["cache_replays"] == 0
    assert len(count) == 2


def test_judge_repair_is_bounded_and_resumable(fixture, tmp_path):
    _, _, source, corpus, bp = fixture
    q = read_json(bp)["questions"][0]
    a = TextRAG(source, client_factory=lambda: answer_factory({}, AgentConfig())).answer(QUESTION).model_dump()
    packet = judge_packet(q, a, corpus)
    good = judge_factory().responder(packet, 1, "evaluation_judgment")
    client = SyntheticClient(lambda p, step, purpose: {} if step == 1 else good)
    path = tmp_path / "judgment.json"
    result = checked_call(client, "Fixture", packet, Judgment, "test", path)
    assert client.calls == 2 and result.specificity.score == 4
    checked_call(client, "Fixture", packet, Judgment, "test", path)
    assert client.calls == 2
    bad = SyntheticClient(lambda *_: {})
    with pytest.raises(ValueError, match="one repair"):
        checked_call(bad, "Fixture", packet, Judgment, "test", tmp_path / "bad.json")
    assert bad.calls == 2


def test_reference_revision_rescores_saved_answers_without_regeneration(fixture, tmp_path):
    gp, mp, _, corpus, bp = fixture
    old = tmp_path / "old"
    run_matrix(gp, mp, bp, old, AgentConfig(), split="pilot", client_factory=answer_factory)
    draft = read_json(bp.parent / "draft.json")
    draft["questions"][0]["facets"][0]["description"] += " Clarified scope."
    dp, rp, fp = tmp_path / "revised.json", tmp_path / "review.json", tmp_path / "frozen.json"
    atomic_json(dp, draft)
    write_review_template(dp, rp)
    r = read_json(rp)
    r["reviewer"] = "SYNTHETIC REVIEW"
    for item in r["questions"]:
        item.update(approved=True, notes="Synthetic reference revision")
    atomic_json(rp, r)
    freeze(corpus, dp, rp, fp)
    new = tmp_path / "new"
    result = fork_scoring(old, fp, new)
    assert result["reused_answers"] == 6
    run_judging(new, AgentConfig(model="gpt-6-sol"), client_factory=judge_factory)
    assert report(new)["answers_reused_from"] == read_json(old / "manifest.json")["fingerprint"]
    changed = copy.deepcopy(draft)
    changed["questions"][0]["text"] += " Different question."
    atomic_json(dp, changed)
    write_review_template(dp, rp)
    r["benchmark_fingerprint"] = read_json(rp)["benchmark_fingerprint"]
    atomic_json(rp, r)
    fp2 = tmp_path / "changed_frozen.json"
    freeze(corpus, dp, rp, fp2)
    with pytest.raises(ValueError, match="cannot change questions"):
        fork_scoring(old, fp2, tmp_path / "invalid")


def test_resume_after_interruption_immediately_after_answer_publication(fixture, tmp_path):
    from org_agent.agent import save_result
    gp, mp, _, _, bp = fixture
    output = tmp_path / "interrupted"
    calls = []
    def factory(job, cfg):
        calls.append(job["run_id"])
        return answer_factory(job, cfg)
    def publish_then_interrupt(answer, directory):
        save_result(answer, directory)
        raise OSError("Synthetic interruption after the answer commit marker")
    with patch("org_eval.runner.save_result", side_effect=publish_then_interrupt):
        with pytest.raises(OSError, match="commit marker"):
            run_matrix(gp, mp, bp, output, AgentConfig(), split="pilot", client_factory=factory)
    progress = run_matrix(gp, mp, bp, output, AgentConfig(), split="pilot", client_factory=factory)
    assert progress["status"] == "complete" and len(calls) == 6
