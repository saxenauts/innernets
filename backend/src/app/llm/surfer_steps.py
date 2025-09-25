from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import json

from .types import ProviderConfig, StructuredRequest, InvokeOptions, JsonSchema
from .adapter import structured as call_structured
from . import prompts_surfer as prompts


class PlannerOut(BaseModel):
    instruction: str = Field(..., description="Concise multi-sentence instruction (2–4 sentences)")
    context: str = Field(..., description="Compact multi-paragraph context summarizing prior knowledge and targets")


class RemixLink(BaseModel):
    url: str = Field(..., max_length=2048)
    title: Optional[str] = Field(default=None, max_length=80)


class RemixCuration(BaseModel):
    title: str = Field(..., max_length=160)
    body_md: str = Field(..., description="Multi-paragraph markdown-like content; bold key phrases, short bullets allowed")
    links: List[RemixLink] = Field(..., min_items=1)


class RemixCurationsOut(BaseModel):
    curations: List[RemixCuration] = Field(default_factory=list)


def _wrap_instruction(user_block: str) -> str:
    return f"{prompts.SYSTEM_PREAMBLE}\n\n{user_block}".strip()


def _subst(template: str, vars: Dict[str, Any]) -> str:
    s = template
    for k, v in vars.items():
        s = s.replace("{{" + k + "}}", v)
    return s


def generate_instruction(
    cfg: ProviderConfig,
    mission: str,
    sources_hints: Optional[str],
    prior_context_str: str,
    *,
    options: Optional[InvokeOptions] = None,
) -> PlannerOut:
    user_text = _subst(
        prompts.GENERATE_SURFER_INSTRUCTION,
        {
            "mission": mission,
            "sources_text": (sources_hints or "(none)"),
            "prior_context_str": prior_context_str or "(none)",
        },
    )
    req = StructuredRequest(
        instruction=_wrap_instruction(user_text),
        context=None,
        schema_name="PlannerOut",
        out_schema=JsonSchema(properties={}, required=[]),
        pydantic_model=PlannerOut,
    )
    res = call_structured(cfg, req, options or InvokeOptions(temperature=1.0, max_tokens=768))
    return PlannerOut(**(res.output or {}))


def remix_curations(
    cfg: ProviderConfig,
    mission: str,
    raw_curations: List[Dict[str, Any]],
    prior_context_str: str,
    sources_text: Optional[str] = None,
    *,
    options: Optional[InvokeOptions] = None,
) -> RemixCurationsOut:
    user_text = _subst(
        prompts.REMIX_CURATIONS,
        {
            "mission": mission,
            "sources_text": (sources_text or "(none)"),
            "prior_context_str": prior_context_str or "(none)",
            "raw_curations_json": json.dumps(raw_curations, ensure_ascii=False),
        },
    )
    req = StructuredRequest(
        instruction=_wrap_instruction(user_text),
        context=None,
        schema_name="RemixCurationsOut",
        out_schema=JsonSchema(properties={}, required=[]),
        pydantic_model=RemixCurationsOut,
    )
    res = call_structured(cfg, req, options or InvokeOptions(temperature=1.0, max_tokens=1200))
    return RemixCurationsOut(**(res.output or {}))
