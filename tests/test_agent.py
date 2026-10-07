"""Agent contracts using real create_agent execution and synthetic provider responses."""
import json

import pytest

pytest.importorskip("langchain", minversion="1.0")

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from org_agent import AgentConfig, OrganizationalAgent, save_result
from org_agent.adapter import JsonChatModel
from org_agent.artifacts import Artifacts
from org_agent.models import DraftAnswer
from org_agent.runtime import ContextExceeded, RunLedger, validate_answer
from org_agent.tools import DatasetTools
from org_memory.hosted import CompatibleClient, ProviderConfig, ProviderUnavailable
from org_memory.storage import atomic_json
from test_candidates import edge, graph
from test_review import accept_facts, build


SOURCE = "On April 19, 2026, the service stopped updating. Jobs exceeded the 10 hour timeout and retried."


def inputs(tmp_path, edges=None, responder=None):
    data = graph(edges or [edge("d1", "r1", record="KEP-6969", text=SOURCE),
                           edge("d2", "r2", record="R2", text="The unrelated service changed its display color.")])
    memory = build(data, tmp_path / "judge", responder or (lambda task: accept_facts(task, "historical_statement")))
    gp, mp = tmp_path / "graph.json", tmp_path / "memory.json"
    atomic_json(gp, data)
    atomic_json(mp, memory)
    return gp, mp, memory


def action(name, args, **extra):
    return {"tool_name": name, "arguments_json": json.dumps(args), "purpose": "Inspect evidence for the question.",
            "discarded_items": [], "pin_evidence_ids": [], **extra}


class ScriptedClient:
    def __init__(self, responder):
        self.responder = responder
        self.calls = 0
        self.trace = []
        self.packets = []
        self.closed = False

    def json(self, system, packet, schema, purpose):
        self.packets.append(packet)
        self.calls += 1
        self.trace.append({"cached": False, "status": "completed", "usage": {"input_tokens": 30, "output_tokens": 10,
                           "cached_input_tokens": 5, "reasoning_output_tokens": 4}})
        return self.responder(packet, self.calls), f"request_{self.calls}"

    def close(self):
        self.closed = True


def tool_results(packet, name):
    return [json.loads(m["content"]) for m in packet["messages"] if m.get("name") == name]


def claim(eid, *, iid=None, quote=SOURCE, start=0):
    return {"statement": "The source reports timeout-related retries.", "kind": "source_report",
            "citations": [{"evidence_id": eid, "quote": quote, "start": start}],
            "memory_ids": [iid] if iid else [], "confidence": "high",
            "confidence_reason": "Directly reported in the cited passage.", "verification_note": "Checked the quoted source."}


def test_create_agent_memory_graph_flow_and_cli_artifacts(tmp_path):
    gp, mp, _ = inputs(tmp_path)
    selected = {}

    def respond(packet, step):
        if step == 1:
            return action("recall_memory", {"cue": "service timeout"})
        if step == 2:
            rows = tool_results(packet, "recall_memory")[-1]["results"]
            selected["item"] = next(r for r in rows if "KEP-6969" in r["record_ids"])
            selected["irrelevant"] = next(r for r in rows if "R2" in r["record_ids"])
            return action("inspect_memory", {"item_id": selected["item"]["item_id"]})
        if step == 3:
            selected["evidence"] = tool_results(packet, "inspect_memory")[-1]["evidence"][0]
            return action("get_evidence", {"evidence_ids": [selected["evidence"]["evidence_id"]]},
                          discarded_items=[{"item_id": selected["irrelevant"]["item_id"], "reason": "Display color does not explain timeout retries."}],
                          pin_evidence_ids=[selected["evidence"]["evidence_id"]])
        return action("DraftAnswer", {"claims": [claim(selected["evidence"]["evidence_id"], iid=selected["item"]["item_id"])]})

    client = ScriptedClient(respond)
    agent = OrganizationalAgent.from_artifacts(gp, mp, client_factory=lambda: client)
    result = agent.answer("What preceded the service outage?")
    assert result.status == "complete", result.model_dump()
    assert client.closed and client.calls == 4
    assert result.claims[0].source_mode == "memory_confirmed_by_graph"
    assert result.claims[0].record_ids == ["KEP-6969"]
    assert result.usage["data_tool_calls"] == 3
    assert result.usage["reported_new_call_tokens"]["output_tokens"] == 40
    assert any(e["kind"] == "item_discard" for e in result.trace)
    assert any(e["kind"] == "context_item_eviction" for e in result.trace)
    assert all(e["serialized_chars"] <= agent.config.max_request_chars for e in result.trace if e["kind"] == "context")
    out = tmp_path / "answer"
    save_result(result, out)
    assert {p.name for p in out.iterdir()} == {"answer.json", "answer.md", "trace.jsonl", "manifest.json"}
    assert json.loads((out / "answer.json").read_text())["claims"][0]["source_mode"] == "memory_confirmed_by_graph"


