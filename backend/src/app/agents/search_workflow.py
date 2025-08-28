from __future__ import annotations

"""Deterministic search workflow orchestrator (ID-first, schema-first).

Flow (KISS loop compliant):
  1) Generate 10 search queries (LLM) with routing hints (keyword|neural)
  2) Exa search per query (25 results each), assign short IDs ("01", "02", ...)
  3) Filter candidates (LLM) → select 2–3 IDs to read
  4) Read contents for selected IDs (Exa)
  5) Propose 3–6 follow-up queries (LLM)
  6) Exa search for follow-ups (continue ID numbering)
  7) Consolidate into curations (LLM): title, hook, 3–4 link_ids each

LLMs never see raw URLs, only short IDs; the orchestrator maps IDs to URLs.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
import logging
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.clients.exa_client import get_exa_client
from app.clients.exa_schemas import SearchResponse, ContentsResponse, ResultWithContent
from app.llm.types import ProviderConfig, InvokeOptions
from app.llm import search_steps as steps


class SearchJobParams(BaseModel):
    mission: str = Field(..., description="User mission/intent for the search workflow")
    include_domains: List[str] = Field(default_factory=list)
    exclude_domains: List[str] = Field(default_factory=list)
    # fixed fanout and routing live in steps; allow overrides cautiously
    num_results_per_query: int = Field(default=25, ge=1, le=25)
    read_top_k: int = Field(default=2, ge=0, le=5)
    max_chars_per_page: int = Field(default=15000, ge=200, le=200_000)


class SearchWorkflowResult(BaseModel):
    queries: List[steps.QueryItem] = Field(default_factory=list)
    followups: List[steps.FollowupItem] = Field(default_factory=list)
    curations: List[Dict[str, Any]] = Field(default_factory=list)
    reads: int = 0
    cost_exa: float = 0.0
    usage_tokens: Dict[str, int] = Field(default_factory=lambda: {"prompt": 0, "completion": 0, "total": 0})


def _domain(url: Optional[str]) -> str:
    if not url:
        return ""
    try:
        return urlparse(url).netloc or ""
    except Exception:
        return ""


def _dedupe_by_url(results: List[ResultWithContent]) -> List[ResultWithContent]:
    seen: Set[str] = set()
    out: List[ResultWithContent] = []
    for r in results:
        u = (r.url or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(r)
    return out


def _id(n: int) -> str:
    return str(n).zfill(2)


def _exa_search(
    exa,
    queries: List[steps.QueryItem],
    include_domains: List[str],
    exclude_domains: List[str],
    num_results: int,
) -> Tuple[List[ResultWithContent], float, List[Dict[str, Any]]]:
    all_results: List[ResultWithContent] = []
    cost_calls: List[Dict[str, Any]] = []
    cost_search_total = 0.0
    for qi in queries:
        sr: SearchResponse = exa.search(
            query=qi.query,
            type=qi.query_type,
            num_results=num_results,
            include_domains=include_domains or None,
            exclude_domains=exclude_domains or None,
        )
        if sr.provider_cost and sr.provider_cost.total is not None:
            t = float(sr.provider_cost.total or 0.0)
            cost_search_total += t
            cost_calls.append({"type": "search", "total": t})
        if sr.results:
            all_results.extend(sr.results)
    return all_results, cost_search_total, cost_calls


def _assign_ids(
    results: List[ResultWithContent],
    start_id: int,
    keep_for_llm: int = 30,
) -> Tuple[int, Dict[str, str], Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    id_to_url: Dict[str, str] = {}
    id_to_meta: Dict[str, Dict[str, Any]] = {}
    candidates_ctx: List[Dict[str, Any]] = []
    next_id = start_id
    for r in results:
        if not r.url:
            continue
        rid = _id(next_id)
        next_id += 1
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
        if len(candidates_ctx) < keep_for_llm:
            candidates_ctx.append({k: v for k, v in meta.items() if k != "url"})
    return next_id, id_to_url, id_to_meta, candidates_ctx


def _read_contents(
    exa,
    selected_ids: List[str],
    id_to_url: Dict[str, str],
    id_to_meta: Dict[str, Dict[str, Any]],
    max_chars: int,
) -> Tuple[List[Dict[str, Any]], Optional[ContentsResponse], float, List[Dict[str, Any]]]:
    to_read_urls = [id_to_url[sid] for sid in selected_ids if sid in id_to_url]
    if not to_read_urls:
        return [], None, 0.0, []
    contents: ContentsResponse = exa.get_contents(urls=to_read_urls, text={"max_characters": max_chars})
    cost = 0.0
    calls: List[Dict[str, Any]] = []
    if contents and contents.provider_cost and contents.provider_cost.total is not None:
        cost = float(contents.provider_cost.total or 0.0)
        calls.append({"type": "contents", "total": cost})
    read_summaries: List[Dict[str, Any]] = []
    if contents and contents.results:
        url_to_text: Dict[str, Tuple[str, str]] = {}
        for r in contents.results:
            if r and r.url:
                url_to_text[r.url] = (r.title or "", (r.text or "").strip())
        for sid in selected_ids:
            url = id_to_url.get(sid)
            title, body = url_to_text.get(url, (id_to_meta[sid]["title"], ""))
            read_summaries.append({
                "id": sid,
                "title": title,
                "domain": id_to_meta[sid]["domain"],
                "summary": (body or "")[:800],
            })
    return read_summaries, contents, cost, calls


def _search_followups(
    exa,
    followups: List[steps.FollowupItem],
    next_id: int,
    id_to_url: Dict[str, str],
    id_to_meta: Dict[str, Dict[str, Any]],
    include_domains: List[str],
    exclude_domains: List[str],
    num_results: int,
) -> Tuple[int, List[Dict[str, Any]], float, List[Dict[str, Any]]]:
    all_items_for_consolidation: List[Dict[str, Any]] = []
    cost = 0.0
    calls: List[Dict[str, Any]] = []
    for fi in followups:
        sr2: SearchResponse = exa.search(
            query=fi.query,
            type=fi.query_type,
            num_results=num_results,
            include_domains=include_domains or None,
            exclude_domains=exclude_domains or None,
        )
        if sr2.provider_cost and sr2.provider_cost.total is not None:
            t = float(sr2.provider_cost.total or 0.0)
            cost += t
            calls.append({"type": "search", "total": t})
        if not (sr2 and sr2.results):
            continue
        for r in _dedupe_by_url(list(sr2.results)):
            if not r.url:
                continue
            rid = _id(next_id)
            next_id += 1
            id_to_url[rid] = r.url
            id_to_meta[rid] = {
                "id": rid,
                "title": r.title or "",
                "domain": _domain(r.url),
                "url": r.url,
                "snippet": "",
                "published_at": getattr(r, "publishedDate", None),
            }
            all_items_for_consolidation.append(
                {
                    "id": rid,
                    "title": id_to_meta[rid]["title"],
                    "domain": id_to_meta[rid]["domain"],
                    "snippet_or_summary": "",
                }
            )
    return next_id, all_items_for_consolidation, cost, calls


def run(job: Dict[str, Any], user_token: Optional[str] = None) -> Dict[str, Any]:
    payload = job.get("payload") or {}
    params_raw = payload.get("params") or {}
    try:
        params = SearchJobParams(**params_raw)
    except Exception as e:
        # Fallback to a minimal default mission so the worker doesn't crash
        params = SearchJobParams(mission=str(params_raw or "Web research mission"))

    # Provider config for LLM
    cfg = ProviderConfig.from_env()
    opts = InvokeOptions(temperature=1.0, max_tokens=512)

    # Usage accumulator (LLM)
    usage_total = {"prompt": 0, "completion": 0, "total": 0}

    # 1) Generate search queries (LLM, 10 items)
    q_out = steps.generate_search_queries(cfg, params.mission, additional_context={}, options=opts)
    queries: List[steps.QueryItem] = list(q_out.queries or [])
    if not queries:
        # Safety fallback: 10 copies of mission as keyword
        queries = [steps.QueryItem(query=params.mission, query_type="keyword") for _ in range(10)]

    # Exa accumulators
    exa = get_exa_client()
    cost_calls: List[Dict[str, Any]] = []
    cost_search_total = 0.0
    cost_contents_total = 0.0
    cost_exa = 0.0

    # 2) Exa search and ID assignment
    initial_results, cst, calls = _exa_search(
        exa,
        queries,
        include_domains=params.include_domains,
        exclude_domains=params.exclude_domains,
        num_results=params.num_results_per_query,
    )
    cost_search_total += cst
    cost_exa += cst
    cost_calls.extend(calls)
    initial_results = _dedupe_by_url(initial_results)
    next_id = 1
    next_id, id_to_url, id_to_meta, candidates_ctx = _assign_ids(initial_results, next_id, keep_for_llm=30)

    # 3) Filter candidates (LLM) → select 2–3 IDs
    filt_out = steps.filter_candidates(cfg, params.mission, candidates=candidates_ctx, additional_context={}, options=InvokeOptions(temperature=1.0, max_tokens=256))
    selected_ids = [sid for sid in (filt_out.selected_ids or []) if sid in id_to_url]
    if len(selected_ids) < 2:
        # Fallback: take first two candidates if available
        selected_ids = [candidates_ctx[i]["id"] for i in range(min(2, len(candidates_ctx)))]

    # 4) Read contents for selected IDs
    read_summaries, contents, cst, calls = _read_contents(
        exa,
        selected_ids,
        id_to_url,
        id_to_meta,
        params.max_chars_per_page,
    )
    cost_contents_total += cst
    cost_exa += cst
    cost_calls.extend(calls)

    # 5) Propose follow-ups (LLM)
    follow_out = steps.propose_followups(
        cfg,
        params.mission,
        initial_queries=queries,
        filtered_ids=selected_ids,
        read_summaries=read_summaries,
        additional_context={},
        prior_urls=[],
        options=InvokeOptions(temperature=1.0, max_tokens=512),
    )
    followups: List[steps.FollowupItem] = list(follow_out.followups or [])

    # 6) Second search on follow-ups (continue IDs)
    # include read summaries first
    all_items_for_consolidation: List[Dict[str, Any]] = [
        {"id": it["id"], "title": it["title"], "domain": it["domain"], "snippet_or_summary": it.get("summary", "")} for it in read_summaries
    ]
    next_id, more_items, cst, calls = _search_followups(
        exa,
        followups,
        next_id,
        id_to_url,
        id_to_meta,
        include_domains=params.include_domains,
        exclude_domains=params.exclude_domains,
        num_results=params.num_results_per_query,
    )
    cost_search_total += cst
    cost_exa += cst
    cost_calls.extend(calls)
    all_items_for_consolidation.extend(more_items)

    # 7) Consolidate into curations (LLM)
    cons_out = steps.consolidate_curations(
        cfg,
        params.mission,
        all_items=all_items_for_consolidation,
        additional_context={},
        options=InvokeOptions(temperature=1.0, max_tokens=768),
    )

    # Assemble output result + metrics
    output = SearchWorkflowResult(
        queries=queries,
        followups=followups,
        curations=[c.model_dump(mode="json") for c in (cons_out.curations or [])],
        reads=len(selected_ids),
        cost_exa=float(cost_exa),
        usage_tokens={
            "prompt": int(usage_total["prompt"]),
            "completion": int(usage_total["completion"]),
            "total": int(usage_total["total"]),
        },
    )

    # Minimal log line (concise)
    try:
        logger = logging.getLogger("app.search_workflow")
        logger.setLevel(logging.INFO)
        log_line = (
            f"workflow mission='{params.mission[:60]}' queries={len(output.queries)} reads={output.reads} "
            f"cost.total={output.cost_exa:.4f} cost.search={cost_search_total:.4f} cost.contents={cost_contents_total:.4f}"
        )
        logger.info(log_line)
        print(log_line)
    except Exception:
        pass

    # Scheduler-facing dict: maintain old fields for compatibility and add 'curations'
    return {
        "agent": payload.get("agent", "search_only_v1"),
        "queries": len(output.queries),
        "reads": output.reads,
        "cost_exa": output.cost_exa,
        "cost_exa_breakdown": {
            "total": float(cost_exa),
            "search": float(cost_search_total),
            "contents": float(cost_contents_total),
            "calls": cost_calls,
        },
        "usage_tokens": output.usage_tokens,
        "followups": [f.model_dump(mode="json") for f in followups],
        "curations": output.curations,
    }
