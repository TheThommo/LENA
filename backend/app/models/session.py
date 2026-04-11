"""
Session Models

Represents user sessions in the LENA platform.
Sessions track access patterns, geography, and referral sources for analytics.
"""

from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SessionBase(BaseModel):
    """Base fields for session operations."""
    ip_address: str = Field(..., max_length=45)
    geo_city: Optional[str] = Field(None, max_length=100)
    geo_country: Optional[str] = Field(None, max_length=100)
    geo_lat: Optional[float] = None
    geo_lon: Optional[float] = None
    referrer: Optional[str] = Field(None, max_length=500)
    utm_source: Optional[str] = Field(None, max_length=100)
    utm_medium: Optional[str] = Field(None, max_length=100)
    utm_campaign: Optional[str] = Field(None, max_length=100)
    # Funnel tracking for anonymous sessions
    name: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    disclaimer_accepted_at: Optional[datetime] = None
    search_count: int = 0


class SessionCreate(SessionBase):
    """Fields required to create a session."""
    user_id: Optional[UUID] = None
    tenant_id: UUID


class SessionUpdate(BaseModel):
    """Partial session update (all fields optional)."""
    geo_city: Optional[str] = Field(None, max_length=100)
    geo_country: Optional[str] = Field(None, max_length=100)
    geo_lat: Optional[float] = None
    geo_lon: Optional[float] = None
    utm_source: Optional[str] = Field(None, max_length=100)
    utm_medium: Optional[str] = Field(None, max_length=100)
    utm_campaign: Optional[str] = Field(None, max_length=100)
    name: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    disclaimer_accepted_at: Optional[datetime] = None
    search_count: Optional[int] = None
    ended_at: Optional[datetime] = None


class Session(SessionBase):
    """Full session record from database."""
    id: UUID
    user_id: Optional[UUID] = None
    tenant_id: UUID
    started_at: datetime
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SessionStatus(BaseModel):
    """Status of an anonymous session."""
    session_id: UUID
    funnel_stage: str
    search_count: int
    name: Optional[str] = None
    email: Optional[str] = None
    disclaimer_accepted_at: Optional[datetime] = None
