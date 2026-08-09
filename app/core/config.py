from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_env: str = "development"
    app_version: str = "0.1.0"
    log_level: str = "INFO"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/dev.db"

    # LLM
    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    openai_api_key: str = ""
    llm_fallback_provider: str = ""

    # Gmail
    gmail_credentials_file: str = "credentials.json"
    gmail_token_file: str = "token.json"

    # Outreach defaults
    default_follow_up_days: int = 3
    default_max_follow_ups: int = 2

    # Sender profile (your identity — used by EmailGeneratorAgent for personalization)
    sender_name: str = ""
    sender_email: str = ""
    sender_background: str = ""  # e.g. "ML Engineer with 5 years exp in Python and LLMs"
    sender_tone: str = "professional"  # "professional" | "casual" | "concise"

    # Scheduler
    scheduler_interval_minutes: int = 720  # Runs twice a day (every 12 hours)

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.database_url


# Singleton — import and use `settings` directly throughout the app
settings = Settings()
