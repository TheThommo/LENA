"""Crossref API — DOI metadata resolution (P1 enrichment)."""

import httpx
from typing import Optional

from app.core.logging import get_logger

logger = get_logger("lena.sources")

BASE_URL = "https://api.crossref.org/works"


async def resolve_doi_metadata(doi: str) -> Optional[dict]:
    """Resolve a DOI to title + URL via Crossref (best-effort)."""
    if not doi:
        return None
    clean = doi.replace("https://doi.org/", "").strip()
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(
                f"{BASE_URL}/{clean}",
                headers={"User-Agent": "LENA/1.0 (mailto:support@heathnet.com.au)"},
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            msg = resp.json().get("message") or {}
            return {
                "title": " ".join(msg.get("title") or []) or None,
                "doi": clean,
                "url": f"https://doi.org/{clean}",
                "year": (msg.get("published-print") or msg.get("published-online") or {}).get("date-parts", [[None]])[0][0],
            }
    except Exception as exc:
        logger.debug("Crossref DOI resolve failed for %s: %s", doi, exc)
        return None
