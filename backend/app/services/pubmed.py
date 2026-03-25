"""
PubMed / NCBI E-Utilities Service

Endpoints used:
- esearch: Search PubMed and get PMIDs
- efetch: Fetch article details by PMID
- (Future) elink: Find related articles

Docs: https://www.ncbi.nlm.nih.gov/books/NBK25501/

Rate limits:
- Without API key: 3 requests/second
- With API key: 10 requests/second
"""

import httpx
from lxml import etree
from typing import Optional
from dataclasses import dataclass

from app.core.config import settings

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@dataclass
class PubMedArticle:
    pmid: str
    title: str
    abstract: str
    authors: list[str]
    journal: str
    year: Optional[int]
    doi: Optional[str]
    url: str


def _build_params(**kwargs) -> dict:
    """Add API key and email to params if available."""
    params = {k: v for k, v in kwargs.items() if v is not None}
    if settings.ncbi_api_key:
        params["api_key"] = settings.ncbi_api_key
    if settings.ncbi_email:
        params["email"] = settings.ncbi_email
    return params


async def search_pubmed(
    query: str,
    max_results: int = 10,
    sort: str = "relevance",
) -> list[str]:
    """
    Search PubMed and return a list of PMIDs.

    Args:
        query: Search term (supports PubMed search syntax)
        max_results: Number of results to return (max 100)
        sort: Sort order - "relevance" or "date"

    Returns:
        List of PMID strings
    """
    params = _build_params(
        db="pubmed",
        term=query,
        retmax=min(max_results, 100),
        sort=sort,
        retmode="json",
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{BASE_URL}/esearch.fcgi", params=params)
        response.raise_for_status()
        data = response.json()

    return data.get("esearchresult", {}).get("idlist", [])


async def fetch_articles(pmids: list[str]) -> list[PubMedArticle]:
    """
    Fetch full article details for a list of PMIDs.

    Args:
        pmids: List of PubMed IDs

    Returns:
        List of PubMedArticle objects
    """
    if not pmids:
        return []

    params = _build_params(
        db="pubmed",
        id=",".join(pmids),
        retmode="xml",
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{BASE_URL}/efetch.fcgi", params=params)
        response.raise_for_status()

    root = etree.fromstring(response.content)
    articles = []

    for article_elem in root.findall(".//PubmedArticle"):
        medline = article_elem.find(".//MedlineCitation")
        if medline is None:
            continue

        pmid = medline.findtext("PMID", default="")
        article = medline.find("Article")
        if article is None:
            continue

        title = article.findtext("ArticleTitle", default="No title")

        # Abstract can have multiple sections
        abstract_parts = []
        abstract_elem = article.find("Abstract")
        if abstract_elem is not None:
            for text in abstract_elem.findall("AbstractText"):
                label = text.get("Label", "")
                content = text.text or ""
                if label:
                    abstract_parts.append(f"{label}: {content}")
                else:
                    abstract_parts.append(content)
        abstract = " ".join(abstract_parts) if abstract_parts else "No abstract available"

        # Authors
        authors = []
        author_list = article.find("AuthorList")
        if author_list is not None:
            for author in author_list.findall("Author"):
                last = author.findtext("LastName", "")
                first = author.findtext("ForeName", "")
                if last:
                    authors.append(f"{last} {first}".strip())

        # Journal
        journal = article.findtext(".//Journal/Title", default="Unknown")

        # Year
        year = None
        pub_date = article.find(".//PubDate")
        if pub_date is not None:
            year_text = pub_date.findtext("Year")
            if year_text and year_text.isdigit():
                year = int(year_text)

        # DOI
        doi = None
        for id_elem in article_elem.findall(".//ArticleId"):
            if id_elem.get("IdType") == "doi":
                doi = id_elem.text
                break

        articles.append(PubMedArticle(
            pmid=pmid,
            title=title,
            abstract=abstract,
            authors=authors,
            journal=journal,
            year=year,
            doi=doi,
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        ))

    return articles


async def test_connection() -> dict:
    """Test the PubMed API connection with a simple search."""
    try:
        pmids = await search_pubmed("COVID-19 treatment", max_results=3)
        if pmids:
            articles = await fetch_articles(pmids[:1])
            return {
                "source": "PubMed/NCBI",
                "status": "connected",
                "test_query": "COVID-19 treatment",
                "results_found": len(pmids),
                "sample_title": articles[0].title if articles else "N/A",
                "api_key_configured": bool(settings.ncbi_api_key),
            }
        return {
            "source": "PubMed/NCBI",
            "status": "connected_no_results",
            "message": "API reachable but no results for test query",
        }
    except Exception as e:
        return {
            "source": "PubMed/NCBI",
            "status": "error",
            "error": str(e),
        }
