from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import get_current_user_id
from ..clients.exa_client import get_exa_client


router = APIRouter(prefix="/exa", tags=["exa"])


# --- Pydantic Schemas (subset mirroring Exa) ---

SearchType = Literal["keyword", "neural", "fast", "auto"]


class _BaseModel(BaseModel):
    model_config = {"extra": "allow"}


class HighlightsReq(_BaseModel):
    num_sentences: int = 5
    highlights_per_url: int = 1
    query: Optional[str] = None


class SummaryReq(_BaseModel):
    query: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None


class TextReq(_BaseModel):
    max_characters: Optional[int] = Field(default=None, ge=100, le=200_000)
    include_html_tags: bool = False


class ContentsOptions(_BaseModel):
    text: Optional[Union[bool, TextReq]] = None
    highlights: Optional[HighlightsReq] = None
    summary: Optional[SummaryReq] = None
    livecrawl: Optional[Literal["never", "fallback", "always", "preferred"]] = None
    livecrawl_timeout: Optional[int] = Field(default=None, ge=100, le=60_000)
    subpages: Optional[int] = Field(default=0, ge=0, le=10)
    subpage_target: Optional[Union[str, List[str]]] = None
    extras: Optional[Dict[str, Any]] = None
    context: Optional[Union[bool, Dict[str, int]]] = None


class SearchRequest(_BaseModel):
    # SDK-first (snake_case, top-level options)
    query: str
    type: SearchType = "auto"
    category: Optional[str] = None
    num_results: int = 10
    include_domains: Optional[List[str]] = None
    exclude_domains: Optional[List[str]] = None
    start_crawl_date: Optional[str] = None
    end_crawl_date: Optional[str] = None
    start_published_date: Optional[str] = None
    end_published_date: Optional[str] = None
    context: Optional[Union[bool, Dict[str, int]]] = None
    moderation: Optional[bool] = False
    # contents flattened per SDK
    text: Optional[Union[bool, TextReq]] = None
    highlights: Optional[Union[bool, HighlightsReq]] = None
    summary: Optional[SummaryReq] = None
    subpages: Optional[int] = Field(default=0, ge=0, le=10)
    subpage_target: Optional[Union[str, List[str]]] = None
    livecrawl: Optional[Literal["never", "fallback", "always", "preferred"]] = None
    livecrawl_timeout: Optional[int] = Field(default=None, ge=100, le=60_000)
    extras: Optional[Dict[str, Any]] = None


