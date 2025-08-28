import os
import json
import pytest
from urllib.parse import urlparse


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc
    except Exception:
        return ""


@pytest.mark.live
def test_live_full_trace_personal_ai_dashboard_companies():
    if os.getenv("RUN_LIVE_OPENAI_TESTS") != "1":
        print("[live-test] RUN_LIVE_OPENAI_TESTS is not '1'; skipping live full-trace test")
        pytest.skip("Set RUN_LIVE_OPENAI_TESTS=1 to run live full-trace test")

    # Load .env if present
    try:
        from dotenv import load_dotenv
        load_dotenv(os.getenv("DOTENV_PATH", ".env"), override=False)
    except Exception:
        pass

    # Require env
    missing = [k for k in [
        "EXA_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_DEPLOYMENT_NAME",
    ] if not os.getenv(k)]
    if missing:
        pytest.skip("Missing env: " + ", ".join(missing))

    # Imports
    from app.llm.types import ProviderConfig, InvokeOptions, JsonSchema, StructuredRequest
    from app.llm.adapter import structured
    from app.llm import prompts
    from app.llm import search_steps as steps
    from app.clients.exa_client import get_exa_client
    from app.clients.exa_schemas import SearchResponse

    cfg = ProviderConfig.from_env("azure_openai")
    exa = get_exa_client()

    mission = "personal AI dashboard companies"
    additional_ctx = {}

    def _id(n: int) -> str:
        return str(n).zfill(2)

    print("\n===== STEP 1: GENERATE QUERIES =====")
    user_text = prompts.GENERATE_SEARCH_QUERIES
    user_text = user_text.replace("{{mission}}", mission)
    user_text = user_text.replace("{{additional_context_json}}", json.dumps(additional_ctx, ensure_ascii=False))
    print("[LLM user message]\n" + user_text)

    req = StructuredRequest(
        instruction=prompts.SYSTEM_PREAMBLE + "\n\n" + user_text,
        context=None,
        schema_name="GenerateQueriesOut",
        out_schema=JsonSchema(properties={}, required=[]),
        pydantic_model=steps.GenerateQueriesOut,
    )
    res1 = structured(cfg, req, InvokeOptions(temperature=1.0, max_tokens=512))
    print("[LLM raw output]", json.dumps(res1.output, indent=2))
    q_out = steps.GenerateQueriesOut(**res1.output)
    queries = q_out.queries
    print("[Parsed queries]", [q.model_dump() for q in queries])

    print("\n===== STEP 2: EXA SEARCH (per query) =====")
    id_to_url = {}
    id_to_meta = {}
    next_id = 1
    all_results = []
    for qi in queries:
        sr: SearchResponse = exa.search(
            query=qi.query,
            type=qi.query_type,
            num_results=25,
        )
        print(f"[Exa] query='{qi.query}' type='{qi.query_type}' results={len(sr.results or [])}")
        all_results.extend(sr.results or [])

    # Dedup by URL
    seen = set()
    deduped = []
    for r in all_results:
        if not r.url or r.url in seen:
            continue
        seen.add(r.url)
        deduped.append(r)
    print(f"[Exa] deduped results={len(deduped)}")

    candidates = []
    for r in deduped:
        rid = _id(next_id); next_id += 1
        id_to_url[rid] = r.url
        meta = {
            "id": rid,
            "title": r.title or "",
            "domain": _domain(r.url),
            "url": r.url,
            "snippet": "",
            "published_at": getattr(r, "publishedDate", None),
        }
        id_to_meta[rid] = meta
        if len(candidates) < 30:
            candidates.append({k: v for k, v in meta.items() if k != "url"})
    print("[Candidates → LLM]", json.dumps(candidates, indent=2))

    print("\n===== STEP 3: FILTER CANDIDATES (LLM) =====")
    user_text = prompts.FILTER_CANDIDATES
    user_text = user_text.replace("{{mission}}", mission)
    user_text = user_text.replace("{{candidates_json}}", json.dumps(candidates, ensure_ascii=False))
    user_text = user_text.replace("{{additional_context_json}}", json.dumps(additional_ctx, ensure_ascii=False))
    print("[LLM user message]\n" + user_text)

    req2 = StructuredRequest(
        instruction=prompts.SYSTEM_PREAMBLE + "\n\n" + user_text,
        context=None,
        schema_name="FilterCandidatesOut",
        out_schema=JsonSchema(properties={}, required=[]),
        pydantic_model=steps.FilterCandidatesOut,
    )
    res2 = structured(cfg, req2, InvokeOptions(temperature=1.0, max_tokens=256))
    print("[LLM raw output]", json.dumps(res2.output, indent=2))
    selected = steps.FilterCandidatesOut(**res2.output)
    selected_ids = selected.selected_ids
    if len(selected_ids) < 2:
        selected_ids = [candidates[i]["id"] for i in range(min(2, len(candidates)))]
    print("[Selected IDs]", selected_ids)

    print("\n===== STEP 4: EXA CONTENTS (READ) =====")
    read_urls = [id_to_url[sid] for sid in selected_ids]
    print("[Exa get_contents URLs]", read_urls)
    contents = exa.get_contents(urls=read_urls, text={"max_characters": 15000})
    read_summaries = []
    url_to_text = {}
    for r in contents.results or []:
        url_to_text[r.url] = (r.title or "", (r.text or "").strip())
    for sid in selected_ids:
        u = id_to_url[sid]
        title, body = url_to_text.get(u, (id_to_meta[sid]["title"], ""))
        read_summaries.append({"id": sid, "title": title, "domain": id_to_meta[sid]["domain"], "summary": (body or "")[:800]})
    print("[Read summaries]", json.dumps(read_summaries, indent=2))

    print("\n===== STEP 5: PROPOSE FOLLOWUPS (LLM) =====")
    initial_queries_json = [q.model_dump(mode="json") for q in queries]
    user_text = prompts.PROPOSE_FOLLOWUPS
    user_text = user_text.replace("{{mission}}", mission)
    user_text = user_text.replace("{{initial_queries_json}}", json.dumps(initial_queries_json, ensure_ascii=False))
    user_text = user_text.replace("{{read_summaries_json}}", json.dumps(read_summaries, ensure_ascii=False))
    user_text = user_text.replace("{{additional_context_json}}", json.dumps(additional_ctx, ensure_ascii=False))
    user_text = user_text.replace("{{prior_urls_json}}", json.dumps([], ensure_ascii=False))
    print("[LLM user message]\n" + user_text)

    req3 = StructuredRequest(
        instruction=prompts.SYSTEM_PREAMBLE + "\n\n" + user_text,
        context=None,
        schema_name="ProposeFollowupsOut",
        out_schema=JsonSchema(properties={}, required=[]),
        pydantic_model=steps.ProposeFollowupsOut,
    )
    res3 = structured(cfg, req3, InvokeOptions(temperature=1.0, max_tokens=512))
    print("[LLM raw output]", json.dumps(res3.output, indent=2))
    follow = steps.ProposeFollowupsOut(**res3.output)
    followups = follow.followups
    print("[Parsed followups]", [f.model_dump() for f in followups])

    print("\n===== STEP 6: EXA SEARCH (FOLLOWUPS) =====")
    all_items = [
        {"id": it["id"], "title": it["title"], "domain": it["domain"], "snippet_or_summary": it.get("summary", "")}
        for it in read_summaries
    ]
    for fi in followups:
        sr: SearchResponse = exa.search(query=fi.query, type=fi.query_type, num_results=25)
        print(f"[Exa] followup='{fi.query}' type='{fi.query_type}' results={len(sr.results or [])}")
        for r in (sr.results or [])[:10]:
            rid = _id(next_id); next_id += 1
            id_to_url[rid] = r.url
            id_to_meta[rid] = {
                "id": rid,
                "title": r.title or "",
                "domain": _domain(r.url or ""),
                "url": r.url,
            }
            all_items.append({
                "id": rid,
                "title": id_to_meta[rid]["title"],
                "domain": id_to_meta[rid]["domain"],
                "snippet_or_summary": "",
            })
    print("[All items → consolidation]", json.dumps(all_items[:20], indent=2))

    print("\n===== STEP 7: CONSOLIDATE CURATIONS (LLM) =====")
    user_text = prompts.CONSOLIDATE_CURATIONS
    user_text = user_text.replace("{{mission}}", mission)
    user_text = user_text.replace("{{all_items_json}}", json.dumps(all_items, ensure_ascii=False))
    user_text = user_text.replace("{{additional_context_json}}", json.dumps(additional_ctx, ensure_ascii=False))
    print("[LLM user message]\n" + user_text)

    req4 = StructuredRequest(
        instruction=prompts.SYSTEM_PREAMBLE + "\n\n" + user_text,
        context=None,
        schema_name="ConsolidateOut",
        out_schema=JsonSchema(properties={}, required=[]),
        pydantic_model=steps.ConsolidateOut,
    )
    res4 = structured(cfg, req4, InvokeOptions(temperature=1.0, max_tokens=768))
    print("[LLM raw output]", json.dumps(res4.output, indent=2))
    cons = steps.ConsolidateOut(**res4.output)
    print("[Curations]", json.dumps([c.model_dump() for c in cons.curations], indent=2))

    # Sanity assertions
    assert len(queries) == 10
    assert len(cons.curations) >= 1
