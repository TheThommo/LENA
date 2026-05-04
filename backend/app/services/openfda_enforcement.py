"""
openFDA Food Enforcement — FDA recalls and safety alerts for supplements.

Gives LENA recall history: Class I (dangerous), Class II (moderate),
Class III (unlikely harm). Combined with CAERS adverse events this
lets us compute a Supplement Trust Score.

API: https://api.fda.gov/food/enforcement.json
Docs: https://open.fda.gov/apis/food/enforcement/
Free; 240 req/min anon, 120k/day with OPENFDA_API_KEY.
"""

import os
import httpx
from dataclasses import dataclass, field
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.logging import get_logger

logger = get_logger("lena.sources")

BASE_URL = "https://api.fda.gov/food/enforcement.json"


@dataclass
class FDARecall:
    recall_number: str
    product_description: str
    reason_for_recall: str
    classification: str  # "Class I", "Class II", "Class III"
    status: str  # "Ongoing", "Completed", "Terminated"
    recalling_firm: str
    recall_date: Optional[str] = None
    voluntary_mandated: Optional[str] = None
    distribution_pattern: Optional[str] = None
    url: str = ""
    severity: str = "unknown"  # "critical", "moderate", "low"


def _escape(q: str) -> str:
    return q.replace('"', '').strip()


def _classify_severity(classification: str) -> str:
    """Map FDA recall class to human-readable severity."""
    c = classification.strip().lower()
    if "i" in c and "ii" not in c:
        return "critical"
    elif "ii" in c and "iii" not in c:
        return "moderate"
    elif "iii" in c:
        return "low"
    return "unknown"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)),
)
async def search_recalls(query: str, max_results: int = 20) -> list[FDARecall]:
    """Search FDA food enforcement (recall) database for a supplement name.

    Searches product_description and recalling_firm fields. Returns recalls
    sorted by date (newest first).
    """
    clean = _escape(query)
    if not clean:
        return []

    search_expr = (
        f'product_description:"{clean}"'
        f'+OR+recalling_firm:"{clean}"'
        f'+OR+reason_for_recall:"{clean}"'
    )
    params = {"search": search_expr, "limit": max_results, "sort": "recall_initiation_date:desc"}
    api_key = os.getenv("OPENFDA_API_KEY")
    if api_key:
        params["api_key"] = api_key

    async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "LENA/1.0"}) as client:
        try:
            resp = await client.get(BASE_URL, params=params)
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return []
            raise

    results_raw = data.get("results") or []
    recalls: list[FDARecall] = []

    for rec in results_raw[:max_results]:
        recall_number = rec.get("recall_number", "")
        if not recall_number:
            continue

        classification = rec.get("classification", "")
        recalls.append(
            FDARecall(
                recall_number=recall_number,
                product_description=rec.get("product_description", ""),
                reason_for_recall=rec.get("reason_for_recall", ""),
                classification=classification,
                status=rec.get("status", ""),
                recalling_firm=rec.get("recalling_firm", ""),
                recall_date=rec.get("recall_initiation_date"),
                voluntary_mandated=rec.get("voluntary_mandated"),
                distribution_pattern=rec.get("distribution_pattern"),
                url=f"https://api.fda.gov/food/enforcement.json?search=recall_number:{recall_number}",
                severity=_classify_severity(classification),
            )
        )

    logger.info(f"FDA Enforcement: {len(recalls)} recalls for '{query}'")
    return recalls


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)),
)
async def count_adverse_events(query: str) -> dict:
    """Get aggregate adverse event counts from openFDA CAERS for a supplement.

    Returns a dict with total count, serious outcome counts, and date range.
    This is a COUNT query — much cheaper than fetching individual reports.
    """
    clean = _escape(query)
    if not clean:
        return {"total": 0, "serious": 0, "deaths": 0, "hospitalizations": 0}

    caers_url = "https://api.fda.gov/food/event.json"
    search_expr = (
        f'products.name_brand:"{clean}"'
        f'+OR+products.industry_name:"{clean}"'
    )
    params = {"search": search_expr, "count": "outcomes"}
    api_key = os.getenv("OPENFDA_API_KEY")
    if api_key:
        params["api_key"] = api_key

    async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "LENA/1.0"}) as client:
        try:
            resp = await client.get(caers_url, params=params)
            if resp.status_code == 404:
                return {"total": 0, "serious": 0, "deaths": 0, "hospitalizations": 0}
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return {"total": 0, "serious": 0, "deaths": 0, "hospitalizations": 0}
            raise

    results = data.get("results") or []
    total = sum(r.get("count", 0) for r in results)
    deaths = 0
    hospitalizations = 0
    serious = 0

    for r in results:
        term = (r.get("term") or "").upper()
        count = r.get("count", 0)
        if "DEATH" in term:
            deaths += count
            serious += count
        elif "HOSPITALIZATION" in term or "HOSPITAL" in term:
            hospitalizations += count
            serious += count
        elif "LIFE THREATENING" in term or "DISABILITY" in term:
            serious += count

    logger.info(f"CAERS counts for '{query}': total={total}, serious={serious}, deaths={deaths}")
    return {
        "total": total,
        "serious": serious,
        "deaths": deaths,
        "hospitalizations": hospitalizations,
    }
