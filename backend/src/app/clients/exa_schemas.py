from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class _BaseModel(BaseModel):
    model_config = {"extra": "allow"}


SearchType = Literal["keyword", "neural", "fast", "auto"]


class TextReq(_BaseModel):
    max_characters: Optional[int] = Field(default=None, ge=100, le=200_000)
    include_html_tags: bool = False


class HighlightsReq(_BaseModel):
    num_sentences: int = 5
    highlights_per_url: int = 1
    query: Optional[str] = None


class SummaryReq(_BaseModel):
    query: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None


class Result(_BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    publishedDate: Optional[str] = None
    author: Optional[str] = None
    id: Optional[str] = None


class ResultWithContent(Result):
    text: Optional[str] = None
    highlights: Optional[List[str]] = None
    highlightScores: Optional[List[float]] = None
    summary: Optional[str] = None
    subpages: Optional[List['ResultWithContent']] = None
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


class ContentsResponse(_BaseModel):
    requestId: Optional[str] = None
    results: Optional[List[ResultWithContent]] = None
    context: Optional[str] = None
    statuses: Optional[List[Dict[str, Any]]] = None
    provider_cost: Optional[CostDollars] = None

