"""
Repository Layer

Data access layer for all LENA tables.
Repositories handle CRUD operations and return Pydantic models.
"""

from app.db.repositories.tenant_repo import TenantRepository
from app.db.repositories.user_repo import UserRepository, UserTenantRepository
from app.db.repositories.session_repo import SessionRepository
from app.db.repositories.search_repo import SearchRepository, SearchResultRepository
from app.db.repositories.analytics_repo import (
    UsageAnalyticsRepository,
    SearchLogRepository,
    AuditTrailRepository,
)
from app.db.repositories.subscription_repo import PlanRepository, SubscriptionRepository

__all__ = [
    "TenantRepository",
    "UserRepository",
    "UserTenantRepository",
    "SessionRepository",
    "SearchRepository",
    "SearchResultRepository",
    "UsageAnalyticsRepository",
    "SearchLogRepository",
    "AuditTrailRepository",
    "PlanRepository",
    "SubscriptionRepository",
]
