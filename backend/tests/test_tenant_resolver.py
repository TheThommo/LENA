"""Tests for tenant resolution used by search logging."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.tenant_resolver import get_default_tenant_id, resolve_tenant_id_for_user


@pytest.mark.asyncio
async def test_resolve_tenant_falls_back_to_users_tenant_id():
    user_id = str(uuid4())
    tenant_id = str(uuid4())

    fake_user = MagicMock()
    fake_user.tenant_id = tenant_id

    with patch(
        "app.db.repositories.user_repo.UserTenantRepository.get_by_user_id",
        new_callable=AsyncMock,
        return_value=[],
    ), patch(
        "app.db.repositories.user_repo.UserRepository.get_by_id",
        new_callable=AsyncMock,
        return_value=fake_user,
    ):
        resolved = await resolve_tenant_id_for_user(user_id)

    assert resolved == tenant_id


@pytest.mark.asyncio
async def test_resolve_tenant_prefers_user_tenants():
    user_id = str(uuid4())
    tenant_id = str(uuid4())

    membership = MagicMock()
    membership.tenant_id = tenant_id

    with patch(
        "app.db.repositories.user_repo.UserTenantRepository.get_by_user_id",
        new_callable=AsyncMock,
        return_value=[membership],
    ):
        resolved = await resolve_tenant_id_for_user(user_id)

    assert resolved == tenant_id


def test_get_default_tenant_id_caches(monkeypatch):
    import app.services.tenant_resolver as mod

    mod._cached_default_tenant_id = None
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": "tenant-default"}]
    )
    monkeypatch.setattr(mod, "get_supabase_admin_client", lambda: client)

    assert get_default_tenant_id() == "tenant-default"
    assert get_default_tenant_id() == "tenant-default"
