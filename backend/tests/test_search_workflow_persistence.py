from typing import Any, Dict, List


def test_stream_run_persists_curations(monkeypatch):
    # Fake Exa client
    class FakeResult:
        def __init__(self, url, title):
            self.url = url
            self.title = title
            self.publishedDate = None

    class FakeSearchResponse:
        def __init__(self, results):
            self.results = results
            self.provider_cost = type("C", (), {"total": 0.0})

    class FakeContentsResponse:
        def __init__(self, results):
            self.results = results
            self.provider_cost = type("C", (), {"total": 0.0})

    class FakeContentResult:
        def __init__(self, url, title, text):
            self.url = url
            self.title = title
            self.text = text

    class FakeExa:
        def search(self, query: str, type: str, num_results: int, include_domains=None, exclude_domains=None):
            # Return two URLs
            return FakeSearchResponse([
                FakeResult("https://a.com/one", "One"),
                FakeResult("https://b.com/two", "Two"),
            ])

        def get_contents(self, urls: List[str], text: Dict[str, Any]):
            return FakeContentsResponse([
                FakeContentResult(urls[0], "One", "Body one"),
                FakeContentResult(urls[1], "Two", "Body two"),
            ])

    # get_exa_client is imported into the orchestrator module; patch there

    # Fake LLM steps to control outputs
    from app.llm import search_steps as steps

    monkeypatch.setattr(steps, "generate_search_queries", lambda cfg, mission, additional_context=None, options=None: steps.GenerateQueriesOut(queries=[
        steps.QueryItem(query="q1", query_type="keyword"),
        steps.QueryItem(query="q2", query_type="neural"),
        steps.QueryItem(query="q3", query_type="keyword"),
        steps.QueryItem(query="q4", query_type="neural"),
        steps.QueryItem(query="q5", query_type="keyword"),
    ]))

    monkeypatch.setattr(steps, "filter_candidates", lambda cfg, mission, candidates, additional_context=None, options=None: steps.FilterCandidatesOut(selected_ids=[candidates[0]["id"], candidates[1]["id"]]))

    monkeypatch.setattr(steps, "propose_followups", lambda *a, **k: steps.ProposeFollowupsOut(followups=[
        steps.FollowupItem(query="f1", query_type="keyword"),
        steps.FollowupItem(query="f2", query_type="neural"),
        steps.FollowupItem(query="f3", query_type="keyword"),
    ]))

    # Consolidate returns one curation with both ids
    def _cons(cfg, mission, all_items, additional_context=None, options=None):
        return steps.ConsolidateOut(curations=[
            steps.Curation(title="T1", hook="H1", link_ids=["01", "02", "03"]),
            steps.Curation(title="T2", hook="H2", link_ids=["01", "02", "03"]),
        ])

    monkeypatch.setattr(steps, "consolidate_curations", _cons)

    # Fake curations repo to capture calls
    calls: Dict[str, Any] = {"created": None, "clusters": None, "links": []}

    from app.repositories import curations_repo

    def _create_run(stream_id: str, job_id=None, status="running"):
        calls["created"] = {"stream_id": stream_id, "job_id": job_id, "status": status}
        return {"id": "run-1"}

    def _insert_clusters(run_id: str, clusters: List[Dict[str, Any]]):
        calls["clusters"] = clusters
        # return rows with ids in order
        return [{"id": f"c-{i}", **c} for i, c in enumerate(clusters)]

    def _insert_links(cluster_id: str, links: List[Dict[str, Any]]):
        calls["links"].append({"cluster_id": cluster_id, "links": links})
        return links

    monkeypatch.setattr(curations_repo, "create_curation_run", _create_run)
    monkeypatch.setattr(curations_repo, "insert_clusters", _insert_clusters)
    monkeypatch.setattr(curations_repo, "insert_cluster_links", _insert_links)
    monkeypatch.setattr(curations_repo, "complete_curation_run", lambda *a, **k: None)
    monkeypatch.setattr(curations_repo, "get_previous_context", lambda stream_id: {})

    # Fake urls repo to return ids
    from app.repositories import urls_repo
    monkeypatch.setattr(urls_repo, "ensure_url", lambda url, title=None, domain=None, description=None, published_at=None: {"id": f"url:{url}", "url": url})

    # Fake service client for stream lookup (when params missing)
    class _Row:
        def __init__(self, data):
            self.data = data

    class _Tbl:
        def __init__(self, name):
            self.name = name
            self._eq = None
            self._limit = None
        def select(self, sel):
            return self
        def eq(self, col, val):
            self._eq = (col, val); return self
        def limit(self, n):
            self._limit = n; return self
        def execute(self):
            if self.name == "streams":
                return _Row([{"mission": "Test mission", "sources_hints": None, "cadence": "weekly"}])
            return _Row([])

    class _Client:
        def table(self, name):
            return _Tbl(name)

    import app.supabase_client as sc
    monkeypatch.setattr(sc, "get_service_client", lambda: _Client())

    # Execute a stream run
    from app.agents import search_workflow as sw
    monkeypatch.setattr(sw, "get_exa_client", lambda: FakeExa())
    job = {"id": "job-1", "payload": {"type": "stream_run", "stream_id": "s-1", "params": {}}}
    out = sw.run(job, user_token=None)

    # Validate persistence calls
    assert calls["created"]["stream_id"] == "s-1"
    assert len(calls["clusters"]) >= 1
    assert len(calls["links"]) >= 1
    assert len(calls["links"][0]["links"]) >= 2
