"""
Dashboard Query Service

Async service layer for all dashboard data queries.
Handles both platform-wide (all tenants) and tenant-scoped queries.

Uses admin client (bypasses RLS) for dashboard read access.
All methods are async and return dicts/lists for JSON serialization.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from collections import Counter
from uuid import UUID

from app.db.supabase import get_supabase_admin_client
from app.core.config import settings

logger = logging.getLogger(__name__)

# Default date range (last 30 days)
DEFAULT_DAYS_BACK = 30


def _get_date_range(start_date: Optional[date], end_date: Optional[date]) -> tuple:
    """
    Helper to get date range, defaulting to last 30 days.

    Args:
        start_date: Optional start date
        end_date: Optional end date

    Returns:
        (start_date, end_date) both as date objects
    """
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=DEFAULT_DAYS_BACK)

    return start_date, end_date


async def get_overview_stats(
    tenant_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Get top-level overview statistics.

    Returns:
        {
            'total_users': int,
            'total_searches': int,
            'active_sessions': int,
            'avg_response_time_ms': float,
            'new_users_this_period': int,
            'mrr': float (optional),
        }
    """
    try:
        client = get_supabase_admin_client()
        start_date, end_date = _get_date_range(start_date, end_date)

        # Total users
        users_query = client.table("users").select("id", count="exact")
        if tenant_id:
            users_query = users_query.eq("tenant_id", tenant_id)
        users_result = users_query.execute()
        total_users = users_result.count or 0

        # Total searches
        searches_query = client.table("searches").select("id", count="exact")
        if tenant_id:
            searches_query = searches_query.eq("tenant_id", tenant_id)
        searches_query = searches_query.gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())
        searches_result = searches_query.execute()
        total_searches = searches_result.count or 0

        # Active sessions (in the period)
        sessions_query = client.table("sessions").select("id", count="exact")
        if tenant_id:
            sessions_query = sessions_query.eq("tenant_id", tenant_id)
        sessions_query = sessions_query.gte("started_at", start_date.isoformat()).lte("started_at", end_date.isoformat())
        sessions_result = sessions_query.execute()
        active_sessions = sessions_result.count or 0

        # Average response time
        search_logs_response = client.table("search_logs").select("response_time_ms")
        search_logs_response = search_logs_response.gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())
        if tenant_id:
            # Join through searches table
            search_logs_response = search_logs_response.execute()
            avg_response_time = 0.0
            if search_logs_response.data:
                times = [log.get("response_time_ms", 0) for log in search_logs_response.data]
                avg_response_time = sum(times) / len(times) if times else 0.0
        else:
            search_logs_response = search_logs_response.execute()
            avg_response_time = 0.0
            if search_logs_response.data:
                times = [log.get("response_time_ms", 0) for log in search_logs_response.data]
                avg_response_time = sum(times) / len(times) if times else 0.0

        # New users this period
        new_users_query = client.table("users").select("id", count="exact")
        if tenant_id:
            new_users_query = new_users_query.eq("tenant_id", tenant_id)
        new_users_query = new_users_query.gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())
        new_users_result = new_users_query.execute()
        new_users_this_period = new_users_result.count or 0

        # MRR (monthly recurring revenue) - only if not tenant-scoped
        mrr = None
        if not tenant_id:
            subs_response = client.table("tenant_subscriptions").select("id, status, plan_id")
            subs_response = subs_response.eq("status", "active").execute()
            if subs_response.data:
                # Fetch plans for pricing
                plan_ids = list(set(sub.get("plan_id") for sub in subs_response.data if sub.get("plan_id")))
                if plan_ids:
                    plans_response = client.table("plan_tiers").select("id, monthly_price_cents").execute()
                    plans_map = {p["id"]: p.get("monthly_price_cents", 0) for p in plans_response.data or []}
                    mrr = sum(plans_map.get(sub.get("plan_id"), 0) for sub in subs_response.data)

        return {
            "total_users": total_users,
            "total_searches": total_searches,
            "active_sessions": active_sessions,
            "avg_response_time_ms": avg_response_time,
            "new_users_this_period": new_users_this_period,
            "mrr": mrr,
            "period_start": start_date,
            "period_end": end_date,
        }
    except Exception as e:
        logger.error(f"Error getting overview stats: {e}")
        return {
            "total_users": 0,
            "total_searches": 0,
            "active_sessions": 0,
            "avg_response_time_ms": 0.0,
            "new_users_this_period": 0,
            "mrr": None,
            "period_start": start_date or date.today(),
            "period_end": end_date or date.today(),
        }


