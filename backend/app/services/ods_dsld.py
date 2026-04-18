"""
NIH Office of Dietary Supplements — DSLD (Dietary Supplement Label Database)

DSLD holds the labeled contents of > 150k US supplement products.
Useful for LENA as a grounded source of what supplements ARE on the market,
their declared ingredients, serving sizes, and claims.

API: https://api.ods.od.nih.gov/dsld/v9/
Docs: https://dsld.od.nih.gov/docs
Free, no API key, public.
"""

import httpx
from dataclasses import dataclass
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.logging import get_logger

logger = get_logger("lena.sources")

BASE_URL = "https://api.ods.od.nih.gov/dsld/v9"


@dataclass
class DSLDProduct:
    dsld_id: str
    title: str          # product full name
    brand: str
    summary: str        # ingredient list + serving info
    url: str
    year: Optional[int]


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)),
)
async def search_dsld(query: str, max_results: int = 10) -> list[DSLDProduct]:
    """Search DSLD for supplement products matching `query`."""
    params = {
        "method": "by_keyword",
        "q": query,
        "size": max_results,
        "from": 0,
    }
    async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "LENA/1.0"}) as client:
        resp = await client.get(f"{BASE_URL}/search-filter", params=params)
        resp.raise_for_status()
        data = resp.json()

    hits = (data.get("hits") or {}).get("hits") or []
    products: list[DSLDProduct] = []
    for hit in hits[:max_results]:
        src = hit.get("_source") or {}
        dsld_id = str(hit.get("_id") or src.get("id") or "")
        if not dsld_id:
            continue

        full_name = src.get("fullName") or src.get("productName") or "Unknown product"
        brand = src.get("brandName") or ""
        serving = src.get("servingSizes") or src.get("servingSize") or ""

        ingredient_lines: list[str] = []
        ingredients = src.get("ingredientRows") or src.get("ingredients") or []
        for ing in ingredients[:15]:
            name = ing.get("name") or ing.get("ingredientName") or ""
            quantity = ing.get("quantity") or ing.get("amount") or ""
            unit = ing.get("unit") or ""
            if name:
                bits = [name]
                if quantity:
                    bits.append(f"{quantity}{unit}".strip())
                ingredient_lines.append(" ".join(bits))

        summary_parts: list[str] = []
        if brand:
            summary_parts.append(f"Brand: {brand}.")
        if serving:
            summary_parts.append(f"Serving: {serving}.")
        if ingredient_lines:
            summary_parts.append("Ingredients: " + "; ".join(ingredient_lines))

        year = None
        off_market_date = src.get("offMarketDate") or src.get("onMarketDate")
        if isinstance(off_market_date, str) and len(off_market_date) >= 4:
            try:
                year = int(off_market_date[:4])
            except ValueError:
                year = None

        products.append(
            DSLDProduct(
                dsld_id=dsld_id,
                title=full_name,
                brand=brand,
                summary=" ".join(summary_parts) or "Supplement label data.",
                url=f"https://dsld.od.nih.gov/label/{dsld_id}",
                year=year,
            )
        )

    logger.info(f"DSLD: {len(products)} products for '{query}'")
    return products
