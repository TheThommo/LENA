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
    """True for owner, configured bypass emails, and named internal testers."""
    if not email:
        return False
    el = email.lower().strip()
    if el == settings.admin_email.lower().strip():
        return True
    if el in settings.bypass_user_email_set:
        return True
    local = el.split("@", 1)[0]
    if local in settings.internal_tester_local_names_set:
        return True
    return False


async def user_has_full_access(client, user_id: Optional[str]) -> bool:
    """
    Full access = skip project caps, search quotas, and content guardrails.
    Used for owner (Mark), Lauren QA, and Railway-configured bypass UUIDs.
    """
    if not user_id:
        return False
    if settings.is_bypass_user(user_id):
        return True
    email = await lookup_user_email(client, user_id)
    return is_bypass_email(email)


def project_limit_upgrade_message(active_project_name: Optional[str] = None) -> str:
    """Welcoming commercial copy — never an error tone."""
    if active_project_name:
        return (
            f"You're getting great value from **Projects**! "
            f"The Free plan includes **one active research folder** — "
            f"**{active_project_name}** is yours right now.\n\n"
            "Upgrade to **Pro** for unlimited projects, or archive a folder "
            "from the ⋯ menu and create a new one anytime."
        )
    return (
        "You're getting great value from **Projects**! "
        "The Free plan includes **one active research folder**.\n\n"
        "Upgrade to **Pro** for unlimited projects, or archive a folder "
        "from the ⋯ menu and create a new one anytime."
    )