@pytest.mark.parametrize("change", ["incomplete", "pilot", "schema", "graph", "stale", "tamper"])
def test_artifact_failures_precede_provider(tmp_path, change):
    gp, mp, memory = inputs(tmp_path)
    if change == "incomplete":
        memory["build_metadata"]["status"] = "incomplete"
    elif change == "pilot":
        memory["build_metadata"]["scope"] = "pilot"
    elif change == "schema":
        memory["schema_version"] = "2.0"
    elif change == "tamper":
        memory["facts"][0]["statement"] = "Fabricated"
    elif change == "graph":
        atomic_json(gp, graph([edge("other", text="Different graph.")]))
    else:
        atomic_json(tmp_path / "build_progress.json", {"status": "incomplete"})
    atomic_json(mp, memory)
    with pytest.raises(ValueError):
        OrganizationalAgent.from_artifacts(gp, mp, client_factory=lambda: pytest.fail("Provider opened while loading"))


def test_scoped_fact_dedup_compressed_and_standalone_timeline(tmp_path):
    text = "On April 21, 2026 the service reported a data gap."
    edges = [edge("d1", "r1", record="R1", text=text), edge("d2", "r2", record="R2", text=text),
             edge("d3", "o1", target_type="outcome", relation="PRODUCES", record="R3", text=text)]

    def respond(task):
        out = accept_facts(task, "historical_statement")
        for j in out["episode_judgments"]:
            j.update(worth_remembering=False)
        return out

    gp, mp, m = inputs(tmp_path, edges, respond)
    tools = DatasetTools(Artifacts.load(gp, mp))
    rows = tools.recall_memory("service data gap", limit=20)["results"]
    assert len([r for r in rows if r["type"] == "fact"]) == 3
    assert not any(r["type"] == "episode" for r in rows)
    assert any(r["type"] == "episode" for r in tools.recall_memory("service data gap", include_compressed=True)["results"])
    assert tools.inspect_memory(m["episodes"][0]["id"])["retention"] == "compressed"
    assert tools.memory_timeline("o1")["dated"]["results"]
    assert tools.list_outcomes("o1")["total"] == 1
    assert tools.list_patterns()["available"] is False


def test_graph_paths_parallel_relations_directions_and_offsets(tmp_path):
    edges = [edge("d1", "r1", record="R1", text=SOURCE), edge("d1", "r1", record="R2", text="A second relationship."),
             edge("d2", "r1", record="R3", text="A third relationship."),
             edge("d2", "r1", record="R4", kind="inferred", text="An inferred cause, unverified.")]
    gp, mp, _ = inputs(tmp_path, edges)
    tools = DatasetTools(Artifacts.load(gp, mp))
    paths = tools.graph_paths("d1", "d2")
    assert paths["paths"] and paths["paths"][0]["edges"][-1]["traversed_forward"] is False
    assert not tools.graph_paths("d1", "d2", direction="forward")["paths"]
    assert tools.graph_neighborhood("r1")["total"] == 4
    assert any(e["provenance_kind"] == "inferred" for e in tools.graph_neighborhood("r1")["results"])
    eid = next(eid for eid, e in tools.index["evidence"].items() if e["record_id"] == "R1")
    piece = tools.get_evidence([eid], start=3, chars=15)["results"][0]
    assert piece["quote"] == SOURCE[3:18] and piece["next_start"] == 18
    assert tools.search_graph("R1", mode="records")["records"]["results"][0]["evidence_id"] == eid


