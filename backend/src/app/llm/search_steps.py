from __future__ import annotations

"""LLM-facing steps for the Search workflow.

This module centralizes the JSON schemas and prompt wrappers for:
  1) generate_search_queries
  3) filter_candidates
  5) propose_followups
  7) consolidate_curations

Each function uses the shared provider abstraction (structured outputs)
and returns Pydantic-validated data structures. IDs are authoritative and
LLMs must never be asked to echo URLs.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from .types import ProviderConfig, StructuredRequest, InvokeOptions, JsonSchema
from .adapter import structured as call_structured
from . import prompts
import json


# ---------------------------
# Output Schemas (Pydantic)
# ---------------------------


class QueryItem(BaseModel):
    query: str = Field(..., max_length=256)
    query_type: Literal["keyword", "neural"]


class GenerateQueriesOut(BaseModel):
    queries: List[QueryItem] = Field(..., min_items=5, max_items=5)


class FilterCandidatesOut(BaseModel):
    selected_ids: List[str] = Field(..., min_items=2, max_items=3)


class FollowupItem(BaseModel):
    query: str = Field(..., max_length=256)
    query_type: Literal["keyword", "neural"]


class ProposeFollowupsOut(BaseModel):
    followups: List[FollowupItem] = Field(..., min_items=3, max_items=6)


class Curation(BaseModel):
    title: str = Field(..., max_length=120)
    hook: str = Field(..., max_length=140)
    link_ids: List[str] = Field(..., min_items=3, max_items=4)


class ConsolidateOut(BaseModel):
    curations: List[Curation] = Field(..., min_items=2, max_items=6)


__all__ = [
    "QueryItem",
    "GenerateQueriesOut",
    "FilterCandidatesOut",
    "FollowupItem",
    "ProposeFollowupsOut",
    "Curation",
    "ConsolidateOut",
]


# ---------------------------
# Prompt templates
# ---------------------------


def _wrap_instruction(user_block: str) -> str:
    # Provider adds its own system hint; include our preamble at top of instruction for stronger adherence.
    return f"{prompts.SYSTEM_PREAMBLE}\n\n{user_block}".strip()


def _subst(template: str, vars: Dict[str, Any]) -> str:
    s = template
    for k, v in vars.items():
        s = s.replace("{{" + k + "}}", v)
    return s


def generate_search_queries(
    cfg: ProviderConfig,
    mission: str,
    additional_context: Optional[Dict[str, Any]] = None,
    *,
    options: Optional[InvokeOptions] = None,
) -> GenerateQueriesOut:
    ctx = additional_context or {}
    user_text = _subst(
        prompts.GENERATE_SEARCH_QUERIES,
        {
            "mission": mission,
            "additional_context_json": json.dumps(ctx, ensure_ascii=False),
        },
    )
    req = StructuredRequest(
        instruction=_wrap_instruction(user_text),
        context=None,
        schema_name="GenerateQueriesOut",
        out_schema=JsonSchema(properties={}, required=[]),
        pydantic_model=GenerateQueriesOut,
    )
    res = call_structured(cfg, req, options or InvokeOptions(temperature=1.0, max_tokens=512))
    return GenerateQueriesOut(**(res.output or {}))


def filter_candidates(
    cfg: ProviderConfig,
    mission: str,
    candidates: List[Dict[str, Any]],
    additional_context: Optional[Dict[str, Any]] = None,
    *,
    options: Optional[InvokeOptions] = None,
) -> FilterCandidatesOut:
    ctx = additional_context or {}
    user_text = _subst(
        prompts.FILTER_CANDIDATES,
        {
            "mission": mission,
            "candidates_json": json.dumps(candidates, ensure_ascii=False),
            "additional_context_json": json.dumps(ctx, ensure_ascii=False),
        },
    )
    req = StructuredRequest(
        instruction=_wrap_instruction(user_text),
        context=None,
        schema_name="FilterCandidatesOut",
        out_schema=JsonSchema(properties={}, required=[]),
        pydantic_model=FilterCandidatesOut,
    )
    res = call_structured(cfg, req, options or InvokeOptions(temperature=1.0, max_tokens=256))
    return FilterCandidatesOut(**(res.output or {}))


def propose_followups(
    cfg: ProviderConfig,
    mission: str,
    initial_queries: List[QueryItem],
    filtered_ids: List[str],
    read_summaries: List[Dict[str, Any]],
    additional_context: Optional[Dict[str, Any]] = None,
    prior_urls: Optional[List[Dict[str, str]]] = None,
    *,
    options: Optional[InvokeOptions] = None,
) -> ProposeFollowupsOut:
    ctx = additional_context or {}
    user_text = _subst(
        prompts.PROPOSE_FOLLOWUPS,
        {
            "mission": mission,
            "initial_queries_json": json.dumps([q.model_dump(mode="json") for q in initial_queries], ensure_ascii=False),
            "read_summaries_json": json.dumps(read_summaries, ensure_ascii=False),
            "additional_context_json": json.dumps(ctx, ensure_ascii=False),
            "prior_urls_json": json.dumps(prior_urls or [], ensure_ascii=False),
        },
    )
    req = StructuredRequest(
        instruction=_wrap_instruction(user_text),
        context=None,
        schema_name="ProposeFollowupsOut",
        out_schema=JsonSchema(properties={}, required=[]),
        pydantic_model=ProposeFollowupsOut,
    )
    res = call_structured(cfg, req, options or InvokeOptions(temperature=1.0, max_tokens=512))
    return ProposeFollowupsOut(**(res.output or {}))


def consolidate_curations(
    cfg: ProviderConfig,
    mission: str,
    all_items: List[Dict[str, Any]],
    additional_context: Optional[Dict[str, Any]] = None,
    *,
    options: Optional[InvokeOptions] = None,
) -> ConsolidateOut:
    ctx = additional_context or {}
    user_text = _subst(
        prompts.CONSOLIDATE_CURATIONS,
        {
            "mission": mission,
            "all_items_json": json.dumps(all_items, ensure_ascii=False),
            "additional_context_json": json.dumps(ctx, ensure_ascii=False),
        },
    )
    req = StructuredRequest(
        instruction=_wrap_instruction(user_text),
        context=None,
        schema_name="ConsolidateOut",
        out_schema=JsonSchema(properties={}, required=[]),
        pydantic_model=ConsolidateOut,
    )
    res = call_structured(cfg, req, options or InvokeOptions(temperature=1.0, max_tokens=768))
    return ConsolidateOut(**(res.output or {}))
