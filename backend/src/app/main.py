import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from dotenv import load_dotenv
from .routes import profile as profile_routes
from .routes import streams as streams_routes
from .config import settings
from .scheduler.runner import start_background_scheduler
from .agents.dispatcher import handle as handle_job
import httpx


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
    surfer_ok = None
    try:
        base = settings.SURFER_BASE_URL.rstrip("/")
        with httpx.Client(timeout=0.3) as cli:
            r = cli.get(f"{base}/healthz")
            surfer_ok = r.status_code == 200
    except Exception:
        surfer_ok = False
    return {"ok": True, "surfer_ok": surfer_ok}


# -----------------------------
# Error model standardization
# -----------------------------

_CODE_BY_STATUS = {
    400: "BadRequest",
    401: "Unauthorized",
    403: "Forbidden",
    404: "NotFound",
    409: "Conflict",
    429: "RateLimited",
}


@app.exception_handler(RequestValidationError)
def _handle_validation_error(request: Request, exc: RequestValidationError):  # type: ignore[override]
    return JSONResponse(status_code=422, content={"code": "BadRequest", "message": "Validation failed"})


@app.exception_handler(HTTPException)
def _handle_http_exception(request: Request, exc: HTTPException):  # type: ignore[override]
    code = _CODE_BY_STATUS.get(exc.status_code, "Internal" if exc.status_code >= 500 else "Error")
    msg = exc.detail if isinstance(exc.detail, str) else (code if exc.detail is None else str(exc.detail))
    return JSONResponse(status_code=exc.status_code, content={"code": code, "message": msg})


@app.exception_handler(Exception)
def _handle_unexpected(request: Request, exc: Exception):  # type: ignore[override]
    return JSONResponse(status_code=500, content={"code": "Internal", "message": "Internal server error"})


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
    th, stop = start_background_scheduler(handle_job, None)
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

# no-op change to trigger staging deploy
