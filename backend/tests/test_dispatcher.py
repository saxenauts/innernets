from __future__ import annotations

from typing import Any, Dict


def test_dispatcher_prefers_payload_agent(monkeypatch):
    calls: Dict[str, int] = {"surfer": 0, "search": 0}

    # Patch runners
    from app.agents import dispatcher as dp

    def _srf_run(job, user_token=None):
        calls["surfer"] += 1
        return {"agent": "surfer_v1"}

    def _sw_run(job, user_token=None):
        calls["search"] += 1
        return {"agent": "search_only_v1"}

    monkeypatch.setattr(dp.srf, "run", _srf_run)
    monkeypatch.setattr(dp.sw, "run", _sw_run)

    # No need to consult schedule when payload.agent is set
    job = {"payload": {"agent": "search_only_v1"}, "schedule_id": "sched-x"}
    out = dp.handle(job)
    assert out["agent"] == "search_only_v1"
    assert calls["search"] == 1
    assert calls["surfer"] == 0


def test_dispatcher_falls_back_to_schedule_meta_agent(monkeypatch):
    calls: Dict[str, int] = {"surfer": 0, "search": 0}

    from app.agents import dispatcher as dp

    # Fake client that returns schedule meta agent
    class _Resp:
        def __init__(self, data):
            self.data = data

    class _Tbl:
        def __init__(self, name):
            self.name = name
            self._id = None

        def select(self, _):
            return self

        def eq(self, field, value):
            if self.name == "schedules" and field == "id":
                self._id = value
            return self

        def limit(self, *_):
            return self

        def execute(self):
            if self.name == "schedules":
                return _Resp([
                    {"id": self._id, "meta": {"agent": "surfer_v1"}},
                ])
            return _Resp([])

    class _Cli:
        def table(self, name):
            return _Tbl(name)

    def _srf_run(job, user_token=None):
        calls["surfer"] += 1
        return {"agent": "surfer_v1"}

    def _sw_run(job, user_token=None):
        calls["search"] += 1
        return {"agent": "search_only_v1"}

    monkeypatch.setattr(dp, "get_service_client", lambda: _Cli())
    monkeypatch.setattr(dp.srf, "run", _srf_run)
    monkeypatch.setattr(dp.sw, "run", _sw_run)

    job = {"payload": {}, "schedule_id": "sched-1"}
    out = dp.handle(job)
    assert out["agent"] == "surfer_v1"
    assert calls["surfer"] == 1
    assert calls["search"] == 0


def test_dispatcher_alias_engine_and_default(monkeypatch):
    calls: Dict[str, int] = {"surfer": 0, "search": 0}

    from app.agents import dispatcher as dp

    class _Resp:
        def __init__(self, data):
            self.data = data

    class _Tbl:
        def __init__(self, name):
            self.name = name
            self._id = None

        def select(self, _):
            return self

        def eq(self, field, value):
            if self.name == "schedules" and field == "id":
                self._id = value
            return self

        def limit(self, *_):
            return self

        def execute(self):
            if self.name == "schedules":
                # Use alias 'engine' instead of 'agent'
                return _Resp([
                    {"id": self._id, "meta": {"engine": "surfer"}},
                ])
            return _Resp([])

    class _Cli:
        def table(self, name):
            return _Tbl(name)

    def _srf_run(job, user_token=None):
        calls["surfer"] += 1
        return {"agent": "surfer_v1"}

    def _sw_run(job, user_token=None):
        calls["search"] += 1
        return {"agent": "search_only_v1"}

    monkeypatch.setattr(dp, "get_service_client", lambda: _Cli())
    monkeypatch.setattr(dp.srf, "run", _srf_run)
    monkeypatch.setattr(dp.sw, "run", _sw_run)

    # Unknown payload.agent → fallback to schedule meta (engine alias), which resolves to surfer
    job = {"payload": {"agent": ""}, "schedule_id": "sched-2"}
    out = dp.handle(job)
    assert out["agent"] == "surfer_v1"
    assert calls["surfer"] == 1

    # Unknown agent everywhere should default to surfer (empty schedule meta)
    class _TblEmpty:
        def __init__(self, name):
            self.name = name
        def select(self, _):
            return self
        def eq(self, *_):
            return self
        def limit(self, *_):
            return self
        def execute(self):
            return _Resp([])
    class _CliEmpty:
        def table(self, name):
            return _TblEmpty(name)
    monkeypatch.setattr(dp, "get_service_client", lambda: _CliEmpty())
    job2 = {"payload": {"agent": "unknown"}, "schedule_id": "sched-3"}
    out2 = dp.handle(job2)
    assert out2["agent"] == "surfer_v1"
    assert calls["surfer"] == 2
