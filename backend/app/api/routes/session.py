"""
Anonymous Session Routes

Handles the freemium funnel flow for anonymous visitors:
1. POST /api/session/start - Create anonymous session
2. POST /api/session/{session_id}/name - Capture name
3. POST /api/session/{session_id}/disclaimer - Accept medical disclaimer
4. POST /api/session/{session_id}/email - Capture email
5. GET /api/session/{session_id}/status - Get current funnel status
"""

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from fastapi import APIRouter, HTTPException, status, Request

from app.db.repositories.session_repo import SessionRepository
from app.models import SessionCreate, SessionUpdate, SessionStatus
from app.core.tenant import detect_tenant
from app.services.funnel_tracker import track_funnel_stage

router = APIRouter(tags=["session"])


class SessionStartRequest(BaseModel):
    """Request to start an anonymous session."""
    pass


class SessionStartResponse(BaseModel):
    """Response with session ID and initial token."""
    session_id: UUID
    session_token: str  # JWT token for this session


class NameCaptureRequest(BaseModel):
    """Request to capture visitor name."""
    name: str = Field(..., min_length=1, max_length=255)


class DisclaimerAcceptanceRequest(BaseModel):
    """Request to accept medical disclaimer."""
    accepted: bool = Field(...)


class DisclaimerAcceptanceResponse(BaseModel):
    """Response with session token after disclaimer acceptance."""
    session_token: str
    message: str


class EmailCaptureRequest(BaseModel):
    """Request to capture visitor email and optional CRM data."""
    email: EmailStr
    institution: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    city: str | None = Field(None, max_length=100)
    country: str | None = Field(None, max_length=100)
    data_consent_accepted: bool = Field(False)


class FunnelStageResponse(BaseModel):
    """Response showing current funnel stage."""
    session_id: UUID
    funnel_stage: str
    search_count: int
    name: str | None
    email: str | None


@router.post(
    "/session/start",
    response_model=SessionStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_session(request: Request) -> SessionStartResponse:
    """
    Start an anonymous session.

    This is the first step in the freemium funnel.
    Creates a session record and returns a session_id.

    Analytics: Tracks "landed" funnel stage.
    """
    from app.db.repositories.tenant_repo import TenantRepository

    # Extract tenant and IP
    tenant_slug = detect_tenant(request)
    ip_address = request.state.ip_address
    geo_data = request.state.geo_data or {}

    # Get or create tenant
    tenant = await TenantRepository.get_by_slug(tenant_slug)
    if not tenant:
        # Create default tenant if needed
        from app.models import TenantCreate
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

    # Build session create
    session_create = SessionCreate(
        user_id=None,
        tenant_id=tenant.id,
        ip_address=ip_address,
        geo_city=geo_data.get("city"),
        geo_country=geo_data.get("country"),
        geo_lat=geo_data.get("lat"),
        geo_lon=geo_data.get("lon"),
        referrer=request.state.referrer_data.get("referrer") if request.state.referrer_data else None,
        utm_source=request.state.utm_data.get("utm_source") if request.state.utm_data else None,
        utm_medium=request.state.utm_data.get("utm_medium") if request.state.utm_data else None,
        utm_campaign=request.state.utm_data.get("utm_campaign") if request.state.utm_data else None,
    )

    # Create session in DB
    session = await SessionRepository.create(session_create)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session",
        )

    # Track funnel stage
    await track_funnel_stage(
        session_id=str(session.id),
        tenant_id=str(session.tenant_id),
        stage="landed",
    )

    # Create a session token (simple JWT-like token containing session_id)
    # In a real app, this would be a proper JWT
    session_token = f"session_{session.id}"

    return SessionStartResponse(
        session_id=session.id,
        session_token=session_token,
    )


@router.post(
    "/session/{session_id}/name",
    response_model=SessionStatus,
    status_code=status.HTTP_200_OK,
)
async def capture_name(
    session_id: UUID,
    body: NameCaptureRequest,
) -> SessionStatus:
    """
    Capture visitor name.

    Step 2 in the freemium funnel.
    Stores name on the session.

    Analytics: Tracks "name_captured" funnel stage.
    """
    # Get session
    session = await SessionRepository.get_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Update name
    session_update = SessionUpdate(name=body.name)
    updated_session = await SessionRepository.update(session_id, session_update)
    if not updated_session:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update session",
        )

    # Track funnel stage
    await track_funnel_stage(
        session_id=str(session_id),
        tenant_id=str(session.tenant_id),
        stage="name_captured",
        metadata={"name": body.name},
    )

    return SessionStatus(
        session_id=session_id,
        funnel_stage="name_captured",
        search_count=updated_session.search_count or 0,
        name=updated_session.name,
        email=updated_session.email,
        disclaimer_accepted_at=updated_session.disclaimer_accepted_at,
    )


