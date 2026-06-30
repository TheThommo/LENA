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
from app.services import pubmed, clinical_trials, cochrane, who_iris, cdc, openalex, ods_dsld, openfda, semantic_scholar, europe_pmc, dailymed
from app.services.topic_classifier import classify_query_topic
from app.services.result_cache import get_cached_result, cache_result
from app.services.outlier_authors import (
    is_outlier_result,
    result_authors_match_outlier,
)

logger = get_logger("lena.search")


# Maps source names to their query functions
ALL_SOURCES = [
    "pubmed", "clinical_trials", "cochrane", "who_iris", "cdc", "openalex",
    "semantic_scholar", "europe_pmc", "dailymed",
    "ods_dsld", "openfda",
]


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
    results = []
    for t in trials:
        summary = t.summary or ""
        if t.nct_id:
            summary += (
                f"\n\nIPD data may be available via Vivli (partner platform): "
                f"https://vivli.org/ — search for {t.nct_id}"
            )
        results.append(
            SourceResult(
                source_name="clinical_trials",
                title=t.title,
                summary=summary.strip(),
                url=t.url,
                year=int(t.start_date[:4]) if t.start_date and len(t.start_date) >= 4 else None,
            )
        )
    return results


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


async def _query_dailymed(query: str, max_results: int) -> list[SourceResult]:
    labels = await dailymed.search_dailymed(query, max_results=max_results)
    return [
        SourceResult(
            source_name="dailymed",
            title=l.title,
            summary=l.summary,
            url=l.url,
        )
        for l in labels
    ]


async def _query_semantic_scholar(query: str, max_results: int) -> list[SourceResult]:
    papers = await semantic_scholar.search_semantic_scholar(query, max_results=max_results)
    return [
        SourceResult(
            source_name="semantic_scholar",
            title=p.title,
            summary=p.abstract,
            url=p.url,
            doi=p.doi,
            year=p.year,
            authors=list(p.authors or []),
        )
        for p in papers
    ]


async def _query_europe_pmc(query: str, max_results: int) -> list[SourceResult]:
    articles = await europe_pmc.search_europe_pmc(query, max_results=max_results)
    return [
        SourceResult(
            source_name="europe_pmc",
            title=a.title,
            summary=a.abstract,
            url=a.url,
            doi=a.doi,
            year=a.year,
            authors=list(a.authors or []),
        )
        for a in articles
    ]


# Map source names to their query functions
SOURCE_QUERY_MAP = {
    "pubmed": _query_pubmed,
    "clinical_trials": _query_clinical_trials,
    "cochrane": _query_cochrane,
    "who_iris": _query_who_iris,
    "cdc": _query_cdc,
    "openalex": _query_openalex,
    "semantic_scholar": _query_semantic_scholar,
    "europe_pmc": _query_europe_pmc,
    "dailymed": _query_dailymed,
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
    profile_context: Optional[str] = None,
    attached_context: Optional[str] = None,
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
            "semantic_scholar": "Semantic Scholar",
            "europe_pmc": "Europe PMC",
            "dailymed": "FDA DailyMed (drug labels)",
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
        if attached_context:
            context = f"{context}\n\n{attached_context}"

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
            profile_context=profile_context,
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
    # Brand-credibility / supplement-verification filler — queries like
    # "is Nutricost a credible brand" should NOT send "credible" or "brand"
    # to PubMed; those words match nothing useful in academic databases.
    "credible", "credibility", "legitimate", "legit", "trustworthy", "safe",
    "safety", "quality", "brand", "brands", "company", "companies",
    "reputation", "genuine", "authentic", "fake", "counterfeit", "scam",
    "reliable", "real", "recommend", "recommended", "worth", "worthwhile",
    "trusted", "certified", "certification", "verified", "verification",
    "tested", "testing", "approved", "pure", "purity", "potency", "potent",
    "effective", "effectiveness", "bogus", "fraudulent", "recall", "recalled",
    "money", "price", "cheap", "expensive", "affordable", "budget",
    "work", "works", "working", "product", "products", "pill", "pills",
    "capsule", "capsules", "tablet", "tablets", "powder", "liquid",
    "take", "taking", "dose", "dosage", "daily", "compare", "comparison",
    "powders", "powdered",
    "actually", "really", "truly", "still", "ever", "never", "always",
    "help", "helps", "helping", "cause", "causes", "prevent", "prevents",
    "know", "think", "believe", "guess", "wonder", "worry",
    # Personal context filler in long health-history prompts
    "currently", "taking", "started", "improved", "previously", "averaged",
    "around", "recent", "problems", "plan", "goals", "framing", "interested",
    "prefers", "wants", "complete", "strategy", "approach", "rather", "broad",
    "context", "diagnosed", "major", "concern", "listed", "depending",
    "product", "listing", "recommended", "serving", "capsule", "capsules",
    "tablet", "tablets", "foods", "nutrition", "gold", "california", "nutricost",
    "elemental", "buffered", "effervescent", "laperva", "bisglycinate", "malate",
    "taurate", "citrate", "oxide", "cholecalciferol",
    # Generic medical/research verbs & descriptors — match almost every paper
    "manage", "managing", "management", "option", "options", "approach",
    "approaches", "strategy", "strategies", "method", "methods",
    "latest", "current", "recent", "new", "novel", "emerging", "update",
    "updated", "guidelines", "guideline", "guide", "recommendation",
    "recommendations", "standard", "standards", "protocol", "protocols",
    "overview", "comprehensive", "narrative", "systematic", "meta-analysis",
    "diagnosis", "diagnostic", "prognosis", "prognostic", "screening",
    "prevention", "preventive", "intervention", "interventions",
    "role", "potential", "possible", "early", "advanced", "modern",
}

