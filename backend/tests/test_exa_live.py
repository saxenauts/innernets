import os
import pytest


@pytest.mark.live
def test_exa_live_search_and_contents():
    if not os.getenv("RUN_LIVE_EXA_TESTS"):
        pytest.skip("Set RUN_LIVE_EXA_TESTS=1 to run live Exa tests")
    if not os.getenv("EXA_API_KEY"):
        pytest.skip("Missing EXA_API_KEY in environment")

    from app.clients.exa_client import get_exa_client

    exa = get_exa_client()
    # Keep costs tiny: few results, keyword search, text only
    data = exa.search_and_contents(
        query="latest banana model from google",
        type="keyword",
        num_results=3,
        text={"max_characters": 1500},
    )
    results = data.results or []
    assert len(results) >= 1
    url = results[0].url
    assert url and isinstance(url, str)

    body2 = exa.get_contents(urls=[url], text={"max_characters": 1500})
    # Print a small slice so we can see output when -s is used
    first = (body2.results or [])[0] if body2.results else None
    if first and first.text:
        print("EXA_FIRST_URL:", url)
        print("EXA_FIRST_TEXT_SNIPPET:", first.text[:200])
    assert isinstance(body2.results, list)
