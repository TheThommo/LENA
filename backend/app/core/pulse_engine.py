"""
PULSE Engine (Published Literature Source Evaluation)

The cross-reference validation engine. LENA queries multiple sources,
compares INDIVIDUAL FINDINGS across papers from different databases,
and scores how well the evidence converges.

This is NOT keyword matching. PULSE extracts claims from each paper's
abstract, cross-matches them against claims from papers in OTHER sources,
and weights by evidence hierarchy (systematic review > RCT > cohort >
case study > expert opinion).

Confidence (v2) scores agreement inside the *responding* evidence universe
for the active research lens — not "how many of every database answered":
- Claim corroboration across independent works/classes raises confidence.
- Source-class diversity (literature / trial / label / guideline) matters.
- Empty specialty databases are expected and do not punish the score.
- Below a minimum evidence gate, PULSE reports insufficient rather than a
  misleadingly low percentage.
"""

import re
import math
import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from difflib import SequenceMatcher

logger = logging.getLogger("lena.pulse")


class ValidationStatus(str, Enum):
    VALIDATED = "validated"
    EDGE_CASE = "edge_case"
    INSUFFICIENT = "insufficient_validation"
    PENDING = "pending"


# Status is a pure function of confidence against these published thresholds.
# Keep in sync with evals.assertions.CONFIDENCE_STATUS_THRESHOLDS and UI explainer.
# Bands (UI copy): ≥80 Strong · 60–79 Solid · 40–59 Emerging · <40 / gate fail Insufficient
CONFIDENCE_STATUS_THRESHOLDS: tuple[tuple[float, ValidationStatus], ...] = (
    (0.80, ValidationStatus.VALIDATED),
    (0.40, ValidationStatus.EDGE_CASE),
    (0.0, ValidationStatus.INSUFFICIENT),
)

# Database → independent evidence class (mode-agnostic identity).
SOURCE_CLASS_MAP: dict[str, str] = {
    "pubmed": "literature",
    "europe_pmc": "literature",
    "openalex": "literature",
    "semantic_scholar": "literature",
    "cochrane": "literature",
    "who_iris": "literature",
    "cdc": "literature",
    "clinical_trials": "trial_registry",
    "dailymed": "label",
    "openfda": "label",
    "ods_dsld": "label",
}

# Minimum evidence gate before a confidence % is shown.
PULSE_GATE_MIN_WORKS = 3
PULSE_GATE_MIN_CLASSES = 2
PULSE_GATE_MIN_WORKS_WITH_CLASSES = 2


def source_class_for(source_name: str) -> str:
    return SOURCE_CLASS_MAP.get((source_name or "").lower(), "literature")


def status_for_confidence(confidence: float) -> ValidationStatus:
    """Map confidence ratio → status label. Never set status independently."""
    c = float(confidence or 0.0)
    for threshold, label in CONFIDENCE_STATUS_THRESHOLDS:
        if c >= threshold:
            return label
    return ValidationStatus.INSUFFICIENT


# ── Evidence Hierarchy ─────────────────────────────────────────────────
# Higher weight = stronger evidence. Used to weight cross-validation
# so a Cochrane systematic review corroborating a PubMed RCT scores
# higher than two OpenAlex observational studies agreeing.

EVIDENCE_WEIGHTS = {
    "systematic_review": 1.5,
    "meta_analysis": 1.4,
    "rct": 1.3,
    "cohort": 1.1,
    "case_control": 1.0,
    "case_report": 0.8,
    "observational": 0.9,
    "editorial": 0.6,
    "unknown": 0.7,
}

# Source-level defaults (Cochrane is almost always systematic reviews)
SOURCE_EVIDENCE_DEFAULTS = {
    "cochrane": "systematic_review",
    "clinical_trials": "rct",
    "pubmed": "unknown",  # varies — detected per paper
    "who_iris": "unknown",
    "cdc": "observational",
    "openalex": "unknown",
    "semantic_scholar": "unknown",
    "europe_pmc": "unknown",
    "dailymed": "unknown",
    "ods_dsld": "observational",
    "openfda": "observational",
}

# Patterns to detect study type from abstract text
_STUDY_TYPE_PATTERNS = [
    (r"systematic review|systematically reviewed", "systematic_review"),
    (r"meta-analysis|meta analysis|pooled analysis", "meta_analysis"),
    (r"randomized controlled|randomised controlled|double-blind|placebo-controlled|RCT", "rct"),
    (r"cohort study|prospective study|longitudinal study|follow-up study", "cohort"),
    (r"case-control|case control|retrospective study", "case_control"),
    (r"case report|case series|single case", "case_report"),
    (r"cross-sectional|observational|survey|prevalence", "observational"),
    (r"editorial|commentary|opinion|letter to the editor", "editorial"),
]


def detect_study_type(text: str, source_name: str = "") -> str:
    """Detect study type from abstract text. Falls back to source default."""
    if not text:
        return SOURCE_EVIDENCE_DEFAULTS.get(source_name, "unknown")
    text_lower = text.lower()
    for pattern, study_type in _STUDY_TYPE_PATTERNS:
        if re.search(pattern, text_lower):
            return study_type
    return SOURCE_EVIDENCE_DEFAULTS.get(source_name, "unknown")


# ── Claim Extraction ───────────────────────────────────────────────────
# Extract key findings from abstracts at the sentence level.
# These are the units of cross-validation — not keywords.

# Sentence patterns that indicate a finding/claim
_CLAIM_INDICATORS = re.compile(
    r"(?:found that|showed that|demonstrated that|associated with|"
    r"resulted in|led to|reduced|increased|decreased|improved|"
    r"no significant|significantly|correlated with|linked to|"
    r"effective in|efficacy of|risk of|compared to|relative to|"
    r"odds ratio|hazard ratio|confidence interval|p\s*[<=]|"
    r"prevalence|incidence|mortality|morbidity|"
    r"conclude|suggest|indicate|reveal|confirm)",
    re.IGNORECASE,
)


