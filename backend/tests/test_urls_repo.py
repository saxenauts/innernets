from typing import Any, Dict


def test_urls_repo_ensure_and_bulk(monkeypatch):
    # In-memory table stub
    store: Dict[str, Dict[str, Any]] = {}

    class Result:
        def __init__(self, data):
            self.data = data

    class Table:
        def __init__(self, name):
            self.name = name
            self._op = None
            self._sel = None
            self._eq = None
            self._limit = None
            self._payload = None

        def select(self, sel):
            self._op = "select"; self._sel = sel; return self
        def eq(self, col, val):
            self._eq = (col, val); return self
        def limit(self, n):
            self._limit = n; return self
        def insert(self, payload):
            self._op = "insert"; self._payload = payload; return self
        def update(self, patch):
            self._op = "update"; self._payload = patch; return self
        def execute(self):
            if self._op == "select":
                if self._eq and self._eq[0] == "url":
                    for row in store.values():
                        if row["url"] == self._eq[1]:
                            return Result([row.copy()])
                if self._eq and self._eq[0] == "id":
                    row = store.get(self._eq[1])
                    return Result([row.copy()] if row else [])
                return Result([])
            if self._op == "insert":
                payload = self._payload.copy()
                rid = f"u-{len(store)+1}"
                payload["id"] = rid
                store[rid] = payload
                return Result([payload.copy()])
            if self._op == "update":
                if not self._eq or self._eq[0] != "id":
                    raise AssertionError("update without id eq")
                rid = self._eq[1]
                row = store.get(rid)
                if row:
                    row.update(self._payload)
                return Result([row.copy()] if row else [])
            raise AssertionError("unsupported op")

    class Client:
        def table(self, name):
            assert name == "urls"
            return Table(name)

    from app.repositories import urls_repo
    monkeypatch.setattr(urls_repo, "get_service_client", lambda: Client())

    # Create
    row1 = urls_repo.ensure_url("https://example.com/a", title="A")
    assert row1["id"]
    assert row1["url"] == "https://example.com/a"
    # Idempotent update
    row2 = urls_repo.ensure_url("https://example.com/a", description="desc")
    assert row2["id"] == row1["id"]
    # Bulk
    res = urls_repo.bulk_ensure([
        {"url": "https://example.com/a"},
        {"url": "https://example.com/b", "title": "B"},
    ])
    assert {x["url"] for x in res} == {"https://example.com/a", "https://example.com/b"}

