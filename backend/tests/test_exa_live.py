import os
import time

import pytest
from fastapi.testclient import TestClient


@pytest.mark.live
def test_exa_live_search_and_contents():
    if not os.getenv("RUN_LIVE_EXA_TESTS"):
        pytest.skip("Set RUN_LIVE_EXA_TESTS=1 to run live Exa tests")
    if not os.getenv("EXA_API_KEY"):
        pytest.skip("Missing EXA_API_KEY in environment")

    from app.main import app
    from app import auth as auth_mod

    # Bypass Supabase JWT verification for local live run
    app.dependency_overrides[auth_mod.get_current_user_id] = lambda Authorization=None: "live-user"
    client = TestClient(app)

    # Keep costs tiny: 1 result, keyword search, text only
    payload = {
        "query": "arxiv 2307.06435 Large Language Models",
        "type": "keyword",
        "numResults": 1,
        "contents": {"text": {"maxCharacters": 2000}},
    }

    r = client.post("/exa/search", json=payload, headers={"Authorization": "Bearer dummy"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("provider_cost") is not None
    results = data.get("results") or []
    assert len(results) >= 1
    first = results[0]
    assert "url" in first

    # Contents endpoint on the first URL (cheap: 1 page, text only)
    url = first["url"]
    r2 = client.post(
        "/exa/contents",
        json={"urls": [url], "text": {"maxCharacters": 2000}},
        headers={"Authorization": "Bearer dummy"},
    )
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert body2.get("provider_cost") is not None
    assert isinstance(body2.get("results"), list)
    # Clear overrides
    app.dependency_overrides.clear()

