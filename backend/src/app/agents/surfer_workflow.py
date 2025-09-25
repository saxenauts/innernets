from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.config import settings
from app.llm.types import ProviderConfig, InvokeOptions
from app.llm import surfer_steps
from app.repositories import curations_repo, urls_repo
from app.clients import surfer_client
from app.supabase_client import get_service_client


def _compose_stream_context(prev_ctx: Dict[str, Any]) -> str:
    curations = prev_ctx.get("curations") or []
    if not curations:
        return ""
    lines: List[str] = []
    for c in curations[:4]:
        title = (c.get("title") or "").strip()
        hook = (c.get("hook") or "").strip()
        parts: List[str] = []
        if title:
            parts.append(title)
        if hook:
            parts.append(hook)
        sample_links = c.get("link_urls_sample") or []
        if sample_links:
            parts.append("links: " + ", ".join([str(u) for u in sample_links[:2]]))
        if parts:
            lines.append(" — ".join(parts))
    if not lines:
        return ""
    last_at = prev_ctx.get("last_run_at")
    header = "Recent highlights"
    if last_at:
        header += f" (last run: {last_at})"
    return header + ":\n- " + "\n- ".join(lines)


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

    # Build prior context and optional stream_context string
    prev_ctx: Dict[str, Any] = {}
    try:
        if stream_id:
            prev_ctx = curations_repo.get_previous_context(stream_id) or {}
    except Exception:
        prev_ctx = {}
    stream_context = _compose_stream_context(prev_ctx)

    # LLM: generate one concise instruction for Surfer
    cfg = ProviderConfig.from_env()
    instr_out = surfer_steps.generate_instruction(
        cfg, mission, sources_hints, additional_context=prev_ctx, options=InvokeOptions(temperature=1.0, max_tokens=256)
    )
    instruction = instr_out.instruction.strip() or mission

    # Submit to surfer service and wait (long-running)
    if settings.SURFER_USE_MOCK:
        submit = surfer_client.explorer_submit(instruction, stream_context=stream_context, use_mock=True, sync=False)
        job_id = submit.get("job_id")
        if not job_id:
            # In some mock impls sync returns curations directly
            result = submit
        else:
            result = surfer_client.wait_for_result(job_id)
    else:
        submit = surfer_client.explorer_submit(
            instruction,
            stream_context=stream_context,
            headless=settings.SURFER_HEADLESS,
            max_steps=settings.SURFER_MAX_STEPS,
            sync=False,
        )
        job_id = submit.get("job_id")
        if not job_id:
            # fallback to sync path if service is dev-mode
            result = surfer_client.explorer_submit(
                instruction, stream_context=stream_context, headless=settings.SURFER_HEADLESS, max_steps=settings.SURFER_MAX_STEPS, sync=True
            )
        else:
            result = surfer_client.wait_for_result(job_id)

    raw_curations: List[Dict[str, Any]] = list(result.get("curations") or [])

    # LLM: turn summary -> title + hook
    remix = surfer_steps.remix_curations(cfg, mission, raw_curations)
    curated = list(remix.curations or [])

    if not curated and raw_curations:
        # Fallback: mirror raw curations (defensive)
        curated = []
        for rc in raw_curations[:4]:
            summary = (rc.get("summary") or "").strip()
            title = (summary[:110] + "...") if len(summary) > 110 else summary or "New insight"
            links = rc.get("links") or []
            clean_links = []
            for l in links[:3]:
                url = (l.get("url") or "").strip()
                if not url:
                    continue
                clean_links.append({"url": url, "title": (l.get("title") or "").strip() or None})
            if not clean_links:
                continue
            curated.append({
                "title": title,
                "hook": summary[:150],
                "links": clean_links,
            })

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
        "surfer_job_id": submit.get("job_id"),
        "surfer_status_url": submit.get("status_url"),
        "surfer_logs_url": submit.get("logs_url"),
        "surfer_result_ready": bool(raw_curations),
        "curations_raw": len(raw_curations),
        "curations_final": len([c for c in curated_dicts if (c.get("title") and c.get("links"))]),
    }

    if stream_id:
        run_row = None
        try:
            run_row = curations_repo.create_curation_run(stream_id=stream_id, job_id=job.get("id"), status="running")
            clusters_payload: List[Dict[str, Any]] = []
            persistable: List[Dict[str, Any]] = []
            for idx, item in enumerate(curated_dicts):
                title = (item.get("title") or "").strip()
                hook = (item.get("hook") or "").strip()
                links_payload = item.get("links") or []
                if not title or not hook or not links_payload:
                    continue
                persistable.append(item)
                clusters_payload.append({"title": title[:120], "hook": hook[:200], "position": len(persistable) - 1})
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
