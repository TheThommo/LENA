"""
Billing routes - Stripe Checkout + webhooks + customer portal.

Scaffolded before Stripe keys are in Railway env. All endpoints return
503 with a clear message when settings.stripe_enabled is False, so the
frontend can degrade gracefully to a mailto fallback.

Plans (env-driven, not hardcoded):
- pro_monthly   ($30/mo)   -> STRIPE_PRICE_PRO_MONTHLY
- pro_annual    ($300/yr)  -> STRIPE_PRICE_PRO_ANNUAL
- pro_founding  ($50/yr)   -> STRIPE_PRICE_PRO_FOUNDING  (first 50 only)

Webhook events handled:
- checkout.session.completed          -> write customer/subscription IDs
- customer.subscription.updated       -> sync status + period end
- customer.subscription.deleted       -> mark cancelled
"""

from __future__ import annotations

import logging
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.core.auth import require_auth
from app.core.config import settings
from app.db.supabase import get_supabase_admin_client
from app.db.repositories.user_repo import UserTenantRepository

logger = logging.getLogger("lena.billing")

router = APIRouter(prefix="/billing", tags=["billing"])


PlanKey = Literal["pro_monthly", "pro_annual", "pro_founding"]


class CheckoutRequest(BaseModel):
    plan: PlanKey


class CheckoutResponse(BaseModel):
    url: str
    session_id: str


class PortalResponse(BaseModel):
    url: str


def _require_stripe():
    """Short-circuit if Stripe keys aren't set yet."""
    if not settings.stripe_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured yet. Please contact support.",
        )
    import stripe  # noqa: WPS433 (import inside fn: dep may be absent in dev)
    stripe.api_key = settings.stripe_secret_key
    return stripe


def _resolve_price_id(plan: PlanKey) -> str:
    mapping = {
        "pro_monthly": settings.stripe_price_pro_monthly,
        "pro_annual": settings.stripe_price_pro_annual,
        "pro_founding": settings.stripe_price_pro_founding,
    }
    price_id = mapping.get(plan)
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan '{plan}' is not configured.",
        )
    return price_id


async def _founding_seats_remaining() -> int:
    """Count tenant_subscriptions currently on the founding price.
    Uses admin client so RLS does not hide rows."""
    if not settings.stripe_price_pro_founding:
        return 0
    client = get_supabase_admin_client()
    try:
        resp = (
            client.table("tenant_subscriptions")
            .select("id", count="exact")
            .eq("stripe_price_id", settings.stripe_price_pro_founding)
            .in_("status", ["active", "trialing", "past_due"])
            .execute()
        )
        used = resp.count or 0
    except Exception:
        logger.warning("founding seat count failed", exc_info=True)
        used = 0
    remaining = settings.stripe_founding_max_redemptions - used
    return max(remaining, 0)


async def _resolve_user_tenant(user_id: str) -> Optional[str]:
    """Primary tenant for this user. LENA consumers are mapped 1:1 to a tenant."""
    try:
        memberships = await UserTenantRepository.get_by_user_id(UUID(user_id))
    except Exception:
        memberships = []
    if not memberships:
        return None
    return str(memberships[0].tenant_id)


