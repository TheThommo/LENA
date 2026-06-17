"""
DB Explorer — discover and group Supabase public tables for HQ console.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Set

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 300

# Preferred grouping for known LENA tables. Unknown tables land in "Other collections".
TABLE_GROUPS: Dict[str, List[str]] = {
    "Users and access": [
        "users",
        "user_tenants",
        "roles",
        "permissions",
        "role_permissions",
        "user_personas",
    ],
    "Tenancy": ["tenants", "tenant_config"],
    "Billing": ["plan_tiers", "tenant_subscriptions", "trial_config"],
    "Sessions and identity": ["sessions", "anon_fingerprints"],
    "Search and product": [
        "searches",
        "search_logs",
        "search_results",
        "pulse_scores",
        "saved_results",
        "search_feedback",
        "collections",
        "collection_items",
        "projects",
    ],
    "Compliance and audit": ["audit_log", "disclaimer_acceptances", "event_log"],
    "Usage analytics": ["usage_daily", "usage_monthly", "platform_metrics"],
    "Agent and docs": [
        "agent_memory",
        "agent_guardrail_triggers",
        "tenant_documents",
        "document_tags",
        "notifications",
        "notification_preferences",
        "shared_results",
    ],
}

SENSITIVE_COLUMNS = {
    "password_hash",
    "reset_token_hash",
    "reset_token_expires_at",
    "query_vector",
}

# Tables we never expose in the explorer (PostgREST internals, etc.).
BLOCKED_TABLES = {
    "schema_migrations",
    "supabase_migrations",
}

_cache: dict | None = None


def _static_table_set() -> Set[str]:
    return {table for tables in TABLE_GROUPS.values() for table in tables}


def parse_openapi_tables(spec: dict) -> Set[str]:
    """Extract public table names from a PostgREST OpenAPI document."""
    tables: Set[str] = set()
    for path in spec.get("paths", {}):
        if not path.startswith("/"):
            continue
        name = path.strip("/").split("{")[0].rstrip("/")
        if not name or name.startswith("rpc/"):
            continue
        if name in BLOCKED_TABLES:
            continue
        tables.add(name)
    return tables


def build_table_groups(discovered: Set[str]) -> Dict[str, List[str]]:
    """Merge discovered tables with preferred grouping; ungrouped tables get their own bucket."""
    groups: Dict[str, List[str]] = {}
    assigned: Set[str] = set()

    for group_name, tables in TABLE_GROUPS.items():
        present = sorted(t for t in tables if t in discovered)
        if present:
            groups[group_name] = present
            assigned.update(present)

    unassigned = sorted(discovered - assigned - BLOCKED_TABLES)
    if unassigned:
        groups["Other collections"] = unassigned

    return groups


async def fetch_supabase_tables() -> Set[str]:
    """Live discovery via PostgREST OpenAPI (service role). Falls back to static list."""
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return _static_table_set()

    url = f"{settings.supabase_url.rstrip('/')}/rest/v1/"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Accept": "application/openapi+json",
    }

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            tables = parse_openapi_tables(response.json())
            if tables:
                return tables
    except Exception as exc:
        logger.warning("DB explorer OpenAPI discovery failed: %s", exc)

    return _static_table_set()


async def get_db_explorer_catalog(force_refresh: bool = False) -> dict:
    """Cached table catalog for HQ DB Explorer."""
    global _cache
    now = time.time()

    if (
        not force_refresh
        and _cache
        and now - _cache["fetched_at"] < CACHE_TTL_SECONDS
    ):
        return _cache

    discovered = await fetch_supabase_tables()
    groups = build_table_groups(discovered)
    allowed = set(discovered) - BLOCKED_TABLES

    _cache = {
        "fetched_at": now,
        "groups": groups,
        "allowed_tables": allowed,
        "discovered_count": len(allowed),
        "source": "live" if len(discovered) > len(_static_table_set()) // 2 else "static",
    }
    return _cache


def mask_row(row: dict) -> dict:
    masked = dict(row)
    for key in list(masked.keys()):
        if key in SENSITIVE_COLUMNS:
            masked[key] = "[redacted]"
    return masked
