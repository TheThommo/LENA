"""
OpenAlex API Service

OpenAlex is a free, open catalog of the global research system — 250M+ works,
100M+ authors, and 100K+ institutions. It replaced Microsoft Academic Graph.

Docs: https://docs.openalex.org/
Base: https://api.openalex.org

Rate limits:
- Without polite pool: 10 requests/second
- With polite pool (email in User-Agent): 100 requests/second
No API key required.
"""

import httpx
from typing import Optional
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.logging import get_logger

logger = get_logger("lena.sources")

BASE_URL = "https://api.openalex.org"


@dataclass
class OpenAlexWork:
    openalex_id: str
    title: str
    abstract: str
    authors: list[str]
    journal: Optional[str]
    year: Optional[int]
    doi: Optional[str]
    url: str
    cited_by_count: int
    open_access: bool


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)),
)
async def search_openalex(
    query: str,
    max_results: int = 10,
) -> list[OpenAlexWork]:
    """
    Search OpenAlex for academic works (papers, articles, preprints).

    Args:
        query: Search term
        max_results: Number of results to return (max 200)

    Returns:
        List of OpenAlexWork objects
    """
    params = {
        "search": query,
        "per_page": min(max_results, 200),
        "sort": "relevance_score:desc",
        "select": "id,title,authorships,publication_year,doi,primary_location,cited_by_count,open_access,abstract_inverted_index",
    }

    headers = {
        "Accept": "application/json",
        "User-Agent": "LENA-Research-Agent/1.0 (mailto:support@heathnet.com.au)",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/works",
            params=params,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    works = []
    for result in data.get("results", []):
        openalex_id = result.get("id", "")

        title = result.get("title") or "No title"

        # Reconstruct abstract from inverted index
        abstract = _reconstruct_abstract(result.get("abstract_inverted_index"))

        # Extract authors
        authors = []
        for authorship in result.get("authorships", [])[:10]:
            author = authorship.get("author", {})
            name = author.get("display_name", "")
            if name:
                authors.append(name)

        # Journal / venue
        journal = None
        primary_loc = result.get("primary_location") or {}
        source = primary_loc.get("source") or {}
        if source:
            journal = source.get("display_name")

        year = result.get("publication_year")

        # DOI
        doi_raw = result.get("doi")
        doi = doi_raw.replace("https://doi.org/", "") if doi_raw else None

        # URL — prefer DOI link, fall back to OpenAlex page
        url = doi_raw or f"https://openalex.org/works/{openalex_id.split('/')[-1]}" if openalex_id else ""

        # Open access
        oa = result.get("open_access", {})
        is_oa = oa.get("is_oa", False)

        works.append(OpenAlexWork(
            openalex_id=openalex_id,
            title=title,
            abstract=abstract,
            authors=authors,
            journal=journal,
            year=year,
            doi=doi,
            url=url,
            cited_by_count=result.get("cited_by_count", 0),
            open_access=is_oa,
        ))

    logger.debug(f"OpenAlex search for '{query}' returned {len(works)} results")
    return works


def _reconstruct_abstract(inverted_index: Optional[dict]) -> str:
    """Reconstruct abstract text from OpenAlex inverted index format."""
    if not inverted_index:
        return ""
    try:
        word_positions: list[tuple[int, str]] = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        word_positions.sort(key=lambda x: x[0])
        return " ".join(w for _, w in word_positions)
    except Exception:
        return ""


async def test_connection() -> dict:
    """Test the OpenAlex API connection."""
    try:
        works = await search_openalex("cancer immunotherapy", max_results=3)
        return {
            "source": "OpenAlex",
            "status": "connected",
            "test_query": "cancer immunotherapy",
            "results_found": len(works),
            "sample_title": works[0].title if works else "N/A",
            "api_key_required": False,
            "note": "Free open catalog of 250M+ academic works",
        }
    except Exception as e:
        return {
            "source": "OpenAlex",
            "status": "error",
            "error": str(e),
        }
