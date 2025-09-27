from fastapi.testclient import TestClient
import jwt


def _auth_headers(user_id: str = "u-404"):
    from app.config import settings
    return {
        "Authorization": "Bearer "
        + jwt.encode({"sub": user_id, "exp": 9999999999, "aud": "authenticated"}, settings.SUPABASE_JWT_SECRET or "testsecret", algorithm="HS256")
    }


def test_error_shape_404_not_found(monkeypatch):
    # Patch settings secret for JWT encode/verify
    from app.config import settings
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "testsecret", raising=False)

    # Make profile repo return None to trigger 404
    from app.routes import profile as profile_module

    def fake_get_profile(user_id: str, token: str):
        return None

    monkeypatch.setattr(profile_module.profile_repo, "get_profile", fake_get_profile)

    from app.main import app
    app.dependency_overrides.clear()
    client = TestClient(app)

    r = client.get("/me/profile", headers=_auth_headers())
    assert r.status_code == 404
    body = r.json()
    assert body.get("code") == "NotFound"
    assert isinstance(body.get("message"), str)


def test_error_shape_422_validation(monkeypatch):
    # Patch settings secret for JWT encode/verify
    from app.config import settings
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "testsecret", raising=False)

    from app.main import app
    app.dependency_overrides.clear()
    client = TestClient(app)

    payload = {"mission": "M1", "cadence": "invalid"}
    r = client.post("/streams", headers=_auth_headers(), json=payload)
    assert r.status_code == 422
    body = r.json()
    assert body.get("code") == "BadRequest"
    assert isinstance(body.get("message"), str)

