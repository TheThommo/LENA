"""
Health check and connection test routes.
"""

from fastapi import APIRouter

from app.services import pubmed, clinical_trials, cochrane, who_iris, cdc, openai_service
from app.db.supabase import test_connection as test_supabase

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "service": "LENA API"}


@router.get("/connections")
async def test_all_connections():
    """
    Test all external API connections.
    Returns status for each data source.
    """
    results = {
        "pubmed": await pubmed.test_connection(),
        "clinical_trials": await clinical_trials.test_connection(),
        "cochrane": await cochrane.test_connection(),
        "who_iris": await who_iris.test_connection(),
        "cdc": await cdc.test_connection(),
    }

    # Count connected vs errors
    connected = sum(1 for r in results.values() if r.get("status") == "connected")
    total = len(results)

    return {
        "summary": f"{connected}/{total} data sources connected",
        "all_connected": connected == total,
        "sources": results,
    }


@router.get("/connections/openai")
async def test_openai():
    """Test OpenAI connection (separate since it requires API key)."""
    return await openai_service.test_connection()


@router.get("/connections/supabase")
async def test_supabase_connection():
    """Test Supabase connection (separate since it requires credentials)."""
    return await test_supabase()
