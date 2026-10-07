import asyncio
import copy
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from org_memory import BuildConfig, build_memory, validate_memory
from org_memory.codex_provider import CodexClient, CodexProviderConfig, REVIEW_SETTINGS
from org_memory.hosted import BudgetExceeded, ProviderUnavailable, create_client, default_output_dir, obj
from org_memory.review import ReviewIncomplete
from test_candidates import edge, graph
from test_review import response_for


class Dump:
    def __init__(self, data):
        self.data = data

    def model_dump(self, **kwargs):
        return self.data


class FakeSDK:
    """Fake the verified Python SDK boundary, including its async turn handles."""
    Sandbox = NS(read_only="read-only")
    ApprovalMode = NS(deny_all="deny-all")
    CodexConfig = NS
    types = NS(ReasoningEffort=str, ConfigReadResponse=object)

    def __init__(self, responder=None, *, account="chatgpt", fail=None, hang=False):
        self.responder = responder or (lambda task: {"value": "fixture"})
        self.account_type = account
        self.fail = fail
        self.hang = hang
        self.sessions = []
        self.threads = []
        self.turns = []
        self.closed = 0
        self.interrupted = 0

    def AsyncCodex(self, config):
        owner = self
        self.sessions.append(config)

        class Session:
            async def __aenter__(self):
                return self

            async def account(self):
                if owner.fail:
                    raise owner.fail
                return NS(account=NS(root=NS(type=owner.account_type)) if owner.account_type else None)

            async def models(self, *, include_hidden):
                return NS(data=[NS(model=m, supported_reasoning_efforts=[NS(reasoning_effort="medium"), NS(reasoning_effort="high")])
                                for m in ("gpt-5.6-luna", "gpt-6-sol")])

            @property
            def _client(self):
                return self

            async def request(self, method, params, *, response_model):
                assert method == "config/read"
                return NS(config=Dump({"mcp_servers": {"external": {"enabled": True}}}))

            async def thread_start(self, **kwargs):
                owner.threads.append(copy.deepcopy(kwargs))
                tid = f"thread-{len(owner.threads)}"

                class Thread:
                    id = tid

                    async def turn(self, text, **options):
                        owner.turns.append((json.loads(text)["task"], options))
                        number = len(owner.turns)

                        class Turn:
                            id = f"turn-{number}"

                            async def run(self):
                                if owner.hang:
                                    await asyncio.Event().wait()
                                output = owner.responder(json.loads(text)["task"])
                                if isinstance(output, BaseException):
                                    raise output
                                if isinstance(output, NS):
                                    return output
                                return NS(status="completed", error=None, id=self.id,
                                          final_response=json.dumps(output), items=[],
                                          usage=NS(total=Dump({"input_tokens": 10, "output_tokens": 5,
                                                               "cached_input_tokens": 2})))

                            async def interrupt(self):
                                owner.interrupted += 1

                        return Turn()

                return Thread()

            async def close(self):
                owner.closed += 1

        return Session()


def make_client(tmp_path, sdk=None, **kwargs):
    sdk = sdk or FakeSDK()
    return CodexClient(CodexProviderConfig(cache_dir=str(tmp_path), **kwargs), sdk_loader=lambda: sdk), sdk


def test_structured_turn_is_isolated_and_reuses_connection(tmp_path):
    client, sdk = make_client(tmp_path)
    schema = obj({"value": {"type": "string"}})
    with client:
        assert client.json("Review evidence only", {"x": 1}, schema, "episode_review")[0] == {"value": "fixture"}
        client.json("Review patterns", {"x": 2}, schema, "pattern_synthesis")
        assert client.calls == 2 and len(sdk.sessions) == 1 and len(sdk.threads) == 2
        assert sdk.threads[0]["developer_instructions"] == "Review evidence only"
        for thread in sdk.threads:
            assert thread["model"] == "gpt-5.6-luna" and thread["ephemeral"]
            assert thread["sandbox"] == "read-only" and thread["approval_mode"] == "deny-all"
            assert thread["config"]["mcp_servers"]["external"]["enabled"] is False
            assert all(thread["config"][key] == value for key, value in REVIEW_SETTINGS.items())
            assert Path(thread["cwd"]).is_dir()
        assert sdk.turns[0][1]["output_schema"] == schema
        assert sdk.turns[0][1]["effort"] == "medium"
        assert sdk.turns[0][1]["turn_service_tier"] == "default"
    assert sdk.closed == 1 and not client._worker.is_alive()
    assert not Path(sdk.threads[0]["cwd"]).exists()


