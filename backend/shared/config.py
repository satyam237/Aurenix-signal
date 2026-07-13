from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    gemini_api_key: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    openai_model: str = "gpt-5-mini"
    gemini_model: str = "gemini-3-flash-preview"

    daily_cost_cap_usd: float = 10.0
    cron_hour_utc: int = 6
    dedup_hours: int = 6
    brand_id: str = "nautikal"

    rate_limit_rpm: int = 30
    bulk_concurrency: int = 6


def get_settings() -> Settings:
    return Settings()