def extract_claims(text: str, max_claims: int = 5) -> list[str]:
    """
    Extract key claim sentences from an abstract.

    A "claim" is a sentence that contains a finding indicator — something
    that states a result, association, or conclusion. Generic methods
    sentences ("We conducted a study...") are filtered out.
    """
    if not text or len(text) < 50:
        return []

    # Split into sentences (simple but effective for abstracts)
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    claims = []
    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 30 or len(sent) > 500:
            continue
        # Must contain a claim indicator
        if _CLAIM_INDICATORS.search(sent):
            # Skip pure methods sentences
            if re.match(r'^(We |This study |The aim |The purpose |The objective )', sent):
                if not re.search(r'found|showed|demonstrated|concluded', sent, re.I):
                    continue
            claims.append(sent)

    return claims[:max_claims]


# Medical term synonyms for improving claim matching across paraphrased
# findings. "Mortality" and "death" mean the same thing in a medical abstract.
_MEDICAL_SYNONYMS: dict[str, str] = {
    "death": "mortality", "deaths": "mortality", "died": "mortality",
    "fatal": "mortality", "lethal": "mortality",
    "elevated": "increased", "higher": "increased", "raised": "increased",
    "rise": "increased", "greater": "increased",
    "reduced": "decreased", "lower": "decreased", "declined": "decreased",
    "diminished": "decreased", "drop": "decreased",
    "cardiac": "cardiovascular", "heart": "cardiovascular",
    "bp": "blood_pressure", "hypertension": "blood_pressure",
    "temp": "temperature", "heat": "temperature", "hot": "temperature",
    "thermal": "temperature", "warming": "temperature",
    "dehydration": "fluid_loss", "fluid": "fluid_loss",
    "efficacy": "effectiveness", "effective": "effectiveness",
    "adverse": "side_effect", "toxicity": "side_effect",
}


def _normalize_medical_terms(words: set[str]) -> set[str]:
    """Map medical synonyms so 'death' and 'mortality' count as the same concept."""
    normalized = set()
    for w in words:
        normalized.add(_MEDICAL_SYNONYMS.get(w, w))
    return normalized


def _claim_similarity_lexical(claim_a: str, claim_b: str) -> float:
    """
    Lexical similarity: word-level Jaccard with medical synonym normalization.
    Fast fallback when embeddings are unavailable.
    """
    a = re.sub(r'[^a-z0-9\s]', '', claim_a.lower())
    b = re.sub(r'[^a-z0-9\s]', '', claim_b.lower())

    words_a = set(a.split()) - STOP_WORDS
    words_b = set(b.split()) - STOP_WORDS

    if not words_a or not words_b:
        return 0.0

    norm_a = _normalize_medical_terms(words_a)
    norm_b = _normalize_medical_terms(words_b)

    jaccard = len(norm_a & norm_b) / len(norm_a | norm_b)
    sequence = SequenceMatcher(None, a, b).ratio()

    return (jaccard * 0.65) + (sequence * 0.35)


# Thresholds — embedding similarity is higher-resolution than lexical,
# so it uses a tighter threshold.
CLAIM_MATCH_THRESHOLD_LEXICAL = 0.22
CLAIM_MATCH_THRESHOLD_EMBEDDING = 0.72

# Runtime flag: set to True when embeddings are available
_use_embeddings = False
_claim_embeddings: dict[str, list[float]] = {}


async def _precompute_claim_embeddings(all_claims: list[str]) -> bool:
    """
    Batch-embed all claims upfront. Returns True if successful.
    Falls back to lexical matching if OpenAI key is missing or API fails.
    """
    global _use_embeddings, _claim_embeddings
    _claim_embeddings.clear()

    try:
        from app.services.openai_service import get_embeddings, clear_embedding_cache
        from app.core.config import settings
        if not settings.openai_api_key or not all_claims:
            _use_embeddings = False
            return False

        # Deduplicate claims for efficient embedding
        unique_claims = list(set(all_claims))
        vectors = await get_embeddings(unique_claims)
        _claim_embeddings = dict(zip(unique_claims, vectors))
        _use_embeddings = True
        logger.info(f"Embedded {len(unique_claims)} unique claims for PULSE cross-validation")
        return True
    except Exception as e:
        logger.warning(f"Embedding failed, falling back to lexical matching: {e}")
        _use_embeddings = False
        return False


def _claim_similarity(claim_a: str, claim_b: str) -> float:
    """
    Semantic similarity between two claim sentences.

    Uses OpenAI embeddings (text-embedding-3-small) when available,
    falling back to lexical Jaccard + medical synonym normalization.

    Embeddings catch deep paraphrasing that word matching misses:
      "Heat exposure increased cardiovascular mortality"
      "Environmental temperature elevation was linked to excess cardiac deaths"
    These share almost no words but embeddings see them as the same finding.
    """
    if _use_embeddings and claim_a in _claim_embeddings and claim_b in _claim_embeddings:
        from app.services.openai_service import cosine_similarity
        return cosine_similarity(_claim_embeddings[claim_a], _claim_embeddings[claim_b])

    return _claim_similarity_lexical(claim_a, claim_b)


def _get_match_threshold() -> float:
    """Return the appropriate threshold for the current matching mode."""
    return CLAIM_MATCH_THRESHOLD_EMBEDDING if _use_embeddings else CLAIM_MATCH_THRESHOLD_LEXICAL


# ── Stop Words & Keywords ──────────────────────────────────────────────

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "can", "this", "that", "these",
    "those", "it", "its", "not", "no", "nor", "as", "if", "than", "then",
    "so", "up", "out", "about", "into", "over", "after", "before", "between",
    "under", "during", "through", "above", "below", "each", "all", "both",
    "few", "more", "most", "other", "some", "such", "only", "own", "same",
    "also", "very", "just", "because", "one", "two", "three", "four", "five",
    "study", "studies", "results", "result", "effect", "effects", "use",
    "used", "using", "based", "however", "conclusion", "conclusions",
    "background", "methods", "method", "objective", "objectives", "purpose",
    "review", "analysis", "data", "group", "groups", "compared", "associated",
    "significant", "significantly", "patients", "participants", "included",
    "including", "showed", "found", "reported",
}

