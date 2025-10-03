from __future__ import annotations

import os
from dotenv import load_dotenv
import uvicorn
import logging


def main() -> None:
    load_dotenv(os.getenv("DOTENV_PATH", ".env"), override=False)
    # Enable in-app scheduler by default for this launcher
    os.environ.setdefault("SCHEDULER_IN_APP", "1")
    # Configure logging level for local runs
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
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "1") in {"1", "true", "TRUE"},
    )


if __name__ == "__main__":
    main()