# Filler tokens that must never appear in supplement brand extraction.
# If detected, the whole supplement card is suppressed (query too noisy).
_SUPPLEMENT_BRAND_GARBAGE: set[str] = {
    "they", "them", "their", "floater", "floaters", "thing", "things",
    "stuff", "something", "anything", "everything", "someone", "anyone",
    "help", "helps", "helped", "works", "worked", "working",
    "does", "did", "doing", "take", "takes", "taking", "took",
    "should", "could", "would", "might", "maybe",
    "what", "how", "why", "when", "where", "which", "who", "whom",
}

_SUPPLEMENT_IDENTITY_STOPWORDS: set[str] = (
    _RELEVANCE_STOPWORDS
    | _SUPPLEMENTS_KEYWORDS
    | _HERBAL_KEYWORDS
    | _SUPPLEMENT_BRAND_GARBAGE
    | {
        "supplement", "supplements", "brand", "product", "review", "reviews", "best",
        "credible", "trustworthy", "good", "bad", "really", "very",
        "about", "with", "from", "into", "your", "you", "are", "was", "were",
        "have", "has", "had", "also", "just", "only", "safe", "effective",
        "sleep", "for", "the", "and", "not", "but", "can", "get", "use",
    }
)


def _extract_supplement_identity(
    query: str,
    subjects: list[str],
) -> tuple[str | None, str | None]:
    """Split a supplement query into ingredient name vs brand.

    Returns (None, None) when extraction confidence is too low — callers
    should skip rendering the supplement trust card.
    """
    import re

    if not subjects:
        return None, None

    all_tokens = re.findall(r"[A-Za-z][A-Za-z0-9'-]{2,}", query)

    name_parts = [
        t for t in subjects
        if t.lower() in _SUPPLEMENTS_KEYWORDS or t.lower() in _HERBAL_KEYWORDS
    ]

    raw_brand_parts = [
        t for t in all_tokens
        if t.lower() not in _SUPPLEMENT_IDENTITY_STOPWORDS
        and len(t) >= 3
    ]

    name_token_set = {t.lower() for t in name_parts}
    if any(
        t.lower() in _SUPPLEMENT_BRAND_GARBAGE and t.lower() not in name_token_set
        for t in all_tokens
    ):
        return None, None

    def _is_brand_like_token(token: str) -> bool:
        if token.isupper() and len(token) >= 2:
            return True
        if len(token) >= 2 and token[0].isupper() and token[1:].islower():
            return True
        return False

    brand_parts = [t for t in raw_brand_parts if _is_brand_like_token(t)][:3]
    supp_name = " ".join(name_parts) if name_parts else None
    supp_brand = " ".join(brand_parts) if brand_parts else None

    if not supp_name:
        # Brand-only credibility queries: "is Nutricost magnesium credible"
        if any(t.lower() in _SUPPLEMENTS_KEYWORDS | _HERBAL_KEYWORDS for t in subjects):
            supp_name = " ".join(
                t for t in subjects
                if t.lower() in _SUPPLEMENTS_KEYWORDS or t.lower() in _HERBAL_KEYWORDS
            ) or None
        elif brand_parts and not any(
            t.lower() in _SUPPLEMENTS_KEYWORDS | _HERBAL_KEYWORDS for t in subjects
        ):
            # Pure brand query — verifier expects name; use first brand token
            supp_name = brand_parts[0]
            supp_brand = " ".join(brand_parts[1:3]) if len(brand_parts) > 1 else None
        else:
            return None, None

    if not supp_name:
        return None, None

    if supp_brand:
        brand_tokens = supp_brand.lower().split()
        if brand_tokens:
            garbage = sum(1 for t in brand_tokens if t in _SUPPLEMENT_BRAND_GARBAGE)
            if garbage / len(brand_tokens) > 0.5:
                supp_brand = None

    return supp_name, supp_brand


