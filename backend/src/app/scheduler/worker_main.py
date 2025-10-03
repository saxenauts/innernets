from __future__ import annotations

import os
import time
from dotenv import load_dotenv
import signal

from ..config import settings
import logging
from .worker import run_once
from ..agents.dispatcher import handle as handle_job


_stop = False


def _handle_signal(signum, frame):
    global _stop
    _stop = True


def main() -> None:
    load_dotenv(os.getenv("DOTENV_PATH", ".env"), override=False)
    # Configure root logging level from LOG_LEVEL
    level = os.getenv("LOG_LEVEL", "info").lower()
    lvl = logging.INFO
    if level in {"debug"}: lvl = logging.DEBUG
    if level in {"warning","warn"}: lvl = logging.WARNING
    if level in {"error"}: lvl = logging.ERROR
    logging.basicConfig(level=lvl, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # Clamp noisy third‑party loggers even when LOG_LEVEL=debug
    for noisy in ("httpx", "httpcore", "hpack", "postgrest", "supabase", "anyio"):
        try:
            logging.getLogger(noisy).setLevel(logging.WARNING)
        except Exception:
            pass
    interval = 2.0
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    while not _stop:
        processed = run_once(handle_job)
        if processed == 0:
            time.sleep(interval)


if __name__ == "__main__":
    main()