MIN_KEYWORD_LENGTH = 3


@dataclass
class SourceResult:
    """A single result from one data source."""
    source_name: str
    title: str
    summary: str = ""
    url: str = ""
    doi: Optional[str] = None
    pmid: Optional[str] = None
    year: Optional[int] = None
    relevance_score: float = 0.0
    keywords: list[str] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    matched_modes: list[str] = field(default_factory=list)
    is_retracted: bool = False
    # Distinct-work identity (DOI → PMID → normalized title). Set by dedup.
    work_id: str = ""
    # Every database where this same work was retrieved (dedup audit trail).
    database_locations: list[str] = field(default_factory=list)
    # Dynamic PULSE fields (populated during validation)
    study_type: str = "unknown"
    claims: list[str] = field(default_factory=list)
    cross_validations: int = 0  # how many DISTINCT other works corroborate
    contradictions: int = 0     # how many papers from OTHER sources contradict


def normalize_title_for_dedup(title: str) -> str:
    """Topic-agnostic title key for work identity."""
    t = re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()
    return re.sub(r"\s+", " ", t)


def work_identity(result: "SourceResult") -> str:
    """
    Distinct-work key: DOI, then PMID, then normalized title.
    Never uses drug/disease names — identity fields only.
    """
    doi = (result.doi or "").strip().lower()
    if doi:
        # Strip resolver prefixes if present
        doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
        return f"doi:{doi}"
    pmid = (result.pmid or "").strip().lower()
    if not pmid and result.url:
        m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", result.url or "", re.I)
        if m:
            pmid = m.group(1)
        else:
            m = re.search(r"europepmc\.org/article/MED/(\d+)", result.url or "", re.I)
            if m:
                pmid = m.group(1)
    if pmid:
        return f"pmid:{pmid}"
    title_key = normalize_title_for_dedup(result.title)
    if title_key and len(title_key) >= 12:
        return f"title:{title_key}"
    # Last resort: unstable unique — do not collapse unknown empties together
    return f"row:{result.source_name}:{id(result)}"


def deduplicate_results_by_work(
    results_by_source: dict[str, list["SourceResult"]],
) -> dict[str, list["SourceResult"]]:
    """
    Collapse the same scholarly work seen in multiple databases into one
    SourceResult BEFORE cross-validation / counting.

    Primary source_name is the first location encountered (stable dict order);
    database_locations lists every DB that returned the work.
    """
    groups: dict[str, list[SourceResult]] = {}
    order: list[str] = []
    for source_name, results in results_by_source.items():
        for r in results:
            r.source_name = source_name or r.source_name
            wid = work_identity(r)
            r.work_id = wid
            if wid not in groups:
                groups[wid] = []
                order.append(wid)
            groups[wid].append(r)

    merged_by_source: dict[str, list[SourceResult]] = {}
    for wid in order:
        members = groups[wid]
        locations: list[str] = []
        for m in members:
            loc = m.source_name or ""
            if loc and loc not in locations:
                locations.append(loc)
        # Prefer the member with the longest summary as the canonical record
        primary = max(members, key=lambda x: len(x.summary or ""))
        primary.work_id = wid
        primary.database_locations = locations
        # Keep primary source_name as first location for bucketing; locations
        # retain the full audit trail of databases.
        if locations:
            primary.source_name = locations[0]
        merged_by_source.setdefault(primary.source_name, []).append(primary)

    raw_n = sum(len(v) for v in results_by_source.values())
    merged_n = sum(len(v) for v in merged_by_source.values())
    if merged_n < raw_n:
        logger.info(
            "PULSE dedup: %d raw results → %d distinct works (collapsed %d duplicates)",
            raw_n,
            merged_n,
            raw_n - merged_n,
        )
    return merged_by_source


@dataclass
class SourceAgreement:
    """Tracks how much a source's results overlap with the consensus."""
    source_name: str
    result_count: int
    keyword_overlap_score: float
    shared_keywords: list[str] = field(default_factory=list)
    unique_keywords: list[str] = field(default_factory=list)
    is_consensus: bool = True
    # Dynamic fields
    study_types_found: list[str] = field(default_factory=list)
    cross_validation_count: int = 0  # total cross-validations across this source's papers


@dataclass
class CrossValidation:
    """A specific finding corroborated between two papers from different sources."""
    paper_a_title: str
    paper_a_source: str
    paper_b_title: str
    paper_b_source: str
    claim_a: str
    claim_b: str
    similarity: float
    combined_weight: float  # evidence hierarchy weight of both papers


