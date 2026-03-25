"""
LENA - Literature and Evidence Navigation Agent
FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import health, search

app = FastAPI(
    title="LENA API",
    description="Literature and Evidence Navigation Agent - Clinical Research Platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router, prefix="/api")
app.include_router(search.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "LENA",
        "description": "Literature and Evidence Navigation Agent",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health",
    }
