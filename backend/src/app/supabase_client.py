from functools import lru_cache
from typing import Optional

from .config import settings

try:
    from supabase import Client, create_client  # type: ignore
except Exception:  # pragma: no cover - library import errors are surfaced at runtime
    Client = object  # fallback type to satisfy type checkers
    def create_client(*args, **kwargs):  # type: ignore
        raise RuntimeError("supabase package not installed. See backend/pyproject.toml for dependencies.")


@lru_cache(maxsize=1)
def get_supabase_client(url: Optional[str] = None, key: Optional[str] = None) -> Client:  # type: ignore[name-defined]
    """Create or return a cached Supabase client using service role key.

    Note: The service role key must only be used on the server.
    """
    supabase_url = url or settings.SUPABASE_URL
    supabase_key = key or settings.SUPABASE_SERVICE_ROLE_KEY

    if not supabase_url or not supabase_key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")

    return create_client(supabase_url, supabase_key)


def _set_user_auth(client: "Client", token: str) -> "Client":  # type: ignore[name-defined]
    """Apply user Authorization header to a Supabase client instance.

    Compatible with older/newer supabase-py shapes (postgrest/rest).
    """
    try:
        client.postgrest.auth(token)  # type: ignore[attr-defined]
    except Exception:
        if hasattr(client, "rest") and hasattr(client.rest, "auth"):
            client.rest.auth(token)  # type: ignore[attr-defined]
    return client


@lru_cache(maxsize=256)
def _get_cached_user_client(token: str, supabase_url: str, public_anon: str) -> "Client":  # type: ignore[name-defined]
    """LRU-cached per-token Supabase client to reuse HTTP connections.

    Caching by (token, url, anon) ensures each active user reuses a pooled
    httpx connection while preserving RLS via their JWT. When the token rotates,
    a new cache entry is created automatically.
    """
    c = create_client(supabase_url, public_anon)
    return _set_user_auth(c, token)


def get_user_supabase_client(token: str, url: Optional[str] = None, anon_key: Optional[str] = None) -> Client:  # type: ignore[name-defined]
    """Return a Supabase client authenticated as the user via JWT (cached).

    Uses the anon key and sets the PostgREST Authorization header to enforce
    Row Level Security (RLS). The client is cached per (token, url, anon) to
    reuse the underlying HTTP connection pool and reduce TLS handshakes.
    """
    supabase_url = url or settings.SUPABASE_URL
    public_anon = anon_key or getattr(settings, "SUPABASE_ANON_KEY", None)

    if not supabase_url or not public_anon:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY")

    return _get_cached_user_client(token, supabase_url, public_anon)


def get_service_client() -> Client:  # type: ignore[name-defined]
    """Alias for service-role Supabase client.

    Exists for testability and to keep call sites simple in scheduler modules.
    """
    return get_supabase_client()
