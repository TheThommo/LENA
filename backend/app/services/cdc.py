"""
CDC Public API Service

CDC provides several public data APIs. For LENA, the most relevant are:
1. CDC WONDER API - mortality and disease statistics
2. CDC Open Data (Socrata) - datasets on various health topics
3. MMWR (Morbidity and Mortality Weekly Report) - via CDC search

For MVP, we use the CDC Open Data portal (data.cdc.gov) which runs on
Socrata and provides a well-documented JSON API.

Docs: https://dev.socrata.com/docs/endpoints
No API key required, but an app token increases rate limits.
"""

import httpx
from typing import Optional
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.logging import get_logger

logger = get_logger("lena.sources")

# CDC Open Data (Socrata-based)
CDC_DATA_URL = "https://data.cdc.gov/resource"

# Some useful CDC dataset IDs
CDC_DATASETS = {
    "covid_cases": "9mfq-cb36",           # COVID-19 case surveillance
    "vaccinations": "rh2h-3yt2",           # COVID-19 vaccinations
    "chronic_disease": "g4ie-h725",        # Chronic disease indicators
    "nutrition": "hn4x-zwk7",             # Nutrition/physical activity
    "wonder_mortality": "bi63-dtpu",       # CDC WONDER mortality
}


@dataclass
class CDCDataset:
    dataset_id: str
    name: str
    description: str
    rows_count: int
    sample_data: list[dict]
    url: str


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)),
)
async def search_cdc_data(
    query: str,
    dataset_id: Optional[str] = None,
    max_results: int = 10,
) -> list[dict]:
    """
    Search CDC Open Data for relevant datasets or query a specific dataset.

    Args:
        query: Search term or SoQL query
        dataset_id: Specific dataset ID to query (if known)
        max_results: Number of rows to return

    Returns:
        List of data rows as dictionaries
    """
    headers = {
        "Accept": "application/json",
        "User-Agent": "LENA-Research-Agent/1.0",
    }

    if dataset_id:
        # Query a specific dataset using SoQL
        url = f"{CDC_DATA_URL}/{dataset_id}.json"
        params = {
            "$limit": min(max_results, 100),
            "$q": query,  # Full-text search
        }
    else:
        # Search the CDC data catalog via discovery API
        url = "https://api.us.socrata.com/api/catalog/v1"
        params = {
            "q": query,
            "domains": "data.cdc.gov",
            "limit": min(max_results, 20),
        }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

    # Catalog search returns a different format
    if not dataset_id:
        logger.debug(f"CDC catalog search for '{query}' returned results")
        results = []
        for result in data.get("results", []):
            resource = result.get("resource", {})
            results.append({
                "dataset_id": resource.get("id", ""),
                "name": resource.get("name", ""),
                "description": resource.get("description", "")[:200],
                "type": resource.get("type", ""),
                "updated_at": resource.get("updatedAt", ""),
                "url": result.get("permalink", ""),
            })
        return results

    logger.debug(f"CDC dataset search returned {len(data) if isinstance(data, list) else 0} rows")
    return data if isinstance(data, list) else []


async def get_dataset_info(dataset_id: str) -> Optional[CDCDataset]:
    """Get metadata about a specific CDC dataset."""
    headers = {
        "Accept": "application/json",
        "User-Agent": "LENA-Research-Agent/1.0",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get sample data
        response = await client.get(
            f"{CDC_DATA_URL}/{dataset_id}.json",
            params={"$limit": 3},
            headers=headers,
        )
        response.raise_for_status()
        sample = response.json()

    return CDCDataset(
        dataset_id=dataset_id,
        name=f"CDC Dataset {dataset_id}",
        description="",
        rows_count=len(sample),
        sample_data=sample if isinstance(sample, list) else [],
        url=f"https://data.cdc.gov/resource/{dataset_id}",
    )


async def test_connection() -> dict:
    """Test the CDC Open Data API connection."""
    try:
        # Search the catalog for something common
        results = await search_cdc_data("diabetes", max_results=3)
        return {
            "source": "CDC Open Data",
            "status": "connected",
            "test_query": "diabetes",
            "results_found": len(results),
            "sample_name": results[0].get("name", "N/A") if results else "N/A",
            "api_key_required": False,
            "note": "Uses Socrata Open Data API",
        }
    except Exception as e:
        return {
            "source": "CDC Open Data",
            "status": "error",
            "error": str(e),
        }
