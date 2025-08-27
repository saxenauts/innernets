import importlib
import pytest


def test_supabase_client_requires_env(monkeypatch):
    # Ensure env is not set
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    # Ensure dotenv autoload does not rehydrate values from a file
    monkeypatch.setenv("DOTENV_PATH", "__not_found__.env")

    # Reload config and client so settings reflect current env
    config_mod = importlib.import_module("app.config")
    importlib.reload(config_mod)
    mod = importlib.import_module("app.supabase_client")
    importlib.reload(mod)

    # Expect creating client without env to raise ValueError
    mod.get_supabase_client.cache_clear()  # type: ignore[attr-defined]
    with pytest.raises(ValueError):
        mod.get_supabase_client()


def test_supabase_client_with_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "fake-key")

    # Reload config and client modules so settings picks up new env
    config_mod = importlib.import_module("app.config")
    importlib.reload(config_mod)
    mod = importlib.import_module("app.supabase_client")
    importlib.reload(mod)

    class FakeClient:
        pass

    def fake_create_client(url, key):
        assert url.startswith("https://example.")
        assert key == "fake-key"
        return FakeClient()

    # Monkeypatch the function on module
    monkeypatch.setattr(mod, "create_client", fake_create_client)

    mod.get_supabase_client.cache_clear()  # type: ignore[attr-defined]
    client = mod.get_supabase_client()
    assert isinstance(client, FakeClient)
