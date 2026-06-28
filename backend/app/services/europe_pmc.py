"""Europe PMC REST API — biomedical literature full-text index (P1)."""

import httpx
from dataclasses import dataclass
from typing import Optional

from app.core.logging import get_logger

logger = get_logger("lena.sources")

BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


@dataclass
class EuropePMCArticle:
    title: str
    abstract: str
    authors: list[str]
    year: Optional[int]
    doi: Optional[str]
    url: str
    source: str


async def search_europe_pmc(query: str, max_results: int = 10) -> list[EuropePMCArticle]:
    params = {
        "query": query,
        "format": "json",
        "pageSize": min(max_results, 100),
        "resultType": "core",
    }
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.get(BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("Europe PMC search failed: %s", exc)
        return []

    articles: list[EuropePMCArticle] = []
    for item in (data.get("resultList") or {}).get("result") or []:
        pmid = item.get("pmid") or item.get("id")
        doi = item.get("doi")
        url = f"https://europepmc.org/article/MED/{pmid}" if pmid else (f"https://doi.org/{doi}" if doi else "")
        authors_raw = item.get("authorString") or ""
        authors = [a.strip() for a in authors_raw.split(",") if a.strip()][:8]
        year = None
        if item.get("pubYear"):
            try:
                year = int(item["pubYear"])
            except (TypeError, ValueError):
                pass
        articles.append(
            EuropePMCArticle(
                title=item.get("title") or "Untitled",
                abstract=item.get("abstractText") or "",
                authors=authors,
                year=year,
                doi=doi,
                url=url,
                source=item.get("source") or "MED",
            )
        )
    return articles
