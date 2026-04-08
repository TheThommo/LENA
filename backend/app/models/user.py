"""
User Models

Represents users in the LENA platform.
Users belong to tenants and have role-based permissions.
"""

from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.enums import UserRole, PersonaType


class UserBase(BaseModel):
    """Base fields for user operations."""
    email: str = Field(..., min_length=5, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    role: UserRole = UserRole.PUBLIC_USER
    persona_type: PersonaType = PersonaType.GENERAL


class UserCreate(UserBase):
    """Fields required to create a user."""
    tenant_id: UUID


class UserUpdate(BaseModel):
    """Partial user update (all fields optional)."""
    email: Optional[str] = Field(None, min_length=5, max_length=255)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[UserRole] = None
    persona_type: Optional[PersonaType] = None


class UserPublic(BaseModel):
    """Safe user info for public endpoints (no sensitive fields)."""
    id: UUID
    email: str
    name: str
    role: UserRole
    persona_type: PersonaType
    tenant_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class User(UserPublic):
    """Full user record from database."""
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserTenantBase(BaseModel):
    """Base fields for user-tenant relationship."""
    user_id: UUID
    tenant_id: UUID
    role: UserRole


class UserTenantCreate(UserTenantBase):
    """Fields required to create a user-tenant relationship."""
    pass


class UserTenant(UserTenantBase):
    """User-tenant relationship record."""
    joined_at: datetime

    class Config:
        from_attributes = True
