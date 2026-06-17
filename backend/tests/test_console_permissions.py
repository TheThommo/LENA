"""Tests for HQ console permissions."""

from app.services.console_permissions import (
    ROLE_HIERARCHY,
    console_nav,
    has_min_level,
    map_lena_role,
    role_level,
)


def test_role_level_uses_hierarchy_index():
    assert role_level("owner") < role_level("admin")
    assert role_level("admin") < role_level("support")
    assert role_level("support") < role_level("read_only")


def test_has_min_level_uses_index_not_string_compare():
    assert has_min_level("owner", role_level("admin")) is True
    assert has_min_level("read_only", role_level("admin")) is False


def test_map_lena_platform_admin_to_owner():
    assert map_lena_role("platform_admin") == "owner"


def test_console_nav_db_explorer_owner_only():
    owner_nav = console_nav("owner")
    support_nav = console_nav("support")
    assert owner_nav["db_explorer"] is True
    assert support_nav["db_explorer"] is False
    assert support_nav["users"] is True
