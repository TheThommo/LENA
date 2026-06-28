"""Semantic Scholar API — academic paper search (P1)."""

import httpx
from dataclasses import dataclass
from typing import Optional

from app.core.logging import get_logger

logger = get_logger("lena.sources")

BASE_URL = "https://api.semanticscholar.org/graph/v1"


@dataclass
class SemanticScholarPaper:
    paper_id: str
    title: str
    abstract: str
    authors: list[str]
    year: Optional[int]
    doi: Optional[str]
    url: str
    citation_count: int


async def search_semantic_scholar(query: str, max_results: int = 10) -> list[SemanticScholarPaper]:
    params = {
        "query": query,
        "limit": min(max_results, 100),
        "fields": "title,abstract,authors,year,externalIds,citationCount,url",
    }
    headers = {"User-Agent": "LENA-Research-Agent/1.0 (mailto:support@heathnet.com.au)"}
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.get(f"{BASE_URL}/paper/search", params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("Semantic Scholar search failed: %s", exc)
        return []

    papers: list[SemanticScholarPaper] = []
    for item in data.get("data") or []:
        ext = item.get("externalIds") or {}
        doi = ext.get("DOI")
        authors = [a.get("name", "") for a in (item.get("authors") or []) if a.get("name")]
        papers.append(
            SemanticScholarPaper(
                paper_id=str(item.get("paperId") or ""),
                title=item.get("title") or "Untitled",
                abstract=item.get("abstract") or "",
                authors=authors,
                year=item.get("year"),
                doi=doi,
                url=item.get("url") or f"https://www.semanticscholar.org/paper/{item.get('paperId', '')}",
                citation_count=int(item.get("citationCount") or 0),
            )
        )
    return papers
