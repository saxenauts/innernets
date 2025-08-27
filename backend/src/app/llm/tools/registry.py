from __future__ import annotations

from typing import Dict, List
from ..types import FunctionSpec, JsonSchema


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, FunctionSpec] = {}

    def register(self, spec: FunctionSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> FunctionSpec:
        return self._tools[name]

    def list(self) -> List[FunctionSpec]:
        return list(self._tools.values())


registry = ToolRegistry()


# Seed with early search-only pipeline tools (prompts handled upstream)
registry.register(
    FunctionSpec(
        name="generate_search_queries",
        description="Generate 3-4 diverse, well-formed search queries based on context and goals.",
        parameters=JsonSchema(
            properties={
                "context": {"type": "string", "description": "Brief context and goals for the run."},
                "hints": {"type": "array", "items": {"type": "string"}, "description": "Optional hints or constraints."},
            },
            required=["context"],
            additionalProperties=False,
        ),
    )
)

registry.register(
    FunctionSpec(
        name="evaluate_candidates",
        description="Score candidates for fit, credibility, and novelty from titles/snippets/domains.",
        parameters=JsonSchema(
            properties={
                "candidates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "snippet": {"type": "string"},
                            "url": {"type": "string"},
                            "domain": {"type": "string"},
                            "date": {"type": "string"},
                        },
                        "required": ["title", "url"],
                        "additionalProperties": False,
                    },
                },
                "context": {"type": "string"},
            },
            required=["candidates"],
            additionalProperties=False,
        ),
    )
)

registry.register(
    FunctionSpec(
        name="propose_followups",
        description="Propose up to 6 follow-up query schemas to widen or deepen coverage.",
        parameters=JsonSchema(
            properties={
                "gaps": {"type": "string", "description": "Observed gaps or thin areas from the first pass."},
                "context": {"type": "string"},
            },
            required=["gaps"],
            additionalProperties=False,
        ),
    )
)

registry.register(
    FunctionSpec(
        name="compose_stream_items",
        description="Select ~10–14 items, dedupe, and produce hooks and reasons for each.",
        parameters=JsonSchema(
            properties={
                "candidates": {"type": "array", "items": {"type": "object"}},
                "target": {"type": "integer", "description": "Target number of items"},
                "context": {"type": "string"},
            },
            required=["candidates", "target"],
            additionalProperties=False,
        ),
    )
)

