"""
LENA Pydantic Models

Re-exports all model classes for clean imports across the application.
Models are organized by domain: enums, tenants, users, sessions, searches, analytics, subscriptions.
"""

# Enums
from app.models.enums import (
    UserRole,
    PersonaType,
    PlanType,
    SearchSource,
    PulseStatus,
    SubscriptionStatus,
    AuditAction,
    TriggerType,
)

# Tenant models
from app.models.tenant import (
    TenantBase,
    TenantCreate,
    TenantUpdate,
    Tenant,
)

# User models
from app.models.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserPublic,
    User,
    UserTenantBase,
    UserTenantCreate,
    UserTenant,
)

# Session models
from app.models.session import (
    SessionBase,
    SessionCreate,
    SessionUpdate,
    Session,
    SessionStatus,
)

# Search models
from app.models.search import (
    SearchBase,
    SearchCreate,
    Search,
    SearchResultBase,
    SearchResultCreate,
    SearchResult,
    SearchWithResults,
)

# Analytics models
from app.models.analytics import (
    UsageAnalyticsBase,
    UsageAnalyticsCreate,
    UsageAnalytics,
    SearchLogBase,
    SearchLogCreate,
    SearchLog,
    AuditEntryBase,
    AuditEntryCreate,
    AuditEntry,
)

# Subscription models
from app.models.subscription import (
    PlanBase,
    PlanCreate,
    PlanUpdate,
    Plan,
    SubscriptionBase,
    SubscriptionCreate,
    SubscriptionUpdate,
    Subscription,
    SubscriptionWithPlan,
)

__all__ = [
    # Enums
    "UserRole",
    "PersonaType",
    "PlanType",
    "SearchSource",
    "PulseStatus",
    "SubscriptionStatus",
    "AuditAction",
    "TriggerType",
    # Tenants
    "TenantBase",
    "TenantCreate",
    "TenantUpdate",
    "Tenant",
    # Users
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserPublic",
    "User",
    "UserTenantBase",
    "UserTenantCreate",
    "UserTenant",
    # Sessions
    "SessionBase",
    "SessionCreate",
    "SessionUpdate",
    "Session",
    "SessionStatus",
    # Searches
    "SearchBase",
    "SearchCreate",
    "Search",
    "SearchResultBase",
    "SearchResultCreate",
    "SearchResult",
    "SearchWithResults",
    # Analytics
    "UsageAnalyticsBase",
    "UsageAnalyticsCreate",
    "UsageAnalytics",
    "SearchLogBase",
    "SearchLogCreate",
    "SearchLog",
    "AuditEntryBase",
    "AuditEntryCreate",
    "AuditEntry",
    # Subscriptions
    "PlanBase",
    "PlanCreate",
    "PlanUpdate",
    "Plan",
    "SubscriptionBase",
    "SubscriptionCreate",
    "SubscriptionUpdate",
    "Subscription",
    "SubscriptionWithPlan",
]
