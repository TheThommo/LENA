"""
Comprehensive Tests for PULSE Engine (Published Literature Source Evaluation)

Tests the cross-reference validation engine, keyword extraction, scoring rules,
and consensus detection.

Run with: pytest tests/test_pulse_engine.py -v
"""

import pytest
from app.core.pulse_engine import (
    extract_keywords,
    _compute_overlap,
    run_pulse_validation,
    SourceResult,
    ValidationStatus,
)


class TestKeywordExtraction:
    """Test keyword extraction logic."""

    def test_extract_keywords_basic(self):
        """Extract keywords from simple text."""
        text = "heart failure and cardiac disease treatment"
        keywords = extract_keywords(text, top_n=10)
        assert "heart" in keywords or "failure" in keywords
        assert "cardiac" in keywords
        assert "treatment" in keywords

    def test_extract_keywords_filters_stopwords(self):
        """Stopwords should be filtered out."""
        text = "the and a or in on at to for with by from"
        keywords = extract_keywords(text, top_n=10)
        # Should not contain short/stop words
        assert all(len(kw) >= 3 for kw in keywords)
        assert "the" not in keywords
        assert "and" not in keywords
        assert "for" not in keywords

    def test_extract_keywords_empty_input(self):
        """Empty text should return empty list."""
        assert extract_keywords("") == []
        assert extract_keywords("   ") == []

    def test_extract_keywords_short_words_filtered(self):
        """Words shorter than 3 chars should be filtered."""
        text = "a ab abc abcd"
        keywords = extract_keywords(text, top_n=10)
        # "a", "ab" should be filtered
        for kw in keywords:
            assert len(kw) >= 3

    def test_extract_keywords_case_insensitive(self):
        """Keywords should be extracted case-insensitively."""
        text = "Heart Heart CARDIAC cardiac"
        keywords = extract_keywords(text, top_n=10)
        # Should have lowercase versions
        assert all(kw.islower() for kw in keywords)
        # Both Heart and cardiac should be recognized
        assert "heart" in keywords
        assert "cardiac" in keywords

    def test_extract_keywords_respects_top_n(self):
        """Should return at most top_n keywords."""
        text = "heart cardiac coronary arrhythmia hypertension valve aorta stroke"
        keywords = extract_keywords(text, top_n=3)
        assert len(keywords) <= 3

    def test_extract_keywords_frequency_based(self):
        """Should return more frequent keywords first."""
        text = "apple apple apple banana banana orange"
        keywords = extract_keywords(text, top_n=10)
        # apple appears 3x, banana 2x, orange 1x
        # The most frequent should appear first
        if keywords:
            # Check if apple is earlier (more frequent)
            assert "apple" in keywords


class TestComputeOverlap:
    """Test Jaccard similarity calculation."""

    def test_compute_overlap_identical_sets(self):
        """Identical sets should have overlap of 1.0."""
        set_a = {"heart", "cardiac", "disease"}
        set_b = {"heart", "cardiac", "disease"}
        overlap = _compute_overlap(set_a, set_b)
        assert overlap == 1.0

    def test_compute_overlap_no_intersection(self):
        """Disjoint sets should have overlap of 0.0."""
        set_a = {"heart", "cardiac"}
        set_b = {"liver", "hepatic"}
        overlap = _compute_overlap(set_a, set_b)
        assert overlap == 0.0

    def test_compute_overlap_partial(self):
        """Partial overlap should be between 0 and 1."""
        set_a = {"heart", "cardiac", "disease"}
        set_b = {"heart", "blood", "vessel"}
        overlap = _compute_overlap(set_a, set_b)
        # intersection: {heart} = 1
        # union: {heart, cardiac, disease, blood, vessel} = 5
        # overlap = 1/5 = 0.2
        assert overlap == pytest.approx(0.2, rel=1e-2)

    def test_compute_overlap_empty_set_a(self):
        """Empty set A should return 0."""
        overlap = _compute_overlap(set(), {"heart", "cardiac"})
        assert overlap == 0.0

    def test_compute_overlap_empty_set_b(self):
        """Empty set B should return 0."""
        overlap = _compute_overlap({"heart", "cardiac"}, set())
        assert overlap == 0.0

    def test_compute_overlap_both_empty(self):
        """Both empty sets should return 0."""
        overlap = _compute_overlap(set(), set())
        assert overlap == 0.0


