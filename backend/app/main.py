"""
LENA - Literature and Evidence Navigation Agent
FastAPI Application Entry Point
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import health, search, session, auth, dashboard_platform, dashboard_tenant, dashboard_export, dashboard_subscriptions, projects, discover
from app.middleware.analytics import AnalyticsMiddleware
from app.middleware.search_gate import SearchGateMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

logger = logging.getLogger(__name__)

# Fail loudly at startup if the signing secret was never rotated in production.
if settings.is_production and settings.jwt_secret_key == "change-me-in-production":
    raise RuntimeError(
        "JWT_SECRET_KEY is still set to the default placeholder in production. "
        "Refusing to start — set a strong secret via environment variable."
    )

# Hide OpenAPI docs in production so attackers can't introspect the API surface.
_docs_url = None if settings.is_production else "/docs"
_redoc_url = None if settings.is_production else "/redoc"
_openapi_url = None if settings.is_production else "/openapi.json"

app = FastAPI(
    title="LENA API",
    description="Literature and Evidence Navigation Agent - Clinical Research Platform",
    version="0.1.0",
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
    redirect_slashes=False,
)

# Middleware order matters: last added = outermost (runs first).
# CORSMiddleware must be outermost so it adds CORS headers to ALL responses,
# including early returns from inner middleware like SearchGateMiddleware.

# Inner: Search gate (enforces freemium limits)
app.add_middleware(SearchGateMiddleware)

# Middle: Analytics
app.add_middleware(AnalyticsMiddleware)

# Security headers on every response (clickjacking/CSP/HSTS)
app.add_middleware(SecurityHeadersMiddleware)

# Outer: CORS (must be last = outermost so headers are always added)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router, prefix="/api")
app.include_router(session.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(discover.router, prefix="/api")
app.include_router(dashboard_platform.router, prefix="/api")
app.include_router(dashboard_subscriptions.router, prefix="/api")
app.include_router(dashboard_tenant.router, prefix="/api")
app.include_router(dashboard_export.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "LENA",
        "description": "Literature and Evidence Navigation Agent",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health",
    }
