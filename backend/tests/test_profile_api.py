from fastapi.testclient import TestClient
import jwt


def test_get_profile_not_found(monkeypatch):
    # Fake repo to avoid DB
    from app.routes import profile as profile_module

    def fake_get_profile(user_id: str, token: str | None = None):
        return None

    monkeypatch.setattr(profile_module.profile_repo, "get_profile", fake_get_profile)

    # Patch auth secret
    from app.config import settings
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "testsecret", raising=False)

    token = jwt.encode({"sub": "00000000-0000-0000-0000-000000000001", "exp": 9999999999, "aud": "authenticated"}, "testsecret", algorithm="HS256")

    from app.main import app
    client = TestClient(app)
    # Clear any overrides from other tests
    app.dependency_overrides.clear()

    r = client.get("/me/profile", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_put_profile_upserts_and_returns(monkeypatch):
    from app.routes import profile as profile_module

    def fake_upsert_profile(user_id: str, fields, token: str | None = None):
        return {
            "id": user_id,
            "display_name": fields.get("display_name", None),
            "time_zone": fields.get("time_zone", "UTC"),
        }

    monkeypatch.setattr(profile_module.profile_repo, "upsert_profile", fake_upsert_profile)

    # Patch auth secret
    from app.config import settings
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "testsecret", raising=False)

    token = jwt.encode({"sub": "u-123", "exp": 9999999999, "aud": "authenticated"}, "testsecret", algorithm="HS256")

    from app.main import app
    client = TestClient(app)

    payload = {"display_name": "Jane", "time_zone": "UTC"}
    r = client.put("/me/profile", headers={"Authorization": f"Bearer {token}"}, json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "u-123"
    assert data["display_name"] == "Jane"
    assert data["time_zone"] == "UTC"
