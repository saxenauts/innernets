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


settings = Settings()
