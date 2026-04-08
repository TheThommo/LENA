"""
Pydantic Enums for LENA

These match the Supabase enum types exactly.
All enum values are lowercase to match database constraints.
"""

from enum import Enum


class UserRole(str, Enum):
    """User roles within a tenant."""
    PLATFORM_ADMIN = "platform_admin"
    TENANT_ADMIN = "tenant_admin"
    PRACTITIONER = "practitioner"
    RESEARCHER = "researcher"
    PUBLIC_USER = "public_user"


class PersonaType(str, Enum):
    """User persona types for response personalization."""
    MEDICAL_STUDENT = "medical_student"
    CLINICIAN = "clinician"
    PHARMACIST = "pharmacist"
    RESEARCHER = "researcher"
    LECTURER = "lecturer"
    PHYSIOTHERAPIST = "physiotherapist"
    PATIENT = "patient"
    GENERAL = "general"


class PlanType(str, Enum):
    """Subscription plan types."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class SearchSource(str, Enum):
    """Data sources for search results."""
    PUBMED = "pubmed"
    CLINICAL_TRIALS = "clinical_trials"
    COCHRANE = "cochrane"
    WHO_IRIS = "who_iris"
    CDC = "cdc"


class PulseStatus(str, Enum):
    """PULSE validation status for search results."""
    VALIDATED = "validated"
    EDGE_CASE = "edge_case"
    INSUFFICIENT_VALIDATION = "insufficient_validation"
    PENDING = "pending"


class SubscriptionStatus(str, Enum):
    """Subscription lifecycle statuses."""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    TRIALING = "trialing"


class AuditAction(str, Enum):
    """Actions tracked in the audit trail."""
    LOGIN = "login"
    LOGOUT = "logout"
    SEARCH = "search"
    VIEW_RESULT = "view_result"
    EXPORT = "export"
    ADMIN_ACTION = "admin_action"
    SETTINGS_CHANGE = "settings_change"


class TriggerType(str, Enum):
    """Types of triggers for scheduled tasks."""
    ROW_INSERT = "row_insert"
    ROW_UPDATE = "row_update"
    SCHEDULED = "scheduled"
    MANUAL = "manual"