def test_provenance_validation_unseen_altered_and_false_attribution(tmp_path):
    gp, mp, m = inputs(tmp_path)
    artifacts = Artifacts.load(gp, mp)
    tools = DatasetTools(artifacts)
    ledger = RunLedger(AgentConfig(), artifacts, "question")
    item = next(i for i in m["episodes"] if "KEP-6969" in i["record_ids"])
    eid = item["evidence_ids"][0]
    draft = DraftAnswer(claims=[claim(eid, iid=item["id"])])
    assert validate_answer(draft, ledger, tools.items)[1]
    memory_message = ToolMessage(name="inspect_memory", content=json.dumps(tools.inspect_memory(item["id"])), tool_call_id="a")
    ledger.present([memory_message])
    valid, errors = validate_answer(draft, ledger, tools.items)
    assert not errors and valid[0].source_mode == "memory"
    graph_message = ToolMessage(name="get_evidence", content=json.dumps(tools.get_evidence([eid])), tool_call_id="b")
    ledger.present([graph_message])
    assert validate_answer(draft, ledger, tools.items)[0][0].source_mode == "memory_confirmed_by_graph"
    for bad in [claim(eid, quote="invented"), claim("unknown"), claim(eid, start=1)]:
        assert validate_answer(DraftAnswer(claims=[bad]), ledger, tools.items)[1]


def test_one_citation_repair_excludes_invalid_claims(tmp_path):
    gp, mp, m = inputs(tmp_path)
    eid = next(e for e in m["evidence"] if m["evidence"][e]["record_id"] == "KEP-6969")

    def respond(packet, step):
        if step == 1:
            return action("get_evidence", {"evidence_ids": [eid]})
        return action("DraftAnswer", {"claims": [claim(eid, quote="Fabricated quotation")]})

    client = ScriptedClient(respond)
    result = OrganizationalAgent.from_artifacts(gp, mp, client_factory=lambda: client).answer("Why?")
    assert client.calls == 3 and result.status == "partial" and not result.claims
    assert result.validation_errors and len([e for e in result.trace if e["kind"] == "citation_repair"]) == 1
    assert [t["name"] for t in client.packets[-1]["tools"]] == ["DraftAnswer"]


@pytest.mark.parametrize("trigger", ["tool_budget", "no_gain", "model_budget"])
def test_retrieval_limits_force_structured_finish(tmp_path, trigger):
    gp, mp, _ = inputs(tmp_path)
    config = AgentConfig(max_tool_calls=1 if trigger == "tool_budget" else 10,
                         no_gain_limit=1 if trigger == "no_gain" else 10,
                         max_model_calls=3 if trigger == "model_budget" else 12)

    def respond(packet, step):
        names = [t["name"] for t in packet["tools"]]
        if names == ["DraftAnswer"]:
            return action("DraftAnswer", {"claims": [], "unanswered": ["No supporting evidence found."]})
        return action("search_graph", {"query": "nonexistentword"})

    client = ScriptedClient(respond)
    result = OrganizationalAgent.from_artifacts(gp, mp, config, client_factory=lambda: client).answer("Why?")
    assert result.status == "partial" and result.stop_reason and client.calls == 2


