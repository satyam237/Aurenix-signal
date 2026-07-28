"""Supabase key validation helpers."""

from __future__ import annotations


def validate_service_role_key(key: str) -> str | None:
    """Return an error message if the key is not a server-side secret key."""
    if not key:
        return "SUPABASE_SERVICE_ROLE_KEY is not set"
    if key.startswith("sb_publishable_"):
        return (
            "SUPABASE_SERVICE_ROLE_KEY is set to a publishable (public) key. "
            "Use the secret key from Supabase Dashboard → Settings → API → Secret key "
            "(starts with sb_secret_ or legacy service_role JWT)."
        )
    if key.startswith("sb_secret_") or key.startswith("eyJ"):
        return None
    return (
        "SUPABASE_SERVICE_ROLE_KEY format not recognized. "
        "Use sb_secret_... or legacy service_role JWT from Supabase Dashboard → Settings → API."
    )
