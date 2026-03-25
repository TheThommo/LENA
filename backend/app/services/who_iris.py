"""
WHO IRIS (Institutional Repository for Information Sharing) Service

WHO IRIS is built on DSpace and exposes a REST API for searching
WHO publications, guidelines, technical reports, and policy documents.

Docs: https://apps.who.int/iris/rest
Base: https://apps.who.int/iris/rest

This is completely free, no API key needed.
Rate limits are not formally documented but be respectful (1-2 req/sec).
"""

import httpx
from typing import Optional
from dataclasses import dataclass

BASE_URL = "https://apps.who.int/iris/rest"


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

    Args:
        query: Search term
        max_results: Number of results to return

    Returns:
        List of WHODocument objects
    """
    params = {
        "query": query,
        "expand": "metadata",
        "limit": min(max_results, 50),
    }

    headers = {
        "Accept": "application/json",
        "User-Agent": "LENA-Research-Agent/1.0",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/items/find-by-metadata-field",
            params=params,
            headers=headers,
        )

        # WHO IRIS search can also be done via the discover endpoint
        # If the metadata endpoint doesn't work, fall back to discover
        if response.status_code != 200:
            # Fallback: use the simpler search endpoint
            response = await client.get(
                f"{BASE_URL}/items",
                params={"query": query, "limit": min(max_results, 50)},
                headers=headers,
            )
            response.raise_for_status()

        data = response.json()

    documents = []

    # Handle both list and dict responses
    items = data if isinstance(data, list) else data.get("items", [])

    for item in items[:max_results]:
        # Extract metadata
        metadata = {}
        for m in item.get("metadata", []):
            key = m.get("key", "")
            value = m.get("value", "")
            if key not in metadata:
                metadata[key] = value
            elif isinstance(metadata[key], list):
                metadata[key].append(value)
            else:
                metadata[key] = [metadata[key], value]

        iris_id = str(item.get("id", ""))
        title = metadata.get("dc.title", item.get("name", "No title"))
        description = metadata.get("dc.description.abstract", "")
        year_str = metadata.get("dc.date.issued", "")
        year = None
        if year_str and len(year_str) >= 4 and year_str[:4].isdigit():
            year = int(year_str[:4])

        # Authors
        authors_raw = metadata.get("dc.contributor.author", [])
        if isinstance(authors_raw, str):
            authors_raw = [authors_raw]

        documents.append(WHODocument(
            iris_id=iris_id,
            title=title if isinstance(title, str) else str(title),
            description=description if isinstance(description, str) else "",
            authors=authors_raw if isinstance(authors_raw, list) else [str(authors_raw)],
            year=year,
            document_type=metadata.get("dc.type", "Unknown"),
            language=metadata.get("dc.language.iso", "en"),
            url=f"https://apps.who.int/iris/handle/{item.get('handle', '')}",
            pdf_url=None,  # Would need a second call to get bitstreams
        ))

    return documents


async def test_connection() -> dict:
    """Test the WHO IRIS API connection."""
    try:
        # Simple connectivity test: fetch recent items
        headers = {
            "Accept": "application/json",
            "User-Agent": "LENA-Research-Agent/1.0",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BASE_URL}/items",
                params={"limit": 3, "expand": "metadata"},
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        items = data if isinstance(data, list) else data.get("items", [])

        return {
            "source": "WHO IRIS",
            "status": "connected",
            "test_query": "recent items",
            "results_found": len(items),
            "sample_title": items[0].get("name", "N/A") if items else "N/A",
            "api_key_required": False,
        }
    except Exception as e:
        return {
            "source": "WHO IRIS",
            "status": "error",
            "error": str(e),
        }
