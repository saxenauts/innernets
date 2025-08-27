import os
import pytest


@pytest.mark.live
def test_search_workflow_live_end_to_end():
    # Be pragmatic for now: auto-load .env and proceed if keys are present.
    try:
        from dotenv import load_dotenv
        load_dotenv(os.getenv("DOTENV_PATH", ".env"), override=False)
    except Exception:
        pass
    if not (os.getenv("EXA_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_API_VERSION") and os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")):
        pytest.skip("Missing one or more provider env vars; add them to backend/.env to run live test")

    from app.agents import search_workflow as sw

    job = {
        "payload": {
            "agent": "search_only_v1",
            "params": {
                "mission": "AI tools with persistent user memory & context",
                "hints": ["site:github.com", "recent"],
                "search_type": "keyword",
                "num_results_per_query": 3,
                "read_top_k": 1,
                "max_chars_per_page": 1200,
                "compose_items_limit": 6,
            },
        }
    }

    out = sw.run(job)
    assert out["queries"] >= 1
    assert isinstance(out.get("items"), list)
    # Useful prints for manual verification
    print("Workflow metrics:", out)
