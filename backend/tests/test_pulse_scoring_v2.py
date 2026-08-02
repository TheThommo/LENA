"""PULSE scoring v2: responding-universe denominator, evidence gate, Pharma mode."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.pulse_engine import (  # noqa: E402
    SourceResult,
    run_pulse_validation,
    source_class_for,
    status_for_confidence,
)
from app.services.search_orchestrator import (  # noqa: E402
    VALID_MODES,
    _tag_result_modes,
)


def _paper(source: str, *, title: str, summary: str, keywords: list[str] | None = None) -> SourceResult:
    return SourceResult(
        source_name=source,
        title=title,
        summary=summary,
        url=f"https://example.com/{source}",
        doi=None,
        pmid=None,
        year=2024,
        keywords=keywords or [],
        authors=["Smith A"],
    )


@pytest.mark.asyncio
async def test_empty_databases_do_not_dilute_responding_universe():
    """Confidence is scored only on sources that returned papers."""
    results = {
        "pubmed": [
            _paper(
                "pubmed",
                title="Empagliflozin reduces heart failure hospitalisation",
                summary=(
                    "In patients with HFrEF, empagliflozin reduced cardiovascular death "
                    "or hospitalisation for heart failure versus placebo."
                ),
                keywords=["empagliflozin", "heart", "failure"],
            ),
            _paper(
                "pubmed",
                title="SGLT2 inhibitors and HFrEF outcomes",
                summary=(
                    "SGLT2 inhibitors including empagliflozin reduced hospitalisation "
                    "for heart failure in HFrEF populations."
                ),
                keywords=["sglt2", "heart", "failure"],
            ),
        ],
        "clinical_trials": [
            _paper(
                "clinical_trials",
                title="EMPEROR-Reduced trial of empagliflozin in HFrEF",
                summary=(
                    "This randomised trial found empagliflozin reduced the combined risk "
                    "of cardiovascular death or heart failure hospitalisation."
                ),
                keywords=["empagliflozin", "trial", "hfref"],
            ),
        ],
        "dailymed": [
            _paper(
                "dailymed",
                title="Empagliflozin tablets prescribing information",
                summary=(
                    "FDA label: empagliflozin is indicated to reduce cardiovascular death "
                    "and hospitalisation for heart failure in adults with HFrEF."
                ),
                keywords=["empagliflozin", "label", "hfref"],
            ),
        ],
    }
    report = await run_pulse_validation(
        query="Does empagliflozin reduce hospitalisation in HFrEF?",
        results_by_source=results,
        modes=["pharma"],
    )
    # Simulate orchestrator: many attempted DBs, few responding
    report._sources_attempted = 11
    report._sources_errored = 1
    bd = report._compute_confidence()
    assert bd["gate"]["passed"] is True
    assert bd["source_coverage"] == 1.0  # responding universe, not 3/11
    assert report.confidence_ratio >= 0.40
    assert "pharma" in (bd.get("lens") or "")
    assert bd.get("justification")
    payload = report.to_dict()
    assert payload["sources_failed"] == 1  # infra only
    assert payload["pulse_justification"]


@pytest.mark.asyncio
async def test_evidence_gate_fails_for_single_work():
    results = {
        "pubmed": [
            _paper(
                "pubmed",
                title="Single paper on aquatic cold-fusion tonic",
                summary="No indexed human trials show aquatic cold-fusion tonic reverses osteoarthritis.",
                keywords=["osteoarthritis"],
            )
        ]
    }
    report = await run_pulse_validation(
        query="Does cold-fusion tonic reverse osteoarthritis?",
        results_by_source=results,
        modes=["all"],
    )
    bd = report._compute_confidence()
    assert bd["gate"]["passed"] is False
    assert report.confidence_ratio == 0.0
    assert report.status == status_for_confidence(0.0)
    assert "Insufficient for PULSE" in bd["justification"][0]


@pytest.mark.asyncio
async def test_two_classes_two_works_passes_gate():
    results = {
        "pubmed": [
            _paper(
                "pubmed",
                title="Metformin glycaemic control trial summary",
                summary="Metformin reduced HbA1c in adults with type 2 diabetes versus placebo.",
                keywords=["metformin", "diabetes"],
            )
        ],
        "dailymed": [
            _paper(
                "dailymed",
                title="Metformin hydrochloride tablets label",
                summary="Label indication: metformin is used with diet and exercise for type 2 diabetes.",
                keywords=["metformin", "label"],
            )
        ],
    }
    report = await run_pulse_validation(
        query="What is metformin used for?",
        results_by_source=results,
        modes=["pharma"],
    )
    bd = report._compute_confidence()
    assert bd["gate"]["passed"] is True
    assert set(bd["source_classes"]) >= {"literature", "label"}
    assert report.confidence_ratio >= 0.40


def test_source_class_map():
    assert source_class_for("pubmed") == "literature"
    assert source_class_for("clinical_trials") == "trial_registry"
    assert source_class_for("dailymed") == "label"
    assert source_class_for("openfda") == "label"


def test_pharma_mode_is_valid_and_tags_labels():
    assert "pharma" in VALID_MODES
    r = SourceResult(
        source_name="dailymed",
        title="Amiodarone tablets",
        summary="US labelling warns of pulmonary toxicity and recommends monitoring.",
        url="https://example.com/label",
        doi=None,
        pmid=None,
        year=2022,
        keywords=["amiodarone"],
        authors=[],
    )
    _tag_result_modes(r)
    assert "pharma" in r.matched_modes
    assert "all" in r.matched_modes
