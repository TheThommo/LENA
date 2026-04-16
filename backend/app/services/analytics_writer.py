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
        logger.error("Failed to enrich session", exc_info=True)


async def _session_exists(client, session_id: str) -> bool:
    """Cheap existence check so we don't violate search_logs.session_id FK."""
    try:
        resp = client.table("sessions").select("id").eq("id", session_id).limit(1).execute()
        return bool(resp.data)
    except Exception:
        return False


async def log_search_event(
    search_id: str,
    session_id: Optional[str],
    query: str,
    persona: str,
    tenant_id: str,
    response_time_ms: float,
    sources_queried: list[str],
    sources_succeeded: list[str],
    total_results: int,
    pulse_status: str,
    user_id: Optional[str] = None,
    llm_usage: Optional[dict] = None,
) -> None:
    """
    Log a search event to `search_logs` (detailed) and `searches` (rollup).
    user_id is None for anonymous searches; session_id is None (or a not-in-DB
    placeholder) for authenticated searches that bypass the session flow.

    On failure we log the exact payload so the next schema drift is debuggable.
    """
    client = get_supabase_admin_client()

    # Only attach session_id if it's a real row — otherwise the FK rejects the
    # insert and the whole record is lost. Authenticated users legitimately
    # have no session_id at this point.
    real_session_id: Optional[str] = None
    if session_id:
        if await _session_exists(client, session_id):
            real_session_id = session_id

    # 1. Write to search_logs (full analytics row)
    log_payload: dict[str, Any] = {
        "id": search_id,
        "session_id": real_session_id,
        "tenant_id": tenant_id,
        "query": query,
        "persona": persona,
        "response_time_ms": response_time_ms,
        "sources_queried": sources_queried,
        "sources_succeeded": sources_succeeded,
        "total_results": total_results,
        "pulse_status": pulse_status,
    }
    if user_id:
        log_payload["user_id"] = user_id
    if llm_usage:
        # Migration add_cost_columns_to_search_logs added these columns.
        # Writing them here is how the Cost Intelligence admin view gets data.
        log_payload["llm_model"] = llm_usage.get("model")
        log_payload["llm_prompt_tokens"] = llm_usage.get("prompt_tokens")
        log_payload["llm_completion_tokens"] = llm_usage.get("completion_tokens")
        log_payload["llm_cost_micros"] = llm_usage.get("cost_micros")

    try:
        client.table("search_logs").insert(log_payload).execute()
        logger.info(
            "search_logs write ok: search_id=%s sources=%d/%d results=%d ms=%.0f",
            search_id, len(sources_succeeded), len(sources_queried),
            total_results, response_time_ms,
        )
    except Exception:
        logger.error(
            "search_logs insert FAILED — payload=%s", log_payload, exc_info=True
        )

    # 2. Write to searches table (rollup for dashboard counts)
    search_payload: dict[str, Any] = {
        "id": search_id,
        "tenant_id": tenant_id,
        "query_text": query,
        "persona_used": persona,
        "result_count": total_results,
        "duration_ms": int(response_time_ms),
        "status": pulse_status,
    }
    if user_id:
        search_payload["user_id"] = user_id

    try:
        client.table("searches").insert(search_payload).execute()
        logger.debug("searches write ok: search_id=%s", search_id)
    except Exception:
        logger.error(
            "searches insert FAILED — payload=%s", search_payload, exc_info=True
        )


async def log_usage_event(
    tenant_id: str,
    user_id: Optional[str],
    action: str,
    metadata: Optional[dict] = None,
    session_id: Optional[str] = None,
) -> None:
    """
    Log a generic usage/funnel event to `event_log` table.

    For funnel events, the funnel stage (e.g. "landed", "registered") goes
    into `feature_name` (text). `value` is numeric and left NULL unless the
    caller passes a metadata["numeric_value"]. The old behaviour of dumping
    the stage string into `value` broke every funnel insert with
    "invalid input syntax for type numeric".
    """
    try:
        client = get_supabase_admin_client()

        md = metadata or {}
        is_funnel = action == "funnel_stage"
        stage = md.get("stage")

        payload: dict[str, Any] = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "event_type": "funnel" if is_funnel else "usage",
            "event_name": stage if is_funnel and stage else action,
            "feature_name": stage if is_funnel else md.get("feature_name"),
            "session_id": session_id or md.get("session_id"),
            "persona": md.get("persona"),
        }

        numeric = md.get("numeric_value")
        if isinstance(numeric, (int, float)):
            payload["value"] = numeric

        client.table("event_log").insert(payload).execute()
        logger.info(f"Event logged: {payload['event_name']} (user={user_id}, session={payload.get('session_id')})")

    except Exception as e:
        logger.error("Failed to log usage event", exc_info=True)


_PLACEHOLDER_TENANT = "00000000-0000-0000-0000-000000000000"
_cached_default_tenant_id: Optional[str] = None


def _resolve_audit_tenant_id(client, tenant_id: str) -> Optional[str]:
    """
    Audit rows must point at a real tenants.id. Callers that can't resolve
    a tenant (e.g. login with unknown email) historically passed the all-zeros
    UUID, which violated the FK and dropped the row. Swap that for the real
    "default" tenant id, cached per-process.
    """
    global _cached_default_tenant_id
    if tenant_id and tenant_id != _PLACEHOLDER_TENANT:
        return tenant_id
    if _cached_default_tenant_id:
        return _cached_default_tenant_id
    try:
        resp = client.table("tenants").select("id").eq("slug", "default").limit(1).execute()
        if resp.data:
            _cached_default_tenant_id = resp.data[0]["id"]
            return _cached_default_tenant_id
    except Exception:
        logger.error("Could not resolve default tenant for audit log", exc_info=True)
    return None


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

        resolved_tenant = _resolve_audit_tenant_id(client, tenant_id)
        if not resolved_tenant:
            logger.warning(
                "Dropping audit event (no tenant could be resolved): action=%s", action
            )
            return

        payload = {
            "user_id": user_id,
            "tenant_id": resolved_tenant,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "old_values": details or {},
            "ip_address": ip_address,
        }

        client.table("audit_log").insert(payload).execute()
        logger.debug(f"Audit event logged: {action} on {resource_type} {resource_id} by {user_id}")

    except Exception as e:
        logger.error("Failed to log audit event", exc_info=True)


def schedule_analytics_task(coro) -> None:
    """
    Schedule an async analytics task to run in the background.
    Never blocks or raises exceptions.
    """
    try:
        asyncio.create_task(coro)
    except Exception as e:
        logger.error("Failed to schedule analytics task", exc_info=True)