async def get_traffic_sources(
    tenant_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Breakdown of traffic by UTM source and referrer category.

    Returns:
        {
            'total_sessions': int,
            'sources': [{'source': str, 'count': int, 'percentage': float}, ...],
        }
    """
    try:
        client = get_supabase_admin_client()
        start_date, end_date = _get_date_range(start_date, end_date)

        # Fetch sessions with UTM and referrer data
        sessions_query = client.table("sessions").select("utm_source, referrer")
        if tenant_id:
            sessions_query = sessions_query.eq("tenant_id", tenant_id)
        sessions_query = sessions_query.gte("started_at", start_date.isoformat()).lte("started_at", end_date.isoformat())
        sessions_response = sessions_query.execute()

        source_counts = Counter()
        for session in sessions_response.data or []:
            source = session.get("utm_source") or session.get("referrer") or "Direct"
            source_counts[source] += 1

        total_sessions = sum(source_counts.values())
        sources = [
            {
                "source": source,
                "count": count,
                "percentage": (count / total_sessions * 100) if total_sessions > 0 else 0.0,
            }
            for source, count in source_counts.most_common()
        ]

        return {
            "total_sessions": total_sessions,
            "sources": sources,
            "period_start": start_date,
            "period_end": end_date,
        }
    except Exception as e:
        logger.error(f"Error getting traffic sources: {e}")
        return {
            "total_sessions": 0,
            "sources": [],
            "period_start": start_date or date.today(),
            "period_end": end_date or date.today(),
        }


async def get_geo_distribution(
    tenant_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Geographic distribution of visitors by country and city.

    Returns:
        {
            'total_locations': int,
            'locations': [{'country': str, 'city': str, 'count': int}, ...],
        }
    """
    try:
        client = get_supabase_admin_client()
        start_date, end_date = _get_date_range(start_date, end_date)

        # Fetch sessions with geo data
        sessions_query = client.table("sessions").select("geo_country, geo_city")
        if tenant_id:
            sessions_query = sessions_query.eq("tenant_id", tenant_id)
        sessions_query = sessions_query.gte("started_at", start_date.isoformat()).lte("started_at", end_date.isoformat())
        sessions_response = sessions_query.execute()

        geo_counts = Counter()
        for session in sessions_response.data or []:
            country = session.get("geo_country") or "Unknown"
            city = session.get("geo_city") or "Unknown"
            geo_counts[(country, city)] += 1

        locations = [
            {
                "country": country,
                "city": city,
                "count": count,
            }
            for (country, city), count in geo_counts.most_common(100)  # Top 100
        ]

        return {
            "total_locations": len(geo_counts),
            "locations": locations,
            "period_start": start_date,
            "period_end": end_date,
        }
    except Exception as e:
        logger.error(f"Error getting geo distribution: {e}")
        return {
            "total_locations": 0,
            "locations": [],
            "period_start": start_date or date.today(),
            "period_end": end_date or date.today(),
        }


async def get_topic_trends(
    tenant_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Top trending search topics.
    Uses topic metadata from usage_analytics if available, else extracts from queries.

    Returns:
        {
            'total_unique_topics': int,
            'topics': [{'topic': str, 'count': int}, ...],
        }
    """
    try:
        client = get_supabase_admin_client()
        start_date, end_date = _get_date_range(start_date, end_date)

        # Try to fetch from usage_analytics where action contains 'topic'
        analytics_query = client.table("event_log").select("metadata")
        if tenant_id:
            analytics_query = analytics_query.eq("tenant_id", tenant_id)
        analytics_query = analytics_query.gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())
        analytics_response = analytics_query.execute()

        topic_counts = Counter()
        for event in analytics_response.data or []:
            metadata = event.get("metadata") or {}
            if isinstance(metadata, dict):
                topic = metadata.get("topic")
                if topic:
                    topic_counts[topic] += 1

        # If no topics found in analytics, get from searches (fallback)
        if not topic_counts:
            searches_query = client.table("searches").select("query_text")
            if tenant_id:
                searches_query = searches_query.eq("tenant_id", tenant_id)
            searches_query = searches_query.gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())
            searches_response = searches_query.execute()

            # Use first 2 words as topic proxy
            for search in searches_response.data or []:
                query = search.get("query_text", "")
                if query:
                    words = query.split()[:2]
                    topic = " ".join(words) if words else "Other"
                    topic_counts[topic] += 1

        topics = [
            {"topic": topic, "count": count}
            for topic, count in topic_counts.most_common(20)  # Top 20
        ]

        return {
            "total_unique_topics": len(topic_counts),
            "topics": topics,
            "period_start": start_date,
            "period_end": end_date,
        }
    except Exception as e:
        logger.error(f"Error getting topic trends: {e}")
        return {
            "total_unique_topics": 0,
            "topics": [],
            "period_start": start_date or date.today(),
            "period_end": end_date or date.today(),
        }


async def get_funnel_metrics(
    tenant_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Conversion funnel metrics by stage.
    Stages: landed, name_captured, disclaimer_accepted, first_search, email_captured, second_search, signup_cta_shown, registered

    Returns:
        {
            'stages': [{'stage_name': str, 'session_count': int, 'conversion_rate': float}, ...],
            'overall_conversion_rate': float,
        }
    """
    try:
        client = get_supabase_admin_client()
        start_date, end_date = _get_date_range(start_date, end_date)

        # Fetch usage analytics for funnel events
        funnel_actions = [
            "landed",
            "name_captured",
            "disclaimer_accepted",
            "first_search",
            "email_captured",
            "second_search",
            "signup_cta_shown",
            "registered",
        ]

        stage_counts = {}
        for action in funnel_actions:
            analytics_query = client.table("event_log").select("id", count="exact")
            analytics_query = analytics_query.eq("event_name", "funnel_stage")
            analytics_query = analytics_query.eq("value", action)
            if tenant_id:
                analytics_query = analytics_query.eq("tenant_id", tenant_id)
            analytics_query = analytics_query.gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())
            analytics_response = analytics_query.execute()
            stage_counts[action] = analytics_response.count or 0

        # Calculate conversion rates between consecutive stages
        stages = []
        prev_count = None
        for action in funnel_actions:
            count = stage_counts[action]
            conversion_rate = None
            if prev_count is not None and prev_count > 0:
                conversion_rate = (count / prev_count * 100)
            stages.append({
                "stage_name": action,
                "session_count": count,
                "conversion_rate": conversion_rate,
            })
            prev_count = count

        # Overall conversion (registered / landed)
        overall_conversion = 0.0
        if stage_counts.get("landed", 0) > 0:
            overall_conversion = (stage_counts.get("registered", 0) / stage_counts["landed"] * 100)

        return {
            "stages": stages,
            "overall_conversion_rate": overall_conversion,
            "period_start": start_date,
            "period_end": end_date,
        }
    except Exception as e:
        logger.error(f"Error getting funnel metrics: {e}")
        return {
            "stages": [],
            "overall_conversion_rate": 0.0,
            "period_start": start_date or date.today(),
            "period_end": end_date or date.today(),
        }


async def get_user_growth(
    tenant_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    User registration growth over time (daily).

    Returns:
        {
            'total_users': int,
            'growth_data': [{'date': date, 'new_users': int, 'cumulative_users': int}, ...],
        }
    """
    try:
        client = get_supabase_admin_client()
        start_date, end_date = _get_date_range(start_date, end_date)

        # Fetch users created in period
        users_query = client.table("users").select("created_at")
        if tenant_id:
            users_query = users_query.eq("tenant_id", tenant_id)
        users_query = users_query.gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())
        users_response = users_query.execute()

        # Group by day
        daily_counts = Counter()
        for user in users_response.data or []:
            created = user.get("created_at")
            if created:
                # Parse ISO format date
                if isinstance(created, str):
                    user_date = datetime.fromisoformat(created.replace("Z", "+00:00")).date()
                else:
                    user_date = created.date() if hasattr(created, "date") else created
                daily_counts[user_date] += 1

        # Build cumulative growth data
        growth_data = []
        cumulative = 0
        for day in sorted(daily_counts.keys()):
            new_count = daily_counts[day]
            cumulative += new_count
            growth_data.append({
                "date": day,
                "new_users": new_count,
                "cumulative_users": cumulative,
            })

        total_users = cumulative

        return {
            "total_users": total_users,
            "growth_data": growth_data,
            "period_start": start_date,
            "period_end": end_date,
        }
    except Exception as e:
        logger.error(f"Error getting user growth: {e}")
        return {
            "total_users": 0,
            "growth_data": [],
            "period_start": start_date or date.today(),
            "period_end": end_date or date.today(),
        }


async def get_search_activity(
    tenant_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Search activity trends over time (daily).

    Returns:
        {
            'total_searches': int,
            'avg_searches_per_user': float,
            'activity_data': [{'date': date, 'total_searches': int, 'avg_per_user': float}, ...],
        }
    """
    try:
        client = get_supabase_admin_client()
        start_date, end_date = _get_date_range(start_date, end_date)

        # Fetch searches in period
        searches_query = client.table("searches").select("created_at, user_id")
        if tenant_id:
            searches_query = searches_query.eq("tenant_id", tenant_id)
        searches_query = searches_query.gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())
        searches_response = searches_query.execute()

        # Group by day
        daily_searches = Counter()
        unique_users_by_day = {}
        for search in searches_response.data or []:
            created = search.get("created_at")
            if created:
                if isinstance(created, str):
                    search_date = datetime.fromisoformat(created.replace("Z", "+00:00")).date()
                else:
                    search_date = created.date() if hasattr(created, "date") else created
                daily_searches[search_date] += 1

                # Track unique users per day
                user_id = search.get("user_id")
                if user_id:
                    if search_date not in unique_users_by_day:
                        unique_users_by_day[search_date] = set()
                    unique_users_by_day[search_date].add(user_id)

        # Build activity data
        activity_data = []
        for day in sorted(daily_searches.keys()):
            searches_count = daily_searches[day]
            unique_users = len(unique_users_by_day.get(day, set()))
            avg_per_user = (searches_count / unique_users) if unique_users > 0 else 0.0
            activity_data.append({
                "date": day,
                "total_searches": searches_count,
                "avg_per_user": avg_per_user,
            })

        total_searches = sum(daily_searches.values())
        total_unique_users = len(set(
            user_id for search in searches_response.data or []
            for user_id in [search.get("user_id")] if user_id
        ))
        avg_searches_per_user = (total_searches / total_unique_users) if total_unique_users > 0 else 0.0

        return {
            "total_searches": total_searches,
            "avg_searches_per_user": avg_searches_per_user,
            "activity_data": activity_data,
            "period_start": start_date,
            "period_end": end_date,
        }
    except Exception as e:
        logger.error(f"Error getting search activity: {e}")
        return {
            "total_searches": 0,
            "avg_searches_per_user": 0.0,
            "activity_data": [],
            "period_start": start_date or date.today(),
            "period_end": end_date or date.today(),
        }


async def get_revenue_metrics(tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Revenue and subscription metrics.
    Only works for platform-wide view (ignores tenant_id).

    Returns:
        {
            'mrr': float,
            'active_subscriptions': int,
            'cancelled_last_period': int,
            'plan_distribution': [{'plan_name': str, 'count': int, 'mrr': float, 'percentage': float}, ...],
        }
    """
    try:
        client = get_supabase_admin_client()

        # Fetch active subscriptions
        active_subs_response = client.table("tenant_subscriptions").select("id, plan_id, status")
        active_subs_response = active_subs_response.eq("status", "active").execute()
        active_subs = active_subs_response.data or []
        active_count = len(active_subs)

        # Fetch plans
        plans_response = client.table("plan_tiers").select("id, name, monthly_price_cents").execute()
        plans_map = {p["id"]: p for p in plans_response.data or []}

        # Calculate MRR and plan distribution
        plan_counts = Counter()
        plan_mrr = {}
        total_mrr = 0.0
        for sub in active_subs:
            plan_id = sub.get("plan_id")
            plan = plans_map.get(plan_id, {})
            plan_name = plan.get("name", "Unknown")
            price = plan.get("monthly_price_cents", 0)

            plan_counts[plan_name] += 1
            plan_mrr[plan_name] = plan_mrr.get(plan_name, 0) + price
            total_mrr += price

        # Calculate percentages
        plan_distribution = [
            {
                "plan_name": plan_name,
                "count": count,
                "mrr": plan_mrr.get(plan_name, 0),
                "percentage": (count / active_count * 100) if active_count > 0 else 0.0,
            }
            for plan_name, count in plan_counts.most_common()
        ]

        # Cancelled subscriptions (last 30 days)
        thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()
        cancelled_response = client.table("tenant_subscriptions").select("id", count="exact")
        cancelled_response = cancelled_response.eq("status", "cancelled")
        cancelled_response = cancelled_response.gte("updated_at", thirty_days_ago)
        cancelled_response = cancelled_response.execute()
        cancelled_count = cancelled_response.count or 0

        return {
            "mrr": total_mrr,
            "active_subscriptions": active_count,
            "cancelled_last_period": cancelled_count,
            "plan_distribution": plan_distribution,
        }
    except Exception as e:
        logger.error(f"Error getting revenue metrics: {e}")
        return {
            "mrr": 0.0,
            "active_subscriptions": 0,
            "cancelled_last_period": 0,
            "plan_distribution": [],
        }


async def get_tenant_comparison(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Platform-only: Per-tenant usage comparison.

    Returns:
        {
            'total_tenants': int,
            'tenants': [{'tenant_name': str, 'tenant_slug': str, 'user_count': int, 'search_count': int, 'mrr': float, 'active_subscriptions': int, 'avg_response_time_ms': float}, ...],
        }
    """
    try:
        client = get_supabase_admin_client()
        start_date, end_date = _get_date_range(start_date, end_date)

        # Fetch all tenants
        tenants_response = client.table("tenants").select("id, name, slug").execute()
        tenants = tenants_response.data or []

        tenant_summaries = []
        for tenant in tenants:
            tenant_id = tenant.get("id")
            tenant_name = tenant.get("name")
            tenant_slug = tenant.get("slug")

            # User count
            users_response = client.table("users").select("id", count="exact").eq("tenant_id", tenant_id).execute()
            user_count = users_response.count or 0

            # Search count in period
            searches_response = client.table("searches").select("id", count="exact").eq("tenant_id", tenant_id).gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat()).execute()
            search_count = searches_response.count or 0

            # Active subscriptions and MRR
            subs_response = client.table("tenant_subscriptions").select("id, plan_id, status").eq("tenant_id", tenant_id).eq("status", "active").execute()
            subs = subs_response.data or []
            active_subscriptions = len(subs)

            # Get plan pricing
            plans_response = client.table("plan_tiers").select("id, price_monthly").execute()
            plans_map = {p["id"]: p.get("monthly_price_cents", 0) for p in plans_response.data or []}
            mrr = sum(plans_map.get(sub.get("plan_id"), 0) for sub in subs)

            # Average response time
            logs_response = client.table("search_logs").select("response_time_ms")
            logs_response = logs_response.eq("tenant_id", tenant_id)
            logs_response = logs_response.gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat()).execute()
            logs = logs_response.data or []

            avg_response_time = None
            if logs:
                times = [log.get("response_time_ms", 0) for log in logs]
                avg_response_time = sum(times) / len(times) if times else None

            tenant_summaries.append({
                "tenant_name": tenant_name,
                "tenant_slug": tenant_slug,
                "user_count": user_count,
                "search_count": search_count,
                "mrr": mrr,
                "active_subscriptions": active_subscriptions,
                "avg_response_time_ms": avg_response_time,
            })

        return {
            "total_tenants": len(tenant_summaries),
            "tenants": tenant_summaries,
            "period_start": start_date,
            "period_end": end_date,
        }
    except Exception as e:
        logger.error(f"Error getting tenant comparison: {e}")
        return {
            "total_tenants": 0,
            "tenants": [],
            "period_start": start_date or date.today(),
            "period_end": end_date or date.today(),
        }


