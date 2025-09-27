from __future__ import annotations

from typing import Any, Dict, List, Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import get_current_user_id, get_current_token
from ..repositories import streams_repo, curations_repo
from ..scheduler import jobs as jobs_repo


router = APIRouter(prefix="/streams", tags=["streams"])


# -----------------------------
# Models (KISS, inline)
# -----------------------------

class Cadence(str, Enum):
    daily = "daily"
    three_x_week = "3xweek"
    weekly = "weekly"
    discovery = "discovery"


class LinkOut(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    domain: Optional[str] = None
    position: Optional[int] = None


class CurationOut(BaseModel):
    title: Optional[str] = None
    # Deprecated but kept for back-compat
    hook: Optional[str] = Field(default=None, description="deprecated; prefer body_md")
    body_md: Optional[str] = None
    links: List[LinkOut] = []
    position: Optional[int] = None


class RunOut(BaseModel):
    id: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    # Back-compat alias present in current responses
    run_at: Optional[str] = None
    curations: List[CurationOut] = []


class RunsListOut(BaseModel):
    runs: List[RunOut]
    next_cursor: Optional[str] = None


class LatestOut(BaseModel):
    run_id: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    # Back-compat alias
    run_at: Optional[str] = None
    curations: List[CurationOut] = []


class StreamOut(BaseModel):
    id: str
    mission: str
    sources: Optional[str] = None
    cadence: str
    time_zone: Optional[str] = None
    active: Optional[bool] = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    latest_run_at: Optional[str] = None


class EnqueueOut(BaseModel):
    job_id: Optional[str] = None
    status: Optional[str] = None


class StreamCreate(BaseModel):
    mission: str
    # Accept 'sources' (preferred) or legacy 'sources_hints'
    sources: Optional[str] = None
    sources_hints: Optional[str] = None
    cadence: Cadence
    time_zone: Optional[str] = None


class StreamUpdate(BaseModel):
    mission: Optional[str] = None
    # Accept new 'sources' name; keep legacy 'sources_hints' for back-compat
    sources: Optional[str] = Field(default=None, description="Preferred: sources for this stream")
    sources_hints: Optional[str] = Field(default=None, description="Legacy: kept for back-compat")
    cadence: Optional[Cadence] = None
    time_zone: Optional[str] = None
    active: Optional[bool] = None


def _to_stream_out(row: Dict[str, Any], latest_run_at: Optional[str] = None) -> StreamOut:
    return StreamOut(
        id=row.get("id"),
        mission=row.get("mission"),
        sources=row.get("sources_hints"),
        cadence=row.get("cadence"),
        time_zone=row.get("time_zone"),
        active=row.get("active", True),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        latest_run_at=latest_run_at,
    )


@router.post("", status_code=201, response_model=StreamOut)
def create_stream(payload: StreamCreate, user_id: str = Depends(get_current_user_id), token: str = Depends(get_current_token)) -> StreamOut:
    row = streams_repo.create_stream(user_id, token, payload.model_dump())
    return _to_stream_out(row)


@router.get("", response_model=List[StreamOut])
def list_streams(user_id: str = Depends(get_current_user_id), token: str = Depends(get_current_token)) -> List[StreamOut]:
    rows = streams_repo.list_streams(user_id, token)
    # Optionally decorate with latest run timestamp (simple N+1)
    out: List[StreamOut] = []
    for r in rows:
        latest = None
        try:
            latest = curations_repo.get_latest_run(r["id"])  # service role read
        except Exception:
            # Gracefully degrade if service-role client not configured in dev
            latest = None
        latest_at = latest.get("started_at") if latest else None
        out.append(_to_stream_out(r, latest_run_at=latest_at))
    return out


@router.get("/{stream_id}", response_model=StreamOut)
def get_stream(stream_id: str, user_id: str = Depends(get_current_user_id), token: str = Depends(get_current_token)) -> StreamOut:
    row = streams_repo.get_stream(stream_id, user_id, token)
    if not row:
        raise HTTPException(status_code=404, detail="Stream not found")
    return _to_stream_out(row)


@router.put("/{stream_id}", response_model=StreamOut)
def update_stream(stream_id: str, payload: StreamUpdate, user_id: str = Depends(get_current_user_id), token: str = Depends(get_current_token)) -> StreamOut:
    # Map 'sources' to repo's expected field
    fields = payload.model_dump(exclude_none=True)
    row = streams_repo.update_stream(stream_id, user_id, token, fields)
    return _to_stream_out(row)


@router.post("/{stream_id}/run", status_code=202, response_model=EnqueueOut)
def run_stream_now(stream_id: str, user_id: str = Depends(get_current_user_id), token: str = Depends(get_current_token)) -> EnqueueOut:
    # Enqueue an ad-hoc job with payload
    job = jobs_repo.enqueue_job(user_id=user_id, payload={"type": "stream_run", "stream_id": stream_id})
    return EnqueueOut(job_id=job.get("id"), status=job.get("status", "queued"))


@router.get("/{stream_id}/latest", response_model=LatestOut)
def latest_curation(stream_id: str, user_id: str = Depends(get_current_user_id), token: str = Depends(get_current_token)) -> LatestOut:
    try:
        run = curations_repo.get_latest_run(stream_id)
    except Exception:
        run = None
    if not run:
        return LatestOut(run_id=None, run_at=None, curations=[])
    curations: List[Dict[str, Any]] = []
    for idx, c in enumerate(run.get("clusters", []) or []):
        links = c.get("links", [])
        curations.append(
            {
                "title": c.get("title"),
                "hook": c.get("hook"),  # deprecated; kept for back-compat
                "body_md": c.get("body_md"),
                "links": links,
                "position": c.get("position", idx),
            }
        )
    return LatestOut(
        run_id=run.get("id"),
        run_at=run.get("started_at"),
        started_at=run.get("started_at"),
        finished_at=run.get("finished_at"),
        curations=[CurationOut(**c) for c in curations],
    )


@router.delete("/{stream_id}", status_code=204)
def delete_stream(stream_id: str, hard: bool = False, user_id: str = Depends(get_current_user_id), token: str = Depends(get_current_token)):
    # Soft-delete: mark inactive and disable schedule
    # Ensure the stream exists and user has access
    row = streams_repo.get_stream(stream_id, user_id, token)
    if not row:
        raise HTTPException(status_code=404, detail="Stream not found")
    streams_repo.delete_stream(stream_id, user_id, token, hard=bool(hard))
    return None


@router.get("/{stream_id}/runs", response_model=RunsListOut)
def list_runs(
    stream_id: str,
    limit: int = Query(10, ge=1, le=25),
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
                    "hook": c.get("hook"),  # deprecated; kept for back-compat
                    "body_md": c.get("body_md"),
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
    return RunsListOut(
        runs=[RunOut(**rr) for rr in out_runs],
        next_cursor=next_cursor,
    )
