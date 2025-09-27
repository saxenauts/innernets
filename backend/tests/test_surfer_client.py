from __future__ import annotations

import time
import types
import pytest

from app.clients import surfer_client as sc


def test_wait_for_result_success(monkeypatch):
    # completed state then result available
    monkeypatch.setattr(sc, "job_status", lambda job_id: {"state": "completed"})
    payload = {"curations": [{"summary": "ok", "links": [{"url": "https://x.com"}]}]}
    monkeypatch.setattr(sc, "job_result", lambda job_id: payload)
    out = sc.wait_for_result("job-1", poll_interval_s=0, max_wait_s=1)
    assert out == payload


def test_wait_for_result_409_then_ready(monkeypatch):
    # completed then first result call 409, second returns data
    monkeypatch.setattr(sc, "job_status", lambda job_id: {"state": "completed"})
    calls = {"result": 0}

    def _job_result(_job_id):
        calls["result"] += 1
        if calls["result"] == 1:
            raise sc.SurferError("Result not ready (409)")
        return {"curations": [1]}

    monkeypatch.setattr(sc, "job_result", _job_result)
    out = sc.wait_for_result("job-2", poll_interval_s=0, max_wait_s=1)
    assert out.get("curations") == [1]
    assert calls["result"] >= 2


def test_wait_for_result_timeout(monkeypatch):
    # Always running; enforce a tiny max_wait_s to trigger timeout
    monkeypatch.setattr(sc, "job_status", lambda job_id: {"state": "running"})
    with pytest.raises(sc.SurferError) as ei:
        sc.wait_for_result("job-3", poll_interval_s=0, max_wait_s=0.01)
    assert "Timeout" in str(ei.value)


def test_wait_for_result_failed_state(monkeypatch):
    monkeypatch.setattr(sc, "job_status", lambda job_id: {"state": "failed"})
    with pytest.raises(sc.SurferError) as ei:
        sc.wait_for_result("job-4", poll_interval_s=0, max_wait_s=1)
    assert "ended as failed" in str(ei.value)

