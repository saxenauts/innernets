from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

import jwt
from fastapi import Header, HTTPException

from .config import settings


class AuthError(HTTPException):
    def __init__(self, detail: str = "Unauthorized") -> None:
        super().__init__(status_code=401, detail=detail)


def _get_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise AuthError("Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthError("Invalid Authorization header format")
    return parts[1]


def decode_supabase_jwt(token: str) -> Dict[str, Any]:
    secret = settings.SUPABASE_JWT_SECRET
    if not secret:
        raise AuthError("Server missing SUPABASE_JWT_SECRET")
    try:
        claims = jwt.decode(
            token,
            key=secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
            audience=settings.SUPABASE_JWT_AUD,
        )
        return claims
    except jwt.ExpiredSignatureError:
        raise AuthError("Token expired")
    except jwt.InvalidTokenError:
        raise AuthError("Invalid token")


def get_current_user_id(Authorization: Optional[str] = Header(default=None)) -> str:
    """Authenticate request using Supabase JWT in Authorization header.

    Returns the `sub` (user id) claim on success.
    """
    token = _get_bearer_token(Authorization)
    claims = decode_supabase_jwt(token)
    user_id = claims.get("sub") or claims.get("user_id") or claims.get("userId")
    if not user_id:
        raise AuthError("Token missing subject")
    return str(user_id)
