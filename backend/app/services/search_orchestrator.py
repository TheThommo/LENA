"""
Search Orchestrator

The glue that ties all 5 data sources together with PULSE validation.
Queries all sources in parallel, normalises results into SourceResult
objects, and runs them through the PULSE engine for cross-referencing.
"""

import asyncio
from typing import Optional

from app.core.pulse_engine import SourceResult, run_pulse_validation, PULSEReport
from app.core.guardrails import check_for_advice_request, get_warm_redirect
from app.services import pubmed, clinical_trials, cochrane, who_iris, cdc


# Maps source names to their query functions
ALL_SOURCES = ["pubmed", "clinical_trials", "cochrane", "who_iris", "cdc"]


async def _query_pubmed(query: str, max_results: int) -> list[SourceResult]:
    """Query PubMed and convert to SourceResult objects."""
    try:
        pmids = await pubmed.search_pubmed(query, max_results=max_results)
        if not pmids:
            return []
        articles = await pubmed.fetch_articles(pmids)
        return [
            SourceResult(
                source_name="pubmed",
                title=a.title,
                summary=a.abstract,
                url=a.url,
                doi=a.doi,
                year=a.year,
            )
            for a in articles
        ]
    except Exception as e:
        # Log but don't fail the whole search
        print(f"[LENA] PubMed query failed: {e}")
        return []


async def _query_clinical_trials(query: str, max_results: int) -> list[SourceResult]:
    """Query ClinicalTrials.gov and convert to SourceResult objects."""
    try:
        trials = await clinical_trials.search_trials(query, max_results=max_results)
        return [
            SourceResult(
                source_name="clinical_trials",
                title=t.title,
                summary=t.summary,
                url=t.url,
                year=int(t.start_date[:4]) if t.start_date and len(t.start_date) >= 4 else None,
            )
            for t in trials
        ]
    except Exception as e:
        print(f"[LENA] ClinicalTrials.gov query failed: {e}")
        return []


async def _query_cochrane(query: str, max_results: int) -> list[SourceResult]:
    """Query Cochrane reviews (via PubMed) and convert to SourceResult objects."""
    try:
        pmids = await cochrane.search_cochrane(query, max_results=max_results)
        if not pmids:
            return []
        reviews = await cochrane.fetch_cochrane_reviews(pmids)
        return [
            SourceResult(
                source_name="cochrane",
                title=r.title,
                summary=r.abstract,
                url=r.cochrane_url or r.pubmed_url,
                doi=r.doi,
                year=r.year,
            )
            for r in reviews
        ]
    except Exception as e:
        print(f"[LENA] Cochrane query failed: {e}")
        return []


async def _query_who_iris(query: str, max_results: int) -> list[SourceResult]:
    """Query WHO IRIS and convert to SourceResult objects."""
    try:
        docs = await who_iris.search_who_iris(query, max_results=max_results)
        return [
            SourceResult(
                source_name="who_iris",
                title=d.title,
                summary=d.description,
                url=d.url,
                year=d.year,
            )
            for d in docs
        ]
    except Exception as e:
        print(f"[LENA] WHO IRIS query failed: {e}")
        return []


async def _query_cdc(query: str, max_results: int) -> list[SourceResult]:
    """Query CDC Open Data and convert to SourceResult objects."""
    try:
        results = await cdc.search_cdc_data(query, max_results=max_results)
        return [
            SourceResult(
                source_name="cdc",
                title=r.get("name", "CDC Dataset"),
                summary=r.get("description", ""),
                url=r.get("url", ""),
            )
            for r in results
        ]
    except Exception as e:
        print(f"[LENA] CDC query failed: {e}")
        return []


# Map source names to their query functions
SOURCE_QUERY_MAP = {
    "pubmed": _query_pubmed,
    "clinical_trials": _query_clinical_trials,
    "cochrane": _query_cochrane,
    "who_iris": _query_who_iris,
    "cdc": _query_cdc,
}


async def search_all_sources(
    query: str,
    max_results_per_source: int = 10,
    sources: Optional[list[str]] = None,
) -> tuple[dict[str, list[SourceResult]], dict[str, str]]:
    """
    Query multiple data sources in parallel.

    Args:
        query: The search query
        max_results_per_source: Max results from each source
        sources: List of source names to query (defaults to all)

    Returns:
        Tuple of (results_by_source, errors_by_source)
    """
    sources_to_query = sources or ALL_SOURCES
    errors: dict[str, str] = {}

    # Build the list of coroutines to run in parallel
    tasks = {}
    for source_name in sources_to_query:
        if source_name in SOURCE_QUERY_MAP:
            tasks[source_name] = SOURCE_QUERY_MAP[source_name](query, max_results_per_source)

    # Run all queries in parallel
    task_names = list(tasks.keys())
    task_coros = list(tasks.values())
    raw_results = await asyncio.gather(*task_coros, return_exceptions=True)

    # Collect results and errors
    results_by_source: dict[str, list[SourceResult]] = {}
    for name, result in zip(task_names, raw_results):
        if isinstance(result, Exception):
            errors[name] = str(result)
        elif result:  # Only include sources that returned results
            results_by_source[name] = result

    return results_by_source, errors


async def run_search(
    query: str,
    max_results_per_source: int = 10,
    sources: Optional[list[str]] = None,
) -> dict:
    """
    Full LENA search pipeline:
    1. Check for medical advice guardrail
    2. Query all sources in parallel
    3. Run PULSE cross-reference validation
    4. Return unified response

    Args:
        query: The user's search query
        max_results_per_source: Max results per source
        sources: Optional list of specific sources to query

    Returns:
        Dictionary with PULSE report, source errors, and metadata
    """
    # Step 1: Check medical advice guardrail
    if check_for_advice_request(query):
        return {
            "guardrail_triggered": True,
            "guardrail_response": get_warm_redirect(query),
            "query": query,
            "pulse_report": None,
        }

    # Step 2: Query all sources in parallel
    results_by_source, errors = await search_all_sources(
        query=query,
        max_results_per_source=max_results_per_source,
        sources=sources,
    )

    # Step 3: Run PULSE validation
    pulse_report = await run_pulse_validation(
        query=query,
        results_by_source=results_by_source,
    )

    # Step 4: Build response
    return {
        "guardrail_triggered": False,
        "query": query,
        "sources_queried": list(results_by_source.keys()),
        "sources_failed": errors,
        "total_results": sum(len(r) for r in results_by_source.values()),
        "pulse_report": pulse_report.to_dict(),
    }
