"""
In-Memory Search Result Cache

Simple, fast cache for search results with TTL and size limits.
No external dependencies - uses standard Python dict + timestamps.

Key features:
- Cache key: hash of (query + sources + include_alt_medicine)
- TTL: 5 minutes
- Max entries: 500
- Thread-safe via GIL (Python 3.7+)
"""

import hashlib
import time
from typing import Optional, Any
from app.core.logging import get_logger

logger = get_logger("lena.sources")

# Global cache store
_CACHE_STORE: dict[str, dict[str, Any]] = {}
_CACHE_MAX_ENTRIES = 500
_CACHE_TTL_SECONDS = 300  # 5 minutes


def _make_cache_key(
    query: str,
    sources: Optional[list[str]] = None,
    include_alt_medicine: bool = True,
) -> str:
    """
    Generate a deterministic cache key from search parameters.

    Args:
        query: Search query
        sources: List of source names (None = all)
        include_alt_medicine: Whether alt medicine is included

    Returns:
        Cache key string
    """
    key_parts = [
        query,
        ",".join(sorted(sources)) if sources else "all_sources",
        str(include_alt_medicine),
    ]
    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def get_cached_result(
    query: str,
    sources: Optional[list[str]] = None,
    include_alt_medicine: bool = True,
) -> Optional[dict]:
    """
    Retrieve a cached search result if it exists and hasn't expired.

    Args:
        query: Search query
        sources: List of source names
        include_alt_medicine: Whether alt medicine is included

    Returns:
        Cached result dict or None if not found/expired
    """
    cache_key = _make_cache_key(query, sources, include_alt_medicine)

    if cache_key not in _CACHE_STORE:
        return None

    entry = _CACHE_STORE[cache_key]
    age = time.time() - entry["created_at"]

    if age > _CACHE_TTL_SECONDS:
        # Expired - remove it
        del _CACHE_STORE[cache_key]
        logger.debug(f"Cache entry expired: {cache_key}")
        return None

    logger.debug(f"Cache hit: {cache_key} (age={age:.1f}s)")
    return entry["result"]


def cache_result(
    query: str,
    result: dict,
    sources: Optional[list[str]] = None,
    include_alt_medicine: bool = True,
) -> None:
    """
    Store a search result in the cache.

    Automatically evicts oldest entry if cache is full.

    Args:
        query: Search query
        result: Result dict to cache
        sources: List of source names
        include_alt_medicine: Whether alt medicine is included
    """
    cache_key = _make_cache_key(query, sources, include_alt_medicine)

    # Evict oldest entry if cache is full
    if len(_CACHE_STORE) >= _CACHE_MAX_ENTRIES:
        oldest_key = min(
            _CACHE_STORE.keys(),
            key=lambda k: _CACHE_STORE[k]["created_at"],
        )
        del _CACHE_STORE[oldest_key]
        logger.debug(f"Cache evicted oldest entry: {oldest_key}")

    _CACHE_STORE[cache_key] = {
        "result": result,
        "created_at": time.time(),
    }
    logger.debug(f"Cache stored: {cache_key} (size={len(_CACHE_STORE)})")


def clear_cache() -> None:
    """Clear all cached results."""
    _CACHE_STORE.clear()
    logger.info("Cache cleared")


def get_cache_stats() -> dict:
    """Get cache statistics."""
    return {
        "total_entries": len(_CACHE_STORE),
        "max_entries": _CACHE_MAX_ENTRIES,
        "ttl_seconds": _CACHE_TTL_SECONDS,
        "usage_percent": round((len(_CACHE_STORE) / _CACHE_MAX_ENTRIES) * 100, 1),
    }
