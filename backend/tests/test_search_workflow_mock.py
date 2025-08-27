from __future__ import annotations

import types
import pytest


def test_search_workflow_mock_llm_and_exa(monkeypatch):
    # Mock LLM structured to return deterministic outputs for 4 calls
    call_seq = {"i": 0}

    class DummyUsage:
        def __init__(self):
            self.prompt_tokens = 10
            self.completion_tokens = 20
            self.total_tokens = 30

    class DummyRes:
        def __init__(self, output):
            self.output = output
            self.usage = DummyUsage()
            self.model = "dummy"

    def fake_structured(_cfg, req, _opts):
        i = call_seq["i"]; call_seq["i"] += 1
        if i == 0:
            # Generate queries
            return DummyRes({"queries": ["ai memory tools", "site:github.com agent memory"]})
        if i == 1:
            # Evaluate candidates
            cands = req.context.get("candidates")
            assert isinstance(cands, list) and len(cands) >= 1
            # Pick first two
            out = {
                "scores": [
                    {"url": c.get("url") or "https://example.com/", "score": 90, "read": True}
                    for c in cands[:2]
                ]
            }
            return DummyRes(out)
        if i == 2:
            # Propose followups
            return DummyRes({"followups": ["benchmarks persistent memory", "privacy frameworks"]})
        # Compose items
        candz = req.context.get("candidates") or []
        items = []
        for c in candz[:2]:
            items.append({
                "title": c.get("title") or "Item",
                "url": c.get("url") or "https://example.com/",
                "hook": "Short hook",
                "reason": "Relevant",
            })
        return DummyRes({"items": items})

    # Mock Exa client wrapper
    class FakeResult:
        def __init__(self, title, url):
            self.title = title
            self.url = url

    class FakeCost:
        def __init__(self, total):
            self.total = total

    class FakeSearchResponse:
        def __init__(self, results, cost=0.001):
            self.results = results
            self.provider_cost = FakeCost(cost)

    class FakeContentsResponse:
        def __init__(self, results, cost=0.002):
            self.results = results
            self.provider_cost = FakeCost(cost)

    def fake_get_exa_client():
        class C:
            def search(self, **kwargs):
                # return 3 items with URLs
                return FakeSearchResponse([
                    types.SimpleNamespace(title="MemGPT", url="https://github.com/cpacker/MemGPT"),
                    types.SimpleNamespace(title="LangGraph", url="https://langchain-ai.github.io/langgraph/"),
                    types.SimpleNamespace(title="Paper", url="https://arxiv.org/abs/2308.XXXX"),
                ])

            def get_contents(self, **kwargs):
                urls = kwargs.get("urls") or []
                return FakeContentsResponse([
                    types.SimpleNamespace(title="MemGPT", url=urls[0] if urls else "https://example.com/", text="..."),
                ])

        return C()

    # Apply patches
    import app.agents.search_workflow as sw
    monkeypatch.setattr(sw, "llm_structured", fake_structured)
    monkeypatch.setattr(sw, "get_exa_client", fake_get_exa_client)

    job = {"payload": {"agent": "search_only_v1", "params": {"mission": "AI tools with persistent user memory"}}}
    out = sw.run(job)

    assert out["agent"] == "search_only_v1"
    assert out["queries"] >= 1
    assert out["reads"] >= 1
    assert out["cost_exa"] > 0
    # breakdown present
    b = out.get("cost_exa_breakdown")
    assert isinstance(b, dict)
    assert b.get("total") == out["cost_exa"]
    assert b.get("search") >= 0
    assert isinstance(out["usage_tokens"], dict)
    assert isinstance(out.get("items"), list)
