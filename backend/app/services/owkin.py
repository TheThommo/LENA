"""
Owkin enterprise pathology API — DORMANT unless OWKIN_ENABLED=true.

NOT scored by PULSE. Enterprise-only enrichment panel.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("lena.sources.owkin")


@dataclass
class OwkinPathologyResult:
    id: str
    title: str
    summary: str
    url: str
    confidence: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


async def search_owkin(query: str, max_results: int = 5) -> list[OwkinPathologyResult]:
    """
    Query Owkin pathology analysis. No-op when OWKIN_ENABLED is false.
    When enabled, requires OWKIN_API_KEY and OWKIN_API_URL (fail loud).
    """
    if not settings.owkin_enabled:
        return []

    if not settings.owkin_api_key:
        raise RuntimeError(
            "OWKIN_ENABLED=true but OWKIN_API_KEY is missing. "
            "Set OWKIN_API_KEY or disable Owkin with OWKIN_ENABLED=false."
        )
    if not settings.owkin_api_url:
        raise RuntimeError(
            "OWKIN_ENABLED=true but OWKIN_API_URL is missing. "
            "Set OWKIN_API_URL or disable Owkin with OWKIN_ENABLED=false."
        )

    headers = {
        "Authorization": f"Bearer {settings.owkin_api_key}",
        "Accept": "application/json",
    }
    payload = {"query": query, "limit": max_results}
    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(
            settings.owkin_api_url.rstrip("/") + "/v1/pathology/search",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    rows = data.get("results") or data.get("analyses") or []
    out: list[OwkinPathologyResult] = []
    for row in rows:
        out.append(
            OwkinPathologyResult(
                id=str(row.get("id") or ""),
                title=row.get("title") or "Pathology analysis",
                summary=(row.get("summary") or row.get("findings") or "")[:800],
                url=row.get("url") or "",
                confidence=row.get("confidence"),
            )
        )
        if len(out) >= max_results:
            break
    return out
