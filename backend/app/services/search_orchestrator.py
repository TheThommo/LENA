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
from app.core.guardrails import run_all_guardrails
from app.core.logging import get_logger
from app.core.config import settings
from app.services import pubmed, clinical_trials, cochrane, who_iris, cdc, openalex
from app.services.topic_classifier import classify_query_topic
from app.services.result_cache import get_cached_result, cache_result
from app.services.outlier_authors import (
    is_outlier_result,
    result_authors_match_outlier,
)

logger = get_logger("lena.search")


# Maps source names to their query functions
ALL_SOURCES = ["pubmed", "clinical_trials", "cochrane", "who_iris", "cdc", "openalex"]


async def _query_pubmed(query: str, max_results: int) -> list[SourceResult]:
    """Query PubMed and convert to SourceResult objects."""
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
            authors=list(a.authors or []),
        )
        for a in articles
    ]


async def _query_clinical_trials(query: str, max_results: int) -> list[SourceResult]:
    """Query ClinicalTrials.gov and convert to SourceResult objects."""
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


async def _query_cochrane(query: str, max_results: int) -> list[SourceResult]:
    """Query Cochrane reviews (via PubMed) and convert to SourceResult objects."""
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
            authors=list(getattr(r, "authors", []) or []),
        )
        for r in reviews
    ]


async def _query_who_iris(query: str, max_results: int) -> list[SourceResult]:
    """Query WHO IRIS and convert to SourceResult objects."""
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


async def _query_cdc(query: str, max_results: int) -> list[SourceResult]:
    """Query CDC Open Data and convert to SourceResult objects."""
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


async def _query_openalex(query: str, max_results: int) -> list[SourceResult]:
    """Query OpenAlex and convert to SourceResult objects."""
    works = await openalex.search_openalex(query, max_results=max_results)
    return [
        SourceResult(
            source_name="openalex",
            title=w.title,
            summary=w.abstract,
            url=w.url,
            doi=w.doi,
            year=w.year,
            authors=list(getattr(w, "authors", []) or []),
        )
        for w in works
    ]


# Map source names to their query functions
SOURCE_QUERY_MAP = {
    "pubmed": _query_pubmed,
    "clinical_trials": _query_clinical_trials,
    "cochrane": _query_cochrane,
    "who_iris": _query_who_iris,
    "cdc": _query_cdc,
    "openalex": _query_openalex,
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
) -> tuple[Optional[str], Optional[dict]]:
    """
    Use OpenAI to generate an intelligent, persona-aware summary from the
    search results.

    Returns (summary, usage_dict). usage_dict has keys model, prompt_tokens,
    completion_tokens, cost_micros — or None if the call was skipped/failed
    so the caller knows there's no cost to record.
    """
    if not settings.openai_api_key:
        logger.debug("OpenAI key not set – skipping LLM summary")
        return None, None

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

        summary, usage = await generate_response(
            query=query,
            context=context,
            persona=persona_enum,
            model="gpt-4o-mini",
        )
        usage_dict = None
        if usage is not None:
            usage_dict = {
                "model": usage.model,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "cost_micros": usage.cost_micros,
            }
        return summary, usage_dict
    except Exception as e:
        logger.warning(f"LLM summary generation failed (non-blocking): {e}")
        return None, None


