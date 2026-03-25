"""
Health check and connection test routes.
"""

import asyncio
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
    Test all external API connections in parallel.
    Returns status for each data source.
    """
    # Run all 5 connection tests in parallel
    test_results = await asyncio.gather(
        pubmed.test_connection(),
        clinical_trials.test_connection(),
        cochrane.test_connection(),
        who_iris.test_connection(),
        cdc.test_connection(),
        return_exceptions=True,
    )

    source_names = ["pubmed", "clinical_trials", "cochrane", "who_iris", "cdc"]
    results = {}
    for name, result in zip(source_names, test_results):
        if isinstance(result, Exception):
            results[name] = {"status": "error", "error": str(result)}
        else:
            results[name] = result

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
