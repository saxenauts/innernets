from __future__ import annotations

"""
DB-backed job helpers (stubs).

NOTE: For now we operate via Supabase PostgREST using the service role key.
Implementations are minimal and may be mocked in tests.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from .. import supabase_client as sb_mod
# Back-compat for tests that patch jobs.get_service_client
get_service_client = sb_mod.get_service_client


def enqueue_job(user_id: str, payload: Dict[str, Any], schedule_id: Optional[str] = None, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
    sb = sb_mod.get_service_client()
    row = {
        "user_id": user_id,
        "payload": payload,
        "schedule_id": schedule_id,
    }
    if idempotency_key:
        row["idempotency_key"] = idempotency_key
    # Use upsert on idempotency_key to avoid duplicate enqueues
    if idempotency_key:
        resp = sb.table("jobs").upsert(row, on_conflict="idempotency_key").execute()
    else:
        resp = sb.table("jobs").insert(row).execute()
    return resp.data[0]


def claim_jobs(limit: int = 1) -> List[Dict[str, Any]]:
    sb = sb_mod.get_service_client()
    # Minimal approach: select queued oldest-first; in real Postgres we'd use SKIP LOCKED
    resp = sb.table("jobs").select("*").eq("status", "queued").order("queued_at", desc=False).limit(limit).execute()
    jobs = resp.data or []
    now = datetime.now(timezone.utc).isoformat()
    for j in jobs:
        # mark running and bump attempts
        attempts = int(j.get("attempts", 0) or 0)
        max_attempts = int(j.get("max_attempts", 3) or 3)
        if attempts >= max_attempts:
            # Skip claiming if we've exhausted max attempts
            continue
        sb.table("jobs").update({"status": "running", "started_at": now, "attempts": (attempts + 1)}).eq("id", j["id"]).execute()
    return jobs


def mark_running(job_id: str) -> None:
    sb = sb_mod.get_service_client()
    now = datetime.now(timezone.utc).isoformat()
    # increment attempts on transition
    # Fetch current attempts to increment safely
    try:
        cur = sb.table("jobs").select("attempts").eq("id", job_id).limit(1).execute().data
        attempts = int((cur[0] or {}).get("attempts", 0)) if cur else 0
    except Exception:
        attempts = 0
    sb.table("jobs").update({"status": "running", "started_at": now, "attempts": (attempts + 1)}).eq("id", job_id).execute()


def mark_done(job_id: str, success: bool, error: Optional[Dict[str, Any]] = None) -> None:
    sb = sb_mod.get_service_client()
    status = "succeeded" if success else "failed"
    now = datetime.now(timezone.utc).isoformat()
    patch: Dict[str, Any] = {"status": status, "finished_at": now}
    if error:
        patch["last_error"] = error
    sb.table("jobs").update(patch).eq("id", job_id).execute()


def start_run(job_id: str) -> Dict[str, Any]:
    sb = sb_mod.get_service_client()
    resp = sb.table("runs").insert({"job_id": job_id}).execute()
    return resp.data[0]


def finish_run(run_id: str, status: str, metrics: Optional[Dict[str, Any]] = None, error: Optional[Dict[str, Any]] = None) -> None:
    sb = sb_mod.get_service_client()
    now = datetime.now(timezone.utc).isoformat()
    patch: Dict[str, Any] = {"status": status, "finished_at": now}
    if metrics is not None:
        patch["metrics"] = metrics
    if error is not None:
        patch["error"] = error
    sb.table("runs").update(patch).eq("id", run_id).execute()