@dataclass
class PULSEReport:
    """The output of the PULSE validation process."""
    query: str
    validated_results: list[SourceResult] = field(default_factory=list)
    edge_cases: list[SourceResult] = field(default_factory=list)
    status: ValidationStatus = ValidationStatus.PENDING
    consensus_summary: str = ""
    consensus_keywords: list[str] = field(default_factory=list)
    source_count: int = 0
    agreement_count: int = 0
    source_agreements: list[SourceAgreement] = field(default_factory=list)
    # Dynamic cross-validation data
    cross_validations: list[CrossValidation] = field(default_factory=list)
    total_claims_extracted: int = 0
    total_cross_validations: int = 0
    total_contradictions: int = 0
    # Claim-pipeline audit trail (set by orchestrator / run_pulse_validation)
    atomic_claims: list[dict] = field(default_factory=list)
    claim_groups: list[dict] = field(default_factory=list)
    reconciliation_edge_cases: list[dict] = field(default_factory=list)

    @property
    def sources_queried_count(self) -> int:
        """Responding databases in the scored universe (not all planned DBs)."""
        return self.source_count

    @property
    def sources_attempted_count(self) -> int:
        return getattr(self, "_sources_attempted", self.source_count) or self.source_count

    @property
    def sources_failed_count(self) -> int:
        """Hard infra failures only when orchestrator set _sources_errored."""
        errored = getattr(self, "_sources_errored", None)
        if errored is not None:
            return int(errored)
        # Legacy fallback — do not invent failures from dedup collapse.
        return 0

    @property
    def confidence_ratio(self) -> float:
        return self._compute_confidence()["ratio"]

    def refresh_status(self) -> ValidationStatus:
        """
        Recompute status from current confidence (E9).

        Status is a pure function of confidence_ratio via status_for_confidence.
        Never assign VALIDATED / EDGE_CASE / PENDING independently of the ratio.
        Empty corpus / gate fail → confidence 0.0 → insufficient_validation.
        """
        self.status = status_for_confidence(self.confidence_ratio)
        return self.status

    def _responding_source_names(self) -> list[str]:
        names = {sa.source_name for sa in self.source_agreements if sa.source_name}
        for r in self.validated_results + self.edge_cases:
            if r.source_name:
                names.add(r.source_name)
            for loc in r.database_locations or []:
                if loc:
                    names.add(loc)
        return sorted(names)

    def _source_classes(self) -> list[str]:
        classes = {source_class_for(n) for n in self._responding_source_names()}
        return sorted(classes)

    def _active_lens(self) -> str:
        modes = getattr(self, "_active_modes", None) or ["all"]
        cleaned = [m for m in modes if m and m != "all"]
        if not cleaned:
            return "all"
        if len(cleaned) == 1:
            return cleaned[0]
        return "+".join(cleaned)

    def _evaluate_gate(self, *, distinct_works: int, source_classes: list[str]) -> dict:
        n_classes = len(source_classes)
        passed = distinct_works >= PULSE_GATE_MIN_WORKS or (
            n_classes >= PULSE_GATE_MIN_CLASSES
            and distinct_works >= PULSE_GATE_MIN_WORKS_WITH_CLASSES
        )
        if passed:
            reason = (
                f"Gate passed: {distinct_works} distinct works across "
                f"{n_classes} source class(es)."
            )
        elif distinct_works == 0:
            reason = "No relevant papers returned in this research lens."
        else:
            reason = (
                f"Need ≥{PULSE_GATE_MIN_WORKS} distinct works, or ≥"
                f"{PULSE_GATE_MIN_CLASSES} independent source classes with ≥"
                f"{PULSE_GATE_MIN_WORKS_WITH_CLASSES} works "
                f"(have {distinct_works} works, {n_classes} classes)."
            )
        return {
            "passed": passed,
            "reason": reason,
            "distinct_works": distinct_works,
            "source_classes": source_classes,
            "required_works": PULSE_GATE_MIN_WORKS,
            "required_classes": PULSE_GATE_MIN_CLASSES,
        }

    def _compute_confidence(self) -> dict:
        """
        Mode-aware confidence over the *responding* evidence universe.

        PULSE =
          0.55 × claim corroboration
        + 0.25 × source-class diversity
        + 0.20 × theme agreement
        − contradiction discount (capped)

        Empty non-responding databases are excluded from the denominator.
        """
        empty = {
            "ratio": 0.0,
            "claim_corroboration": 0.0,
            "source_class_diversity": 0.0,
            "theme_agreement": 0.0,
            # Legacy aliases kept for older UI clients during rollout
            "cross_validation_density": 0.0,
            "source_coverage": 0.0,
            "source_agreement": 0.0,
            "coverage_factor": 1.0,
            "edge_case_penalty": 0.0,
            "contradiction_penalty": 0.0,
            "gate": {
                "passed": False,
                "reason": "No relevant papers returned in this research lens.",
                "distinct_works": 0,
                "source_classes": [],
                "required_works": PULSE_GATE_MIN_WORKS,
                "required_classes": PULSE_GATE_MIN_CLASSES,
            },
            "justification": [
                "Insufficient for PULSE — no relevant papers in this research lens."
            ],
            "lens": self._active_lens(),
            "weights": {
                "claim_corroboration": 0.55,
                "source_class_diversity": 0.25,
                "theme_agreement": 0.20,
            },
            "evidence_tier_weights": dict(EVIDENCE_WEIGHTS),
            "status_thresholds": [
                {"min_confidence": t, "status": s.value}
                for t, s in CONFIDENCE_STATUS_THRESHOLDS
            ],
        }

        papers = self.validated_results + self.edge_cases
        total_papers = len(papers)
        if self.source_count == 0 or total_papers == 0:
            return empty

        responding = self._responding_source_names()
        classes = self._source_classes()
        distinct_works = int(
            getattr(self, "_distinct_work_count", total_papers) or total_papers
        )
        gate = self._evaluate_gate(
            distinct_works=distinct_works, source_classes=classes
        )

        if not gate["passed"]:
            out = dict(empty)
            out["gate"] = gate
            out["justification"] = [
                "Insufficient for PULSE — " + gate["reason"],
                f"Research lens: {self._active_lens()}.",
            ]
            out["lens"] = self._active_lens()
            out["source_coverage"] = 1.0  # responding universe is complete by definition
            return out

        papers_with_xval = sum(1 for r in papers if r.cross_validations > 0)
        claim_corroboration = papers_with_xval / total_papers

        # Full credit at 3 independent classes (literature / trial / label…)
        source_class_diversity = min(1.0, len(classes) / 3.0)

        responding_n = max(len(responding), 1)
        theme_agreement = min(1.0, self.agreement_count / responding_n)

        raw = (
            claim_corroboration * 0.55
            + source_class_diversity * 0.25
            + theme_agreement * 0.20
        )

        contradiction_penalty = 0.0
        if self.total_contradictions > 0:
            denom = max(1, self.total_cross_validations + self.total_contradictions)
            contradiction_penalty = min(
                0.45, self.total_contradictions / denom
            )
            raw *= 1.0 - (contradiction_penalty * 0.35)

        ratio = min(max(raw, 0.0), 0.95)

        # Soft floor once the gate has passed — never show ~0% for a valid corpus.
        if ratio < 0.40:
            baseline = min(
                0.48,
                0.32
                + 0.04 * min(len(classes), 3)
                + 0.01 * min(papers_with_xval, 8),
            )
            ratio = max(ratio, baseline)

        justification: list[str] = []
        justification.append(
            f"Scored within the {self._active_lens()} lens using "
            f"{len(responding)} responding database"
            f"{'' if len(responding) == 1 else 's'} "
            f"({', '.join(classes) or 'literature'})."
        )
        if papers_with_xval:
            justification.append(
                f"{papers_with_xval} of {total_papers} papers had claims "
                f"corroborated across independent works."
            )
        else:
            justification.append(
                "Findings were not yet corroborated across independent works."
            )
        justification.append(
            f"Source-class diversity: {len(classes)} class"
            f"{'' if len(classes) == 1 else 'es'} "
            f"({', '.join(classes)})."
        )
        if self.agreement_count:
            justification.append(
                f"{self.agreement_count} responding source"
                f"{'' if self.agreement_count == 1 else 's'} shared consensus themes."
            )
        if contradiction_penalty > 0:
            justification.append(
                f"Discounted for {self.total_contradictions} opposing / "
                f"superseding claim group(s)."
            )

        return {
            "ratio": ratio,
            "claim_corroboration": round(claim_corroboration, 2),
            "source_class_diversity": round(source_class_diversity, 2),
            "theme_agreement": round(theme_agreement, 2),
            # Legacy aliases (mapped to v2 components for older UI)
            "cross_validation_density": round(claim_corroboration, 2),
            "source_coverage": 1.0,
            "source_agreement": round(theme_agreement, 2),
            "coverage_factor": 1.0,
            "edge_case_penalty": 0.0,
            "contradiction_penalty": round(contradiction_penalty, 2),
            "gate": gate,
            "justification": justification,
            "lens": self._active_lens(),
            "responding_sources": responding,
            "source_classes": classes,
            "weights": {
                "claim_corroboration": 0.55,
                "source_class_diversity": 0.25,
                "theme_agreement": 0.20,
                # legacy keys for older clients
                "cross_validation_density": 0.55,
                "source_coverage": 0.25,
                "source_agreement": 0.20,
            },
            "evidence_tier_weights": dict(EVIDENCE_WEIGHTS),
            "status_thresholds": [
                {"min_confidence": t, "status": s.value}
                for t, s in CONFIDENCE_STATUS_THRESHOLDS
            ],
        }

    def to_dict(self) -> dict:
        """Serialise the report to a dictionary for API responses."""
        conf = self._compute_confidence()
        # E9: never emit a status that disagrees with the confidence ratio
        status = status_for_confidence(conf["ratio"])
        self.status = status
        return {
            "query": self.query,
            "status": status.value,
            "confidence_ratio": round(conf["ratio"], 2),
            "confidence_breakdown": conf,
            "source_count": self.source_count,
            "sources_attempted": self.sources_attempted_count,
            "sources_failed": self.sources_failed_count,
            "responding_sources": conf.get("responding_sources") or self._responding_source_names(),
            "source_classes": conf.get("source_classes") or self._source_classes(),
            "pulse_lens": conf.get("lens") or self._active_lens(),
            "pulse_gate": conf.get("gate"),
            "pulse_justification": conf.get("justification") or [],
            "agreement_count": self.agreement_count,
            "consensus_keywords": self.consensus_keywords[:20],
            "validated_count": len(self.validated_results),
            "edge_case_count": len(self.edge_cases),
            "consensus_summary": self.consensus_summary,
            "total_claims_extracted": self.total_claims_extracted,
            "total_cross_validations": self.total_cross_validations,
            "total_contradictions": self.total_contradictions,
            "atomic_claims": self.atomic_claims,
            "claim_groups": self.claim_groups,
            "reconciliation_edge_cases": self.reconciliation_edge_cases,
            "source_agreements": [
                {
                    "source": sa.source_name,
                    "result_count": sa.result_count,
                    "overlap_score": round(sa.keyword_overlap_score, 2),
                    "shared_keywords": sa.shared_keywords[:10],
                    "unique_keywords": sa.unique_keywords[:10],
                    "is_consensus": sa.is_consensus,
                    "study_types": sa.study_types_found,
                    "cross_validations": sa.cross_validation_count,
                }
                for sa in self.source_agreements
            ],
            "cross_validations": [
                {
                    "paper_a": xv.paper_a_title[:80],
                    "source_a": xv.paper_a_source,
                    "paper_b": xv.paper_b_title[:80],
                    "source_b": xv.paper_b_source,
                    "similarity": round(xv.similarity, 2),
                    "weight": round(xv.combined_weight, 2),
                }
                for xv in self.cross_validations[:20]  # Top 20 strongest
            ],
            "distinct_work_count": getattr(
                self, "_distinct_work_count", len(self.validated_results) + len(self.edge_cases)
            ),
            "raw_result_count_before_dedup": getattr(self, "_raw_result_count_before_dedup", None),
            "validated_results": [
                {
                    "source": r.source_name,
                    "title": r.title,
                    "url": r.url,
                    "doi": r.doi,
                    "pmid": r.pmid,
                    "year": r.year,
                    "work_id": r.work_id,
                    "database_locations": list(r.database_locations or [r.source_name]),
                    "relevance_score": round(r.relevance_score, 2),
                    "keywords": r.keywords[:10],
                    "authors": r.authors[:6],
                    "matched_modes": r.matched_modes,
                    "study_type": r.study_type,
                    "cross_validations": r.cross_validations,
                    "contradictions": r.contradictions,
                    "summary": (r.summary[:200] + "…") if len(r.summary) > 200 else r.summary,
                }
                for r in self.validated_results
            ],
            "edge_cases": [
                {
                    "source": r.source_name,
                    "title": r.title,
                    "url": r.url,
                    "doi": r.doi,
                    "pmid": r.pmid,
                    "year": r.year,
                    "work_id": r.work_id,
                    "database_locations": list(r.database_locations or [r.source_name]),
                    "keywords": r.keywords[:10],
                    "authors": r.authors[:6],
                    "matched_modes": r.matched_modes,
                    "study_type": r.study_type,
                    "cross_validations": r.cross_validations,
                    "contradictions": r.contradictions,
                }
                for r in self.edge_cases
            ],
        }


