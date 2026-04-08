"""
Authentication Routes

Handles user registration, login, and profile endpoints.

Endpoints:
- POST /api/auth/register - Create new user account
- POST /api/auth/login - Authenticate and get JWT token
- GET /api/auth/me - Get current user profile
- POST /api/auth/logout - Invalidate session
"""

from uuid import UUID
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, HTTPException, status, Depends, Request

from app.db.repositories.user_repo import UserRepository
from app.db.repositories.tenant_repo import TenantRepository
from app.db.repositories.subscription_repo import SubscriptionRepository, PlanRepository
from app.db.repositories.session_repo import SessionRepository
from app.models import (
    UserCreate, UserPublic, User, SessionUpdate,
    TenantCreate, SubscriptionCreate,
)
from app.models.enums import UserRole, PersonaType, SubscriptionStatus
from app.core.auth import create_access_token, require_auth
from app.core.config import settings
from app.core.tenant import detect_tenant
from app.services.funnel_tracker import track_funnel_stage

router = APIRouter(tags=["auth"])


class RegisterRequest(BaseModel):
    """Request to create a new user account."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    session_id: Optional[UUID] = None  # Optional: link existing session


class RegisterResponse(BaseModel):
    """Response after successful registration."""
    user: UserPublic
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Request to login."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Response after successful login."""
    user: UserPublic
    access_token: str
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    """Response after logout."""
    message: str


@router.post(
    "/auth/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(request: Request, body: RegisterRequest) -> RegisterResponse:
    """
    Register a new user account.

    If session_id is provided, links the account to the anonymous session's
    searches and analytics.

    Assigns user to tenant (from request subdomain/header or default "lena").
    Assigns "free" plan by default.
    Tracks "registered" funnel stage.
    """
    # Detect tenant
    tenant_slug = detect_tenant(request)

    # Get or create tenant
    tenant = await TenantRepository.get_by_slug(tenant_slug)
    if not tenant:
        # Create default tenant if it doesn't exist
        tenant_create = TenantCreate(
            name=f"{tenant_slug.capitalize()} Tenant",
            slug=tenant_slug,
            domain=request.headers.get("Host", "lena-research.com"),
        )
        tenant = await TenantRepository.create(tenant_create)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create tenant",
            )

    # Check if user already exists
    existing_user = await UserRepository.get_by_email(body.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # TODO: In production, use Supabase Auth for password hashing
    # For now, we'll create the user in the database
    # This is a placeholder - actual implementation should use Supabase Auth

    # Create user
    user_create = UserCreate(
        email=body.email,
        name=body.name,
        tenant_id=tenant.id,
        role=UserRole.PUBLIC_USER,
        persona_type=PersonaType.GENERAL,
    )
    user = await UserRepository.create(user_create)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )

    # Get or create "free" plan
    free_plan = await PlanRepository.get_by_slug("free")
    if not free_plan:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Free plan not configured",
        )

    # Create subscription
    subscription_create = SubscriptionCreate(
        tenant_id=tenant.id,
        plan_id=free_plan.id,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=365),
    )
    subscription = await SubscriptionRepository.create(subscription_create)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription",
        )

    # If session_id provided, link it to the user
    if body.session_id:
        session = await SessionRepository.get_by_id(body.session_id)
        if session:
            session_update = SessionUpdate(user_id=user.id)
            await SessionRepository.update(body.session_id, session_update)

            # Track funnel stage
            await track_funnel_stage(
                session_id=str(body.session_id),
                tenant_id=str(tenant.id),
                stage="registered",
                user_id=str(user.id),
            )

    # Create JWT token
    access_token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(tenant.id),
        role=user.role.value,
    )

    return RegisterResponse(
        user=UserPublic(**user.model_dump()),
        access_token=access_token,
    )


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
async def login(request: Request, body: LoginRequest) -> LoginResponse:
    """
    Login with email and password.

    Returns JWT access token.

    TODO: In production, verify password against Supabase Auth.
    For now, this is a placeholder.
    """
    # Find user by email
    user = await UserRepository.get_by_email(body.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # TODO: Verify password against Supabase Auth
    # For now, we skip password verification for testing

    # Update last login
    updated_user = await UserRepository.update_last_login(user.id)
    if not updated_user:
        updated_user = user

    # Create JWT token
    access_token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role.value,
    )

    return LoginResponse(
        user=UserPublic(**updated_user.model_dump()),
        access_token=access_token,
    )


@router.get(
    "/auth/me",
    response_model=UserPublic,
    status_code=status.HTTP_200_OK,
)
async def get_current_user_profile(
    user_data: dict = Depends(require_auth),
) -> UserPublic:
    """
    Get current user's profile.

    Requires valid JWT in Authorization header.
    """
    user_id = UUID(user_data.get("user_id"))
    user = await UserRepository.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserPublic(**user.model_dump())


@router.post(
    "/auth/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
)
async def logout(
    request: Request,
    user_data: dict = Depends(require_auth),
) -> LogoutResponse:
    """
    Logout (invalidate session).

    Since we use stateless JWT tokens, logout is mainly for logging
    the event. Clients should discard the token.
    """
    # Log the logout event
    # TODO: Track in audit trail if needed

    return LogoutResponse(
        message="Logged out successfully. Please discard your token.",
    )
