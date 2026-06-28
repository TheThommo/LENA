"""Tests for URL / document content ingestion."""

import pytest

from app.services.content_ingest import (
    extract_urls,
    format_attached_context,
    strip_urls,
    IngestedContent,
)


def test_extract_urls_from_query():
    q = (
        "Effects of headache powders https://medsinfo.sahpra.org.za/medicine/abc "
        "and also http://example.com/page."
    )
    urls = extract_urls(q)
    assert len(urls) == 2
    assert urls[0].startswith("https://medsinfo")


def test_strip_urls_keeps_question():
    q = "What are the effects? https://example.com/doc"
    assert strip_urls(q) == "What are the effects?"


def test_format_attached_context():
    blocks = [
        IngestedContent("url", "https://x.com", "Headache Powder", "Ingredients: aspirin"),
    ]
    text = format_attached_context(blocks)
    assert "Attached documents" in text
    assert "aspirin" in text
