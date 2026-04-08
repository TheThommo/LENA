"""
Tenant Models

Represents a tenant (organization) in the LENA platform.
Multi-tenant architecture: each tenant has its own users, searches, subscriptions.
"""

from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TenantBase(BaseModel):
    """Base fields for tenant operations."""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    domain: Optional[str] = Field(None, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=500)
    primary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")


class TenantCreate(TenantBase):
    """Fields required to create a tenant."""
    pass


class TenantUpdate(BaseModel):
    """Partial tenant update (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    domain: Optional[str] = Field(None, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=500)
    primary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    config: Optional[dict] = None


class Tenant(TenantBase):
    """Full tenant record from database."""
    id: UUID
    config: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