def extract_keywords(text: str, top_n: int = 15) -> list[str]:
    """Extract meaningful keywords from text using frequency analysis."""
    if not text:
        return []
    words = re.findall(r"[a-z]{3,}", text.lower())
    filtered = [w for w in words if w not in STOP_WORDS and len(w) >= MIN_KEYWORD_LENGTH]
    counts = Counter(filtered)
    return [word for word, _ in counts.most_common(top_n)]


def _compute_overlap(keywords_a: set[str], keywords_b: set[str]) -> float:
    """Compute Jaccard similarity between two keyword sets."""
    if not keywords_a or not keywords_b:
        return 0.0
    intersection = keywords_a & keywords_b
    union = keywords_a | keywords_b
    return len(intersection) / len(union) if union else 0.0


_THEME_WEAK_EDGE = {
    "less", "more", "such", "include", "includes", "including", "remain",
    "remains", "show", "shows", "showed", "using", "used", "via", "per",
    "within", "among", "across", "versus", "vs", "into", "onto", "able",
    "lower", "higher", "better", "worse", "related", "regarding",
    "programmes", "programs", "analyses", "contemporary", "broadly",
    "models", "reduces", "reduced", "reduce", "increased", "increase",
    "decreasing", "improved", "improves",
}

_THEME_CONNECTORS = {
    "of", "and", "for", "with", "after", "in", "on", "to", "vs", "versus",
    "or", "by",
}


