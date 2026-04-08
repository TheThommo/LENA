"""
Analytics Repository

CRUD operations for analytics data.
Tracks usage events, search logs, and audit trails.
"""

from uuid import UUID
from typing import Optional, List
from app.db.supabase import get_supabase_client, get_supabase_admin_client
from app.models import (
    UsageAnalytics,
    UsageAnalyticsCreate,
    SearchLog,
    SearchLogCreate,
    AuditEntry,
    AuditEntryCreate,
)


class UsageAnalyticsRepository:
    """Repository for usage analytics operations."""

    @staticmethod
    async def create(analytics_create: UsageAnalyticsCreate) -> Optional[UsageAnalytics]:
        """Create a new usage analytics event."""
        try:
            client = get_supabase_admin_client()
            response = (
                client.table("usage_analytics")
                .insert(
                    {
                        "tenant_id": str(analytics_create.tenant_id),
                        "user_id": str(analytics_create.user_id)
                        if analytics_create.user_id
                        else None,
                        "action": analytics_create.action,
                        "metadata": analytics_create.metadata,
                    }
                )
                .execute()
            )
            if response.data and len(response.data) > 0:
                return UsageAnalytics(**response.data[0])
            return None
        except Exception as e:
            print(f"Error creating usage analytics: {e}")
            return None

    @staticmethod
    async def get_by_tenant_id(
        tenant_id: UUID, limit: int = 100
    ) -> List[UsageAnalytics]:
        """Get recent analytics events for a tenant."""
        try:
            client = get_supabase_admin_client()
            response = (
                client.table("usage_analytics")
                .select("*")
                .eq("tenant_id", str(tenant_id))
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return (
                [UsageAnalytics(**row) for row in response.data]
                if response.data
                else []
            )
        except Exception as e:
            print(f"Error fetching tenant analytics: {e}")
            return []

    @staticmethod
    async def get_by_user_id(
        user_id: UUID, limit: int = 50
    ) -> List[UsageAnalytics]:
        """Get analytics events for a user."""
        try:
            client = get_supabase_admin_client()
            response = (
                client.table("usage_analytics")
                .select("*")
                .eq("user_id", str(user_id))
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return (
                [UsageAnalytics(**row) for row in response.data]
                if response.data
                else []
            )
        except Exception as e:
            print(f"Error fetching user analytics: {e}")
            return []


class SearchLogRepository:
    """Repository for search log operations."""

    @staticmethod
    async def create(search_log_create: SearchLogCreate) -> Optional[SearchLog]:
        """Create a new search log."""
        try:
            client = get_supabase_admin_client()
            response = (
                client.table("search_logs")
                .insert(
                    {
                        "search_id": str(search_log_create.search_id),
                        "response_time_ms": search_log_create.response_time_ms,
                        "sources_queried": search_log_create.sources_queried,
                        "sources_succeeded": search_log_create.sources_succeeded,
                        "total_results": search_log_create.total_results,
                        "pulse_status": search_log_create.pulse_status.value
                        if search_log_create.pulse_status
                        else None,
                    }
                )
                .execute()
            )
            if response.data and len(response.data) > 0:
                return SearchLog(**response.data[0])
            return None
        except Exception as e:
            print(f"Error creating search log: {e}")
            return None

    @staticmethod
    async def get_by_search_id(search_id: UUID) -> Optional[SearchLog]:
        """Get the log for a specific search."""
        try:
            client = get_supabase_client()
            response = (
                client.table("search_logs")
                .select("*")
                .eq("search_id", str(search_id))
                .execute()
            )
            if response.data and len(response.data) > 0:
                return SearchLog(**response.data[0])
            return None
        except Exception as e:
            print(f"Error fetching search log: {e}")
            return None

    @staticmethod
    async def get_recent(limit: int = 100) -> List[SearchLog]:
        """Get recent search logs."""
        try:
            client = get_supabase_admin_client()
            response = (
                client.table("search_logs")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return [SearchLog(**row) for row in response.data] if response.data else []
        except Exception as e:
            print(f"Error fetching recent search logs: {e}")
            return []


class AuditTrailRepository:
    """Repository for audit trail operations."""

    @staticmethod
    async def create(audit_create: AuditEntryCreate) -> Optional[AuditEntry]:
        """Create a new audit entry."""
        try:
            client = get_supabase_admin_client()
            response = (
                client.table("audit_trail")
                .insert(
                    {
                        "user_id": str(audit_create.user_id)
                        if audit_create.user_id
                        else None,
                        "tenant_id": str(audit_create.tenant_id),
                        "action": audit_create.action.value,
                        "resource_type": audit_create.resource_type,
                        "resource_id": audit_create.resource_id,
                        "details": audit_create.details,
                        "ip_address": audit_create.ip_address,
                    }
                )
                .execute()
            )
            if response.data and len(response.data) > 0:
                return AuditEntry(**response.data[0])
            return None
        except Exception as e:
            print(f"Error creating audit entry: {e}")
            return None

    @staticmethod
    async def get_by_user_id(user_id: UUID, limit: int = 50) -> List[AuditEntry]:
        """Get audit entries for a user."""
        try:
            client = get_supabase_admin_client()
            response = (
                client.table("audit_trail")
                .select("*")
                .eq("user_id", str(user_id))
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return (
                [AuditEntry(**row) for row in response.data]
                if response.data
                else []
            )
        except Exception as e:
            print(f"Error fetching user audit entries: {e}")
            return []

    @staticmethod
    async def get_by_tenant_id(
        tenant_id: UUID, limit: int = 100
    ) -> List[AuditEntry]:
        """Get audit entries for a tenant."""
        try:
            client = get_supabase_admin_client()
            response = (
                client.table("audit_trail")
                .select("*")
                .eq("tenant_id", str(tenant_id))
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return (
                [AuditEntry(**row) for row in response.data]
                if response.data
                else []
            )
        except Exception as e:
            print(f"Error fetching tenant audit entries: {e}")
            return []

    @staticmethod
    async def get_by_action(action: str, limit: int = 50) -> List[AuditEntry]:
        """Get audit entries by action type."""
        try:
            client = get_supabase_admin_client()
            response = (
                client.table("audit_trail")
                .select("*")
                .eq("action", action)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return (
                [AuditEntry(**row) for row in response.data]
                if response.data
                else []
            )
        except Exception as e:
            print(f"Error fetching audit entries by action: {e}")
            return []
