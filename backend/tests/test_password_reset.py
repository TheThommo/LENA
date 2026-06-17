"""
Tests for password reset flow (POC A3).

Run with: pytest tests/test_password_reset.py -v
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import UserRole


@pytest.fixture
def client():
    return TestClient(app)


class TestForgotPassword:
    """Forgot-password must work for all registered users, not just admins."""

    @patch("app.api.routes.auth.check_rate_limit")
    @patch("app.db.supabase.get_supabase_admin_client")
    @patch("app.api.routes.auth.send_password_reset_email", new_callable=AsyncMock)
    @patch("app.api.routes.auth.UserRepository.get_by_email", new_callable=AsyncMock)
    def test_sends_reset_email_for_public_user(
        self,
        mock_get_user,
        mock_send_email,
        mock_supabase,
        _mock_rate_limit,
        client,
    ):
        user = MagicMock()
        user.id = uuid4()
        user.role = UserRole.PUBLIC_USER
        mock_get_user.return_value = user
        mock_supabase.return_value.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "researcher@example.com"},
        )

        assert response.status_code == 200
        mock_send_email.assert_awaited_once()
        assert "researcher@example.com" in mock_send_email.await_args.args[0]

    @patch("app.api.routes.auth.check_rate_limit")
    @patch("app.api.routes.auth.UserRepository.get_by_email", new_callable=AsyncMock)
    @patch("app.api.routes.auth.send_password_reset_email", new_callable=AsyncMock)
    def test_unknown_email_returns_generic_success_without_sending(
        self,
        mock_send_email,
        mock_get_user,
        _mock_rate_limit,
        client,
    ):
        mock_get_user.return_value = None

        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "nobody@example.com"},
        )

        assert response.status_code == 200
        assert "registered" in response.json()["message"].lower()
        mock_send_email.assert_not_awaited()