def test_malformed_action_and_bad_tool_arguments_are_bounded(tmp_path):
    gp, mp, _ = inputs(tmp_path)

    def respond(packet, step):
        if step == 1:
            return {"unexpected": True}
        if step == 2:
            return action("inspect_memory", {"item_id": "missing"})
        return action("DraftAnswer", {"claims": [], "unanswered": ["The requested item was absent."]})

    client = ScriptedClient(respond)
    result = OrganizationalAgent.from_artifacts(gp, mp, client_factory=lambda: client).answer("Question")
    assert client.calls == 3 and result.status == "partial"
    assert any(e["kind"] == "action_repair" for e in result.trace)
    assert next(e for e in result.trace if e["kind"] == "tool")["error"]


def test_provider_interruption_records_failure(tmp_path):
    gp, mp, _ = inputs(tmp_path)

    def fail(*_):
        raise ProviderUnavailable("Synthetic interruption")

    client = ScriptedClient(fail)
    result = OrganizationalAgent.from_artifacts(gp, mp, client_factory=lambda: client).answer("Question")
    assert result.status == "failed" and client.closed and result.usage["model_calls"] == 1


def test_context_eviction_keeps_pairs_pins_and_full_ledger(tmp_path):
    gp, mp, _ = inputs(tmp_path)
    a = Artifacts.load(gp, mp)
    ledger = RunLedger(AgentConfig(max_request_chars=12000), a, "question")
    eid = next(iter(a.index["evidence"]))
    messages = [SystemMessage(content="instructions"), HumanMessage(content="question")]
    for number in range(3):
        cid = str(number)
        messages += [AIMessage(content="inspect", tool_calls=[{"id": cid, "name": "get_evidence", "args": {"n": number}}]),
                     ToolMessage(content=json.dumps({"evidence_id": eid if number == 0 else f"e{number}", "quote": "x" * 5000,
                                 "start": 0, "end": 5000}), tool_call_id=cid, name="get_evidence")]
    ledger.pinned.add(eid)
    selected = ledger.project(messages, lambda rows: sum(len(str(m.content)) for m in rows))
    assert {m.tool_call_id for m in selected if isinstance(m, ToolMessage)} == {"0", "2"}
    assert len(messages) == 8 and any(e["kind"] == "context_eviction" for e in ledger.events)
    ledger.pinned |= {"e1", "e2"}
    with pytest.raises(ContextExceeded):
        ledger.project(messages, lambda rows: sum(len(str(m.content)) for m in rows))
    with pytest.raises(ValueError, match="exchange"):
        ledger.project(messages[:-1], lambda _: 10)


def test_larger_default_context_retains_pinned_evidence_and_still_enforces_cap(tmp_path):
    gp, mp, _ = inputs(tmp_path)
    artifacts = Artifacts.load(gp, mp)
    messages = [SystemMessage(content="instructions"), HumanMessage(content="question")]
    for number in range(3):
        cid = str(number)
        messages += [AIMessage(content="inspect", tool_calls=[{"id": cid, "name": "get_evidence", "args": {"n": number}}]),
                     ToolMessage(content=json.dumps({"evidence_id": f"e{number}", "quote": "x" * 20000,
                                 "start": 0, "end": 20000}), tool_call_id=cid, name="get_evidence")]
    def size(rows):
        return sum(len(str(m.content)) for m in rows)
    old = RunLedger(AgentConfig(max_request_chars=48000), artifacts, "question")
    old.pinned.update({"e0", "e1", "e2"})
    with pytest.raises(ContextExceeded):
        old.project(messages, size)
    ledger = RunLedger(AgentConfig(), artifacts, "question")
    ledger.pinned.update(old.pinned)
    selected = ledger.project(messages, size)
    assert {m.tool_call_id for m in selected if isinstance(m, ToolMessage)} == {"0", "1", "2"}
    assert 48000 < ledger.events[-1]["serialized_chars"] <= 200000
    assert not any(e["kind"] == "context_eviction" for e in ledger.events)
    # Pins plus the newest exchange remain protected, but cannot exceed the new cap.
    messages[-1] = messages[-1].model_copy(update={"content": "x" * 200000})
    with pytest.raises(ContextExceeded):
        ledger.project(messages, size)


