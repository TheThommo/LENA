"""
Entitlements — who gets full access (no plan caps, no content gates).

Owner, internal testers, and BYPASS_USER_IDS / BYPASS_USER_EMAILS on Railway
skip freemium limits. Everyone else sees welcoming upgrade CTAs — never raw errors.
"""

from __future__ import annotations

from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("lena.entitlements")

_email_cache: dict[str, Optional[str]] = {}


async def lookup_user_email(client, user_id: str) -> Optional[str]:
    """Fetch user email by id (cached per process for hot paths)."""
    uid = str(user_id).lower()
    if uid in _email_cache:
        return _email_cache[uid]
    try:
        res = (
            client.table("users")
            .select("email")
            .eq("id", uid)
            .limit(1)
            .execute()
        )
        email = (res.data[0].get("email") if res.data else None) or None
        _email_cache[uid] = email.lower().strip() if email else None
        return _email_cache[uid]
    except Exception:
        logger.warning("email lookup failed for user %s", uid, exc_info=True)
        return None


def is_bypass_email(email: Optional[str]) -> bool:
    """True for owner and explicitly listed bypass emails only."""
    if not email:
        return False
    return email.lower().strip() in settings.bypass_user_email_set


async def user_has_full_access(client, user_id: Optional[str]) -> bool:
    """
    Full access = skip project caps, search quotas, and content guardrails.
    Used for owner (Mark), named QA emails in BYPASS_USER_EMAILS, and bypass UUIDs.
    """
    if not user_id:
        return False
    if settings.is_bypass_user(user_id):
        return True
    email = await lookup_user_email(client, user_id)
    return is_bypass_email(email)


async def resolve_user_access_tier(client, user_id: Optional[str]) -> "AccessTier":
    """
    Resolve paid / free access tier for a registered user.
    Existing $19 Pro (slug pro or researcher) → AccessTier.RESEARCHER (unlimited).
    """
    from app.core.plan_tiers import AccessTier, normalize_plan_slug

    if not user_id:
        return AccessTier.ANONYMOUS
    if await user_has_full_access(client, user_id):
        return AccessTier.ENTERPRISE  # operator bypass ≈ full surface

    try:
        ut = (
            client.table("user_tenants")
            .select("tenant_id")
            .eq("user_id", str(user_id))
            .limit(1)
            .execute()
        )
        if not ut.data:
            return AccessTier.FREE
        tenant_id = ut.data[0]["tenant_id"]
        sub = (
            client.table("tenant_subscriptions")
            .select("status, plan_id, stripe_price_id")
            .eq("tenant_id", tenant_id)
            .in_("status", ["active", "trialing"])
            .limit(1)
            .execute()
        )
        if not sub.data:
            return AccessTier.FREE
        plan_id = sub.data[0].get("plan_id")
        monthly = None
        plan_name = None
        if plan_id:
            plan = (
                client.table("plan_tiers")
                .select("name, display_name, monthly_price_cents")
                .eq("id", plan_id)
                .limit(1)
                .execute()
            )
            if plan.data:
                plan_name = plan.data[0].get("name")
                monthly = plan.data[0].get("monthly_price_cents")
        # Fallback: map known Stripe price env IDs
        if not plan_name:
            price = sub.data[0].get("stripe_price_id")
            researcher_prices = {
                settings.stripe_price_researcher_monthly,
                settings.stripe_price_researcher_annual,
                # Legacy env names still hold the $19 Price IDs until human migrates
                settings.stripe_price_pro_monthly,
                settings.stripe_price_pro_annual,
            }
            pro_prices = {
                settings.stripe_price_pro_49_monthly,
                settings.stripe_price_pro_49_annual,
            }
            if price and price in {p for p in researcher_prices if p}:
                return AccessTier.RESEARCHER
            if price and price in {p for p in pro_prices if p}:
                return AccessTier.PRO
            if price and price == settings.stripe_price_pro_founding:
                return AccessTier.FOUNDING
            return AccessTier.RESEARCHER  # paid unknown → researcher (no loss)
        return normalize_plan_slug(plan_name, monthly_price_cents=monthly)
    except Exception:
        logger.warning("resolve_user_access_tier failed for %s", user_id, exc_info=True)
        return AccessTier.FREE


def project_limit_upgrade_message(active_project_name: Optional[str] = None) -> str:
    """Welcoming commercial copy — never an error tone."""
    if active_project_name:
        return (
            f"You're getting great value from **Projects**! "
            f"The Free plan includes **one active research folder** — "
            f"**{active_project_name}** is yours right now.\n\n"
            "Upgrade to **Researcher** ($19/mo) for unlimited projects and advanced sources, "
            "or archive a folder from the ⋯ menu and create a new one anytime."
        )
    return (
        "You're getting great value from **Projects**! "
        "The Free plan includes **one active research folder**.\n\n"
        "Upgrade to **Researcher** ($19/mo) for unlimited projects and advanced sources, "
        "or archive a folder from the ⋯ menu and create a new one anytime."
    )
