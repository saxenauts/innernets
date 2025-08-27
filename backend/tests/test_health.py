from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_healthz_ok():
    r = client.get("/healthz")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True


def test_root_metadata():
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "innernets-backend"
    assert body["status"] == "ready"