def test_bind_tools_named_choice_and_no_native_tools(tmp_path):
    gp, mp, _ = inputs(tmp_path)
    a = Artifacts.load(gp, mp)
    model = JsonChatModel(client=ScriptedClient(lambda *_: None), ledger=RunLedger(AgentConfig(), a, "q"))
    bound = model.bind_tools(DatasetTools(a).registered(), tool_choice="get_evidence")
    assert [t["function"]["name"] for t in bound.bound_tools] == ["get_evidence"]
    with pytest.raises(ValueError):
        model.bind_tools([], tool_choice="unknown")


@pytest.mark.parametrize("empty", [True, False])
def test_completed_enriched_memory_and_stale_enrichment(tmp_path, empty):
    from org_memory.abstraction_run import run_abstraction
    from test_abstraction import QUESTIONS, synthesis_client
    gp, mp, memory = inputs(tmp_path)
    synth = synthesis_client(tmp_path, responder=(lambda _: {"proposals": []}) if empty else None)
    out = tmp_path / "enriched"
    enriched, _ = run_abstraction(memory, QUESTIONS, out, synth)
    assert enriched["abstraction_metadata"]["status"] == "complete"
    tools = DatasetTools(Artifacts.load(gp, out / "memory.json"))
    patterns = tools.list_patterns()
    assert patterns["available"] and bool(patterns["results"]) is not empty
    if not empty:
        details = tools.inspect_memory(patterns["results"][0]["item_id"])
        assert details["evidence"] and details["uncertainty"]
    checkpoint = json.loads((out / "checkpoint.json").read_text())
    checkpoint["run_id"] = "wrong"
    atomic_json(out / "checkpoint.json", checkpoint)
    with pytest.raises(ValueError, match="identity"):
        Artifacts.load(gp, out / "memory.json")


def test_timeline_standalone_without_episodes_and_uncertain_dates(tmp_path):
    def reject_episodes(task):
        out = accept_facts(task, "historical_statement")
        for j in out["episode_judgments"]:
            j.update(supported=False, worth_remembering=False)
        return out

    edges = [edge("d1", "r1", text="On April 21, 2026 a gap was reported."),
             edge("d2", "r1", record="R2", text="Pruning behavior changed, date unknown."),
             edge("d3", "r1", record="R3", text="On April 29 a backfill was requested."),
             edge("d4", "o1", record="R4", target_type="outcome", relation="PRODUCES", text="A restart was reported.")]
    gp, mp, m = inputs(tmp_path, edges, reject_episodes)
    assert not m["episodes"]
    tools = DatasetTools(Artifacts.load(gp, mp))
    timeline = tools.memory_timeline("r1")
    assert timeline["dated"]["total"] == 1 and timeline["unplaced"]["total"] == 2
    assert tools.list_outcomes("o1")["total"] == 1


def test_alias_expansion_preserves_identities(tmp_path):
    # Existing declared families derive from labels; no identity merges are introduced.
    edges = [edge("d1", "dev", text="A DocDB consistency gap was reported."),
             edge("d2", "prod", record="R2", text="DocumentDB needs validation.")]
    edges[0]["target"]["label"] = "DocDB dev"
    edges[1]["target"]["label"] = "DocumentDB production"
    gp, mp, _ = inputs(tmp_path, edges)
    tools = DatasetTools(Artifacts.load(gp, mp))
    result = tools.search_graph("docdb", mode="entities")
    assert {r["id"] for r in result["entities"]["results"]} == {"dev", "prod"}
    assert "documentdb" in result["expanded_query"]


