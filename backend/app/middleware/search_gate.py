"""
Search Gate Middleware

Enforces freemium search limits on the /api/search/ endpoints.

Rules:
- No session token? → 401 (must complete disclaimer first)
- Search count >= 2 AND not registered? → 403 (signup required)
- Otherwise: Allow, and increment search counter
- Registered users bypass the counter (their plan limits apply)
"""

import logging
from uuid import UUID
from typing import Callable, Optional

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.db.repositories.session_repo import SessionRepository
from app.models import SessionUpdate
from app.services.funnel_tracker import track_funnel_stage

logger = logging.getLogger(__name__)


def extract_session_id(request: Request) -> Optional[str]:
    """
    Extract session ID from Authorization header or X-Session-ID header.
    Token format: "session_{uuid}" or "session_{uuid}_authorized"
    """
    # Check Authorization header (Bearer token)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
        if token.startswith("session_"):
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

        # Only apply to search endpoints
        if not request.url.path.startswith("/api/search"):
            return await call_next(request)

        # Extract session ID from request
        session_id = extract_session_id(request)

        # Check if user is authenticated (has a user_id in JWT)
        # This would be extracted by require_auth dependency if present
        # For now, we check if session exists
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session required. Complete the medical disclaimer first.",
            )

        try:
            # Get session
            session = await SessionRepository.get_by_id(UUID(session_id))
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid session.",
                )

            # Check if disclaimer has been accepted
            if not session.disclaimer_accepted_at:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Medical disclaimer must be accepted before searching.",
                )

            # Check if user is registered (has user_id)
            # If not registered, enforce the free search limit
            if not session.user_id:
                search_count = session.search_count or 0

                # Hard gate at 2 free searches
                if search_count >= 2:
                    # Track funnel stage
                    await track_funnel_stage(
                        session_id=str(session.id),
                        tenant_id=str(session.tenant_id),
                        stage="signup_cta_shown",
                    )

                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You've used your 2 free searches. Sign up to continue.",
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
                elif new_count == 2:
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

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in search gate: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )

        # Allow request to proceed
        return await call_next(request)
