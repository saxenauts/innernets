from __future__ import annotations

import os
import time
from dotenv import load_dotenv

from ..config import settings
from .worker import run_once
from ..agents.dispatcher import handle as handle_job


def main() -> None:
    load_dotenv(os.getenv("DOTENV_PATH", ".env"), override=False)
    interval = 2.0
    while True:
        processed = run_once(handle_job)
        if processed == 0:
            time.sleep(interval)


if __name__ == "__main__":
    main()
