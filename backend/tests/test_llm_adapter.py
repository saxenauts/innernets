import json
import importlib
from typing import Any, List

import pytest


def make_fake_response(payload: dict, status_code: int = 200):
    class FakeResponse:
        def __init__(self, payload: dict, status_code: int) -> None:
            self._payload = payload
            self.status_code = status_code
            self.text = json.dumps(payload)

        def json(self) -> Any:  # type: ignore
            return self._payload

    return FakeResponse(payload, status_code)


def test_invoke_tools_parses_tool_calls(monkeypatch):
    types_mod = importlib.import_module("app.llm.types")
    adapter_mod = importlib.import_module("app.llm.adapter")
    steps = importlib.import_module("app.llm.search_steps")
    azure_mod = importlib.import_module("app.llm.providers.azure_openai")

    cfg = types_mod.ProviderConfig(
        provider="azure_openai",
        azure_endpoint="https://example.openai.azure.com",
        azure_api_version="2025-02-01-preview",
        azure_api_key="test",
        azure_deployment="gpt-4o-mini",
    )

    messages = [types_mod.Message(role="user", content="Generate queries")]
    tool = types_mod.FunctionSpec(
        name="generate_search_queries",
        description="...",
        parameters=types_mod.JsonSchema(properties={"context": {"type": "string"}}, required=["context"]),
    )
    opts = types_mod.InvokeOptions(tool_choice="function")

    fake_payload = {
        "id": "chatcmpl-123",
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "generate_search_queries",
                                "arguments": json.dumps({"context": "foo"}),
                            },
                        }
                    ],
                },
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }

    # Tools path removed; keep placeholder test skipped
    pytest.skip("tool invocation removed; structured-only")


def test_invoke_tools_http_error(monkeypatch):
    types_mod = importlib.import_module("app.llm.types")
    adapter_mod = importlib.import_module("app.llm.adapter")

    cfg = types_mod.ProviderConfig(
        provider="azure_openai",
        azure_endpoint="https://example.openai.azure.com",
        azure_api_version="2025-02-01-preview",
        azure_api_key="test",
        azure_deployment="gpt-4o-mini",
    )

    messages = [types_mod.Message(role="user", content="Generate queries")]
    tool = types_mod.FunctionSpec(
        name="generate_search_queries",
        description="...",
        parameters=types_mod.JsonSchema(properties={}),
    )
    opts = types_mod.InvokeOptions(tool_choice="function")

    pytest.skip("tool invocation removed; structured-only")


def test_structured_outputs(monkeypatch):
    types_mod = importlib.import_module("app.llm.types")
    adapter_mod = importlib.import_module("app.llm.adapter")
    steps = importlib.import_module("app.llm.search_steps")

    cfg = types_mod.ProviderConfig(
        provider="azure_openai",
        azure_endpoint="https://example.openai.azure.com",
        azure_api_version="2025-02-01-preview",
        azure_api_key="test",
        azure_deployment="gpt-4o-mini",
    )

    req = types_mod.StructuredRequest(
        instruction="Generate 3 queries",
        context={"mission": "learn hardware"},
        schema_name="queries",
        out_schema=types_mod.JsonSchema(properties={}, required=[]),
        pydantic_model=steps.GenerateQueriesOut,
    )
    opts = types_mod.InvokeOptions()

    class FakeParsed(steps.GenerateQueriesOut):
        pass

    fake_parsed = steps.GenerateQueriesOut(
        queries=[
            steps.QueryItem(query=f"q{i}", query_type=("keyword" if i % 2 else "neural"))
            for i in range(1, 11)
        ]
    ).model_dump()

    # Mock Chat Completions path
    class FakeChatCompletion:
        def __init__(self):
            self.id = "chatcmpl-1"
            self.usage = type("U", (), {"prompt_tokens": 12, "completion_tokens": 10, "total_tokens": 22})()
            self.choices = [type("C", (), {"message": type("M", (), {"content": json.dumps(fake_parsed)})()})()]

    class FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    return FakeChatCompletion()

    import app.llm.providers.azure_openai as prov
    def fake_get_client(cfg):
        return FakeClient()

    monkeypatch.setattr(prov, "get_client", fake_get_client)

    res = adapter_mod.structured(cfg, req, opts)
    assert res.id is not None
    assert res.output["queries"][0]["query"] == "q1"
    assert res.usage.total_tokens == 22


def test_structured_generate_queries_only(monkeypatch):
    types_mod = importlib.import_module("app.llm.types")
    adapter_mod = importlib.import_module("app.llm.adapter")
    steps = importlib.import_module("app.llm.search_steps")
    prov = importlib.import_module("app.llm.providers.azure_openai")

    cfg = types_mod.ProviderConfig(
        provider="azure_openai",
        azure_endpoint="https://example.openai.azure.com",
        azure_api_version="2025-02-01-preview",
        azure_api_key="test",
        azure_deployment="gpt-4o-mini",
    )

    payload = steps.GenerateQueriesOut(
        queries=[
            steps.QueryItem(query=f"q{i}", query_type=("keyword" if i % 2 else "neural"))
            for i in range(1, 11)
        ]
    ).model_dump()
    class FakeChatCompletion:
        def __init__(self, data):
            self.id = "chatcmpl-xyz"
            self.usage = type("U", (), {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20})()
            self.choices = [type("C", (), {"message": type("M", (), {"content": json.dumps(data)})()})()]

    class FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    return FakeChatCompletion(payload)

    def fake_get_client(cfg):
        return FakeClient()

    monkeypatch.setattr(prov, "get_client", fake_get_client)

    req = types_mod.StructuredRequest(
        instruction="Generate 2 queries",
        context={"mission": "test"},
        schema_name="GenerateQueriesOut",
        out_schema=types_mod.JsonSchema(properties={}, required=[]),
        pydantic_model=steps.GenerateQueriesOut,
    )
    res = adapter_mod.structured(cfg, req, types_mod.InvokeOptions())
    assert res.output["queries"][1]["query"] == "q2"