@router.get("/status")
async def billing_status():
    """Public: is Stripe wired up and which plans are live?"""
    founding_remaining = await _founding_seats_remaining() if settings.stripe_enabled else 0
    return {
        "enabled": settings.stripe_enabled,
        "publishable_key": settings.stripe_publishable_key,
        "plans": {
            "pro_monthly": bool(settings.stripe_price_pro_monthly),
            "pro_annual": bool(settings.stripe_price_pro_annual),
            "pro_founding": bool(settings.stripe_price_pro_founding),
        },
        "founding_remaining": founding_remaining,
        "founding_max": settings.stripe_founding_max_redemptions,
    }


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(body: CheckoutRequest, user=Depends(require_auth)):
    """Create a Stripe Checkout session for the authenticated user's tenant."""
    stripe = _require_stripe()

    user_id = str(user["user_id"])
    user_email = user.get("email")

    # Founding-50 gate: check seat availability before creating checkout.
    if body.plan == "pro_founding":
        remaining = await _founding_seats_remaining()
        if remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Founding 50 seats are fully redeemed.",
            )

    price_id = _resolve_price_id(body.plan)
    tenant_id = await _resolve_user_tenant(user_id)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no tenant. Cannot bill without a tenant.",
        )

    # Reuse an existing Stripe customer for this tenant if we have one so
    # repeat checkouts don't create duplicate customers.
    existing_customer_id: Optional[str] = None
    try:
        client = get_supabase_admin_client()
        sub = (
            client.table("tenant_subscriptions")
            .select("stripe_customer_id")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if sub.data and sub.data[0].get("stripe_customer_id"):
            existing_customer_id = sub.data[0]["stripe_customer_id"]
    except Exception:
        logger.warning("tenant_subscription lookup failed", exc_info=True)

    try:
        session_obj = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=settings.billing_success_url,
            cancel_url=settings.billing_cancel_url,
            customer=existing_customer_id,
            customer_email=user_email if not existing_customer_id else None,
            client_reference_id=user_id,
            subscription_data={
                "metadata": {
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "plan": body.plan,
                },
            },
            metadata={
                "user_id": user_id,
                "tenant_id": tenant_id,
                "plan": body.plan,
            },
            allow_promotion_codes=True,
        )
    except Exception as e:  # stripe.error.StripeError subclasses
        logger.error("Stripe checkout create failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stripe checkout failed: {e}",
        )

    return CheckoutResponse(url=session_obj.url, session_id=session_obj.id)


@router.get("/portal", response_model=PortalResponse)
async def customer_portal(user=Depends(require_auth)):
    """Stripe Customer Portal link so the user can self-serve cancel / change plan."""
    stripe = _require_stripe()

    user_id = str(user["user_id"])
    tenant_id = await _resolve_user_tenant(user_id)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenant.")

    client = get_supabase_admin_client()
    sub = (
        client.table("tenant_subscriptions")
        .select("stripe_customer_id")
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    customer_id = (sub.data[0] if sub.data else {}).get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer on file.")

    try:
        portal = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=settings.billing_success_url,
        )
    except Exception as e:
        logger.error("Stripe portal failed: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Stripe portal failed: {e}")
    return PortalResponse(url=portal.url)


# =====================================================================
# Webhook
# =====================================================================
#
# Stripe POSTs to /api/billing/webhook. We verify via STRIPE_WEBHOOK_SECRET
# and then upsert tenant_subscriptions based on the event type.
#
# Events expected:
#   - checkout.session.completed      first-time purchase
#   - customer.subscription.updated   status/period changes, plan changes
#   - customer.subscription.deleted   cancellations
# =====================================================================


_STRIPE_STATUS_MAP = {
    "trialing": "trial",
    "active": "active",
    "past_due": "past_due",
    "canceled": "cancelled",
    "unpaid": "suspended",
    "incomplete": "suspended",
    "incomplete_expired": "suspended",
    "paused": "suspended",
}


def _map_status(stripe_status: Optional[str]) -> Optional[str]:
    """Convert Stripe's status vocabulary to our subscription_status enum."""
    if not stripe_status:
        return None
    return _STRIPE_STATUS_MAP.get(stripe_status, "suspended")


def _plan_id_from_price(price_id: Optional[str]) -> Optional[str]:
    """Map a Stripe price to the internal plan_tiers row via
    plan_tiers.stripe_monthly_price_id / stripe_annual_price_id.
    Used so tenant_subscriptions.plan_id stays consistent with our schema."""
    if not price_id:
        return None
    client = get_supabase_admin_client()
    try:
        monthly = (
            client.table("plan_tiers")
            .select("id")
            .eq("stripe_monthly_price_id", price_id)
            .limit(1)
            .execute()
        )
        if monthly.data:
            return monthly.data[0]["id"]
        annual = (
            client.table("plan_tiers")
            .select("id")
            .eq("stripe_annual_price_id", price_id)
            .limit(1)
            .execute()
        )
        if annual.data:
            return annual.data[0]["id"]
    except Exception:
        logger.warning("plan_id lookup failed for price %s", price_id, exc_info=True)
    return None


