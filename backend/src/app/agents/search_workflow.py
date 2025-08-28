from __future__ import annotations

"""Deterministic search workflow orchestrator.

Implements a fixed, serial flow:
  1) Generate search queries (LLM)
  2) Exa search (per query, small fanout)
  3) Evaluate/filter candidates (LLM)
  4) Optional contents read for top picks
  5) Propose follow-up queries (LLM)
  6) Compose items (LLM)

This module aims to be robust and price-efficient with conservative defaults.
"""

from typing import Any, Dict, List, Optional, Set
import logging
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.clients.exa_client import get_exa_client
from app.clients.exa_schemas import SearchResponse, ContentsResponse, ResultWithContent
from app.llm import prompts
from app.llm import structured as llm_structured
from app.llm.types import ProviderConfig, StructuredRequest, InvokeOptions, JsonSchema
from app.llm.schemas import (
    GenerateSearchQueriesOut,
    EvaluateCandidatesOut,
    ProposeFollowupsOut,
    ComposeStreamItemsOut,
)


class SearchJobParams(BaseModel):
    mission: str = Field(..., description="User mission/intent for the search workflow")
    hints: List[str] = Field(default_factory=list, description="Optional hints like site:, filetype:")
    include_domains: List[str] = Field(default_factory=list)
    exclude_domains: List[str] = Field(default_factory=list)
    search_type: Optional[str] = Field(default="keyword")  # keyword|neural|auto|fast
    num_results_per_query: int = Field(default=5, ge=1, le=25)
    read_top_k: int = Field(default=2, ge=0, le=5)
    max_chars_per_page: int = Field(default=1500, ge=200, le=200_000)
    compose_items_limit: int = Field(default=10, ge=3, le=20)


