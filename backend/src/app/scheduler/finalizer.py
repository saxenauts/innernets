from __future__ import annotations

"""
Finalizer: reconcile late Surfer completions and persist results.

Scans scheduler runs that are still running or timed out, checks the Surfer
service for completion, and if ready persists curations and marks the run/job
as succeeded. Safe to call periodically; operations are idempotent.
"""

from typing import Any, Dict, List, Optional
import logging

from app.config import settings
from app.supabase_client import get_service_client
from app.clients import surfer_client
from app.scheduler.jobs import finish_run, mark_done
from app.llm.types import ProviderConfig, InvokeOptions
from app.llm import surfer_steps
from app.agents import surfer_workflow as srfw
from app.repositories import curations_repo, urls_repo


logger = logging.getLogger("finalizer")


def _select_candidates(limit: int = 25) -> List[Dict[str, Any]]:
    sb = get_service_client()
    runs = (
        sb.table("runs")
        .select("id, job_id, status, started_at, finished_at, metrics, error, updated_at")
        .in_("status", ["running", "failed"])  # type: ignore[attr-defined]
        .order("updated_at", desc=False)
        .limit(limit)
        .execute()
        .data
        or []
    )
    out: List[Dict[str, Any]] = []
    for r in runs:
        m = r.get("metrics") or {}
        sj = (m.get("surfer_job_id") or "").strip()
        if not sj:
            continue
        # Only consider: running, or failed due to timeout
        if r.get("status") == "failed":
            err = (r.get("error") or {}).get("message") if isinstance(r.get("error"), dict) else None
            if not (err and "Timeout waiting for job" in str(err)):
                continue
        out.append(r)
    return out


def _job_payload(job_id: str) -> Optional[Dict[str, Any]]:
    sb = get_service_client()
    j = sb.table("jobs").select("id, user_id, schedule_id, payload").eq("id", job_id).limit(1).execute().data or []
    return j[0] if j else None


def _already_persisted(job_id: str) -> bool:
    sb = get_service_client()
    cr = sb.table("curation_runs").select("id").eq("job_id", job_id).limit(1).execute().data or []
    return bool(cr)


def _persist_curations(stream_id: str, job_id: str, raw_curations: List[Dict[str, Any]], mission: str, sources_hints: Optional[str]) -> Dict[str, Any]:
    prior_context = srfw._build_prior_context(stream_id)
    cfg = ProviderConfig.from_env()
    remix = surfer_steps.remix_curations(cfg, mission, raw_curations, prior_context, sources_hints)
    curated = list(remix.curations or [])
    # Fallback: mirror raw (same as surfer_workflow)
    if not curated and raw_curations:
        curated = []
        for rc in raw_curations[:4]:
            summary = (rc.get("summary") or "").strip()
            title = (summary[:110] + "...") if len(summary) > 110 else (summary or "New insight")
            links = rc.get("links") or []
            clean_links = []
            for l in links[:3]:
                url = (l.get("url") or "").strip()
                if not url:
                    continue
                clean_links.append({"url": url, "title": (l.get("title") or "").strip() or None})
            if not clean_links:
                continue
            body_md = f"**Key** — {summary}"
            curated.append({"title": title, "body_md": body_md, "links": clean_links})

    # Persist
    run_row = curations_repo.create_curation_run(stream_id=stream_id, job_id=job_id, status="running")
    clusters_payload: List[Dict[str, Any]] = []
    persistable: List[Dict[str, Any]] = []
    for idx, item in enumerate(curated):
        if not isinstance(item, dict):
            try:
                item = item.model_dump(mode="json")  # type: ignore[attr-defined]
            except Exception:
                continue
        title = (item.get("title") or "").strip()
        body_md = (item.get("body_md") or "").strip()
        links_payload = item.get("links") or []
        if not title or not links_payload:
            continue
        persistable.append(item)
        teaser = body_md.splitlines()[0].strip() if body_md else ""
        clusters_payload.append({"title": title[:160], "hook": teaser[:200], "position": len(persistable) - 1, "body_md": body_md or None})
    cluster_rows = curations_repo.insert_clusters(run_row["id"], clusters_payload) if clusters_payload else []
    for cur_item, row in zip(persistable, cluster_rows):
        link_refs: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for j, link in enumerate(cur_item.get("links") or []):
            url = (link.get("url") or "").strip()
            if not url:
                continue
            title = (link.get("title") or "").strip() or None
            url_row = urls_repo.ensure_url(url, title=title)
            if url_row["id"] in seen:
                continue
            seen.add(url_row["id"])
            link_refs.append({"url_id": url_row["id"], "snapshot_title": title, "position": j})
        if link_refs:
            curations_repo.insert_cluster_links(row["id"], link_refs)
    curations_repo.complete_curation_run(run_row["id"], status="succeeded")
    return {"curations_raw": len(raw_curations), "curations_final": len(persistable)}


def finalize_once(max_n: int = 5) -> int:
    """Process up to max_n late runs. Returns count finalized."""
    candidates = _select_candidates(limit=max_n * 5)
    done = 0
    for r in candidates:
        if done >= max_n:
            break
        try:
            m = r.get("metrics") or {}
            surfer_job_id = (m.get("surfer_job_id") or "").strip()
            if not surfer_job_id:
                continue
            job_id = r.get("job_id")
            if not job_id:
                continue
            j = _job_payload(job_id)
            if not j:
                continue
            payload = j.get("payload") or {}
            stream_id = (payload.get("stream_id") or "").strip()
            if not stream_id:
                continue
            # Skip if we already created a curation run for this job
            if _already_persisted(job_id):
                finish_run(r["id"], status="succeeded", metrics=m)
                mark_done(job_id, success=True)
                done += 1
                continue

            # Check Surfer status
            st = surfer_client.job_status(surfer_job_id)
            state = (st.get("state") or "").lower()
            if state not in {"completed", "failed", "canceled"}:
                continue  # still running
            if state in {"failed", "canceled"}:
                finish_run(r["id"], status="failed", error={"message": f"Surfer {state}"})
                mark_done(job_id, success=False, error={"message": f"Surfer {state}"})
                done += 1
                continue

            # Completed → fetch results and persist
            result = surfer_client.job_result(surfer_job_id)
            raw_curations: List[Dict[str, Any]] = list(result.get("curations") or [])
            # Load mission/sources
            sb = get_service_client()
            srow = sb.table("streams").select("mission, sources_hints").eq("id", stream_id).limit(1).execute().data
            mission = (srow[0] or {}).get("mission") if srow else None
            sources_hints = (srow[0] or {}).get("sources_hints") if srow else None
            mission = (mission or "Web research mission")

            stats = _persist_curations(stream_id, job_id, raw_curations, mission, sources_hints)
            # Mark scheduler run/job succeeded
            met = dict(m)
            met["surfer_result_ready"] = bool(raw_curations)
            met.update(stats)
            finish_run(r["id"], status="succeeded", metrics=met)
            mark_done(job_id, success=True)
            done += 1
        except Exception:
            logger.debug("finalize_once: error while finalizing run %s", r.get("id"), exc_info=True)
            # try next candidate
            continue
    return done