def test_cache_replay_new_call_accounting_and_fresh_question_state(tmp_path):
    gp, mp, _ = inputs(tmp_path)
    requests = []

    def transport(endpoint, body):
        requests.append(body)
        response = action("DraftAnswer", {"claims": [], "unanswered": ["Fixture has not retrieved supporting evidence."]})
        return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(response)}}],
                "usage": {"prompt_tokens": 50, "completion_tokens": 10}}

    def factory():
        return CompatibleClient(ProviderConfig(api_key="fixture", cache_dir=str(tmp_path / "answers")), transport=transport)
    agent = OrganizationalAgent.from_artifacts(gp, mp, client_factory=factory)
    first = agent.answer("Same question")
    second = agent.answer("Same question")
    assert len(requests) == 1
    assert first.usage["reported_new_call_tokens"]["input_tokens"] == 50
    assert second.usage["cache_replays"] == 1 and not second.usage["reported_new_call_tokens"]
    assert first.usage["model_calls"] == second.usage["model_calls"] == 1


def test_context_counts_new_pages_as_progress(tmp_path):
    gp, mp, _ = inputs(tmp_path)
    a = Artifacts.load(gp, mp)
    ledger = RunLedger(AgentConfig(), a, "question")
    for i in range(4):
        ledger.tool_result("get_evidence", {}, str(i), {"results": [{"evidence_id": "same", "start": i*10,
                           "end": i*10+10, "quote": "x"*10}]}, 0)
    assert ledger.no_gain == 0


def test_admin_closure_and_inferred_only_do_not_support_factual_claims(tmp_path):
    def respond(task):
        result = accept_facts(task)
        for row in result["episode_judgments"]:
            row.update(supported=False, worth_remembering=False)
        return result

    gp, mp, _ = inputs(tmp_path, [edge(text="status: Done"), edge("d2", "r2", record="R2", kind="inferred", text="It recovered.")], respond)
    a = Artifacts.load(gp, mp)
    tools = DatasetTools(a)
    ledger = RunLedger(AgentConfig(), a, "question")
    for eid in tools.eids:
        result = tools.get_evidence([eid])
        ledger.present([ToolMessage(name="get_evidence", content=json.dumps(result), tool_call_id=eid)])
        quote = result["results"][0]["quote"]
        assert validate_answer(DraftAnswer(claims=[claim(eid, quote=quote)]), ledger, tools.items)[1]


def test_cli_persists_result_with_scripted_provider(tmp_path, monkeypatch, capsys):
    import run_task2
    gp, mp, _ = inputs(tmp_path)
    client = ScriptedClient(lambda *_: action("DraftAnswer", {"claims": [], "unanswered": ["No evidence retrieved."]}))
    monkeypatch.setattr(OrganizationalAgent, "_client", lambda _: client)
    out = tmp_path / "cli"
    assert run_task2.main(["--graph", str(gp), "--memory", str(mp), "--question", "Why?", "--output", str(out)]) == 2
    assert (out / "answer.json").exists() and "partial" in capsys.readouterr().out


def test_smoke_fixture_is_valid_without_hosted_calls(tmp_path):
    from scripts.smoke_agent import make_fixture
    gp, mp = make_fixture(tmp_path)
    artifacts = Artifacts.load(gp, mp)
    assert len(artifacts.memory["episodes"]) == 2
    assert {f["kind"] for f in artifacts.memory["facts"]} == {"historical_statement", "documented_routine"}


def test_interrupted_run_persists_append_only_trace(tmp_path):
    gp, mp, _ = inputs(tmp_path)

    def interrupt(*_):
        raise KeyboardInterrupt()

    client = ScriptedClient(interrupt)
    agent = OrganizationalAgent.from_artifacts(gp, mp, client_factory=lambda: client)
    trace_path = tmp_path / "stream.jsonl"
    result = agent.answer("Question", trace_path=trace_path)
    events = [json.loads(line) for line in trace_path.read_text().splitlines()]
    assert events == result.trace and result.status == "failed" and client.closed
    assert next(e for e in events if e["kind"] == "model_started")["status"] == "pending"
    assert next(e for e in events if e["kind"] == "model")["status"] == "interrupted"


