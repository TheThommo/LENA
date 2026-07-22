"""
Open Targets Platform — target / disease evidence (GraphQL).

NOT scored by PULSE — enrichment "Target Evidence" only.
API: https://api.platform.opentargets.org/api/v4/graphql (no key)
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.logging import get_logger

logger = get_logger("lena.sources.opentargets")

GRAPHQL_URL = "https://api.platform.opentargets.org/api/v4/graphql"

_SEARCH_QUERY = """
query Search($q: String!) {
  search(queryString: $q, entityNames: ["target", "disease"], page: {index: 0, size: 8}) {
    hits {
      id
      entity
      name
      description
      score
    }
  }
}
"""


@dataclass
class OpenTargetsHit:
    id: str
    entity: str
    name: str
    description: str
    score: Optional[float]
    url: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)),
)
async def search_open_targets(query: str, max_results: int = 8) -> list[OpenTargetsHit]:
    """Search Open Targets for targets and diseases related to the query."""
    payload = {"query": _SEARCH_QUERY, "variables": {"q": query}}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(GRAPHQL_URL, json=payload)
        response.raise_for_status()
        data = response.json()

    hits_raw = (((data.get("data") or {}).get("search") or {}).get("hits")) or []
    hits: list[OpenTargetsHit] = []
    for row in hits_raw:
        entity = (row.get("entity") or "target").lower()
        oid = row.get("id") or ""
        name = row.get("name") or oid
        if not oid:
            continue
        if entity == "disease":
            url = f"https://platform.opentargets.org/disease/{oid}"
        else:
            url = f"https://platform.opentargets.org/target/{oid}"
        hits.append(
            OpenTargetsHit(
                id=oid,
                entity=entity,
                name=name,
                description=(row.get("description") or "")[:400],
                score=row.get("score"),
                url=url,
            )
        )
        if len(hits) >= max_results:
            break
    return hits
