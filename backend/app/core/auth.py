"""
Authentication Utilities

Handles JWT token creation, verification, and user authentication dependencies.
Uses PyJWT for stateless token management.
"""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import Request, HTTPException, status, Depends
from app.core.config import settings


def create_access_token(
    user_id: str,
    tenant_id: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User ID to encode
        tenant_id: Tenant ID to encode
        role: User role to encode
        expires_delta: Optional custom expiration time (defaults to config)

    Returns:
        JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_expiration_minutes)

    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "user_id": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload (dict)

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency to extract current user from Authorization header.
    Returns None if no valid token is found (for optional auth).

    Args:
        request: FastAPI request

    Returns:
        Decoded token payload or None
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    try:
        scheme, token = auth_header.split()
        if scheme.lower() != "bearer":
            return None

        payload = verify_token(token)
        return payload
    except (ValueError, HTTPException):
        return None


async def require_auth(request: Request) -> Dict[str, Any]:
    """
    FastAPI dependency that requires authentication.
    Raises 401 if no valid token found.

    Args:
        request: FastAPI request

    Returns:
        Decoded token payload

    Raises:
        HTTPException: 401 Unauthorized
    """
    user = await get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide a valid Bearer token.",
        )
    return user


def require_role(allowed_roles: list[str]):
    """
    FastAPI dependency factory that checks user role.

    Args:
        allowed_roles: List of allowed user roles

    Returns:
        Async function that validates role
    """

    async def role_checker(user: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
        """Check if user has one of the allowed roles."""
        if user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(allowed_roles)}",
            )
        return user

    return role_checker
