"""
Admin Subscription Override Routes

Platform-admin-only endpoints for managing tenant subscriptions:
- List all subscriptions with tenant + plan details
- Extend a subscription's current_period_end by N days
- Override a tenant's daily search limit (via override_max_searches_per_day)
- Change a tenant's plan

All writes use the admin Supabase client (bypasses RLS).
"""

from uuid import UUID
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import require_role
from app.models.enums import UserRole
from app.db.supabase import get_supabase_admin_client

router = APIRouter(
    prefix="/dashboard/platform/subscriptions",
    tags=["dashboard_platform_subscriptions"],
    dependencies=[Depends(require_role([UserRole.PLATFORM_ADMIN.value]))],
)


class ExtendRequest(BaseModel):
    days: int = Field(..., ge=1, le=3650, description="Number of days to extend the period")


class OverrideUsageRequest(BaseModel):
    override_max_searches_per_day: Optional[int] = Field(
        None, ge=0, description="Per-tenant daily search cap; null clears the override"
    )


class ChangePlanRequest(BaseModel):
    plan_id: UUID


@router.get("")
async def list_subscriptions():
    """Return all tenant subscriptions with tenant name and plan info."""
    client = get_supabase_admin_client()

    subs_resp = (
        client.table("tenant_subscriptions")
        .select(
            "id, tenant_id, plan_id, status, current_period_start, current_period_end, "
            "trial_ends_at, searches_used_this_month, override_max_searches_per_day, "
            "stripe_customer_id, stripe_subscription_id, billing_email, created_at"
        )
        .order("created_at", desc=True)
        .execute()
    )
    subs = subs_resp.data or []

    # Hydrate tenant names and plan details in a single extra round-trip each
    tenant_ids = list({s["tenant_id"] for s in subs if s.get("tenant_id")})
    plan_ids = list({s["plan_id"] for s in subs if s.get("plan_id")})

    tenants_map = {}
    if tenant_ids:
        t_resp = client.table("tenants").select("id, name, slug").in_("id", tenant_ids).execute()
        tenants_map = {t["id"]: t for t in (t_resp.data or [])}

    plans_map = {}
    if plan_ids:
        p_resp = (
            client.table("plan_tiers")
            .select("id, name, slug, monthly_price_cents, searches_per_day, saved_results_limit")
            .in_("id", plan_ids)
            .execute()
        )
        plans_map = {p["id"]: p for p in (p_resp.data or [])}

    enriched = []
    for s in subs:
        tenant = tenants_map.get(s.get("tenant_id"), {})
        plan = plans_map.get(s.get("plan_id"), {})
        enriched.append({
            **s,
            "tenant_name": tenant.get("name"),
            "tenant_slug": tenant.get("slug"),
            "plan_name": plan.get("name"),
            "plan_slug": plan.get("slug"),
            "plan_monthly_price_cents": plan.get("monthly_price_cents"),
            "plan_searches_per_day": plan.get("searches_per_day"),
        })

    return {"subscriptions": enriched, "total": len(enriched)}


@router.post("/{subscription_id}/extend")
async def extend_subscription(subscription_id: UUID, body: ExtendRequest):
    """Extend current_period_end by N days (preserves everything else)."""
    client = get_supabase_admin_client()

    existing = (
        client.table("tenant_subscriptions").select("current_period_end").eq("id", str(subscription_id)).execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Subscription not found")

    current_end_str = existing.data[0].get("current_period_end")
    base = (
        datetime.fromisoformat(current_end_str.replace("Z", "+00:00"))
        if current_end_str
        else datetime.now(timezone.utc)
    )
    # Never extend from a past date — roll forward from now if the sub had expired
    if base < datetime.now(timezone.utc):
        base = datetime.now(timezone.utc)
    new_end = base + timedelta(days=body.days)

    updated = (
        client.table("tenant_subscriptions")
        .update({"current_period_end": new_end.isoformat(), "status": "active"})
        .eq("id", str(subscription_id))
        .execute()
    )
    if not updated.data:
        raise HTTPException(status_code=500, detail="Failed to extend subscription")

    return {"success": True, "new_current_period_end": new_end.isoformat()}


@router.post("/{subscription_id}/override-usage")
async def override_usage(subscription_id: UUID, body: OverrideUsageRequest):
    """Set or clear the per-tenant daily search cap."""
    client = get_supabase_admin_client()
    updated = (
        client.table("tenant_subscriptions")
        .update({"override_max_searches_per_day": body.override_max_searches_per_day})
        .eq("id", str(subscription_id))
        .execute()
    )
    if not updated.data:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"success": True, "override_max_searches_per_day": body.override_max_searches_per_day}


@router.post("/{subscription_id}/change-plan")
async def change_plan(subscription_id: UUID, body: ChangePlanRequest):
    """Switch a tenant to a different plan tier."""
    client = get_supabase_admin_client()

    plan_check = client.table("plan_tiers").select("id").eq("id", str(body.plan_id)).execute()
    if not plan_check.data:
        raise HTTPException(status_code=400, detail="Plan not found")

    updated = (
        client.table("tenant_subscriptions")
        .update({"plan_id": str(body.plan_id)})
        .eq("id", str(subscription_id))
        .execute()
    )
    if not updated.data:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"success": True, "plan_id": str(body.plan_id)}


@router.get("/plans")
async def list_plans():
    """List available plan tiers for the change-plan dropdown."""
    client = get_supabase_admin_client()
    resp = (
        client.table("plan_tiers")
        .select("id, name, slug, monthly_price_cents, annual_price_cents, searches_per_day")
        .order("monthly_price_cents", desc=False)
        .execute()
    )
    return {"plans": resp.data or []}
