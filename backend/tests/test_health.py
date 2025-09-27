from fastapi.testclient import TestClient
from app.main import app
import app.main as main_mod


client = TestClient(app)


def test_healthz_ok(monkeypatch):
    # Simulate Surfer healthy
    class _FakeResp:
        status_code = 200

    class _FakeClient:
        def __init__(self, timeout: float):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url):
            return _FakeResp()

    monkeypatch.setattr(main_mod.httpx, "Client", _FakeClient)
    r = client.get("/healthz")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data.get("surfer_ok") is True


def test_root_metadata():
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "innernets-backend"
    assert body["status"] == "ready"
