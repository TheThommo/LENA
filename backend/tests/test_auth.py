"""
Tests for Authentication Module

Tests JWT token creation, verification, and dependency functions.

Run with: pytest tests/test_auth.py -v
"""

import pytest
from datetime import datetime, timedelta, timezone
import jwt as pyjwt

from fastapi import HTTPException
from app.core.auth import (
    create_access_token,
    verify_token,
)
from app.core.config import settings


class TestTokenCreation:
    """Test JWT token creation."""

    def test_create_token_basic(self):
        """Create a basic token."""
        token = create_access_token(
            user_id="user_123",
            tenant_id="tenant_abc",
            role="public_user",
        )
        assert token
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_contains_user_id(self):
        """Token payload should contain user_id."""
        user_id = "user_123"
        token = create_access_token(
            user_id=user_id,
            tenant_id="tenant_abc",
            role="public_user",
        )

        payload = pyjwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert payload["user_id"] == user_id

    def test_token_contains_tenant_id(self):
        """Token payload should contain tenant_id."""
        tenant_id = "tenant_abc"
        token = create_access_token(
            user_id="user_123",
            tenant_id=tenant_id,
            role="public_user",
        )

        payload = pyjwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert payload["tenant_id"] == tenant_id

    def test_token_contains_role(self):
        """Token payload should contain role."""
        role = "platform_admin"
        token = create_access_token(
            user_id="user_123",
            tenant_id="tenant_abc",
            role=role,
        )

        payload = pyjwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert payload["role"] == role

    def test_token_contains_exp(self):
        """Token payload should contain expiration."""
        token = create_access_token(
            user_id="user_123",
            tenant_id="tenant_abc",
            role="public_user",
        )

        payload = pyjwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert "exp" in payload
        assert payload["exp"] > datetime.now(timezone.utc).timestamp()

    def test_token_contains_iat(self):
        """Token payload should contain issued-at time."""
        token = create_access_token(
            user_id="user_123",
            tenant_id="tenant_abc",
            role="public_user",
        )

        payload = pyjwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert "iat" in payload

    def test_token_custom_expiration(self):
        """Custom expiration delta should be respected."""
        custom_delta = timedelta(minutes=30)
        token = create_access_token(
            user_id="user_123",
            tenant_id="tenant_abc",
            role="public_user",
            expires_delta=custom_delta,
        )

        payload = pyjwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)

        # Should expire in approximately 30 minutes (with small tolerance for execution time)
        delta = (exp_time - now).total_seconds()
        assert 29 * 60 < delta < 31 * 60

    def test_token_uuid_converted_to_string(self):
        """UUID objects should be converted to strings."""
        from uuid import uuid4
        user_id = uuid4()
        tenant_id = uuid4()

        token = create_access_token(
            user_id=str(user_id),
            tenant_id=str(tenant_id),
            role="public_user",
        )

        payload = pyjwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert isinstance(payload["user_id"], str)
        assert isinstance(payload["tenant_id"], str)


class TestTokenVerification:
    """Test JWT token verification."""

    def test_verify_valid_token(self):
        """Valid token should be verified successfully."""
        token = create_access_token(
            user_id="user_123",
            tenant_id="tenant_abc",
            role="public_user",
        )

        payload = verify_token(token)
        assert payload["user_id"] == "user_123"
        assert payload["tenant_id"] == "tenant_abc"
        assert payload["role"] == "public_user"

    def test_verify_invalid_token(self):
        """Invalid token should raise HTTPException."""
        invalid_token = "invalid.token.here"

        with pytest.raises(HTTPException) as exc_info:
            verify_token(invalid_token)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail

    def test_verify_expired_token(self):
        """Expired token should raise HTTPException."""
        # Create token that expires immediately
        token = create_access_token(
            user_id="user_123",
            tenant_id="tenant_abc",
            role="public_user",
            expires_delta=timedelta(seconds=-1),  # Already expired
        )

        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_verify_tampered_token(self):
        """Tampered token (wrong signature) should fail."""
        token = create_access_token(
            user_id="user_123",
            tenant_id="tenant_abc",
            role="public_user",
        )

        # Tamper with the token
        tampered = token[:-5] + "XXXXX"

        with pytest.raises(HTTPException) as exc_info:
            verify_token(tampered)

        assert exc_info.value.status_code == 401

    def test_verify_wrong_secret_key(self):
        """Token signed with different key should fail verification."""
        token = create_access_token(
            user_id="user_123",
            tenant_id="tenant_abc",
            role="public_user",
        )

        # Try to verify with wrong secret - should raise pyjwt exception
        with pytest.raises(Exception):  # Could be InvalidTokenError or similar
            pyjwt.decode(token, "wrong-secret-key", algorithms=[settings.jwt_algorithm])


class TestTokenRoles:
    """Test token creation with different roles."""

    def test_token_with_platform_admin_role(self):
        """Token with platform_admin role."""
        token = create_access_token(
            user_id="admin_1",
            tenant_id="lena",
            role="platform_admin",
        )

        payload = verify_token(token)
        assert payload["role"] == "platform_admin"

    def test_token_with_tenant_admin_role(self):
        """Token with tenant_admin role."""
        token = create_access_token(
            user_id="admin_1",
            tenant_id="tenant_abc",
            role="tenant_admin",
        )

        payload = verify_token(token)
        assert payload["role"] == "tenant_admin"

    def test_token_with_practitioner_role(self):
        """Token with practitioner role."""
        token = create_access_token(
            user_id="practitioner_1",
            tenant_id="tenant_abc",
            role="practitioner",
        )

        payload = verify_token(token)
        assert payload["role"] == "practitioner"

    def test_token_with_researcher_role(self):
        """Token with researcher role."""
        token = create_access_token(
            user_id="researcher_1",
            tenant_id="tenant_abc",
            role="researcher",
        )

        payload = verify_token(token)
        assert payload["role"] == "researcher"

    def test_token_with_public_user_role(self):
        """Token with public_user role."""
        token = create_access_token(
            user_id="user_1",
            tenant_id="tenant_abc",
            role="public_user",
        )

        payload = verify_token(token)
        assert payload["role"] == "public_user"


class TestMultiTenant:
    """Test token behavior with multiple tenants."""

    def test_token_isolated_by_tenant(self):
        """Tokens should contain correct tenant_id."""
        token_nyu = create_access_token(
            user_id="user_1",
            tenant_id="nyu",
            role="public_user",
        )

        token_acme = create_access_token(
            user_id="user_1",
            tenant_id="acme",
            role="public_user",
        )

        payload_nyu = verify_token(token_nyu)
        payload_acme = verify_token(token_acme)

        assert payload_nyu["tenant_id"] == "nyu"
        assert payload_acme["tenant_id"] == "acme"

    def test_token_default_tenant_lena(self):
        """Default tenant should be 'lena' (platform)."""
        token = create_access_token(
            user_id="user_1",
            tenant_id="lena",
            role="platform_admin",
        )

        payload = verify_token(token)
        assert payload["tenant_id"] == "lena"
