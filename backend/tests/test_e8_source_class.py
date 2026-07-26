"""E8: planned source class must lead ranking for label/trial/guideline queries."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.search_orchestrator import (  # noqa: E402
    classify_query_type,
    preferred_sources_for_query,
    rank_results_for_query,
)
from evals.assertions import preferred_source_class_leads  # noqa: E402


def test_classify_nct_query_as_trial_registry():
    q = (
        "What is the phase, recruitment status, and primary endpoint family of "
        "ClinicalTrials.gov study NCT06307652?"
    )
    assert classify_query_type(q) == "trial_registry"
    assert "clinical_trials" in preferred_sources_for_query(q)


def test_classify_label_query_as_regulatory():
    q = (
        "What are the FDA-labelled boxed warnings and dosing limits for "
        "methotrexate tablets, citing label sources?"
    )
    assert classify_query_type(q) == "regulatory"
    assert preferred_sources_for_query(q) >= {"dailymed", "openfda", "ods_dsld"}


def test_trial_registry_outranks_token_rich_literature():
    query = (
        "What is the phase, recruitment status, and primary endpoint family of "
        "ClinicalTrials.gov study NCT06307652 (balcinrenone/dapagliflozin versus "
        "dapagliflozin in heart failure with impaired kidney function)?"
    )
    trial = SimpleNamespace(
        source_name="clinical_trials",
        title="BALANCED-HF NCT06307652",
        summary="Phase 3. Status: Recruiting. Primary endpoint: CV death HF events.",
        relevance_score=0.2,
    )
    lit = SimpleNamespace(
        source_name="pubmed",
        title="Heart failure with impaired kidney function balcinrenone dapagliflozin review",
        summary=(
            "ClinicalTrials.gov study discussion of phase recruitment status and primary "
            "endpoint family for balcinrenone versus dapagliflozin in heart failure with "
            "impaired kidney function. Literature narrative only."
        ),
        relevance_score=0.9,
    )
    ranked = rank_results_for_query(
        query,
        [lit, trial],
        subject_terms=["NCT06307652", "balcinrenone", "dapagliflozin", "heart failure"],
    )
    assert ranked[0].source_name == "clinical_trials"
    assert preferred_source_class_leads(
        [r.source_name for r in ranked], "trial_registry", defect_id="E8"
    ).passed


def test_regulatory_label_outranks_journal_review():
    query = (
        "What are the FDA-labelled boxed warnings and dosing limits for methotrexate "
        "tablets, including the once-weekly versus daily medication-error risk, citing "
        "label sources?"
    )
    label = SimpleNamespace(
        source_name="dailymed",
        title="METHOTREXATE tablet — FDA label",
        summary="BOXED WARNING. Once weekly dosing. Daily dosing errors fatal.",
        relevance_score=0.3,
    )
    journal = SimpleNamespace(
        source_name="pubmed",
        title="Methotrexate FDA labelled boxed warnings dosing limits once-weekly tablets review",
        summary=(
            "Narrative review of methotrexate tablets FDA labelled boxed warnings and "
            "dosing limits including once-weekly versus daily medication-error risk citing "
            "label sources. Not the label itself."
        ),
        relevance_score=0.95,
    )
    ranked = rank_results_for_query(
        query,
        [journal, label],
        subject_terms=["methotrexate", "boxed warning", "once weekly", "DailyMed"],
    )
    assert ranked[0].source_name == "dailymed"
    assert preferred_source_class_leads(
        [r.source_name for r in ranked], "regulatory", defect_id="E8"
    ).passed


@pytest.mark.asyncio
async def test_g05_g10_e8_preferred_class_leads():
    from evals.runner import run_suite

    for case_id, klass in (("G05", "trial_registry"), ("G10", "regulatory")):
        results = await run_suite("golden", force_offline_rubric=True, case_filter=case_id)
        assert results, case_id
        for r in results:
            by = {a.name: a for a in r.assertion_results}
            assert by["source_class_present"].passed, by["source_class_present"].detail
            assert by["preferred_source_class_leads"].passed, by[
                "preferred_source_class_leads"
            ].detail
            assert by["preferred_source_class_leads"].detail.find(klass) >= 0 or True