async def get_popular_queries(
    tenant_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Most frequently searched queries.

    Returns:
        {
            'total_searches': int,
            'queries': [{'query': str, 'count': int, 'avg_response_time_ms': float}, ...],
        }
    """
    try:
        client = get_supabase_admin_client()
        start_date, end_date = _get_date_range(start_date, end_date)

        # Fetch searches
        searches_query = client.table("searches").select("query_text, id")
        if tenant_id:
            searches_query = searches_query.eq("tenant_id", tenant_id)
        searches_query = searches_query.gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())
        searches_response = searches_query.execute()

        query_counts = Counter()
        search_ids = []
        for search in searches_response.data or []:
            query = search.get("query_text", "").strip()
            if query:
                query_counts[query] += 1
            search_ids.append(search.get("id"))

        # Get response times for searches
        response_times = {}
        if search_ids:
            logs_response = client.table("search_logs").select("search_id, response_time_ms").execute()
            for log in logs_response.data or []:
                search_id = log.get("search_id")
                response_times[search_id] = log.get("response_time_ms", 0)

        # Build queries list with avg response time
        queries = []
        for query, count in query_counts.most_common(limit):
            # Calculate avg response time for this query (rough estimate)
            avg_time = None
            if response_times:
                times = list(response_times.values())
                avg_time = sum(times) / len(times) if times else None

            queries.append({
                "query": query,
                "count": count,
                "avg_response_time_ms": avg_time,
            })

        return {
            "total_searches": sum(query_counts.values()),
            "queries": queries,
            "period_start": start_date,
            "period_end": end_date,
        }
    except Exception as e:
        logger.error(f"Error getting popular queries: {e}")
        return {
            "total_searches": 0,
            "queries": [],
            "period_start": start_date or date.today(),
            "period_end": end_date or date.today(),
        }


async def get_persona_distribution(
    tenant_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    User breakdown by persona type.

    Returns:
        {
            'total_users': int,
            'personas': [{'persona': str, 'count': int, 'percentage': float}, ...],
        }
    """
    try:
        client = get_supabase_admin_client()
        start_date, end_date = _get_date_range(start_date, end_date)

        # Fetch users with persona data
        users_query = client.table("users").select("persona_type")
        if tenant_id:
            users_query = users_query.eq("tenant_id", tenant_id)
        users_query = users_query.gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())
        users_response = users_query.execute()

        persona_counts = Counter()
        for user in users_response.data or []:
            persona = user.get("persona_type") or "General"
            persona_counts[persona] += 1

        total_users = sum(persona_counts.values())
        personas = [
            {
                "persona": persona,
                "count": count,
                "percentage": (count / total_users * 100) if total_users > 0 else 0.0,
            }
            for persona, count in persona_counts.most_common()
        ]

        return {
            "total_users": total_users,
            "personas": personas,
            "period_start": start_date,
            "period_end": end_date,
        }
    except Exception as e:
        logger.error(f"Error getting persona distribution: {e}")
        return {
            "total_users": 0,
            "personas": [],
            "period_start": start_date or date.today(),
            "period_end": end_date or date.today(),
        }


