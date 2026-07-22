"""
Access tiers and entitlements for LENA pricing.

Tiers (Phase 4 / surgical update):
  anonymous | free | researcher | pro | enterprise | founding

Source access is binary:
  - Anonymous / Free → 11 original sources only
  - Researcher+ (incl. founding) → all 15 sources (11 + bioRxiv + ChEMBL + Open Targets + Synapse)

Researcher vs Pro is differentiated by collaboration / usage features, not sources.

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


# Core 11 sources (Anonymous / Free)
CORE_SOURCES: Set[str] = {
    "pubmed", "clinical_trials", "cochrane", "who_iris", "cdc", "openalex",
    "semantic_scholar", "europe_pmc", "dailymed", "ods_dsld", "openfda",
}

# Paid scored add-on (bioRxiv is the only new scored source after cuts)
PAID_SCORED_SOURCES: Set[str] = {"biorxiv"}

# Paid enrichment (not PULSE-scored)
PAID_ENRICHMENT_SOURCES: Set[str] = {"chembl", "opentargets", "synapse"}

# plan_tiers.slug values that grant Researcher-or-better unlimited search
RESEARCHER_PLUS_SLUGS: Set[str] = {
    "researcher",
    "pro",  # legacy slug for $19 rows until migration renames; also new $49 after migration uses pro
    "pro_founding",
    "founding",
    "professional",  # legacy seed
    "enterprise",
}

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


def is_paid_tier(tier: AccessTier) -> bool:
    return has_unlimited_searches(tier)


def is_pro_plus(tier: AccessTier) -> bool:
    """Pro and Enterprise get collaboration / power features."""
    return tier_rank(tier) >= tier_rank(AccessTier.PRO)


def allowed_scored_sources(tier: AccessTier) -> Set[str]:
    """Which ALL_SOURCES entries may be queried for this tier."""
    if is_paid_tier(tier):
        return set(CORE_SOURCES) | set(PAID_SCORED_SOURCES)
    return set(CORE_SOURCES)


def enrichment_allowed(name: str, tier: AccessTier, *, synapse_access: Optional[str] = None) -> bool:
    """
    Whether an enrichment source/card is available for this tier.

    Paid tiers get all enrichment sources (including Synapse open + restricted).
    synapse_access is accepted for call-site compatibility but no longer gates access.
    """
    _ = synapse_access
    if name in PAID_ENRICHMENT_SOURCES:
        return is_paid_tier(tier)
    return False


def filter_scored_sources(requested: Iterable[str], tier: AccessTier) -> list[str]:
    allowed = allowed_scored_sources(tier)
    return [s for s in requested if s in allowed]


# ── Feature gating (Researcher vs Pro) ──────────────────────────────


def can_unlimited_projects(tier: AccessTier) -> bool:
    return is_pro_plus(tier)


def can_team_sharing(tier: AccessTier) -> bool:
    return is_pro_plus(tier)


def can_custom_my_brain(tier: AccessTier) -> bool:
    return is_pro_plus(tier)


def can_priority_processing(tier: AccessTier) -> bool:
    return is_pro_plus(tier)


def can_saved_search_alerts(tier: AccessTier) -> bool:
    return is_pro_plus(tier)


def can_bulk_pdf_export(tier: AccessTier) -> bool:
    return is_pro_plus(tier)


def can_pdf_export(tier: AccessTier) -> bool:
    """Single PDF export — Researcher+."""
    return is_paid_tier(tier)


def can_content_ingest(tier: AccessTier) -> bool:
    return is_paid_tier(tier)


def max_projects(tier: AccessTier) -> Optional[int]:
    """None = unlimited. Researcher/Founding = 5. Free tiers use product defaults elsewhere."""
    if is_pro_plus(tier):
        return None
    if is_paid_tier(tier):
        return 5
    return None  # free/anon limits enforced by existing project gate
