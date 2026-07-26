"""E6: real temporal supersession / polarity hygiene (topic-agnostic)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.claim_pipeline import (  # noqa: E402
    ReconcileClass,
    _polarity_conflict,
    bind_claims_from_pulse_results,
    reconcile_claims,
    surfaceable_edge_cases,
)


def test_negated_reduce_is_not_positive_polarity():
    """'did not reduce' must not also count as a positive 'reduce' hit."""
    older = (
        "Earlier guidance supported aspirin for primary cardiovascular prevention "
        "in some older adults."
    )
    trial = (
        "In ASPREE, low-dose aspirin for primary prevention in adults ≥70 did not "
        "reduce cardiovascular disease versus placebo."
    )
    guideline = (
        "USPSTF recommends against initiating low-dose aspirin for primary "
        "prevention of CVD in adults 60 years or older."
    )
    assert _polarity_conflict(older, trial)
    assert _polarity_conflict(older, guideline)
    # Same-direction later evidence is not a contradiction
    assert not _polarity_conflict(trial, guideline)


def test_older_support_vs_newer_against_is_temporal_supersession():
    papers = [
        SimpleNamespace(
            source_name="pubmed",
            title="Older meta-analyses supporting aspirin primary prevention",
            year=2009,
            summary=(
                "Earlier evidence and guidance supported aspirin for primary "
                "cardiovascular prevention in some older adults based on "
                "reductions in nonfatal events."
            ),
            study_type="meta",
        ),
        SimpleNamespace(
            source_name="cdc",
            title="USPSTF communication: aspirin primary prevention",
            year=2022,
            summary=(
                "USPSTF recommends against initiating low-dose aspirin for "
                "primary prevention of CVD in adults 60 years or older (Grade D). "
                "This does not apply to secondary prevention."
            ),
            study_type="guideline",
        ),
    ]
    claims = bind_claims_from_pulse_results(papers)
    groups = reconcile_claims(claims)
    edges = surfaceable_edge_cases(groups)
    assert edges, "expected a surfaced divergence"
    assert any(
        e.get("classification") == ReconcileClass.TEMPORAL_SUPERSESSION.value
        for e in edges
    )
    blob = " ".join(
        f"{e.get('topic','')} {e.get('reason','')}" for e in edges
    ).lower()
    assert "primary" in blob


def test_agreeing_negative_findings_do_not_supersede_each_other():
    """ASPREE (no benefit) and USPSTF (against) agree directionally — not supersession."""
    papers = [
        SimpleNamespace(
            source_name="pubmed",
            title="ASPREE",
            year=2018,
            summary=(
                "In ASPREE, low-dose aspirin for primary prevention in adults ≥70 "
                "did not reduce cardiovascular disease and increased major "
                "haemorrhage versus placebo."
            ),
            study_type="rct",
        ),
        SimpleNamespace(
            source_name="cdc",
            title="USPSTF",
            year=2022,
            summary=(
                "USPSTF recommends against initiating low-dose aspirin for "
                "primary prevention of CVD in adults 60 years or older (Grade D)."
            ),
            study_type="guideline",
        ),
    ]
    claims = bind_claims_from_pulse_results(papers)
    groups = reconcile_claims(claims)
    edges = surfaceable_edge_cases(groups)
    assert not edges, f"same-direction negatives must not conflict: {edges}"


def test_same_database_different_papers_can_supersede():
    """Two PubMed papers on the same proposition must still be able to diverge (E6)."""
    papers = [
        SimpleNamespace(
            source_name="pubmed",
            title="Older meta-analyses supporting aspirin primary prevention",
            year=2009,
            summary=(
                "Earlier evidence and guidance supported aspirin for primary "
                "cardiovascular prevention in some older adults."
            ),
            study_type="meta",
        ),
        SimpleNamespace(
            source_name="pubmed",
            title="ASPREE: aspirin in healthy elderly primary prevention",
            year=2018,
            summary=(
                "In ASPREE, low-dose aspirin for primary prevention in adults ≥70 "
                "did not reduce cardiovascular disease versus placebo."
            ),
            study_type="rct",
        ),
    ]
    claims = bind_claims_from_pulse_results(papers)
    edges = surfaceable_edge_cases(reconcile_claims(claims))
    assert edges, "distinct PubMed papers must still surface supersession"
    assert any(
        e.get("classification") == ReconcileClass.TEMPORAL_SUPERSESSION.value
        for e in edges
    )