def test_cache_works_without_sdk_or_budget_and_records_usage(tmp_path):
    schema = obj({})
    client, sdk = make_client(tmp_path, max_calls=1)
    with client:
        output, key = client.json("Review", {}, schema, "episode_review")
        assert client.trace[-1]["usage"]["input_tokens"] == 10
        assert client.trace[-1]["estimated_original_cost_usd"] is None
        assert client.json("Review", {}, schema, "episode_review") == (output, key)
        assert client.calls == 1 and client.trace[-1]["cached"]
        with pytest.raises(BudgetExceeded):
            client.json("Review", {"other": 1}, schema, "episode_review")
    def unavailable():
        raise AssertionError("Cache-only resume must not load the SDK")
    with CodexClient(replace(client.config, max_calls=0), sdk_loader=unavailable) as replay:
        assert replay.json("Review", {}, schema, "episode_review") == (output, key)
        assert replay.calls == 0 and replay._loop is None


@pytest.mark.parametrize("change", ["model", "reasoning", "system", "packet", "schema"])
def test_cache_separates_configuration_and_contract(tmp_path, change):
    with make_client(tmp_path)[0] as first:
        _, first_key = first.json("Review", {}, obj({}), "fixture")
    options = {"model": "gpt-6-sol"} if change == "model" else {"reasoning_effort": "high"} if change == "reasoning" else {}
    with make_client(tmp_path, **options)[0] as second:
        _, key = second.json("Changed" if change == "system" else "Review",
                             {"changed": True} if change == "packet" else {},
                             obj({"changed": {"type": "string"}}) if change == "schema" else obj({}), "fixture")
        assert key != first_key and second.calls == 1


@pytest.mark.parametrize("account", [None, "apiKey"])
def test_preflight_rejects_non_subscription_auth_without_turns(tmp_path, account):
    client, sdk = make_client(tmp_path, FakeSDK(account=account))
    with client, pytest.raises(ProviderUnavailable, match="ChatGPT sign-in"):
        client.json("Review", {}, obj({}), "fixture")
    assert client.calls == 0 and not sdk.turns and sdk.closed == 1


@pytest.mark.parametrize("settings", [{"model": "unavailable"}, {"reasoning_effort": "low"}])
def test_model_and_effort_preflight(tmp_path, settings):
    client, sdk = make_client(tmp_path, **settings)
    with client, pytest.raises(ProviderUnavailable):
        client.json("Review", {}, obj({}), "fixture")
    assert not sdk.turns and client.calls == 0


def test_timeout_interrupts_turn_and_closes_worker(tmp_path):
    client, sdk = make_client(tmp_path, FakeSDK(hang=True), timeout=0.05)
    with client, pytest.raises(ProviderUnavailable, match="timed out"):
        client.json("Review", {}, obj({}), "fixture")
    assert sdk.interrupted == 1 and sdk.closed == 1
    assert client.calls == 1 and not client._worker.is_alive()
    assert client.trace[-1]["status"] == "failed"


def test_caller_interruption_cancels_and_closes_connection(tmp_path, monkeypatch):
    import threading
    entered = threading.Event()
    sdk = FakeSDK(hang=True)
    original_factory = sdk.AsyncCodex
    def session_factory(config):
        session = original_factory(config)
        original_start = session.thread_start
        async def start(**kwargs):
            thread = await original_start(**kwargs)
            original_turn = thread.turn
            async def turn(*a, **kw):
                handle = await original_turn(*a, **kw)
                entered.set()
                return handle
            thread.turn = turn
            return thread
        session.thread_start = start
        return session
    sdk.AsyncCodex = session_factory
    submit = asyncio.run_coroutine_threadsafe
    first = True
    def interrupt_result(coro, loop):
        nonlocal first
        future = submit(coro, loop)
        if first:
            first = False
            def interrupted(*a, **kw):
                assert entered.wait(2)
                raise KeyboardInterrupt
            future.result = interrupted
        return future
    monkeypatch.setattr(asyncio, "run_coroutine_threadsafe", interrupt_result)
    client, _ = make_client(tmp_path, sdk)
    with pytest.raises(KeyboardInterrupt):
        client.json("Review", {}, obj({}), "fixture")
    assert sdk.closed == 1 and sdk.interrupted == 1 and not client._worker.is_alive()
    assert client.trace[-1]["error_type"] == "KeyboardInterrupt"


