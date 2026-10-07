"""Subscription-backed JSON review through the optional official Python SDK.

The synchronous facade owns an async loop, so CLI and Jupyter callers use the
same contract. Authentication remains in Codex; no tokens are read or copied.
"""
from __future__ import annotations

import asyncio
import importlib
import json
import math
import os
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from .evidence import stable_id
from .hosted import BudgetExceeded, ProviderUnavailable


ADAPTER_VERSION = 1
# Applied at startup AND per thread, without editing the user's Codex config.
REVIEW_SETTINGS = {
    "forced_login_method": "chatgpt",
    "model_provider": "openai",
    "approval_policy": "never",
    "sandbox_mode": "read-only",
    "web_search": "disabled",
    "agents.enabled": False,
    "skills.include_instructions": False,
    "include_apps_instructions": False,
    "notify": [],
    **{f"features.{name}": False for name in (
        "shell_tool", "unified_exec", "apply_patch_freeform", "code_mode",
        "code_mode_host", "js_repl", "apps", "plugins", "remote_plugin",
        "browser_use", "computer_use", "image_generation", "view_image",
        "multi_agent", "multi_agent_v2", "memory_tool", "memories", "hooks",
        "codex_hooks", "plugin_hooks", "skill_search", "tool_search", "tool_suggest",
        "fast_mode", "ultrafast_mode", "unbounded_connection_retries",
    )},
}


@dataclass(frozen=True)
class CodexProviderConfig:
    model: str = "gpt-5.6-luna"
    reasoning_effort: str = "medium"
    timeout: float = 300.0
    max_calls: int = 200
    cache_dir: str = "artifacts/cache"
    codex_bin: str | None = None

    def __post_init__(self):
        if not self.model.strip():
            raise ValueError("Codex model must be nonempty")
        if self.reasoning_effort not in {"low", "medium", "high", "xhigh", "max"}:
            raise ValueError("MEMORY_CODEX_REASONING_EFFORT must be low, medium, high, xhigh or max")
        if not math.isfinite(self.timeout) or self.timeout <= 0 or self.max_calls < 0:
            raise ValueError("Codex timeout must be positive and finite; call limit must be nonnegative")

    @classmethod
    def from_env(cls):
        return cls(
            model=os.getenv("MEMORY_MODEL") or cls.model,
            reasoning_effort=os.getenv("MEMORY_CODEX_REASONING_EFFORT") or cls.reasoning_effort,
            timeout=float(os.getenv("MEMORY_TIMEOUT_SECONDS") or "300"),
            max_calls=int(os.getenv("MEMORY_MAX_CALLS", "200")),
            cache_dir=os.getenv("MEMORY_CACHE_DIR") or cls.cache_dir,
            codex_bin=os.getenv("MEMORY_CODEX_BIN") or None,
        )


def _load_sdk():
    try:
        return importlib.import_module("openai_codex")
    except ImportError:
        raise ProviderUnavailable(
            "Codex SDK is unavailable. Install it with python -m pip install -r requirements.txt."
        ) from None


def _value(value):
    return getattr(value, "value", value)


