"""
Search Gate Middleware

Enforces freemium search limits on the /api/search/ endpoints.

Rules:
- Authenticated user (valid JWT)? → Allow (registered users bypass counter)
- No session token? → 401 (must complete disclaimer first)
- Search count >= 5 AND not registered? → 403 (signup required)
- Otherwise: Allow, and increment search counter
"""

import logging
from uuid import UUID
from typing import Callable, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse

from app.db.repositories.session_repo import SessionRepository
from app.models import SessionUpdate
from app.services.funnel_tracker import track_funnel_stage

logger = logging.getLogger(__name__)


def _extract_bearer_token(request: Request) -> Optional[str]:
    """Extract the raw Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


def _try_decode_jwt(token: str) -> Optional[dict]:
    """
    Try to decode the token as a LENA JWT.
    Returns the payload dict if valid, None otherwise.
    """
    try:
        from app.core.auth import verify_token
        return verify_token(token)
    except Exception:
        return None


def extract_session_id(request: Request) -> Optional[str]:
    """
    Extract session ID from Authorization header or X-Session-ID header.
    Token format: "session_{uuid}" or "session_{uuid}_authorized"
    """
    # Check Authorization header (Bearer token)
    token = _extract_bearer_token(request)
    if token and token.startswith("session_"):
        # Extract UUID from "session_{uuid}" or "session_{uuid}_authorized"
        parts = token.split("_")
        if len(parts) >= 2:
            try:
                return str(UUID(parts[1]))
            except (ValueError, IndexError):
                pass

    # Check X-Session-ID header
    session_id_header = request.headers.get("X-Session-ID", "")
    if session_id_header:
        try:
            return str(UUID(session_id_header))
        except ValueError:
            pass

    return None


class SearchGateMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces freemium search limits.
    Only applies to /api/search/ endpoints.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check search gate before allowing request."""

        # Only apply to search endpoints (skip OPTIONS preflight requests)
        if not request.url.path.startswith("/api/search") or request.method == "OPTIONS":
            return await call_next(request)

        # ── Pre-auth guardrails ──────────────────────────────────────
        # Self-harm, profanity, and off-topic checks run BEFORE session
        # validation so they work for anonymous visitors who haven't
        # completed the disclaimer. These are hard blocks — no search
        # runs, no session needed.
        query_param = request.query_params.get("q", "")
        if query_param:
            from app.core.guardrails import run_all_guardrails
            guardrail_type, guardrail_msg = run_all_guardrails(query_param)
            if guardrail_type and guardrail_type != "medical_advice":
                return JSONResponse(
                    status_code=200,
                    content={
                        "guardrail_triggered": True,
                        "guardrail_type": guardrail_type,
                        "guardrail_message": guardrail_msg,
                        "query": query_param,
                        "pulse_report": None,
                        "response_time_ms": 0,
                    },
                )

        # ── Check for authenticated user (JWT) first ──
        bearer = _extract_bearer_token(request)
        if bearer and not bearer.startswith("session_"):
            jwt_payload = _try_decode_jwt(bearer)
            if jwt_payload and jwt_payload.get("user_id"):
                # Authenticated registered user — bypass the FREE search
                # limit, but still try to link the session so search_count
                # increments (needed for admin Visitor Activity and the
                # funnel stage counts).
                request.state.user_id = jwt_payload["user_id"]

                # Try to find and increment the user's session
                session_id = extract_session_id(request)
                if session_id:
                    try:
                        session = await SessionRepository.get_by_id(UUID(session_id))
                        if session:
                            new_count = (session.search_count or 0) + 1
                            await SessionRepository.update(
                                UUID(session_id),
                                SessionUpdate(search_count=new_count),
                            )
                            request.state.session_id = session_id
                            request.state.session = session
                        else:
                            request.state.session_id = None
                            request.state.session = None
                    except Exception:
                        request.state.session_id = None
                        request.state.session = None
                else:
                    request.state.session_id = None
                    request.state.session = None

                return await call_next(request)

        # ── Anonymous / session-based flow ──
        session_id = extract_session_id(request)

        if not session_id:
            return JSONResponse(
                status_code=401,
                content={"detail": "Session required. Complete the medical disclaimer first."},
            )

        try:
            # Get session
            session = await SessionRepository.get_by_id(UUID(session_id))
            if not session:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid session."},
                )

            # Check if disclaimer has been accepted
            if not session.disclaimer_accepted_at:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Medical disclaimer must be accepted before searching."},
                )

            # Check if user is registered (has user_id)
            # If not registered, enforce the free search limit
            if not session.user_id:
                search_count = session.search_count or 0

                # Hard gate at 5 free searches/day
                if search_count >= 5:
                    # Track funnel stage
                    await track_funnel_stage(
                        session_id=str(session.id),
                        tenant_id=str(session.tenant_id),
                        stage="signup_cta_shown",
                    )

                    return JSONResponse(
                        status_code=403,
                        content={"detail": "You've used your 5 free searches today. Sign up for Pro to continue."},
                    )

                # Increment search counter
                new_count = search_count + 1
                session_update = SessionUpdate(search_count=new_count)
                await SessionRepository.update(UUID(session_id), session_update)

                # Track first search and email capture stages
                if new_count == 1:
                    await track_funnel_stage(
                        session_id=str(session.id),
                        tenant_id=str(session.tenant_id),
                        stage="first_search",
                    )
                elif new_count == 5:
                    await track_funnel_stage(
                        session_id=str(session.id),
                        tenant_id=str(session.tenant_id),
                        stage="second_search",
                    )
            else:
                # Registered user - check subscription plan
                # TODO: Implement plan-based limits
                pass

            # Store session info in request state for downstream handlers
            request.state.session_id = session_id
            request.state.session = session

        except Exception as e:
            logger.error(f"Error in search gate: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )

        # Allow request to proceed
        return await call_next(request)
