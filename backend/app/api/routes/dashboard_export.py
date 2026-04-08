"""
Dashboard Export Routes

Export dashboard data in JSON or CSV format.
Supports both platform-wide and tenant-scoped exports.
"""

import csv
import io
import json
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse
from app.core.auth import require_auth, require_role
from app.models.enums import UserRole
from app.services.dashboard_queries import (
    get_overview_stats,
    get_traffic_sources,
    get_geo_distribution,
    get_topic_trends,
    get_funnel_metrics,
    get_user_growth,
    get_search_activity,
    get_popular_queries,
    get_persona_distribution,
    get_pulse_accuracy,
)

router = APIRouter(
    prefix="/dashboard/export",
    tags=["dashboard_export"],
)


def get_scoped_tenant_id(request: Request, user: dict) -> Optional[str]:
    """
    Determine which tenant to scope the export to.

    Rules:
    - Tenant admins can only export their own tenant
    - Platform admins can export any tenant or all (tenant_id=None)

    Args:
        request: FastAPI request
        user: Decoded JWT payload

    Returns:
        Tenant ID to scope to, or None for platform-wide
    """
    # Only platform_admin can export without a tenant scope
    is_platform_admin = user.get("role") == UserRole.PLATFORM_ADMIN.value

    requested_tenant = request.headers.get("X-Tenant-ID")
    if requested_tenant and not is_platform_admin:
        raise HTTPException(
            status_code=403,
            detail="Tenant admins cannot override tenant scope",
        )

    # If tenant_admin, use their own tenant
    if not is_platform_admin:
        return user.get("tenant_id")

    # Platform admin: use requested tenant or None (all)
    return requested_tenant


def json_serializer(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


async def export_overview_csv(
    tenant_id: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
) -> str:
    """Export overview stats as CSV."""
    data = await get_overview_stats(tenant_id=tenant_id, start_date=start_date, end_date=end_date)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Total Users", data.get("total_users", 0)])
    writer.writerow(["Total Searches", data.get("total_searches", 0)])
    writer.writerow(["Active Sessions", data.get("active_sessions", 0)])
    writer.writerow(["Avg Response Time (ms)", data.get("avg_response_time_ms", 0)])
    writer.writerow(["New Users This Period", data.get("new_users_this_period", 0)])
    writer.writerow(["MRR", data.get("mrr", 0)])
    writer.writerow(["Period Start", data.get("period_start", "")])
    writer.writerow(["Period End", data.get("period_end", "")])

    return output.getvalue()


async def export_traffic_csv(
    tenant_id: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
) -> str:
    """Export traffic sources as CSV."""
    data = await get_traffic_sources(tenant_id=tenant_id, start_date=start_date, end_date=end_date)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Source", "Count", "Percentage"])
    for source in data.get("sources", []):
        writer.writerow([source["source"], source["count"], source["percentage"]])

    return output.getvalue()


async def export_geo_csv(
    tenant_id: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
) -> str:
    """Export geo distribution as CSV."""
    data = await get_geo_distribution(tenant_id=tenant_id, start_date=start_date, end_date=end_date)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Country", "City", "Count"])
    for loc in data.get("locations", []):
        writer.writerow([loc["country"], loc["city"], loc["count"]])

    return output.getvalue()


async def export_topics_csv(
    tenant_id: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
) -> str:
    """Export topics as CSV."""
    data = await get_topic_trends(tenant_id=tenant_id, start_date=start_date, end_date=end_date)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Topic", "Count"])
    for topic in data.get("topics", []):
        writer.writerow([topic["topic"], topic["count"]])

    return output.getvalue()


async def export_funnel_csv(
    tenant_id: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
) -> str:
    """Export funnel metrics as CSV."""
    data = await get_funnel_metrics(tenant_id=tenant_id, start_date=start_date, end_date=end_date)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Stage", "Session Count", "Conversion Rate"])
    for stage in data.get("stages", []):
        conversion_rate = stage.get("conversion_rate", "")
        writer.writerow([stage["stage_name"], stage["session_count"], conversion_rate or ""])

    return output.getvalue()


async def export_users_csv(
    tenant_id: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
) -> str:
    """Export user growth as CSV."""
    data = await get_user_growth(tenant_id=tenant_id, start_date=start_date, end_date=end_date)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "New Users", "Cumulative Users"])
    for point in data.get("growth_data", []):
        writer.writerow([point["date"], point["new_users"], point["cumulative_users"]])

    return output.getvalue()


async def export_searches_csv(
    tenant_id: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
) -> str:
    """Export search activity as CSV."""
    data = await get_search_activity(tenant_id=tenant_id, start_date=start_date, end_date=end_date)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Total Searches", "Avg Per User"])
    for point in data.get("activity_data", []):
        avg = point.get("avg_per_user", "")
        writer.writerow([point["date"], point["total_searches"], avg or ""])

    return output.getvalue()


@router.get("/")
async def export_dashboard(
    report_type: str = Query(..., description="Type of report: overview, traffic, geo, topics, funnel, users, searches"),
    format: str = Query("json", description="Export format: json or csv"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    request: Request = None,
    user=Depends(require_auth),
):
    """
    Export dashboard data in JSON or CSV format.

    Query params:
        - report_type: Type of report (overview, traffic, geo, topics, funnel, users, searches)
        - format: Export format (json or csv) - default json
        - start_date: Optional start date
        - end_date: Optional end date
        - X-Tenant-ID header: (platform admins only) Specify tenant to export

    Returns:
        JSON or CSV file with requested data
    """
    # Validate report type
    valid_reports = ["overview", "traffic", "geo", "topics", "funnel", "users", "searches"]
    if report_type not in valid_reports:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid report_type. Must be one of: {', '.join(valid_reports)}",
        )

    # Validate format
    if format not in ["json", "csv"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid format. Must be 'json' or 'csv'",
        )

    # Get tenant scope
    tenant_id = get_scoped_tenant_id(request, user)

    # Export based on type
    if format == "json":
        if report_type == "overview":
            data = await get_overview_stats(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
        elif report_type == "traffic":
            data = await get_traffic_sources(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
        elif report_type == "geo":
            data = await get_geo_distribution(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
        elif report_type == "topics":
            data = await get_topic_trends(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
        elif report_type == "funnel":
            data = await get_funnel_metrics(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
        elif report_type == "users":
            data = await get_user_growth(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
        elif report_type == "searches":
            data = await get_search_activity(tenant_id=tenant_id, start_date=start_date, end_date=end_date)

        return JSONResponse(
            content=json.loads(json.dumps(data, default=json_serializer)),
            media_type="application/json",
        )

    else:  # CSV
        if report_type == "overview":
            csv_data = await export_overview_csv(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
        elif report_type == "traffic":
            csv_data = await export_traffic_csv(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
        elif report_type == "geo":
            csv_data = await export_geo_csv(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
        elif report_type == "topics":
            csv_data = await export_topics_csv(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
        elif report_type == "funnel":
            csv_data = await export_funnel_csv(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
        elif report_type == "users":
            csv_data = await export_users_csv(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
        elif report_type == "searches":
            csv_data = await export_searches_csv(tenant_id=tenant_id, start_date=start_date, end_date=end_date)

        return StreamingResponse(
            iter([csv_data]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=dashboard_{report_type}_{date.today()}.csv"},
        )
