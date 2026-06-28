"""Tests for entitlements / full-access bypass."""

from app.core.config import settings
from app.core.entitlements import is_bypass_email, project_limit_upgrade_message


def test_owner_email_bypassed():
    assert is_bypass_email("mark.e.s.thompson@gmail.com")


def test_lauren_email_bypassed():
    assert is_bypass_email("lauren@capitalfive.co.za")


def test_explicit_bypass_email_only():
    assert not is_bypass_email("lauren@gmail.com")
    assert not is_bypass_email("random.user@gmail.com")


def test_bypass_user_emails_config_includes_admin():
    assert "mark.e.s.thompson@gmail.com" in settings.bypass_user_email_set


def test_upgrade_message_is_welcoming_not_error():
    msg = project_limit_upgrade_message("Hypertension")
    assert "Hypertension" in msg
    assert "402" not in msg
    assert "failed" not in msg.lower()
    assert "Pro" in msg
