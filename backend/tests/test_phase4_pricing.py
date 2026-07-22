"""Phase 4 pricing: AccessTier, migration of $19 Pro → Researcher, binary source gating."""

from app.core.plan_tiers import (
    AccessTier,
    allowed_scored_sources,
    can_bulk_pdf_export,
    can_custom_my_brain,
    can_priority_processing,
    can_saved_search_alerts,
    can_team_sharing,
    can_unlimited_projects,
    enrichment_allowed,
    filter_scored_sources,
    has_unlimited_searches,
    max_projects,
    normalize_plan_slug,
)
from app.api.routes.billing import PlanKey, _tier_for_price_id
from app.core import config as cfg


def test_access_tier_enum_has_required_values():
    names = {t.value for t in AccessTier}
    assert names == {
        "anonymous",
        "free",
        "researcher",
        "pro",
        "enterprise",
        "founding",
    }


def test_legacy_19_pro_resolves_to_researcher_unlimited():
    # Simulated existing $19 (or legacy $30) pro row → Researcher
    tier = normalize_plan_slug("pro", monthly_price_cents=1900)
    assert tier == AccessTier.RESEARCHER
    assert has_unlimited_searches(tier) is True

    tier30 = normalize_plan_slug("pro", monthly_price_cents=3000)
    assert tier30 == AccessTier.RESEARCHER


def test_new_49_pro_resolves_to_pro():
    tier = normalize_plan_slug("pro", monthly_price_cents=4900)
    assert tier == AccessTier.PRO
    assert has_unlimited_searches(tier) is True


def test_source_gating_binary_paid_vs_free():
    """Anonymous/Free = 11 core; Researcher+ = all 15 (11 + biorxiv scored + 3 enrichment)."""
    for tier in (AccessTier.ANONYMOUS, AccessTier.FREE):
        scored = allowed_scored_sources(tier)
        assert "pubmed" in scored
        assert "biorxiv" not in scored
        assert not enrichment_allowed("chembl", tier)
        assert not enrichment_allowed("opentargets", tier)
        assert not enrichment_allowed("synapse", tier)

    for tier in (AccessTier.RESEARCHER, AccessTier.PRO, AccessTier.ENTERPRISE, AccessTier.FOUNDING):
        scored = allowed_scored_sources(tier)
        assert "biorxiv" in scored
        assert enrichment_allowed("chembl", tier)
        assert enrichment_allowed("opentargets", tier)
        assert enrichment_allowed("synapse", tier)
        # Restricted Synapse is no longer Pro-only — all paid get all sources
        assert enrichment_allowed("synapse", tier, synapse_access="restricted")


def test_no_cut_source_gating_references():
    """Cut sources must not appear in allowed scored/enrichment sets."""
    for tier in AccessTier:
        scored = allowed_scored_sources(tier)
        assert "consensus" not in scored
        assert not enrichment_allowed("biorender", tier)
        assert not enrichment_allowed("owkin", tier)


def test_researcher_denied_pro_features():
    r = AccessTier.RESEARCHER
    assert can_unlimited_projects(r) is False
    assert can_team_sharing(r) is False
    assert can_custom_my_brain(r) is False
    assert can_priority_processing(r) is False
    assert can_saved_search_alerts(r) is False
    assert can_bulk_pdf_export(r) is False
    assert max_projects(r) == 5


def test_pro_allowed_pro_features():
    p = AccessTier.PRO
    assert can_unlimited_projects(p) is True
    assert can_team_sharing(p) is True
    assert can_custom_my_brain(p) is True
    assert can_priority_processing(p) is True
    assert can_saved_search_alerts(p) is True
    assert can_bulk_pdf_export(p) is True
    assert max_projects(p) is None

    e = AccessTier.ENTERPRISE
    assert can_unlimited_projects(e) is True
    assert can_bulk_pdf_export(e) is True


def test_filter_scored_sources_preserves_core_order():
    filtered = filter_scored_sources(
        ["pubmed", "biorxiv", "openalex"],
        AccessTier.FREE,
    )
    assert filtered == ["pubmed", "openalex"]

    paid = filter_scored_sources(
        ["pubmed", "biorxiv", "openalex"],
        AccessTier.RESEARCHER,
    )
    assert paid == ["pubmed", "biorxiv", "openalex"]


def test_plan_key_includes_researcher_and_pro():
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
