"""
Health check and connection test routes.
"""

import asyncio
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.services import pubmed, clinical_trials, cochrane, who_iris, cdc, openalex, openai_service
from app.db.supabase import test_connection as test_supabase

router = APIRouter(prefix="/health", tags=["health"])

_SITE_PROBE_TIMEOUT = 6.0


def _production_sites() -> List[Dict[str, str]]:
    """Canonical production surfaces — always include lenamd.com."""
    app_url = (settings.app_url or "https://www.lenamd.com").rstrip("/")
    return [
        {"name": "www.lenamd.com", "url": app_url, "path": "/", "role": "production_app"},
        {"name": "www.lenamd.com /chat", "url": app_url, "path": "/chat", "role": "production_chat"},
        {"name": "www.lenamd.com /admin", "url": app_url, "path": "/admin.html", "role": "production_admin"},
        {"name": "lenamd.com", "url": "https://lenamd.com", "path": "/", "role": "apex_domain"},
    ]


async def _probe_site(site: Dict[str, str]) -> Dict[str, Any]:
    """HEAD/GET a public production URL and return a compact status dict."""
    base = site["url"].rstrip("/")
    path = site.get("path") or "/"
    target = f"{base}{path}"
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=_SITE_PROBE_TIMEOUT,
        ) as client:
            response = await client.get(target)
            ok = response.status_code < 400
            return {
                "name": site["name"],
                "url": target,
                "role": site.get("role"),
                "status": "healthy" if ok else "degraded",
                "status_code": response.status_code,
            }
    except Exception as exc:
        return {
            "name": site["name"],
            "url": target,
            "role": site.get("role"),
            "status": "unreachable",
            "status_code": None,
            "error": str(exc),
        }


@router.get("")
@router.get("/")
async def health_check():
    """Basic health check plus production site probes (lenamd.com)."""
    sites = await asyncio.gather(*[_probe_site(s) for s in _production_sites()])
    site_list = list(sites)
    sites_healthy = all(s.get("status") == "healthy" for s in site_list)
    return {
        "status": "healthy" if sites_healthy else "degraded",
        "service": "LENA API",
        "environment": settings.app_env,
        "railway": settings.on_railway,
        "app_url": settings.app_url,
        "sites": site_list,
        "sites_healthy": sites_healthy,
    }


@router.get("/connections")
async def test_all_connections():
    """
    Test all external API connections in parallel.
    Returns status for each data source.
    """
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Not Found")
    # Run all 6 connection tests in parallel
    test_results = await asyncio.gather(
        pubmed.test_connection(),
        clinical_trials.test_connection(),
        cochrane.test_connection(),
        who_iris.test_connection(),
        cdc.test_connection(),
        openalex.test_connection(),
        return_exceptions=True,
    )

    source_names = ["pubmed", "clinical_trials", "cochrane", "who_iris", "cdc", "openalex"]
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
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Not Found")
    return await openai_service.test_connection()


@router.get("/connections/supabase")
async def test_supabase_connection():
    """Test Supabase connection (separate since it requires credentials)."""
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Not Found")
    return await test_supabase()
