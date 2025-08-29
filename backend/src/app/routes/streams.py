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
    # Accept 'sources' (preferred) or legacy 'sources_hints'
    sources: Optional[str] = None
    sources_hints: Optional[str] = None
    cadence: str
    time_zone: Optional[str] = None


class StreamUpdate(BaseModel):
    mission: Optional[str] = None
    # Accept new 'sources' name; keep legacy 'sources_hints' for back-compat
    sources: Optional[str] = Field(default=None, description="Preferred: sources for this stream")
    sources_hints: Optional[str] = Field(default=None, description="Legacy: kept for back-compat")
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
    # Map 'sources' to repo's expected field
    fields = payload.model_dump(exclude_none=True)
    row = streams_repo.update_stream(stream_id, user_id, token, fields)
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


@router.delete("/{stream_id}", status_code=204)
def delete_stream(stream_id: str, hard: bool = False, user_id: str = Depends(get_current_user_id), token: str = Depends(get_current_token)):
    # Soft-delete: mark inactive and disable schedule
    # Ensure the stream exists and user has access
    row = streams_repo.get_stream(stream_id, user_id, token)
    if not row:
        raise HTTPException(status_code=404, detail="Stream not found")
    streams_repo.delete_stream(stream_id, user_id, token, hard=bool(hard))
    return None


@router.get("/{stream_id}/runs")
def list_runs(
    stream_id: str,
    limit: int = 10,
    before: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    token: str = Depends(get_current_token),
):
    # Auth check: ensure user can access the stream
    row = streams_repo.get_stream(stream_id, user_id, token)
    if not row:
        raise HTTPException(status_code=404, detail="Stream not found")
    runs = curations_repo.get_runs(stream_id, limit=limit, before_started_at=before) or []
    out_runs: List[Dict[str, Any]] = []
    for r in runs:
        curations: List[Dict[str, Any]] = []
        for idx, c in enumerate(r.get("clusters", []) or []):
            links = c.get("links", [])
            curations.append(
                {
                    "title": c.get("title"),
                    "hook": c.get("hook"),
                    "links": links,
                    "position": c.get("position", idx),
                }
            )
        out_runs.append(
            {
                "id": r.get("id"),
                "run_at": r.get("started_at"),
                "started_at": r.get("started_at"),
                "finished_at": r.get("finished_at"),
                "curations": curations,
            }
        )
    next_cursor = out_runs[-1]["started_at"] if out_runs else None
    return {"runs": out_runs, "next_cursor": next_cursor}
