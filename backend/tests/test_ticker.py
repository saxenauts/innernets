from __future__ import annotations

from datetime import datetime, timezone, timedelta
import types


def _fake_now():
    return datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_ticker_enqueues_and_advances(monkeypatch):
    store = {"schedules": [], "jobs": []}

    class FakeResp:
        def __init__(self, data):
            self.data = data

    class Table:
        def __init__(self, name):
            self.name = name
            self._filters = []
            self._order = None
            self._limit = None
            self._last_id = None

        def select(self, _):
            return self

        def eq(self, field, value):
            if field == "id":
                self._last_id = value
            else:
                self._filters.append((field, value))
            return self

        def lte(self, field, value):
            self._filters.append((field, ("<=", value)))
            return self

        def gte(self, field, value):
            self._filters.append((field, (">=", value)))
            return self

        def order(self, *_args, **_kwargs):
            return self

        def limit(self, n):
            self._limit = n
            return self

        def execute(self):
            if self.name == "schedules":
                nowiso = _fake_now().isoformat()
                data = [s for s in store["schedules"] if s.get("active", True) and s.get("next_run_at", nowiso) <= nowiso]
                return FakeResp(data[: self._limit or len(data)])
            if self.name == "jobs":
                return FakeResp([j for j in store["jobs"]])
            return FakeResp([])

        def update(self, patch):
            # Return a chainable object whose eq() returns itself, and whose execute() applies patch
            chain = types.SimpleNamespace()

            def _eq(field, value):
                if field == "id":
                    self._last_id = value
                return chain

            def _execute():
                if self.name == "schedules":
                    for s in store["schedules"]:
                        if s.get("id") == self._last_id:
                            s.update(patch)
                    return FakeResp([])
                if self.name == "jobs":
                    for j in store["jobs"]:
                        if j.get("id") == self._last_id:
                            j.update(patch)
                    return FakeResp([])
                return FakeResp([])

            chain.eq = _eq
            chain.execute = _execute
            return chain

        def upsert(self, row, on_conflict=None):
            def exec():
                if self.name == "jobs":
                    key = row.get("idempotency_key")
                    if key:
                        for j in store["jobs"]:
                            if j.get("idempotency_key") == key:
                                return FakeResp([j])
                    r = dict(row)
                    r.setdefault("id", f"job-{len(store['jobs'])+1}")
                    store["jobs"].append(r)
                    return FakeResp([r])
                return FakeResp([row])

            return types.SimpleNamespace(execute=exec)

        def insert(self, row):
            def exec():
                if self.name == "jobs":
                    r = dict(row)
                    r.setdefault("id", f"job-{len(store['jobs'])+1}")
                    store["jobs"].append(r)
                    return FakeResp([r])
                return FakeResp([row])

            return types.SimpleNamespace(execute=exec)

    class FakeClient:
        def table(self, name):
            return Table(name)

    # Patch all call sites that may hold bound references
    from app import supabase_client as sb_mod
    monkeypatch.setattr(sb_mod, "get_service_client", lambda: FakeClient())
    import app.scheduler.jobs as jobs_mod
    monkeypatch.setattr(jobs_mod, "get_service_client", lambda: FakeClient())

    # Seed one due schedule
    store["schedules"].append({
        "id": "sch-1",
        "user_id": "u1",
        "name": "test",
        "cadence": "PT30M",
        "time_zone": "UTC",
        "active": True,
        "next_run_at": _fake_now().isoformat(),
    })

    # Patch ticker's now
    import app.scheduler.ticker as ticker
    monkeypatch.setattr(ticker, "get_service_client", lambda: FakeClient())
    monkeypatch.setattr(ticker, "datetime", types.SimpleNamespace(now=lambda tz=None: _fake_now(), timezone=timezone, timedelta=timedelta))

    enq = ticker.tick(max_jobs=5)
    assert len(enq) == 1
    # schedule should have next_run_at advanced by 30 minutes
    next_run = store["schedules"][0]["next_run_at"]
    assert next_run > _fake_now().isoformat()
