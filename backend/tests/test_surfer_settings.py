from __future__ import annotations

from typing import Any

from app.clients import surfer_client as sc


class _FakeResp:
    def __init__(self, status_code: int = 200, json_data: Any = None):
        self.status_code = status_code
        self._json = json_data or {}

    def json(self):
        return self._json


class _FakeHttpxClient:
    def __init__(self, capture: dict):
        self.capture = capture

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, headers=None, json=None):
        self.capture["url"] = url
        return _FakeResp(200, {"job_id": "j-1"})


def test_surfer_use_mock_routes_to_mock(monkeypatch):
    # Stable base URL
    monkeypatch.setattr(sc, "_base", lambda: "http://localhost:8001")

    captured = {}

    # Patch httpx.Client used inside surfer_client
    import app.clients.surfer_client as sc_mod

    def fake_client_factory(timeout: float):
        return _FakeHttpxClient(captured)

    monkeypatch.setattr(sc_mod.httpx, "Client", fake_client_factory)

    # Pass use_mock=True explicitly to avoid env coupling in tests
    sc.explorer_submit("do it", sync=False, use_mock=True)
    assert "/api/explorer/mock" in captured["url"]


def test_surfer_use_mock_false_targets_jobs(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "SURFER_USE_MOCK", False, raising=False)
    monkeypatch.setattr(sc, "_base", lambda: "http://localhost:8001")
    captured = {}
    import app.clients.surfer_client as sc_mod

    def fake_client_factory(timeout: float):
        return _FakeHttpxClient(captured)

    monkeypatch.setattr(sc_mod.httpx, "Client", fake_client_factory)

    sc.explorer_submit("do it", sync=False)
    assert captured["url"].endswith("/api/explorer/jobs")
