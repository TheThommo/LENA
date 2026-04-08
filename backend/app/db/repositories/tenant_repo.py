"""
Tenant Repository

CRUD operations for tenants.
"""

from uuid import UUID
from typing import Optional, List
from app.db.supabase import get_supabase_client, get_supabase_admin_client
from app.models import Tenant, TenantCreate, TenantUpdate


class TenantRepository:
    """Repository for tenant operations."""

    @staticmethod
    async def create(tenant_create: TenantCreate) -> Optional[Tenant]:
        """Create a new tenant."""
        try:
            client = get_supabase_admin_client()
            response = (
                client.table("tenants")
                .insert(
                    {
                        "name": tenant_create.name,
                        "slug": tenant_create.slug,
                        "domain": tenant_create.domain,
                        "logo_url": tenant_create.logo_url,
                        "primary_color": tenant_create.primary_color,
                    }
                )
                .execute()
            )
            if response.data and len(response.data) > 0:
                return Tenant(**response.data[0])
            return None
        except Exception as e:
            print(f"Error creating tenant: {e}")
            return None

    @staticmethod
    async def get_by_id(tenant_id: UUID) -> Optional[Tenant]:
        """Get a tenant by ID."""
        try:
            client = get_supabase_client()
            response = (
                client.table("tenants").select("*").eq("id", str(tenant_id)).execute()
            )
            if response.data and len(response.data) > 0:
                return Tenant(**response.data[0])
            return None
        except Exception as e:
            print(f"Error fetching tenant: {e}")
            return None

    @staticmethod
    async def get_by_slug(slug: str) -> Optional[Tenant]:
        """Get a tenant by slug."""
        try:
            client = get_supabase_client()
            response = (
                client.table("tenants").select("*").eq("slug", slug).execute()
            )
            if response.data and len(response.data) > 0:
                return Tenant(**response.data[0])
            return None
        except Exception as e:
            print(f"Error fetching tenant by slug: {e}")
            return None

    @staticmethod
    async def get_by_domain(domain: str) -> Optional[Tenant]:
        """Get a tenant by domain."""
        try:
            client = get_supabase_client()
            response = (
                client.table("tenants").select("*").eq("domain", domain).execute()
            )
            if response.data and len(response.data) > 0:
                return Tenant(**response.data[0])
            return None
        except Exception as e:
            print(f"Error fetching tenant by domain: {e}")
            return None

    @staticmethod
    async def list_all() -> List[Tenant]:
        """List all tenants."""
        try:
            client = get_supabase_admin_client()
            response = client.table("tenants").select("*").execute()
            return [Tenant(**row) for row in response.data] if response.data else []
        except Exception as e:
            print(f"Error listing tenants: {e}")
            return []

    @staticmethod
    async def update(
        tenant_id: UUID, tenant_update: TenantUpdate
    ) -> Optional[Tenant]:
        """Update a tenant."""
        try:
            client = get_supabase_admin_client()
            update_data = tenant_update.model_dump(exclude_unset=True)
            response = (
                client.table("tenants")
                .update(update_data)
                .eq("id", str(tenant_id))
                .execute()
            )
            if response.data and len(response.data) > 0:
                return Tenant(**response.data[0])
            return None
        except Exception as e:
            print(f"Error updating tenant: {e}")
            return None

    @staticmethod
    async def delete(tenant_id: UUID) -> bool:
        """Delete a tenant."""
        try:
            client = get_supabase_admin_client()
            response = (
                client.table("tenants").delete().eq("id", str(tenant_id)).execute()
            )
            return response.data is not None
        except Exception as e:
            print(f"Error deleting tenant: {e}")
            return False
