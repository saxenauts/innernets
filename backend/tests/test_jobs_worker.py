from __future__ import annotations

import types


def test_enqueue_claim_execute(monkeypatch):
    # Patch Supabase client to record calls and store rows in-memory
    store = {
        "jobs": [],
        "runs": [],
    }

    class FakeResp:
        def __init__(self, data):
            self.data = data

    class Table:
        def __init__(self, name):
            self.name = name

        def insert(self, row):
            def exec():
                if self.name == "jobs":
                    r = dict(row)
                    r.setdefault("id", f"job-{len(store['jobs'])+1}")
                    store["jobs"].append(r)
                    return FakeResp([r])
                if self.name == "runs":
                    r = dict(row)
                    r.setdefault("id", f"run-{len(store['runs'])+1}")
                    store["runs"].append(r)
                    return FakeResp([r])
                return FakeResp([dict(row)])

            return types.SimpleNamespace(execute=exec)

        def select(self, _):
            # ignore projection
            return self

        def eq(self, field, value):
            self._eq = (field, value)
            return self

        def order(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def execute(self):
            if self.name == "jobs":
                queued = [j for j in store["jobs"] if j.get("status", "queued") == "queued"]
                return FakeResp(list(queued))
            return FakeResp([])

        def update(self, patch):
            def exec():
                if self.name == "jobs":
                    # update by last eq id
                    for j in store["jobs"]:
                        if j.get("id") == getattr(self, "_last_id", None):
                            j.update(patch)
                    return FakeResp([])
                if self.name == "runs":
                    for r in store["runs"]:
                        if r.get("id") == getattr(self, "_last_id", None):
                            r.update(patch)
                    return FakeResp([])
                return FakeResp([])

            return types.SimpleNamespace(execute=exec, eq=self.eq)

        def eq(self, field, value):
            if field == "id":
                self._last_id = value
            return self

    class FakeClient:
        def table(self, name):
            return Table(name)

    from app import supabase_client as sb_mod

    monkeypatch.setattr(sb_mod, "get_service_client", lambda: FakeClient())

    # Import after patch
    from app.scheduler.jobs import enqueue_job
    from app.scheduler.worker import run_once

    # Enqueue a job
    job = enqueue_job(user_id="u1", payload={"agent": "search_only_v1", "params": {"mission": "x"}})
    assert job["user_id"] == "u1"

    # Provide a fake handler that returns metrics
    def handle_job(_job):
        return {"queries": 0, "reads": 0, "cost_exa": 0.0, "usage_tokens": {"prompt": 0, "completion": 0, "total": 0}}

    processed = run_once(handle_job)
    assert processed == 1