class CodexClient:
    provider = "codex"

    def __init__(self, config, *, sdk_loader=_load_sdk):
        self.config = config
        self.calls = 0
        self.call_limit = config.max_calls
        self.trace = []
        self._sdk_loader = sdk_loader
        self._sdk = self._session = self._turn = None
        self._thread_id = self._turn_id = None
        self._loop = self._worker = self._workdir = None
        self._closed = False
        self._thread_settings = dict(REVIEW_SETTINGS)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _start_worker(self):
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            self._worker = threading.Thread(target=self._loop.run_forever, name="memory-codex", daemon=True)
            self._worker.start()

    async def _connect(self):
        if self._session is not None:
            return
        self._sdk = self._sdk_loader()
        self._workdir = tempfile.TemporaryDirectory(prefix="memory-codex-")
        sdk_config = self._sdk.CodexConfig(
            codex_bin=self.config.codex_bin,
            cwd=self._workdir.name,
            config_overrides=tuple(f"{key}={json.dumps(value)}" for key, value in REVIEW_SETTINGS.items()),
        )
        self._session = self._sdk.AsyncCodex(sdk_config)
        await self._session.__aenter__()
        account = (await self._session.account()).account
        if account is None or getattr(getattr(account, "root", account), "type", None) != "chatgpt":
            raise ProviderUnavailable("Codex review requires ChatGPT sign-in. Run codex login, then retry.")
        models = (await self._session.models(include_hidden=True)).data
        model = next((m for m in models if m.model == self.config.model), None)
        if model is None:
            raise ProviderUnavailable("Selected Codex model is not in the account's catalog; choose an available MEMORY_MODEL.")
        efforts = {_value(e.reasoning_effort) for e in model.supported_reasoning_efforts}
        if self.config.reasoning_effort not in efforts:
            raise ProviderUnavailable("Selected reasoning effort is not supported by the Codex model.")

        # The high-level SDK has no config-read wrapper. This isolated use of its
        # typed RPC client enumerates the *effective* servers, including profiles.
        # An empty mcp_servers table alone would merge with inherited settings.
        # ConfigReadResponse belongs to the generated RPC models; the public
        # types facade does not export it in SDK 0.160.1.
        types = importlib.import_module("openai_codex.generated.v2_all") if self._sdk_loader is _load_sdk else self._sdk.types
        effective = await self._session._client.request(
            "config/read", {"cwd": self._workdir.name, "includeLayers": False},
            response_model=types.ConfigReadResponse,
        )
        servers = effective.config.model_dump().get("mcp_servers") or {}
        self._thread_settings["mcp_servers"] = {name: {"enabled": False} for name in servers}

    async def _stop_session(self):
        if self._turn is not None:
            turn, self._turn = self._turn, None
            try:
                await asyncio.wait_for(turn.interrupt(), timeout=2)
            except Exception:
                pass
        if self._session is not None:
            session, self._session = self._session, None
            try:
                await asyncio.wait_for(session.close(), timeout=5)
            except Exception:
                pass
        if self._workdir is not None:
            self._workdir.cleanup()
            self._workdir = None

    async def _review(self, system, packet, schema):
        await self._connect()
        thread = await self._session.thread_start(
            model=self.config.model, model_provider="openai", ephemeral=True,
            cwd=self._workdir.name, sandbox=self._sdk.Sandbox.read_only,
            approval_mode=self._sdk.ApprovalMode.deny_all,
            base_instructions="You review supplied evidence and return structured JSON. Do not use tools.",
            developer_instructions=system,
            config=self._thread_settings,
        )
        self._thread_id = thread.id
        # Only an attempted model turn consumes the review-call budget.
        self.calls += 1
        types = importlib.import_module("openai_codex.types") if self._sdk_loader is _load_sdk else self._sdk.types
        self._turn = await thread.turn(
            json.dumps({"task": packet}, ensure_ascii=False),
            output_schema=schema, effort=types.ReasoningEffort(self.config.reasoning_effort),
            approval_mode=self._sdk.ApprovalMode.deny_all, sandbox=self._sdk.Sandbox.read_only,
            turn_service_tier="default",
        )
        self._turn_id = self._turn.id
        result = await self._turn.run()
        self._turn = None
        if _value(result.status) != "completed" or result.error is not None:
            raise ProviderUnavailable(
                "Codex turn did not complete. Check login, model access, subscription limits and connectivity, then rerun."
            )
        # Do not persist raw SDK events, errors, account objects or tool output.
        usage = result.usage.total.model_dump(mode="json") if result.usage is not None else {}
        return {"content": result.final_response, "usage": usage,
                "thread_id": thread.id, "turn_id": result.id}

    async def _request(self, system, packet, schema):
        try:
            return await asyncio.wait_for(self._review(system, packet, schema), timeout=self.config.timeout)
        except BaseException as exc:
            await self._stop_session()
            if isinstance(exc, (asyncio.CancelledError, ProviderUnavailable)):
                raise
            if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
                raise ProviderUnavailable("Codex review timed out; the turn was cancelled. Rerun to resume cached work.") from None
            if isinstance(exc, Exception):
                raise ProviderUnavailable(
                    "Codex SDK connection failed. Check its installation, runtime, login and network locally."
                ) from None
            raise

    def json(self, system, packet, schema, purpose):
        if self._closed:
            raise ProviderUnavailable("Codex client is closed; create a new client to resume.")
        request = {"adapter_version": ADAPTER_VERSION, "provider": self.provider,
                   "model": self.config.model, "reasoning_effort": self.config.reasoning_effort,
                   "system": system, "packet": packet, "schema": schema}
        key = stable_id("request", request)
        path = Path(self.config.cache_dir) / "codex" / f"{key}.json"
        cached, started = path.exists(), time.monotonic()
        self._thread_id = self._turn_id = None
        entry = {"request_id": key, "purpose": purpose, "provider": self.provider,
                 "endpoint": "codex/turn", "model": self.config.model,
                 "reasoning_effort": self.config.reasoning_effort, "cached": cached,
                 "estimated_original_cost_usd": None,
                 "estimated_this_run_cost_usd": 0.0 if cached else None,
                 "cache_file": str(path)}
        future = None
        try:
            if cached:
                envelope = json.loads(path.read_text())
                if envelope.get("request") != request:
                    raise ValueError("Codex cache request does not match its key")
                result = envelope["response"]
            else:
                if self.calls >= min(self.config.max_calls, self.call_limit):
                    raise BudgetExceeded("Codex review-turn budget exhausted; cached calls remain available.")
                self._start_worker()
                future = asyncio.run_coroutine_threadsafe(self._request(system, packet, schema), self._loop)
                result = future.result()
            entry.update({k: result.get(k) for k in ("usage", "thread_id", "turn_id")})
            content = result.get("content")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Codex returned no structured content")
            try:
                output = json.loads(content)
            except json.JSONDecodeError:
                raise ValueError("Codex response is not complete JSON") from None
            if not isinstance(output, dict):
                raise ValueError("Codex response must be a JSON object")
            if not cached:
                path.parent.mkdir(parents=True, exist_ok=True)
                # Same-directory replace avoids leaving a partial cache on interruption.
                with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
                    temporary = Path(stream.name)
                    try:
                        json.dump({"request": request, "response": result}, stream, ensure_ascii=False)
                        stream.close()
                        temporary.replace(path)
                    finally:
                        temporary.unlink(missing_ok=True)
            entry["status"] = "completed"
            return output, key
        except BaseException as exc:
            entry.update(status="failed", error_type=type(exc).__name__)
            if future is not None and not future.done():
                future.cancel()
                self.close()
            raise
        finally:
            entry.setdefault("thread_id", self._thread_id)
            entry.setdefault("turn_id", self._turn_id)
            entry["latency_seconds"] = round(time.monotonic() - started, 4)
            self.trace.append(entry)

    def embed(self, texts):
        raise ValueError("Codex does not provide embeddings; disable dense recall.")

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._loop is not None:
            try:
                asyncio.run_coroutine_threadsafe(self._stop_session(), self._loop).result(timeout=10)
            finally:
                self._loop.call_soon_threadsafe(self._loop.stop)
                self._worker.join(timeout=10)
                if not self._worker.is_alive():
                    self._loop.close()
