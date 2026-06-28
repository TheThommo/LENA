"""Tests for product-context search relevance filtering."""

import pytest

from app.core.pulse_engine import SourceResult
from app.services.content_ingest import IngestedContent, extract_search_terms_from_context
from app.services.search_orchestrator import (
    _filter_relevant,
    _post_filter_by_query_fit,
    _prioritize_display_keywords,
    _query_fit_score,
)
from app.core.pulse_engine import PULSEReport, run_pulse_validation


def test_extract_ingredients_from_sahpra_style_text():
    blocks = [
        IngestedContent(
            "url",
            "https://medsinfo.sahpra.org.za/medicine/x",
            "Headache Powder",
            "Active ingredient: Paracetamol 300 mg, Aspirin 300 mg, Caffeine 30 mg per sachet.",
        ),
    ]
    primary, secondary = extract_search_terms_from_context(blocks)
    assert "paracetamol" in primary
    assert "aspirin" in primary
    assert "caffeine" in primary


def test_filter_relevant_requires_primary_when_product_attached():
    results = {
        "pubmed": [
            SourceResult(
                source_name="pubmed",
                title="Pharmacological therapies for management of opium withdrawal",
                summary="Headache is a common withdrawal symptom among patients.",
            ),
            SourceResult(
                source_name="pubmed",
                title="Aspirin and paracetamol combination safety review",
                summary="Long-term use of aspirin-paracetamol combinations requires monitoring.",
            ),
        ],
    }
    filtered = _filter_relevant(
        results,
        subject_terms=["headache", "powders", "client"],
        primary_terms=["aspirin", "paracetamol", "caffeine"],
    )
    titles = [r.title for r in filtered["pubmed"]]
    assert any("Aspirin" in t for t in titles)
    assert not any("opium" in t.lower() for t in titles)


def test_filter_relevant_allows_generic_or_when_no_product_context():
    results = {
        "pubmed": [
            SourceResult(
                source_name="pubmed",
                title="Headache treatment guidelines",
                summary="Evidence for acute headache management.",
            ),
        ],
    }
    filtered = _filter_relevant(results, subject_terms=["headache"])
    assert len(filtered["pubmed"]) == 1


def test_post_filter_drops_zero_overlap_with_primary_context():
    report = PULSEReport(query="headache powders")
    report.validated_results = [
        SourceResult(
            source_name="openalex",
            title="Antibiotic use in urban South Africa",
            summary="Health providers discussed antibiotic prescribing.",
            relevance_score=0.3,
        ),
        SourceResult(
            source_name="pubmed",
            title="Caffeine and analgesic combinations",
            summary="Paracetamol and caffeine improve headache relief.",
            relevance_score=0.4,
        ),
    ]
    _post_filter_by_query_fit(
        report,
        subject_terms=["headache"],
        primary_terms=["paracetamol", "caffeine"],
    )
    assert len(report.validated_results) == 1
    assert "Caffeine" in report.validated_results[0].title


def test_prioritize_display_keywords():
    r = SourceResult(
        source_name="pubmed",
        title="Test",
        summary="Test",
        keywords=["withdrawal", "aspirin", "patients", "opium", "paracetamol"],
    )
    _prioritize_display_keywords(r, ["aspirin", "paracetamol", "caffeine"])
    assert r.keywords[0] in ("aspirin", "paracetamol")


@pytest.mark.asyncio
async def test_pulse_query_fit_boosts_on_topic_paper():
    results = {
        "pubmed": [
            SourceResult(
                source_name="pubmed",
                title="Aspirin safety in chronic headache powder use",
                summary="Paracetamol and aspirin combinations were studied for adverse events.",
            ),
            SourceResult(
                source_name="pubmed",
                title="Prehistoric cranial operations",
                summary="Trepanation cases in ancient societies.",
            ),
        ],
    }
    report = await run_pulse_validation(
        query="headache powders",
        results_by_source=results,
        subject_terms=["aspirin", "paracetamol", "caffeine"],
    )
    if len(report.validated_results) >= 2:
        assert report.validated_results[0].relevance_score >= report.validated_results[1].relevance_score


def test_query_fit_score():
    blob = "aspirin and paracetamol combination therapy"
    score = _query_fit_score(blob, ["aspirin", "paracetamol", "caffeine"])
    assert score >= 0.66
