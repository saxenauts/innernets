from __future__ import annotations

from typing import List, Optional, Literal, Union
from pydantic import BaseModel, Field, HttpUrl, conint, field_validator


class GenerateSearchQueriesOut(BaseModel):
    queries: List[str] = Field(..., min_length=1, description="3–4 concise web search queries")


class CandidateScore(BaseModel):
    url: HttpUrl
    score: conint(ge=0, le=100) = Field(..., description="Overall selection score 0–100 (integer)")
    read: bool = Field(False, description="Whether to read contents for this candidate")

    @field_validator("score", mode="before")
    @classmethod
    def coerce_score_to_int(cls, v: Union[int, float, str]) -> int:
        """Accept floats/strings and coerce to integer 0–100.

        - If value is a float within [0, 5], assume 0–5 scale and map to 0–100.
        - Otherwise, round to nearest int and clamp to [0, 100].
        """
        try:
            if isinstance(v, bool):
                # Avoid bool being treated as int
                raise ValueError("bool not allowed for score")
            if isinstance(v, (int,)):
                x = int(v)
            elif isinstance(v, float):
                x = int(round(v * 20)) if 0.0 <= v <= 5.0 else int(round(v))
            elif isinstance(v, str):
                vf = float(v.strip())
                x = int(round(vf * 20)) if 0.0 <= vf <= 5.0 else int(round(vf))
            else:
                return v  # let pydantic raise
            # clamp
            if x < 0:
                return 0
            if x > 100:
                return 100
            return x
        except Exception:
            return v


class EvaluateCandidatesOut(BaseModel):
    scores: List[CandidateScore]


class ProposeFollowupsOut(BaseModel):
    followups: List[str] = Field(..., min_length=1, description="Up to 6 follow-up query ideas")


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
