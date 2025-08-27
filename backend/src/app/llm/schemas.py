from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl, conint


class GenerateSearchQueriesOut(BaseModel):
    queries: List[str] = Field(..., min_length=1, description="3–4 concise web search queries")


class CandidateScore(BaseModel):
    url: HttpUrl
    score: conint(ge=0, le=100) = Field(..., description="Overall selection score 0–100")
    read: bool = Field(False, description="Whether to read contents for this candidate")


class EvaluateCandidatesOut(BaseModel):
    scores: List[CandidateScore]


class ProposeFollowupsOut(BaseModel):
    followups: List[str] = Field(..., min_items=1, description="Up to 6 follow-up query ideas")


class ComposedItem(BaseModel):
    title: str
    url: HttpUrl
    hook: str = Field(..., max_length=150)
    reason: str = Field(..., max_length=100)


class ComposeStreamItemsOut(BaseModel):
    items: List[ComposedItem]


__all__ = [
    "GenerateSearchQueriesOut",
    "CandidateScore",
    "EvaluateCandidatesOut",
    "ProposeFollowupsOut",
    "ComposedItem",
    "ComposeStreamItemsOut",
]
