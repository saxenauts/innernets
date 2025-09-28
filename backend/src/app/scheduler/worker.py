from __future__ import annotations

"""Minimal dev worker to execute the search-only agent loop.

This is a stub; it will be expanded to:
- poll schedules -> enqueue jobs
- claim jobs -> run agent
- record runs and metrics

In dev, it can use `DEV_TEST_USER_TOKEN` to act on behalf of a test user.
"""

import os
import time
from typing import Dict, Any
import logging
import uuid
import json

from ..config import settings
from .jobs import claim_jobs, start_run, finish_run, mark_done
from .ticker import tick


logger = logging.getLogger("scheduler")


def run_once(handle_job) -> int:
    """Claim one job and process it. Returns number of jobs processed."""
    jobs = claim_jobs(limit=1)
    if not jobs:
        return 0
    job = jobs[0]
    trace_id = str(uuid.uuid4())
    t0 = time.time()
    run = start_run(job["id"])  # start run record
    run_id = run["id"]
    try:
        try:
            logger.info(
                json.dumps(
                    {
                        "event": "job.started",
                        "trace_id": trace_id,
                        "job_id": job.get("id"),
                        "run_id": run_id,
                        "user_id": job.get("user_id"),
                        "schedule_id": job.get("schedule_id"),
                        "agent": (job.get("payload") or {}).get("agent"),
                    }
                )
            )
        except Exception:
            pass
        # Pass run_id to handler so it can record external IDs early
        job["__run_id"] = run_id
        metrics: Dict[str, Any] = handle_job(job)
        finish_run(run_id, status="succeeded", metrics=metrics)
        mark_done(job["id"], success=True)
        try:
            logger.info(
                json.dumps(
                    {
                        "event": "job.succeeded",
                        "trace_id": trace_id,
                        "job_id": job.get("id"),
                        "run_id": run_id,
                        "elapsed_ms": int((time.time() - t0) * 1000),
                    }
                )
            )
        except Exception:
            pass
    except Exception as e:
        # Persist failure; metrics may have been written earlier by the handler
        finish_run(run_id, status="failed", error={"message": str(e)})
        mark_done(job["id"], success=False, error={"message": str(e)})
        try:
            logger.error(
                json.dumps(
                    {
                        "event": "job.failed",
                        "trace_id": trace_id,
                        "job_id": job.get("id"),
                        "run_id": run_id,
                        "error": str(e),
                    }
                )
            )
        except Exception:
            pass
    return 1


def dev_loop(handle_job, sleep_sec: float | None = None) -> None:
    """Simple dev loop: claim and process jobs for a fixed user.

    `handle_job` should perform the agent loop and return metrics.
    """
    interval = max(1.0, (sleep_sec or settings.SCHEDULE_POLL_INTERVAL_MS / 1000.0))
    while True:
        # enqueue due work first
        try:
            tick(max_jobs=settings.SCHEDULE_MAX_JOBS_PER_TICK)
        except Exception:
            # dev: ignore ticker failures in loop
            pass
        processed = run_once(handle_job)
        if processed == 0:
            time.sleep(interval)
