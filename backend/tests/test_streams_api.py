from fastapi.testclient import TestClient
import jwt


def _make_token(sub: str = "u-1") -> str:
    from app.config import settings
    return jwt.encode({"sub": sub, "exp": 9999999999, "aud": settings.SUPABASE_JWT_AUD}, settings.SUPABASE_JWT_SECRET or "testsecret", algorithm="HS256")


def test_create_and_get_streams(monkeypatch):
    # Patch auth secret for tests
    from app.config import settings
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "testsecret", raising=False)

    # Fakes
    created = {
        "id": "s-1",
        "user_id": "u-1",
        "mission": "Find great papers",
        "sources_hints": "prefer arXiv",
        "cadence": "weekly",
        "time_zone": "UTC",
        "active": True,
        "created_at": "2025-08-29T00:00:00Z",
        "updated_at": "2025-08-29T00:00:00Z",
    }

    from app.routes import streams as streams_module

    monkeypatch.setattr(streams_module.streams_repo, "create_stream", lambda uid, tok, fields: created)
    monkeypatch.setattr(streams_module.streams_repo, "list_streams", lambda uid, tok: [created])
    monkeypatch.setattr(streams_module.streams_repo, "get_stream", lambda sid, uid, tok: created if sid == "s-1" else None)

    # latest
    latest = {
        "id": "r-1",
        "started_at": "2025-08-29T01:00:00Z",
        "finished_at": "2025-08-29T01:05:00Z",
        "clusters": [
            {"id": "c-1", "title": "Cluster A", "hook": "Why it matters", "position": 0, "links": [{"url": "https://x.com", "domain": "x.com"}]}
        ],
    }
    monkeypatch.setattr(streams_module.curations_repo, "get_latest_run", lambda sid: latest if sid == "s-1" else None)
    monkeypatch.setattr(streams_module.jobs_repo, "enqueue_job", lambda user_id, payload, schedule_id=None, idempotency_key=None: {"id": "j-1", "status": "queued"})

    from app.main import app
    app.dependency_overrides.clear()
    client = TestClient(app)
    token = _make_token("u-1")
    headers = {"Authorization": f"Bearer {token}"}

    # Create
    r = client.post("/streams", json={"mission": "Find great papers", "cadence": "weekly", "sources_hints": "prefer arXiv"}, headers=headers)
    assert r.status_code == 201
    assert r.json()["id"] == "s-1"

    # List
    r = client.get("/streams", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["id"] == "s-1"
    assert data[0]["latest_run_at"] == "2025-08-29T01:00:00Z"

    # Get by id
    r = client.get("/streams/s-1", headers=headers)
    assert r.status_code == 200
    assert r.json()["mission"] == "Find great papers"

    # Update
    monkeypatch.setattr(streams_module.streams_repo, "update_stream", lambda sid, uid, tok, fields: {**created, **fields})
    r = client.put("/streams/s-1", json={"cadence": "daily"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["cadence"] == "daily"

    # Run now
    r = client.post("/streams/s-1/run", headers=headers)
    assert r.status_code == 202
    assert r.json()["status"] == "queued"

    # Latest
    r = client.get("/streams/s-1/latest", headers=headers)
    assert r.status_code == 200
    latest_json = r.json()
    assert latest_json["run_id"] == "r-1"
    assert latest_json["curations"][0]["title"] == "Cluster A"

