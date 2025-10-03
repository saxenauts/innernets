from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings
from app.llm.types import ProviderConfig, InvokeOptions
from app.llm import surfer_steps
from app.repositories import curations_repo, urls_repo
from app.scheduler.jobs import update_run_metrics
from app.clients import surfer_client
from app.explorer.runner import Explorer, ExplorerConfig
from app.supabase_client import get_service_client


def _build_prior_context(stream_id: Optional[str]) -> str:
    """Build a multi-line prior context string from the last 5 runs.

    Format per curation: ISO_TIMESTAMP | Title — Hook | URLs: url1, url2, ...
    """
    if not stream_id:
        return ""
    try:
        runs = curations_repo.get_runs(stream_id, limit=5)
    except Exception:
        runs = []
    lines: List[str] = []
    for r in runs or []:
        ts = r.get("started_at") or r.get("run_at") or ""
        curations = r.get("curations") or []
        for c in curations:
            title = (c.get("title") or "").strip()
            hook = (c.get("hook") or "").strip()
            links = c.get("links") or []
            urls = [str(l.get("url")).strip() for l in links if l.get("url")] if isinstance(links, list) else []
            parts: List[str] = []
            if ts:
                parts.append(ts)
            if title:
                parts.append(title)
            if hook:
                parts.append(hook)
            if urls:
                parts.append("URLs: " + ", ".join(urls[:6]))
            if parts:
                lines.append(" | ".join(parts))
    return "\n".join(lines)


def _make_artifacts_dir(job_id: Optional[str]) -> Path:
    base = Path(__file__).resolve().parents[4] / ".artifacts" / "innernets-explorer"
    base.mkdir(parents=True, exist_ok=True)
    suffix = (job_id or "local").replace("/", "-")[:12]
    stamp = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    path = base / f"explorer-{stamp}-{suffix}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _curations_from_batches(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    batches = result.get("curations_batches") or []
    out: List[Dict[str, Any]] = []
    for batch in batches:
        pages = batch.get("pages") or []
        page_map = {}
        for pg in pages:
            pid = pg.get("id") if isinstance(pg, dict) else None
            if pid is not None:
                page_map[str(pid)] = pg
        curations = batch.get("curations") or []
        for cur in curations:
            if not isinstance(cur, dict):
                continue
            summary = (cur.get("summary") or "").strip()
            page_ids = [str(x) for x in (cur.get("pages") or [])]
            links: List[Dict[str, str]] = []
            for pid in page_ids:
                pg = page_map.get(pid)
                if not isinstance(pg, dict):
                    continue
                url = (pg.get("url") or "").strip()
                if not url:
                    continue
                title = (
                    (pg.get("serp_title") or pg.get("title") or "").strip()
                    or url
                )
                links.append({"url": url, "title": title})
            if summary and links:
                out.append({"summary": summary, "links": links})
    return out


def run(job: Dict[str, Any], user_token: Optional[str] = None) -> Dict[str, Any]:
    payload = job.get("payload") or {}
    stream_id: Optional[str] = payload.get("stream_id") if isinstance(payload.get("stream_id"), str) else None

    # Resolve mission and sources from stream
    mission = "Web research mission"
    sources_hints = None
    if stream_id:
        try:
            resp = get_service_client().table("streams").select("mission, sources_hints").eq("id", stream_id).limit(1).execute()
            data = (resp.data or [None])[0]
            if data:
                mission = data.get("mission") or mission
                sources_hints = data.get("sources_hints")
        except Exception:
            pass

    # Build rich prior context string from recent runs
    prior_context = _build_prior_context(stream_id)

    # LLM: generate one concise instruction for Surfer
    cfg = ProviderConfig.from_env()
    instr_out = surfer_steps.generate_instruction(
        cfg, mission, sources_hints, prior_context, options=InvokeOptions(temperature=1.0, max_tokens=768)
    )
    instruction = (instr_out.instruction or "").strip() or mission
    stream_context = (instr_out.context or "").strip()

    artifacts_dir = _make_artifacts_dir(job.get("id") if isinstance(job.get("id"), str) else None)
    explorer_cfg = ExplorerConfig(
        instruction=instruction,
        artifacts_dir=artifacts_dir,
        headless=settings.SURFER_HEADLESS,
        max_steps=settings.SURFER_MAX_STEPS,
        search_concurrency=settings.SURFER_SEARCH_CONCURRENCY,
        read_concurrency=settings.SURFER_READ_CONCURRENCY,
        batch_size=settings.SURFER_BATCH_SIZE,
        max_depth=settings.SURFER_MAX_DEPTH,
        batch_concurrency=settings.SURFER_READ_CONCURRENCY,
        stream_context=stream_context,
    )

    explorer = Explorer(explorer_cfg)
    try:
        explorer.logger.info("Instruction", instruction)
        if stream_context:
            explorer.logger.info("Stream Context", stream_context)
    except Exception:
        pass
    result = explorer.run()
    result.setdefault("artifacts_dir", str(artifacts_dir))

    raw_curations: List[Dict[str, Any]] = _curations_from_batches(result)

    # LLM: turn summary -> title + hook
    remix = surfer_steps.remix_curations(cfg, mission, raw_curations, prior_context, sources_hints)
    curated = list(remix.curations or [])

    if not curated and raw_curations:
        # Fallback: mirror raw curations (defensive)
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

    # Persist curated feed (title/hook/links)
    curated_dicts: List[Dict[str, Any]] = []
    for item in curated:
        if isinstance(item, dict):
            curated_dicts.append(item)
        else:
            curated_dicts.append(item.model_dump(mode="json"))

    # Persist if running for a stream
    metrics: Dict[str, Any] = {
        "agent": "surfer_v1",
        "engine": "innernets_explorer",
        "surfer_result_ready": bool(raw_curations),
        "curations_raw": len(raw_curations),
        "curations_final": len([c for c in curated_dicts if (c.get("title") and c.get("links"))]),
        "explorer_confidence": result.get("confidence"),
        "explorer_artifacts_dir": result.get("artifacts_dir"),
    }

    if stream_id:
        run_row = None
        try:
            run_row = curations_repo.create_curation_run(stream_id=stream_id, job_id=job.get("id"), status="running")
            clusters_payload: List[Dict[str, Any]] = []
            persistable: List[Dict[str, Any]] = []
            for idx, item in enumerate(curated_dicts):
                title = (item.get("title") or "").strip()
                body_md = (item.get("body_md") or "").strip()
                links_payload = item.get("links") or []
                if not title or not body_md or not links_payload:
                    continue
                persistable.append(item)
                # Deprecated hook: store a short teaser derived from body_md for back-compat
                teaser = body_md.splitlines()[0].strip()
                clusters_payload.append({"title": title[:160], "hook": teaser[:200], "position": len(persistable) - 1, "body_md": body_md})
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
            curations_repo.complete_curation_run(run_row["id"], status="succeeded", metrics=metrics)
        except Exception as e:
            if run_row and run_row.get("id"):
                try:
                    curations_repo.complete_curation_run(run_row["id"], status="failed", metrics={"error": str(e), **metrics})
                except Exception:
                    pass
            raise

    return metrics
