"""
Analytics Models

Represents analytics data in the LENA platform.
Tracks usage events, search logs, and audit trails.
"""

from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.enums import AuditAction, PulseStatus, SearchSource


class UsageAnalyticsBase(BaseModel):
    """Base fields for usage analytics."""
    action: str = Field(..., min_length=1, max_length=100)
    metadata: Optional[dict] = None


class UsageAnalyticsCreate(UsageAnalyticsBase):
    """Fields required to create a usage event."""
    tenant_id: UUID
    user_id: Optional[UUID] = None


class UsageAnalytics(UsageAnalyticsBase):
    """Full usage analytics record from database."""
    id: UUID
    tenant_id: UUID
    user_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SearchLogBase(BaseModel):
    """Base fields for search logs."""
    response_time_ms: int = Field(..., ge=0)
    sources_queried: int = Field(..., ge=0)
    sources_succeeded: int = Field(..., ge=0)
    total_results: int = Field(..., ge=0)
    pulse_status: Optional[PulseStatus] = None


class SearchLogCreate(SearchLogBase):
    """Fields required to create a search log."""
    search_id: UUID


class SearchLog(SearchLogBase):
    """Full search log record from database."""
    id: UUID
    search_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class AuditEntryBase(BaseModel):
    """Base fields for audit entries."""
    action: AuditAction
    resource_type: Optional[str] = Field(None, max_length=100)
    resource_id: Optional[str] = Field(None, max_length=100)
    details: Optional[dict] = None
    ip_address: str = Field(..., max_length=45)


class AuditEntryCreate(AuditEntryBase):
    """Fields required to create an audit entry."""
    user_id: Optional[UUID] = None
    tenant_id: UUID


class AuditEntry(AuditEntryBase):
    """Full audit entry record from database."""
    id: UUID
    user_id: Optional[UUID] = None
    tenant_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
