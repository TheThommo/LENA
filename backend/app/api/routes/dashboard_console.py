"""
HQ Console API routes: permissions, KPI registry, audit log, DB explorer.
"""

import csv
import io
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.core.auth import require_auth, require_role
from app.db.supabase import get_supabase_admin_client
from app.models.enums import UserRole
from app.services.console_permissions import console_nav, map_lena_role
from app.services.db_explorer import get_db_explorer_catalog, mask_row
from app.services.dashboard_queries import (
    _get_date_range,
    get_funnel_metrics,
    get_leads,
    get_overview_stats,
    get_revenue_metrics,
    get_user_growth,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/dashboard/platform/console",
    tags=["dashboard_console"],
    dependencies=[Depends(require_role([UserRole.PLATFORM_ADMIN.value]))],
)

@router.get("/permissions")
async def get_console_permissions(user=Depends(require_auth)):
    """Nav visibility for the signed-in HQ user."""
    lena_role = user.get("role") or UserRole.PUBLIC_USER.value
    console_role = map_lena_role(lena_role)
    return {
        "lena_role": lena_role,
        "console_role": console_role,
        "nav": console_nav(console_role),
    }


@router.get("/kpis")
async def get_kpi_registry(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """Registry-driven KPI cards for Command Center (not hardcoded in UI)."""
    start_date, end_date = _get_date_range(start_date, end_date)

    overview = await get_overview_stats(None, start_date, end_date)
    revenue = await get_revenue_metrics(None)
    funnel = await get_funnel_metrics(None, start_date, end_date)
    leads = await get_leads(None, start_date, end_date)
    growth = await get_user_growth(None, start_date, end_date)

    new_users = growth.get("growth_data", [])
    latest_new = new_users[-1].get("new_users", 0) if new_users else 0

    registry = [
        {
            "id": "mrr",
            "label": "MRR",
            "value": revenue.get("mrr", 0),
            "format": "money_cents",
            "group": "topline",
        },
        {
            "id": "active_subscriptions",
            "label": "Active subscriptions",
            "value": revenue.get("active_subscriptions", 0),
            "format": "integer",
            "group": "topline",
        },
        {
            "id": "total_users",
            "label": "Total users",
            "value": overview.get("total_users", 0),
            "format": "integer",
            "group": "topline",
        },
        {
            "id": "total_searches",
            "label": "Searches (period)",
            "value": overview.get("total_searches", 0),
            "format": "integer",
            "group": "product",
        },
        {
            "id": "active_sessions",
            "label": "Active sessions",
            "value": overview.get("active_sessions", 0),
            "format": "integer",
            "group": "product",
        },
        {
            "id": "new_users_period",
            "label": "New users (period)",
            "value": overview.get("new_users_this_period", 0),
            "format": "integer",
            "group": "growth",
        },
        {
            "id": "new_users_latest_day",
            "label": "New users (latest day)",
            "value": latest_new,
            "format": "integer",
            "group": "growth",
        },
        {
            "id": "total_leads",
            "label": "Leads captured",
            "value": leads.get("total_leads", 0),
            "format": "integer",
            "group": "growth",
        },
        {
            "id": "funnel_registered",
            "label": "Funnel: registered",
            "value": next(
                (s.get("count", 0) for s in funnel.get("stages", []) if s.get("stage") == "registered"),
                0,
            ),
            "format": "integer",
            "group": "funnel",
        },
        {
            "id": "avg_response_ms",
            "label": "Avg response (ms)",
            "value": round(overview.get("avg_response_time_ms", 0)),
            "format": "integer",
            "group": "ops",
        },
    ]

    return {
        "kpis": registry,
        "period_start": start_date,
        "period_end": end_date,
    }


@router.get("/audit-log")
async def list_audit_log(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
):
    """Paginated audit trail for HQ governance view."""
    client = get_supabase_admin_client()
    q = (
        client.table("audit_log")
        .select(
            "id, tenant_id, user_id, action, resource_type, resource_id, "
            "old_values, new_values, ip_address, created_at",
            count="exact",
        )
        .order("created_at", desc=True)
    )
    if action:
        q = q.eq("action", action)
    if resource_type:
        q = q.eq("resource_type", resource_type)

    res = q.range(offset, offset + limit - 1).execute()
    rows = res.data or []

    user_ids = list({r["user_id"] for r in rows if r.get("user_id")})
    users_map: Dict[str, dict] = {}
    if user_ids:
        u = client.table("users").select("id, email, name").in_("id", user_ids).execute()
        users_map = {row["id"]: row for row in (u.data or [])}

    enriched = []
    for row in rows:
        u = users_map.get(row.get("user_id") or "", {})
        enriched.append({
            **row,
            "actor_email": u.get("email"),
            "actor_name": u.get("name"),
        })

    return {"entries": enriched, "total": res.count or len(enriched), "limit": limit, "offset": offset}


@router.get("/db/tables")
async def list_db_tables(refresh: bool = Query(False)):
    """Grouped table list for DB Explorer sidebar (live Supabase discovery)."""
    catalog = await get_db_explorer_catalog(force_refresh=refresh)
    return {
        "groups": catalog["groups"],
        "discovered_count": catalog["discovered_count"],
        "source": catalog["source"],
    }


@router.get("/db/{table_name}")
async def browse_db_table(
    table_name: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    sort: Optional[str] = Query(None),
    order: str = Query("desc"),
    filter_col: Optional[str] = Query(None, alias="filter"),
    filter_val: Optional[str] = Query(None),
):
    """Paginated, sortable table browse via admin client (bypasses RLS)."""
    catalog = await get_db_explorer_catalog()
    if table_name not in catalog["allowed_tables"]:
        raise HTTPException(status_code=404, detail="Table not available in explorer")

    client = get_supabase_admin_client()
    offset = (page - 1) * limit
    sort_col = sort or "created_at"
    ascending = order.lower() == "asc"

    try:
        q = client.table(table_name).select("*", count="exact")
        if filter_col and filter_val is not None and filter_val != "":
            q = q.ilike(filter_col, f"%{filter_val}%")
        q = q.order(sort_col, desc=not ascending)
        res = q.range(offset, offset + limit - 1).execute()
    except Exception as exc:
        logger.warning("DB explorer query failed for %s: %s", table_name, exc)
        try:
            q = client.table(table_name).select("*", count="exact")
            if filter_col and filter_val:
                q = q.ilike(filter_col, f"%{filter_val}%")
            res = q.range(offset, offset + limit - 1).execute()
            sort_col = sort or "id"
        except Exception as inner:
            raise HTTPException(status_code=400, detail=str(inner)) from inner

    rows = [mask_row(r) for r in (res.data or [])]
    columns = list(rows[0].keys()) if rows else []

    return {
        "table": table_name,
        "columns": columns,
        "rows": rows,
        "total": res.count or len(rows),
        "page": page,
        "limit": limit,
        "sort": sort_col,
        "order": order,
    }


@router.get("/db/{table_name}/export")
async def export_db_table_csv(
    table_name: str,
    limit: int = Query(1000, ge=1, le=5000),
    sort: Optional[str] = Query(None),
    order: str = Query("desc"),
):
    """CSV export for the current table slice."""
    catalog = await get_db_explorer_catalog()
    if table_name not in catalog["allowed_tables"]:
        raise HTTPException(status_code=404, detail="Table not available in explorer")

    client = get_supabase_admin_client()
    sort_col = sort or "created_at"
    ascending = order.lower() == "asc"

    try:
        q = client.table(table_name).select("*").order(sort_col, desc=not ascending).limit(limit)
        res = q.execute()
    except Exception:
        q = client.table(table_name).select("*").limit(limit)
        res = q.execute()
        sort_col = sort or "id"
    rows = [mask_row(r) for r in (res.data or [])]

    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    else:
        output.write("")

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{table_name}.csv"'},
    )
