"""
Session Repository

CRUD operations for user sessions.
Tracks access patterns for analytics.
"""

from uuid import UUID
from typing import Optional, List
from datetime import datetime
from app.db.supabase import get_supabase_client, get_supabase_admin_client
from app.models import Session, SessionCreate, SessionUpdate


class SessionRepository:
    """Repository for session operations."""

    @staticmethod
    async def create(session_create: SessionCreate) -> Optional[Session]:
        """Create a new session."""
        try:
            client = get_supabase_client()
            response = (
                client.table("sessions")
                .insert(
                    {
                        "user_id": str(session_create.user_id)
                        if session_create.user_id
                        else None,
                        "tenant_id": str(session_create.tenant_id),
                        "ip_address": session_create.ip_address,
                        "geo_city": session_create.geo_city,
                        "geo_country": session_create.geo_country,
                        "geo_lat": session_create.geo_lat,
                        "geo_lon": session_create.geo_lon,
                        "referrer": session_create.referrer,
                        "utm_source": session_create.utm_source,
                        "utm_medium": session_create.utm_medium,
                        "utm_campaign": session_create.utm_campaign,
                    }
                )
                .execute()
            )
            if response.data and len(response.data) > 0:
                return Session(**response.data[0])
            return None
        except Exception as e:
            print(f"Error creating session: {e}")
            return None

    @staticmethod
    async def get_by_id(session_id: UUID) -> Optional[Session]:
        """Get a session by ID."""
        try:
            client = get_supabase_client()
            response = (
                client.table("sessions")
                .select("*")
                .eq("id", str(session_id))
                .execute()
            )
            if response.data and len(response.data) > 0:
                return Session(**response.data[0])
            return None
        except Exception as e:
            print(f"Error fetching session: {e}")
            return None

    @staticmethod
    async def get_by_user_id(user_id: UUID) -> List[Session]:
        """Get all sessions for a user."""
        try:
            client = get_supabase_client()
            response = (
                client.table("sessions")
                .select("*")
                .eq("user_id", str(user_id))
                .order("started_at", desc=True)
                .execute()
            )
            return [Session(**row) for row in response.data] if response.data else []
        except Exception as e:
            print(f"Error fetching user sessions: {e}")
            return []

    @staticmethod
    async def get_by_tenant_id(tenant_id: UUID, limit: int = 100) -> List[Session]:
        """Get recent sessions for a tenant."""
        try:
            client = get_supabase_client()
            response = (
                client.table("sessions")
                .select("*")
                .eq("tenant_id", str(tenant_id))
                .order("started_at", desc=True)
                .limit(limit)
                .execute()
            )
            return [Session(**row) for row in response.data] if response.data else []
        except Exception as e:
            print(f"Error fetching tenant sessions: {e}")
            return []

    @staticmethod
    async def update(
        session_id: UUID, session_update: SessionUpdate
    ) -> Optional[Session]:
        """Update a session."""
        try:
            client = get_supabase_client()
            update_data = session_update.model_dump(exclude_unset=True, mode='json')
            response = (
                client.table("sessions")
                .update(update_data)
                .eq("id", str(session_id))
                .execute()
            )
            if response.data and len(response.data) > 0:
                return Session(**response.data[0])
            return None
        except Exception as e:
            print(f"Error updating session: {e}")
            return None

    @staticmethod
    async def end_session(session_id: UUID) -> Optional[Session]:
        """End a session by setting ended_at."""
        try:
            client = get_supabase_client()
            response = (
                client.table("sessions")
                .update({"ended_at": "now()"})
                .eq("id", str(session_id))
                .execute()
            )
            if response.data and len(response.data) > 0:
                return Session(**response.data[0])
            return None
        except Exception as e:
            print(f"Error ending session: {e}")
            return None
