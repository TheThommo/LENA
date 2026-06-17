"""
Tests for supplement name/brand extraction guard (POC A2).

Run with: pytest tests/test_supplement_extraction.py -v
"""

import pytest

from app.services.search_orchestrator import (
    _extract_supplement_identity,
    _subject_terms,
)


class TestExtractSupplementIdentity:
    """Guard against word-salad supplement cards."""

    def test_garbage_query_returns_none(self):
        query = "supplements magnesium by they floaters"
        subjects = _subject_terms(query)
        name, brand = _extract_supplement_identity(query, subjects)
        assert name is None
        assert brand is None

    def test_nature_made_vitamin_d(self):
        query = "Nature Made Vitamin D 5000IU"
        subjects = _subject_terms(query)
        name, brand = _extract_supplement_identity(query, subjects)
        assert name is not None
        assert "vitamin" in name.lower()
        assert brand is not None
        assert "Nature" in brand
        assert "Made" in brand

    def test_nutricost_magnesium_credible(self):
        query = "is Nutricost magnesium glycinate credible"
        subjects = _subject_terms(query)
        name, brand = _extract_supplement_identity(query, subjects)
        assert name is not None
        assert "magnesium" in name.lower()
        assert brand is not None
        assert brand.split()[0].lower() == "nutricost"

    def test_magnesium_only_no_garbage_brand(self):
        query = "magnesium for sleep"
        subjects = _subject_terms(query)
        name, brand = _extract_supplement_identity(query, subjects)
        assert name == "magnesium"
        assert brand is None

    def test_empty_subjects(self):
        name, brand = _extract_supplement_identity("hello", [])
        assert name is None
        assert brand is None

    def test_filler_brand_tokens_suppress_card(self):
        query = "best magnesium supplement what should they take"
        subjects = _subject_terms(query)
        name, brand = _extract_supplement_identity(query, subjects)
        assert name is None
        assert brand is None
