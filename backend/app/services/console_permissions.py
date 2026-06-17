"""
HQ console permission helpers.

Maps LENA user roles to a console role hierarchy and nav visibility.
Uses index comparison per the universal HQ build prompt - never compare
role strings directly in permission logic.
"""

from typing import Dict, TypedDict

ROLE_HIERARCHY = ("owner", "admin", "support", "read_only")

LENA_ROLE_TO_CONSOLE: Dict[str, str] = {
    "platform_admin": "owner",
    "tenant_admin": "admin",
    "practitioner": "support",
    "researcher": "support",
    "public_user": "read_only",
}


class ConsoleNavVisibility(TypedDict):
    command_center: bool
    analytics: bool
    revenue: bool
    tenants: bool
    users: bool
    subscriptions: bool
    invoices: bool
    llm_costs: bool
    system_health: bool
    product_admin: bool
    growth: bool
    audit_log: bool
    business_goals: bool
    db_explorer: bool
    settings: bool


def role_level(console_role: str) -> int:
    try:
        return ROLE_HIERARCHY.index(console_role)
    except ValueError:
        return len(ROLE_HIERARCHY)


def has_min_level(console_role: str, required_level: int) -> bool:
    return role_level(console_role) <= required_level


def map_lena_role(lena_role: str) -> str:
    return LENA_ROLE_TO_CONSOLE.get(lena_role or "", "read_only")


def console_nav(console_role: str) -> ConsoleNavVisibility:
    """Return nav visibility flags for a console role tier."""
    level = role_level(console_role)
    return ConsoleNavVisibility(
        command_center=has_min_level(console_role, role_level("read_only")),
        analytics=has_min_level(console_role, role_level("read_only")),
        revenue=has_min_level(console_role, role_level("read_only")),
        tenants=has_min_level(console_role, role_level("support")),
        users=has_min_level(console_role, role_level("support")),
        subscriptions=has_min_level(console_role, role_level("admin")),
        invoices=has_min_level(console_role, role_level("admin")),
        llm_costs=has_min_level(console_role, role_level("admin")),
        system_health=has_min_level(console_role, role_level("admin")),
        product_admin=has_min_level(console_role, role_level("support")),
        growth=has_min_level(console_role, role_level("read_only")),
        audit_log=has_min_level(console_role, role_level("admin")),
        business_goals=has_min_level(console_role, role_level("read_only")),
        db_explorer=has_min_level(console_role, role_level("owner")),
        settings=has_min_level(console_role, role_level("admin")),
    )


def can_access_hq(console_role: str) -> bool:
    """Minimum tier allowed to open HQ at all."""
    return has_min_level(console_role, role_level("support"))
