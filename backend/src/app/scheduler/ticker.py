from __future__ import annotations

"""Scheduler ticker: selects due schedules and enqueues jobs idempotently.

This implementation is minimal and uses Supabase PostgREST. It is designed
to be easily swappable with direct SQL/pg functions when needed.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from ..supabase_client import get_service_client
from .jobs import enqueue_job


def _parse_ts(value: Any):
    """Parse ISO8601-ish string into aware datetime (UTC on failure)."""
    import datetime as pydt
    if isinstance(value, pydt.datetime):
        return value
    if not value:
        return pydt.datetime.max.replace(tzinfo=pydt.timezone.utc)
    s = str(value)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = pydt.datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pydt.timezone.utc)
        return dt
    except Exception:
        return pydt.datetime.max.replace(tzinfo=pydt.timezone.utc)


def _calc_next_run(current: datetime, cadence: str, tz: str) -> datetime:
    """Compute next run time. For now, support simple intervals like PT1H/PT30M.

    TODO: add cronexpr support later without breaking signature.
    """
    # Very minimal ISO8601-like interval support: PT<n>M or PT<n>H
    if cadence.startswith("PT") and cadence.endswith("M"):
        minutes = int(cadence[2:-1])
        return current + timedelta(minutes=minutes)
    if cadence.startswith("PT") and cadence.endswith("H"):
        hours = int(cadence[2:-1])
        return current + timedelta(hours=hours)
    # Fallback: hourly
    return current + timedelta(hours=1)


def tick(max_jobs: int = 25) -> List[Dict[str, Any]]:
    """Select due schedules and enqueue at most `max_jobs` jobs.

    Returns list of enqueued job rows.
    """
    sb = get_service_client()
    now = datetime.now(timezone.utc)
    # Select due schedules (active, next_run_at <= now)
    q = sb.table("schedules").select("*").eq("active", True)
    # Try lte if available; fall back to filter; otherwise rely on server-side defaults
    try:
        q = q.lte("next_run_at", now.isoformat())  # type: ignore[attr-defined]
    except Exception:
        try:
            q = q.filter("next_run_at", "lte", now.isoformat())  # type: ignore[attr-defined]
        except Exception:
            pass
    resp = q.order("next_run_at").limit(max_jobs).execute()
    raw_schedules: List[Dict[str, Any]] = resp.data or []
    # Defensive: also filter client-side to only include due schedules
    schedules: List[Dict[str, Any]] = []
    for sch in raw_schedules:
        try:
            nra = _parse_ts(sch.get("next_run_at"))
            if nra <= now:
                schedules.append(sch)
        except Exception:
            # if parse fails, skip
            continue

    enqueued: List[Dict[str, Any]] = []
    for sch in schedules:
        if len(enqueued) >= max_jobs:
            break
        user_id = sch["user_id"]
        schedule_id = sch["id"]

        # deterministic idempotency key per schedule/time window
        idk = f"sch:{schedule_id}:at:{int(now.timestamp())//60}"  # minute bucket
        # Hydrate params from schedule.meta if present
        meta = sch.get("meta") or {}
        meta_params = {}
        try:
            # Support either flat keys or nested under 'params'
            mp = meta.get("params") if isinstance(meta, dict) else None
            if isinstance(mp, dict):
                meta_params = dict(mp)
            elif isinstance(meta, dict):
                meta_params = {k: v for k, v in meta.items() if k in {
                    "mission", "hints", "include_domains", "exclude_domains",
                    "search_type", "num_results_per_query", "read_top_k",
                    "max_chars_per_page", "compose_items_limit"
                }}
        except Exception:
            meta_params = {}

        payload = {"agent": "search_only_v1", "params": {"schedule_id": schedule_id, **(meta_params or {})}}
        job = enqueue_job(
            user_id=user_id,
            payload=payload,
            schedule_id=schedule_id,
            idempotency_key=idk,
        )
        enqueued.append(job)

        # update schedule next_run_at
        tz = sch.get("time_zone", "UTC")
        cadence = sch.get("cadence", "PT1H")
        # Use schedule's current next_run_at as the base to avoid drift, but ensure monotonicity
        try:
            base = _parse_ts(sch.get("next_run_at"))
        except Exception:
            base = now
        next_at = _calc_next_run(base if base > now else now, cadence, tz)
        sb.table("schedules").update({"last_enqueued_at": now.isoformat(), "next_run_at": next_at.isoformat()}).eq("id", schedule_id).execute()

    return enqueued
