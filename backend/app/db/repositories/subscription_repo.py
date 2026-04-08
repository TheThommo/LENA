"""
Subscription Repository

CRUD operations for subscription plans and tenant subscriptions.
Tracks billing and feature access.
"""

from uuid import UUID
from typing import Optional, List
from app.db.supabase import get_supabase_client, get_supabase_admin_client
from app.models import (
    Plan,
    PlanCreate,
    PlanUpdate,
    Subscription,
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionWithPlan,
)


class PlanRepository:
    """Repository for subscription plan operations."""

    @staticmethod
    async def create(plan_create: PlanCreate) -> Optional[Plan]:
        """Create a new plan."""
        try:
            client = get_supabase_admin_client()
            response = (
                client.table("plans")
                .insert(
                    {
                        "name": plan_create.name,
                        "slug": plan_create.slug.value,
                        "price_monthly": plan_create.price_monthly,
                        "search_limit_monthly": plan_create.search_limit_monthly,
                        "features": plan_create.features,
                        "is_active": plan_create.is_active,
                    }
                )
                .execute()
            )
            if response.data and len(response.data) > 0:
                return Plan(**response.data[0])
            return None
        except Exception as e:
            print(f"Error creating plan: {e}")
            return None

    @staticmethod
    async def get_by_id(plan_id: UUID) -> Optional[Plan]:
        """Get a plan by ID."""
        try:
            client = get_supabase_client()
            response = (
                client.table("plans").select("*").eq("id", str(plan_id)).execute()
            )
            if response.data and len(response.data) > 0:
                return Plan(**response.data[0])
            return None
        except Exception as e:
            print(f"Error fetching plan: {e}")
            return None

    @staticmethod
    async def get_by_slug(slug: str) -> Optional[Plan]:
        """Get a plan by slug."""
        try:
            client = get_supabase_client()
            response = (
                client.table("plans").select("*").eq("slug", slug).execute()
            )
            if response.data and len(response.data) > 0:
                return Plan(**response.data[0])
            return None
        except Exception as e:
            print(f"Error fetching plan by slug: {e}")
            return None

    @staticmethod
    async def list_active() -> List[Plan]:
        """List all active plans."""
        try:
            client = get_supabase_client()
            response = (
                client.table("plans")
                .select("*")
                .eq("is_active", True)
                .order("price_monthly", asc=True)
                .execute()
            )
            return [Plan(**row) for row in response.data] if response.data else []
        except Exception as e:
            print(f"Error listing active plans: {e}")
            return []

    @staticmethod
    async def list_all() -> List[Plan]:
        """List all plans."""
        try:
            client = get_supabase_admin_client()
            response = (
                client.table("plans")
                .select("*")
                .order("price_monthly", asc=True)
                .execute()
            )
            return [Plan(**row) for row in response.data] if response.data else []
        except Exception as e:
            print(f"Error listing plans: {e}")
            return []

    @staticmethod
    async def update(plan_id: UUID, plan_update: PlanUpdate) -> Optional[Plan]:
        """Update a plan."""
        try:
            client = get_supabase_admin_client()
            update_data = plan_update.model_dump(exclude_unset=True)
            if "slug" in update_data and update_data["slug"] is not None:
                update_data["slug"] = update_data["slug"].value
            response = (
                client.table("plans")
                .update(update_data)
                .eq("id", str(plan_id))
                .execute()
            )
            if response.data and len(response.data) > 0:
                return Plan(**response.data[0])
            return None
        except Exception as e:
            print(f"Error updating plan: {e}")
            return None


class SubscriptionRepository:
    """Repository for subscription operations."""

    @staticmethod
    async def create(
        subscription_create: SubscriptionCreate,
    ) -> Optional[Subscription]:
        """Create a new subscription."""
        try:
            client = get_supabase_admin_client()
            response = (
                client.table("subscriptions")
                .insert(
                    {
                        "tenant_id": str(subscription_create.tenant_id),
                        "plan_id": str(subscription_create.plan_id),
                        "status": subscription_create.status.value,
                        "current_period_start": subscription_create.current_period_start.isoformat(),
                        "current_period_end": subscription_create.current_period_end.isoformat(),
                    }
                )
                .execute()
            )
            if response.data and len(response.data) > 0:
                return Subscription(**response.data[0])
            return None
        except Exception as e:
            print(f"Error creating subscription: {e}")
            return None

    @staticmethod
    async def get_by_id(subscription_id: UUID) -> Optional[Subscription]:
        """Get a subscription by ID."""
        try:
            client = get_supabase_client()
            response = (
                client.table("subscriptions")
                .select("*")
                .eq("id", str(subscription_id))
                .execute()
            )
            if response.data and len(response.data) > 0:
                return Subscription(**response.data[0])
            return None
        except Exception as e:
            print(f"Error fetching subscription: {e}")
            return None

    @staticmethod
    async def get_by_tenant_id(tenant_id: UUID) -> Optional[Subscription]:
        """Get the active subscription for a tenant."""
        try:
            client = get_supabase_client()
            response = (
                client.table("subscriptions")
                .select("*")
                .eq("tenant_id", str(tenant_id))
                .eq("status", "active")
                .execute()
            )
            if response.data and len(response.data) > 0:
                return Subscription(**response.data[0])
            return None
        except Exception as e:
            print(f"Error fetching tenant subscription: {e}")
            return None

    @staticmethod
    async def get_with_plan(subscription_id: UUID) -> Optional[SubscriptionWithPlan]:
        """Get a subscription with its plan details."""
        try:
            sub = await SubscriptionRepository.get_by_id(subscription_id)
            if not sub:
                return None

            plan = await PlanRepository.get_by_id(sub.plan_id)
            if not plan:
                return None

            return SubscriptionWithPlan(**sub.model_dump(), plan=plan)
        except Exception as e:
            print(f"Error fetching subscription with plan: {e}")
            return None

    @staticmethod
    async def update(
        subscription_id: UUID, subscription_update: SubscriptionUpdate
    ) -> Optional[Subscription]:
        """Update a subscription."""
        try:
            client = get_supabase_admin_client()
            update_data = {}
            if subscription_update.status is not None:
                update_data["status"] = subscription_update.status.value
            if subscription_update.current_period_start is not None:
                update_data["current_period_start"] = (
                    subscription_update.current_period_start.isoformat()
                )
            if subscription_update.current_period_end is not None:
                update_data["current_period_end"] = (
                    subscription_update.current_period_end.isoformat()
                )
            if subscription_update.plan_id is not None:
                update_data["plan_id"] = str(subscription_update.plan_id)

            response = (
                client.table("subscriptions")
                .update(update_data)
                .eq("id", str(subscription_id))
                .execute()
            )
            if response.data and len(response.data) > 0:
                return Subscription(**response.data[0])
            return None
        except Exception as e:
            print(f"Error updating subscription: {e}")
            return None

    @staticmethod
    async def list_by_status(status: str, limit: int = 100) -> List[Subscription]:
        """List subscriptions by status."""
        try:
            client = get_supabase_admin_client()
            response = (
                client.table("subscriptions")
                .select("*")
                .eq("status", status)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return (
                [Subscription(**row) for row in response.data]
                if response.data
                else []
            )
        except Exception as e:
            print(f"Error listing subscriptions by status: {e}")
            return []
