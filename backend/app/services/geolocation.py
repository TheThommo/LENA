"""
IP Geolocation Service

Resolves client IP addresses to geographic information.
Uses ip-api.com (free tier, 45 req/min limit).
Implements simple LRU cache to avoid duplicate lookups.
"""

import httpx
import logging
from typing import Optional
from collections import OrderedDict

logger = logging.getLogger(__name__)

# Simple LRU cache (max 1000 entries)
_geo_cache: OrderedDict[str, dict] = OrderedDict()
_CACHE_MAX_SIZE = 1000


def _is_private_ip(ip: str) -> bool:
    """Check if IP is private/localhost (not geolocatable)."""
    private_ranges = [
        "127.",      # Loopback
        "192.168.",  # Private
        "10.",       # Private
        "172.16.", "172.17.", "172.18.", "172.19.",
        "172.20.", "172.21.", "172.22.", "172.23.",
        "172.24.", "172.25.", "172.26.", "172.27.",
        "172.28.", "172.29.", "172.30.", "172.31.",  # Private
        "localhost",
        "::1",       # IPv6 loopback
    ]
    return any(ip.startswith(prefix) for prefix in private_ranges)


async def geolocate_ip(ip: str) -> Optional[dict]:
    """
    Resolve IP address to geographic information.

    Returns:
        dict with keys: country, city, lat, lon
        Or None if private IP, rate-limited, or lookup fails
    """
    if not ip:
        return None

    # Check for private/localhost
    if _is_private_ip(ip):
        logger.debug(f"IP {ip} is private/localhost, skipping geolocation")
        return None

    # Check cache
    if ip in _geo_cache:
        logger.debug(f"Cache hit for IP {ip}")
        _geo_cache.move_to_end(ip)  # Mark as recently used
        return _geo_cache[ip]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "status,country,city,lat,lon,query"}
            )
            response.raise_for_status()
            data = response.json()

        # Check if lookup was successful
        if data.get("status") != "success":
            logger.warning(f"ip-api returned status={data.get('status')} for IP {ip}")
            return None

        # Build result dict
        result = {
            "country": data.get("country"),
            "city": data.get("city"),
            "lat": data.get("lat"),
            "lon": data.get("lon"),
        }

        # Cache the result
        _geo_cache[ip] = result
        if len(_geo_cache) > _CACHE_MAX_SIZE:
            # Remove oldest entry
            _geo_cache.popitem(last=False)

        logger.debug(f"Geolocated IP {ip} to {result['city']}, {result['country']}")
        return result

    except httpx.RequestError as e:
        # Network error or timeout
        logger.warning(f"Geolocation request failed for IP {ip}: {e}")
        return None
    except httpx.HTTPStatusError as e:
        # HTTP error (rate limit is 429)
        if e.response.status_code == 429:
            logger.warning(f"ip-api rate limit hit (45 req/min). Skipping geolocation.")
        else:
            logger.warning(f"ip-api HTTP {e.response.status_code} for IP {ip}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error geolocating IP {ip}: {e}")
        return None
