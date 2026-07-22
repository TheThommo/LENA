"""
bioRxiv / medRxiv preprint search.

Uses Europe PMC (indexes bioRxiv/medRxiv) for free-text recall, then
enriches with api.biorxiv.org detail when a DOI is available.

PULSE: SCORED as study_type=preprint (below case_report). Flagged PREPRINT.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.logging import get_logger

logger = get_logger("lena.sources.biorxiv")

EUROPE_PMC_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
BIORXIV_DETAILS_URL = "https://api.biorxiv.org/details"


@dataclass
class BiorxivPreprint:
    doi: str
    title: str
    abstract: str
    authors: list[str]
    year: Optional[int]
    url: str
    server: str  # biorxiv | medrxiv
    category: Optional[str] = None


def _server_from_row(row: dict) -> str:
    journal = (row.get("journalTitle") or row.get("bookOrReportDetails") or "").lower()
    source = (row.get("source") or "").upper()
    if "medrxiv" in journal or source == "MEDRXIV":
        return "medrxiv"
    return "biorxiv"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)),
)
async def search_biorxiv(query: str, max_results: int = 10) -> list[BiorxivPreprint]:
    """
    Search bioRxiv/medRxiv preprints for a free-text query.
    """
    # SRC:PPR = preprint abstracts in Europe PMC (covers bioRxiv + medRxiv)
    epmc_query = f"(SRC:PPR) AND ({query})"
    params = {
        "query": epmc_query,
        "format": "json",
        "pageSize": min(max_results, 25),
        "resultType": "core",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(EUROPE_PMC_URL, params=params)
        response.raise_for_status()
        data = response.json()

    results: list[BiorxivPreprint] = []
    for row in (data.get("resultList") or {}).get("result") or []:
        title = (row.get("title") or "").strip()
        if not title:
            continue
        doi = (row.get("doi") or "").strip()
        server = _server_from_row(row)
        year = None
        pub_year = row.get("pubYear")
        if pub_year:
            try:
                year = int(str(pub_year)[:4])
            except ValueError:
                year = None
        authors: list[str] = []
        author_str = row.get("authorString") or ""
        if author_str:
            authors = [a.strip() for a in author_str.split(",") if a.strip()][:10]
        abstract = (row.get("abstractText") or "").strip()
        url = (
            f"https://www.{server}.org/content/{doi}"
            if doi
            else (row.get("fullTextUrlList") or {}).get("fullTextUrl", [{}])[0].get("url", "")
        )
        # Optional enrichment from api.biorxiv.org (fail soft — keep EPMC row)
        if doi and not abstract:
            try:
                detail = await _fetch_biorxiv_detail(client, server, doi)
                if detail:
                    abstract = detail.get("abstract") or abstract
                    if detail.get("authors") and not authors:
                        authors = detail["authors"]
                    if detail.get("category"):
                        category = detail["category"]
                    else:
                        category = None
                else:
                    category = None
            except Exception as exc:
                logger.debug("bioRxiv detail enrich failed for %s: %s", doi, exc)
                category = None
        else:
            category = row.get("pubType")

        results.append(
            BiorxivPreprint(
                doi=doi,
                title=title,
                abstract=abstract,
                authors=authors,
                year=year,
                url=url or f"https://doi.org/{quote(doi)}" if doi else "",
                server=server,
                category=category if isinstance(category, str) else None,
            )
        )
        if len(results) >= max_results:
            break

    return results


async def _fetch_biorxiv_detail(
    client: httpx.AsyncClient,
    server: str,
    doi: str,
) -> Optional[dict]:
    """GET https://api.biorxiv.org/details/{server}/{doi}/na/json"""
    url = f"{BIORXIV_DETAILS_URL}/{server}/{doi}/na/json"
    resp = await client.get(url, timeout=20.0)
    if resp.status_code >= 400:
        return None
    payload = resp.json()
    collection = payload.get("collection") or []
    if not collection:
        return None
    item = collection[0]
    authors_raw = item.get("authors") or ""
    authors = [a.strip() for a in authors_raw.split(";") if a.strip()][:10]
    return {
        "abstract": (item.get("abstract") or "").strip(),
        "authors": authors,
        "category": item.get("category"),
    }


async def test_connection() -> dict:
    try:
        rows = await search_biorxiv("CRISPR", max_results=1)
        return {"status": "connected", "sample": rows[0].title if rows else None}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
