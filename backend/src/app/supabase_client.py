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
