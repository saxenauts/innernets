from fastapi import Header, HTTPException


def get_current_user_id(x_user_id: str = Header(..., alias="X-User-Id")) -> str:
    """Temporary dev auth: read user id from X-User-Id header.

    Replace with real auth (Supabase JWT) later.
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return x_user_id

