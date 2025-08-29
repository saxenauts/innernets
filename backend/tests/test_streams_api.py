from fastapi.testclient import TestClient
import jwt


def _auth_headers(user_id: str = "u-123"):
    from app.config import settings
    return {
        "Authorization": "Bearer "
        + jwt.encode({"sub": user_id, "exp": 9999999999, "aud": "authenticated"}, settings.SUPABASE_JWT_SECRET or "testsecret", algorithm="HS256")
    }


def test_update_stream_accepts_sources_alias(monkeypatch):
    # Patch settings secret for JWT encode/verify
    from app.config import settings
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "testsecret", raising=False)

    captured = {}

    def fake_update_stream(stream_id: str, user_id: str, token: str, fields):
        captured["stream_id"] = stream_id
        captured["user_id"] = user_id
        captured["fields"] = fields
        # Simulate DB echo after update
        return {
            "id": stream_id,
            "mission": fields.get("mission"),
            "sources_hints": fields.get("sources_hints"),
            "cadence": fields.get("cadence", "weekly"),
            "time_zone": "UTC",
            "active": True,
        }

    from app.routes import streams as streams_module
    monkeypatch.setattr(streams_module.streams_repo, "update_stream", fake_update_stream)
    # get_stream used by delete; not needed here

    from app.main import app
    app.dependency_overrides.clear()
    client = TestClient(app)

    payload = {"mission": "M1", "sources": "only arXiv", "cadence": "3xweek"}
    r = client.put("/streams/s-1", headers=_auth_headers(), json=payload)
    assert r.status_code == 200
    data = r.json()
    # route accepts 'sources' and forwards to repo; repo may handle mapping
    assert captured["fields"]["sources"] == "only arXiv"
    assert data["mission"] == "M1"
    assert data["cadence"] == "3xweek"


def test_delete_stream_soft(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "testsecret", raising=False)

    calls = {"deleted": None}

    def fake_get_stream(stream_id: str, user_id: str, token: str):
        return {"id": stream_id, "user_id": user_id, "mission": "M", "active": True}

    def fake_delete_stream(stream_id: str, user_id: str, token: str):
        calls["deleted"] = stream_id

    from app.routes import streams as streams_module
    monkeypatch.setattr(streams_module.streams_repo, "get_stream", fake_get_stream)
    monkeypatch.setattr(streams_module.streams_repo, "delete_stream", fake_delete_stream)

    from app.main import app
    app.dependency_overrides.clear()
    client = TestClient(app)

    r = client.delete("/streams/s-2", headers=_auth_headers())
    assert r.status_code == 204
    assert calls["deleted"] == "s-2"
