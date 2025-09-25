from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from datetime import datetime, timezone

from ..supabase_client import get_service_client


def _urls_table():
    return get_service_client().table("urls")


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc or ""
    except Exception:
        return ""


def ensure_url(url: str, title: Optional[str] = None, description: Optional[str] = None, published_at: Optional[str] = None, domain: Optional[str] = None) -> Dict[str, Any]:
    u = (url or "").strip()
    if not u:
        raise ValueError("url required")
    dm = domain or _domain(u)
    tbl = _urls_table()
    # Try select
    got = tbl.select("*").eq("url", u).limit(1).execute().data or []
    if got:
        row = got[0]
        patch: Dict[str, Any] = {"last_seen_at": datetime.now(timezone.utc).isoformat()}
        if title:
            patch["last_title"] = title
        if description:
            patch["last_description"] = description
        if published_at:
            patch["last_published_at"] = published_at
        if dm and not row.get("domain"):
            patch["domain"] = dm
        if patch:
            tbl.update(patch).eq("id", row["id"]).execute()
        # Re-fetch minimal fields
        got2 = tbl.select("id, url, domain, last_title, last_description, last_published_at").eq("id", row["id"]).limit(1).execute().data or []
        return got2[0] if got2 else row
    # Insert new
    payload: Dict[str, Any] = {
        "url": u,
        "domain": dm or "",
        "last_seen_at": datetime.now(timezone.utc).isoformat(),
    }
    if title:
        payload["last_title"] = title
    if description:
        payload["last_description"] = description
    if published_at:
        payload["last_published_at"] = published_at
    row = tbl.insert(payload).execute().data[0]
    return row


def bulk_ensure(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for it in items:
        url = it.get("url")
        if not url:
            continue
        row = ensure_url(
            url,
            title=it.get("title"),
            description=it.get("description"),
            published_at=it.get("published_at"),
            domain=it.get("domain"),
        )
        out.append({"url": row["url"], "url_id": row["id"]})
    return out
