"""
Analytics Middleware

Runs on every request to:
1. Extract client IP (check X-Forwarded-For first)
2. Geolocate the IP
3. Extract UTM parameters
4. Extract referrer header
5. Store analytics context in request.state
6. Enrich session with geo/referrer data (background task)
"""

import logging
from typing import Callable
from datetime import datetime, timezone

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.services.geolocation import geolocate_ip
from app.services.tracking import parse_utm_params, classify_referrer
from app.services.analytics_writer import log_session_start, schedule_analytics_task

logger = logging.getLogger(__name__)


def _extract_client_ip(request: Request) -> str:
    """Extract client IP, checking X-Forwarded-For first."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """Collects analytics for every request and enriches sessions."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract client info
        ip_address = _extract_client_ip(request)
        referrer = request.headers.get("referer")
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

        # Store analytics context in request.state
        request.state.ip_address = ip_address
        request.state.geo_data = geo_data
        request.state.referrer_data = referrer_data
        request.state.utm_data = utm_data
        request.state.request_started_at = datetime.now(timezone.utc)

        # Process the request
        response = await call_next(request)

        # After request: enrich session with geo/referrer if session exists
        try:
            session_id = getattr(request.state, "session_id", None)
            tenant_id = None

            # Try to get tenant_id from query params or session
            if hasattr(request.state, "session") and request.state.session:
                tenant_id = str(request.state.session.tenant_id)
            else:
                tenant_id = query_params.get("tenant_id")

            if session_id and tenant_id and (geo_data or referrer_data.get("raw") or utm_data.get("utm_source")):
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
        except Exception as e:
            logger.warning(f"Failed to schedule session enrichment: {e}")

        return response
