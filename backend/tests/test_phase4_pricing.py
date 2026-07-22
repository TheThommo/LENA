"""Phase 4 pricing: AccessTier, migration of $19 Pro → Researcher, source gating."""

from app.core.plan_tiers import (
    AccessTier,
    allowed_scored_sources,
    enrichment_allowed,
    filter_scored_sources,
    has_unlimited_searches,
    normalize_plan_slug,
)
from app.api.routes.billing import PlanKey, _tier_for_price_id
from app.core import config as cfg


def test_access_tier_enum_has_required_values():
    names = {t.value for t in AccessTier}
    assert "anonymous" in names
    assert "free" in names
    assert "researcher" in names
    assert "pro" in names
    assert "enterprise" in names
    assert "founding" in names


def test_legacy_19_pro_resolves_to_researcher_unlimited():
    # Simulated existing $19 (or legacy $30) pro row → Researcher
    tier = normalize_plan_slug("pro", monthly_price_cents=1900)
    assert tier == AccessTier.RESEARCHER
    assert has_unlimited_searches(tier) is True

    tier30 = normalize_plan_slug("pro", monthly_price_cents=3000)
    # <=2500 is researcher; 3000 legacy seed still defaults to researcher when
    # price alone is ambiguous — normalize treats >2500 and <4000 via default researcher
    # Actually code: <=2500 researcher, >=4000 pro, else researcher
    assert tier30 == AccessTier.RESEARCHER


def test_new_49_pro_resolves_to_pro():
    tier = normalize_plan_slug("pro", monthly_price_cents=4900)
    assert tier == AccessTier.PRO
    assert has_unlimited_searches(tier) is True


def test_source_gating():
    anon = allowed_scored_sources(AccessTier.ANONYMOUS)
    assert "pubmed" in anon
    assert "biorxiv" not in anon
    assert "consensus" not in anon

    free = allowed_scored_sources(AccessTier.FREE)
    assert "dailymed" in free
    assert "biorxiv" not in free

    researcher = allowed_scored_sources(AccessTier.RESEARCHER)
    assert "biorxiv" in researcher and "consensus" in researcher

    assert enrichment_allowed("chembl", AccessTier.RESEARCHER)
    assert enrichment_allowed("owkin", AccessTier.ENTERPRISE)
    assert not enrichment_allowed("owkin", AccessTier.PRO)
    assert enrichment_allowed("synapse", AccessTier.RESEARCHER, synapse_access="open")
    assert not enrichment_allowed("synapse", AccessTier.RESEARCHER, synapse_access="restricted")
    assert enrichment_allowed("synapse", AccessTier.PRO, synapse_access="restricted")


def test_filter_scored_sources_preserves_core_order():
    filtered = filter_scored_sources(
        ["pubmed", "biorxiv", "consensus", "openalex"],
        AccessTier.FREE,
    )
    assert filtered == ["pubmed", "openalex"]


def test_plan_key_includes_researcher_and_pro():
    # typing-only: ensure literals accepted by assigning
    keys: list[PlanKey] = [
        "researcher_monthly",
        "researcher_annual",
        "pro_monthly",
        "pro_annual",
        "pro_founding",
    ]
    assert len(keys) == 5


def test_tier_for_price_id_maps_legacy_to_researcher(monkeypatch):
    monkeypatch.setattr(cfg.settings, "stripe_price_pro_monthly", "price_legacy_19")
    monkeypatch.setattr(cfg.settings, "stripe_price_researcher_monthly", None)
    monkeypatch.setattr(cfg.settings, "stripe_price_pro_49_monthly", "price_new_49")
    monkeypatch.setattr(cfg.settings, "stripe_price_pro_founding", "price_founding")
    assert _tier_for_price_id("price_legacy_19") == "researcher"
    assert _tier_for_price_id("price_new_49") == "pro"
    assert _tier_for_price_id("price_founding") == "pro_founding"
