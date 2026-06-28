"""Unit tests for P1/P2 source integrations (Semantic Scholar, Europe PMC, DailyMed, Crossref)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.semantic_scholar import search_semantic_scholar
from app.services.europe_pmc import search_europe_pmc
from app.services.dailymed import search_dailymed
from app.services.crossref import resolve_doi_metadata


@pytest.mark.asyncio
async def test_semantic_scholar_parses_results():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {
                "paperId": "abc123",
                "title": "Vitamin D and immunity",
                "abstract": "A study on vitamin D.",
                "authors": [{"name": "Smith J"}],
                "year": 2023,
                "externalIds": {"DOI": "10.1234/test"},
                "citationCount": 42,
                "url": "https://www.semanticscholar.org/paper/abc123",
            }
        ]
    }
    with patch("app.services.semantic_scholar.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        papers = await search_semantic_scholar("vitamin d", max_results=5)
    assert len(papers) == 1
    assert papers[0].title == "Vitamin D and immunity"
    assert papers[0].doi == "10.1234/test"
    assert papers[0].citation_count == 42


@pytest.mark.asyncio
async def test_semantic_scholar_handles_failure():
    with patch("app.services.semantic_scholar.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=Exception("timeout"))
        papers = await search_semantic_scholar("test", max_results=5)
    assert papers == []


@pytest.mark.asyncio
async def test_europe_pmc_parses_results():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "resultList": {
            "result": [
                {
                    "pmid": "12345",
                    "title": "Europe PMC article",
                    "abstractText": "Abstract text here.",
                    "authorString": "Jones A, Lee B",
                    "pubYear": "2022",
                    "doi": "10.5678/epmc",
                    "source": "MED",
                }
            ]
        }
    }
    with patch("app.services.europe_pmc.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        articles = await search_europe_pmc("covid vaccine", max_results=5)
    assert len(articles) == 1
    assert articles[0].title == "Europe PMC article"
    assert "12345" in articles[0].url


@pytest.mark.asyncio
async def test_dailymed_parses_results():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {
                "setid": "uuid-123",
                "title": "Ibuprofen 200mg tablet",
                "labeler": "Example Pharma",
            }
        ]
    }
    with patch("app.services.dailymed.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        labels = await search_dailymed("ibuprofen", max_results=5)
    assert len(labels) == 1
    assert labels[0].set_id == "uuid-123"
    assert "Example Pharma" in labels[0].summary


@pytest.mark.asyncio
async def test_crossref_resolves_doi():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "message": {
            "title": ["Resolved Title"],
            "published-print": {"date-parts": [[2021]]},
        }
    }
    with patch("app.services.crossref.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        meta = await resolve_doi_metadata("10.1234/example")
    assert meta is not None
    assert meta["title"] == "Resolved Title"
    assert meta["year"] == 2021


@pytest.mark.asyncio
async def test_crossref_returns_none_on_404():
    mock_response = MagicMock()
    mock_response.status_code = 404
    with patch("app.services.crossref.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        meta = await resolve_doi_metadata("10.9999/missing")
    assert meta is None