def _is_alphabetised_token_join(phrase: str) -> bool:
    """
    True when a phrase looks like a sorted bag-of-tokens join (E7 failure mode).

    Require ≥3 tokens: legitimate bigrams (e.g. 'cardiac rehabilitation')
    are often alphabetical by chance.
    """
    words = [w for w in re.findall(r"[a-z0-9\-]+", (phrase or "").lower()) if w]
    return len(words) >= 3 and words == sorted(words)


def build_theme_clusters(
    texts: list[str],
    *,
    max_themes: int = 8,
    min_count: int = 1,
) -> list[str]:
    """
    Build multi-word theme phrases from claim/paper text (E7).

    Uses contiguous n-grams that appear in the source prose — never
    alphabetised token bags from proposition topics. Returns [] (omit)
    when no quality phrase clusters exist.
    """
    if not texts:
        return []

    counts: Counter = Counter()
    doc_hits: dict[str, set[int]] = {}
    for doc_i, text in enumerate(texts):
        if not text:
            continue
        # Skip alphabetised token-bag lines (legacy topic dumps) entirely
        if _is_alphabetised_token_join(text):
            continue
        words = re.findall(r"[a-z0-9][a-z0-9\-]{1,}", text.lower())
        if len(words) < 2:
            continue
        # Prefer content bigrams; allow connector trigrams ("X after Y")
        seen_in_doc: set[str] = set()
        for n in (2, 3):
            if len(words) < n:
                continue
            for i in range(len(words) - n + 1):
                window = words[i : i + n]
                if window[0] in STOP_WORDS or window[-1] in STOP_WORDS:
                    continue
                if window[0] in _THEME_WEAK_EDGE or window[-1] in _THEME_WEAK_EDGE:
                    continue
                if any(w in _THEME_WEAK_EDGE for w in window):
                    continue
                content = [
                    w
                    for w in window
                    if w not in STOP_WORDS
                    and w not in _THEME_CONNECTORS
                    and len(w) >= MIN_KEYWORD_LENGTH
                ]
                if len(content) < 2:
                    continue
                # Every token must be content or a light connector
                if any(w not in content and w not in _THEME_CONNECTORS for w in window):
                    continue
                # Trigrams must include a connector; otherwise prefer bigrams
                if n == 3 and not any(w in _THEME_CONNECTORS for w in window):
                    continue
                if all(w.isdigit() or len(w) <= 2 for w in content):
                    continue
                phrase = " ".join(window)
                if _is_alphabetised_token_join(phrase):
                    continue
                counts[phrase] += 1
                if phrase not in seen_in_doc:
                    doc_hits.setdefault(phrase, set()).add(doc_i)
                    seen_in_doc.add(phrase)

    if not counts:
        return []

    def _score(phrase: str) -> tuple:
        toks = phrase.split()
        content_n = sum(
            1
            for w in toks
            if w not in STOP_WORDS
            and w not in _THEME_CONNECTORS
            and len(w) >= MIN_KEYWORD_LENGTH
        )
        docs = len(doc_hits.get(phrase, ()))
        return (
            -counts[phrase],
            -docs,
            -content_n,
            -len(toks),
            phrase,
        )

    ranked = [p for p, c in counts.items() if c >= min_count]
    ranked.sort(key=_score)

    selected: list[str] = []
    selected_norm: list[str] = []
    for phrase in ranked:
        if _is_alphabetised_token_join(phrase):
            continue
        norm = phrase
        if any(norm in kept or kept in norm for kept in selected_norm):
            replaced = False
            for i, kept in enumerate(list(selected_norm)):
                if kept in norm and kept != norm and len(norm.split()) > len(kept.split()):
                    selected[i] = phrase
                    selected_norm[i] = norm
                    replaced = True
                    break
            if replaced or any(norm in kept for kept in selected_norm):
                continue
        selected.append(phrase)
        selected_norm.append(norm)
        if len(selected) >= max_themes:
            break

    if selected and (
        sum(1 for t in selected if _is_alphabetised_token_join(t)) / len(selected) >= 0.5
    ):
        return []
    return selected


