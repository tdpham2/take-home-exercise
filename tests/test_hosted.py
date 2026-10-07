import json
from dataclasses import replace

import pytest

from org_memory.hosted import BudgetExceeded, CompatibleClient, ProviderConfig, _check_schema, load_env, obj


def fake_completion(payload):
    return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"value": "test fixture"})}}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 5}}


def test_client_cache_budget_trace_and_no_credentials(tmp_path):
    sent = []
    def transport(endpoint, payload):
        sent.append((endpoint, payload))
        return fake_completion(payload)
    cfg = ProviderConfig(api_key="test-secret-do-not-log", base_url="https://example.invalid/v1", max_calls=1, cache_dir=str(tmp_path))
    client = CompatibleClient(cfg, transport=transport)
    schema = obj({"value": {"type": "string"}})
    first, request_id = client.json("Return JSON", {"a": 1}, schema, "test")
    second, _ = client.json("Return JSON", {"a": 1}, schema, "test")
    assert first == second and len(sent) == 1
    assert client.trace[-1]["cached"]
    assert client.trace[-1]["estimated_this_run_cost_usd"] == 0
    assert "test-secret" not in repr(cfg)
    assert "test-secret" not in json.dumps(client.trace)
    assert "test-secret" not in next(tmp_path.glob("*.json")).read_text()
    with pytest.raises(BudgetExceeded):
        client.json("Return JSON", {"a": 2}, schema, "test")
    # Different provider/model cannot hit the same cache.
    other = CompatibleClient(replace(cfg, model="different-model"), transport=transport)
    other.json("Return JSON", {"a": 1}, schema, "test")
    assert len(sent) == 2


def test_client_refusal_and_truncated_output(tmp_path):
    cfg = ProviderConfig(api_key="fixture", cache_dir=str(tmp_path))
    client = CompatibleClient(cfg, transport=lambda *_: {"choices": [{"finish_reason": "length", "message": {"content": "{"}}]})
    with pytest.raises(ValueError, match="did not finish"):
        client.json("Return JSON", {}, obj({}), "fixture")


def test_client_missing_credentials_and_unsafe_url():
    with pytest.raises(ValueError, match="API_KEY"):
        CompatibleClient(ProviderConfig())
    with pytest.raises(ValueError, match="without embedded credentials"):
        CompatibleClient(ProviderConfig(api_key="fixture", base_url="https://user:password@example.invalid/v1"))


def test_simple_schema_rejects_unknown_fields():
    schema = obj({"value": {"type": "string"}})
    _check_schema({"value": "valid"}, schema)
    with pytest.raises(ValueError):
        _check_schema({"value": "valid", "hallucinated": True}, schema)


def test_embedding_order_is_validated(tmp_path):
    cfg = ProviderConfig(api_key="fixture", cache_dir=str(tmp_path))
    client = CompatibleClient(cfg, transport=lambda *_: {"data": [{"index": 1, "embedding": [1, 0]}, {"index": 0, "embedding": [0, 1]}]})
    assert client.embed(["a", "b"]) == [[0, 1], [1, 0]]
    wrong = CompatibleClient(replace(cfg, cache_dir=str(tmp_path / "other")), transport=lambda *_: {"data": []})
    with pytest.raises(ValueError, match="ordering/count"):
        wrong.embed(["a"])


def test_dotenv_is_literal_and_does_not_override_existing(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text('TEST_MEMORY_VALUE="$(do-not-execute)"\nTEST_MEMORY_EXISTING=new\n')
    monkeypatch.setenv("TEST_MEMORY_EXISTING", "original")
    monkeypatch.delenv("TEST_MEMORY_VALUE", raising=False)
    load_env(path)
    import os
    assert os.environ["TEST_MEMORY_VALUE"] == "$(do-not-execute)"
    assert os.environ["TEST_MEMORY_EXISTING"] == "original"
    monkeypatch.delenv("TEST_MEMORY_VALUE")