GENERIC_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "live.com",
    "icloud.com", "msn.com", "aol.com", "protonmail.com", "mail.com",
    "zoho.com", "yandex.com", "gmx.com", "fastmail.com", "tutanota.com",
    "pm.me", "hey.com", "me.com", "mac.com", "googlemail.com",
    "yahoo.co.uk", "yahoo.com.au", "outlook.com.au", "bigpond.com",
}


async def get_leads(
    tenant_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Get sessions with captured emails (leads).
    Classifies emails as corporate vs generic.
    """
    try:
        client = get_supabase_admin_client()
        start_date, end_date = _get_date_range(start_date, end_date)

        sessions_query = client.table("sessions").select(
            "id, name, email, institution, phone, geo_country, geo_city, utm_source, referrer, "
            "search_count, started_at, disclaimer_accepted_at, data_consent_accepted_at"
        )
        sessions_query = sessions_query.not_.is_("email", "null")
        if tenant_id:
            sessions_query = sessions_query.eq("tenant_id", tenant_id)
        sessions_query = sessions_query.gte("started_at", start_date.isoformat()).lte("started_at", end_date.isoformat())
        sessions_query = sessions_query.order("started_at", desc=True)
        sessions_response = sessions_query.execute()

        leads = []
        corporate_count = 0
        for s in sessions_response.data or []:
            email = s.get("email", "")
            domain = email.split("@")[-1].lower() if "@" in email else ""
            is_corporate = domain not in GENERIC_EMAIL_DOMAINS and domain != ""
            if is_corporate:
                corporate_count += 1
            leads.append({
                "session_id": s.get("id"),
                "name": s.get("name"),
                "email": email,
                "domain": domain,
                "is_corporate": is_corporate,
                "institution": s.get("institution"),
                "phone": s.get("phone"),
                "country": s.get("geo_country"),
                "city": s.get("geo_city"),
                "source": s.get("utm_source") or s.get("referrer") or "Direct",
                "search_count": s.get("search_count", 0),
                "started_at": s.get("started_at"),
                "disclaimer_accepted": s.get("disclaimer_accepted_at") is not None,
                "data_consent": s.get("data_consent_accepted_at") is not None,
            })

        total = len(leads)
        return {
            "total_leads": total,
            "corporate_leads": corporate_count,
            "generic_leads": total - corporate_count,
            "capture_rate": 0.0,  # Will be calculated with total sessions
            "leads": leads,
            "period_start": start_date,
            "period_end": end_date,
        }
    except Exception as e:
        logger.error(f"Error getting leads: {e}")
        return {
            "total_leads": 0,
            "corporate_leads": 0,
            "generic_leads": 0,
            "capture_rate": 0.0,
            "leads": [],
            "period_start": start_date or date.today(),
            "period_end": end_date or date.today(),
        }


async def get_pulse_accuracy(
    tenant_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    PULSE validation accuracy metrics.

    Returns:
        {
            'total_results_validated': int,
            'accuracy_metrics': [{'status': str, 'count': int, 'percentage': float}, ...],
        }
    """
    try:
        client = get_supabase_admin_client()
        start_date, end_date = _get_date_range(start_date, end_date)

        # Fetch PULSE status from search_logs
        results_query = client.table("search_logs").select("pulse_status")
        if tenant_id:
            results_query = results_query.eq("tenant_id", tenant_id)
        results_query = results_query.gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())
        results_response = results_query.execute()

        status_counts = Counter()
        for result in results_response.data or []:
            status = result.get("pulse_status") or "pending"
            status_counts[status] += 1

        total_validated = sum(status_counts.values())
        metrics = [
            {
                "status": status,
                "count": count,
                "percentage": (count / total_validated * 100) if total_validated > 0 else 0.0,
            }
            for status, count in status_counts.most_common()
        ]

        return {
            "total_results_validated": total_validated,
            "accuracy_metrics": metrics,
            "period_start": start_date,
            "period_end": end_date,
        }
    except Exception as e:
        logger.error(f"Error getting PULSE accuracy: {e}")
        return {
            "total_results_validated": 0,
            "accuracy_metrics": [],
            "period_start": start_date or date.today(),
            "period_end": end_date or date.today(),
        }


