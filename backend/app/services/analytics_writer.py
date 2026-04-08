"""
Analytics Event Writer

Fire-and-forget async logging for all analytics events.
Writes to Supabase tables: sessions, usage_analytics, search_logs, audit_trail.

All writes are background tasks to never block user requests.
Errors are logged but never raised.
"""

import logging
import asyncio
from typing import Optional, Any
from datetime import datetime

from app.db.supabase import get_supabase_client

logger = logging.getLogger(__name__)


async def log_session_start(
    session_id: str,
    ip: str,
    geo_data: Optional[dict],
    referrer_data: dict,
    utm_data: dict,
    tenant_id: str,
) -> None:
    """
    Log the start of a new session.

    Args:
        session_id: Unique session identifier (UUID)
        ip: Client IP address
        geo_data: Result from geolocation (country, city, lat, lon) or None
        referrer_data: Result from classify_referrer (raw, domain, category)
        utm_data: Result from parse_utm_params (utm_source, medium, campaign, term, content)
        tenant_id: Tenant identifier (for multi-tenancy)
    """
    try:
        client = get_supabase_client()

        # Build payload
        payload = {
            "id": session_id,
            "tenant_id": tenant_id,
            "ip_address": ip,
            "geo_city": geo_data.get("city") if geo_data else None,
            "geo_country": geo_data.get("country") if geo_data else None,
            "geo_lat": geo_data.get("lat") if geo_data else None,
            "geo_lon": geo_data.get("lon") if geo_data else None,
            "referrer": referrer_data.get("raw"),
            "referrer_domain": referrer_data.get("domain"),
            "referrer_category": referrer_data.get("category"),
            "utm_source": utm_data.get("utm_source"),
            "utm_medium": utm_data.get("utm_medium"),
            "utm_campaign": utm_data.get("utm_campaign"),
            "utm_term": utm_data.get("utm_term"),
            "utm_content": utm_data.get("utm_content"),
            "started_at": datetime.utcnow().isoformat(),
        }

        result = client.table("sessions").insert(payload).execute()
        logger.debug(f"Session logged: {session_id} from {geo_data.get('city') if geo_data else 'unknown'}")

    except Exception as e:
        logger.error(f"Failed to log session start: {e}")
        # Silently continue - analytics failure should never crash the app


async def log_search_event(
    search_id: str,
    session_id: str,
    query: str,
    persona: str,
    tenant_id: str,
    response_time_ms: float,
    sources_queried: list[str],
    sources_succeeded: list[str],
    total_results: int,
    pulse_status: str,
) -> None:
    """
    Log a search event (after search completes).

    Args:
        search_id: Unique search identifier
        session_id: Parent session ID
        query: The search query text
        persona: Detected persona (patient, provider, researcher)
        tenant_id: Tenant identifier
        response_time_ms: How long the search took (milliseconds)
        sources_queried: List of source names queried
        sources_succeeded: List of source names that succeeded
        total_results: Total papers/results returned
        pulse_status: PULSE status (valid, flagged, risky)
    """
    try:
        client = get_supabase_client()

        payload = {
            "id": search_id,
            "session_id": session_id,
            "tenant_id": tenant_id,
            "query": query,
            "persona": persona,
            "response_time_ms": response_time_ms,
            "sources_queried": sources_queried,
            "sources_succeeded": sources_succeeded,
            "total_results": total_results,
            "pulse_status": pulse_status,
            "created_at": datetime.utcnow().isoformat(),
        }

        result = client.table("search_logs").insert(payload).execute()
        logger.debug(f"Search logged: {search_id} ({len(sources_succeeded)}/{len(sources_queried)} sources, {total_results} results in {response_time_ms}ms)")

    except Exception as e:
        logger.error(f"Failed to log search event: {e}")


async def log_usage_event(
    tenant_id: str,
    user_id: Optional[str],
    action: str,
    metadata: Optional[dict] = None,
) -> None:
    """
    Log a generic usage event (clicks, page views, conversions, etc).

    Args:
        tenant_id: Tenant identifier
        user_id: User ID (can be None for anonymous sessions)
        action: Action type (e.g., "button_click", "form_submit", "disclaimer_accepted")
        metadata: Optional additional data (as dict, will be stored as JSONB)
    """
    try:
        client = get_supabase_client()

        payload = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "action": action,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }

        result = client.table("usage_analytics").insert(payload).execute()
        logger.debug(f"Usage event logged: {action} (user={user_id})")

    except Exception as e:
        logger.error(f"Failed to log usage event: {e}")


async def log_audit_event(
    user_id: Optional[str],
    tenant_id: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str],
    details: Optional[dict],
    ip_address: str,
) -> None:
    """
    Log an audit event (admin actions, data modifications, permission changes).

    Args:
        user_id: User who took the action (can be None for system actions)
        tenant_id: Tenant identifier
        action: audit_action enum value (e.g., "create", "update", "delete", "access")
        resource_type: Type of resource affected (e.g., "search", "user", "document")
        resource_id: ID of the resource affected
        details: Optional additional audit details (as dict, will be stored as JSONB)
        ip_address: IP address from which action was taken
    """
    try:
        client = get_supabase_client()

        payload = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
            "created_at": datetime.utcnow().isoformat(),
        }

        result = client.table("audit_trail").insert(payload).execute()
        logger.debug(f"Audit event logged: {action} on {resource_type} {resource_id} by {user_id}")

    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")


def schedule_analytics_task(coro) -> None:
    """
    Schedule an async analytics task to run in the background.
    Never blocks or raises exceptions.

    Args:
        coro: Async coroutine to schedule
    """
    try:
        asyncio.create_task(coro)
    except Exception as e:
        logger.error(f"Failed to schedule analytics task: {e}")
