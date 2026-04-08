"""
Analytics Middleware

Runs on every request to:
1. Extract client IP (check X-Forwarded-For first)
2. Geolocate the IP
3. Extract UTM parameters
4. Extract referrer header
5. Create or update session tracking
6. Store analytics context in request.state

All Supabase writes are background tasks (never blocking).
Errors are logged but never raised (analytics failures must not break the app).
"""

import logging
import uuid
from typing import Callable
from datetime import datetime

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.services.geolocation import geolocate_ip
from app.services.tracking import parse_utm_params, classify_referrer
from app.services.analytics_writer import log_session_start, schedule_analytics_task

logger = logging.getLogger(__name__)


def _extract_client_ip(request: Request) -> str:
    """
    Extract client IP from request.
    Checks X-Forwarded-For header first (for proxies/load balancers).
    Falls back to request.client.host.
    """
    # Check X-Forwarded-For (set by proxies/load balancers)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take the first IP in the comma-separated list
        return forwarded_for.split(",")[0].strip()

    # Fallback to direct client IP
    if request.client:
        return request.client.host

    return "unknown"


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """
    Middleware that collects analytics for every request.
    Stores session/context info in request.state for use by route handlers.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request, collect analytics, then pass to route handler."""

        # Extract client info
        ip_address = _extract_client_ip(request)
        referrer = request.headers.get("referer")  # Note: HTTP header spelling is "referer"
        query_params = dict(request.query_params)

        # Parse UTM and referrer (synchronous)
        utm_data = parse_utm_params(query_params)
        referrer_data = classify_referrer(referrer)

        # Geolocate IP (async)
        try:
            geo_data = await geolocate_ip(ip_address)
        except Exception as e:
            logger.warning(f"Geolocation failed: {e}")
            geo_data = None

        # Create a unique session ID if not already set
        # In a real app, this would check for existing session cookies
        session_id = str(uuid.uuid4())

        # For now, use a hardcoded default tenant
        # In production, this would be extracted from subdomain, auth token, or query param
        tenant_id = "default_tenant"

        # Store analytics context in request.state
        request.state.session_id = session_id
        request.state.tenant_id = tenant_id
        request.state.ip_address = ip_address
        request.state.geo_data = geo_data
        request.state.referrer_data = referrer_data
        request.state.utm_data = utm_data
        request.state.request_started_at = datetime.utcnow()

        # Schedule session logging (fire-and-forget, non-blocking)
        schedule_analytics_task(
            log_session_start(
                session_id=session_id,
                ip=ip_address,
                geo_data=geo_data,
                referrer_data=referrer_data,
                utm_data=utm_data,
                tenant_id=tenant_id,
            )
        )

        # Continue processing the request
        response = await call_next(request)

        return response
