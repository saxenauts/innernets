from __future__ import annotations

import os
from dotenv import load_dotenv
import uvicorn


def main() -> None:
    load_dotenv(os.getenv("DOTENV_PATH", ".env"), override=False)
    # Enable in-app scheduler by default for this launcher
    os.environ.setdefault("SCHEDULER_IN_APP", "1")
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "1") in {"1", "true", "TRUE"},
    )


if __name__ == "__main__":
    main()

