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

from ..config import settings
from .jobs import claim_jobs, start_run, finish_run, mark_done
from .ticker import tick


def run_once(handle_job) -> int:
    """Claim one job and process it. Returns number of jobs processed."""
    jobs = claim_jobs(limit=1)
    if not jobs:
        return 0
    job = jobs[0]
    run = start_run(job["id"])  # start run record
    run_id = run["id"]
    try:
        metrics: Dict[str, Any] = handle_job(job)
        finish_run(run_id, status="succeeded", metrics=metrics)
        mark_done(job["id"], success=True)
    except Exception as e:
        finish_run(run_id, status="failed", error={"message": str(e)})
        mark_done(job["id"], success=False, error={"message": str(e)})
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
