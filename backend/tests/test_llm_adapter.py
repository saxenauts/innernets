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
    schemas = importlib.import_module("app.llm.schemas")
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
    schemas = importlib.import_module("app.llm.schemas")

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
        pydantic_model=schemas.GenerateSearchQueriesOut,
    )
    opts = types_mod.InvokeOptions()

    class FakeParsed(schemas.GenerateSearchQueriesOut):
        pass

    fake_parsed = schemas.GenerateSearchQueriesOut(queries=["q1", "q2", "q3"]).model_dump()

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
    assert res.output["queries"][0] == "q1"
    assert res.usage.total_tokens == 22


def test_structured_all_functions(monkeypatch):
    types_mod = importlib.import_module("app.llm.types")
    adapter_mod = importlib.import_module("app.llm.adapter")
    schemas = importlib.import_module("app.llm.schemas")
    prov = importlib.import_module("app.llm.providers.azure_openai")

    cfg = types_mod.ProviderConfig(
        provider="azure_openai",
        azure_endpoint="https://example.openai.azure.com",
        azure_api_version="2025-02-01-preview",
        azure_api_key="test",
        azure_deployment="gpt-4o-mini",
    )

    # Prepare fake outputs for each step
    outputs = [
        schemas.GenerateSearchQueriesOut(queries=["q1", "q2", "q3"]).model_dump(),
        schemas.EvaluateCandidatesOut(scores=[]).model_dump(),
        schemas.ProposeFollowupsOut(followups=["fq1"]).model_dump(),
        schemas.ComposeStreamItemsOut(items=[]).model_dump(),
    ]
    idx = {"count": 0}

    # Mock Chat Completions returning different payloads per call
    class FakeChatCompletion2:
        def __init__(self, data):
            self.id = f"chatcmpl-{idx['count']}"
            self.usage = type("U", (), {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20})()
            self.choices = [type("C", (), {"message": type("M", (), {"content": json.dumps(data)})()})()]

    class FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    i = idx["count"]
                    payload = outputs[i]
                    idx["count"] += 1
                    return FakeChatCompletion2(payload)

    def fake_get_client(cfg):
        return FakeClient()

    monkeypatch.setattr(prov, "get_client", fake_get_client)

    # 1. generate_search_queries
    req1 = types_mod.StructuredRequest(
        instruction="Generate 3 queries",
        context={"mission": "learn hardware"},
        schema_name="GenerateSearchQueriesOut",
        out_schema=types_mod.JsonSchema(properties={}, required=[]),
        pydantic_model=schemas.GenerateSearchQueriesOut,
    )
    r1 = adapter_mod.structured(cfg, req1, types_mod.InvokeOptions())
    assert r1.output["queries"][0] == "q1"

    # 2. evaluate_candidates
    req2 = types_mod.StructuredRequest(
        instruction="Evaluate candidates",
        context={"candidates": []},
        schema_name="EvaluateCandidatesOut",
        out_schema=types_mod.JsonSchema(properties={}, required=[]),
        pydantic_model=schemas.EvaluateCandidatesOut,
    )
    r2 = adapter_mod.structured(cfg, req2, types_mod.InvokeOptions())
    assert isinstance(r2.output["scores"], list)

    # 3. propose_followups
    req3 = types_mod.StructuredRequest(
        instruction="Propose followups",
        context={"gaps": "thin coverage"},
        schema_name="ProposeFollowupsOut",
        out_schema=types_mod.JsonSchema(properties={}, required=[]),
        pydantic_model=schemas.ProposeFollowupsOut,
    )
    r3 = adapter_mod.structured(cfg, req3, types_mod.InvokeOptions())
    assert r3.output["followups"][0] == "fq1"

    # 4. compose_stream_items
    req4 = types_mod.StructuredRequest(
        instruction="Compose items",
        context={"candidates": []},
        schema_name="ComposeStreamItemsOut",
        out_schema=types_mod.JsonSchema(properties={}, required=[]),
        pydantic_model=schemas.ComposeStreamItemsOut,
    )
    r4 = adapter_mod.structured(cfg, req4, types_mod.InvokeOptions())
    assert isinstance(r4.output["items"], list)
