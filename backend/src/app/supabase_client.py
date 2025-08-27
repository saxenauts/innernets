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


def get_user_supabase_client(token: str, url: Optional[str] = None, anon_key: Optional[str] = None) -> Client:  # type: ignore[name-defined]
    """Create a Supabase client authenticated as the user via JWT.

    This uses the anon key and sets the PostgREST auth header to the provided user token,
    ensuring Row Level Security (RLS) policies are enforced by the database.
    """
    supabase_url = url or settings.SUPABASE_URL
    public_anon = anon_key or getattr(settings, "SUPABASE_ANON_KEY", None)

    if not supabase_url or not public_anon:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY")

    client = create_client(supabase_url, public_anon)
    # Set Authorization header for PostgREST requests to the user's access token
    try:
        client.postgrest.auth(token)  # type: ignore[attr-defined]
    except Exception:
        # Fallback for older clients: set on rest client if available
        if hasattr(client, "rest") and hasattr(client.rest, "auth"):
            client.rest.auth(token)  # type: ignore[attr-defined]
    return client
