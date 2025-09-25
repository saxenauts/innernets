from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import json

from .types import ProviderConfig, StructuredRequest, InvokeOptions, JsonSchema
from .adapter import structured as call_structured
from . import prompts_surfer as prompts


class InstructionOut(BaseModel):
    instruction: str = Field(..., max_length=320)


class RemixLink(BaseModel):
    url: str = Field(..., max_length=2048)
    title: Optional[str] = Field(default=None, max_length=80)


class RemixCuration(BaseModel):
    title: str = Field(..., max_length=120)
    hook: str = Field(..., max_length=160)
    links: List[RemixLink] = Field(..., min_items=1, max_items=4)


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
    additional_context: Optional[Dict[str, Any]] = None,
    *,
    options: Optional[InvokeOptions] = None,
) -> InstructionOut:
    user_text = _subst(
        prompts.GENERATE_SURFER_INSTRUCTION,
        {
            "mission": mission,
            "sources_hints": (sources_hints or "(none)"),
            "additional_context_json": json.dumps(additional_context or {}, ensure_ascii=False),
        },
    )
    req = StructuredRequest(
        instruction=_wrap_instruction(user_text),
        context=None,
        schema_name="InstructionOut",
        out_schema=JsonSchema(properties={}, required=[]),
        pydantic_model=InstructionOut,
    )
    res = call_structured(cfg, req, options or InvokeOptions(temperature=1.0, max_tokens=256))
    return InstructionOut(**(res.output or {}))


def remix_curations(
    cfg: ProviderConfig,
    mission: str,
    raw_curations: List[Dict[str, Any]],
    *,
    options: Optional[InvokeOptions] = None,
) -> RemixCurationsOut:
    user_text = _subst(
        prompts.REMIX_CURATIONS,
        {
            "mission": mission,
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
    res = call_structured(cfg, req, options or InvokeOptions(temperature=1.0, max_tokens=768))
    return RemixCurationsOut(**(res.output or {}))
