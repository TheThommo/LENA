"""
Tenant Detection

Extracts tenant identifier from request (subdomain, header, or default).
Supports multi-tenant architecture where each tenant is isolated.

Subdomain pattern: {tenant_slug}.lena-research.com
Default tenant: "lena" (the platform itself)
"""

from fastapi import Request
from typing import Optional


def detect_tenant(request: Request) -> str:
    """
    Detect tenant from request.

    Priority:
    1. X-Tenant-ID header (for API clients)
    2. Subdomain from Host header (e.g., "acme.lena-research.com" -> "acme")
    3. Default: "lena"

    Args:
        request: FastAPI request

    Returns:
        Tenant slug (string)
    """
    # Check X-Tenant-ID header first
    tenant_id_header = request.headers.get("X-Tenant-ID")
    if tenant_id_header:
        return tenant_id_header.strip().lower()

    # Extract subdomain from Host header
    host = request.headers.get("Host", "")
    if host:
        # Remove port if present
        hostname = host.split(":")[0].lower()

        # Railway URLs (*.up.railway.app) are not tenant subdomains
        if "railway.app" in hostname:
            return "lena"

        # Check if it's a subdomain (not the root domain)
        parts = hostname.split(".")
        if len(parts) >= 3:
            # Extract subdomain (first part before first dot)
            subdomain = parts[0]
            # Skip "www" prefix if present
            if subdomain != "www":
                return subdomain

    # Default to "lena" (platform itself)
    return "lena"
