"""
Search Orchestrator

The glue that ties all 5 data sources together with PULSE validation.
Queries all sources in parallel, normalises results into SourceResult
objects, and runs them through the PULSE engine for cross-referencing.
"""

import asyncio
import time
from typing import Optional

from app.core.pulse_engine import SourceResult, run_pulse_validation, PULSEReport
from app.core.guardrails import check_for_advice_request, get_warm_redirect
from app.core.logging import get_logger
from app.core.config import settings
from app.services import pubmed, clinical_trials, cochrane, who_iris, cdc
from app.services.topic_classifier import classify_query_topic
from app.services.result_cache import get_cached_result, cache_result

logger = get_logger("lena.search")


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
        logger.warning(f"PubMed query failed: {e}")
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
        logger.warning(f"ClinicalTrials.gov query failed: {e}")
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
        logger.warning(f"Cochrane query failed: {e}")
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
        logger.warning(f"WHO IRIS query failed: {e}")
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
        logger.warning(f"CDC query failed: {e}")
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


async def _generate_llm_summary(
    query: str,
    pulse_report: PULSEReport,
    persona_type: str = "general",
) -> Optional[str]:
    """
    Use OpenAI to generate an intelligent, persona-aware summary from the
    search results.  Returns None gracefully if the key is not configured or
    the call fails so we never block the user.
    """
    if not settings.openai_api_key:
        logger.debug("OpenAI key not set – skipping LLM summary")
        return None

    try:
        from app.services.openai_service import generate_response
        from app.core.persona import PersonaType

        # Build evidence context from validated results + edge cases
        evidence_lines: list[str] = []
        for idx, r in enumerate(pulse_report.validated_results[:12], 1):
            line = f"[{idx}] ({r.source_name}) {r.title}"
            if r.summary:
                # Trim very long abstracts to keep token count sane
                snippet = r.summary[:400] + ("…" if len(r.summary) > 400 else "")
                line += f"\n    {snippet}"
            if r.doi:
                line += f"\n    DOI: {r.doi}"
            evidence_lines.append(line)

        if pulse_report.edge_cases:
            evidence_lines.append("\n--- Edge Cases (single-source only) ---")
            for idx, r in enumerate(pulse_report.edge_cases[:4], len(evidence_lines)):
                line = f"[{idx}] ({r.source_name}) {r.title}"
                if r.summary:
                    snippet = r.summary[:300] + ("…" if len(r.summary) > 300 else "")
                    line += f"\n    {snippet}"
                evidence_lines.append(line)

        context = "\n\n".join(evidence_lines)

        # Map string to PersonaType enum
        try:
            persona_enum = PersonaType(persona_type)
        except ValueError:
            persona_enum = PersonaType.GENERAL

        summary = await generate_response(
            query=query,
            context=context,
            persona=persona_enum,
            model="gpt-4o-mini",
        )
        return summary
    except Exception as e:
        logger.warning(f"LLM summary generation failed (non-blocking): {e}")
        return None


async def run_search(
    query: str,
    max_results_per_source: int = 10,
    sources: Optional[list[str]] = None,
    include_alt_medicine: bool = True,
    persona: str = "general",
) -> dict:
    """
    Full LENA search pipeline:
    1. Check for medical advice guardrail
    2. Check result cache
    3. Query all sources in parallel
    4. Run PULSE cross-reference validation
    5. Filter by alt medicine toggle
    6. Cache results and return unified response

    Args:
        query: The user's search query
        max_results_per_source: Max results per source
        sources: Optional list of specific sources to query
        include_alt_medicine: Whether to include alternative medicine results

    Returns:
        Dictionary with PULSE report, source errors, timing, and metadata
    """
    start_time = time.time()
    logger.info(f"Starting search: query='{query}', alt_medicine={include_alt_medicine}")

    # Step 1: Check medical advice guardrail
    if check_for_advice_request(query):
        logger.debug("Medical advice guardrail triggered")
        return {
            "guardrail_triggered": True,
            "guardrail_response": get_warm_redirect(query),
            "query": query,
            "pulse_report": None,
            "response_time_ms": (time.time() - start_time) * 1000,
        }

    # Step 2: Check cache
    cached = get_cached_result(query, sources, include_alt_medicine)
    if cached:
        cached["response_time_ms"] = (time.time() - start_time) * 1000
        cached["from_cache"] = True
        logger.info(f"Cache hit for query: '{query}'")
        return cached

    # Step 3: Query all sources in parallel
    results_by_source, errors = await search_all_sources(
        query=query,
        max_results_per_source=max_results_per_source,
        sources=sources,
    )

    if errors:
        logger.warning(f"Source errors: {errors}")

    # Step 4: Run PULSE validation
    pulse_report = await run_pulse_validation(
        query=query,
        results_by_source=results_by_source,
    )

    # Step 5: Filter by alt medicine toggle if needed
    if not include_alt_medicine and pulse_report.validated_results:
        alt_med_topics = classify_query_topic(query)
        alt_med_keywords = {"herbal", "herb", "acupuncture", "homeopathy", "naturopathy",
                            "ayurveda", "traditional medicine", "chinese medicine", "tcm",
                            "supplement", "natural remedy", "essential oil", "aromatherapy",
                            "meditation", "yoga", "chiropractic", "osteopathy", "holistic"}

        # Filter validated results
        filtered_results = []
        for result in pulse_report.validated_results:
            result_keywords = set(result.keywords or [])
            if not (result_keywords & alt_med_keywords):
                filtered_results.append(result)

        logger.debug(f"Alt medicine filter: {len(pulse_report.validated_results)} -> {len(filtered_results)} results")
        pulse_report.validated_results = filtered_results

    # Step 6: Generate LLM summary (non-blocking, best-effort)
    llm_summary = await _generate_llm_summary(query, pulse_report, persona)

    # Step 7: Build response
    response_time_ms = (time.time() - start_time) * 1000
    result = {
        "guardrail_triggered": False,
        "query": query,
        "sources_queried": list(results_by_source.keys()),
        "sources_failed": errors,
        "total_results": sum(len(r) for r in results_by_source.values()),
        "include_alt_medicine": include_alt_medicine,
        "pulse_report": pulse_report.to_dict(),
        "llm_summary": llm_summary,
        "response_time_ms": response_time_ms,
    }

    # Cache the result for future identical queries
    cache_result(query, result, sources, include_alt_medicine)
    logger.info(f"Search completed: {len(pulse_report.validated_results)} validated results in {response_time_ms:.0f}ms")

    return result
