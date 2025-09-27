from fastapi.testclient import TestClient
import jwt


def _auth_headers(user_id: str = "u-123"):
    from app.config import settings
    return {
        "Authorization": "Bearer "
        + jwt.encode({"sub": user_id, "exp": 9999999999, "aud": "authenticated"}, settings.SUPABASE_JWT_SECRET or "testsecret", algorithm="HS256")
    }


def test_create_stream_invalid_cadence_422(monkeypatch):
    # Ensure JWT secret is set for test token
    from app.config import settings
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "testsecret", raising=False)

    from app.main import app
    app.dependency_overrides.clear()
    client = TestClient(app)

    payload = {"mission": "M1", "sources": "arXiv only", "cadence": "hourly"}  # invalid per enum
    r = client.post("/streams", headers=_auth_headers(), json=payload)
    assert r.status_code == 422


def test_create_stream_success_shape(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "testsecret", raising=False)

    def fake_create_stream(user_id: str, token: str, fields):
        assert fields["cadence"] == "weekly"
        return {
            "id": "s-1",
            "user_id": user_id,
            "mission": fields.get("mission"),
            "sources_hints": fields.get("sources") or fields.get("sources_hints"),
            "cadence": fields.get("cadence", "weekly"),
            "time_zone": fields.get("time_zone") or "UTC",
            "active": True,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

    from app.routes import streams as streams_module
    monkeypatch.setattr(streams_module.streams_repo, "create_stream", fake_create_stream)

    from app.main import app
    app.dependency_overrides.clear()
    client = TestClient(app)

    payload = {"mission": "M1", "sources": "arXiv only", "cadence": "weekly"}
    r = client.post("/streams", headers=_auth_headers(), json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["id"] == "s-1"
    assert data["mission"] == "M1"
    # expose sources (not sources_hints)
    assert data["sources"] == "arXiv only"
    assert "sources_hints" not in data


def test_list_runs_shape_and_next_cursor(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "testsecret", raising=False)

    from app.routes import streams as streams_module

    def fake_get_stream(stream_id: str, user_id: str, token: str):
        return {"id": stream_id, "user_id": user_id, "mission": "M", "active": True}

    def fake_get_runs(stream_id: str, limit: int = 10, before_started_at=None):
        return [
            {
                "id": "r-1",
                "stream_id": stream_id,
                "started_at": "2025-01-01T00:00:00Z",
                "finished_at": "2025-01-01T00:10:00Z",
                "clusters": [
                    {
                        "id": "c-1",
                        "run_id": "r-1",
                        "title": "T1",
                        "hook": "H1",
                        "body_md": "B1",
                        "position": 0,
                        "links": [
                            {"url": "https://example.com/a", "domain": "example.com", "title": "A", "position": 0}
                        ],
                    }
                ],
            },
            {
                "id": "r-0",
                "stream_id": stream_id,
                "started_at": "2024-12-31T23:00:00Z",
                "finished_at": "2024-12-31T23:05:00Z",
                "clusters": [],
            },
        ]

    monkeypatch.setattr(streams_module.streams_repo, "get_stream", fake_get_stream)
    from app.repositories import curations_repo as cur_repo
    monkeypatch.setattr(cur_repo, "get_runs", fake_get_runs)

    from app.main import app
    app.dependency_overrides.clear()
    client = TestClient(app)

    r = client.get("/streams/s-1/runs?limit=2", headers=_auth_headers())
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body.get("runs"), list) and len(body["runs"]) == 2
    first = body["runs"][0]
    assert "curations" in first and isinstance(first["curations"], list)
    assert first["curations"][0]["links"][0]["url"].startswith("https://")
    assert body["next_cursor"] == body["runs"][-1]["started_at"]

