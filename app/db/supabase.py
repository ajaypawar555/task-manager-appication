"""Supabase client construction."""

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    """Create one configured Supabase client on first use."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key.get_secret_value():
        raise RuntimeError("Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY.")
    key = settings.supabase_key.get_secret_value()
    if key.startswith("sb_publishable_"):
        raise RuntimeError(
            "SUPABASE_KEY is a publishable key, which cannot access this app's protected "
            "tasks table. "
            "Set a server-side Supabase secret key or legacy service_role key in .env."
        )
    return create_client(settings.supabase_url, key)
