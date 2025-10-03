import os
from typing import Optional
from dotenv import load_dotenv


class Settings:
    """Minimal environment loader. Avoids extra deps for now.

    NOTE: In development, load .env via `python-dotenv` when running the app.
    """

    def __init__(self) -> None:
        # Load .env if present (does not override existing env)
        load_dotenv(os.getenv("DOTENV_PATH", ".env"), override=False)
        # Core
        self.APP_ENV: str = os.getenv("APP_ENV", "local")
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")
        self.TZ: str = os.getenv("TZ", "UTC")

        # Supabase / DB
        self.SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
        self.SUPABASE_SERVICE_ROLE_KEY: Optional[str] = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        # Public anon key (client-facing). Must be spelled exactly SUPABASE_ANON_KEY.
        self.SUPABASE_ANON_KEY: Optional[str] = os.getenv("SUPABASE_ANON_KEY")
        self.POSTGRES_CONNECTION_STRING: Optional[str] = os.getenv("POSTGRES_CONNECTION_STRING")

        # Providers
        self.PROVIDER: str = os.getenv("PROVIDER", "azure_openai")
        self.OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.OPENAI_ORG: Optional[str] = os.getenv("OPENAI_ORG")
        self.OPENAI_BASE_URL: Optional[str] = os.getenv("OPENAI_BASE_URL")
        self.AZURE_OPENAI_ENDPOINT: Optional[str] = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.AZURE_OPENAI_API_VERSION: Optional[str] = os.getenv("AZURE_OPENAI_API_VERSION")
        self.AZURE_OPENAI_API_KEY: Optional[str] = os.getenv("AZURE_OPENAI_API_KEY")
        # Azure deployment name (canonical)
        self.AZURE_OPENAI_DEPLOYMENT_NAME: Optional[str] = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

        # Exa
        self.EXA_API_KEY: Optional[str] = os.getenv("EXA_API_KEY")
        self.EXA_BASE_URL: str = os.getenv("EXA_BASE_URL", "https://api.exa.ai")

        # Supabase Auth
        self.SUPABASE_JWT_SECRET: Optional[str] = os.getenv("SUPABASE_JWT_SECRET")
        self.SUPABASE_JWT_AUD: str = os.getenv("SUPABASE_JWT_AUD", "authenticated")

        # Scheduler
        self.SCHEDULE_POLL_INTERVAL_MS: int = int(os.getenv("SCHEDULE_POLL_INTERVAL_MS", "30000"))
        self.SCHEDULE_MAX_JOBS_PER_TICK: int = int(os.getenv("SCHEDULE_MAX_JOBS_PER_TICK", "25"))

        # Surfer Docker Service (external)
        # Note: choose a port that will not conflict with this backend in dev.
        # Example: SURFER_BASE_URL=http://127.0.0.1:8001
        self.SURFER_BASE_URL: str = os.getenv("SURFER_BASE_URL", "http://127.0.0.1:8001")
        self.SURFER_API_KEY: Optional[str] = os.getenv("SURFER_API_KEY")
        self.SURFER_POLL_INTERVAL_S: int = int(os.getenv("SURFER_POLL_INTERVAL_S", "30"))
        self.SURFER_MAX_WAIT_S: int = int(os.getenv("SURFER_MAX_WAIT_S", "1800"))  # 30 minutes
        self.SURFER_HEADLESS: bool = os.getenv("SURFER_HEADLESS", "1") in {"1", "true", "TRUE"}
        self.SURFER_MAX_STEPS: int = int(os.getenv("SURFER_MAX_STEPS", "3"))
        # Depth per iteration for follow-up reading waves (SERP -> page -> subpage ...)
        self.SURFER_MAX_DEPTH: int = int(os.getenv("SURFER_MAX_DEPTH", "3"))
        # Reading batch size per wave (Explorer uses ~5)
        self.SURFER_BATCH_SIZE: int = int(os.getenv("SURFER_BATCH_SIZE", "5"))
        # Optional concurrency hints (used for search fanout only on our side)
        self.SURFER_SEARCH_CONCURRENCY: int = int(os.getenv("SURFER_SEARCH_CONCURRENCY", "3"))
        self.SURFER_READ_CONCURRENCY: int = int(os.getenv("SURFER_READ_CONCURRENCY", "8"))
        # Dev-only: route to /api/explorer/mock
        self.SURFER_USE_MOCK: bool = os.getenv("SURFER_USE_MOCK", "0") in {"1", "true", "TRUE"}

        # New Explorer Engine (v2) flags
        self.SURFER_ENGINE_ENABLED: bool = os.getenv("SURFER_ENGINE_ENABLED", "0") in {"1", "true", "TRUE"}
        # logging style for the engine: 'surfer' to mimic ai-surfer explorer logs
        self.SURFER_ENGINE_LOG_STYLE: str = os.getenv("SURFER_ENGINE_LOG_STYLE", "surfer")


settings = Settings()

# no-op change to trigger staging deploy via CI (safe comment)
