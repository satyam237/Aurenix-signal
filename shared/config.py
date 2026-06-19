from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    gemini_api_key: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    openai_model: str = "gpt-4o-mini"
    gemini_model: str = "gemini-2.0-flash"

    daily_cost_cap_usd: float = 10.0
    cron_hour_utc: int = 6
    dedup_hours: int = 6
    brand_id: str = "nautikal"

    rate_limit_rpm: int = 30


def get_settings() -> Settings:
    return Settings()