_MEDICAL_CONDITION_KEYWORDS: set[str] = {
    "hypertension", "hypotension", "hypertensive", "retinopathy", "diabetes",
    "diabetic", "heartburn", "gerd", "reflux", "diarrhea", "constipation",
    "glaucoma", "macular", "stroke", "cardiovascular", "cholesterol",
    "hyperlipidemia", "anemia", "migraine", "epilepsy", "asthma", "copd",
    "arthritis", "osteoporosis", "neuropathy", "cancer", "oncology",
    "arrhythmia", "atrial", "fibrillation", "heart", "cardiac", "ocular",
    "vision", "csr",
}

_MEDICAL_CONDITION_PHRASES: tuple[str, ...] = (
    "central serous retinopathy", "blood pressure", "high blood pressure",
    "loose stools", "eye strain", "eye health", "vitamin d", "vitamin k",
    "magnesium supplementation", "headache powder", "headache powders",
)

# Symptom terms that match too many unrelated papers when a product is attached.
_GENERIC_SYMPTOM_TERMS: set[str] = {
    "headache", "headaches", "pain", "ache", "aches", "fever", "nausea",
    "fatigue", "symptom", "symptoms", "discomfort", "relief",
}


def _stem_variants(term: str) -> list[str]:
    """Return term plus simple plural/singular variants for substring matching."""
    t = term.lower()
    variants = {t}
    if t.endswith("s") and len(t) > 4:
        variants.add(t[:-1])
    elif not t.endswith("s"):
        variants.add(t + "s")
    return list(variants)


def _blob_matches_any(blob: str, terms: list[str]) -> bool:
    for term in terms:
        for variant in _stem_variants(term):
            if variant in blob:
                return True
    return False


def _query_fit_score(blob: str, terms: list[str]) -> float:
    """Fraction of subject terms found in title+summary (0..1)."""
    if not terms:
        return 1.0
    hits = sum(1 for t in terms if _blob_matches_any(blob, [t]))
    return hits / len(terms)



