"""Tests for lead search enrichment helpers."""

from app.services.dashboard_queries import (
    _merge_session_context,
    _normalize_search_row,
    _rows_for_lead,
    _session_search_total,
)


def test_merge_session_context_fills_missing_fields():
    lead = {
        "session_id": None,
        "institution": None,
        "phone": None,
        "country": None,
        "city": None,
        "data_consent": False,
        "disclaimer_accepted": False,
        "source": "Registration",
    }
    session = {
        "id": "sess-1",
        "institution": "Acme Clinic",
        "phone": "+61 400 000 000",
        "geo_country": "AU",
        "geo_city": "Sydney",
        "data_consent_accepted_at": "2026-05-21T08:28:00Z",
        "disclaimer_accepted_at": "2026-05-21T08:28:00Z",
        "utm_source": "google",
        "referrer": None,
    }

    _merge_session_context(lead, session)

    assert lead["session_id"] == "sess-1"
    assert lead["institution"] == "Acme Clinic"
    assert lead["phone"] == "+61 400 000 000"
    assert lead["country"] == "AU"
    assert lead["city"] == "Sydney"
    assert lead["data_consent"] is True
    assert lead["disclaimer_accepted"] is True
    assert lead["source"] == "google"


def test_merge_session_context_does_not_overwrite_existing_values():
    lead = {
        "session_id": "existing",
        "institution": "Keep Me",
        "phone": "111",
        "country": "NZ",
        "city": "Auckland",
        "data_consent": False,
        "disclaimer_accepted": True,
        "source": "Direct",
    }
    session = {
        "id": "sess-2",
        "institution": "Other",
        "phone": "222",
        "geo_country": "AU",
        "geo_city": "Melbourne",
        "data_consent_accepted_at": "2026-05-21T08:28:00Z",
        "disclaimer_accepted_at": None,
        "utm_source": "newsletter",
    }

    _merge_session_context(lead, session)

    assert lead["session_id"] == "existing"
    assert lead["institution"] == "Keep Me"
    assert lead["phone"] == "111"
    assert lead["country"] == "NZ"
    assert lead["city"] == "Auckland"
    assert lead["data_consent"] is True
    assert lead["disclaimer_accepted"] is True
    assert lead["source"] == "Direct"


def test_normalize_search_row_from_searches_table():
    row = _normalize_search_row(
        {
            "id": "abc-123",
            "query_text": "magnesium floaters",
            "created_at": "2026-05-21T08:30:00Z",
            "result_count": 4,
            "status": "validated",
            "user_id": "user-1",
        },
        "searches",
    )
    assert row["query"] == "magnesium floaters"
    assert row["total_results"] == 4
    assert row["pulse_status"] == "validated"


def test_rows_for_lead_matches_user_and_session_searches():
    lead = {"user_id": "user-1", "session_id": "sess-1", "email": "j@test.com"}
    logs = [
        {
            "id": "1",
            "query": "by user",
            "created_at": "2026-05-21T09:00:00Z",
            "user_id": "user-1",
            "session_id": None,
        },
        {
            "id": "2",
            "query": "by session",
            "created_at": "2026-05-21T08:00:00Z",
            "user_id": None,
            "session_id": "sess-1",
        },
        {
            "id": "3",
            "query": "other user",
            "created_at": "2026-05-21T07:00:00Z",
            "user_id": "user-2",
            "session_id": None,
        },
    ]
    rows = _rows_for_lead(lead, logs, {}, {})
    assert [r["query"] for r in rows] == ["by user", "by session"]


def test_session_search_total_fallback():
    total = _session_search_total(
        "user-1",
        "j@test.com",
        {"user-1": {"search_count": 3}},
        {"j@test.com": [{"search_count": 2}]},
    )
    assert total == 5
