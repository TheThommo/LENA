"""E9: status is a pure function of confidence — never set independently."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.pulse_engine import (  # noqa: E402
    CONFIDENCE_STATUS_THRESHOLDS,
    PULSEReport,
    SourceResult,
    ValidationStatus,
    run_pulse_validation,
    status_for_confidence,
)
from evals.assertions import confidence_status_coherent  # noqa: E402


def test_status_for_confidence_thresholds():
    assert status_for_confidence(0.0) == ValidationStatus.INSUFFICIENT
    assert status_for_confidence(0.39) == ValidationStatus.INSUFFICIENT
    assert status_for_confidence(0.40) == ValidationStatus.EDGE_CASE
    assert status_for_confidence(0.79) == ValidationStatus.EDGE_CASE
    assert status_for_confidence(0.80) == ValidationStatus.VALIDATED
    assert status_for_confidence(1.0) == ValidationStatus.VALIDATED
    # Threshold table is the published contract (v2 bands)
    assert CONFIDENCE_STATUS_THRESHOLDS[0][0] == 0.80
    assert CONFIDENCE_STATUS_THRESHOLDS[1][0] == 0.40


def test_refresh_status_never_leaves_pending_for_known_confidence():
    report = PULSEReport(query="empty")
    report.source_count = 0
    report.status = ValidationStatus.PENDING  # stale independent assignment
    report.refresh_status()
    assert report.status == ValidationStatus.INSUFFICIENT
    assert confidence_status_coherent(
        report.confidence_ratio, report.status.value, defect_id="E9"
    ).passed


def test_to_dict_status_matches_confidence_even_if_field_stale():
    report = PULSEReport(query="stale")
    report.source_count = 2
    report.agreement_count = 2
    report.validated_results = [
        SourceResult(source_name="pubmed", title="A", summary="Finding reduced risk."),
        SourceResult(source_name="cochrane", title="B", summary="Finding reduced risk."),
    ]
    # Corrupt status independently — to_dict must still emit coherent label
    report.status = ValidationStatus.VALIDATED
    payload = report.to_dict()
    expected = status_for_confidence(payload["confidence_ratio"]).value
    assert payload["status"] == expected
    assert confidence_status_coherent(
        payload["confidence_ratio"], payload["status"], defect_id="E9"
    ).passed


@pytest.mark.asyncio
async def test_empty_and_single_source_status_coherent():
    empty = await run_pulse_validation("q", {})
    assert empty.status == status_for_confidence(empty.confidence_ratio)
    assert confidence_status_coherent(
        empty.confidence_ratio, empty.status.value, defect_id="E9"
    ).passed

    single = await run_pulse_validation(
        "q",
        {
            "pubmed": [
                SourceResult(
                    source_name="pubmed",
                    title="Preprint only",
                    summary="This medRxiv preprint is not peer-reviewed.",
                )
            ]
        },
    )
    assert single.status == status_for_confidence(single.confidence_ratio)
    assert single.status != ValidationStatus.VALIDATED


@pytest.mark.asyncio
async def test_g04_g12_e9_floors():
    from evals.runner import run_suite

    for case_id in ("G04", "G12", "G06"):
        results = await run_suite("golden", force_offline_rubric=True, case_filter=case_id)
        assert results, case_id
        for r in results:
            by = {a.name: a for a in r.assertion_results}
            assert by["confidence_status_coherent"].passed, by[
                "confidence_status_coherent"
            ].detail
            if "status_is" in by:
                assert by["status_is"].passed, by["status_is"].detail
            assert r.status == "insufficient_validation" or by[
                "confidence_status_coherent"
            ].passed
