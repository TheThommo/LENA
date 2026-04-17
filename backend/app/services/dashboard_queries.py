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

        # Total searches. Primary source is the searches table. Fallback:
        # sum(sessions.search_count) — so historic visits that pre-date the
        # persona-enum fix (when searches inserts were silently rejected)
        # still register a number in the admin KPI instead of the
        # misleading "0".
        searches_query = client.table("searches").select("id", count="exact")
        if tenant_id:
            searches_query = searches_query.eq("tenant_id", tenant_id)
        searches_query = searches_query.gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())
        searches_result = searches_query.execute()
        total_searches = searches_result.count or 0

        if total_searches == 0:
            # Fallback: sum the per-session counter that SearchGateMiddleware
            # increments for every anonymous search.
            fb_q = client.table("sessions").select("search_count")
            if tenant_id:
                fb_q = fb_q.eq("tenant_id", tenant_id)
            fb_q = fb_q.gte("started_at", start_date.isoformat()).lte("started_at", end_date.isoformat())
            fb_res = fb_q.execute()
            total_searches = sum((r.get("search_count") or 0) for r in (fb_res.data or []))

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

        # Infer funnel from sessions table instead of event_log.
        # Every milestone is already stored as a column (name, email,
        # disclaimer_accepted_at, search_count, user_id) so the funnel
        # works even when the event_log is empty (it has been since launch
        # because the numeric-column bug dropped every write).
        q_base = client.table("sessions").select(
            "id, name, email, disclaimer_accepted_at, search_count, user_id",
        ).gte("started_at", start_date.isoformat()).lte("started_at", end_date.isoformat())
        if tenant_id:
            q_base = q_base.eq("tenant_id", tenant_id)
        all_sessions = (q_base.execute()).data or []

        # Count each milestone
        landed = len(all_sessions)
        named = sum(1 for s in all_sessions if s.get("name"))
        disclaimed = sum(1 for s in all_sessions if s.get("disclaimer_accepted_at"))
        first_search = sum(1 for s in all_sessions if (s.get("search_count") or 0) >= 1)
        emailed = sum(1 for s in all_sessions if s.get("email") and s["email"] != "_skipped")
        second_search = sum(1 for s in all_sessions if (s.get("search_count") or 0) >= 2)
        registered = sum(1 for s in all_sessions if s.get("user_id"))

        funnel_actions = [
            ("landed", landed),
            ("name_captured", named),
            ("disclaimer_accepted", disclaimed),
            ("first_search", first_search),
            ("email_captured", emailed),
            ("second_search", second_search),
            ("registered", registered),
        ]

        stages = []
        prev_count = None
        for action, count in funnel_actions:
            conversion_rate = None
            if prev_count is not None and prev_count > 0:
                conversion_rate = (count / prev_count * 100)
            stages.append({
                "stage_name": action,
                "session_count": count,
                "conversion_rate": conversion_rate,
            })
            prev_count = count

        overall_conversion = 0.0
        if landed > 0:
            overall_conversion = (registered / landed * 100)

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
            plans_response = client.table("plan_tiers").select("id, monthly_price_cents").execute()
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
    Get leads from TWO sources and merge:
      1. Sessions where email was captured (anonymous + pre-registration)
      2. Registered users (from users table) — covers sign-ups that went
         straight to /register without the session email-capture step.

    Deduplicates by email (lowercase). Classifies as corporate vs generic.
    """
    try:
        client = get_supabase_admin_client()
        start_date, end_date = _get_date_range(start_date, end_date)

        # Source 1: sessions with email
        sessions_query = client.table("sessions").select(
            "id, name, email, institution, phone, geo_country, geo_city, utm_source, referrer, "
            "search_count, started_at, disclaimer_accepted_at, data_consent_accepted_at, user_id"
        )
        sessions_query = sessions_query.not_.is_("email", "null")
        if tenant_id:
            sessions_query = sessions_query.eq("tenant_id", tenant_id)
        sessions_query = sessions_query.gte("started_at", start_date.isoformat()).lte("started_at", end_date.isoformat())
        sessions_query = sessions_query.order("started_at", desc=True)
        sessions_response = sessions_query.execute()

        # Source 2: registered users
        users_query = client.table("users").select("id, email, name, created_at")
        if tenant_id:
            users_query = users_query.eq("tenant_id", tenant_id)
        users_query = users_query.gte("created_at", start_date.isoformat()).lte("created_at", end_date.isoformat())
        users_response = users_query.execute()

        seen_emails: set[str] = set()
        leads = []
        corporate_count = 0

        def classify(email_str: str) -> tuple[str, bool]:
            domain = email_str.split("@")[-1].lower() if "@" in email_str else ""
            is_corp = domain not in GENERIC_EMAIL_DOMAINS and domain != ""
            return domain, is_corp

        # Process sessions first (richer context: geo, search_count, etc.)
        for s in sessions_response.data or []:
            email = (s.get("email") or "").strip()
            if not email or email == "_skipped":
                continue
            key = email.lower()
            if key in seen_emails:
                continue
            seen_emails.add(key)
            domain, is_corp = classify(email)
            if is_corp:
                corporate_count += 1
            leads.append({
                "session_id": s.get("id"),
                "name": s.get("name"),
                "email": email,
                "domain": domain,
                "is_corporate": is_corp,
                "registered": s.get("user_id") is not None,
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

        # Merge registered users not already covered by a session
        for u in users_response.data or []:
            email = (u.get("email") or "").strip()
            if not email:
                continue
            key = email.lower()
            if key in seen_emails:
                continue
            seen_emails.add(key)
            domain, is_corp = classify(email)
            if is_corp:
                corporate_count += 1
            leads.append({
                "session_id": None,
                "name": u.get("name"),
                "email": email,
                "domain": domain,
                "is_corporate": is_corp,
                "registered": True,
                "institution": None,
                "phone": None,
                "country": None,
                "city": None,
                "source": "Registration",
                "search_count": 0,
                "started_at": u.get("created_at"),
                "disclaimer_accepted": True,
                "data_consent": False,
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


async def get_cost_intelligence(
    tenant_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Per-user LLM cost, total spend, token volumes, and top-spender ranking.

    Costs are stored as USD millionths (llm_cost_micros) so arithmetic in
    Python never drifts with float rounding. Dollars are only produced at
    the response boundary.

    Per-user key preference:
      1. users.email (registered user) -> "jane@acme.com"
      2. sessions.email (anon capture)  -> "lead@example.com"
      3. session_id as fallback bucket  -> "anon:7ab2…"
    """
    try:
        client = get_supabase_admin_client()
        start, end = _get_date_range(start_date, end_date)

        q = (
            client.table("search_logs")
            .select(
                "id, user_id, session_id, tenant_id, query, persona, "
                "llm_model, llm_prompt_tokens, llm_completion_tokens, "
                "llm_cost_micros, created_at"
            )
            .gte("created_at", start.isoformat())
            .lte("created_at", end.isoformat())
            .not_.is_("llm_cost_micros", "null")
            .order("created_at", desc=True)
        )
        if tenant_id:
            q = q.eq("tenant_id", tenant_id)
        res = q.execute()
        rows = res.data or []

        # Hydrate user + session email in two bulk calls.
        user_ids = list({r["user_id"] for r in rows if r.get("user_id")})
        session_ids = list({r["session_id"] for r in rows if r.get("session_id")})
        users_map: Dict[str, dict] = {}
        sessions_map: Dict[str, dict] = {}
        if user_ids:
            u = client.table("users").select("id, email, name").in_("id", user_ids).execute()
            users_map = {row["id"]: row for row in (u.data or [])}
        if session_ids:
            s = client.table("sessions").select("id, name, email").in_("id", session_ids).execute()
            sessions_map = {row["id"]: row for row in (s.data or [])}

        by_user: Dict[str, dict] = {}
        total_micros = 0
        total_prompt = 0
        total_completion = 0
        total_searches = 0
        for r in rows:
            micros = int(r.get("llm_cost_micros") or 0)
            pt = int(r.get("llm_prompt_tokens") or 0)
            ct = int(r.get("llm_completion_tokens") or 0)
            total_micros += micros
            total_prompt += pt
            total_completion += ct
            total_searches += 1

            u = users_map.get(r.get("user_id") or "", {})
            s = sessions_map.get(r.get("session_id") or "", {})
            key_email = u.get("email") or s.get("email")
            key_name = u.get("name") or s.get("name")
            if key_email:
                key = key_email.lower()
                display_name = key_name or key_email
            else:
                # Fallback bucket: one anon session == one "user".
                key = f"anon:{r.get('session_id') or 'unknown'}"
                display_name = "Anonymous visitor"

            slot = by_user.setdefault(key, {
                "key": key,
                "email": key_email,
                "name": display_name,
                "registered": bool(r.get("user_id")),
                "searches": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "cost_micros": 0,
                "last_search_at": None,
            })
            slot["searches"] += 1
            slot["prompt_tokens"] += pt
            slot["completion_tokens"] += ct
            slot["cost_micros"] += micros
            ts = r.get("created_at")
            if ts and (slot["last_search_at"] is None or ts > slot["last_search_at"]):
                slot["last_search_at"] = ts

        # Sort by cost desc for top spenders
        per_user = sorted(by_user.values(), key=lambda x: x["cost_micros"], reverse=True)

        # Convert to user-facing $ / cents here, preserving the raw micro counter
        def enrich(entry: dict) -> dict:
            cost_usd = entry["cost_micros"] / 1_000_000.0
            entry["cost_usd"] = round(cost_usd, 4)
            entry["cost_cents"] = round(cost_usd * 100, 2)
            entry["avg_cost_per_search_usd"] = round(cost_usd / entry["searches"], 4) if entry["searches"] else 0
            return entry

        per_user = [enrich(e) for e in per_user]
        top_spenders = per_user[:limit]

        total_usd = total_micros / 1_000_000.0
        avg_per_search_usd = total_usd / total_searches if total_searches else 0.0
        distinct_users = len(per_user)

        return {
            "total_cost_usd": round(total_usd, 4),
            "total_cost_cents": round(total_usd * 100, 2),
            "total_searches_with_llm": total_searches,
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "distinct_users": distinct_users,
            "avg_cost_per_search_usd": round(avg_per_search_usd, 6),
            "avg_cost_per_user_usd": round(total_usd / distinct_users, 4) if distinct_users else 0.0,
            "top_spenders": top_spenders,
            "per_user": per_user,
            "period_start": start,
            "period_end": end,
        }
    except Exception:
        logger.error("Error getting cost intelligence", exc_info=True)
        return {
            "total_cost_usd": 0,
            "total_cost_cents": 0,
            "total_searches_with_llm": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "distinct_users": 0,
            "avg_cost_per_search_usd": 0,
            "avg_cost_per_user_usd": 0,
            "top_spenders": [],
            "per_user": [],
            "period_start": start_date or date.today(),
            "period_end": end_date or date.today(),
        }