def test_missing_sdk_is_terminal_with_installation_guidance(tmp_path, monkeypatch):
    import org_memory.codex_provider as provider
    def unavailable(*_):
        raise ImportError("private details")
    monkeypatch.setattr(provider.importlib, "import_module", unavailable)
    with CodexClient(CodexProviderConfig(cache_dir=str(tmp_path))) as client:
        with pytest.raises(ProviderUnavailable, match="requirements.txt"):
            client.json("Review", {}, obj({}), "fixture")
        assert client.calls == 0 and len(client.trace) == 1


def test_sdk_errors_are_sanitized_and_checkpoint_without_splitting(tmp_path):
    client, sdk = make_client(tmp_path, FakeSDK(fail=RuntimeError("token=DO-NOT-LOG")))
    with client, pytest.raises(ReviewIncomplete) as result:
        build_memory(graph([edge(), edge("d2", record="R2")]), BuildConfig(mode="hosted"), client=client)
    memory = result.value.memory
    assert not memory["episodes"] and memory["build_metadata"]["status"] == "incomplete"
    assert len(client.trace) == 1 and len(sdk.sessions) == 1
    assert "DO-NOT-LOG" not in str(result.value) + json.dumps(memory) + json.dumps(client.trace)


@pytest.mark.parametrize("content", [None, "", "{", "[]"])
def test_empty_malformed_or_nonobject_output_not_cached(tmp_path, content):
    sdk = FakeSDK(lambda _: NS(status="completed", error=None, id="t", final_response=content, usage=None))
    with make_client(tmp_path, sdk)[0] as client, pytest.raises(ValueError):
        client.json("Review", {}, obj({}), "fixture")
    assert not list(tmp_path.rglob("*.json"))


@pytest.mark.parametrize("status", ["failed", "interrupted"])
def test_failed_turn_is_terminal_and_not_cached(tmp_path, status):
    sdk = FakeSDK(lambda _: NS(status=status, error=NS(message="private token")))
    with make_client(tmp_path, sdk)[0] as client, pytest.raises(ProviderUnavailable):
        client.json("Review", {}, obj({}), "fixture")
    assert client.calls == 1 and "private token" not in json.dumps(client.trace)
    assert not list(tmp_path.rglob("*.json"))


def test_invalid_judgment_is_corrected_and_validated_cache_resumes(tmp_path):
    def respond(task):
        out = response_for(task)
        if "validation_feedback" not in task:
            out["episode_judgments"][0]["supported"] = "invalid boolean"
        return out
    config = BuildConfig(mode="hosted", llm_max_patterns=0)
    client, sdk = make_client(tmp_path, FakeSDK(respond))
    with client:
        memory = build_memory(graph([edge()]), config, client=client)
        assert client.calls == 2 and len(memory["episodes"]) == 1
        assert validate_memory(memory)["passed"]
        assert memory["build_metadata"]["hosted_provider"] == "codex"
        client.call_limit = 0
        resumed = build_memory(graph([edge()]), config, client=client)
        assert client.calls == 2 and resumed["episodes"] == memory["episodes"]


def test_pattern_stage_is_deferred_without_calling_provider(tmp_path):
    def respond(task):
        return response_for(task) if task["operation"] == "judge_fixed_memory" else NS(status="failed", error=NS(message="quota"))
    client, sdk = make_client(tmp_path, FakeSDK(respond))
    with client:
        memory = build_memory(graph([edge(), edge("d2", record="R2", text="Second outage.")]),
                              BuildConfig(mode="hosted", llm_max_patterns=2), client=client)
    assert len(memory["episodes"]) == 2 and not memory["patterns"]
    assert client.calls == 1 and memory["build_metadata"]["pattern_analysis"]["status"] == "deferred"


