import os
import json
import pytest
from dotenv import load_dotenv
import importlib.util
import pathlib


def _mask(v: str, keep: int = 4) -> str:
    if not v:
        return "<empty>"
    if len(v) <= keep * 2:
        return v[:keep] + "…"
    return v[:keep] + "…" + v[-2:]


def _debug_env():
    keys = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_DEPLOYMENT_NAME",
    ]
    print("[live-test] Env snapshot:")
    for k in keys:
        v = os.getenv(k)
        status = "FOUND" if v else "MISSING"
        shown = _mask(v or "") if "KEY" in k else (v or "")
        print(f"  - {k}: {status} {shown}")


def _require_env(var: str) -> str:
    v = os.getenv(var)
    if not v:
        pytest.skip(f"Missing {var}; set to run live test")
    return v


@pytest.mark.live
def test_llm_live_structured_search_queries():
    if os.getenv("RUN_LIVE_OPENAI_TESTS") != "1":
        print("[live-test] RUN_LIVE_OPENAI_TESTS is not '1'; skipping live call")
        pytest.skip("Set RUN_LIVE_OPENAI_TESTS=1 to run live Azure OpenAI test")

    # Load local .env if present
    load_dotenv(os.getenv("DOTENV_PATH", ".env"), override=False)

    # Validate Azure env is present
    _debug_env()
    missing = []
    for req in ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_API_VERSION"]:
        if not os.getenv(req):
            missing.append(req)
    if not os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"):
        missing.append("AZURE_OPENAI_DEPLOYMENT_NAME")
    if missing:
        # Fail (not skip) to make the reason obvious in output
        pytest.fail("Missing required env: " + ", ".join(missing))

    from app.llm.types import ProviderConfig, StructuredRequest, InvokeOptions, JsonSchema
    from app.llm import structured
    from app.llm.schemas import GenerateSearchQueriesOut
    from app.llm import prompts

    cfg = ProviderConfig.from_env("azure_openai")

    instruction = (
        prompts.GENERATE_SEARCH_QUERIES
        + "\nGenerate 3 focused queries for the mission."
    )
    req = StructuredRequest(
        instruction=instruction,
        context={
            "mission": "AI tools with persistent user memory",
            "hints": ["site:github.com", "recent", "frameworks"],
        },
        schema_name="GenerateSearchQueriesOut",
        out_schema=JsonSchema(properties={}, required=[]),
        pydantic_model=GenerateSearchQueriesOut,
    )

    opts = InvokeOptions(temperature=0, max_tokens=256)

    res = structured(cfg, req, opts)

    assert res.output, "No output returned from Azure OpenAI"
    parsed = GenerateSearchQueriesOut(**res.output)
    assert len(parsed.queries) >= 1
    assert all(isinstance(q, str) and len(q) > 0 for q in parsed.queries)

    # Print outputs for visibility when running with -s
    print("Azure model:", res.model)
    print("Token usage:", json.dumps(res.usage.model_dump(), indent=2))
    print("Queries:")
    for q in parsed.queries:
        print(" -", q)


