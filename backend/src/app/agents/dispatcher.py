from __future__ import annotations

from typing import Any, Dict, Optional

from . import search_workflow as sw
from . import surfer_workflow as srf
from app.supabase_client import get_service_client


def _resolve_agent_from_schedule(job: Dict[str, Any]) -> Optional[str]:
    try:
        sched_id = job.get("schedule_id")
        if not sched_id:
            return None
        sb = get_service_client()
        sch = sb.table("schedules").select("id, meta").eq("id", sched_id).limit(1).execute().data
        if sch and isinstance(sch, list):
            meta = (sch[0] or {}).get("meta") or {}
            if isinstance(meta, dict):
                agent = meta.get("agent") or meta.get("engine")
                if isinstance(agent, str) and agent:
                    return agent
    except Exception:
        return None
    return None


def handle(job: Dict[str, Any], user_token: Optional[str] = None) -> Dict[str, Any]:
    payload = job.get("payload") or {}
    agent = (payload.get("agent") or "").strip().lower()
    if not agent:
        agent = (_resolve_agent_from_schedule(job) or "").strip().lower()

    # Default to surfer for new streams; keep exa search path available
    if agent in {"surfer", "surfer_v1"} or agent == "":
        return srf.run(job, user_token=user_token)
    if agent in {"search_only_v1", "search", "exa_search_v1"}:
        return sw.run(job, user_token=user_token)

    # Unknown → safe default
    return srf.run(job, user_token=user_token)