def preview_inputs(tmp_path):
    from org_memory.abstraction_run import load_preview_memory, run_abstraction
    from test_abstraction import QUESTIONS, partial_memory, synthesis_client
    base = partial_memory(tmp_path)
    evidence = sorted(base["evidence"].values(), key=lambda e: min(e["raw_positions"]))
    gp, live = tmp_path / "graph.json", tmp_path / "live.json"
    atomic_json(gp, graph([e["raw_edge"] for e in evidence]))
    atomic_json(live, base)
    out = tmp_path / "preview"
    snapshot = load_preview_memory(live, out)
    questions = [{**QUESTIONS[0], "id": f"area{i}"} for i in range(4)]
    run_abstraction(snapshot, questions, out, synthesis_client(tmp_path), preview=True)
    return gp, out / "memory.preview.json", live


def test_preview_requires_opt_in_and_marks_answer_and_prompt(tmp_path):
    gp, mp, live = preview_inputs(tmp_path)
    with pytest.raises(ValueError, match="explicit --preview"):
        Artifacts.load(gp, mp)
    # The input is frozen: subsequent live checkpoint progress is irrelevant.
    live.write_text("the ongoing build has moved on")
    client = ScriptedClient(lambda *_: action("DraftAnswer", {"claims": [], "unanswered": ["Provisional check only."]}))
    agent = OrganizationalAgent.from_artifacts(gp, mp, preview=True, client_factory=lambda: client)
    result = agent.answer("What patterns are available?")
    assert result.provisional and "Provisional preview" in result.markdown()
    assert result.manifest["execution_scope"] == "preview"
    assert result.manifest["coverage"]["base_status"] == "incomplete"
    assert client.packets[0]["artifacts"]["coverage"]["processed_abstraction_packets"] == 3
    assert any(e["kind"] == "input_scope" for e in result.trace)
    assert agent.dataset.list_patterns()["available"]


@pytest.mark.parametrize("failure", ["unfinished", "snapshot", "checkpoint", "pattern"])
def test_preview_preserves_integrity_checks(tmp_path, failure):
    gp, mp, _ = preview_inputs(tmp_path)
    if failure == "snapshot":
        path = mp.parent / "preview_input.json"
        snapshot = json.loads(path.read_text())
        snapshot["base_fingerprint"] = "changed"
        atomic_json(path, snapshot)
    elif failure == "checkpoint":
        path = mp.parent / "checkpoint.json"
        checkpoint = json.loads(path.read_text())
        checkpoint["metadata"]["preview_status"] = "incomplete"
        atomic_json(path, checkpoint)
    else:
        memory = json.loads(mp.read_text())
        if failure == "unfinished":
            memory["abstraction_metadata"]["preview_status"] = "incomplete"
        else:
            memory["patterns"][0]["statement"] = "An invented pattern."
        atomic_json(mp, memory)
    with pytest.raises(ValueError):
        Artifacts.load(gp, mp, preview=True)


def test_validation_only_cli_uses_no_provider(tmp_path, monkeypatch, capsys):
    import run_task2
    gp, mp, _ = preview_inputs(tmp_path)
    monkeypatch.setattr(OrganizationalAgent, "_client", lambda _: pytest.fail("Validation must not open a provider"))
    assert run_task2.main(["--graph", str(gp), "--memory", str(mp), "--preview", "--validate-only"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "validated" and result["model_calls"] == 0
    assert result["execution_scope"] == "preview" and result["counts"]["patterns"] > 0


def test_preview_flag_does_not_admit_arbitrary_incomplete_memory(tmp_path):
    gp, mp, memory = inputs(tmp_path)
    with pytest.raises(ValueError, match="finished abstraction preview"):
        Artifacts.load(gp, mp, preview=True)
    memory["build_metadata"]["status"] = "incomplete"
    atomic_json(mp, memory)
    with pytest.raises(ValueError, match="finished abstraction preview"):
        Artifacts.load(gp, mp, preview=True)
