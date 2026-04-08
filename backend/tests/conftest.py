"""
Pytest Configuration and Shared Fixtures for LENA Test Suite

Provides:
- Mock Supabase client (prevents hitting real DB)
- Mock httpx client (prevents hitting real APIs)
- Test settings override
- Sample data factories
- FastAPI test client
"""

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Generator

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.pulse_engine import SourceResult


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Override test settings."""
    test_settings = settings.copy(update={
        "jwt_secret_key": "test-secret-key-for-testing",
        "jwt_algorithm": "HS256",
        "jwt_expiration_minutes": 60,
        "cors_origins": "http://localhost:3000,http://localhost:8000",
    })
    return test_settings


@pytest.fixture
def mock_supabase():
    """Mock Supabase client that doesn't hit real DB."""
    with patch("app.db.supabase.get_supabase_client") as mock:
        client = MagicMock()
        # Default: return empty results
        client.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock.return_value = client
        yield client


@pytest.fixture
def mock_httpx():
    """Mock httpx.AsyncClient for external API calls."""
    with patch("httpx.AsyncClient") as mock_client:
        instance = AsyncMock()
        mock_client.return_value.__aenter__ = AsyncMock(return_value=instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
        instance.get = AsyncMock(
            return_value=MagicMock(status_code=200, text="", json=lambda: {})
        )
        instance.post = AsyncMock(
            return_value=MagicMock(status_code=200, text="", json=lambda: {})
        )
        yield instance


@pytest.fixture
def test_client() -> TestClient:
    """FastAPI TestClient for route testing."""
    return TestClient(app)


# ===== Sample Data Factories =====

@pytest.fixture
def create_test_user():
    """Factory: create a test user dict."""
    def _create(user_id=None, tenant_id=None, role="public_user", email=None):
        return {
            "user_id": user_id or str(uuid4()),
            "tenant_id": tenant_id or "lena",
            "role": role,
            "email": email or f"test_{uuid4().hex[:8]}@example.com",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    return _create


@pytest.fixture
def create_test_session():
    """Factory: create a test session dict."""
    def _create(
        session_id=None,
        tenant_id=None,
        user_id=None,
        disclaimer_accepted=True,
        search_count=0,
    ):
        return {
            "id": session_id or str(uuid4()),
            "tenant_id": tenant_id or "lena",
            "user_id": user_id,
            "search_count": search_count,
            "disclaimer_accepted_at": (
                datetime.now(timezone.utc).isoformat() if disclaimer_accepted else None
            ),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    return _create


@pytest.fixture
def create_test_search_result():
    """Factory: create a test SourceResult."""
    def _create(
        source_name="pubmed",
        title=None,
        summary=None,
        keywords=None,
        relevance_score=0.85,
        is_retracted=False,
    ):
        return SourceResult(
            source_name=source_name,
            title=title or f"Sample {source_name} paper on testing",
            summary=summary or "This is a test summary of medical research findings.",
            url=f"https://example.com/{uuid4()}",
            doi=f"10.1234/test.{uuid4().hex[:6]}",
            year=2024,
            relevance_score=relevance_score,
            keywords=keywords or ["test", "sample", "research"],
            is_retracted=is_retracted,
        )
    return _create


@pytest.fixture
def create_test_auth_token():
    """Factory: create a valid JWT token."""
    from app.core.auth import create_access_token

    def _create(user_id=None, tenant_id=None, role="public_user"):
        return create_access_token(
            user_id=user_id or str(uuid4()),
            tenant_id=tenant_id or "lena",
            role=role,
            expires_delta=timedelta(minutes=60),
        )
    return _create


@pytest.fixture
def create_test_session_token():
    """Factory: create a session token (for freemium funnel)."""
    def _create(session_id=None):
        session_id = session_id or str(uuid4())
        return f"session_{session_id}"
    return _create


# ===== Auto-clear fixtures =====

@pytest.fixture(autouse=True)
def clear_cache():
    """Auto-clear result cache before each test."""
    from app.services.result_cache import clear_cache as clear_fn
    clear_fn()
    yield
    clear_fn()


@pytest.fixture(autouse=True)
def reset_geolocation_cache():
    """Auto-clear geolocation cache before each test."""
    import app.services.geolocation as geo_module
    geo_module._geo_cache.clear()
    yield
    geo_module._geo_cache.clear()