# ── Result-mode filter ───────────────────────────────────────────────
# Two sets:
#  * _ALT_MED_KEYWORDS — single-token matches (PULSE keyword intersection)
#  * _ALT_MED_PHRASES — multi-word phrases (scanned against title+summary blob)
# Must be tokens actually found in abstracts, including specific supplements
# and compounds that don't look "herbal" on the surface.
_ALT_MED_KEYWORDS: set[str] = {
    # modality / tradition tokens
    "herbal", "herb", "herbs", "acupuncture", "homeopathy", "naturopathy",
    "ayurveda", "ayurvedic", "tcm", "supplement", "supplements",
    "remedy", "remedies", "aromatherapy", "meditation", "yoga",
    "chiropractic", "osteopathy", "holistic", "phytotherapy", "botanical",
    "nutraceutical", "integrative", "functional",
    # specific herbs / supplements / compounds commonly studied
    "nattokinase", "quercetin", "curcumin", "turmeric", "resveratrol",
    "melatonin", "niacin", "nicotinamide", "berberine", "bromelain",
    "serrapeptase", "astragalus", "andrographis", "ashwagandha", "ginseng",
    "garlic", "ginger", "echinacea", "elderberry", "licorice", "rhodiola",
    "reishi", "cordyceps", "valerian", "chamomile", "passionflower",
    "saffron", "milk", "thistle", "spirulina", "chlorella",
    "ivermectin", "hydroxychloroquine",  # non-herbal but part of outlier therapeutics
    "glutathione", "nac", "lysine", "zinc", "magnesium",
    "omega", "probiotic", "probiotics", "prebiotic", "prebiotics",
    "cbd", "cannabidiol",
    # vitamin / fatty acid categories (without capturing "vitamin" alone which is too broad)
    "tocopherol", "cholecalciferol", "ascorbate", "ascorbic",
}

_ALT_MED_PHRASES: tuple[str, ...] = (
    "traditional medicine", "chinese medicine", "natural remedy",
    "essential oil", "complementary medicine", "alternative medicine",
    "integrative medicine", "functional medicine", "plant-based",
    "whole food", "whole-food", "vitamin c", "vitamin d", "vitamin e",
    "omega-3", "omega 3", "fish oil", "cod liver",
)

VALID_MODES = {"all", "herbal", "outlier"}


def _normalise_modes(modes: Optional[list[str]]) -> list[str]:
    """Keep only known modes; empty / unknown collapses to ['all']."""
    if not modes:
        return ["all"]
    cleaned = [m for m in modes if m in VALID_MODES]
    return cleaned or ["all"]


def _tag_result_modes(result: SourceResult) -> None:
    """Populate result.matched_modes with every mode this result qualifies for.

    'all' is always included so a result is never invisible when no filter
    is active. 'herbal' / 'outlier' are set based on content.
    """
    tags = ["all"]
    # Herbal / alt-med: check keyword tokens AND raw title+summary blob.
    # Multi-word phrases ("vitamin c", "fish oil") never survive PULSE's alpha-
    # token extractor, so the blob pass is mandatory — not a fallback.
    text_tokens = set((result.keywords or []))
    blob = f"{result.title or ''} {result.summary or ''}".lower()
    if (
        (text_tokens & _ALT_MED_KEYWORDS)
        or any(k in blob for k in _ALT_MED_KEYWORDS)
        or any(p in blob for p in _ALT_MED_PHRASES)
    ):
        tags.append("herbal")
    # Outlier: match against author list
    if is_outlier_result(result.authors or []):
        tags.append("outlier")
    result.matched_modes = tags


def _scope_corpus_by_modes(
    results_by_source: dict[str, list[SourceResult]],
    modes: list[str],
) -> dict[str, list[SourceResult]]:
    """Filter raw per-source results down to only those matching the active modes.

    Rules:
    - "all" in modes → pass everything through (no filter).
    - Otherwise union: a result is kept if it matches ANY active mode.
    - Tagging happens first so downstream consumers see matched_modes.
    """
    # Tag every result first
    for results in results_by_source.values():
        for r in results:
            _tag_result_modes(r)

    if "all" in modes:
        return results_by_source

    active = set(modes)
    scoped: dict[str, list[SourceResult]] = {}
    for src, results in results_by_source.items():
        kept = [r for r in results if active.intersection(r.matched_modes)]
        if kept:
            scoped[src] = kept
    return scoped


