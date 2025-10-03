from __future__ import annotations

from typing import Any, Dict, Optional
import httpx

from app.config import settings


class SurferError(Exception):
    pass


def _headers() -> Dict[str, str]:
    h = {"content-type": "application/json"}
    if settings.SURFER_API_KEY:
        h["authorization"] = f"Bearer {settings.SURFER_API_KEY}"
    return h


def _base() -> str:
    return settings.SURFER_BASE_URL.rstrip("/")


def google_search(*, query: str, headless: Optional[bool] = None) -> Dict[str, Any]:
    """Call ai-surfer /api/google-search and return the result envelope.

    Returns { result: { ... }, logs: str }
    """
    payload: Dict[str, Any] = {"query": query}
    if headless is not None:
        payload["headless"] = bool(headless)
    url = f"{_base()}/api/google-search"
    with httpx.Client(timeout=60.0) as cli:
        resp = cli.post(url, headers=_headers(), json=payload)
        if resp.status_code != 200:
            raise SurferError(f"Google search failed: HTTP {resp.status_code}: {resp.text}")
        return resp.json()


def read_wave(
    *,
    urls: list[str],
    headless: Optional[bool] = None,
    citations: Optional[bool] = None,
    prune: Optional[bool] = None,
) -> Dict[str, Any]:
    """Call ai-surfer /api/read-wave and return the result envelope.

    Returns { result: { pages: [...] }, logs: str }
    """
    payload: Dict[str, Any] = {"urls": urls}
    if headless is not None:
        payload["headless"] = bool(headless)
    if citations is not None:
        payload["citations"] = bool(citations)
    if prune is not None:
        payload["prune"] = bool(prune)
    url = f"{_base()}/api/read-wave"
    with httpx.Client(timeout=60.0) as cli:
        resp = cli.post(url, headers=_headers(), json=payload)
        if resp.status_code != 200:
            raise SurferError(f"Read wave failed: HTTP {resp.status_code}: {resp.text}")
        return resp.json()
