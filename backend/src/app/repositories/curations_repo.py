from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from ..supabase_client import get_service_client, get_user_supabase_client


def _tbl(name: str):
    return get_service_client().table(name)


def create_curation_run(stream_id: str, job_id: Optional[str] = None, status: str = "running") -> Dict[str, Any]:
    row = {"stream_id": stream_id, "job_id": job_id, "status": status}
    resp = _tbl("curation_runs").insert(row).execute()
    return resp.data[0]


def complete_curation_run(run_id: str, status: str = "succeeded", metrics: Optional[Dict[str, Any]] = None) -> None:
    from datetime import datetime, timezone
    patch: Dict[str, Any] = {"status": status, "finished_at": datetime.now(timezone.utc).isoformat()}
    if metrics is not None:
        patch["metrics"] = metrics
    _tbl("curation_runs").update(patch).eq("id", run_id).execute()


def insert_clusters(run_id: str, clusters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Expect items like {title, hook, position}
    payload = [
        {"run_id": run_id, "title": c["title"], "hook": c.get("hook", ""), "position": int(c.get("position", idx))}
        for idx, c in enumerate(clusters)
    ]
    resp = _tbl("curation_clusters").insert(payload).execute()
    return resp.data or []


def insert_cluster_links(cluster_id: str, links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Expect items like {url_id, snapshot_title?, position}
    payload = [
        {"cluster_id": cluster_id, "url_id": l["url_id"], "snapshot_title": l.get("snapshot_title"), "position": int(l.get("position", idx))}
        for idx, l in enumerate(links)
        if l.get("url_id")
    ]
    if not payload:
        return []
    resp = _tbl("curation_cluster_links").insert(payload).execute()
    return resp.data or []


def get_latest_run(stream_id: str) -> Optional[Dict[str, Any]]:
    runs = _tbl("curation_runs").select("id, stream_id, job_id, status, started_at, finished_at, metrics").eq("stream_id", stream_id).order("started_at", desc=True).limit(1).execute().data or []
    if not runs:
        return None
    run = runs[0]
    clusters = _tbl("curation_clusters").select("id, run_id, title, hook, position").eq("run_id", run["id"]).order("position", desc=False).execute().data or []
    if clusters:
        cluster_ids = [c["id"] for c in clusters]
        # Join links with URLs via explicit FK (url_id → urls.id)
        links = (
            get_service_client()
            .table("curation_cluster_links")
            .select("*, urls:urls!curation_cluster_links_url_id_fkey(id,url,domain,last_title)")
            .in_("cluster_id", cluster_ids)
            .order("position", desc=False)
            .execute()
            .data
            or []
        )
        by_cluster: Dict[str, List[Dict[str, Any]]] = {cid: [] for cid in cluster_ids}
        for l in links:
            u = l.get("urls") or {}
            by_cluster.setdefault(l["cluster_id"], []).append(
                {
                    "url": u.get("url"),
                    "domain": u.get("domain"),
                    "title": l.get("snapshot_title") or u.get("last_title"),
                    "position": l.get("position", 0),
                }
            )
        for c in clusters:
            c["links"] = by_cluster.get(c["id"], [])
    run["clusters"] = clusters
    return run


def get_previous_context(stream_id: str) -> Dict[str, Any]:
    latest = get_latest_run(stream_id)
    if not latest:
        return {}
    ctx: Dict[str, Any] = {
        "last_run_at": latest.get("started_at"),
        "curations": [],
    }
    for c in latest.get("clusters", []) or []:
        ctx["curations"].append(
            {
                "title": c.get("title"),
                "hook": c.get("hook"),
                "link_domains": list({(l.get("domain") or "").strip() for l in (c.get("links") or []) if l.get("domain")}),
                "link_urls_sample": [l.get("url") for l in (c.get("links") or [])[:2] if l.get("url")],
            }
        )
    return ctx


def get_runs(stream_id: str, limit: int = 10, before_started_at: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return multiple runs in reverse chronological order with clusters+links.

    - Supports simple pagination via `before_started_at` (ISO8601 string).
    - Returns a list of run dicts, each with `clusters: [...]` where each cluster has `links` joined to urls.
    """
    # Base query for runs
    q = _tbl("curation_runs").select(
        "id, stream_id, job_id, status, started_at, finished_at, metrics"
    ).eq("stream_id", stream_id)
    # Apply cursor (strictly older than cursor timestamp)
    if before_started_at:
        try:
            # Prefer lt if available; fall back to filter
            q = q.lt("started_at", before_started_at)  # type: ignore[attr-defined]
        except Exception:
            try:
                q = q.filter("started_at", "lt", before_started_at)  # type: ignore[attr-defined]
            except Exception:
                pass
    runs = q.order("started_at", desc=True).limit(limit).execute().data or []
    if not runs:
        return []

    run_ids = [r["id"] for r in runs]
    # Fetch clusters for all runs
    clusters = (
        _tbl("curation_clusters")
        .select("id, run_id, title, hook, position")
        .in_("run_id", run_ids)
        .order("position", desc=False)
        .execute()
        .data
        or []
    )
    cluster_ids: List[str] = [c["id"] for c in clusters]

    # Join links + urls for all clusters via explicit FK (url_id → urls.id)
    links_by_cluster: Dict[str, List[Dict[str, Any]]] = {}
    if cluster_ids:
        links = (
            get_service_client()
            .table("curation_cluster_links")
            .select("*, urls:urls!curation_cluster_links_url_id_fkey(id,url,domain,last_title)")
            .in_("cluster_id", cluster_ids)
            .order("position", desc=False)
            .execute()
            .data
            or []
        )
        for l in links:
            u = l.get("urls") or {}
            links_by_cluster.setdefault(l["cluster_id"], []).append(
                {
                    "url": u.get("url"),
                    "domain": u.get("domain"),
                    "title": l.get("snapshot_title") or u.get("last_title"),
                    "position": l.get("position", 0),
                }
            )

    # Attach links to clusters, then group by run
    for c in clusters:
        cid = c["id"]
        c["links"] = links_by_cluster.get(cid, [])
    clusters_by_run: Dict[str, List[Dict[str, Any]]] = {rid: [] for rid in run_ids}
    for c in clusters:
        clusters_by_run.setdefault(c["run_id"], []).append(c)
    for r in runs:
        r["clusters"] = clusters_by_run.get(r["id"], [])
    return runs
