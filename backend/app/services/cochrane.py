"""
Cochrane Library Open Access Service

Cochrane systematic reviews are the gold standard for evidence-based medicine.
We access them via PubMed Central (PMC) open access subset, which includes
Cochrane reviews that are freely available.

Strategy:
1. Search PubMed specifically for Cochrane Database of Systematic Reviews
2. Fetch abstracts and metadata via E-Utilities
3. Link to full text on Cochrane Library where available

This avoids needing a paid Wiley API key while still getting Cochrane content.
"""

import httpx
from typing import Optional
from dataclasses import dataclass

from app.core.config import settings

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
COCHRANE_JOURNAL = "Cochrane Database Syst Rev"


@dataclass
class CochraneReview:
    pmid: str
    title: str
    abstract: str
    authors: list[str]
    year: Optional[int]
    doi: Optional[str]
    cochrane_url: Optional[str]
    pubmed_url: str
    review_type: str  # "intervention", "diagnostic", "overview", etc.


def _build_params(**kwargs) -> dict:
    """Add API key and email to params if available."""
    params = {k: v for k, v in kwargs.items() if v is not None}
    if settings.ncbi_api_key:
        params["api_key"] = settings.ncbi_api_key
    if settings.ncbi_email:
        params["email"] = settings.ncbi_email
    return params


async def search_cochrane(
    query: str,
    max_results: int = 10,
) -> list[str]:
    """
    Search for Cochrane systematic reviews via PubMed.

    Restricts search to the Cochrane Database of Systematic Reviews journal.

    Args:
        query: Search term
        max_results: Number of results to return

    Returns:
        List of PMIDs for Cochrane reviews
    """
    # Restrict to Cochrane journal
    cochrane_query = f'({query}) AND ("{COCHRANE_JOURNAL}"[Journal])'

    params = _build_params(
        db="pubmed",
        term=cochrane_query,
        retmax=min(max_results, 50),
        sort="relevance",
        retmode="json",
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{BASE_URL}/esearch.fcgi", params=params)
        response.raise_for_status()
        data = response.json()

    return data.get("esearchresult", {}).get("idlist", [])


async def fetch_cochrane_reviews(pmids: list[str]) -> list[CochraneReview]:
    """
    Fetch Cochrane review details from PubMed.

    Args:
        pmids: List of PubMed IDs

    Returns:
        List of CochraneReview objects
    """
    if not pmids:
        return []

    # Reuse the PubMed fetch logic
    from lxml import etree

    params = _build_params(
        db="pubmed",
        id=",".join(pmids),
        retmode="xml",
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{BASE_URL}/efetch.fcgi", params=params)
        response.raise_for_status()

    root = etree.fromstring(response.content)
    reviews = []

    for article_elem in root.findall(".//PubmedArticle"):
        medline = article_elem.find(".//MedlineCitation")
        if medline is None:
            continue

        pmid = medline.findtext("PMID", default="")
        article = medline.find("Article")
        if article is None:
            continue

        title = article.findtext("ArticleTitle", default="No title")

        # Abstract
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
        abstract = " ".join(abstract_parts) if abstract_parts else ""

        # Authors
        authors = []
        author_list = article.find("AuthorList")
        if author_list is not None:
            for author in author_list.findall("Author"):
                last = author.findtext("LastName", "")
                first = author.findtext("ForeName", "")
                if last:
                    authors.append(f"{last} {first}".strip())

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

        # Build Cochrane URL from DOI if available
        cochrane_url = None
        if doi:
            cochrane_url = f"https://doi.org/{doi}"

        # Determine review type from title keywords
        review_type = "systematic_review"
        title_lower = title.lower()
        if "diagnostic" in title_lower:
            review_type = "diagnostic"
        elif "overview" in title_lower:
            review_type = "overview"
        elif "protocol" in title_lower:
            review_type = "protocol"

        reviews.append(CochraneReview(
            pmid=pmid,
            title=title,
            abstract=abstract,
            authors=authors,
            year=year,
            doi=doi,
            cochrane_url=cochrane_url,
            pubmed_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            review_type=review_type,
        ))

    return reviews


async def test_connection() -> dict:
    """Test the Cochrane search via PubMed."""
    try:
        pmids = await search_cochrane("hypertension treatment", max_results=3)
        if pmids:
            reviews = await fetch_cochrane_reviews(pmids[:1])
            return {
                "source": "Cochrane (via PubMed)",
                "status": "connected",
                "test_query": "hypertension treatment",
                "results_found": len(pmids),
                "sample_title": reviews[0].title if reviews else "N/A",
                "access_method": "PubMed E-Utilities (free)",
                "api_key_required": False,
            }
        return {
            "source": "Cochrane (via PubMed)",
            "status": "connected_no_results",
            "message": "API reachable but no Cochrane reviews found for test query",
        }
    except Exception as e:
        return {
            "source": "Cochrane (via PubMed)",
            "status": "error",
            "error": str(e),
        }
