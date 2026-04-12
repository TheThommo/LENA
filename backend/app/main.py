"""
LENA - Literature and Evidence Navigation Agent
FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import health, search, session, auth, dashboard_platform, dashboard_tenant, dashboard_export
from app.middleware.analytics import AnalyticsMiddleware
from app.middleware.search_gate import SearchGateMiddleware

app = FastAPI(
    title="LENA API",
    description="Literature and Evidence Navigation Agent - Clinical Research Platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    redirect_slashes=False,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Analytics
app.add_middleware(AnalyticsMiddleware)

# Search gate (enforces freemium limits) - must be before search router
app.add_middleware(SearchGateMiddleware)

# Routes
app.include_router(health.router, prefix="/api")
app.include_router(session.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(dashboard_platform.router, prefix="/api")
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