async def run_pulse_validation(
    query: str,
    results_by_source: dict[str, list[SourceResult]],
    edge_case_threshold: float = 0.15,
    subject_terms: Optional[list[str]] = None,
    modes: Optional[list[str]] = None,
) -> PULSEReport:
    """
    Cross-reference results from multiple sources using BOTH keyword overlap
    AND citation-level claim matching.

    The process:
    1. Extract keywords per result (legacy, still useful for source profiling)
    2. Extract claims (key findings) from each paper's abstract
    3. Detect study type per paper (systematic review, RCT, cohort, etc.)
    4. Cross-match claims between papers from DIFFERENT sources
    5. Score each paper based on cross-validation count + evidence weight
    6. Build source-level agreement from both keyword overlap and claim matches
    7. Determine overall validation status (pure function of confidence)
    """
    report = PULSEReport(query=query)
    report._active_modes = list(modes or ["all"])
    query_terms = [t.lower() for t in (subject_terms or []) if t]

    if not results_by_source:
        report.source_count = 0
        report.refresh_status()  # E9: confidence 0 → insufficient_validation
        return report

    # ── Step 0: Dedup by distinct work (DOI → PMID → title) ───────────
    # Must run BEFORE any cross-validation counting. Same paper in PubMed
    # and Europe PMC is ONE work, not two independent corroborating sources.
    raw_before = sum(len(v) for v in results_by_source.values())
    results_by_source = deduplicate_results_by_work(results_by_source)
    report.source_count = len(results_by_source)
    report._raw_result_count_before_dedup = raw_before
    report._distinct_work_count = sum(len(v) for v in results_by_source.values())

    # ── Step 1: Extract keywords AND claims for every result ──────────
    source_keyword_profiles: dict[str, set[str]] = {}
    all_papers: list[SourceResult] = []
    all_claims_flat: list[str] = []  # for batch embedding

    for source_name, results in results_by_source.items():
        source_keywords: set[str] = set()
        for r in results:
            text = f"{r.title} {r.summary}"
            r.keywords = extract_keywords(text, top_n=15)
            r.claims = extract_claims(r.summary)
            r.study_type = detect_study_type(r.summary, source_name)
            r.source_name = source_name
            if not r.work_id:
                r.work_id = work_identity(r)
            if not r.database_locations:
                r.database_locations = [source_name]
            source_keywords.update(r.keywords)
            all_papers.append(r)
            all_claims_flat.extend(r.claims)
            report.total_claims_extracted += len(r.claims)
        source_keyword_profiles[source_name] = source_keywords

    # ── Step 1b: Batch-embed all claims for semantic matching ────────
    # Falls back to lexical matching if OpenAI API is unavailable.
    await _precompute_claim_embeddings(all_claims_flat)
    match_threshold = _get_match_threshold()

    # ── Step 2: Build consensus keywords (legacy, kept for theme display) ──
    min_sources_for_consensus = min(3, max(1, report.source_count // 2 + 1))
    all_keyword_counts: Counter = Counter()
    for keywords in source_keyword_profiles.values():
        for kw in keywords:
            all_keyword_counts[kw] += 1

    consensus_keywords = {
        kw for kw, count in all_keyword_counts.items()
        if count >= min_sources_for_consensus
    }
    report.consensus_keywords = sorted(consensus_keywords)

    # ── Step 3: Cross-validate claims between DISTINCT works ───────────
    # Independent corroboration requires a different work_id. Same work seen
    # in two databases must never increment cross_validations.
    for i, paper_a in enumerate(all_papers):
        if not paper_a.claims:
            continue
        for paper_b in all_papers[i + 1:]:
            if not paper_b.claims:
                continue
            # Same distinct work (post-dedup safety net)
            if paper_a.work_id and paper_b.work_id and paper_a.work_id == paper_b.work_id:
                continue
            # Same database bucket — not independent
            if paper_a.source_name == paper_b.source_name:
                continue
            # Also reject if location sets are identical single-DB mirrors
            loc_a = set(paper_a.database_locations or [paper_a.source_name])
            loc_b = set(paper_b.database_locations or [paper_b.source_name])
            if loc_a == loc_b and len(loc_a) == 1:
                continue

            # Compare every claim pair
            for claim_a in paper_a.claims:
                for claim_b in paper_b.claims:
                    sim = _claim_similarity(claim_a, claim_b)
                    if sim >= match_threshold:
                        weight_a = EVIDENCE_WEIGHTS.get(paper_a.study_type, 0.7)
                        weight_b = EVIDENCE_WEIGHTS.get(paper_b.study_type, 0.7)
                        combined_weight = (weight_a + weight_b) / 2.0

                        xv = CrossValidation(
                            paper_a_title=paper_a.title,
                            paper_a_source=paper_a.source_name,
                            paper_b_title=paper_b.title,
                            paper_b_source=paper_b.source_name,
                            claim_a=claim_a,
                            claim_b=claim_b,
                            similarity=sim,
                            combined_weight=combined_weight,
                        )
                        report.cross_validations.append(xv)
                        paper_a.cross_validations += 1
                        paper_b.cross_validations += 1
                        report.total_cross_validations += 1

    # Sort cross-validations by strength (similarity * weight)
    report.cross_validations.sort(
        key=lambda xv: xv.similarity * xv.combined_weight, reverse=True
    )

    # ── Step 4: Score each source against keyword consensus ──────────
    # Keyword uniqueness is ABSENCE / scope profiling — never divergence.
    # is_consensus stays True unless a later reconcile step finds a real
    # CONTRADICTION or TEMPORAL_SUPERSESSION involving that source.
    for source_name, source_kws in source_keyword_profiles.items():
        overlap_score = _compute_overlap(source_kws, consensus_keywords)
        shared = sorted(source_kws & consensus_keywords)
        unique = sorted(source_kws - consensus_keywords)

        source_papers = [p for p in all_papers if p.source_name == source_name]
        study_types = list(set(p.study_type for p in source_papers))
        xval_count = sum(p.cross_validations for p in source_papers)

        agreement = SourceAgreement(
            source_name=source_name,
            result_count=len(results_by_source[source_name]),
            keyword_overlap_score=overlap_score,
            shared_keywords=shared,
            unique_keywords=unique,
            is_consensus=True,
            study_types_found=study_types,
            cross_validation_count=xval_count,
        )
        report.source_agreements.append(agreement)

    # Agreement count for confidence: sources with corroborating signal
    # (keyword overlap or claim cross-validation) — not "non-divergent".
    report.agreement_count = sum(
        1
        for sa in report.source_agreements
        if sa.keyword_overlap_score >= edge_case_threshold or sa.cross_validation_count > 0
    )

    # ── Step 4b: Claim reconcile — only real conflicts flip is_consensus ─
    try:
        from app.core.claim_pipeline import (
            bind_claims_from_pulse_results,
            reconcile_claims,
            surfaceable_edge_cases,
            ReconcileClass,
        )

        bound = bind_claims_from_pulse_results(all_papers)
        groups = reconcile_claims(bound)
        edges = surfaceable_edge_cases(groups)
        report.atomic_claims = [c.to_dict() for c in bound]
        report.claim_groups = [g.to_dict() for g in groups]
        report.reconciliation_edge_cases = edges
        report.total_contradictions = sum(
            1 for e in edges if e.get("classification") == ReconcileClass.CONTRADICTION.value
        )

        conflict_sources: set[str] = set()
        for e in edges:
            for c in e.get("claims") or []:
                for sid in c.get("source_ids") or []:
                    conflict_sources.add(sid)
        for sa in report.source_agreements:
            if sa.source_name in conflict_sources:
                sa.is_consensus = False

        # E7: theme clusters = contiguous phrases from claim spans / titles.
        # Alphabetised proposition-token bags are not themes — omit if none.
        theme_texts: list[str] = []
        for c in bound:
            span = (getattr(c, "span", None) or getattr(c, "text", None) or "").strip()
            if span:
                theme_texts.append(span)
            for title in getattr(c, "source_titles", None) or []:
                if title:
                    theme_texts.append(str(title))
        if not theme_texts:
            for p in all_papers:
                if p.title:
                    theme_texts.append(p.title)
                if p.summary:
                    theme_texts.append(p.summary[:500])
        report.consensus_keywords = build_theme_clusters(theme_texts, max_themes=8)
    except Exception as e:
        logger.warning(f"Claim reconciliation skipped: {e}")
        # Still attempt themes from paper text when reconcile fails
        theme_texts = []
        for p in all_papers:
            if p.title:
                theme_texts.append(p.title)
            if p.summary:
                theme_texts.append(p.summary[:500])
        report.consensus_keywords = build_theme_clusters(theme_texts, max_themes=8)

    # Divergent sources for narrative = conflict participants only (D4/D5/D6)
    edge_sources = {sa.source_name for sa in report.source_agreements if not sa.is_consensus}

    MAX_PER_SOURCE = 10
    source_validated_counts: dict[str, int] = {}

    for source_name, results in results_by_source.items():
        source_validated_counts[source_name] = 0
        for r in results:
            if r.is_retracted:
                logger.debug(f"Excluding retracted paper: {r.title[:50]}")
                continue

            # Dynamic relevance score: consensus + cross-validation + query fit
            keyword_score = 0.0
            if consensus_keywords and r.keywords:
                keyword_score = len(set(r.keywords) & consensus_keywords) / len(consensus_keywords)

            xval_bonus = min(r.cross_validations * 0.15, 0.40)

            query_fit = 0.0
            if query_terms:
                blob = f"{r.title or ''} {r.summary or ''}".lower()
                hits = sum(1 for t in query_terms if t in blob)
                query_fit = hits / len(query_terms)

            evidence_weight = EVIDENCE_WEIGHTS.get(r.study_type, 0.7)

            if query_terms:
                base_score = (
                    keyword_score * 0.20 + xval_bonus * 0.20 + query_fit * 0.60
                ) * evidence_weight
            else:
                base_score = (keyword_score * 0.5 + xval_bonus * 0.5) * evidence_weight

            # Single-source cap: without cross-validation, max 0.40
            if len(results_by_source) == 1:
                base_score = min(base_score, 0.40)

            # Cochrane systematic review bump (earned, not hardcoded)
            if r.study_type in ("systematic_review", "meta_analysis"):
                base_score = min(base_score * 1.15, 0.95)

            r.relevance_score = min(base_score, 0.95)

            if source_validated_counts[source_name] < MAX_PER_SOURCE:
                report.validated_results.append(r)
                source_validated_counts[source_name] += 1
            else:
                report.edge_cases.append(r)

    # ── Step 6: Interleave results (round-robin by source) ───────────
    by_source: dict[str, list[SourceResult]] = {}
    for r in report.validated_results:
        by_source.setdefault(r.source_name, []).append(r)
    for src_results in by_source.values():
        src_results.sort(key=lambda r: r.relevance_score, reverse=True)

    interleaved: list[SourceResult] = []
    source_iters = {s: iter(rs) for s, rs in by_source.items()}
    source_order = sorted(
        source_iters.keys(),
        key=lambda s: next((sa.keyword_overlap_score for sa in report.source_agreements if sa.source_name == s), 0),
        reverse=True,
    )
    while source_iters:
        exhausted = []
        for src in source_order:
            if src not in source_iters:
                continue
            val = next(source_iters[src], None)
            if val is not None:
                interleaved.append(val)
            else:
                exhausted.append(src)
        for src in exhausted:
            del source_iters[src]
            source_order = [s for s in source_order if s != src]

    report.validated_results = interleaved

    # ── Step 7: Status is a pure function of confidence ───────────────
    # Never assign VALIDATED when confidence is below the published threshold.
    report.refresh_status()

    # ── Step 8: Build consensus summary ──────────────────────────────
    if report.consensus_keywords or report.total_cross_validations > 0 or report.reconciliation_edge_cases:
        parts = []
        sources_agreeing = [
            sa.source_name
            for sa in report.source_agreements
            if sa.keyword_overlap_score >= edge_case_threshold or sa.cross_validation_count > 0
        ]

        if report.total_cross_validations > 0:
            parts.append(
                f"{report.total_cross_validations} cross-validated finding(s) "
                f"identified across {len(sources_agreeing)} source(s)."
            )
        # Only surface multi-word theme clusters (omit raw token lists)
        theme_clusters = [t for t in report.consensus_keywords if " " in t or "-" in t]
        if theme_clusters:
            parts.append(f"Key themes: {', '.join(theme_clusters[:8])}.")
        for e in report.reconciliation_edge_cases[:4]:
            dtype = e.get("divergence_type") or e.get("classification") or "CONFLICT"
            reason = e.get("reason") or "sources diverge"
            parts.append(f"{dtype}: {reason}.")
        report.consensus_summary = " ".join(parts)

    return report