@pytest.mark.live
def test_llm_live_structured_all_functions():
    if os.getenv("RUN_LIVE_OPENAI_TESTS") != "1":
        print("[live-test] RUN_LIVE_OPENAI_TESTS is not '1'; skipping live calls")
        pytest.skip("Set RUN_LIVE_OPENAI_TESTS=1 to run live Azure OpenAI tests")

    load_dotenv(os.getenv("DOTENV_PATH", ".env"), override=False)

    _debug_env()
    missing = []
    for req in ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_API_VERSION", "AZURE_OPENAI_DEPLOYMENT_NAME"]:
        if not os.getenv(req):
            missing.append(req)
    if missing:
        pytest.fail("Missing required env: " + ", ".join(missing))

    from app.llm.types import ProviderConfig, StructuredRequest, InvokeOptions, JsonSchema
    from app.llm import structured
    from app.llm import prompts
    from app.llm.schemas import (
        GenerateSearchQueriesOut,
        EvaluateCandidatesOut,
        ProposeFollowupsOut,
        ComposeStreamItemsOut,
    )

    cfg = ProviderConfig.from_env("azure_openai")
    opts = InvokeOptions(temperature=1, max_tokens=512)

    # Load frontend mock streams to enrich context if available
    mocks_path = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "src" / "mocks" / "mock-data.ts"
    mock_streams = None
    try:
        if mocks_path.exists():
            # crude extract of URLs and titles without TS runtime
            text = mocks_path.read_text(encoding="utf-8")
            import re
            items = re.findall(r"url:\s*\"(https?://[^\"]+)\"", text)
            titles = re.findall(r"title:\s*\"([^\"]+)\"", text)
            mock_streams = {"titles": titles[:10], "urls": items[:20]}
    except Exception:
        mock_streams = None

    # 1) Generate Search Queries
    req1 = StructuredRequest(
        instruction=prompts.GENERATE_SEARCH_QUERIES + "\nGenerate 3 focused queries for the mission.",
        context={
            "mission": "Evaluate AI tools with persistent user memory",
            "hints": ["site:github.com", "recent", "frameworks"],
        },
        schema_name="GenerateSearchQueriesOut",
        out_schema=JsonSchema(properties={}, required=[]),
        pydantic_model=GenerateSearchQueriesOut,
    )
    r1 = structured(cfg, req1, opts)
    p1 = GenerateSearchQueriesOut(**r1.output)
    assert len(p1.queries) >= 1
    print("[live] queries:", p1.queries)

    # 2) Evaluate Candidates
    req2 = StructuredRequest(
        instruction=(
            prompts.EVALUATE_CANDIDATES
            + "\nScore exactly 3 candidates. Return schema-only JSON."
            + " For each candidate, provide url (fully-qualified, https://...), score (0-100), and read (true/false)."
        ),
        context={
            "candidates": [
                {"title": "MemGPT", "snippet": "memory-enabled agents", "domain": "github.com"},
                {"title": "LangGraph", "snippet": "stateful agent workflows", "domain": "langchain-ai.github.io"},
                {"title": "LLM Memory", "snippet": "long-term AI memory", "domain": "paperswithcode.com"},
            ]
        },
        schema_name="EvaluateCandidatesOut",
        out_schema=JsonSchema(properties={}, required=[]),
        pydantic_model=EvaluateCandidatesOut,
    )
    if mock_streams and mock_streams.get("urls"):
        req2.context["candidates"][0]["url"] = mock_streams["urls"][0]
    r2 = structured(cfg, req2, opts)
    p2 = EvaluateCandidatesOut(**r2.output)
    assert isinstance(p2.scores, list)
    print("[live] scores:", [s.model_dump() for s in p2.scores])

    # 3) Propose Followups
    req3 = StructuredRequest(
        instruction=prompts.PROPOSE_FOLLOWUPS + "\nPropose 3 follow-up queries.",
        context={"gaps": ["benchmarks", "real deployments", "data privacy"]},
        schema_name="ProposeFollowupsOut",
        out_schema=JsonSchema(properties={}, required=[]),
        pydantic_model=ProposeFollowupsOut,
    )
    r3 = structured(cfg, req3, opts)
    p3 = ProposeFollowupsOut(**r3.output)
    assert len(p3.followups) >= 1
    print("[live] followups:", p3.followups)

    # 4) Compose Stream Items
    req4 = StructuredRequest(
        instruction=prompts.COMPOSE_STREAM_ITEMS + "\nCompose items for current mission.",
        context={
            "candidates": [
                {"title": "MemGPT repo", "url": "https://github.com/cpacker/MemGPT"},
                {"title": "LangGraph docs", "url": "https://langchain-ai.github.io/langgraph/"},
                {"title": "Paper: Memory in LLMs", "url": "https://arxiv.org/abs/2308.XXXX"},
            ]
        },
        schema_name="ComposeStreamItemsOut",
        out_schema=JsonSchema(properties={}, required=[]),
        pydantic_model=ComposeStreamItemsOut,
    )
    # Seed candidates with mock items if available
    if mock_streams and mock_streams.get("urls"):
        req4.context["candidates"][0]["url"] = mock_streams["urls"][1] if len(mock_streams["urls"]) > 1 else mock_streams["urls"][0]
    r4 = structured(cfg, req4, opts)
    p4 = ComposeStreamItemsOut(**r4.output)
    assert isinstance(p4.items, list)
    print("[live] items:", [it.model_dump() for it in p4.items])

    # Print outputs for visibility
    print("Azure model:", r1.model)
    print("Search queries:")
    for q in p1.queries:
        print(" -", q)
    print("Followups:")
    for q in p3.followups:
        print(" -", q)
    print("Items:")
    for it in p4.items:
        print(" -", it.title, it.url)
