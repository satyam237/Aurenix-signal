from __future__ import annotations

from supabase import Client, create_client

from backend.shared.config import Settings, get_settings
from backend.shared.supabase_keys import validate_service_role_key


def get_supabase_client(settings: Settings | None = None) -> Client:
    cfg = settings or get_settings()
    if not cfg.supabase_url or not cfg.supabase_service_role_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
    key_error = validate_service_role_key(cfg.supabase_service_role_key)
    if key_error:
        raise ValueError(key_error)
    return create_client(cfg.supabase_url, cfg.supabase_service_role_key)
