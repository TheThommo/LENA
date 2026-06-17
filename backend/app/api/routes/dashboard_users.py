"""
Platform User Directory Routes

Platform-admin-only endpoints for HQ user management:
- List/search users across tenants
- View user detail
- Update role, persona, active status
- Trigger password reset email
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.auth import require_role
from app.core.config import settings
from app.db.supabase import get_supabase_admin_client
from app.models.enums import PersonaType, UserRole
from app.services.email_service import send_password_reset_email

router = APIRouter(
    prefix="/dashboard/platform/user-directory",
    tags=["dashboard_platform_users"],
    dependencies=[Depends(require_role([UserRole.PLATFORM_ADMIN.value]))],
)


class AdminUserUpdate(BaseModel):
    role: Optional[UserRole] = None
    persona_type: Optional[PersonaType] = None
    is_active: Optional[bool] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)


def _hash_token(raw_token: str) -> str:
    import hashlib
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _hydrate_users(rows: list[dict]) -> list[dict]:
    if not rows:
        return []

    tenant_ids = list({r["tenant_id"] for r in rows if r.get("tenant_id")})
    tenants_map: dict[str, dict] = {}
    if tenant_ids:
        client = get_supabase_admin_client()
        t_resp = (
            client.table("tenants")
            .select("id, name, slug")
            .in_("id", tenant_ids)
            .execute()
        )
        tenants_map = {t["id"]: t for t in (t_resp.data or [])}

    enriched = []
    for row in rows:
        tenant = tenants_map.get(row.get("tenant_id") or "", {})
        enriched.append({
            **row,
            "tenant_name": tenant.get("name"),
            "tenant_slug": tenant.get("slug"),
        })
    return enriched


@router.get("")
async def list_users(
    search: Optional[str] = Query(None, description="Filter by email or name"),
    role: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    active_only: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Paginated user directory for HQ console."""
    client = get_supabase_admin_client()

    q = (
        client.table("users")
        .select(
            "id, email, name, role, persona_type, tenant_id, is_active, "
            "last_login_at, created_at",
            count="exact",
        )
        .order("created_at", desc=True)
    )

    if role:
        q = q.eq("role", role)
    if tenant_id:
        q = q.eq("tenant_id", tenant_id)
    if active_only is True:
        q = q.eq("is_active", True)
    elif active_only is False:
        q = q.eq("is_active", False)

    if search:
        needle = search.strip()
        q = q.or_(f"email.ilike.%{needle}%,name.ilike.%{needle}%")

    res = q.range(offset, offset + limit - 1).execute()
    rows = res.data or []

    return {
        "users": _hydrate_users(rows),
        "total": res.count or len(rows),
        "limit": limit,
        "offset": offset,
    }


@router.get("/{user_id}")
async def get_user(user_id: UUID):
    """Single user detail with tenant context."""
    client = get_supabase_admin_client()
    res = (
        client.table("users")
        .select(
            "id, email, name, role, persona_type, tenant_id, is_active, "
            "last_login_at, created_at, updated_at"
        )
        .eq("id", str(user_id))
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="User not found")

    user = _hydrate_users(res.data)[0]

    memberships = (
        client.table("user_tenants")
        .select("tenant_id, role, joined_at")
        .eq("user_id", str(user_id))
        .execute()
    )
    user["memberships"] = memberships.data or []
    return user


@router.patch("/{user_id}")
async def update_user(user_id: UUID, body: AdminUserUpdate):
    """Update user role, persona, name, or active status."""
    client = get_supabase_admin_client()

    existing = client.table("users").select("id").eq("id", str(user_id)).limit(1).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="User not found")

    update_data: dict = {}
    if body.role is not None:
        update_data["role"] = body.role.value
    if body.persona_type is not None:
        update_data["persona_type"] = body.persona_type.value
    if body.is_active is not None:
        update_data["is_active"] = body.is_active
    if body.name is not None:
        update_data["name"] = body.name

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    updated = (
        client.table("users")
        .update(update_data)
        .eq("id", str(user_id))
        .execute()
    )
    if not updated.data:
        raise HTTPException(status_code=500, detail="Failed to update user")

    return {"success": True, "user": _hydrate_users(updated.data)[0]}


@router.post("/{user_id}/send-reset")
async def send_password_reset(user_id: UUID):
    """Send a password reset email to the user (HQ support action)."""
    client = get_supabase_admin_client()
    res = (
        client.table("users")
        .select("id, email")
        .eq("id", str(user_id))
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="User not found")
    user = res.data[0]

    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    client = get_supabase_admin_client()
    client.table("users").update({
        "reset_token_hash": token_hash,
        "reset_token_expires_at": expires_at.isoformat(),
    }).eq("id", str(user_id)).execute()

    reset_url = f"{settings.app_url}/reset-password?token={raw_token}"
    sent = await send_password_reset_email(user["email"], reset_url)
    if not sent:
        raise HTTPException(status_code=500, detail="Failed to send reset email")

    return {"success": True, "message": f"Reset email sent to {user['email']}"}
