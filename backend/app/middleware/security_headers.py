"""
Security Headers Middleware

Adds defensive headers to every response:
- X-Frame-Options: DENY — prevents clickjacking of admin.html
- X-Content-Type-Options: nosniff — stops MIME sniffing
- Referrer-Policy: strict-origin-when-cross-origin
- Strict-Transport-Security — forces HTTPS for 1 year (only on HTTPS)
- Permissions-Policy — disables unused browser features
- Content-Security-Policy — restricts script/style origins (baseline)
"""

from typing import Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


_CSP = (
    "default-src 'self'; "
    # admin.html loads chart.js from jsdelivr + Google Fonts
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: https:; "
    "connect-src 'self' https://*.up.railway.app https://*.supabase.co; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=()",
        )
        # HSTS — only meaningful over HTTPS, but safe to always send
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )
        # CSP — apply only to HTML responses so JSON APIs are unaffected
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            response.headers.setdefault("Content-Security-Policy", _CSP)
        return response
