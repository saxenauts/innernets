from __future__ import annotations

"""End-to-end demo for the scheduler infra (no mocks).

This script:
  1) Loads env (backend/.env)
  2) Upserts a due schedule for a given user
  3) Runs the ticker to enqueue a job (idempotent per minute)
  4) Claims a job and executes the search workflow once
  5) Prints resulting schedule, job, and run summaries

Requirements (env):
  - SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
  - EXA_API_KEY
  - AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT_NAME
  - SCHEDULE_TEST_USER_ID (uuid of an Auth user in your Supabase project)

Usage:
  poetry run python -m app.scheduler.demo
"""

import os
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import time

from dotenv import load_dotenv

from ..supabase_client import get_service_client
from .ticker import tick
from .jobs import claim_jobs, start_run, finish_run, mark_done, enqueue_job
from ..agents import search_workflow as sw


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_schedule(sb, user_id: str) -> Dict[str, Any]:
    """Create or update a demo schedule that is due now.

    If a schedule named 'e2e-scheduler-demo' exists for the user, make it due now.
    Otherwise, create one.
    """
    name = "e2e-scheduler-demo"
    now = _now_iso()
    # Try to find an existing schedule
    try:
        resp = sb.table("schedules").select("*").eq("user_id", user_id).eq("name", name).limit(1).execute()
        rows = resp.data or []
    except Exception:
        rows = []

    if rows:
        sch = rows[0]
        # make due now and set demo meta params if missing
        meta = sch.get("meta") or {}
        if not isinstance(meta, dict):
            meta = {}
        if not meta.get("params"):
            meta["params"] = {
                "mission": os.getenv("DEMO_SCHEDULE_MISSION", "Scheduled: Watch AI memory tools"),
                "hints": ["recent"],
                "search_type": "keyword",
                "num_results_per_query": 3,
                "read_top_k": 1,
                "max_chars_per_page": 1200,
                "compose_items_limit": 6,
            }
        sb.table("schedules").update({"active": True, "next_run_at": now, "meta": meta}).eq("id", sch["id"]).execute()
        return sch
    else:
        row = {
            "user_id": user_id,
            "name": name,
            "cadence": os.getenv("SCHEDULE_TEST_CADENCE", "PT30M"),
            "time_zone": os.getenv("SCHEDULE_TEST_TZ", "UTC"),
            "active": True,
            "next_run_at": now,
            "meta": {
                "params": {
                    "mission": os.getenv("DEMO_SCHEDULE_MISSION", "Scheduled: Watch AI memory tools"),
                    "hints": ["recent"],
                    "search_type": "keyword",
                    "num_results_per_query": 3,
                    "read_top_k": 1,
                    "max_chars_per_page": 1200,
                    "compose_items_limit": 6,
                }
            },
        }
        resp = sb.table("schedules").insert(row).execute()
        return resp.data[0]


def _latest_job(sb, user_id: str) -> Dict[str, Any] | None:
    try:
        resp = sb.table("jobs").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
        rows = resp.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def _runs_for_job(sb, job_id: str) -> list[Dict[str, Any]]:
    try:
        resp = sb.table("runs").select("*").eq("job_id", job_id).order("created_at", desc=True).execute()
        return resp.data or []
    except Exception:
        return []


def _list_jobs(sb, user_id: str, statuses: Optional[List[str]] = None, limit: int = 50) -> List[Dict[str, Any]]:
    try:
        q = sb.table("jobs").select("*").eq("user_id", user_id).order("queued_at", desc=False).limit(limit)
        if statuses:
            # Simple filter client-side due to library constraints
            rows = q.execute().data or []
            return [j for j in rows if j.get("status") in set(statuses)]
        return q.execute().data or []
    except Exception:
        return []


def _print_queue(sb, user_id: str, header: str = "queue snapshot") -> None:
    rows = _list_jobs(sb, user_id)
    view = [
        {
            "id": r.get("id"),
            "status": r.get("status"),
            "attempts": r.get("attempts"),
            "mission": (r.get("payload", {}) or {}).get("params", {}).get("mission"),
        }
        for r in rows
    ]
    print(f"[demo] {header}:\n" + json.dumps(view, indent=2))


def _process_one(handle_job) -> Optional[Dict[str, Any]]:
    """Claim and process a single job, returning a result summary or None if none available."""
    jobs = claim_jobs(limit=1)
    if not jobs:
        return None
    job = jobs[0]
    run = start_run(job["id"])  # start run record
    run_id = run["id"]
    try:
        metrics: Dict[str, Any] = handle_job(job)
        finish_run(run_id, status="succeeded", metrics=metrics)
        mark_done(job["id"], success=True)
        return {"job_id": job["id"], "status": "succeeded", "metrics": metrics}
    except Exception as e:
        finish_run(run_id, status="failed", error={"message": str(e)})
        mark_done(job["id"], success=False, error={"message": str(e)})
        return {"job_id": job["id"], "status": "failed", "error": str(e)}


