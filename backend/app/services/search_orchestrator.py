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
from app.services import pubmed, clinical_trials, cochrane, who_iris, cdc, openalex, ods_dsld, openfda
from app.services.topic_classifier import classify_query_topic
from app.services.result_cache import get_cached_result, cache_result
from app.services.outlier_authors import (
    is_outlier_result,
    result_authors_match_outlier,
)

logger = get_logger("lena.search")


# Maps source names to their query functions
ALL_SOURCES = ["pubmed", "clinical_trials", "cochrane", "who_iris", "cdc", "openalex", "ods_dsld", "openfda"]


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


async def _query_ods_dsld(query: str, max_results: int) -> list[SourceResult]:
    """Query NIH ODS DSLD (supplement label database) and convert to SourceResult."""
    products = await ods_dsld.search_dsld(query, max_results=max_results)
    return [
        SourceResult(
            source_name="ods_dsld",
            title=p.title,
            summary=p.summary,
            url=p.url,
            year=p.year,
        )
        for p in products
    ]


async def _query_openfda(query: str, max_results: int) -> list[SourceResult]:
    """Query openFDA CAERS adverse events and convert to SourceResult."""
    events = await openfda.search_caers(query, max_results=max_results)
    return [
        SourceResult(
            source_name="openfda",
            title=e.title,
            summary=e.summary,
            url=e.url,
            year=e.year,
        )
        for e in events
    ]