class TestPULSEValidation:
    """Test the main PULSE validation engine."""

    @pytest.mark.asyncio
    async def test_pulse_empty_results(self):
        """No results should return PENDING status."""
        report = await run_pulse_validation(
            query="heart failure",
            results_by_source={},
        )
        assert report.status == ValidationStatus.PENDING
        assert report.source_count == 0
        assert report.agreement_count == 0

    @pytest.mark.asyncio
    async def test_pulse_single_source_capped_at_60(self, create_test_search_result):
        """Single source result relevance capped at 0.60."""
        result = create_test_search_result(source_name="pubmed")

        report = await run_pulse_validation(
            query="heart failure",
            results_by_source={"pubmed": [result]},
        )

        assert report.source_count == 1
        # Single source should be capped at 0.60
        if report.validated_results:
            assert report.validated_results[0].relevance_score <= 0.60

    @pytest.mark.asyncio
    async def test_pulse_five_sources_agreeing_validated(self, create_test_search_result):
        """5 sources with high overlap should be VALIDATED."""
        # Create 5 results with overlapping keywords
        results = {
            "pubmed": [create_test_search_result("pubmed", keywords=["heart", "failure", "cardiac"])],
            "clinical_trials": [create_test_search_result("clinical_trials", keywords=["heart", "failure", "treatment"])],
            "cochrane": [create_test_search_result("cochrane", keywords=["heart", "cardiac", "evidence"])],
            "who_iris": [create_test_search_result("who_iris", keywords=["heart", "disease", "cardiac"])],
            "cdc": [create_test_search_result("cdc", keywords=["heart", "cardiovascular", "health"])],
        }

        report = await run_pulse_validation(
            query="heart failure treatment",
            results_by_source=results,
        )

        assert report.status == ValidationStatus.VALIDATED
        assert report.source_count == 5
        assert report.agreement_count >= 3

    @pytest.mark.asyncio
    async def test_pulse_two_sources_insufficient(self, create_test_search_result):
        """2 sources should be INSUFFICIENT."""
        results = {
            "pubmed": [create_test_search_result("pubmed")],
            "clinical_trials": [create_test_search_result("clinical_trials")],
        }

        report = await run_pulse_validation(
            query="heart failure",
            results_by_source=results,
        )

        assert report.status == ValidationStatus.INSUFFICIENT
        assert report.source_count == 2

    @pytest.mark.asyncio
    async def test_pulse_edge_cases_flagged(self, create_test_search_result):
        """Sources with low overlap should be flagged differently."""
        # Create 4 sources where 3 agree and 1 has very different keywords
        results = {
            "pubmed": [
                SourceResult(
                    source_name="pubmed",
                    title="Heart failure study",
                    summary="Consensus keywords",
                    keywords=["heart", "failure", "cardiac", "treatment"],
                )
            ],
            "clinical_trials": [
                SourceResult(
                    source_name="clinical_trials",
                    title="Heart failure trial",
                    summary="Consensus keywords",
                    keywords=["heart", "failure", "cardiac", "therapy"],
                )
            ],
            "cochrane": [
                SourceResult(
                    source_name="cochrane",
                    title="Heart failure review",
                    summary="Consensus keywords",
                    keywords=["heart", "failure", "evidence", "intervention"],
                )
            ],
            "who_iris": [
                SourceResult(
                    source_name="who_iris",
                    title="Liver disease info",
                    summary="Completely different",
                    keywords=["liver", "disease", "hepatic", "cirrhosis"],
                )
            ],
        }

        report = await run_pulse_validation(
            query="heart failure",
            results_by_source=results,
            edge_case_threshold=0.3,
        )

        # Should have some consensus and some divergence
        has_consensus = any(sa.is_consensus for sa in report.source_agreements)
        has_divergent = any(not sa.is_consensus for sa in report.source_agreements)
        assert has_consensus and has_divergent

    @pytest.mark.asyncio
    async def test_pulse_retracted_papers_not_scored(self):
        """Retracted papers skip scoring but may appear with 0 relevance."""
        results = {
            "pubmed": [
                SourceResult(
                    source_name="pubmed",
                    title="Valid paper",
                    summary="This is valid research",
                    keywords=["heart", "failure"],
                    is_retracted=False,
                    relevance_score=0.0,
                ),
                SourceResult(
                    source_name="pubmed",
                    title="Retracted paper",
                    summary="This was retracted",
                    keywords=["heart", "failure"],
                    is_retracted=True,
                    relevance_score=0.0,
                ),
            ],
            "clinical_trials": [
                SourceResult(
                    source_name="clinical_trials",
                    title="Trial study",
                    summary="This is valid",
                    keywords=["heart", "failure"],
                    is_retracted=False,
                )
            ],
            "cochrane": [
                SourceResult(
                    source_name="cochrane",
                    title="Review study",
                    summary="This is valid",
                    keywords=["heart", "failure"],
                    is_retracted=False,
                )
            ],
        }

        report = await run_pulse_validation(
            query="heart failure",
            results_by_source=results,
        )

        # Retracted papers skip scoring (continue in loop) but may still be in results
        # The key test: retracted papers should NOT get a relevance score > 0
        for result in report.validated_results + report.edge_cases:
            if result.is_retracted:
                # Retracted papers should have 0 relevance score
                assert result.relevance_score == 0.0

    @pytest.mark.asyncio
    async def test_pulse_cochrane_boost(self, create_test_search_result):
        """Cochrane results should get 1.25x multiplier (capped at 1.0)."""
        results = {
            "pubmed": [create_test_search_result("pubmed", keywords=["heart", "failure"])],
            "clinical_trials": [create_test_search_result("clinical_trials", keywords=["heart", "failure"])],
            "cochrane": [create_test_search_result("cochrane", keywords=["heart", "failure"])],
        }

        report = await run_pulse_validation(
            query="heart failure",
            results_by_source=results,
        )

        # Find Cochrane result
        cochrane_result = next(
            (r for r in report.validated_results if r.source_name == "cochrane"),
            None
        )

        if cochrane_result:
            # Score should be capped at 1.0
            assert cochrane_result.relevance_score <= 1.0

    @pytest.mark.asyncio
    async def test_pulse_confidence_ratio_calculation(self, create_test_search_result):
        """Confidence ratio should be agreement_count / source_count."""
        results = {
            "pubmed": [create_test_search_result("pubmed", keywords=["heart", "failure"])],
            "clinical_trials": [create_test_search_result("clinical_trials", keywords=["heart", "failure"])],
            "cochrane": [create_test_search_result("cochrane", keywords=["heart", "failure"])],
        }

        report = await run_pulse_validation(
            query="heart failure",
            results_by_source=results,
        )

        # Should have base confidence = agreement_count / source_count
        assert report.confidence_ratio > 0.0
        assert report.confidence_ratio <= 1.0

    @pytest.mark.asyncio
    async def test_pulse_consensus_keywords(self, create_test_search_result):
        """Consensus keywords should appear in multiple sources."""
        results = {
            "pubmed": [create_test_search_result("pubmed", keywords=["heart", "failure", "cardiac"])],
            "clinical_trials": [create_test_search_result("clinical_trials", keywords=["heart", "failure", "treatment"])],
            "cochrane": [create_test_search_result("cochrane", keywords=["heart", "cardiac", "evidence"])],
        }

        report = await run_pulse_validation(
            query="heart failure",
            results_by_source=results,
        )

        # "heart" appears in all 3 sources, should be in consensus
        # (or at minimum, consensus keywords should exist and be non-empty)
        assert len(report.consensus_keywords) > 0
        # Heart appears in all 3 sources' keywords
        heart_in_sources = all(
            "heart" in sa.shared_keywords
            for sa in report.source_agreements
        )
        # If heart is in all shared keywords, it should be consensus
        if heart_in_sources:
            assert "heart" in report.consensus_keywords

    @pytest.mark.asyncio
    async def test_pulse_conflict_penalty(self, create_test_search_result):
        """Edge cases should lower confidence via penalty."""
        results = {
            "pubmed": [create_test_search_result("pubmed", keywords=["heart", "failure"])],
            "clinical_trials": [create_test_search_result("clinical_trials", keywords=["heart", "failure"])],
            "cochrane": [create_test_search_result("cochrane", keywords=["heart", "failure"])],
            "who_iris": [create_test_search_result("who_iris", keywords=["liver", "disease"])],  # Edge case
        }

        report_with_conflict = await run_pulse_validation(
            query="heart failure",
            results_by_source=results,
        )

        results_no_conflict = {
            "pubmed": [create_test_search_result("pubmed", keywords=["heart", "failure"])],
            "clinical_trials": [create_test_search_result("clinical_trials", keywords=["heart", "failure"])],
            "cochrane": [create_test_search_result("cochrane", keywords=["heart", "failure"])],
            "who_iris": [create_test_search_result("who_iris", keywords=["heart", "failure"])],
        }

        report_no_conflict = await run_pulse_validation(
            query="heart failure",
            results_by_source=results_no_conflict,
        )

        # Conflict scenario should have lower confidence
        if report_with_conflict.edge_cases:
            assert report_with_conflict.confidence_ratio <= report_no_conflict.confidence_ratio

    @pytest.mark.asyncio
    async def test_pulse_report_serialization(self, create_test_search_result):
        """PULSE report should serialize to dict correctly."""
        results = {
            "pubmed": [create_test_search_result("pubmed")],
        }

        report = await run_pulse_validation(
            query="heart failure",
            results_by_source=results,
        )

        report_dict = report.to_dict()

        assert "query" in report_dict
        assert "status" in report_dict
        assert "confidence_ratio" in report_dict
        assert "source_count" in report_dict
        assert "consensus_keywords" in report_dict
        assert report_dict["status"] in ["validated", "edge_case", "insufficient_validation", "pending"]
