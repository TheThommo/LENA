"""Tests for lead search enrichment helpers."""

from app.services.dashboard_queries import _merge_session_context


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
