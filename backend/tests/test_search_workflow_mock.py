from __future__ import annotations

import types
import pytest


def test_search_workflow_mock_llm_and_exa(monkeypatch):
    # Mock new LLM step functions (IDs only)
    from app.llm import search_steps as steps

    def fake_generate_search_queries(cfg, mission, additional_context=None, options=None):
        return steps.GenerateQueriesOut(
            queries=[
                steps.QueryItem(query="ai memory tools", query_type="keyword"),
                steps.QueryItem(query="site:github.com agent memory", query_type="keyword"),
                steps.QueryItem(query="long-term memory agents", query_type="neural"),
                steps.QueryItem(query="vector memory patterns", query_type="neural"),
                steps.QueryItem(query="episodic memory ai", query_type="neural"),
            ]
        )

    def fake_filter_candidates(cfg, mission, candidates, additional_context=None, options=None):
        # select first two IDs deterministically
        ids = [c["id"] for c in candidates][:2]
        return steps.FilterCandidatesOut(selected_ids=ids)

    def fake_propose_followups(
        cfg, mission, initial_queries, filtered_ids, read_summaries, additional_context=None, prior_urls=None, options=None
    ):
        return steps.ProposeFollowupsOut(
            followups=[
                steps.FollowupItem(query="memory eval real-world", query_type="keyword"),
                steps.FollowupItem(query="privacy risks agent memory", query_type="neural"),
                steps.FollowupItem(query="benchmarks episodic vs semantic", query_type="keyword"),
            ]
        )

    def fake_consolidate_curations(cfg, mission, all_items, additional_context=None, options=None):
        # group first 3 into curation A, next 3 into curation B (ids exist from workflow)
        ids = [it["id"] for it in all_items]
        a = ids[:3]
        b = ids[3:6] if len(ids) >= 6 else ids[:3]
        return steps.ConsolidateOut(
            curations=[
                steps.Curation(title="Agent Memory Architectures", hook="Core patterns and tradeoffs.", link_ids=a or []),
                steps.Curation(title="Benchmarks & Privacy", hook="What to trust and guard.", link_ids=b or []),
            ]
        )

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
                    types.SimpleNamespace(title="MemGPT", url=urls[0] if urls else "https://example.com/", text="Lorem ipsum dolor sit amet, consectetur adipiscing elit.")
                ])

        return C()

    # Apply patches
    import app.agents.search_workflow as sw
    from app.llm import search_steps as steps_mod
    monkeypatch.setattr(steps_mod, "generate_search_queries", fake_generate_search_queries)
    monkeypatch.setattr(steps_mod, "filter_candidates", fake_filter_candidates)
    monkeypatch.setattr(steps_mod, "propose_followups", fake_propose_followups)
    monkeypatch.setattr(steps_mod, "consolidate_curations", fake_consolidate_curations)
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
    # curations present
    assert isinstance(out.get("curations"), list)