async def run_search(
    query: str,
    max_results_per_source: int = 10,
    sources: Optional[list[str]] = None,
    include_alt_medicine: bool = True,
    persona: str = "general",
    modes: Optional[list[str]] = None,
) -> dict:
    """
    Full LENA search pipeline:
    1. Check for medical advice guardrail
    2. Check result cache (keyed on query + sources + modes)
    3. Query all sources in parallel
    4. Tag every result with its matched_modes (all / herbal / outlier)
    5. Scope the corpus to the user's selected modes BEFORE PULSE
    6. Run PULSE cross-reference validation on the scoped corpus
    7. Generate LLM summary and cache results

    Args:
        query: The user's search query
        max_results_per_source: Max results per source
        sources: Optional list of specific sources to query
        include_alt_medicine: Legacy toggle; ignored when `modes` is set
        persona: Persona for LLM summary
        modes: Active result-mode filters – any of "all", "herbal", "outlier"

    Returns:
        Dictionary with PULSE report, source errors, timing, and metadata
    """
    # Back-compat: if caller didn't pass modes, derive from include_alt_medicine
    if modes is None:
        modes = ["all"] if include_alt_medicine else ["all"]
    modes = _normalise_modes(modes)

    start_time = time.time()
    logger.info(f"Starting search: query='{query}', modes={modes}")

    # Step 1: Content guardrails (self-harm > profanity > off-topic > advice)
    guardrail_type, guardrail_msg = run_all_guardrails(query)
    if guardrail_type and guardrail_type != "medical_advice":
        # Hard block — no search runs, show the guardrail message only
        logger.info(f"Guardrail BLOCK ({guardrail_type}): '{query[:80]}'")
        return {
            "guardrail_triggered": True,
            "guardrail_type": guardrail_type,
            "guardrail_message": guardrail_msg,
            "query": query,
            "pulse_report": None,
            "response_time_ms": (time.time() - start_time) * 1000,
        }
    # Medical-advice guardrail: search still runs, but the message is
    # prepended to the LLM summary so the user sees the redirect context.
    advice_preamble = guardrail_msg if guardrail_type == "medical_advice" else None

    # Step 2: Check cache
    cached = get_cached_result(query, sources, include_alt_medicine, modes)
    if cached:
        cached["response_time_ms"] = (time.time() - start_time) * 1000
        cached["from_cache"] = True
        # Never re-report the original request's cost on cache hits — would
        # double-count this user's LLM spend.
        cached["llm_usage"] = None
        logger.info(f"Cache hit for query: '{query}'")
        return cached

    # Step 3: Query all sources in parallel
    raw_results_by_source, errors = await search_all_sources(
        query=query,
        max_results_per_source=max_results_per_source,
        sources=sources,
    )

    if errors:
        logger.warning(f"Source errors: {errors}")

    # Step 4+5: Tag results and scope corpus to active modes (pre-PULSE)
    scoped_results_by_source = _scope_corpus_by_modes(raw_results_by_source, modes)

    pre_scope = sum(len(r) for r in raw_results_by_source.values())
    post_scope = sum(len(r) for r in scoped_results_by_source.values())
    logger.debug(f"Mode scope {modes}: {pre_scope} -> {post_scope} results")

    # Step 6: Run PULSE validation on the scoped corpus only
    pulse_report = await run_pulse_validation(
        query=query,
        results_by_source=scoped_results_by_source,
    )

    # PULSE re-extracts keywords; re-tag so matched_modes reflects the fresh keyword set
    for r in pulse_report.validated_results + pulse_report.edge_cases:
        _tag_result_modes(r)

    # Step 7: Generate LLM summary (non-blocking, best-effort)
    llm_summary, llm_usage = await _generate_llm_summary(query, pulse_report, persona)

    # Step 8: Build response
    response_time_ms = (time.time() - start_time) * 1000
    result = {
        "guardrail_triggered": False,
        "query": query,
        "sources_queried": list(raw_results_by_source.keys()),
        "sources_failed": errors,
        "total_results": post_scope,
        "total_pre_scope": pre_scope,
        "include_alt_medicine": include_alt_medicine,
        "modes": modes,
        "pulse_report": pulse_report.to_dict(),
        "llm_summary": (advice_preamble + "\n\n" + llm_summary) if advice_preamble and llm_summary else llm_summary,
        "llm_usage": llm_usage,  # {model, prompt_tokens, completion_tokens, cost_micros} | None
        "response_time_ms": response_time_ms,
    }

    # Cache the result for future identical queries. Strip llm_usage before
    # storing so a subsequent cache hit can't accidentally re-bill anyone.
    to_cache = {**result, "llm_usage": None}
    cache_result(query, to_cache, sources, include_alt_medicine, modes)
    logger.info(f"Search completed: {len(pulse_report.validated_results)} validated results in {response_time_ms:.0f}ms")

    return result
