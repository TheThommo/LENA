"""
Analytics Event Writer

Fire-and-forget async logging for all analytics events.
Writes to Supabase tables: sessions, search_logs, event_log, audit_log.

All writes are background tasks to never block user requests.
Errors are logged but never raised.
"""

import logging
import asyncio
from typing import Optional, Any
from datetime import datetime, timezone

from app.db.supabase import get_supabase_admin_client

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
    Update an existing session with analytics context (IP, geo, referrer, UTM).
    Sessions are created by SessionRepository; this enriches them.
    """
    try:
        client = get_supabase_admin_client()

        update_payload = {
            "ip_address": ip,
            "geo_city": geo_data.get("city") if geo_data else None,
            "geo_country": geo_data.get("country") if geo_data else None,
            "geo_lat": geo_data.get("lat") if geo_data else None,
            "geo_lon": geo_data.get("lon") if geo_data else None,
            "referrer": referrer_data.get("raw"),
            "utm_source": utm_data.get("utm_source"),
            "utm_medium": utm_data.get("utm_medium"),
            "utm_campaign": utm_data.get("utm_campaign"),
        }

        # Try to update the existing session
        result = client.table("sessions").update(update_payload).eq("id", session_id).execute()
        logger.info(f"Session enriched: {session_id} from {geo_data.get('city') if geo_data else 'unknown'}")

    except Exception as e:
        logger.error(f"Failed to enrich session: {e}")


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
    Log a search event to both `searches` and `search_logs` tables.
    """
    try:
        client = get_supabase_admin_client()

        # 1. Write to search_logs (detailed analytics)
        log_payload = {
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
        }

        client.table("search_logs").insert(log_payload).execute()
        logger.info(f"Search logged: {search_id} ({len(sources_succeeded)}/{len(sources_queried)} sources, {total_results} results in {response_time_ms:.0f}ms)")

    except Exception as e:
        logger.error(f"Failed to log search event: {e}")

    # 2. Also write to searches table (for dashboard overview counts)
    try:
        client = get_supabase_admin_client()

        search_payload = {
            "id": search_id,
            "tenant_id": tenant_id,
            "query_text": query,
            "persona_used": persona,
            "result_count": total_results,
            "duration_ms": int(response_time_ms),
            "status": pulse_status,
        }

        client.table("searches").insert(search_payload).execute()
        logger.debug(f"Search record created: {search_id}")

    except Exception as e:
        logger.error(f"Failed to write searches record: {e}")


async def log_usage_event(
    tenant_id: str,
    user_id: Optional[str],
    action: str,
    metadata: Optional[dict] = None,
    session_id: Optional[str] = None,
) -> None:
    """
    Log a generic usage/funnel event to `event_log` table.
    """
    try:
        client = get_supabase_admin_client()

        payload = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "event_type": "funnel" if action == "funnel_stage" else "usage",
            "event_name": action,
            "session_id": session_id or (metadata.get("session_id") if metadata else None),
            "persona": metadata.get("persona") if metadata else None,
            "value": metadata.get("stage") if metadata else action,
        }

        client.table("event_log").insert(payload).execute()
        logger.info(f"Event logged: {action} (user={user_id}, session={payload.get('session_id')})")

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
    Log an audit event to `audit_log` table.
    """
    try:
        client = get_supabase_admin_client()

        payload = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "old_values": details or {},
            "ip_address": ip_address,
        }

        client.table("audit_log").insert(payload).execute()
        logger.debug(f"Audit event logged: {action} on {resource_type} {resource_id} by {user_id}")

    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")


def schedule_analytics_task(coro) -> None:
    """
    Schedule an async analytics task to run in the background.
    Never blocks or raises exceptions.
    """
    try:
        asyncio.create_task(coro)
    except Exception as e:
        logger.error(f"Failed to schedule analytics task: {e}")
