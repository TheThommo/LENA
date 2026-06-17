"""Tests for DB Explorer table discovery and grouping."""

from app.services.db_explorer import (
    build_table_groups,
    parse_openapi_tables,
)


def test_parse_openapi_tables_extracts_public_tables():
    spec = {
        "paths": {
            "/users": {},
            "/searches": {},
            "/rpc/run_sql": {},
            "/projects": {},
        }
    }
    tables = parse_openapi_tables(spec)
    assert tables == {"users", "searches", "projects"}


def test_build_table_groups_assigns_known_and_other():
    discovered = {
        "users",
        "searches",
        "projects",
        "anon_fingerprints",
        "custom_view",
    }
    groups = build_table_groups(discovered)

    assert "users" in groups["Users and access"]
    assert "searches" in groups["Search and product"]
    assert "projects" in groups["Search and product"]
    assert "anon_fingerprints" in groups["Sessions and identity"]
    assert groups["Other collections"] == ["custom_view"]


def test_build_table_groups_no_other_when_all_grouped():
    discovered = {"users", "tenants", "searches"}
    groups = build_table_groups(discovered)
    assert "Other collections" not in groups
