"""OpenAI-compatible JSON calls, explicit configuration, cache, and audit trail.

Uses the REST contract via the standard library so the offline notebook needs
no SDK installation. No request is made merely by importing or constructing.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, replace
from pathlib import Path
from urllib.parse import urlsplit

from .evidence import stable_id


def load_env(path=".env"):
    """Read literal KEY=VALUE entries without shell expansion or execution."""
    path = Path(path)
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError("Expected KEY=VALUE in .env")
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if value[:1] in {"'", '"'} and value[-1:] == value[:1]:
            value = value[1:-1]
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class ProviderConfig:
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4.1-mini-2025-04-14"
    api_key: str = field(default="", repr=False)
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer"
    embedding_model: str = "text-embedding-3-small"
    response_format: str = "json_schema"
    reasoning_effort: str | None = None
    timeout: float = 60.0
    max_calls: int = 200
    cache_dir: str = "artifacts/cache"
    input_usd_per_million: float | None = None
    output_usd_per_million: float | None = None

    @classmethod
    def from_env(cls):
        return cls(
            base_url=os.getenv("MEMORY_BASE_URL", cls.base_url),
            model=os.getenv("MEMORY_MODEL") or cls.model,
            api_key=os.getenv("MEMORY_API_KEY") or os.getenv("OPENAI_API_KEY", ""),
            auth_header=os.getenv("MEMORY_AUTH_HEADER", cls.auth_header),
            auth_prefix=os.getenv("MEMORY_AUTH_PREFIX", cls.auth_prefix),
            embedding_model=os.getenv("MEMORY_EMBEDDING_MODEL", cls.embedding_model),
            response_format=os.getenv("MEMORY_RESPONSE_FORMAT", cls.response_format),
            timeout=float(os.getenv("MEMORY_TIMEOUT_SECONDS") or "60"),
            max_calls=int(os.getenv("MEMORY_MAX_CALLS", "200")),
            cache_dir=os.getenv("MEMORY_CACHE_DIR", cls.cache_dir),
            input_usd_per_million=_optional_float("MEMORY_INPUT_USD_PER_MILLION"),
            output_usd_per_million=_optional_float("MEMORY_OUTPUT_USD_PER_MILLION"),
        )


def _optional_float(name):
    return float(os.environ[name]) if os.getenv(name) else None


class BudgetExceeded(RuntimeError):
    pass


class ProviderUnavailable(RuntimeError):
    """Terminal, sanitized provider failure; splitting packets cannot fix it."""


def create_client(provider=None, *, model=None, max_calls=None, dense=False):
    """Select transport without importing the optional SDK on other paths."""
    provider = provider or os.getenv("MEMORY_PROVIDER") or "compatible"
    if provider not in {"compatible", "codex"}:
        raise ValueError("MEMORY_PROVIDER must be compatible or codex")
    if provider == "codex":
        if dense:
            raise ValueError("Codex does not provide embeddings; disable dense recall or use the compatible provider.")
        from .codex_provider import CodexClient, CodexProviderConfig
        config = CodexProviderConfig.from_env()
        client_type = CodexClient
    else:
        config = ProviderConfig.from_env()
        client_type = CompatibleClient
    if model is not None:
        config = replace(config, model=model)
    if max_calls is not None:
        config = replace(config, max_calls=max_calls)
    return client_type(config)


def default_output_dir(mode, client=None):
    if mode == "hosted" and getattr(client, "provider", None) == "codex":
        # A configurable model must never become an absolute or traversing path.
        from urllib.parse import quote
        name = quote(client.config.model, safe="-_.")
        if name in {".", ".."}:
            name = name.replace(".", "%2E")
        return Path("artifacts/hosted/codex") / name / "judge-v1"
    if mode == "hosted":
        return Path("artifacts/hosted/judge-v1")
    return Path("artifacts") / mode


class CompatibleClient:
    provider = "compatible"

    def close(self):
        """Parity with the managed Codex connection; REST has no open session."""

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def __init__(self, config, *, transport=None):
        self.config = config
        if not config.api_key:
            raise ValueError("Set MEMORY_API_KEY or OPENAI_API_KEY locally before choosing hosted mode.")
        url = urlsplit(config.base_url)
        if url.scheme not in {"https", "http"} or not url.netloc or url.username or url.password or url.query:
            raise ValueError("base_url must be an HTTP(S) API root without embedded credentials or query parameters")
        if config.response_format not in {"json_schema", "json_object"}:
            raise ValueError("MEMORY_RESPONSE_FORMAT must be json_schema or json_object")
        self.transport = transport or self._transport
        self.calls = 0
        self.call_limit = config.max_calls
        self.trace = []

    def _transport(self, endpoint, payload):
        value = f"{self.config.auth_prefix} {self.config.api_key}".strip()
        request = urllib.request.Request(
            self.config.base_url.rstrip("/") + endpoint,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", self.config.auth_header: value}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            # Do not surface echoed credentials or server response bodies.
            raise RuntimeError(f"Hosted API returned HTTP {exc.code}; check endpoint, model and authentication locally.") from None
        except urllib.error.URLError:
            raise RuntimeError("Hosted API could not be reached; check local network and endpoint settings.") from None

    def _call(self, endpoint, payload, purpose):
        key = stable_id("request", {"base_url": self.config.base_url, "endpoint": endpoint, "payload": payload})
        path = Path(self.config.cache_dir) / f"{key}.json"
        started = time.monotonic()
        cached = path.exists()
        if cached:
            result = json.loads(path.read_text())["response"]
        else:
            if self.calls >= min(self.config.max_calls, self.call_limit):
                raise BudgetExceeded("Hosted call budget exhausted; cached calls remain available.")
            self.calls += 1
            try:
                result = self.transport(endpoint, payload)
            except BaseException as exc:
                self.trace.append({"request_id": key, "purpose": purpose, "endpoint": endpoint,
                                   "model": payload["model"], "cached": False, "status": "failed",
                                   "error_type": type(exc).__name__,
                                   "latency_seconds": round(time.monotonic() - started, 4)})
                raise
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"request": payload, "response": result}, ensure_ascii=False))
        if not isinstance(result, dict):
            raise ValueError("Hosted response must be a JSON object")
        usage = result.get("usage", {})
        if not isinstance(usage, dict):
            raise ValueError("Hosted usage must be an object")
        cost = None
        if (self.config.input_usd_per_million is not None and self.config.output_usd_per_million is not None
                and endpoint == "/chat/completions"):
            cost = (usage.get("prompt_tokens", 0) * self.config.input_usd_per_million
                    + usage.get("completion_tokens", 0) * self.config.output_usd_per_million) / 1e6
        self.trace.append({"request_id": key, "purpose": purpose, "endpoint": endpoint,
                           "model": payload["model"], "cached": cached, "usage": usage,
                           "latency_seconds": round(time.monotonic() - started, 4),
                           "estimated_original_cost_usd": cost,
                           "estimated_this_run_cost_usd": 0.0 if cached else cost,
                           "cache_file": str(path)})
        return result, key

    def json(self, system, packet, schema, purpose):
        if self.config.response_format == "json_schema":
            fmt = {"type": "json_schema", "json_schema": {"name": "memory_result", "strict": True, "schema": schema}}
        else:
            fmt = {"type": "json_object"}
        payload = {"model": self.config.model, "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps({"task": packet, "output_schema": schema}, ensure_ascii=False)},
        ], "response_format": fmt, "max_completion_tokens": 6000}
        if self.config.reasoning_effort is not None:
            payload["reasoning_effort"] = self.config.reasoning_effort
        result, key = self._call("/chat/completions", payload, purpose)
        choices = result.get("choices", [])
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict) or choices[0].get("finish_reason") != "stop":
            raise ValueError("Hosted response did not finish normally; no partial JSON will be admitted")
        message = choices[0].get("message")
        if not isinstance(message, dict) or message.get("refusal") or not isinstance(message.get("content"), str) or not message["content"]:
            raise ValueError("Hosted model refused or returned no structured content")
        return json.loads(message["content"]), key

    def embed(self, texts):
        vectors = []
        for offset in range(0, len(texts), 32):
            part = texts[offset:offset + 32]
            payload = {"model": self.config.embedding_model, "input": part, "encoding_format": "float"}
            result, _ = self._call("/embeddings", payload, "text_embedding")
            rows = sorted(result["data"], key=lambda d: d["index"])
            if [r["index"] for r in rows] != list(range(len(part))):
                raise ValueError("Embedding response does not match input ordering/count")
            vectors.extend(r["embedding"] for r in rows)
        return vectors


def obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def array(schema):
    return {"type": "array", "items": schema}


STRING = {"type": "string"}
CONFIDENCE = {"type": "string", "enum": ["high", "medium", "low"]}
def _check_schema(value, schema, path="output"):
    """Small validator for this module's intentionally simple JSON schemas."""
    kind = schema["type"]
    if kind == "object":
        if not isinstance(value, dict) or set(value) != set(schema["properties"]):
            raise ValueError(f"Unexpected fields at {path}")
        for key, sub in schema["properties"].items():
            _check_schema(value[key], sub, f"{path}.{key}")
    elif kind == "array":
        if not isinstance(value, list):
            raise ValueError(f"Expected list at {path}")
        for i, element in enumerate(value):
            _check_schema(element, schema["items"], f"{path}[{i}]")
    elif kind == "string":
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Expected nonempty string at {path}")
        if "enum" in schema and value not in schema["enum"]:
            raise ValueError(f"Unexpected value at {path}")
    elif kind == "boolean":
        if type(value) is not bool:
            raise ValueError(f"Expected boolean at {path}")
    else:
        raise ValueError(f"Unsupported schema type: {kind}")
