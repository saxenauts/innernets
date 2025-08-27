from __future__ import annotations

from typing import Any, Dict, Optional

from exa_py import Exa

from ..config import settings
from .exa_schemas import SearchResponse, ContentsResponse


class ExaClient:
    """Thin wrapper around exa-py to centralize config and safe defaults."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None) -> None:
        key = api_key or settings.EXA_API_KEY
        if not key:
            raise RuntimeError("Missing EXA_API_KEY. Set it in backend/.env or environment.")
        # exa-py accepts a base_url kwarg in recent versions; fallback if not present
        try:
            self._exa = Exa(key, base_url=base_url or settings.EXA_BASE_URL)
        except TypeError:
            self._exa = Exa(key)

    # Search + optional contents (SDK-first, snake_case)
    def search(self, **kwargs: Any) -> SearchResponse:
        t = kwargs.get("type", "auto")
        # Default to 25 to stay in the low-cost tier for neural/auto
        n = kwargs.get("num_results", 25)
        kwargs["num_results"] = n
        if t in {"neural", "auto"} and n > 25:
            raise ValueError("num_results must be ≤ 25 for neural/auto per cost cap")
        if t == "keyword" and n > 100:
            raise ValueError("num_results must be ≤ 100 for keyword searches")
        res = self._exa.search(**kwargs)
        rd = _to_plain(res)
        return SearchResponse(**rd)

    def search_and_contents(self, **kwargs: Any) -> SearchResponse:
        t = kwargs.get("type", "auto")
        # Default to 25 to stay in the low-cost tier for neural/auto
        n = kwargs.get("num_results", 25)
        kwargs["num_results"] = n
        if t in {"neural", "auto"} and n > 25:
            raise ValueError("num_results must be ≤ 25 for neural/auto per cost cap")
        if t == "keyword" and n > 100:
            raise ValueError("num_results must be ≤ 100 for keyword searches")
        res = self._exa.search_and_contents(**kwargs)
        rd = _to_plain(res)
        return SearchResponse(**rd)

    # Contents by URL list
    def get_contents(self, **kwargs: Any) -> ContentsResponse:
        res = self._exa.get_contents(**kwargs)
        rd = _to_plain(res)
        return ContentsResponse(**rd)


_client: Optional[ExaClient] = None


def get_exa_client() -> ExaClient:
    global _client
    if _client is None:
        _client = ExaClient()
    return _client


def _to_plain(obj: Any) -> Any:
    """Recursively convert SDK result objects (dataclasses/pydantic) to plain dict/list types."""
    from dataclasses import is_dataclass, asdict

    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, list):
        return [_to_plain(x) for x in obj]
    if isinstance(obj, tuple):
        return tuple(_to_plain(x) for x in obj)
    if isinstance(obj, dict):
        return {k: _to_plain(v) for k, v in obj.items()}
    if is_dataclass(obj):
        try:
            return _to_plain(asdict(obj))
        except Exception:
            pass
    for attr in ("model_dump", "dict"):
        fn = getattr(obj, attr, None)
        if callable(fn):
            try:
                return _to_plain(fn())
            except Exception:
                pass
    d = getattr(obj, "__dict__", None)
    if isinstance(d, dict):
        return _to_plain(d)
    return obj
