import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from dotenv import load_dotenv
from .routes import profile as profile_routes
from .routes import streams as streams_routes
from .config import settings
from .scheduler.runner import start_background_scheduler
from .agents import search_workflow as sw


load_dotenv(os.getenv("DOTENV_PATH", ".env"), override=False)

app = FastAPI(title="InnerNets Backend", version="0.1.0")

# CORS for local dev frontend
_origins = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/")
def root():
    return {
        "service": "innernets-backend",
        "version": "0.1.0",
        "status": "ready",
    }


app.include_router(profile_routes.router)
app.include_router(streams_routes.router)


# Optional: run scheduler inside app process if enabled via env
_sched_ctx = {"thread": None, "stop": None}


@app.on_event("startup")
def _maybe_start_scheduler() -> None:
    # Guarded by env to avoid running during tests by default
    enabled = os.getenv("SCHEDULER_IN_APP", "0") in {"1", "true", "TRUE"}
    if not enabled:
        return
    th, stop = start_background_scheduler(sw.run, None)
    _sched_ctx["thread"] = th
    _sched_ctx["stop"] = stop


@app.on_event("shutdown")
def _stop_scheduler() -> None:
    stop = _sched_ctx.get("stop")
    th = _sched_ctx.get("thread")
    if stop is not None:
        try:
            stop.set()
        except Exception:
            pass
    if th is not None:
        try:
            th.join(timeout=5.0)
        except Exception:
            pass
