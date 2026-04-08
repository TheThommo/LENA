"""
Subscription Models

Represents subscription plans and tenant subscriptions.
Tracks billing, features, and usage limits.
"""

from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.enums import PlanType, SubscriptionStatus


class PlanBase(BaseModel):
    """Base fields for subscription plans."""
    name: str = Field(..., min_length=1, max_length=100)
    slug: PlanType
    price_monthly: float = Field(..., ge=0.0)
    search_limit_monthly: int = Field(..., ge=0)
    features: Optional[dict] = None
    is_active: bool = True


class PlanCreate(PlanBase):
    """Fields required to create a plan."""
    pass


class PlanUpdate(BaseModel):
    """Partial plan update (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    price_monthly: Optional[float] = Field(None, ge=0.0)
    search_limit_monthly: Optional[int] = Field(None, ge=0)
    features: Optional[dict] = None
    is_active: Optional[bool] = None


class Plan(PlanBase):
    """Full plan record from database."""
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionBase(BaseModel):
    """Base fields for subscriptions."""
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    current_period_start: datetime
    current_period_end: datetime


class SubscriptionCreate(SubscriptionBase):
    """Fields required to create a subscription."""
    tenant_id: UUID
    plan_id: UUID


class SubscriptionUpdate(BaseModel):
    """Partial subscription update (all fields optional)."""
    status: Optional[SubscriptionStatus] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    plan_id: Optional[UUID] = None


class Subscription(SubscriptionBase):
    """Full subscription record from database."""
    id: UUID
    tenant_id: UUID
    plan_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionWithPlan(Subscription):
    """Subscription with its associated plan details."""
    plan: Plan
