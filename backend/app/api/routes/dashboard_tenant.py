"""
Tenant Dashboard Routes

Endpoints accessible to tenant_admin and platform_admin role users.
Each tenant admin sees only their own tenant's data.
Platform admins can view any tenant's dashboard by providing tenant_id.
"""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.core.auth import require_auth, require_role
from app.core.tenant import detect_tenant
from app.models.enums import UserRole
from app.models.dashboard import (
    DashboardOverview,
    TrafficSourcesResponse,
    GeoDistributionResponse,
    TopicTrendsResponse,
    FunnelMetricsResponse,
    UserGrowthResponse,
    SearchActivityResponse,
    PopularQueriesResponse,
    PersonaDistributionResponse,
    PulseAccuracyResponse,
)
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
    prefix="/dashboard/tenant",
    tags=["dashboard_tenant"],
    dependencies=[Depends(require_role([UserRole.TENANT_ADMIN.value, UserRole.PLATFORM_ADMIN.value]))],
)


def get_scoped_tenant_id(request: Request, user: dict) -> str:
    """
    Determine which tenant to scope the dashboard to.

    Rules:
    - Tenant admins see only their own tenant (from JWT)
    - Platform admins can override via X-Tenant-ID header or default to their tenant

    Args:
        request: FastAPI request
        user: Decoded JWT payload

    Returns:
        Tenant ID to scope dashboard to

    Raises:
        HTTPException: If tenant_admin tries to access another tenant
    """
    requested_tenant = request.headers.get("X-Tenant-ID", user.get("tenant_id"))

    # If user is tenant_admin, enforce their tenant
    if user.get("role") == UserRole.TENANT_ADMIN.value:
        if requested_tenant != user.get("tenant_id"):
            raise HTTPException(
                status_code=403,
                detail="Tenant admins can only view their own tenant's dashboard",
            )

    return requested_tenant


@router.get("/overview", response_model=DashboardOverview)
async def get_tenant_overview(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    request: Request = None,
    user=Depends(require_auth),
):
    """
    Get tenant-specific overview statistics.

    Tenant admins see only their own data.
    Platform admins see data for their assigned tenant (default) or specified tenant via X-Tenant-ID header.

    Query params:
        - start_date: Optional start date (YYYY-MM-DD)
        - end_date: Optional end date (YYYY-MM-DD)
        - X-Tenant-ID header: (platform admins only) Override tenant scope

    Returns overview with users, searches, sessions, etc for this tenant.
    """
    tenant_id = get_scoped_tenant_id(request, user)
    data = await get_overview_stats(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
    return DashboardOverview(**data)


@router.get("/traffic", response_model=TrafficSourcesResponse)
async def get_tenant_traffic(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    request: Request = None,
    user=Depends(require_auth),
):
    """
    Get tenant traffic breakdown by source.

    Returns traffic sources for this tenant only.
    """
    tenant_id = get_scoped_tenant_id(request, user)
    data = await get_traffic_sources(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
    return TrafficSourcesResponse(**data)


@router.get("/geo", response_model=GeoDistributionResponse)
async def get_tenant_geo(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    request: Request = None,
    user=Depends(require_auth),
):
    """
    Get geographic distribution for this tenant's users.

    Returns location breakdown by country and city.
    """
    tenant_id = get_scoped_tenant_id(request, user)
    data = await get_geo_distribution(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
    return GeoDistributionResponse(**data)


@router.get("/topics", response_model=TopicTrendsResponse)
async def get_tenant_topics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    request: Request = None,
    user=Depends(require_auth),
):
    """
    Get trending search topics for this tenant.

    Returns top 20 topics by frequency for this tenant.
    """
    tenant_id = get_scoped_tenant_id(request, user)
    data = await get_topic_trends(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
    return TopicTrendsResponse(**data)


@router.get("/funnel", response_model=FunnelMetricsResponse)
async def get_tenant_funnel(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    request: Request = None,
    user=Depends(require_auth),
):
    """
    Get conversion funnel metrics for this tenant.

    Returns funnel stages with conversion rates for this tenant.
    """
    tenant_id = get_scoped_tenant_id(request, user)
    data = await get_funnel_metrics(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
    return FunnelMetricsResponse(**data)


@router.get("/users", response_model=UserGrowthResponse)
async def get_tenant_users(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    request: Request = None,
    user=Depends(require_auth),
):
    """
    Get user registration growth for this tenant.

    Returns daily new user counts and cumulative totals.
    """
    tenant_id = get_scoped_tenant_id(request, user)
    data = await get_user_growth(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
    return UserGrowthResponse(**data)


@router.get("/searches", response_model=SearchActivityResponse)
async def get_tenant_searches(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    request: Request = None,
    user=Depends(require_auth),
):
    """
    Get search activity trends for this tenant.

    Returns daily search counts and averages per user.
    """
    tenant_id = get_scoped_tenant_id(request, user)
    data = await get_search_activity(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
    return SearchActivityResponse(**data)


@router.get("/queries", response_model=PopularQueriesResponse)
async def get_tenant_queries(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    request: Request = None,
    user=Depends(require_auth),
):
    """
    Get most popular search queries for this tenant.

    Query params:
        - limit: Number of top queries to return (default 20, max 100)

    Returns top queries for this tenant by frequency.
    """
    tenant_id = get_scoped_tenant_id(request, user)
    data = await get_popular_queries(tenant_id=tenant_id, start_date=start_date, end_date=end_date, limit=limit)
    return PopularQueriesResponse(**data)


@router.get("/personas", response_model=PersonaDistributionResponse)
async def get_tenant_personas(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    request: Request = None,
    user=Depends(require_auth),
):
    """
    Get user distribution by persona type for this tenant.

    Returns breakdown of this tenant's users by persona.
    """
    tenant_id = get_scoped_tenant_id(request, user)
    data = await get_persona_distribution(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
    return PersonaDistributionResponse(**data)


@router.get("/pulse-accuracy", response_model=PulseAccuracyResponse)
async def get_tenant_pulse_accuracy(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    request: Request = None,
    user=Depends(require_auth),
):
    """
    Get PULSE validation accuracy metrics for this tenant.

    Returns breakdown of this tenant's search results by validation status.
    """
    tenant_id = get_scoped_tenant_id(request, user)
    data = await get_pulse_accuracy(tenant_id=tenant_id, start_date=start_date, end_date=end_date)
    return PulseAccuracyResponse(**data)
