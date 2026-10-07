"""Fingerprints, strict JSON calls, bounded provider access and safe local artifacts."""
from dataclasses import replace
from pathlib import Path
import hashlib
import json
import time

from org_memory.evidence import stable_id
from org_memory.hosted import BudgetExceeded, create_client
from org_memory.storage import atomic_json


def read_json(path):
    return json.loads(Path(path).read_text())


def fingerprint(value):
    return stable_id("sha", value)


def code_fingerprint():
    root = Path(__file__).resolve().parents[1]
    paths = sorted(p for directory in ("org_eval", "org_agent", "org_memory")
                   for p in (root / directory).glob("*.py")) + [root / "run_evaluation.py"]
    return fingerprint({str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in paths if p.exists()})


def strict_schema(model):
    schema = model.model_json_schema()

    def clean(value):
        if isinstance(value, dict):
            value.pop("default", None)
            if value.get("type") == "object":
                value["additionalProperties"] = False
                value["required"] = list(value.get("properties", {}))
            for child in value.values():
                clean(child)
        elif isinstance(value, list):
            for child in value:
                clean(child)
    clean(schema)
    return schema


class CallBudget:
    """Persist attempts before invoking a provider; a crash cannot erase spending history.

    The cap is conservative: application calls, including cache lookups and failures,
    count. Provider-reported usage separately identifies actual new turns and replays.
    """
    def __init__(self, path, limit):
        if limit < 0:
            raise ValueError("Call budget must be nonnegative")
        self.path, self.limit = Path(path), limit
        self.state = read_json(path) if self.path.exists() else {"attempts": []}

    def reserve(self, purpose):
        if len(self.state["attempts"]) >= self.limit:
            raise BudgetExceeded("Evaluation stage call budget exhausted; raise --max-calls to resume")
        row = {"number": len(self.state["attempts"]) + 1, "purpose": purpose, "status": "started"}
        self.state["attempts"].append(row)
        atomic_json(self.path, self.state)
        return row

    def finish(self, row, **fields):
        row.update(fields)
        atomic_json(self.path, self.state)


class BudgetedClient:
    def __init__(self, client, budget):
        self.client, self.budget = client, budget

    @property
    def trace(self):
        return self.client.trace

    def json(self, system, packet, schema, purpose):
        row = self.budget.reserve(purpose)
        started, before = time.monotonic(), len(self.trace)
        try:
            result = self.client.json(system, packet, schema, purpose)
            self.budget.finish(row, status="complete")
            return result
        except BaseException as exc:
            self.budget.finish(row, status="failed", error_type=type(exc).__name__)
            raise
        finally:
            self.budget.finish(row, elapsed_seconds=time.monotonic() - started,
                               provider=self.trace[-1] if len(self.trace) > before else {})

    def close(self):
        self.client.close()


def client_for(config, *, budget=None, factory=None):
    client = factory() if factory else create_client(config.provider, model=config.model,
                                                    max_calls=config.max_model_calls)
    if factory is None:
        client.config = replace(client.config, cache_dir=config.cache_dir,
                                reasoning_effort=config.reasoning_effort, timeout=config.timeout)
    return BudgetedClient(client, budget) if budget else client


def checked_call(client, system, packet, model, purpose, output, validate=None):
    """Persist the input and every judgment, with one bounded format/reference repair."""
    output = Path(output)
    request = {"system": system, "packet": packet, "schema": strict_schema(model)}
    key = fingerprint(request)
    if output.exists():
        saved = read_json(output)
        if saved["request_fingerprint"] != key:
            raise ValueError(f"Stale evaluation call: {output}")
        if saved["status"] == "complete":
            result = model.model_validate(saved["result"])
            if validate:
                validate(result)
            return result
    else:
        saved = {"request_fingerprint": key, "request": request, "attempts": [], "status": "incomplete"}
    while len(saved["attempts"]) < 2:
        task = dict(packet)
        if saved["attempts"]:
            task["format_correction"] = saved["attempts"][-1].get("error", "Return a complete valid response")
        attempt = {"status": "started"}
        saved["attempts"].append(attempt)
        atomic_json(output, saved)
        before = len(client.trace)
        try:
            raw, request_id = client.json(system, task, request["schema"], purpose)
            attempt.update(raw=raw, request_id=request_id)
            result = model.model_validate(raw)
            if validate:
                validate(result)
            saved.update(result=result.model_dump(), status="complete")
            attempt["status"] = "complete"
            return result
        except (ValueError, KeyError, TypeError) as exc:
            attempt.update(status="invalid", error=str(exc)[:2000])
        except BaseException:
            # Transport/budget errors are resumable, not a spent semantic repair.
            saved["attempts"].pop()
            raise
        finally:
            attempt["provider"] = client.trace[-1] if len(client.trace) > before else {}
            atomic_json(output, saved)
    raise ValueError(f"Evaluation response invalid after one repair: {output}")
