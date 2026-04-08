"""
User Repository

CRUD operations for users and user-tenant relationships.
"""

from uuid import UUID
from typing import Optional, List
from app.db.supabase import get_supabase_client, get_supabase_admin_client
from app.models import (
    User,
    UserCreate,
    UserUpdate,
    UserPublic,
    UserTenant,
    UserTenantCreate,
)


class UserRepository:
    """Repository for user operations."""

    @staticmethod
    async def create(user_create: UserCreate) -> Optional[User]:
        """Create a new user."""
        try:
            client = get_supabase_admin_client()
            response = (
                client.table("users")
                .insert(
                    {
                        "email": user_create.email,
                        "name": user_create.name,
                        "tenant_id": str(user_create.tenant_id),
                        "role": user_create.role.value,
                        "persona_type": user_create.persona_type.value,
                    }
                )
                .execute()
            )
            if response.data and len(response.data) > 0:
                return User(**response.data[0])
            return None
        except Exception as e:
            print(f"Error creating user: {e}")
            return None

    @staticmethod
    async def get_by_id(user_id: UUID) -> Optional[User]:
        """Get a user by ID."""
        try:
            client = get_supabase_client()
            response = client.table("users").select("*").eq("id", str(user_id)).execute()
            if response.data and len(response.data) > 0:
                return User(**response.data[0])
            return None
        except Exception as e:
            print(f"Error fetching user: {e}")
            return None

    @staticmethod
    async def get_by_email(email: str) -> Optional[User]:
        """Get a user by email."""
        try:
            client = get_supabase_client()
            response = (
                client.table("users").select("*").eq("email", email).execute()
            )
            if response.data and len(response.data) > 0:
                return User(**response.data[0])
            return None
        except Exception as e:
            print(f"Error fetching user by email: {e}")
            return None

    @staticmethod
    async def get_by_tenant_id(tenant_id: UUID) -> List[User]:
        """Get all users in a tenant."""
        try:
            client = get_supabase_client()
            response = (
                client.table("users")
                .select("*")
                .eq("tenant_id", str(tenant_id))
                .execute()
            )
            return [User(**row) for row in response.data] if response.data else []
        except Exception as e:
            print(f"Error fetching users by tenant: {e}")
            return []

    @staticmethod
    async def update(user_id: UUID, user_update: UserUpdate) -> Optional[User]:
        """Update a user."""
        try:
            client = get_supabase_admin_client()
            update_data = {}
            if user_update.email is not None:
                update_data["email"] = user_update.email
            if user_update.name is not None:
                update_data["name"] = user_update.name
            if user_update.role is not None:
                update_data["role"] = user_update.role.value
            if user_update.persona_type is not None:
                update_data["persona_type"] = user_update.persona_type.value

            response = (
                client.table("users")
                .update(update_data)
                .eq("id", str(user_id))
                .execute()
            )
            if response.data and len(response.data) > 0:
                return User(**response.data[0])
            return None
        except Exception as e:
            print(f"Error updating user: {e}")
            return None

    @staticmethod
    async def update_last_login(user_id: UUID) -> Optional[User]:
        """Update a user's last login timestamp."""
        try:
            client = get_supabase_admin_client()
            response = (
                client.table("users")
                .update({"last_login_at": "now()"})
                .eq("id", str(user_id))
                .execute()
            )
            if response.data and len(response.data) > 0:
                return User(**response.data[0])
            return None
        except Exception as e:
            print(f"Error updating last login: {e}")
            return None

    @staticmethod
    async def delete(user_id: UUID) -> bool:
        """Delete a user."""
        try:
            client = get_supabase_admin_client()
            response = (
                client.table("users").delete().eq("id", str(user_id)).execute()
            )
            return response.data is not None
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False


class UserTenantRepository:
    """Repository for user-tenant relationship operations."""

    @staticmethod
    async def create(
        user_tenant_create: UserTenantCreate,
    ) -> Optional[UserTenant]:
        """Create a user-tenant relationship."""
        try:
            client = get_supabase_admin_client()
            response = (
                client.table("user_tenants")
                .insert(
                    {
                        "user_id": str(user_tenant_create.user_id),
                        "tenant_id": str(user_tenant_create.tenant_id),
                        "role": user_tenant_create.role.value,
                    }
                )
                .execute()
            )
            if response.data and len(response.data) > 0:
                return UserTenant(**response.data[0])
            return None
        except Exception as e:
            print(f"Error creating user-tenant relationship: {e}")
            return None

    @staticmethod
    async def get_by_user_and_tenant(
        user_id: UUID, tenant_id: UUID
    ) -> Optional[UserTenant]:
        """Get a user-tenant relationship."""
        try:
            client = get_supabase_client()
            response = (
                client.table("user_tenants")
                .select("*")
                .eq("user_id", str(user_id))
                .eq("tenant_id", str(tenant_id))
                .execute()
            )
            if response.data and len(response.data) > 0:
                return UserTenant(**response.data[0])
            return None
        except Exception as e:
            print(f"Error fetching user-tenant relationship: {e}")
            return None

    @staticmethod
    async def get_by_user_id(user_id: UUID) -> List[UserTenant]:
        """Get all tenant memberships for a user."""
        try:
            client = get_supabase_client()
            response = (
                client.table("user_tenants")
                .select("*")
                .eq("user_id", str(user_id))
                .execute()
            )
            return (
                [UserTenant(**row) for row in response.data]
                if response.data
                else []
            )
        except Exception as e:
            print(f"Error fetching user tenants: {e}")
            return []

    @staticmethod
    async def get_by_tenant_id(tenant_id: UUID) -> List[UserTenant]:
        """Get all users in a tenant."""
        try:
            client = get_supabase_client()
            response = (
                client.table("user_tenants")
                .select("*")
                .eq("tenant_id", str(tenant_id))
                .execute()
            )
            return (
                [UserTenant(**row) for row in response.data]
                if response.data
                else []
            )
        except Exception as e:
            print(f"Error fetching tenant users: {e}")
            return []

    @staticmethod
    async def delete(user_id: UUID, tenant_id: UUID) -> bool:
        """Delete a user-tenant relationship."""
        try:
            client = get_supabase_admin_client()
            response = (
                client.table("user_tenants")
                .delete()
                .eq("user_id", str(user_id))
                .eq("tenant_id", str(tenant_id))
                .execute()
            )
            return response.data is not None
        except Exception as e:
            print(f"Error deleting user-tenant relationship: {e}")
            return False
