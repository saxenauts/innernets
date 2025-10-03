from __future__ import annotations

import os
import time
import threading
from typing import Callable, Optional

from ..config import settings
from .ticker import tick
from .worker import run_once


def _loop(stop: threading.Event, handle_job: Callable, poll_interval_s: Optional[float]) -> None:
    """Background loop: enqueue due work then claim+execute one job per tick.

    Designed to be started inside FastAPI lifespan; respects a stop event.
    """
    interval = poll_interval_s or (settings.SCHEDULE_POLL_INTERVAL_MS / 1000.0)
    max_jobs = settings.SCHEDULE_MAX_JOBS_PER_TICK
    while not stop.is_set():
        try:
            tick(max_jobs=max_jobs)
        except Exception:
            # Swallow ticker errors to keep background alive
            pass
        try:
            run_once(handle_job)
        except Exception:
            # Likewise for worker
            pass
        # Sleep or exit early if stop flagged
        stop.wait(interval)


def start_background_scheduler(handle_job: Callable, poll_interval_s: Optional[float] = None) -> tuple[threading.Thread, threading.Event]:
    """Start the scheduler in a daemon thread. Returns (thread, stop_event)."""
    stop = threading.Event()
    th = threading.Thread(target=_loop, args=(stop, handle_job, poll_interval_s), daemon=True)
    th.start()
    return th, stop