# Map source names to their query functions
SOURCE_QUERY_MAP = {
    "pubmed": _query_pubmed,
    "clinical_trials": _query_clinical_trials,
    "cochrane": _query_cochrane,
    "who_iris": _query_who_iris,
    "cdc": _query_cdc,
    "openalex": _query_openalex,
    "ods_dsld": _query_ods_dsld,
    "openfda": _query_openfda,
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
    sources_failed: Optional[dict[str, str]] = None,
    sources_queried: Optional[list[str]] = None,
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

        # Build source coverage context so the LLM can reason about evidence gaps
        sources_with_results = set()
        evidence_lines: list[str] = []

        for idx, r in enumerate(pulse_report.validated_results[:12], 1):
            sources_with_results.add(r.source_name)
            line = f"[{idx}] ({r.source_name}) {r.title}"
            if r.summary:
                snippet = r.summary[:400] + ("…" if len(r.summary) > 400 else "")
                line += f"\n    {snippet}"
            if r.doi:
                line += f"\n    DOI: {r.doi}"
            evidence_lines.append(line)

        if pulse_report.edge_cases:
            evidence_lines.append("\n--- Edge Cases (single-source only) ---")
            for idx, r in enumerate(pulse_report.edge_cases[:4], len(evidence_lines)):
                sources_with_results.add(r.source_name)
                line = f"[{idx}] ({r.source_name}) {r.title}"
                if r.summary:
                    snippet = r.summary[:300] + ("…" if len(r.summary) > 300 else "")
                    line += f"\n    {snippet}"
                evidence_lines.append(line)

        # Source coverage preamble — critical for the LLM to understand
        # evidence quality and acknowledge gaps honestly.
        all_source_names = {
            "pubmed": "PubMed (NIH/NLM)",
            "cochrane": "Cochrane Library",
            "clinical_trials": "ClinicalTrials.gov",
            "who_iris": "WHO IRIS",
            "cdc": "CDC Open Data",
            "openalex": "OpenAlex",
            "ods_dsld": "NIH ODS DSLD (supplement labels)",
            "openfda": "openFDA CAERS (adverse events)",
        }
        queried = sources_queried or list(all_source_names.keys())
        failed = sources_failed or {}
        sources_no_results = [
            s for s in queried
            if s not in sources_with_results and s not in failed
        ]

        coverage_lines = []
        coverage_lines.append(f"Sources queried: {len(queried)} ({', '.join(queried)})")
        coverage_lines.append(f"Sources with results: {len(sources_with_results)} ({', '.join(sorted(sources_with_results)) or 'none'})")
        if failed:
            coverage_lines.append(f"Sources that errored: {', '.join(failed.keys())} ({', '.join(failed.values())})")
        if sources_no_results:
            coverage_lines.append(
                f"Sources with NO results for this query: {', '.join(sources_no_results)}. "
                "This means these peer-reviewed databases had no matching literature — "
                "acknowledge this coverage gap in your response."
            )
        if len(sources_with_results) <= 1 and len(queried) > 1:
            coverage_lines.append(
                "IMPORTANT: Only 1 source returned results. This is NOT cross-validated "
                "evidence. Be transparent about this limitation. If the query isn't purely "
                "medical, try to identify what health angle IS relevant and suggest a "
                "better-framed question the user could ask."
            )

        coverage_context = "\n".join(coverage_lines)
        evidence_context = "\n\n".join(evidence_lines)
        context = f"--- Source Coverage ---\n{coverage_context}\n\n--- Evidence ---\n{evidence_context}"

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
# Three disjoint-ish category buckets. A single result can match multiple
# (e.g. "curcumin supplement from Ayurveda" -> supplements + herbal + alternatives).
# Each bucket has a keyword set (token match against PULSE keywords + blob)
# and a phrase tuple (multi-word substring match against raw title+summary blob).

# SUPPLEMENTS — vitamins, minerals, amino acids, isolated compounds,
# probiotics, nutraceuticals. Things you swallow, mostly regulated-ish.
_SUPPLEMENTS_KEYWORDS: set[str] = {
    "supplement", "supplements", "multivitamin", "nutraceutical", "nutraceuticals",
    "probiotic", "probiotics", "prebiotic", "prebiotics", "postbiotic", "postbiotics",
    "electrolyte", "electrolytes",
    # vitamins
    "vitamin", "vitamins", "cholecalciferol", "ergocalciferol", "tocopherol",
    "ascorbate", "ascorbic", "niacin", "riboflavin", "thiamine", "pyridoxine",
    "biotin", "pantothenic", "cobalamin", "folate", "folinic",
    # minerals
    "magnesium", "zinc", "iron", "calcium", "selenium", "iodine", "copper",
    "chromium", "manganese", "potassium", "phosphorus", "molybdenum",
    # amino acids / derivatives
    "glutamine", "glycine", "taurine", "carnitine", "arginine", "lysine",
    "tryptophan", "creatine", "bcaa", "whey", "collagen", "glutathione",
    "nac", "n-acetylcysteine",
    # isolated phytocompounds sold as standalone pills
    "curcumin", "resveratrol", "quercetin", "nattokinase", "bromelain",
    "serrapeptase", "berberine", "lutein", "zeaxanthin", "lycopene",
    "coq10", "ubiquinol", "ubiquinone", "nmn", "nicotinamide",
    # lipids
    "omega-3", "epa", "dha",
    # sleep / mood
    "melatonin", "5-htp",
    # hormones / derivatives
    "dhea", "pregnenolone",
    # cannabinoid isolates
    "cbd", "cannabidiol",
    # misc
    "spirulina", "chlorella",
}

_SUPPLEMENTS_PHRASES: tuple[str, ...] = (
    "dietary supplement", "dietary supplements", "nutritional supplement",
    "vitamin a", "vitamin b", "vitamin c", "vitamin d", "vitamin e", "vitamin k",
    "fish oil", "cod liver", "krill oil", "omega 3", "omega-3",
    "amino acid", "amino acids", "protein powder", "whey protein",
    "coenzyme q10", "coenzyme q-10", "magnesium glycinate", "magnesium citrate",
    "folic acid", "b-complex", "b complex",
)

# HERBAL — whole-plant / botanical medicine. Single-herb extracts,
# teas, tinctures, plant monographs.
_HERBAL_KEYWORDS: set[str] = {
    "herb", "herbs", "herbal", "botanical", "botanicals", "phytotherapy",
    "phytomedicine", "tincture", "decoction", "infusion", "extract",
    # individual herbs / botanicals
    "turmeric", "ginger", "garlic", "ginseng", "ashwagandha", "ginkgo",
    "echinacea", "valerian", "chamomile", "rhodiola", "bacopa", "astragalus",
    "andrographis", "elderberry", "hawthorn", "fenugreek", "cinnamon",
    "peppermint", "lavender", "rosemary", "sage", "thyme", "oregano",
    "dandelion", "nettle", "licorice", "saffron", "passionflower",
    # mushrooms (medicinal)
    "reishi", "chaga", "cordyceps", "shiitake", "maitake",
    # other plant actives
    "kava", "kratom", "moringa",
}

_HERBAL_PHRASES: tuple[str, ...] = (
    "herbal medicine", "herbal remedy", "herbal extract", "herbal tea",
    "plant medicine", "plant-based medicine", "medicinal plant",
    "milk thistle", "st john's wort", "st. john's wort", "saw palmetto",
    "black cohosh", "dong quai", "gotu kola", "tea tree", "aloe vera",
    "lion's mane", "turkey tail", "essential oil", "essential oils",
    "holy basil", "tulsi",
)

# ALTERNATIVES — CAM modalities that are NOT ingestibles. Practices,
# techniques, traditional systems.
_ALTERNATIVES_KEYWORDS: set[str] = {
    "acupuncture", "acupressure", "homeopathy", "homeopathic", "naturopathy",
    "naturopathic", "chiropractic", "chiropractor", "osteopathy", "osteopathic",
    "ayurveda", "ayurvedic", "tcm", "reiki", "reflexology", "aromatherapy",
    "cupping", "moxibustion", "qigong", "meditation", "mindfulness",
    "hypnotherapy", "hypnosis", "biofeedback", "shiatsu", "rolfing",
    "pranayama", "iridology", "holistic", "integrative",
}

_ALTERNATIVES_PHRASES: tuple[str, ...] = (
    "traditional chinese medicine", "traditional medicine", "chinese medicine",
    "alternative medicine", "complementary medicine", "complementary and alternative",
    "integrative medicine", "functional medicine", "mind-body", "mind body",
    "tai chi", "qi gong", "yoga therapy", "energy healing", "crystal healing",
    "alexander technique", "craniosacral", "bowen therapy", "bach flower",
)

# Outlier therapeutics that used to live in the herbal bucket — keep
# reachable via search but don't tag as supplement/herbal/alternative.
_OUTLIER_THERAPEUTICS: set[str] = {
    "ivermectin", "hydroxychloroquine",
}

VALID_MODES = {"all", "supplements", "herbal", "alternatives", "outlier"}

# Map mode name -> (keyword_set, phrase_tuple)
_MODE_RULES: dict[str, tuple[set[str], tuple[str, ...]]] = {
    "supplements": (_SUPPLEMENTS_KEYWORDS, _SUPPLEMENTS_PHRASES),
    "herbal": (_HERBAL_KEYWORDS, _HERBAL_PHRASES),
    "alternatives": (_ALTERNATIVES_KEYWORDS, _ALTERNATIVES_PHRASES),
}

# Source -> default mode tag. Results from these sources get that mode
# auto-tagged regardless of content (they ARE the category).
_SOURCE_DEFAULT_MODES: dict[str, str] = {
    "ods_dsld": "supplements",
    "openfda": "supplements",
}


# ── Query-relevance filter ───────────────────────────────────────────
# Several sources (CDC Socrata catalog, WHO IRIS broad search) return
# rows where the common query words ("health", "benefits") match but the
# actual subject ("magnesium") is nowhere in the paper. A zero-signal
# result destroys credibility on the very first demo query. This filter
# runs AFTER we gather raw results and BEFORE mode scoping / PULSE: any
# paper whose title+summary does not mention at least one of the query's
# distinctive subject tokens is dropped.

_RELEVANCE_STOPWORDS: set[str] = {
    # Generic English stopwords we never want to require
    "the", "and", "for", "with", "from", "what", "which", "when", "where",
    "how", "why", "who", "that", "this", "these", "those", "there", "here",
    "about", "tell", "give", "show", "list", "find", "some", "more", "most",
    "best", "good", "bad", "want", "need", "any", "all", "few", "many",
    "also", "into", "have", "has", "had", "are", "was", "were", "will",
    "would", "could", "should", "can", "cant", "dont", "does", "did",
    "such", "than", "then", "just", "only", "very", "much", "please",
    # Common health/research filler that otherwise matches half of PubMed
    "health", "benefit", "benefits", "effect", "effects", "impact",
    "impacts", "risk", "risks", "outcome", "outcomes", "symptom",
    "symptoms", "study", "studies", "review", "reviews", "research",
    "paper", "papers", "evidence", "trial", "trials", "clinical",
    "patient", "patients", "people", "adult", "adults", "men", "male",
    "males", "women", "female", "females", "child", "children", "older",
    "younger", "elderly", "aged", "treatment", "treatments", "therapy",
    "therapies", "condition", "conditions", "disease", "diseases",
    "related", "associated", "use", "uses", "using", "used",
}


def _subject_terms(query: str, max_terms: int = 3, min_len: int = 4) -> list[str]:
    """Pull distinctive subject tokens out of the user's query.

    Picks the N longest non-stopword tokens of at least `min_len` chars.
    Length is a cheap proxy for specificity ("magnesium" > "benefits" >
    "male"). Returns empty list when nothing distinctive exists so the
    filter becomes a no-op rather than a hard block.
    """
    import re
    tokens = re.findall(r"[a-z][a-z0-9-]{2,}", query.lower())
    candidates = [
        t for t in tokens
        if len(t) >= min_len and t not in _RELEVANCE_STOPWORDS
    ]
    # Dedupe while preserving first-seen order
    seen: set[str] = set()
    ordered: list[str] = []
    for t in candidates:
        if t in seen:
            continue
        seen.add(t)
        ordered.append(t)
    ordered.sort(key=len, reverse=True)
    return ordered[:max_terms]


def _filter_relevant(
    results_by_source: dict[str, list[SourceResult]],
    subject_terms: list[str],
) -> dict[str, list[SourceResult]]:
    """Drop any result whose title+summary doesn't mention a subject term.

    OR-logic across subject_terms so multi-subject queries ("magnesium AND
    potassium") keep papers that mention either. When no subject terms
    could be extracted we pass everything through unchanged.
    """
    if not subject_terms:
        return results_by_source

    needles = [t.lower() for t in subject_terms]
    filtered: dict[str, list[SourceResult]] = {}
    for src, results in results_by_source.items():
        kept: list[SourceResult] = []
        for r in results:
            # Source-native rows (DSLD, openFDA) are categorical - they're
            # supplement label / adverse event data, so we trust the source
            # tag instead of demanding a token match in a 20-character label.
            if (r.source_name or "") in _SOURCE_DEFAULT_MODES:
                kept.append(r)
                continue
            blob = f"{r.title or ''} {r.summary or ''}".lower()
            if any(n in blob for n in needles):
                kept.append(r)
        if kept:
            filtered[src] = kept
    return filtered


def _normalise_modes(modes: Optional[list[str]]) -> list[str]:
    """Keep only known modes; empty / unknown collapses to ['all']."""
    if not modes:
        return ["all"]
    cleaned = [m for m in modes if m in VALID_MODES]
    return cleaned or ["all"]


def _tag_result_modes(result: SourceResult) -> None:
    """Populate result.matched_modes with every mode this result qualifies for.

    'all' is always included so a result is never invisible when no filter
    is active. 'supplements' / 'herbal' / 'alternatives' / 'outlier' are set
    based on content (and source-default for the category-native sources).
    """
    tags = ["all"]

    text_tokens = set((result.keywords or []))
    blob = f"{result.title or ''} {result.summary or ''}".lower()

    # Source-native tagging: ODS DSLD & openFDA ARE supplement data by definition.
    source_default = _SOURCE_DEFAULT_MODES.get(result.source_name or "")
    if source_default:
        tags.append(source_default)

    # Content-based tagging: check each mode's keyword set + phrase tuple.
    # Multi-word phrases ("vitamin c", "fish oil") never survive PULSE's alpha-
    # token extractor, so blob substring match is mandatory, not a fallback.
    for mode, (keywords, phrases) in _MODE_RULES.items():
        if mode in tags:
            continue  # already tagged via source default
        if (
            (text_tokens & keywords)
            or any(k in blob for k in keywords)
            or any(p in blob for p in phrases)
        ):
            tags.append(mode)

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
    bypass_guardrails: bool = False,
) -> dict:
    """
    Full LENA search pipeline:
    1. Check for medical advice guardrail
    2. Check result cache (keyed on query + sources + modes)
    3. Query all sources in parallel
    4. Tag every result with its matched_modes
       (all / supplements / herbal / alternatives / outlier)
    5. Scope the corpus to the user's selected modes BEFORE PULSE
    6. Run PULSE cross-reference validation on the scoped corpus
    7. Generate LLM summary and cache results

    Args:
        query: The user's search query
        max_results_per_source: Max results per source
        sources: Optional list of specific sources to query
        include_alt_medicine: Legacy toggle; ignored when `modes` is set
        persona: Persona for LLM summary
        modes: Active result-mode filters – any of "all", "supplements",
               "herbal", "alternatives", "outlier"

    Returns:
        Dictionary with PULSE report, source errors, timing, and metadata
    """
    # Back-compat: if caller didn't pass modes, derive from include_alt_medicine
    if modes is None:
        modes = ["all"] if include_alt_medicine else ["all"]
    modes = _normalise_modes(modes)

    start_time = time.time()
    logger.info(f"Starting search: query='{query}', modes={modes}")

    # Step 1: Content guardrails (self-harm > profanity > off-topic > advice).
    # Bypass users (internal testers on settings.bypass_user_ids) skip all
    # content guardrails so they can probe edge cases without friction.
    if bypass_guardrails:
        guardrail_type, guardrail_msg = None, None
        logger.info("Guardrails bypassed for tester user")
    else:
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

    # Step 3: Query all sources in parallel.
    # Transform the natural-language user query into a source-friendly
    # query. PubMed, OpenAlex, CDC Socrata etc. all AND-concat spaces,
    # so "Tell me about magnesium health benefits for males 50+" -> zero
    # hits on PubMed. Send the distinctive subject tokens instead so we
    # get broad recall; the relevance filter below then trims noise.
    subjects = _subject_terms(query)
    source_query = " ".join(subjects) if subjects else query
    if source_query != query:
        logger.info("Source query rewritten: %r -> %r", query, source_query)
    raw_results_by_source, errors = await search_all_sources(
        query=source_query,
        max_results_per_source=max_results_per_source,
        sources=sources,
    )

    if errors:
        logger.warning(f"Source errors: {errors}")

    # Step 3b: Drop papers that don't mention the query's subject term at
    # all. Saves PULSE from scoring / ranking noise like "COVID-19 case
    # surveillance" on a magnesium query (the exact bug Thommo hit in
    # demo).
    pre_relevance = sum(len(r) for r in raw_results_by_source.values())
    raw_results_by_source = _filter_relevant(raw_results_by_source, subjects)
    post_relevance = sum(len(r) for r in raw_results_by_source.values())
    if subjects:
        logger.info(
            "Relevance filter on %s: %d -> %d results",
            subjects, pre_relevance, post_relevance,
        )

    # Step 4+5: Tag results and scope corpus to active modes (pre-PULSE)
    scoped_results_by_source = _scope_corpus_by_modes(raw_results_by_source, modes)

    pre_scope = sum(len(r) for r in raw_results_by_source.values())
    post_scope = sum(len(r) for r in scoped_results_by_source.values())
    logger.debug(f"Mode scope {modes}: {pre_scope} -> {post_scope} results")

    # Step 6: Run PULSE validation on the scoped corpus only
    # Tell PULSE how many sources were ATTEMPTED (including failures)
    # so confidence_ratio penalizes low coverage honestly.
    total_sources_attempted = len(scoped_results_by_source) + len(errors)

    pulse_report = await run_pulse_validation(
        query=query,
        results_by_source=scoped_results_by_source,
    )
    # Inject the total-attempted count for confidence calculation
    pulse_report._sources_attempted = total_sources_attempted

    # PULSE re-extracts keywords; re-tag so matched_modes reflects the fresh keyword set
    for r in pulse_report.validated_results + pulse_report.edge_cases:
        _tag_result_modes(r)

    # Step 7: Generate LLM summary (non-blocking, best-effort)
    # Pass source coverage so the LLM can acknowledge evidence gaps honestly
    all_queried = list(raw_results_by_source.keys()) + list(errors.keys())
    llm_summary, llm_usage = await _generate_llm_summary(
        query, pulse_report, persona,
        sources_failed=errors,
        sources_queried=all_queried,
    )

    # Step 7b: Auto-verify supplement if query touches supplement keywords.
    # Runs in parallel with the LLM summary (both are post-PULSE) to add
    # zero latency. Gives users a trust stamp for any supplement they search.
    supplement_verification = None
    _is_supplement_query = (
        "supplements" in modes
        or any(
            t in _SUPPLEMENTS_KEYWORDS or any(p in query.lower() for p in _SUPPLEMENTS_PHRASES[:6])
            for t in (subjects or [])
        )
    )
    if _is_supplement_query and subjects:
        try:
            from app.services.supplement_verifier import verify_supplement
            # Split query into supplement name vs brand. Subject terms are the
            # longest non-stopword tokens; supplement keywords (vitamin, magnesium)
            # are the NAME, everything else that isn't a stopword is a likely BRAND.
            # "Nature Made Vitamin D 5000IU" → name="vitamin", brand="Nature Made"
            import re as _re
            _all_tokens = _re.findall(r"[A-Za-z][A-Za-z0-9'-]{2,}", query)
            _supp_name_parts = [t for t in subjects if t.lower() in _SUPPLEMENTS_KEYWORDS or t.lower() in _HERBAL_KEYWORDS]
            _brand_parts = [
                t for t in _all_tokens
                if t.lower() not in _RELEVANCE_STOPWORDS
                and t.lower() not in _SUPPLEMENTS_KEYWORDS
                and t.lower() not in _HERBAL_KEYWORDS
                and t.lower() not in {"supplement", "supplements", "brand", "product", "review", "best"}
                and len(t) >= 3
            ]
            supp_name = " ".join(_supp_name_parts) if _supp_name_parts else subjects[0]
            supp_brand = " ".join(_brand_parts[:3]) if _brand_parts else None
            sv = await verify_supplement(name=supp_name, brand=supp_brand, include_clinical=False)
            # Clinical evidence already counted from this search's results
            sv.clinical_evidence_count = len(
                [r for r in pulse_report.validated_results
                 if r.source_name in ("pubmed", "cochrane", "openalex")]
            )
            sv.cochrane_reviews = len(
                [r for r in pulse_report.validated_results if r.source_name == "cochrane"]
            )
            # Recompute score with clinical counts from this search
            from app.services.supplement_verifier import _compute_trust_score
            sv.trust_score, sv.trust_level, sv.trust_breakdown = _compute_trust_score(sv)
            supplement_verification = sv.to_dict()
        except Exception:
            logger.warning("Supplement verification failed (non-blocking)", exc_info=True)

    # Step 8: Build response
    response_time_ms = (time.time() - start_time) * 1000
    result = {
        "guardrail_triggered": False,
        "query": query,
        "sources_queried": all_queried,
        "sources_failed": errors,
        "total_results": post_scope,
        "total_pre_scope": pre_scope,
        "include_alt_medicine": include_alt_medicine,
        "modes": modes,
        "pulse_report": pulse_report.to_dict(),
        "supplement_verification": supplement_verification,
        "llm_summary": (advice_preamble + "\n\n" + llm_summary) if advice_preamble and llm_summary else llm_summary,
        "llm_usage": llm_usage,  # {model, prompt_tokens, completion_tokens, cost_micros} | None
        "response_time_ms": response_time_ms,
    }

    # Cache the result for future identical queries. Strip llm_usage before
    # storing so a subsequent cache hit can't accidentally re-bill anyone.
    to_cache = {**result, "llm_usage": None}
    cache_result(query, to_cache, sources, include_alt_medicine, modes)

    # Clear the per-request embedding cache so memory doesn't grow unbounded
    try:
        from app.services.openai_service import clear_embedding_cache
        clear_embedding_cache()
    except Exception:
        pass

    logger.info(f"Search completed: {len(pulse_report.validated_results)} validated results in {response_time_ms:.0f}ms")

    return result
