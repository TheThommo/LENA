"""
WHO IRIS (Institutional Repository for Information Sharing) Service

WHO IRIS is built on DSpace and exposes a REST API for searching
WHO publications, guidelines, technical reports, and policy documents.

Docs: https://iris.who.int/rest
Base: https://iris.who.int/rest

This is completely free, no API key needed.
Rate limits are not formally documented but be respectful (1-2 req/sec).
"""

import httpx
from typing import Optional
from dataclasses import dataclass

# DSpace 7 API (WHO IRIS migrated from /rest to /server/api)
BASE_URL = "https://iris.who.int/server/api"


@dataclass
class WHODocument:
    iris_id: str
    title: str
    description: str
    authors: list[str]
    year: Optional[int]
    document_type: str
    language: str
    url: str
    pdf_url: Optional[str]


async def search_who_iris(
    query: str,
    max_results: int = 10,
) -> list[WHODocument]:
    """
    Search WHO IRIS for publications and guidelines.

    Uses the DSpace 7 discovery endpoint for full-text search.

    Args:
        query: Search term
        max_results: Number of results to return

    Returns:
        List of WHODocument objects
    """
    # DSpace 7 discovery/search endpoint
    params = {
        "query": query,
        "size": min(max_results, 50),
        "dsoType": "item",
    }

    headers = {
        "Accept": "application/json",
        "User-Agent": "LENA-Research-Agent/1.0 (clinical research platform)",
    }

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(
            f"{BASE_URL}/discover/search/objects",
            params=params,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    documents = []

    # DSpace 7 search response structure
    search_results = (
        data.get("_embedded", {})
        .get("searchResult", {})
        .get("_embedded", {})
        .get("objects", [])
    )

    for obj in search_results[:max_results]:
        item = obj.get("_embedded", {}).get("indexableObject", {})
        if not item:
            continue

        iris_id = str(item.get("id", ""))

        # Extract metadata from DSpace 7 format
        metadata = item.get("metadata", {})

        title = _get_metadata_value(metadata, "dc.title", "No title")
        description = _get_metadata_value(metadata, "dc.description.abstract", "")
        year_str = _get_metadata_value(metadata, "dc.date.issued", "")
        doc_type = _get_metadata_value(metadata, "dc.type", "Unknown")
        language = _get_metadata_value(metadata, "dc.language.iso", "en")

        year = None
        if year_str and len(year_str) >= 4 and year_str[:4].isdigit():
            year = int(year_str[:4])

        # Authors (can have multiple values)
        authors = _get_metadata_values(metadata, "dc.contributor.author")

        # Build handle URL
        handle = item.get("handle", "")
        item_url = f"https://iris.who.int/handle/{handle}" if handle else ""

        documents.append(WHODocument(
            iris_id=iris_id,
            title=title,
            description=description,
            authors=authors,
            year=year,
            document_type=doc_type,
            language=language,
            url=item_url,
            pdf_url=None,
        ))

    return documents


def _get_metadata_value(metadata: dict, key: str, default: str = "") -> str:
    """Extract a single metadata value from DSpace 7 format."""
    values = metadata.get(key, [])
    if values and isinstance(values, list) and len(values) > 0:
        return values[0].get("value", default)
    return default


def _get_metadata_values(metadata: dict, key: str) -> list[str]:
    """Extract all metadata values for a key from DSpace 7 format."""
    values = metadata.get(key, [])
    if isinstance(values, list):
        return [v.get("value", "") for v in values if v.get("value")]
    return []


async def test_connection() -> dict:
    """Test the WHO IRIS API connection using DSpace 7 discovery search."""
    try:
        docs = await search_who_iris("malaria prevention", max_results=3)
        return {
            "source": "WHO IRIS",
            "status": "connected",
            "test_query": "malaria prevention",
            "results_found": len(docs),
            "sample_title": docs[0].title if docs else "N/A",
            "api_key_required": False,
        }
    except Exception as e:
        return {
            "source": "WHO IRIS",
            "status": "error",
            "error": str(e),
        }