def _subject_terms(query: str, max_terms: int | None = None, min_len: int = 3) -> list[str]:
    """Pull distinctive subject tokens out of the user's query.

    Medical conditions and supplement/herbal keywords are prioritised so
    long personal-health prompts still retrieve relevant literature.
    """
    import re
    if max_terms is None:
        max_terms = min(10, 4 + len(query) // 250)

    ql = query.lower()
    phrase_hits = [p for p in _MEDICAL_CONDITION_PHRASES if p in ql]

    _academic = _SUPPLEMENTS_KEYWORDS | _HERBAL_KEYWORDS | _ALTERNATIVES_KEYWORDS
    tokens = re.findall(r"[a-z][a-z0-9-]{2,}", ql)
    candidates = [
        t for t in tokens
        if len(t) >= min_len and t not in _RELEVANCE_STOPWORDS
    ]
    seen: set[str] = set()
    ordered: list[str] = []
    for t in candidates:
        if t in seen:
            continue
        seen.add(t)
        ordered.append(t)

    def _tier(t: str) -> tuple[int, int]:
        if t in _MEDICAL_CONDITION_KEYWORDS:
            return (0, -len(t))
        if t in _academic:
            return (1, -len(t))
        return (2, -len(t))

    ordered.sort(key=_tier)
    token_terms = ordered[:max_terms]
    return list(dict.fromkeys(phrase_hits + token_terms))


def _build_source_query(query: str, subjects: list[str]) -> str:
    """Build a PubMed-friendly query from extracted subject terms."""
    ql = query.lower()
    phrase_hits = [p for p in _MEDICAL_CONDITION_PHRASES if p in ql][:2]
    _academic_vocab = _SUPPLEMENTS_KEYWORDS | _HERBAL_KEYWORDS | _ALTERNATIVES_KEYWORDS
    condition_terms = [t for t in subjects if t in _MEDICAL_CONDITION_KEYWORDS]
    academic_terms = [t for t in subjects if t.lower() in _academic_vocab]

    parts: list[str] = []
    for item in phrase_hits + condition_terms + academic_terms:
        if item not in parts:
            parts.append(item)
    if not parts:
        parts = subjects[:8] if subjects else []
    if not parts and len(query) > 400:
        return query[:400]
    return " ".join(parts[:8]) if parts else query


def _filter_relevant(
    results_by_source: dict[str, list[SourceResult]],
    subject_terms: list[str],
    primary_terms: Optional[list[str]] = None,
) -> dict[str, list[SourceResult]]:
    """Drop results whose title+summary don't match the query subject.

    When primary_terms are present (from attached product/URL context), require
    at least one primary ingredient/product match — generic symptom terms like
    'headache' alone are not enough.
    """
    if not subject_terms and not primary_terms:
        return results_by_source

    primary = [t.lower() for t in (primary_terms or [])]
    secondary = [
        t.lower() for t in subject_terms
        if t.lower() not in _GENERIC_SYMPTOM_TERMS or not primary
    ]
    fallback = [t.lower() for t in subject_terms]

    filtered: dict[str, list[SourceResult]] = {}
    for src, results in results_by_source.items():
        kept: list[SourceResult] = []
        for r in results:
            if (r.source_name or "") in _SOURCE_DEFAULT_MODES:
                kept.append(r)
                continue
            blob = f"{r.title or ''} {r.summary or ''}".lower()

            if primary:
                if _blob_matches_any(blob, primary):
                    kept.append(r)
                    continue
                # Without primary match, require 2+ non-generic secondary terms
                sec_hits = sum(1 for t in secondary if _blob_matches_any(blob, [t]))
                if sec_hits >= 2:
                    kept.append(r)
                continue

            needles = fallback or secondary
            if _blob_matches_any(blob, needles):
                kept.append(r)
        if kept:
            filtered[src] = kept
    return filtered


def _post_filter_by_query_fit(
    pulse_report,
    subject_terms: list[str],
    primary_terms: Optional[list[str]] = None,
    min_fit: float = 0.12,
) -> None:
    """Remove validated results with zero query overlap when product context exists."""
    if not primary_terms:
        return

    all_terms = list(dict.fromkeys(primary_terms + subject_terms))
    kept: list = []
    dropped: list = []
    for r in pulse_report.validated_results:
        blob = f"{r.title or ''} {r.summary or ''}".lower()
        fit = _query_fit_score(blob, all_terms)
        primary_hit = _blob_matches_any(blob, primary_terms)
        if primary_hit or fit >= min_fit:
            kept.append(r)
        else:
            dropped.append(r)

    pulse_report.validated_results = kept
    pulse_report.edge_cases.extend(dropped)

    # Never leave validated empty when papers exist — keeps PULSE scoring visible
    if primary_terms and not pulse_report.validated_results:
        pool = sorted(
            pulse_report.edge_cases,
            key=lambda r: r.relevance_score,
            reverse=True,
        )
        if pool:
            pulse_report.validated_results = pool[:8]
            pulse_report.edge_cases = pool[8:]


def _prioritize_display_keywords(result: SourceResult, subject_terms: list[str]) -> None:
    """Reorder keywords so query-relevant terms appear first; trim off-topic noise."""
    if not result.keywords or not subject_terms:
        return
    subject_set = set()
    for t in subject_terms:
        subject_set.update(_stem_variants(t))
    matched = [k for k in result.keywords if k in subject_set or any(s in k for s in subject_set)]
    rest = [k for k in result.keywords if k not in matched]
    # Drop keywords that look like generic paper filler when we have matches
    if matched:
        result.keywords = (matched + rest)[:8]
    else:
        result.keywords = result.keywords[:6]



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


PULSE_MAX_PER_SOURCE = 8
PULSE_MAX_TOTAL = 64


def _cap_corpus_for_pulse(
    results_by_source: dict[str, list[SourceResult]],
) -> dict[str, list[SourceResult]]:
    """Trim the corpus before PULSE so cross-validation stays bounded.

    Category modes already shrink via _scope_corpus_by_modes; "all" mode can
    still pass hundreds of papers and time out. Cap per source, then globally.
    """
    trimmed: dict[str, list[SourceResult]] = {}
    for src, results in results_by_source.items():
        if not results:
            continue
        ranked = sorted(results, key=lambda r: r.relevance_score, reverse=True)
        trimmed[src] = ranked[:PULSE_MAX_PER_SOURCE]

    total = sum(len(v) for v in trimmed.values())
    if total <= PULSE_MAX_TOTAL:
        return trimmed

    keep_one: dict[str, SourceResult] = {src: rs[0] for src, rs in trimmed.items() if rs}
    pool: list[SourceResult] = []
    for src, results in trimmed.items():
        pool.extend(results[1:])

    pool.sort(key=lambda r: r.relevance_score, reverse=True)
    slots = max(0, PULSE_MAX_TOTAL - len(keep_one))
    selected = list(keep_one.values()) + pool[:slots]

    capped: dict[str, list[SourceResult]] = {}
    for paper in selected:
        capped.setdefault(paper.source_name, []).append(paper)
    return capped


async def run_search(
    query: str,
    max_results_per_source: int = 10,
    sources: Optional[list[str]] = None,
    include_alt_medicine: bool = True,
    persona: str = "general",
    modes: Optional[list[str]] = None,
    bypass_guardrails: bool = False,
    profile_context: Optional[str] = None,
    attached_context: Optional[str] = None,
    attached_filename: Optional[str] = None,
    attached_kind: Optional[str] = None,
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

    # Step 1b: Ingest URLs embedded in the query + any uploaded attachment text.
    from app.services.content_ingest import (
        extract_search_terms_from_context,
        format_attached_context,
        ingest_attached_context_header,
        ingest_urls_from_query,
        strip_urls,
    )
    url_blocks = await ingest_urls_from_query(query)
    header_blocks = await ingest_attached_context_header(
        attached_context,
        filename=attached_filename,
        kind=attached_kind,
    )
    attached_blocks = url_blocks + header_blocks
    attached_context_text = format_attached_context(attached_blocks)
    literature_query = strip_urls(query) or query

    context_primary, context_secondary = extract_search_terms_from_context(attached_blocks)
    subjects = _subject_terms(literature_query)
    for term in context_primary + context_secondary:
        if term not in subjects:
            subjects.append(term)
    primary_terms = context_primary or None
    query_subjects = (context_primary + subjects) if context_primary else subjects

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
    source_query = _build_source_query(literature_query, query_subjects)
    if source_query != query:
        logger.info("Source query rewritten: %r -> %r", query[:120], source_query)
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
    raw_results_by_source = _filter_relevant(
        raw_results_by_source, subjects, primary_terms=primary_terms,
    )
    post_relevance = sum(len(r) for r in raw_results_by_source.values())
    if subjects or primary_terms:
        logger.info(
            "Relevance filter on %s (primary=%s): %d -> %d results",
            subjects, primary_terms, pre_relevance, post_relevance,
        )

    # Step 4+5: Tag results and scope corpus to active modes (pre-PULSE)
    scoped_results_by_source = _scope_corpus_by_modes(raw_results_by_source, modes)
    scoped_results_by_source = _cap_corpus_for_pulse(scoped_results_by_source)

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
        subject_terms=query_subjects,
    )
    # Inject the total-attempted count for confidence calculation
    pulse_report._sources_attempted = total_sources_attempted

    _post_filter_by_query_fit(pulse_report, subjects, primary_terms=primary_terms)

    # PULSE re-extracts keywords; re-tag so matched_modes reflects the fresh keyword set
    for r in pulse_report.validated_results + pulse_report.edge_cases:
        _tag_result_modes(r)
        _prioritize_display_keywords(r, query_subjects)

    # Step 7: Generate LLM summary (non-blocking, best-effort)
    # Pass source coverage so the LLM can acknowledge evidence gaps honestly
    all_queried = list(raw_results_by_source.keys()) + list(errors.keys())
    llm_summary, llm_usage = await _generate_llm_summary(
        query, pulse_report, persona,
        sources_failed=errors,
        sources_queried=all_queried,
        profile_context=profile_context,
        attached_context=attached_context_text or None,
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
            supp_name, supp_brand = _extract_supplement_identity(query, subjects)
            if supp_name:
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
        "attached_content": [b.to_dict() for b in attached_blocks if b.text or b.error],
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