class Result(_BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    publishedDate: Optional[str] = None
    author: Optional[str] = None
    id: Optional[str] = None
    image: Optional[str] = None
    favicon: Optional[str] = None


class ResultWithContent(Result):
    text: Optional[str] = None
    highlights: Optional[List[str]] = None
    highlightScores: Optional[List[float]] = None
    summary: Optional[str] = None
    subpages: Optional[List['ResultWithContent']] = None  # forward ref
    extras: Optional[Dict[str, Any]] = None


class CostBreakdown(_BaseModel):
    keywordSearch: Optional[float] = None
    neuralSearch: Optional[float] = None
    contentText: Optional[float] = None
    contentHighlight: Optional[float] = None
    contentSummary: Optional[float] = None


class CostEntry(_BaseModel):
    search: Optional[float] = None
    contents: Optional[float] = None
    breakdown: Optional[CostBreakdown] = None


class CostPricesPerRequest(_BaseModel):
    neuralSearch_1_25_results: Optional[float] = None
    neuralSearch_26_100_results: Optional[float] = None
    neuralSearch_100_plus_results: Optional[float] = None
    keywordSearch_1_100_results: Optional[float] = None
    keywordSearch_100_plus_results: Optional[float] = None


class CostPricesPerPage(_BaseModel):
    contentText: Optional[float] = None
    contentHighlight: Optional[float] = None
    contentSummary: Optional[float] = None


class CostDollars(_BaseModel):
    total: Optional[float] = None
    breakDown: Optional[List[CostEntry]] = None
    perRequestPrices: Optional[CostPricesPerRequest] = None
    perPagePrices: Optional[CostPricesPerPage] = None


class SearchResponse(_BaseModel):
    requestId: Optional[str] = None
    resolvedSearchType: Optional[str] = None
    results: Optional[List[ResultWithContent]] = None
    searchType: Optional[str] = None
    context: Optional[str] = None
    provider_cost: Optional[CostDollars] = None


class ContentsRequest(_BaseModel):
    urls: List[str]
    text: Optional[Union[bool, TextReq]] = True
    highlights: Optional[Union[bool, HighlightsReq]] = None
    summary: Optional[SummaryReq] = None
    livecrawl: Optional[Literal["never", "fallback", "always", "preferred"]] = None
    livecrawl_timeout: Optional[int] = Field(default=None, ge=100, le=60_000)
    subpages: Optional[int] = Field(default=0, ge=0, le=10)
    subpage_target: Optional[Union[str, List[str]]] = None
    extras: Optional[Dict[str, Any]] = None
    context: Optional[Union[bool, Dict[str, int]]] = None


class StatusError(_BaseModel):
    tag: Optional[str] = None
    httpStatusCode: Optional[int] = None


class StatusItem(_BaseModel):
    id: Optional[str] = None
    status: Optional[Literal['success', 'error']] = None
    error: Optional[StatusError] = None


class ContentsResponse(_BaseModel):
    requestId: Optional[str] = None
    results: Optional[List[ResultWithContent]] = None
    context: Optional[str] = None
    statuses: Optional[List[StatusItem]] = None
    provider_cost: Optional[CostDollars] = None


# --- Routes ---


def _to_plain(obj: Any) -> Any:
    # Results from the client are already plain, but keep helper for safety
    if isinstance(obj, dict):
        return obj
    return obj


def _pick(d: Dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in d:
            return d[k]
    return None


@router.post("/search", response_model=SearchResponse)
async def exa_search(req: SearchRequest, user_id: str = Depends(get_current_user_id)):
    # Enforce caps per plan with 400 (Bad Request)
    if req.type in {"neural", "auto"} and req.num_results > 25:
        raise HTTPException(status_code=400, detail="num_results must be ≤ 25 for neural/auto searches")
    if req.type == "keyword" and req.num_results > 100:
        raise HTTPException(status_code=400, detail="num_results must be ≤ 100 for keyword searches")

    try:
        client = get_exa_client()
        result = client.search_and_contents(**req.model_dump(exclude_none=True))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:  # SDK/network error
        raise HTTPException(status_code=502, detail=f"Exa error: {e}")

    rd = _to_plain(result) or {}
    cost = _pick(rd, "costDollars", "cost_dollars")
    return SearchResponse(
        requestId=_pick(rd, "requestId", "request_id"),
        resolvedSearchType=_pick(rd, "resolvedSearchType", "resolved_search_type"),
        results=_pick(rd, "results"),
        searchType=_pick(rd, "searchType", "search_type"),
        context=_pick(rd, "context"),
        provider_cost=cost if isinstance(cost, dict) else None,
    )


@router.post("/contents", response_model=ContentsResponse)
async def exa_contents(req: ContentsRequest, user_id: str = Depends(get_current_user_id)):
    try:
        client = get_exa_client()
        result = client.get_contents(**req.model_dump(exclude_none=True))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Exa error: {e}")

    rd = _to_plain(result) or {}
    cost = _pick(rd, "costDollars", "cost_dollars")
    return ContentsResponse(
        requestId=_pick(rd, "requestId", "request_id"),
        results=_pick(rd, "results"),
        context=_pick(rd, "context"),
        statuses=_pick(rd, "statuses"),
        provider_cost=cost if isinstance(cost, dict) else None,
    )