async def get_session_activity(
    tenant_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 500,
) -> Dict[str, Any]:
    """
    Every visitor session in the period, newest first, regardless of whether
    they submitted their email or completed a search. This surfaces the
    complete visitor story — not just "leads" — and is what the admin needs
    to see WHO showed up when a specific demo happened.

    Does NOT expose what they asked (that's /questions, which requires a
    successful search_logs insert that today may or may not have happened).
    """
    try:
        client = get_supabase_admin_client()
        start, end = _get_date_range(start_date, end_date)

        q = (
            client.table("sessions")
            .select(
                "id, name, email, institution, phone, geo_country, geo_city, "
                "utm_source, referrer, search_count, started_at, "
                "disclaimer_accepted_at, data_consent_accepted_at, user_id",
                count="exact",
            )
            .gte("started_at", start.isoformat())
            .lte("started_at", end.isoformat())
            .order("started_at", desc=True)
            .limit(limit)
        )
        if tenant_id:
            q = q.eq("tenant_id", tenant_id)
        res = q.execute()
        rows = res.data or []
        total = res.count or len(rows)

        sessions_out: List[dict] = []
        total_searches_inferred = 0
        for s in rows:
            sc = s.get("search_count") or 0
            total_searches_inferred += sc
            sessions_out.append({
                "session_id": s.get("id"),
                "user_id": s.get("user_id"),
                "name": s.get("name"),
                "email": s.get("email"),
                "institution": s.get("institution"),
                "country": s.get("geo_country"),
                "city": s.get("geo_city"),
                "search_count": sc,
                "started_at": s.get("started_at"),
                "disclaimer_accepted": s.get("disclaimer_accepted_at") is not None,
                "registered": s.get("user_id") is not None,
                "source": s.get("utm_source") or s.get("referrer") or "Direct",
            })

        return {
            "total_sessions": total,
            "total_searches_inferred": total_searches_inferred,
            "sessions": sessions_out,
            "period_start": start,
            "period_end": end,
        }
    except Exception:
        logger.error("Error getting session activity", exc_info=True)
        return {
            "total_sessions": 0,
            "total_searches_inferred": 0,
            "sessions": [],
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