@router.post(
    "/session/{session_id}/disclaimer",
    response_model=DisclaimerAcceptanceResponse,
    status_code=status.HTTP_200_OK,
)
async def accept_disclaimer(
    session_id: UUID,
    body: DisclaimerAcceptanceRequest,
) -> DisclaimerAcceptanceResponse:
    """
    Accept medical disclaimer.

    Step 3 in the freemium funnel.
    MANDATORY before first search. Logs acceptance with timestamp.

    Analytics: Tracks "disclaimer_accepted" funnel stage.
    """
    if not body.accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Disclaimer must be accepted to continue",
        )

    # Get session
    session = await SessionRepository.get_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Update disclaimer acceptance
    session_update = SessionUpdate(disclaimer_accepted_at=datetime.utcnow())
    updated_session = await SessionRepository.update(session_id, session_update)
    if not updated_session:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update session",
        )

    # Track funnel stage
    await track_funnel_stage(
        session_id=str(session_id),
        tenant_id=str(session.tenant_id),
        stage="disclaimer_accepted",
        metadata={"timestamp": datetime.utcnow().isoformat()},
    )

    # Create session token (this allows searches now)
    session_token = f"session_{session.id}_authorized"

    return DisclaimerAcceptanceResponse(
        session_token=session_token,
        message="Disclaimer accepted. You can now search.",
    )


@router.post(
    "/session/{session_id}/email",
    response_model=SessionStatus,
    status_code=status.HTTP_200_OK,
)
async def capture_email(
    session_id: UUID,
    body: EmailCaptureRequest,
) -> SessionStatus:
    """
    Capture visitor email.

    Step 5 in the freemium funnel (after first search).
    Stores email on the session.

    Analytics: Tracks "email_captured" funnel stage.
    """
    # Get session
    session = await SessionRepository.get_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Build update with email + optional CRM fields
    update_fields: dict = {"email": body.email}
    if body.institution:
        update_fields["institution"] = body.institution
    if body.phone:
        update_fields["phone"] = body.phone
    # User-provided city/country override GeoIP if provided
    if body.city:
        update_fields["geo_city"] = body.city
    if body.country:
        update_fields["geo_country"] = body.country
    if body.data_consent_accepted:
        update_fields["data_consent_accepted_at"] = datetime.utcnow()

    session_update = SessionUpdate(**update_fields)
    updated_session = await SessionRepository.update(session_id, session_update)
    if not updated_session:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update session",
        )

    # Track funnel stage
    await track_funnel_stage(
        session_id=str(session_id),
        tenant_id=str(session.tenant_id),
        stage="email_captured",
        metadata={
            "email": body.email,
            "institution": body.institution,
            "data_consent": body.data_consent_accepted,
        },
    )

    return SessionStatus(
        session_id=session_id,
        funnel_stage="email_captured",
        search_count=updated_session.search_count or 0,
        name=updated_session.name,
        email=updated_session.email,
        disclaimer_accepted_at=updated_session.disclaimer_accepted_at,
    )


@router.get(
    "/session/{session_id}/status",
    response_model=SessionStatus,
    status_code=status.HTTP_200_OK,
)
async def get_session_status(session_id: UUID) -> SessionStatus:
    """
    Get current status of an anonymous session.

    Returns:
    - funnel_stage: Current stage based on what data has been captured
    - search_count: Number of searches performed
    - name, email: If captured
    """
    # Get session
    session = await SessionRepository.get_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Determine current funnel stage based on session state
    if session.disclaimer_accepted_at is None:
        funnel_stage = "name_captured" if session.name else "landed"
    elif session.email:
        funnel_stage = "email_captured"
    elif session.search_count and session.search_count >= 1:
        funnel_stage = "first_search"
    else:
        funnel_stage = "disclaimer_accepted"

    return SessionStatus(
        session_id=session_id,
        funnel_stage=funnel_stage,
        search_count=session.search_count or 0,
        name=session.name,
        email=session.email,
        disclaimer_accepted_at=session.disclaimer_accepted_at,
    )