def test_factory_defaults_overrides_dense_and_safe_output(tmp_path, monkeypatch):
    for key in ("MEMORY_MODEL", "MEMORY_TIMEOUT_SECONDS", "MEMORY_MAX_CALLS"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("MEMORY_PROVIDER", "codex")
    with create_client() as client:
        assert client.config.model == "gpt-5.6-luna" and client.config.timeout == 300
        assert default_output_dir("hosted", client) == Path("artifacts/hosted/codex/gpt-5.6-luna/judge-v1")
    monkeypatch.setenv("MEMORY_MODEL", "gpt-5.6-luna")
    monkeypatch.setenv("MEMORY_MAX_CALLS", "1")
    with create_client(model="gpt-6-sol", max_calls=3) as client:
        assert client.config.model == "gpt-6-sol" and client.config.max_calls == 3
    with pytest.raises(ValueError, match="embeddings"):
        create_client(dense=True)
    with pytest.raises(ValueError, match="PROVIDER"):
        create_client("invalid")
    with create_client(model="../../elsewhere") as client:
        assert default_output_dir("hosted", client).parent.parent == Path("artifacts/hosted/codex")


def test_sync_facade_runs_inside_notebook_event_loop(tmp_path):
    async def notebook_cell():
        with make_client(tmp_path)[0] as client:
            return client.json("Review", {}, obj({}), "fixture")[0]
    assert asyncio.run(notebook_cell()) == {"value": "fixture"}


def test_cli_early_dense_rejection_and_terminal_checkpoint(tmp_path, monkeypatch):
    import run_task1
    monkeypatch.setattr(sys, "argv", ["run_task1.py", "--mode", "hosted", "--provider", "codex", "--dense", "--input", "missing"])
    with pytest.raises(SystemExit) as error:
        run_task1.main()
    assert error.value.code == 2
    source = tmp_path / "input.json"
    source.write_text(json.dumps(graph([edge()])))
    client, sdk = make_client(tmp_path / "cache", FakeSDK(account=None))
    monkeypatch.setattr(run_task1, "create_client", lambda *a, **kw: client)
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["run_task1.py", "--mode", "hosted", "--provider", "codex",
                                     "--input", str(source), "--output", str(out)])
    assert run_task1.main() == 2
    assert (out / "memory.incomplete.json").exists() and not (out / "memory.json").exists()
    assert sdk.closed == 1 and client._closed


def test_offline_import_does_not_load_sdk():
    subprocess.run([sys.executable, "-c", "import run_task1, sys; assert 'openai_codex' not in sys.modules"], check=True)


def test_smoke_runner_checks_requirement_and_zero_turn_replay(tmp_path, monkeypatch):
    from scripts import smoke_codex
    def respond(task):
        out = response_for(task)
        excerpts = {e["id"]: e["text"] for e in task["excerpts"]}
        for p in task["fact_proposals"]:
            if "runbook" in excerpts[p["excerpt_id"]]:
                j = next(j for j in out["fact_judgments"] if j["id"] == p["id"])
                j.update(is_fact=True, kind="requirement", reason="Runbook requirement.")
        return out
    client, sdk = make_client(tmp_path / "cache", FakeSDK(respond), max_calls=3)
    monkeypatch.setattr(smoke_codex, "create_client", lambda *a, **kw: client)
    monkeypatch.setattr(sys, "argv", ["smoke_codex.py", "--output", str(tmp_path / "smoke")])
    assert smoke_codex.main() == 0
    summary = json.loads((tmp_path / "smoke/smoke_result.json").read_text())
    assert summary["facts"] == 1 and summary["new_turns"] == 1 and summary["replay_new_turns"] == 0


def test_installed_sdk_contract():
    sdk = pytest.importorskip("openai_codex")
    from inspect import signature
    from openai_codex.generated.v2_all import ConfigReadResponse
    from openai_codex.types import ReasoningEffort
    assert ConfigReadResponse and ReasoningEffort("medium")
    assert sdk.ApprovalMode.deny_all and sdk.Sandbox.read_only
    assert {"codex_bin", "cwd", "config_overrides"} <= set(signature(sdk.CodexConfig).parameters)
    assert {"base_instructions", "config", "ephemeral"} <= set(signature(sdk.AsyncCodex.thread_start).parameters)
    assert {"output_schema", "turn_service_tier"} <= set(signature(sdk.AsyncThread.turn).parameters)