def main() -> None:
    load_dotenv(os.getenv("DOTENV_PATH", ".env"), override=False)

    # Require service role for DB
    if not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY")):
        raise SystemExit("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in backend/.env")

    user_id = os.getenv("SCHEDULE_TEST_USER_ID")
    if not user_id:
        raise SystemExit("Set SCHEDULE_TEST_USER_ID to a valid Supabase Auth user UUID")

    sb = get_service_client()

    # 1) Ensure due schedule
    sch = _ensure_schedule(sb, user_id)
    print("[demo] schedule ready:", json.dumps({k: sch.get(k) for k in ["id", "user_id", "name", "next_run_at", "cadence", "active"]}, indent=2))

    # 2) Ticker enqueues a job
    enq = tick(max_jobs=1)
    print("[demo] ticker enqueued:", json.dumps([{"id": j.get("id"), "schedule_id": j.get("schedule_id"), "user_id": j.get("user_id"), "status": j.get("status")} for j in enq], indent=2))
    # show schedule advancement
    try:
        sch2 = sb.table("schedules").select("*").eq("id", sch["id"]).limit(1).execute().data[0]
        print("[demo] schedule advanced:", json.dumps({k: sch2.get(k) for k in ["id", "last_enqueued_at", "next_run_at"]}, indent=2))
    except Exception:
        pass

    # Small lag to observe queue before adding more
    time.sleep(float(os.getenv("DEMO_LAG_AFTER_TICK", "3")))

    _print_queue(sb, user_id, header="queue after tick")

    # 3) Enqueue 2 ad-hoc jobs with explicit missions to stress queue
    missions = [
        "Hardware advancements for personal computing",
        "New research with VR",
        "ANC headphone ear health research",
    ]
    # Enqueue first two; the third will be enqueued after a short lag
    adhoc_jobs = []
    for m in missions[:2]:
        j = enqueue_job(
            user_id=user_id,
            payload={
                "agent": "search_only_v1",
                "params": {
                    "mission": m,
                    "hints": ["recent"],
                    "search_type": "keyword",
                    "num_results_per_query": 3,
                    "read_top_k": 1,
                    "max_chars_per_page": 1200,
                    "compose_items_limit": 6,
                },
            },
        )
        adhoc_jobs.append(j)
    print("[demo] enqueued ad-hoc jobs:", json.dumps([{"id": j.get("id"), "mission": j.get("payload", {}).get("params", {}).get("mission")} for j in adhoc_jobs], indent=2))

    _print_queue(sb, user_id, header="queue after ad-hoc enqueues (2)")

    # Short lag; still before the schedule's next_run_at window
    time.sleep(float(os.getenv("DEMO_LAG_BEFORE_THIRD", "2")))

    # Enqueue third ad-hoc job
    j3 = enqueue_job(
        user_id=user_id,
        payload={
            "agent": "search_only_v1",
            "params": {
                "mission": missions[2],
                "hints": ["recent"],
                "search_type": "keyword",
                "num_results_per_query": 3,
                "read_top_k": 1,
                "max_chars_per_page": 1200,
                "compose_items_limit": 6,
            },
        },
    )
    print("[demo] enqueued third ad-hoc:", json.dumps({"id": j3.get("id"), "mission": j3.get("payload", {}).get("params", {}).get("mission")}, indent=2))

    _print_queue(sb, user_id, header="queue before processing")

    # Optional: wait and tick again to enqueue a second scheduled job (e.g., set cadence PT1M and delay ~70s)
    delay_sec = int(os.getenv("DEMO_SECOND_TICK_DELAY_SEC", "0") or 0)
    if delay_sec > 0:
        print(f"[demo] waiting {delay_sec}s to tick again (for next scheduled run)...")
        time.sleep(delay_sec)
        enq2 = tick(max_jobs=1)
        print("[demo] second tick enqueued:", json.dumps([{"id": j.get("id"), "schedule_id": j.get("schedule_id"), "status": j.get("status")} for j in enq2], indent=2))
        _print_queue(sb, user_id, header="queue after second tick")

    if not enq:
        print("[demo] No jobs enqueued (possibly already enqueued for this minute). Proceeding to claim any queued job.")

    # 3) Worker claims and executes once
    # 4) Process jobs sequentially; print outputs per job
    print("[demo] starting processing loop...")
    while True:
        res = _process_one(sw.run)
        if not res:
            break
        # show concise metrics
        metrics = res.get("metrics", {})
        items = metrics.get("items") or []
        followups = metrics.get("followups") or []
        print(
            "[demo] processed job:",
            json.dumps(
                {
                    "job_id": res.get("job_id"),
                    "status": res.get("status"),
                    "queries": metrics.get("queries"),
                    "reads": metrics.get("reads"),
                    "items": items[:3],  # show first 3 items
                    "followups": followups[:3],  # show first 3
                    "usage_tokens": metrics.get("usage_tokens"),
                },
                indent=2,
            ),
        )
        # small pause for readability
        time.sleep(float(os.getenv("DEMO_LAG_BETWEEN_RUNS", "1")))

    _print_queue(sb, user_id, header="queue after processing")


if __name__ == "__main__":
    main()
