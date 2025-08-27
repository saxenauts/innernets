from __future__ import annotations

"""Search-only agent loop (skeleton).

This module will orchestrate the two-step plan in docs/search-only-plan.md.
For now, it exposes a `run(job, user_token)` that returns minimal metrics
and does not call external providers by default (can be mocked in tests).
"""

from typing import Any, Dict


def run(job: Dict[str, Any], user_token: str | None = None) -> Dict[str, Any]:
    payload = job.get("payload") or {}
    agent = payload.get("agent", "search_only_v1")
    params = payload.get("params", {})

    # TODO: integrate exa_client + llm.adapter per plan
    # For now, stub metrics to prove the job loop wiring.
    metrics = {
        "agent": agent,
        "queries": 0,
        "reads": 0,
        "cost_exa": 0.0,
        "usage_tokens": {"prompt": 0, "completion": 0, "total": 0},
    }
    return metrics

