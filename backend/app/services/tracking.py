"""
UTM & Referrer Tracking Service

Parses UTM parameters from query strings and classifies referrer sources.
Supports multi-channel attribution tracking for the freemium funnel.
"""

import logging
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def parse_utm_params(query_params: dict) -> dict:
    """
    Extract UTM parameters from query string.

    Args:
        query_params: FastAPI query parameters dict

    Returns:
        dict with keys: utm_source, utm_medium, utm_campaign, utm_term, utm_content
        (all values are strings or None)
    """
    return {
        "utm_source": query_params.get("utm_source"),
        "utm_medium": query_params.get("utm_medium"),
        "utm_campaign": query_params.get("utm_campaign"),
        "utm_term": query_params.get("utm_term"),
        "utm_content": query_params.get("utm_content"),
    }


def classify_referrer(referrer: Optional[str]) -> dict:
    """
    Classify referrer source into business-meaningful categories.

    Args:
        referrer: Raw Referrer header value (usually full URL)

    Returns:
        dict with keys:
            raw: original referrer string
            domain: extracted domain (e.g., "google.com")
            category: one of [direct, organic_search, social, email, paid, referral, unknown]
    """
    if not referrer or not referrer.strip():
        return {
            "raw": None,
            "domain": None,
            "category": "direct",
        }

    referrer = referrer.strip()

    # Parse domain from URL
    try:
        parsed = urlparse(referrer)
        domain = parsed.netloc.lower() if parsed.netloc else None
    except Exception:
        domain = None

    # Classify by domain patterns
    if not domain:
        return {
            "raw": referrer,
            "domain": None,
            "category": "unknown",
        }

    # Organic search
    organic_engines = [
        "google.com", "google.",
        "bing.com", "bing.",
        "duckduckgo.com",
        "yahoo.com", "yahoo.",
        "baidu.com",
        "yandex.com", "yandex.",
    ]
    if any(domain.startswith(engine) for engine in organic_engines):
        return {
            "raw": referrer,
            "domain": domain,
            "category": "organic_search",
        }

    # Social media
    social_platforms = [
        "facebook.com", "fb.com",
        "twitter.com", "x.com",
        "linkedin.com",
        "instagram.com",
        "reddit.com",
        "youtube.com",
        "tiktok.com",
        "pinterest.com",
        "nextdoor.com",
    ]
    if any(domain.startswith(platform) for platform in social_platforms):
        return {
            "raw": referrer,
            "domain": domain,
            "category": "social",
        }

    # Email / marketing platforms
    email_platforms = [
        "mail.google.com",
        "outlook.live.com",
        "yahoo.mail",
        "mailchimp.com",
        "klaviyo.com",
        "sendgrid.com",
        "constant contact",
    ]
    if any(domain.startswith(platform) for platform in email_platforms):
        return {
            "raw": referrer,
            "domain": domain,
            "category": "email",
        }

    # Paid ads (Facebook Ads, Google Ads, etc.)
    paid_platforms = [
        "ads.google.com",
        "facebook.com/ads",
        "linkedin.com/ads",
        "adroll.com",
        "bing.com/ads",
    ]
    if any(domain.startswith(platform) for platform in paid_platforms):
        return {
            "raw": referrer,
            "domain": domain,
            "category": "paid",
        }

    # Generic referral (all other domains)
    return {
        "raw": referrer,
        "domain": domain,
        "category": "referral",
    }
