from fastapi.testclient import TestClient
import types

from app.main import app


def _auth_headers():
    # Use deps with dev header bypass if configured; otherwise, simulate a token-less path
    # Our routes use Supabase JWT dependency; for tests, we can monkeypatch if needed.
    # For now, just skip auth by overriding dependency in test client scope.
    return {"Authorization": "Bearer test.jwt.token"}


def test_search_validation_caps(monkeypatch):
    client = TestClient(app)

    # Monkeypatch auth to bypass real JWT verification
    from app import auth as auth_mod

    def fake_get_current_user_id(Authorization: str | None = None) -> str:
        return "user-123"

    app.dependency_overrides[auth_mod.get_current_user_id] = fake_get_current_user_id
    try:
        # Neural with >25 should 400
        resp = client.post(
            "/exa/search",
            json={"query": "q", "type": "neural", "numResults": 26},
            headers=_auth_headers(),
        )
        assert resp.status_code == 400

        # Keyword with 101 should 400
        resp = client.post(
            "/exa/search",
            json={"query": "q", "type": "keyword", "numResults": 101},
            headers=_auth_headers(),
        )
        assert resp.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_search_happy_path(monkeypatch):
    client = TestClient(app)

    from app import auth as auth_mod
    from app.routes import exa as exa_routes

    def fake_get_current_user_id(Authorization: str | None = None) -> str:
        return "user-123"

    app.dependency_overrides[auth_mod.get_current_user_id] = fake_get_current_user_id

    class FakeExa:
        def search_and_contents(self, **kwargs):
            return {
                "requestId": "r1",
                "resolvedSearchType": kwargs.get("type", "auto"),
                "results": [{"title": "t", "url": "u"}],
                "searchType": kwargs.get("type", "auto"),
                "context": None,
                "costDollars": {"total": 0.01},
            }

    # Patch client getter
    from app.routes import exa as exa_routes

    class FakeClient:
        def __init__(self):
            ...

        def search_json(self, body):
            # Simulate SDK output shape after client conversion
            return FakeExa().search_and_contents(**{"type": body.get("type", "auto")})

    monkeypatch.setattr(exa_routes, "get_exa_client", lambda: FakeClient())

    resp = client.post(
        "/exa/search",
        json={"query": "hello", "type": "keyword", "numResults": 10},
        headers=_auth_headers(),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["requestId"] == "r1"
    assert body["provider_cost"]["total"] == 0.01


def test_contents_happy_path(monkeypatch):
    client = TestClient(app)

    from app import auth as auth_mod
    from app.routes import exa as exa_routes

    def fake_get_current_user_id(Authorization: str | None = None) -> str:
        return "user-123"

    app.dependency_overrides[auth_mod.get_current_user_id] = fake_get_current_user_id

    class FakeClient:
        def __init__(self):
            ...

        def contents_json(self, body):
            return {
                "requestId": "r2",
                "results": [{"url": "u", "text": "content"}],
                "costDollars": {"total": 0.02},
            }

    monkeypatch.setattr(exa_routes, "get_exa_client", lambda: FakeClient())

    try:
        resp = client.post(
            "/exa/contents",
            json={"urls": ["https://example.com"], "text": True},
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["requestId"] == "r2"
        assert body["provider_cost"]["total"] == 0.02
    finally:
        app.dependency_overrides.clear()
