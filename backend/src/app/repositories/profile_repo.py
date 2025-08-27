from typing import Optional, Dict, Any, List

from ..supabase_client import get_supabase_client, get_user_supabase_client


def _profiles_table(token: str | None = None):
    if token:
        return get_user_supabase_client(token).table("profiles")
    return get_supabase_client().table("profiles")


def get_profile(user_id: str, token: str | None = None) -> Optional[Dict[str, Any]]:
    tbl = _profiles_table(token)
    res = tbl.select("id, display_name, time_zone").eq("id", user_id).limit(1).execute()
    data = getattr(res, "data", None)
    if not data:
        return None
    if isinstance(data, list):
        return data[0] if data else None
    return data


def upsert_profile(user_id: str, fields: Dict[str, Any], token: str | None = None) -> Dict[str, Any]:
    payload = {"id": user_id}
    payload.update({k: v for k, v in fields.items() if v is not None})
    tbl = _profiles_table(token)
    # Some versions of supabase/postgrest python do not support chaining select()/single() after upsert.
    # Perform upsert, then select the row.
    tbl.upsert(payload, on_conflict="id").execute()
    row = get_profile(user_id, token)
    if row is None:
        # Fallback: synthesize minimal response
        return {
            "id": user_id,
            "display_name": payload.get("display_name"),
            "time_zone": payload.get("time_zone", "UTC"),
        }
    return row