class SearchWorkflowResult(BaseModel):
    queries: List[str] = Field(default_factory=list)
    followups: List[str] = Field(default_factory=list)
    items: List[Dict[str, Any]] = Field(default_factory=list)
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

    # 1) Generate search queries (LLM)
    instruction1 = (
        prompts.GENERATE_SEARCH_QUERIES
        + "\nGenerate 3–4 focused queries for the mission."
    )
    req1 = StructuredRequest(
        instruction=instruction1,
        context={"mission": params.mission, "hints": params.hints},
        schema_name="GenerateSearchQueriesOut",
        out_schema=JsonSchema(properties={}, required=[]),
        pydantic_model=GenerateSearchQueriesOut,
    )
    res1 = llm_structured(cfg, req1, opts)
    q_out = GenerateSearchQueriesOut(**(res1.output or {}))
    queries = list(q_out.queries or [])
    if not queries:
        queries = [params.mission]

    # Cap fanout to 2 queries initially for cost control
    queries = queries[:2]

    # Accumulators
    all_results: List[ResultWithContent] = []
    cost_exa = 0.0
    usage_total = {
        "prompt": res1.usage.prompt_tokens or 0,
        "completion": res1.usage.completion_tokens or 0,
        "total": res1.usage.total_tokens or 0,
    }

    exa = get_exa_client()
    search_type = params.search_type or "keyword"
    per_query = max(1, min(params.num_results_per_query, 25 if search_type in {"auto", "neural"} else 100))

    # 2) Exa search per query
    cost_calls: List[Dict[str, Any]] = []
    cost_search_total = 0.0
    cost_contents_total = 0.0
    for q in queries:
        sr: SearchResponse = exa.search(
            query=q,
            type=search_type,
            num_results=per_query,
            include_domains=params.include_domains or None,
            exclude_domains=params.exclude_domains or None,
        )
        if sr.provider_cost and sr.provider_cost.total is not None:
            t = float(sr.provider_cost.total or 0.0)
            cost_exa += t
            cost_search_total += t
            cost_calls.append({"type": "search", "total": t})
        if sr.results:
            all_results.extend(sr.results)

    all_results = _dedupe_by_url(all_results)

    # Build candidate context for LLM scoring
    candidates_ctx: List[Dict[str, Any]] = []
    for r in all_results[: max(3, min(10, len(all_results)) )]:
        candidates_ctx.append(
            {
                "title": r.title or "",
                "domain": _domain(r.url),
                "url": r.url or None,
                "snippet": "",
            }
        )

    # 3) Evaluate/filter candidates (LLM)
    instruction2 = (
        prompts.EVALUATE_CANDIDATES
        + " Score exactly the provided candidates and mark a small subset for reading."
        + " Scores must be integers from 0 to 100."
        + " Return schema-only JSON."
    )
    req2 = StructuredRequest(
        instruction=instruction2,
        context={"mission": params.mission, "candidates": candidates_ctx},
        schema_name="EvaluateCandidatesOut",
        out_schema=JsonSchema(properties={}, required=[]),
        pydantic_model=EvaluateCandidatesOut,
    )
    res2 = llm_structured(cfg, req2, opts)
    usage_total["prompt"] += res2.usage.prompt_tokens or 0
    usage_total["completion"] += res2.usage.completion_tokens or 0
    usage_total["total"] += res2.usage.total_tokens or 0
    scores_out = EvaluateCandidatesOut(**(res2.output or {}))

    # Select URLs to read
    to_read: List[str] = []
    scored = list(scores_out.scores or [])
    # sort by score desc, stable
    scored.sort(key=lambda s: int(getattr(s, "score", 0) or 0), reverse=True)
    for s in scored:
        if getattr(s, "read", False) and s.url:
            to_read.append(str(s.url))
        if len(to_read) >= params.read_top_k:
            break

    # 4) Optional contents read
    contents: Optional[ContentsResponse] = None
    if to_read:
        contents = exa.get_contents(
            urls=to_read,
            text={"max_characters": params.max_chars_per_page},
        )
        if contents and contents.provider_cost and contents.provider_cost.total is not None:
            t = float(contents.provider_cost.total or 0.0)
            cost_exa += t
            cost_contents_total += t
            cost_calls.append({"type": "contents", "total": t})

    # 5) Propose follow-ups (LLM)
    instruction3 = prompts.PROPOSE_FOLLOWUPS + " Propose up to 4 queries."
    ctx3 = {
        "mission": params.mission,
        "observed_domains": sorted({c.get("domain") for c in candidates_ctx if c.get("domain")}),
    }
    req3 = StructuredRequest(
        instruction=instruction3,
        context=ctx3,
        schema_name="ProposeFollowupsOut",
        out_schema=JsonSchema(properties={}, required=[]),
        pydantic_model=ProposeFollowupsOut,
    )
    res3 = llm_structured(cfg, req3, opts)
    usage_total["prompt"] += res3.usage.prompt_tokens or 0
    usage_total["completion"] += res3.usage.completion_tokens or 0
    usage_total["total"] += res3.usage.total_tokens or 0
    followups_out = ProposeFollowupsOut(**(res3.output or {}))

    # 6) Compose items (LLM)
    # Prefer composed set from read contents if available; otherwise from candidates
    compose_candidates: List[Dict[str, str]] = []
    if contents and contents.results:
        for r in contents.results:
            if r.url and r.title:
                compose_candidates.append({"title": r.title, "url": r.url})
    if not compose_candidates:
        for c in candidates_ctx:
            if c.get("url") and c.get("title"):
                compose_candidates.append({"title": c["title"], "url": c["url"]})
    # Limit
    compose_candidates = compose_candidates[: max(3, params.compose_items_limit) ]

    instruction4 = prompts.COMPOSE_STREAM_ITEMS + " Compose succinct, non-repetitive hooks."
    req4 = StructuredRequest(
        instruction=instruction4,
        context={"mission": params.mission, "candidates": compose_candidates},
        schema_name="ComposeStreamItemsOut",
        out_schema=JsonSchema(properties={}, required=[]),
        pydantic_model=ComposeStreamItemsOut,
    )
    res4 = llm_structured(cfg, req4, opts)
    usage_total["prompt"] += res4.usage.prompt_tokens or 0
    usage_total["completion"] += res4.usage.completion_tokens or 0
    usage_total["total"] += res4.usage.total_tokens or 0
    composed = ComposeStreamItemsOut(**(res4.output or {}))

    # Assemble output result + metrics
    output = SearchWorkflowResult(
        queries=queries,
        followups=list(followups_out.followups or []),
        items=[it.model_dump(mode="json") for it in (composed.items or [])],
        reads=len(to_read),
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
        # Also print once for quick dev visibility
        print(log_line)
    except Exception:
        pass

    # The scheduler expects a dict of metrics; include items/followups and cost breakdown
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
        "followups": output.followups,
        "items": output.items,
    }