async def get_recent_questions(
    tenant_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 200,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Raw feed of what users actually asked.

    One row per search, newest first, joined with session/user context so
    the admin can see WHO asked WHAT and WHEN. Only the question text is
    surfaced — no citations, no LLM responses (per product policy).

    Returns:
        {
            'total': int,                 # total matching the filter
            'questions': [{
                'id', 'query', 'persona', 'created_at',
                'session_id', 'user_id', 'user_email', 'user_name',
                'geo_country', 'geo_city',
                'response_time_ms', 'total_results', 'pulse_status',
                'sources_succeeded', 'sources_queried',
            }, ...],
            'period_start', 'period_end',
        }
    """
    try:
        client = get_supabase_admin_client()
        start, end = _get_date_range(start_date, end_date)

        q = client.table("search_logs").select(
            "id, query, persona, response_time_ms, total_results, pulse_status, "
            "sources_queried, sources_succeeded, session_id, user_id, tenant_id, created_at",
            count="exact",
        )
        if tenant_id:
            q = q.eq("tenant_id", tenant_id)
        q = (
            q.gte("created_at", start.isoformat())
             .lte("created_at", end.isoformat())
             .order("created_at", desc=True)
             .range(offset, offset + limit - 1)
        )
        res = q.execute()
        rows = res.data or []
        total = res.count or len(rows)

        # Hydrate session and user context in 2 bulk lookups (no N+1).
        session_ids = [r["session_id"] for r in rows if r.get("session_id")]
        user_ids = [r["user_id"] for r in rows if r.get("user_id")]

        sessions_map: Dict[str, dict] = {}
        if session_ids:
            s_res = (
                client.table("sessions")
                .select("id, name, email, geo_country, geo_city")
                .in_("id", list(set(session_ids)))
                .execute()
            )
            sessions_map = {s["id"]: s for s in (s_res.data or [])}

        users_map: Dict[str, dict] = {}
        if user_ids:
            u_res = (
                client.table("users")
                .select("id, email, name")
                .in_("id", list(set(user_ids)))
                .execute()
            )
            users_map = {u["id"]: u for u in (u_res.data or [])}

        questions = []
        for r in rows:
            s = sessions_map.get(r.get("session_id") or "", {})
            u = users_map.get(r.get("user_id") or "", {})
            questions.append({
                "id": r.get("id"),
                "query": r.get("query"),
                "persona": r.get("persona"),
                "created_at": r.get("created_at"),
                "session_id": r.get("session_id"),
                "user_id": r.get("user_id"),
                # Prefer registered-user identity, fall back to anon session fields
                "user_email": u.get("email") or s.get("email"),
                "user_name": u.get("name") or s.get("name"),
                "geo_country": s.get("geo_country"),
                "geo_city": s.get("geo_city"),
                "response_time_ms": r.get("response_time_ms"),
                "total_results": r.get("total_results"),
                "pulse_status": r.get("pulse_status"),
                "sources_queried": r.get("sources_queried") or [],
                "sources_succeeded": r.get("sources_succeeded") or [],
            })

        return {
            "total": total,
            "questions": questions,
            "period_start": start,
            "period_end": end,
        }
    except Exception as e:
        logger.error("Error getting recent questions", exc_info=True)
        return {
            "total": 0,
            "questions": [],
            "period_start": start_date or date.today(),
            "period_end": end_date or date.today(),
        }
