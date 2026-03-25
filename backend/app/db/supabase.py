"""
Supabase Client

Handles database connection via Supabase Python client.
Uses pgvector extension for semantic search (future feature).
"""

from typing import Optional
from supabase import create_client, Client

from app.core.config import settings

_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get or create the Supabase client."""
    global _client
    if _client is None:
        if not settings.supabase_url or not settings.supabase_anon_key:
            raise ValueError(
                "Supabase URL and anon key must be set in environment variables. "
                "Check your .env file."
            )
        _client = create_client(
            settings.supabase_url,
            settings.supabase_anon_key,
        )
    return _client


async def test_connection() -> dict:
    """Test the Supabase connection."""
    try:
        client = get_supabase_client()
        # Simple health check: try to access the API
        # This will fail gracefully if tables don't exist yet
        result = client.table("_health_check_placeholder").select("*").limit(1).execute()
        return {
            "source": "Supabase",
            "status": "connected",
            "url": settings.supabase_url,
            "note": "Connection established. Tables not yet created.",
        }
    except Exception as e:
        error_str = str(e)
        # A "relation does not exist" error actually means we connected successfully
        if "does not exist" in error_str or "relation" in error_str:
            return {
                "source": "Supabase",
                "status": "connected",
                "url": settings.supabase_url,
                "note": "Connection successful. Database tables need to be created.",
            }
        return {
            "source": "Supabase",
            "status": "error",
            "error": error_str,
            "url_configured": bool(settings.supabase_url),
        }
