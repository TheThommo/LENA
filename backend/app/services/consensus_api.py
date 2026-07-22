"""
Consensus.app academic search — SCORED PULSE validation source.

Requires CONSENSUS_API_KEY (fail loud — never silently skip).
API: GET https://api.consensus.app/v1/quick_search
Auth: x-api-key header (per Consensus OpenAPI securitySchemes).
UI label: "Additional academic sources"
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.core.logging import get_logger
from app.core.source_keys import MissingConsensusApiKeyError

logger = get_logger("lena.sources.consensus")

BASE_URL = "https://api.consensus.app"


@dataclass
class ConsensusPaper:
    title: str
    abstract: str
    url: str
    doi: Optional[str]
    year: Optional[int]
    authors: list[str]
    study_type: Optional[str] = None


def _require_key() -> str:
    key = settings.consensus_api_key
    if not key:
        raise MissingConsensusApiKeyError(
            "CONSENSUS_API_KEY is required to query Consensus.app. "
            "Set the environment variable — LENA will not silently skip this source."
        )
    return key


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)),
)
async def search_consensus(query: str, max_results: int = 10) -> list[ConsensusPaper]:
    """Quick-search Consensus for peer-reviewed papers."""
    key = _require_key()
    headers = {
        "x-api-key": key,
        "accept": "application/json",
    }
    params = {"query": query}
    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.get(
            f"{BASE_URL}/v1/quick_search",
            params=params,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    # Response may be a list or {results|papers|data: [...]}
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = data.get("results") or data.get("papers") or data.get("data") or []
    else:
        rows = []

    papers: list[ConsensusPaper] = []
    for row in rows:
        title = (row.get("title") or row.get("paper_title") or "").strip()
        if not title:
            continue
        abstract = (
            row.get("abstract")
            or row.get("tldr")
            or row.get("summary")
            or ""
        )
        doi = row.get("doi")
        url = row.get("url") or row.get("link") or (f"https://doi.org/{doi}" if doi else "")
        year = row.get("year") or row.get("publication_year")
        if year is not None:
            try:
                year = int(year)
            except (TypeError, ValueError):
                year = None
        authors_raw = row.get("authors") or []
        if isinstance(authors_raw, str):
            authors = [a.strip() for a in authors_raw.split(",") if a.strip()][:8]
        else:
            authors = []
            for a in authors_raw[:8]:
                if isinstance(a, dict):
                    authors.append(a.get("name") or a.get("display_name") or "")
                else:
                    authors.append(str(a))
            authors = [a for a in authors if a]
        papers.append(
            ConsensusPaper(
                title=title,
                abstract=abstract[:2000] if isinstance(abstract, str) else "",
                url=url,
                doi=doi,
                year=year,
                authors=authors,
                study_type=row.get("study_type") or row.get("study_design"),
            )
        )
        if len(papers) >= max_results:
            break
    return papers
