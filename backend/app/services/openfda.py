"""
openFDA adverse-event source — CAERS (CFSAN Adverse Event Reporting System).

For LENA this gives us consumer-reported adverse events on foods, supplements
and cosmetics. It's NOT peer-reviewed literature — treat it as a safety
signal and always label clearly in the UI.

API: https://api.fda.gov/food/event.json
Docs: https://open.fda.gov/apis/food/event/
Free; 240 req/min anon, 120k/day with OPENFDA_API_KEY.
"""

import os
import httpx
from dataclasses import dataclass
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.logging import get_logger

logger = get_logger("lena.sources")

BASE_URL = "https://api.fda.gov/food/event.json"


@dataclass
class CAERSEvent:
    report_number: str
    title: str
    summary: str
    url: str
    year: Optional[int]
    outcomes: list[str]


def _escape(q: str) -> str:
    return q.replace('"', '').strip()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)),
)
async def search_caers(query: str, max_results: int = 10) -> list[CAERSEvent]:
    """Search CAERS for adverse-event reports matching `query`.

    The product name OR reaction field is matched. Events without a usable
    product or reaction are dropped.
    """
    clean = _escape(query)
    if not clean:
        return []

    search_expr = (
        f'products.name_brand:"{clean}"'
        f'+OR+products.industry_name:"{clean}"'
        f'+OR+reactions:"{clean}"'
    )
    params = {"search": search_expr, "limit": max_results}
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
    events: list[CAERSEvent] = []
    for rec in results_raw[:max_results]:
        report_no = str(rec.get("report_number") or "")
        if not report_no:
            continue

        products = rec.get("products") or []
        product_names = [p.get("name_brand") for p in products if p.get("name_brand")]
        product_str = ", ".join(product_names[:3]) or "Unnamed product"

        reactions = [r for r in (rec.get("reactions") or []) if r]
        outcomes = [o for o in (rec.get("outcomes") or []) if o]

        title = f"Adverse event: {product_str}"
        if reactions:
            title += f" — {', '.join(reactions[:4])}"

        summary_parts: list[str] = []
        if reactions:
            summary_parts.append(f"Reactions reported: {'; '.join(reactions[:8])}.")
        if outcomes:
            summary_parts.append(f"Outcomes: {'; '.join(outcomes[:6])}.")
        consumer = rec.get("consumer") or {}
        age = consumer.get("age")
        age_unit = consumer.get("age_unit")
        gender = consumer.get("gender")
        if age and age_unit:
            summary_parts.append(f"Consumer: {age} {age_unit}.")
        if gender:
            summary_parts.append(f"Gender: {gender}.")

        year = None
        date_created = rec.get("date_created") or rec.get("date_started")
        if isinstance(date_created, str) and len(date_created) >= 4:
            try:
                year = int(date_created[:4])
            except ValueError:
                year = None

        events.append(
            CAERSEvent(
                report_number=report_no,
                title=title,
                summary=" ".join(summary_parts) or "CAERS consumer report.",
                url=f"https://www.accessdata.fda.gov/scripts/cfsan/AdverseEvents/index.cfm?caersId={report_no}",
                year=year,
                outcomes=outcomes,
            )
        )

    logger.info(f"CAERS: {len(events)} events for '{query}'")
    return events
