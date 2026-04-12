"""
Dashboard Response Models

Pydantic models for all BI dashboard endpoints.
Handles both platform-wide and tenant-scoped aggregations.
"""

from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, Field


class TimeSeriesPoint(BaseModel):
    """Generic time series data point for charts."""
    date: date
    value: int = Field(..., ge=0)


class TimeSeriesFloat(BaseModel):
    """Time series with floating point values (e.g., averages)."""
    date: date
    value: float = Field(..., ge=0)


class TrafficSource(BaseModel):
    """Breakdown of traffic by referrer or UTM source."""
    source: str
    count: int = Field(..., ge=0)
    percentage: float = Field(..., ge=0, le=100)


class GeoLocation(BaseModel):
    """Geographic location with visitor count."""
    country: Optional[str] = None
    city: Optional[str] = None
    count: int = Field(..., ge=0)


class TopicTrend(BaseModel):
    """Trending search topics over time."""
    topic: str
    count: int = Field(..., ge=0)


class FunnelStage(BaseModel):
    """Single funnel stage metrics."""
    stage_name: str
    session_count: int = Field(..., ge=0)
    conversion_rate: Optional[float] = Field(None, ge=0, le=100)


class UserGrowthPoint(BaseModel):
    """User registration growth data point."""
    date: date
    new_users: int = Field(..., ge=0)
    cumulative_users: int = Field(..., ge=0)


class SearchActivityPoint(BaseModel):
    """Search activity metrics over time."""
    date: date
    total_searches: int = Field(..., ge=0)
    avg_per_user: Optional[float] = Field(None, ge=0)


class PersonaBreakdown(BaseModel):
    """User breakdown by persona type."""
    persona: str
    count: int = Field(..., ge=0)
    percentage: float = Field(..., ge=0, le=100)


class PulseAccuracyMetric(BaseModel):
    """PULSE validation accuracy metrics."""
    status: str  # validated, edge_case, insufficient_validation
    count: int = Field(..., ge=0)
    percentage: float = Field(..., ge=0, le=100)


class PlanDistribution(BaseModel):
    """Subscription plan distribution."""
    plan_name: str
    count: int = Field(..., ge=0)
    mrr: float = Field(..., ge=0)
    percentage: float = Field(..., ge=0, le=100)


class DashboardOverview(BaseModel):
    """Top-level summary statistics for dashboard."""
    total_users: int = Field(..., ge=0)
    total_searches: int = Field(..., ge=0)
    active_sessions: int = Field(..., ge=0)
    avg_response_time_ms: float = Field(..., ge=0)
    new_users_this_period: int = Field(..., ge=0)
    mrr: Optional[float] = Field(None, ge=0)
    period_start: date
    period_end: date


class TrafficSourcesResponse(BaseModel):
    """Aggregated traffic source metrics."""
    total_sessions: int = Field(..., ge=0)
    sources: List[TrafficSource]
    period_start: date
    period_end: date


class GeoDistributionResponse(BaseModel):
    """Geographic distribution of visitors."""
    total_locations: int = Field(..., ge=0)
    locations: List[GeoLocation]
    period_start: date
    period_end: date


class TopicTrendsResponse(BaseModel):
    """Top trending search topics."""
    total_unique_topics: int = Field(..., ge=0)
    topics: List[TopicTrend]
    period_start: date
    period_end: date


class FunnelMetricsResponse(BaseModel):
    """Conversion funnel metrics."""
    stages: List[FunnelStage]
    overall_conversion_rate: float = Field(..., ge=0, le=100)
    period_start: date
    period_end: date


class UserGrowthResponse(BaseModel):
    """User registration growth over time."""
    total_users: int = Field(..., ge=0)
    growth_data: List[UserGrowthPoint]
    period_start: date
    period_end: date


class SearchActivityResponse(BaseModel):
    """Search activity trends over time."""
    total_searches: int = Field(..., ge=0)
    avg_searches_per_user: float = Field(..., ge=0)
    activity_data: List[SearchActivityPoint]
    period_start: date
    period_end: date


class RevenueMetricsResponse(BaseModel):
    """Revenue and subscription metrics."""
    mrr: float = Field(..., ge=0)
    active_subscriptions: int = Field(..., ge=0)
    cancelled_last_period: int = Field(..., ge=0)
    plan_distribution: List[PlanDistribution]
    period_start: date
    period_end: date


class PopularQuery(BaseModel):
    """Most frequently searched queries."""
    query: str
    count: int = Field(..., ge=0)
    avg_response_time_ms: Optional[float] = Field(None, ge=0)


class PopularQueriesResponse(BaseModel):
    """Top searches in the platform or tenant."""
    total_searches: int = Field(..., ge=0)
    queries: List[PopularQuery]
    period_start: date
    period_end: date


class PersonaDistributionResponse(BaseModel):
    """User breakdown by persona type."""
    total_users: int = Field(..., ge=0)
    personas: List[PersonaBreakdown]
    period_start: date
    period_end: date


class PulseAccuracyResponse(BaseModel):
    """PULSE validation accuracy metrics."""
    total_results_validated: int = Field(..., ge=0)
    accuracy_metrics: List[PulseAccuracyMetric]
    period_start: date
    period_end: date


class LeadRecord(BaseModel):
    """Individual lead from email capture."""
    session_id: str
    name: Optional[str] = None
    email: str
    domain: str
    is_corporate: bool = False
    country: Optional[str] = None
    city: Optional[str] = None
    source: str = "Direct"
    search_count: int = 0
    started_at: Optional[str] = None
    disclaimer_accepted: bool = False


class LeadsResponse(BaseModel):
    """Leads intelligence response."""
    total_leads: int = Field(..., ge=0)
    corporate_leads: int = Field(..., ge=0)
    generic_leads: int = Field(..., ge=0)
    capture_rate: float = Field(..., ge=0)
    leads: List[LeadRecord]
    period_start: date
    period_end: date


class TenantSummary(BaseModel):
    """Per-tenant summary for platform view."""
    tenant_name: str
    tenant_slug: str
    user_count: int = Field(..., ge=0)
    search_count: int = Field(..., ge=0)
    mrr: float = Field(..., ge=0)
    active_subscriptions: int = Field(..., ge=0)
    avg_response_time_ms: Optional[float] = Field(None, ge=0)


class TenantComparisonResponse(BaseModel):
    """Platform-wide tenant comparison."""
    total_tenants: int = Field(..., ge=0)
    tenants: List[TenantSummary]
    period_start: date
    period_end: date
