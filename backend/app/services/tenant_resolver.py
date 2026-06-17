"""Resolve tenant_id for authenticated users and analytics writes."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from app.db.supabase import get_supabase_admin_client

logger = logging.getLogger(__name__)

_cached_default_tenant_id: Optional[str] = None


_DEFAULT_TENANT_SLUGS = ("lena", "default")


def get_default_tenant_id() -> Optional[str]:
    """Return the platform default tenant id, cached.

    Registration and session flows create slug ``lena`` on Railway; older
    scripts used ``default``. Try both, then any tenant row as last resort.
    """
    global _cached_default_tenant_id
    if _cached_default_tenant_id:
        return _cached_default_tenant_id
    try:
        client = get_supabase_admin_client()
        for slug in _DEFAULT_TENANT_SLUGS:
            resp = client.table("tenants").select("id").eq("slug", slug).limit(1).execute()
            if resp.data:
                _cached_default_tenant_id = resp.data[0]["id"]
                return _cached_default_tenant_id
        resp = client.table("tenants").select("id").limit(1).execute()
        if resp.data:
            _cached_default_tenant_id = resp.data[0]["id"]
            return _cached_default_tenant_id
    except Exception:
        logger.error("Could not resolve default tenant", exc_info=True)
    return None


async def resolve_tenant_id_for_user(user_id: str) -> Optional[str]:
    """
    Resolve tenant for search logging / billing.

    Order: user_tenants membership → users.tenant_id → default tenant slug.
    Registration sets users.tenant_id but often skips user_tenants, so the
    middle fallback is required for Add to Project to work.
    """
    try:
        from app.db.repositories.user_repo import UserRepository, UserTenantRepository

        memberships = await UserTenantRepository.get_by_user_id(UUID(user_id))
        if memberships:
            return str(memberships[0].tenant_id)

        user = await UserRepository.get_by_id(UUID(user_id))
        if user and user.tenant_id:
            return str(user.tenant_id)
    except Exception:
        logger.warning("tenant resolve via user record failed for %s", user_id, exc_info=True)

    return get_default_tenant_id()
