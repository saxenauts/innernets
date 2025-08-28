from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from ..supabase_client import get_user_supabase_client, get_service_client


def _streams_table(token: str):
    return get_user_supabase_client(token).table("streams")


def _schedules_table(token: str):
    return get_user_supabase_client(token).table("schedules")


def create_stream(user_id: str, token: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    mission = (fields.get("mission") or "").strip()
    if not mission:
        raise ValueError("mission is required")
    payload: Dict[str, Any] = {
        "user_id": user_id,
        "mission": mission,
        "sources_hints": fields.get("sources_hints"),
        "cadence": fields.get("cadence") or "weekly",
        "time_zone": fields.get("time_zone") or "UTC",
        "active": True,
    }
    st = _streams_table(token)
    resp = st.insert(payload).execute()
    row = (resp.data or [None])[0]
    if not row:
        raise RuntimeError("Failed to create stream")

    # Create a schedule tied to this stream (store stream_id in meta)
    name = (mission[:80] or "Stream").strip() or "Stream"
    sched_payload = {
        "user_id": user_id,
        "name": f"Stream: {name}",
        "cadence": payload["cadence"],
        "time_zone": payload["time_zone"],
        "active": True,
        "meta": {"stream_id": row["id"]},
    }
    _schedules_table(token).insert(sched_payload).execute()
    return row


def list_streams(user_id: str, token: str) -> List[Dict[str, Any]]:
    st = _streams_table(token)
    resp = st.select("id, mission, sources_hints, cadence, time_zone, active, created_at, updated_at").eq("user_id", user_id).order("created_at", desc=True).execute()
    return resp.data or []


def get_stream(stream_id: str, user_id: str, token: str) -> Optional[Dict[str, Any]]:
    st = _streams_table(token)
    resp = st.select("id, user_id, mission, sources_hints, cadence, time_zone, active, created_at, updated_at").eq("id", stream_id).limit(1).execute()
    data = resp.data or []
    return data[0] if data else None


def update_stream(stream_id: str, user_id: str, token: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    patch: Dict[str, Any] = {}
    for k in ["mission", "sources_hints", "cadence", "time_zone", "active"]:
        if k in fields and fields[k] is not None:
            patch[k] = fields[k]
    if not patch:
        cur = get_stream(stream_id, user_id, token)
        if not cur:
            raise ValueError("Stream not found")
        return cur

    st = _streams_table(token)
    st.update(patch).eq("id", stream_id).execute()

    # Sync schedule if cadence/time_zone/active changed
    if any(k in patch for k in ("cadence", "time_zone", "active")):
        sched = _find_schedule_for_stream(user_id, token, stream_id)
        if sched:
            sched_patch: Dict[str, Any] = {}
            if "cadence" in patch:
                sched_patch["cadence"] = patch["cadence"]
            if "time_zone" in patch:
                sched_patch["time_zone"] = patch["time_zone"]
            if "active" in patch:
                sched_patch["active"] = bool(patch["active"])
            if sched_patch:
                _schedules_table(token).update(sched_patch).eq("id", sched["id"]).execute()

    cur = get_stream(stream_id, user_id, token)
    if not cur:
        raise ValueError("Stream not found after update")
    return cur


def _find_schedule_for_stream(user_id: str, token: str, stream_id: str) -> Optional[Dict[str, Any]]:
    resp = _schedules_table(token).select("id, user_id, cadence, time_zone, active, meta").eq("user_id", user_id).contains("meta", {"stream_id": stream_id}).limit(1).execute()
    data = resp.data or []
    return data[0] if data else None

