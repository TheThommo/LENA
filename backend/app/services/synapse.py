"""
Synapse.org dataset search.

NOT scored by PULSE — enrichment datasets with access status.
Requires SYNAPSE_API_TOKEN (fail loud — never silently skip).
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.core.logging import get_logger
from app.core.source_keys import MissingSynapseApiTokenError

logger = get_logger("lena.sources.synapse")

BASE_URL = "https://rest.synapse.org"


@dataclass
class SynapseDataset:
    id: str
    name: str
    description: str
    access_status: str  # open | restricted
    url: str
    entity_type: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _require_token() -> str:
    token = settings.synapse_api_token
    if not token:
        raise MissingSynapseApiTokenError(
            "SYNAPSE_API_TOKEN is required to query Synapse.org. "
            "Set the environment variable — LENA will not silently skip this source."
        )
    return token


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)),
)
async def search_synapse(query: str, max_results: int = 8) -> list[SynapseDataset]:
    """Search Synapse entities (datasets / folders / files)."""
    token = _require_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    # Entity search endpoint
    params = {"q": query, "limit": min(max_results, 20)}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/search/entities",
            params=params,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    hits = data.get("hits") or data.get("results") or []
    datasets: list[SynapseDataset] = []
    for row in hits:
        # Response shapes vary — support both flat and nested
        entity = row.get("entity") or row
        eid = str(entity.get("id") or row.get("id") or "")
        name = entity.get("name") or row.get("name") or eid
        if not eid:
            continue
        description = (
            entity.get("description")
            or row.get("description")
            or ""
        )[:500]
        # Infer access: isControlled / concreteType restrictions
        restricted = bool(
            entity.get("isControlled")
            or entity.get("isRestricted")
            or row.get("is_controlled")
            or "Controlled" in str(entity.get("concreteType") or "")
        )
        access = "restricted" if restricted else "open"
        datasets.append(
            SynapseDataset(
                id=eid,
                name=name,
                description=description,
                access_status=access,
                url=f"https://www.synapse.org/#!Synapse:{eid}",
                entity_type=entity.get("concreteType") or row.get("type"),
            )
        )
        if len(datasets) >= max_results:
            break
    return datasets
