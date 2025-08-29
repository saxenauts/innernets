from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import get_current_user_id, get_current_token
from ..repositories import streams_repo, curations_repo
from ..scheduler import jobs as jobs_repo


router = APIRouter(prefix="/streams", tags=["streams"])


class StreamCreate(BaseModel):
    mission: str
    sources_hints: Optional[str] = None
    cadence: str
    time_zone: Optional[str] = None


class StreamUpdate(BaseModel):
    mission: Optional[str] = None
    sources_hints: Optional[str] = None
    cadence: Optional[str] = None
    time_zone: Optional[str] = None
    active: Optional[bool] = None


@router.post("", status_code=201)
def create_stream(payload: StreamCreate, user_id: str = Depends(get_current_user_id), token: str = Depends(get_current_token)):
    row = streams_repo.create_stream(user_id, token, payload.model_dump())
    return row


@router.get("")
def list_streams(user_id: str = Depends(get_current_user_id), token: str = Depends(get_current_token)):
    rows = streams_repo.list_streams(user_id, token)
    # Optionally decorate with latest run timestamp (simple N+1)
    out: List[Dict[str, Any]] = []
    for r in rows:
        latest = None
        try:
            latest = curations_repo.get_latest_run(r["id"])  # service role read
        except Exception:
            # Gracefully degrade if service-role client not configured in dev
            latest = None
        if latest:
            r = dict(r)
            r["latest_run_at"] = latest.get("started_at")
        out.append(r)
    return out


@router.get("/{stream_id}")
def get_stream(stream_id: str, user_id: str = Depends(get_current_user_id), token: str = Depends(get_current_token)):
    row = streams_repo.get_stream(stream_id, user_id, token)
    if not row:
        raise HTTPException(status_code=404, detail="Stream not found")
    return row


@router.put("/{stream_id}")
def update_stream(stream_id: str, payload: StreamUpdate, user_id: str = Depends(get_current_user_id), token: str = Depends(get_current_token)):
    row = streams_repo.update_stream(stream_id, user_id, token, payload.model_dump(exclude_none=True))
    return row


@router.post("/{stream_id}/run", status_code=202)
def run_stream_now(stream_id: str, user_id: str = Depends(get_current_user_id), token: str = Depends(get_current_token)):
    # Enqueue an ad-hoc job with payload
    job = jobs_repo.enqueue_job(user_id=user_id, payload={"type": "stream_run", "stream_id": stream_id})
    return {"job_id": job.get("id"), "status": job.get("status", "queued")}


@router.get("/{stream_id}/latest")
def latest_curation(stream_id: str, user_id: str = Depends(get_current_user_id), token: str = Depends(get_current_token)):
    try:
        run = curations_repo.get_latest_run(stream_id)
    except Exception:
        run = None
    if not run:
        return {"run_id": None, "run_at": None, "curations": []}
    curations: List[Dict[str, Any]] = []
    for idx, c in enumerate(run.get("clusters", []) or []):
        links = c.get("links", [])
        curations.append(
            {
                "title": c.get("title"),
                "hook": c.get("hook"),
                "links": links,
                "position": c.get("position", idx),
            }
        )
    return {
        "run_id": run.get("id"),
        "run_at": run.get("started_at"),
        "started_at": run.get("started_at"),
        "finished_at": run.get("finished_at"),
        "curations": curations,
    }