async def _upsert_subscription(
    tenant_id: str,
    *,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    stripe_price_id: Optional[str] = None,
    status: Optional[str] = None,
    current_period_start: Optional[str] = None,
    current_period_end: Optional[str] = None,
    billing_email: Optional[str] = None,
):
    """Upsert tenant_subscriptions row on tenant_id (UNIQUE in schema)."""
    client = get_supabase_admin_client()
    payload = {
        "tenant_id": tenant_id,
        "stripe_customer_id": stripe_customer_id,
        "stripe_subscription_id": stripe_subscription_id,
        "stripe_price_id": stripe_price_id,
        "status": status,
        "current_period_start": current_period_start,
        "current_period_end": current_period_end,
        "billing_email": billing_email,
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    plan_id = _plan_id_from_price(stripe_price_id)
    if plan_id:
        payload["plan_id"] = plan_id

    try:
        client.table("tenant_subscriptions").upsert(payload, on_conflict="tenant_id").execute()
    except Exception:
        logger.error("tenant_subscriptions upsert failed", exc_info=True)


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Stripe calls this endpoint directly. Body signature MUST verify against
    STRIPE_WEBHOOK_SECRET or we reject with 400. Never trust the body
    without verification.
    """
    if not settings.stripe_enabled or not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook not configured.")

    import stripe
    stripe.api_key = settings.stripe_secret_key

    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.stripe_webhook_secret,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload.")
    except stripe.error.SignatureVerificationError:  # type: ignore[attr-defined]
        raise HTTPException(status_code=400, detail="Signature verification failed.")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        tenant_id = (data.get("metadata") or {}).get("tenant_id")
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        email = (data.get("customer_details") or {}).get("email")
        if tenant_id:
            # Pull the subscription to get price + period.
            try:
                sub = stripe.Subscription.retrieve(subscription_id)
                item = sub["items"]["data"][0] if sub.get("items", {}).get("data") else None
                price_id = item["price"]["id"] if item else None
                await _upsert_subscription(
                    tenant_id,
                    stripe_customer_id=customer_id,
                    stripe_subscription_id=subscription_id,
                    stripe_price_id=price_id,
                    status=_map_status(sub.get("status")),
                    current_period_start=_iso(sub.get("current_period_start")),
                    current_period_end=_iso(sub.get("current_period_end")),
                    billing_email=email,
                )
            except Exception:
                logger.error("checkout.session.completed handler failed", exc_info=True)

    elif event_type in ("customer.subscription.updated", "customer.subscription.created"):
        tenant_id = (data.get("metadata") or {}).get("tenant_id")
        if not tenant_id:
            logger.warning("subscription.updated missing tenant_id metadata")
        else:
            item = data["items"]["data"][0] if data.get("items", {}).get("data") else None
            price_id = item["price"]["id"] if item else None
            await _upsert_subscription(
                tenant_id,
                stripe_customer_id=data.get("customer"),
                stripe_subscription_id=data.get("id"),
                stripe_price_id=price_id,
                status=_map_status(data.get("status")),
                current_period_start=_iso(data.get("current_period_start")),
                current_period_end=_iso(data.get("current_period_end")),
            )

    elif event_type == "customer.subscription.deleted":
        tenant_id = (data.get("metadata") or {}).get("tenant_id")
        if tenant_id:
            await _upsert_subscription(tenant_id, status="cancelled")

    else:
        logger.info("Unhandled Stripe event: %s", event_type)

    return {"received": True}


def _iso(ts: Optional[int]) -> Optional[str]:
    """Stripe gives unix seconds; tenant_subscriptions stores timestamptz."""
    if not ts:
        return None
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
