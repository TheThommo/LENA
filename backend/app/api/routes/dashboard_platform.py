"""
Platform Dashboard Routes

Endpoints accessible only to platform_admin role users.
Provides view across all tenants in the system.
All endpoints return aggregated metrics and charts.
"""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.auth import require_auth, require_role
from app.models.enums import UserRole
from app.models.dashboard import (
    DashboardOverview,
    TrafficSourcesResponse,
    GeoDistributionResponse,
    TopicTrendsResponse,
    FunnelMetricsResponse,
    UserGrowthResponse,
    SearchActivityResponse,
    RevenueMetricsResponse,
    TenantComparisonResponse,
    PopularQueriesResponse,
    PersonaDistributionResponse,
    PulseAccuracyResponse,
    LeadsResponse,
)
from app.services.dashboard_queries import (
    get_overview_stats,
    get_traffic_sources,
    get_geo_distribution,
    get_topic_trends,
    get_funnel_metrics,
    get_user_growth,
    get_search_activity,
    get_revenue_metrics,
    get_tenant_comparison,
    get_popular_queries,
    get_persona_distribution,
    get_pulse_accuracy,
    get_leads,
)

router = APIRouter(
    prefix="/dashboard/platform",
    tags=["dashboard_platform"],
    dependencies=[Depends(require_role([UserRole.PLATFORM_ADMIN.value]))],
)


@router.get("/overview", response_model=DashboardOverview)
async def get_platform_overview(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user=Depends(require_auth),
):
    """
    Get platform-wide overview statistics.

    Query params:
        - start_date: Optional start date (YYYY-MM-DD)
        - end_date: Optional end date (YYYY-MM-DD)

    Returns overview with total users, searches, active sessions, and more.
    """
    data = await get_overview_stats(tenant_id=None, start_date=start_date, end_date=end_date)
    return DashboardOverview(**data)


@router.get("/traffic", response_model=TrafficSourcesResponse)
async def get_platform_traffic(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user=Depends(require_auth),
):
    """
    Get platform traffic breakdown by source (UTM and referrer).

    Returns traffic sources sorted by count.
    """
    data = await get_traffic_sources(tenant_id=None, start_date=start_date, end_date=end_date)
    return TrafficSourcesResponse(**data)


@router.get("/geo", response_model=GeoDistributionResponse)
async def get_platform_geo(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user=Depends(require_auth),
):
    """
    Get geographic distribution of users across the platform.

    Returns breakdown by country and city.
    """
    data = await get_geo_distribution(tenant_id=None, start_date=start_date, end_date=end_date)
    return GeoDistributionResponse(**data)


@router.get("/topics", response_model=TopicTrendsResponse)
async def get_platform_topics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user=Depends(require_auth),
):
    """
    Get trending search topics across the platform.

    Returns top 20 topics by frequency.
    """
    data = await get_topic_trends(tenant_id=None, start_date=start_date, end_date=end_date)
    return TopicTrendsResponse(**data)


@router.get("/funnel", response_model=FunnelMetricsResponse)
async def get_platform_funnel(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user=Depends(require_auth),
):
    """
    Get platform-wide conversion funnel metrics.

    Returns funnel stages with conversion rates.
    """
    data = await get_funnel_metrics(tenant_id=None, start_date=start_date, end_date=end_date)
    return FunnelMetricsResponse(**data)


@router.get("/users", response_model=UserGrowthResponse)
async def get_platform_users(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user=Depends(require_auth),
):
    """
    Get user registration growth over the platform.

    Returns daily growth data.
    """
    data = await get_user_growth(tenant_id=None, start_date=start_date, end_date=end_date)
    return UserGrowthResponse(**data)


@router.get("/searches", response_model=SearchActivityResponse)
async def get_platform_searches(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user=Depends(require_auth),
):
    """
    Get search activity trends across the platform.

    Returns daily search counts and averages per user.
    """
    data = await get_search_activity(tenant_id=None, start_date=start_date, end_date=end_date)
    return SearchActivityResponse(**data)


@router.get("/revenue", response_model=RevenueMetricsResponse)
async def get_platform_revenue(
    user=Depends(require_auth),
):
    """
    Get platform revenue metrics.

    Returns MRR, active subscriptions, and plan distribution.
    This endpoint does not support date range filtering (shows current snapshot).
    """
    data = await get_revenue_metrics(tenant_id=None)
    return RevenueMetricsResponse(
        **data,
        period_start=date.today(),
        period_end=date.today(),
    )


@router.get("/tenants", response_model=TenantComparisonResponse)
async def get_platform_tenants(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user=Depends(require_auth),
):
    """
    Get per-tenant comparison view (platform admins only).

    Returns summary statistics for each tenant.
    """
    data = await get_tenant_comparison(start_date=start_date, end_date=end_date)
    return TenantComparisonResponse(**data)


@router.get("/queries", response_model=PopularQueriesResponse)
async def get_platform_queries(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(require_auth),
):
    """
    Get most popular search queries across the platform.

    Query params:
        - limit: Number of top queries to return (default 20, max 100)

    Returns top queries by frequency.
    """
    data = await get_popular_queries(tenant_id=None, start_date=start_date, end_date=end_date, limit=limit)
    return PopularQueriesResponse(**data)


@router.get("/personas", response_model=PersonaDistributionResponse)
async def get_platform_personas(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user=Depends(require_auth),
):
    """
    Get user distribution by persona type across the platform.

    Returns breakdown of users by persona (patient, clinician, researcher, etc).
    """
    data = await get_persona_distribution(tenant_id=None, start_date=start_date, end_date=end_date)
    return PersonaDistributionResponse(**data)


@router.get("/pulse-accuracy", response_model=PulseAccuracyResponse)
async def get_platform_pulse_accuracy(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user=Depends(require_auth),
):
    """
    Get PULSE validation accuracy metrics across the platform.

    Returns breakdown of results by validation status.
    """
    data = await get_pulse_accuracy(tenant_id=None, start_date=start_date, end_date=end_date)
    return PulseAccuracyResponse(**data)


@router.get("/leads", response_model=LeadsResponse)
async def get_platform_leads(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user=Depends(require_auth),
):
    """
    Get email leads with corporate vs generic classification.

    Returns sessions where email was captured, with domain intelligence.
    """
    data = await get_leads(tenant_id=None, start_date=start_date, end_date=end_date)
    return LeadsResponse(**data)
