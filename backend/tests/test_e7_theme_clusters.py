"""E7: themes must be contiguous phrase clusters, not alphabetised token bags."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.pulse_engine import (  # noqa: E402
    SourceResult,
    build_theme_clusters,
    run_pulse_validation,
)
from evals.assertions import themes_are_clusters  # noqa: E402


def test_build_theme_clusters_prefers_contiguous_phrases():
    texts = [
        "Exercise-based cardiac rehabilitation after myocardial infarction "
        "is associated with reduced cardiovascular mortality and hospital readmission.",
        "Programmes include exercise training, risk-factor modification, education "
        "and psychosocial support. Home-based and hybrid models show comparable outcomes.",
        "Completion of cardiac rehabilitation after MI remains below eligibility.",
    ]
    themes = build_theme_clusters(texts, max_themes=8)
    assert themes, "expected phrase clusters from rehab prose"
    joined = " ".join(themes)
    assert "cardiac rehabilitation" in joined or "myocardial infarction" in joined
    # Must not be alphabetised 3+ token bags (bigrams may be alpha by chance)
    for t in themes:
        words = t.split()
        if len(words) >= 3:
            assert words != sorted(words), t


def test_build_theme_clusters_omits_alphabetised_bags():
    # Pure sorted token dumps (legacy topic joins) should not become themes
    assert build_theme_clusters(["ace adults agents arbs"], max_themes=8) == []
    assert build_theme_clusters(
        ["associated cardiac cardiovascular exercise"], max_themes=8
    ) == []


def test_themes_are_clusters_rejects_alpha_joins():
    result = themes_are_clusters(
        [
            "ace adults agents arbs",
            "associated cardiac cardiovascular exercise",
            "all analyses cause consistent",
        ],
        defect_id="E7",
    )
    assert not result.passed
    assert "alphabetised" in result.detail.lower() or "token" in result.detail.lower()


def test_themes_are_clusters_accepts_real_phrases_or_omit():
    assert themes_are_clusters([], defect_id="E7").passed
    ok = themes_are_clusters(
        ["cardiac rehabilitation", "myocardial infarction", "cardiovascular mortality"],
        defect_id="E7",
    )
    assert ok.passed


@pytest.mark.asyncio
async def test_pulse_g15_style_themes_are_phrase_clusters():
    results = {
        "cochrane": [
            SourceResult(
                source_name="cochrane",
                title="Exercise-based cardiac rehabilitation for coronary heart disease",
                summary=(
                    "Exercise-based cardiac rehabilitation after myocardial infarction is "
                    "associated with reduced cardiovascular mortality and hospital readmission. "
                    "Programmes include exercise training, risk-factor modification, education "
                    "and psychosocial support. Home-based and hybrid models show broadly "
                    "comparable outcomes in lower-risk patients."
                ),
                year=2021,
            )
        ],
        "pubmed": [
            SourceResult(
                source_name="pubmed",
                title="Access and equity in cardiac rehabilitation",
                summary=(
                    "Completion of cardiac rehabilitation after MI remains below eligibility, "
                    "with documented disparities by sex, age, socioeconomic status and geography."
                ),
                year=2022,
            )
        ],
    }
    report = await run_pulse_validation(
        "What themes should a teaching summary cover on cardiac rehabilitation "
        "after myocardial infarction?",
        results,
    )
    floor = themes_are_clusters(report.consensus_keywords, defect_id="E7")
    assert floor.passed, floor.detail
    if report.consensus_keywords:
        blob = " ".join(report.consensus_keywords)
        assert "cardiac" in blob and "rehab" in blob
