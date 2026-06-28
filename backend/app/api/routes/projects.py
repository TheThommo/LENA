"""
Projects — user-owned research folders that group related search threads.

One project groups many searches (1:N). v1 is single-owner, single-tenant,
no sharing. Free tier is capped at 1 active (non-archived) project; Pro is
unlimited. The cap is enforced here so downstream code can trust the invariant.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.auth import require_auth
from app.core.entitlements import (
    project_limit_upgrade_message,
    user_has_full_access,
)
from app.core.logging import get_logger
from app.db.supabase import get_supabase_admin_client

logger = get_logger("lena.projects")
router = APIRouter(prefix="/projects", tags=["projects"])


FREE_TIER_PROJECT_LIMIT = 1


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=2000)
    color: Optional[str] = Field(None, max_length=20)
    emoji: Optional[str] = Field(None, max_length=16)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=2000)
    color: Optional[str] = Field(None, max_length=20)
    emoji: Optional[str] = Field(None, max_length=16)
    archived: Optional[bool] = None


class ProjectOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    color: Optional[str]
    emoji: Optional[str]
    archived_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    search_count: int = 0


class ProjectLimitsOut(BaseModel):
    plan: str  # "free" | "pro"
    max_active: Optional[int]  # None = unlimited
    active_count: int
    can_create: bool


async def _user_plan_is_free(client, user_id: str) -> bool:
    """
    Quick check: is this user on the Free tier? We consult their tenant's
    active subscription; absence of a paid sub == treat as Free. Done as
    a helper so the logic lives in one place when Stripe lands.
    """
    try:
        # Which tenant is this user a member of?
        mem = (
            client.table("user_tenants")
            .select("tenant_id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not mem.data:
            return True
        tenant_id = mem.data[0]["tenant_id"]
        sub = (
            client.table("tenant_subscriptions")
            .select("plan_id, status")
            .eq("tenant_id", tenant_id)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        if not sub.data:
            return True
        plan_id = sub.data[0].get("plan_id")
        if not plan_id:
            return True
        plan = (
            client.table("plan_tiers").select("name").eq("id", plan_id).limit(1).execute()
        )
        if not plan.data:
            return True
        plan_name = (plan.data[0].get("name") or "").lower()
        return plan_name in ("free", "")
    except Exception:
        logger.warning("Could not determine plan tier; defaulting to Free", exc_info=True)
        return True


async def _count_active_projects(client, user_id: str) -> int:
    """Active = not archived. Cap is on active projects only."""
    res = (
        client.table("projects")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .is_("archived_at", "null")
        .execute()
    )
    return res.count or 0


def _enrich(row: dict, search_count: int) -> ProjectOut:
    return ProjectOut(
        id=row["id"],
        name=row["name"],
        description=row.get("description"),
        color=row.get("color"),
        emoji=row.get("emoji"),
        archived_at=row.get("archived_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        search_count=search_count,
    )


@router.get("", response_model=List[ProjectOut])
async def list_projects(user=Depends(require_auth)):
    """List the caller's projects, newest first."""
    client = get_supabase_admin_client()
    user_id = user["user_id"]

    res = (
        client.table("projects")
        .select("*")
        .eq("user_id", user_id)
        .order("archived_at", desc=False, nullsfirst=False)  # active first
        .order("created_at", desc=True)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return []

    # Bulk search_count per project (one extra query; fine for small N)
    proj_ids = [r["id"] for r in rows]
    counts: dict[str, int] = {pid: 0 for pid in proj_ids}
    cnt = (
        client.table("searches")
        .select("project_id", count="exact")
        .in_("project_id", proj_ids)
        .execute()
    )
    # Supabase PostgREST returns all matching rows with count; we still have
    # to bucket manually because there's no group-by in the client.
    for row in cnt.data or []:
        pid = row.get("project_id")
        if pid in counts:
            counts[pid] += 1

    return [_enrich(r, counts.get(r["id"], 0)) for r in rows]


async def _first_active_project_name(client, user_id: str) -> Optional[str]:
    res = (
        client.table("projects")
        .select("name")
        .eq("user_id", user_id)
        .is_("archived_at", "null")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if res.data:
        return res.data[0].get("name")
    return None


async def _project_limits_for_user(client, user_id: str) -> ProjectLimitsOut:
    active = await _count_active_projects(client, user_id)
    is_free = await _user_plan_is_free(client, user_id)
    full_access = await user_has_full_access(client, user_id)

    if full_access or not is_free:
        return ProjectLimitsOut(
            plan="pro" if not is_free else "free",
            max_active=None,
            active_count=active,
            can_create=True,
        )

    return ProjectLimitsOut(
        plan="free",
        max_active=FREE_TIER_PROJECT_LIMIT,
        active_count=active,
        can_create=active < FREE_TIER_PROJECT_LIMIT,
    )


@router.get("/limits", response_model=ProjectLimitsOut)
async def project_limits(user=Depends(require_auth)):
    """Return project quota for the caller's plan (Free = 1 active project)."""
    client = get_supabase_admin_client()
    return await _project_limits_for_user(client, user["user_id"])


@router.post("")
async def create_project(body: ProjectCreate, user=Depends(require_auth)):
    """Create a new project. Free tier capped at FREE_TIER_PROJECT_LIMIT active projects."""
    client = get_supabase_admin_client()
    user_id = user["user_id"]
    tenant_id = user["tenant_id"]

    full_access = await user_has_full_access(client, user_id)
    if not full_access and await _user_plan_is_free(client, user_id):
        active = await _count_active_projects(client, user_id)
        if active >= FREE_TIER_PROJECT_LIMIT:
            active_name = await _first_active_project_name(client, user_id)
            return JSONResponse(
                status_code=200,
                content={
                    "upgrade_required": True,
                    "feature": "projects",
                    "message": project_limit_upgrade_message(active_name),
                    "active_project_name": active_name,
                },
            )

    payload = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "name": body.name.strip(),
        "description": (body.description or "").strip() or None,
        "color": body.color,
        "emoji": body.emoji,
    }
    res = client.table("projects").insert(payload).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create project")
    return JSONResponse(status_code=201, content=_enrich(res.data[0], 0).model_dump(mode="json"))


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(project_id: UUID, body: ProjectUpdate, user=Depends(require_auth)):
    """Rename / edit / archive / unarchive a project."""
    client = get_supabase_admin_client()
    user_id = user["user_id"]

    # Ownership check first so we don't leak existence
    existing = (
        client.table("projects")
        .select("*")
        .eq("id", str(project_id))
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Project not found")

    update: dict = {}
    if body.name is not None:
        update["name"] = body.name.strip()
    if body.description is not None:
        update["description"] = body.description.strip() or None
    if body.color is not None:
        update["color"] = body.color
    if body.emoji is not None:
        update["emoji"] = body.emoji
    if body.archived is not None:
        update["archived_at"] = datetime.utcnow().isoformat() if body.archived else None

    if not update:
        # No-op — just return the current row.
        row = existing.data[0]
    else:
        # Unarchive-and-over-limit check
        if body.archived is False:
            full_access = await user_has_full_access(client, user_id)
            if not full_access and await _user_plan_is_free(client, user_id):
                active = await _count_active_projects(client, user_id)
                if active >= FREE_TIER_PROJECT_LIMIT:
                    active_name = await _first_active_project_name(client, user_id)
                    return JSONResponse(
                        status_code=200,
                        content={
                            "upgrade_required": True,
                            "feature": "projects",
                            "message": project_limit_upgrade_message(active_name),
                            "active_project_name": active_name,
                        },
                    )
        res = (
            client.table("projects")
            .update(update)
            .eq("id", str(project_id))
            .eq("user_id", user_id)
            .execute()
        )
        row = (res.data or existing.data)[0]

    # Pull live search count
    cnt = (
        client.table("searches")
        .select("id", count="exact")
        .eq("project_id", str(project_id))
        .execute()
    )
    return _enrich(row, cnt.count or 0)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: UUID, user=Depends(require_auth)):
    """Delete a project. Searches keep their rows (project_id set to NULL via FK)."""
    client = get_supabase_admin_client()
    user_id = user["user_id"]

    existing = (
        client.table("projects")
        .select("id")
        .eq("id", str(project_id))
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Project not found")

    client.table("projects").delete().eq("id", str(project_id)).eq("user_id", user_id).execute()
    return None


@router.get("/{project_id}/searches")
async def list_project_searches(
    project_id: UUID,
    limit: int = 100,
    user=Depends(require_auth),
):
    """Return every search filed under the given project, newest first."""
    client = get_supabase_admin_client()
    user_id = user["user_id"]

    # Ownership
    owned = (
        client.table("projects")
        .select("id")
        .eq("id", str(project_id))
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not owned.data:
        raise HTTPException(status_code=404, detail="Project not found")

    # Pull from search_logs (text query + richer metadata) rather than
    # searches (rollup), so the project view matches the "Every Question"
    # feel of the admin panel.
    res = (
        client.table("search_logs")
        .select(
            "id, query, persona, response_time_ms, total_results, pulse_status, "
            "sources_queried, sources_succeeded, session_id, created_at"
        )
        .eq("user_id", user_id)
        .eq("project_id", str(project_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return {"project_id": str(project_id), "searches": res.data or []}


class AssignSearchBody(BaseModel):
    project_id: Optional[UUID] = None  # null == move to unfiled


@router.post("/searches/{search_id}/assign")
async def assign_search_to_project(
    search_id: UUID,
    body: AssignSearchBody,
    user=Depends(require_auth),
):
    """
    Move an existing search into (or out of) a project. Passing null
    unfiles it. Enforces ownership on both the search and the project.
    """
    client = get_supabase_admin_client()
    user_id = user["user_id"]
    sid = str(search_id)

    # Ownership: row must exist and belong to caller (or be unowned legacy row).
    log_row = (
        client.table("search_logs")
        .select("id, user_id")
        .eq("id", sid)
        .limit(1)
        .execute()
    )
    search_row = (
        client.table("searches")
        .select("id, user_id")
        .eq("id", sid)
        .limit(1)
        .execute()
    )

    owner_from_logs = (log_row.data or [None])[0]
    owner_from_searches = (search_row.data or [None])[0]

    if not owner_from_logs and not owner_from_searches:
        raise HTTPException(status_code=404, detail="Search not found")

    for row in (owner_from_logs, owner_from_searches):
        if not row:
            continue
        row_user = row.get("user_id")
        if row_user and row_user != user_id:
            raise HTTPException(status_code=404, detail="Search not found")

    # Backfill user_id on legacy rows that were logged before migration 008.
    if owner_from_logs and not owner_from_logs.get("user_id"):
        client.table("search_logs").update({"user_id": user_id}).eq("id", sid).execute()
    if owner_from_searches and not owner_from_searches.get("user_id"):
        client.table("searches").update({"user_id": user_id}).eq("id", sid).execute()

    # Ownership on the target project (if any)
    target_id: Optional[str] = None
    if body.project_id is not None:
        pr = (
            client.table("projects")
            .select("id")
            .eq("id", str(body.project_id))
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not pr.data:
            raise HTTPException(status_code=404, detail="Project not found")
        target_id = str(body.project_id)

    # Write to both tables so admin counts and project view stay in sync.
    client.table("search_logs").update({"project_id": target_id}).eq("id", sid).execute()
    client.table("searches").update({"project_id": target_id}).eq("id", sid).execute()
    return {"ok": True, "search_id": sid, "project_id": target_id}
