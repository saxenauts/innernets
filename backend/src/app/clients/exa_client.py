from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from exa_py import Exa

from ..config import settings


def _camel_to_snake(name: str) -> str:
    out = []
    for ch in name:
        if ch.isupper():
            out.append('_')
            out.append(ch.lower())
        else:
            out.append(ch)
    return ''.join(out).lstrip('_')


def _snakecase_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in d.items():
        nk = _camel_to_snake(k)
        if isinstance(v, dict):
            out[nk] = _snakecase_dict(v)
        elif isinstance(v, list):
            out[nk] = [_snakecase_dict(x) if isinstance(x, dict) else x for x in v]
        else:
            out[nk] = v
    return out


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

    # Search + optional contents: accept Exa-style JSON body
    def search_json(self, body: Dict[str, Any]) -> Dict[str, Any]:
        d = _snakecase_dict(body)
        contents = d.pop("contents", None)
        if isinstance(contents, dict):
            # normalize extras.imagelinks -> image_links inside contents
            extras = contents.get("extras")
            if isinstance(extras, dict) and "imagelinks" in extras:
                extras = dict(extras)
                extras["image_links"] = extras.pop("imagelinks")
                contents["extras"] = extras
            d.update(contents)

        # Caps enforcement
        if d.get("type") in {"neural", "auto"} and d.get("num_results", 0) > 25:
            raise ValueError("numResults must be ≤ 25 for neural/auto per cost cap")
        if d.get("type") == "keyword" and d.get("num_results", 0) > 100:
            raise ValueError("numResults must be ≤ 100 for keyword searches")

        res = self._exa.search_and_contents(**d)
        return _to_plain(res)

    def search_json(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Accept Exa JSON (camelCase per docs), convert, and call SDK.

        This keeps routes aligned with Exa's OpenAPI while we use the Python SDK.
        """
        def camel_to_snake(name: str) -> str:
            out = []
            for ch in name:
                if ch.isupper():
                    out.append('_')
                    out.append(ch.lower())
                else:
                    out.append(ch)
            s = ''.join(out).lstrip('_')
            return s

        def snakecase_dict(d: Dict[str, Any]) -> Dict[str, Any]:
            out: Dict[str, Any] = {}
            for k, v in d.items():
                nk = camel_to_snake(k)
                if isinstance(v, dict):
                    out[nk] = snakecase_dict(v)
                elif isinstance(v, list):
                    out[nk] = [snakecase_dict(x) if isinstance(x, dict) else x for x in v]
                else:
                    out[nk] = v
            return out

        d = snakecase_dict(body)
        # Expand contents.* to top-level args expected by SDK
        contents = d.pop("contents", None)
        if isinstance(contents, dict):
            # normalize extras.imageLinks -> image_links
            extras = contents.get("extras")
            if isinstance(extras, dict):
                if "imagelinks" in extras:
                    extras = dict(extras)
                    extras["image_links"] = extras.pop("imagelinks")
                    contents["extras"] = extras
            d.update(contents)

        # Caps enforcement
        if d.get("type") in {"neural", "auto"} and d.get("num_results", 0) > 25:
            raise ValueError("numResults must be ≤ 25 for neural/auto per cost cap")
        if d.get("type") == "keyword" and d.get("num_results", 0) > 100:
            raise ValueError("numResults must be ≤ 100 for keyword searches")

        res = self._exa.search_and_contents(**d)
        return _to_plain(res)  # type: ignore[no-any-return]

    # Contents by URL list
    def contents_json(self, body: Dict[str, Any]) -> Dict[str, Any]:
        d = _snakecase_dict(body)
        # Normalize extras.imagelinks -> image_links
        extras = d.get("extras")
        if isinstance(extras, dict) and "imagelinks" in extras:
            extras = dict(extras)
            extras["image_links"] = extras.pop("imagelinks")
            d["extras"] = extras
        res = self._exa.get_contents(**d)
        return _to_plain(res)


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
