"""DailyMed API — FDA structured product labels (P2 product research)."""

import httpx
from dataclasses import dataclass
from typing import Optional

from app.core.logging import get_logger

logger = get_logger("lena.sources")

BASE_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v2"


@dataclass
class DailyMedLabel:
    set_id: str
    title: str
    summary: str
    url: str
    labeler: Optional[str]


async def search_dailymed(query: str, max_results: int = 10) -> list[DailyMedLabel]:
    """Search FDA DailyMed SPL labels by drug/product name."""
    params = {"drug_name": query, "pagesize": min(max_results, 50)}
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.get(f"{BASE_URL}/spls.json", params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("DailyMed search failed: %s", exc)
        return []

    labels: list[DailyMedLabel] = []
    for item in (data.get("data") or [])[:max_results]:
        set_id = str(item.get("setid") or "")
        title = item.get("title") or item.get("drug_name") or "Drug label"
        labeler = item.get("labeler") or item.get("labeler_name")
        url = f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}" if set_id else "https://dailymed.nlm.nih.gov/"
        labels.append(
            DailyMedLabel(
                set_id=set_id,
                title=title,
                summary=f"FDA structured product label{f' by {labeler}' if labeler else ''}.",
                url=url,
                labeler=labeler,
            )
        )
    return labels
