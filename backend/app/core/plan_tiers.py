"""
Access tiers and source gating for LENA pricing.

Tiers (Phase 4):
  anonymous | free | researcher | pro | enterprise | founding

Existing $19 Pro subscribers resolve to **researcher** (same price, unlimited) —
nobody worse off.
"""

from __future__ import annotations

from enum import Enum
from typing import Iterable, Optional, Set


class AccessTier(str, Enum):
    ANONYMOUS = "anonymous"
    FREE = "free"
    RESEARCHER = "researcher"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    FOUNDING = "founding"


# Core 11 sources (Free+)
CORE_SOURCES: Set[str] = {
    "pubmed", "clinical_trials", "cochrane", "who_iris", "cdc", "openalex",
    "semantic_scholar", "europe_pmc", "dailymed", "ods_dsld", "openfda",
}

RESEARCHER_SCORED_SOURCES: Set[str] = {"biorxiv", "consensus"}

RESEARCHER_ENRICHMENT: Set[str] = {
    "chembl", "opentargets", "biorender", "synapse_open",
}

PRO_ENRICHMENT: Set[str] = {"synapse_restricted"}

ENTERPRISE_ENRICHMENT: Set[str] = {"owkin"}

# plan_tiers.slug values that grant Researcher-or-better unlimited search
RESEARCHER_PLUS_SLUGS: Set[str] = {
    "researcher",
    "pro",  # legacy slug for $19 rows until migration renames; also new $49 after migration uses pro
    "pro_founding",
    "founding",
    "professional",  # legacy seed
    "enterprise",
}

# After migration: slug `researcher` = $19; slug `pro` = $49
PAID_UNLIMITED_SLUGS: Set[str] = RESEARCHER_PLUS_SLUGS


def normalize_plan_slug(slug: Optional[str], *, monthly_price_cents: Optional[int] = None) -> AccessTier:
    """
    Map a plan_tiers slug (and optional price) to AccessTier.

    Migration rule: legacy $19 (or seeded $30) `pro` rows → RESEARCHER.
    New $49 `pro` → PRO.
    """
    if not slug:
        return AccessTier.FREE
    s = slug.strip().lower()
    if s in ("anonymous", "anon"):
        return AccessTier.ANONYMOUS
    if s in ("free", "starter"):
        return AccessTier.FREE
    if s in ("researcher",):
        return AccessTier.RESEARCHER
    if s in ("pro_founding", "founding"):
        return AccessTier.FOUNDING
    if s in ("enterprise",):
        return AccessTier.ENTERPRISE
    if s == "pro":
        # Price-based split: <= $25/mo treated as legacy Researcher
        if monthly_price_cents is not None and monthly_price_cents <= 2500:
            return AccessTier.RESEARCHER
        if monthly_price_cents is not None and monthly_price_cents >= 4000:
            return AccessTier.PRO
        # Default: treat bare `pro` without price as Researcher (safer for existing subs)
        return AccessTier.RESEARCHER
    if s in ("professional",):
        return AccessTier.PRO
    return AccessTier.FREE


def tier_rank(tier: AccessTier) -> int:
    order = {
        AccessTier.ANONYMOUS: 0,
        AccessTier.FREE: 1,
        AccessTier.RESEARCHER: 2,
        AccessTier.FOUNDING: 2,  # founding ≈ researcher benefits + badge
        AccessTier.PRO: 3,
        AccessTier.ENTERPRISE: 4,
    }
    return order.get(tier, 0)


def has_unlimited_searches(tier: AccessTier) -> bool:
    return tier_rank(tier) >= tier_rank(AccessTier.RESEARCHER)


def allowed_scored_sources(tier: AccessTier) -> Set[str]:
    """Which ALL_SOURCES entries may be queried for this tier."""
    if tier == AccessTier.ANONYMOUS:
        return set(CORE_SOURCES)
    if tier == AccessTier.FREE:
        return set(CORE_SOURCES)
    # Researcher+
    return set(CORE_SOURCES) | set(RESEARCHER_SCORED_SOURCES)


def enrichment_allowed(name: str, tier: AccessTier, *, synapse_access: Optional[str] = None) -> bool:
    """Whether an enrichment source/card is available for this tier."""
    rank = tier_rank(tier)
    if name in ("chembl", "opentargets", "biorender"):
        return rank >= tier_rank(AccessTier.RESEARCHER)
    if name == "synapse":
        if synapse_access == "restricted":
            return rank >= tier_rank(AccessTier.PRO)
        return rank >= tier_rank(AccessTier.RESEARCHER)
    if name == "owkin":
        return rank >= tier_rank(AccessTier.ENTERPRISE)
    return False


def filter_scored_sources(requested: Iterable[str], tier: AccessTier) -> list[str]:
    allowed = allowed_scored_sources(tier)
    return [s for s in requested if s in allowed]
