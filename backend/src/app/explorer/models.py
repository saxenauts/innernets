from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field, ConfigDict

class StepOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    planner: str = Field(..., description="1–2 sentences summarizing search strategy for the next iteration")
    search_queries: List[str] = Field(default_factory=list, description="High‑leverage search queries for this iteration")
    confidence: float = Field(..., ge=0.0, le=1.0, description="0–1 confidence that goals are met")
    stop: bool = Field(..., description="True when the exploration is complete")

class NextLink(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(..., description="URL selected from links_on_page to follow next")
    reason: str = Field(..., description="Short reason why this link is worth exploring next")


class MultiReadingOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary_findings: str = Field(
        ..., description="Dense, combined knowledge learned across all pages; append to findings"
    )
    # Reader returns indices only; caller maps indices back to real URLs
    choose_indices: List[int] = Field(
        default_factory=list,
        description="Indices of links to follow next (use provided idx values from the batch catalog)",
    )


class Curation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(..., description="Concise finding that adds value to the user's reading/learning")
    pages: List[str] = Field(
        default_factory=list,
        description="Page identifiers referenced as page_1, page_2, … (from this batch)",
    )


class CuratedReadingOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    curations: List[Curation] = Field(
        default_factory=list,
        description="Up to 3 non-overlapping curations; each has a finding summary and contributing pages (page_1 etc.)",
    )
    # Reader returns indices only; caller maps indices back to real URLs
    choose_indices: List[int] = Field(
        default_factory=list,
        description="Indices of links to follow next (use provided idx values from <reference index>)",
    )
    # Optional aligned reasons for each chosen index (not used for control flow)
    reasons: List[str] = Field(
        default_factory=list,
        description="Short reasons (5–10 words) aligned with choose_indices; optional",
    )
    # Optional aligned reasons for each chosen index (not used for control flow)
    reasons: List[str] = Field(
        default_factory=list,
        description="Short reasons (5–10 words) aligned with choose_indices; optional",
    )


class Memory(BaseModel):
    model_config = ConfigDict(extra="forbid")
    visited: List[str] = Field(default_factory=list, description="Visited URLs")
    findings: List[str] = Field(default_factory=list)
    run_count: int = 0


class FilterOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    choose_indices: List[int] = Field(
        default_factory=list,
        description="Indices of SERP items to keep (use provided idx values)",
    )
