"""
Tests for Medical Advice Guardrails

Tests detection of advice requests and warm redirect responses.

Run with: pytest tests/test_guardrails.py -v
"""

import pytest
from app.core.guardrails import check_for_advice_request, get_warm_redirect


class TestAdviceDetection:
    """Test detection of medical advice requests."""

    def test_detect_should_i_take(self):
        """Should detect 'should i take' queries."""
        query = "should i take aspirin for headaches?"
        assert check_for_advice_request(query) is True

    def test_detect_should_i_stop(self):
        """Should detect 'should i stop taking' queries."""
        query = "should i stop taking my blood pressure medication?"
        assert check_for_advice_request(query) is True

    def test_detect_is_it_safe(self):
        """Should detect 'is it safe to' queries."""
        query = "is it safe to combine these supplements?"
        assert check_for_advice_request(query) is True

    def test_detect_can_i_take(self):
        """Should detect 'can i take' queries."""
        query = "can i take ibuprofen with my antidepressant?"
        assert check_for_advice_request(query) is True

    def test_detect_what_medication(self):
        """Should detect 'what medication' queries."""
        query = "what medication should I take for anxiety?"
        assert check_for_advice_request(query) is True

    def test_detect_what_should_i_do(self):
        """Should detect 'what should i do about' queries."""
        query = "what should i do about this persistent cough?"
        assert check_for_advice_request(query) is True

    def test_detect_do_i_have(self):
        """Should detect 'do i have' queries."""
        query = "do i have diabetes?"
        assert check_for_advice_request(query) is True

    def test_detect_am_i_at_risk(self):
        """Should detect 'am i at risk' queries."""
        query = "am i at risk for heart disease?"
        assert check_for_advice_request(query) is True

    def test_detect_should_i_be_worried(self):
        """Should detect 'should i be worried' queries."""
        query = "should i be worried about this mole?"
        assert check_for_advice_request(query) is True

    def test_detect_is_this_normal(self):
        """Should detect 'is this normal' queries."""
        query = "is this normal for someone my age?"
        assert check_for_advice_request(query) is True

    def test_detect_what_treatment(self):
        """Should detect 'what treatment' queries."""
        query = "what treatment options exist for my condition?"
        assert check_for_advice_request(query) is True

    def test_detect_should_i_see_doctor(self):
        """Should detect 'should i see a doctor' queries."""
        query = "should i see a doctor for this?"
        assert check_for_advice_request(query) is True

    def test_detect_how_do_i_treat(self):
        """Should detect 'how do i treat' queries."""
        query = "how do i treat a sprained ankle?"
        assert check_for_advice_request(query) is True

    def test_detect_can_you_diagnose(self):
        """Should detect 'can you diagnose' queries."""
        query = "can you diagnose what's causing my symptoms?"
        assert check_for_advice_request(query) is True

    def test_detect_whats_wrong_with_me(self):
        """Should detect 'what's wrong with me' queries."""
        query = "what's wrong with me?"
        assert check_for_advice_request(query) is True

    def test_detect_should_i_go_to_er(self):
        """Should detect 'should i go to the er' queries."""
        query = "should i go to the er for chest pain?"
        assert check_for_advice_request(query) is True

    def test_detect_is_this_serious(self):
        """Should detect 'is this serious' queries."""
        query = "is this serious?"
        assert check_for_advice_request(query) is True

    def test_detect_will_this_go_away(self):
        """Should detect 'will this go away' queries."""
        query = "will this go away by itself?"
        assert check_for_advice_request(query) is True

    def test_detect_what_dose_should(self):
        """Should detect 'what dose should' queries."""
        query = "what dose should i take?"
        assert check_for_advice_request(query) is True

    def test_case_insensitive(self):
        """Advice detection should be case-insensitive."""
        query = "SHOULD I TAKE ASPIRIN?"
        assert check_for_advice_request(query) is True

    def test_case_insensitive_mixed(self):
        """Advice detection with mixed case."""
        query = "Should I Take This Medication?"
        assert check_for_advice_request(query) is True

    # ===== Non-Advice Queries =====

    def test_non_advice_systematic_review(self):
        """Systematic review query should NOT be flagged."""
        query = "systematic review of aspirin for heart disease"
        assert check_for_advice_request(query) is False

    def test_non_advice_meta_analysis(self):
        """Meta-analysis query should NOT be flagged."""
        query = "meta-analysis on blood pressure medications"
        assert check_for_advice_request(query) is False

    def test_non_advice_research(self):
        """Research query should NOT be flagged."""
        query = "what does the literature say about treatment?"
        assert check_for_advice_request(query) is False

    def test_non_advice_mechanism(self):
        """Mechanism question should NOT be flagged."""
        query = "how does aspirin work?"
        assert check_for_advice_request(query) is False

    def test_non_advice_side_effects(self):
        """Side effects inquiry should NOT be flagged."""
        query = "what are the side effects of metformin?"
        assert check_for_advice_request(query) is False

    def test_non_advice_information(self):
        """General information request should NOT be flagged."""
        query = "tell me about heart failure"
        assert check_for_advice_request(query) is False

    def test_non_advice_epidemiology(self):
        """Epidemiology query should NOT be flagged."""
        query = "prevalence of diabetes in the US"
        assert check_for_advice_request(query) is False


class TestWarmRedirect:
    """Test warm redirect response generation."""

    def test_get_warm_redirect_non_empty(self):
        """Warm redirect should not be empty."""
        redirect = get_warm_redirect("any query")
        assert redirect
        assert len(redirect) > 0

    def test_get_warm_redirect_empathetic(self):
        """Warm redirect should be empathetic."""
        redirect = get_warm_redirect("any query")
        # Should acknowledge the user's concern
        assert "see" in redirect.lower() or "care team" in redirect.lower()

    def test_get_warm_redirect_redirects_to_care_team(self):
        """Warm redirect should mention healthcare team."""
        redirect = get_warm_redirect("any query")
        # Should redirect to care team
        assert "doctor" in redirect.lower() or "care team" in redirect.lower()

    def test_get_warm_redirect_offers_research(self):
        """Warm redirect should offer to provide research."""
        redirect = get_warm_redirect("any query")
        # Should offer research instead
        assert "research" in redirect.lower() or "evidence" in redirect.lower()

    def test_get_warm_redirect_consistent(self):
        """Warm redirect should be consistent regardless of query."""
        redirect1 = get_warm_redirect("should i take aspirin?")
        redirect2 = get_warm_redirect("what medication should i take?")
        # The template should be the same
        assert redirect1 == redirect2
