"""
iHerb Product Data — RapidAPI connector.

Searches iHerb's supplement marketplace for product/brand verification data
including ratings, review counts, and pricing. Used by the supplement
verifier to assess market presence and consumer trust signals.
"""

import asyncio
from dataclasses import dataclass
from typing import Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger("lena.iherb")

RAPIDAPI_HOST = "iherb-product-data-api.p.rapidapi.com"
RAPIDAPI_KEY = "83af79f0abmshffb262311697c6ep138c2ajsnde711467d5e0"

# Endpoint patterns to try (API docs are poor, try all known patterns)
_SEARCH_ENDPOINTS = [
    "/search",
    "/product/search",
    "/products/search",
    "/v1/search",
    "/catalog/search",
]


@dataclass
class IHerbProduct:
    """Single iHerb product listing."""
    product_id: str = ""
    name: str = ""
    brand: str = ""
    rating: float = 0.0
    review_count: int = 0
    price: Optional[str] = None
    url: str = ""
    image_url: str = ""
    in_stock: bool = True

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "name": self.name,
            "brand": self.brand,
            "rating": self.rating,
            "review_count": self.review_count,
            "price": self.price,
            "url": self.url,
            "image_url": self.image_url,
            "in_stock": self.in_stock,
        }


@dataclass
class IHerbBrandSummary:
    """Aggregated brand presence data from iHerb."""
    brand_name: str = ""
    products_found: int = 0
    avg_rating: float = 0.0
    total_reviews: int = 0
    top_products: list = None  # list[IHerbProduct]
    brand_url: str = ""

    def __post_init__(self):
        if self.top_products is None:
            self.top_products = []

    def to_dict(self) -> dict:
        return {
            "brand_name": self.brand_name,
            "products_found": self.products_found,
            "avg_rating": round(self.avg_rating, 1),
            "total_reviews": self.total_reviews,
            "top_products": [p.to_dict() for p in self.top_products[:3]],
            "brand_url": self.brand_url,
        }


def _headers() -> dict:
    """RapidAPI auth headers. Uses env var if set, falls back to hardcoded key."""
    import os
    key = getattr(settings, "rapidapi_key", None) or os.getenv("RAPIDAPI_KEY", RAPIDAPI_KEY)
    return {
        "x-rapidapi-host": RAPIDAPI_HOST,
        "x-rapidapi-key": key,
    }


async def search_iherb(
    query: str,
    max_results: int = 10,
) -> list[IHerbProduct]:
    """Search iHerb for supplement products.

    Tries multiple endpoint patterns since the RapidAPI documentation
    is incomplete. Returns empty list on failure (non-blocking).
    """
    products: list[IHerbProduct] = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        for endpoint in _SEARCH_ENDPOINTS:
            try:
                url = f"https://{RAPIDAPI_HOST}{endpoint}"
                resp = await client.get(
                    url,
                    params={"keyword": query, "q": query, "query": query},
                    headers=_headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    products = _parse_search_response(data, max_results)
                    if products:
                        logger.info(f"iHerb search via {endpoint}: {len(products)} products for '{query}'")
                        return products
                elif resp.status_code == 404:
                    continue  # Try next endpoint
                else:
                    logger.debug(f"iHerb {endpoint} returned {resp.status_code}")
            except Exception as e:
                logger.debug(f"iHerb {endpoint} failed: {e}")
                continue

    logger.info(f"iHerb search: no working endpoint found for '{query}' (API may be unavailable)")
    return products


def _parse_search_response(data: dict | list, max_results: int) -> list[IHerbProduct]:
    """Parse iHerb API response into IHerbProduct objects.

    Handles multiple possible response formats since the API structure
    is not well documented.
    """
    products = []

    # Handle list response
    items = data if isinstance(data, list) else data.get("products", data.get("items", data.get("results", [])))

    if not isinstance(items, list):
        return products

    for item in items[:max_results]:
        if not isinstance(item, dict):
            continue
        products.append(IHerbProduct(
            product_id=str(item.get("id", item.get("product_id", item.get("sku", "")))),
            name=item.get("name", item.get("title", item.get("product_name", ""))),
            brand=item.get("brand", item.get("brand_name", item.get("manufacturer", ""))),
            rating=float(item.get("rating", item.get("average_rating", item.get("stars", 0)))),
            review_count=int(item.get("review_count", item.get("reviews", item.get("num_reviews", 0)))),
            price=item.get("price", item.get("current_price", item.get("sale_price", None))),
            url=item.get("url", item.get("product_url", item.get("link", ""))),
            image_url=item.get("image", item.get("image_url", item.get("thumbnail", ""))),
            in_stock=item.get("in_stock", item.get("available", True)),
        ))

    return products


async def get_brand_summary(
    brand: str,
    supplement_name: Optional[str] = None,
) -> IHerbBrandSummary:
    """Get aggregated brand data from iHerb.

    Searches for brand + supplement combination and computes aggregate
    metrics (avg rating, total reviews, product count).
    """
    query = f"{brand} {supplement_name}".strip() if supplement_name else brand
    products = await search_iherb(query, max_results=20)

    if not products:
        # Try brand-only search as fallback
        if supplement_name:
            products = await search_iherb(brand, max_results=20)

    # Filter to products matching the brand name (case-insensitive)
    brand_lower = brand.lower()
    brand_products = [p for p in products if brand_lower in p.brand.lower()] or products

    if not brand_products:
        return IHerbBrandSummary(brand_name=brand)

    total_reviews = sum(p.review_count for p in brand_products)
    ratings = [p.rating for p in brand_products if p.rating > 0]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

    return IHerbBrandSummary(
        brand_name=brand,
        products_found=len(brand_products),
        avg_rating=avg_rating,
        total_reviews=total_reviews,
        top_products=sorted(brand_products, key=lambda p: p.review_count, reverse=True)[:3],
        brand_url=f"https://www.iherb.com/search?kw={brand.replace(' ', '+')}",
    )
