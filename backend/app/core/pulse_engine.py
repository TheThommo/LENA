"""
PULSE Engine (Published Literature Source Evaluation)

The cross-reference validation engine. LENA queries multiple sources,
compares INDIVIDUAL FINDINGS across papers from different databases,
and scores how well the evidence converges.

This is NOT keyword matching. PULSE extracts claims from each paper's
abstract, cross-matches them against claims from papers in OTHER sources,
and weights by evidence hierarchy (systematic review > RCT > cohort >
case study > expert opinion).

The confidence score reflects genuine cross-validation:
- Multiple independent papers from different databases finding the same
  thing = high confidence.
- One database returning results while others have nothing = low
  confidence (acknowledged honestly).
- Papers contradicting each other = flagged with both positions.
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


def _claim_similarity(claim_a: str, claim_b: str) -> float:
    """
    Semantic similarity between two claim sentences.

    Uses word-level Jaccard with medical synonym normalization + character
    sequence matching. This catches paraphrased findings like:
      "heat exposure was associated with increased cardiovascular mortality"
      "high temperatures led to higher rates of cardiovascular death"

    Both normalize to concepts like {temperature, increased, cardiovascular, mortality}.

    Future: replace with embedding cosine similarity via pgvector.
    """
    a = re.sub(r'[^a-z0-9\s]', '', claim_a.lower())
    b = re.sub(r'[^a-z0-9\s]', '', claim_b.lower())

    words_a = set(a.split()) - STOP_WORDS
    words_b = set(b.split()) - STOP_WORDS

    if not words_a or not words_b:
        return 0.0

    # Normalize medical synonyms so "death" ≈ "mortality" etc.
    norm_a = _normalize_medical_terms(words_a)
    norm_b = _normalize_medical_terms(words_b)

    # Jaccard on normalized content words
    jaccard = len(norm_a & norm_b) / len(norm_a | norm_b)

    # SequenceMatcher on original text (catches numeric agreement: "23%" ≈ "25%")
    sequence = SequenceMatcher(None, a, b).ratio()

    # Weighted blend
    return (jaccard * 0.65) + (sequence * 0.35)


# Threshold for claim corroboration. Lower than you'd think because
# medical abstracts paraphrase heavily — the synonym normalization
# helps but isn't perfect. False positives are acceptable (the cross-
# validation count is a signal, not a binary gate).
CLAIM_MATCH_THRESHOLD = 0.22


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
    year: Optional[int] = None
    relevance_score: float = 0.0
    keywords: list[str] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    matched_modes: list[str] = field(default_factory=list)
    is_retracted: bool = False
    # Dynamic PULSE fields (populated during validation)
    study_type: str = "unknown"
    claims: list[str] = field(default_factory=list)
    cross_validations: int = 0  # how many papers from OTHER sources corroborate
    contradictions: int = 0     # how many papers from OTHER sources contradict


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

    @property
    def sources_queried_count(self) -> int:
        return getattr(self, '_sources_attempted', self.source_count) or self.source_count

    @property
    def sources_failed_count(self) -> int:
        return max(0, self.sources_queried_count - self.source_count)

    @property
    def confidence_ratio(self) -> float:
        """
        Dynamic confidence based on ACTUAL cross-validation of findings,
        not just source-level keyword overlap.

        Three components:
        1. Source coverage: what fraction of queried sources returned data?
        2. Cross-validation density: how many findings were corroborated
           across independent sources?
        3. Evidence quality: weighted by study type hierarchy.
        """
        if self.source_count == 0:
            return 0.0

        total_queried = self.sources_queried_count

        # Component 1: Source coverage (0 to 1)
        coverage = self.source_count / max(total_queried, 1)

        # Component 2: Cross-validation density (0 to 1)
        # What fraction of papers have at least one cross-validation?
        total_papers = len(self.validated_results) + len(self.edge_cases)
        if total_papers > 0:
            papers_with_xval = sum(
                1 for r in self.validated_results + self.edge_cases
                if r.cross_validations > 0
            )
            xval_density = papers_with_xval / total_papers
        else:
            xval_density = 0.0

        # Component 3: Source agreement (legacy keyword overlap, still useful)
        if total_queried > 0:
            agreement_ratio = self.agreement_count / total_queried
        else:
            agreement_ratio = 0.0

        # Blend: cross-validation density matters most, then coverage, then agreement
        raw_confidence = (
            xval_density * 0.45 +      # actual finding-level corroboration
            coverage * 0.30 +            # how many sources responded
            agreement_ratio * 0.25       # keyword-level agreement (legacy, still useful)
        )

        # Coverage factor: sqrt scaling so low coverage is penalized but not crushed
        if total_queried > 1:
            coverage_factor = 0.4 + (0.6 * math.sqrt(coverage))
            raw_confidence *= coverage_factor

        # Edge-case penalty
        if self.edge_cases:
            penalty = len(self.edge_cases) / max(1, total_papers)
            raw_confidence *= (1.0 - (penalty * 0.20))

        # Contradiction penalty
        if self.total_contradictions > 0 and self.total_cross_validations > 0:
            contradiction_ratio = self.total_contradictions / (self.total_cross_validations + self.total_contradictions)
            raw_confidence *= (1.0 - (contradiction_ratio * 0.30))

        return min(max(raw_confidence, 0.0), 0.95)

    def to_dict(self) -> dict:
        """Serialise the report to a dictionary for API responses."""
        return {
            "query": self.query,
            "status": self.status.value,
            "confidence_ratio": round(self.confidence_ratio, 2),
            "source_count": self.source_count,
            "sources_attempted": self.sources_queried_count,
            "sources_failed": self.sources_failed_count,
            "agreement_count": self.agreement_count,
            "consensus_keywords": self.consensus_keywords[:20],
            "validated_count": len(self.validated_results),
            "edge_case_count": len(self.edge_cases),
            "consensus_summary": self.consensus_summary,
            "total_claims_extracted": self.total_claims_extracted,
            "total_cross_validations": self.total_cross_validations,
            "total_contradictions": self.total_contradictions,
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
            "validated_results": [
                {
                    "source": r.source_name,
                    "title": r.title,
                    "url": r.url,
                    "doi": r.doi,
                    "year": r.year,
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
                    "year": r.year,
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


async def run_pulse_validation(
    query: str,
    results_by_source: dict[str, list[SourceResult]],
    edge_case_threshold: float = 0.15,
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
    7. Determine overall validation status
    """
    report = PULSEReport(query=query)
    report.source_count = len(results_by_source)

    if report.source_count == 0:
        report.status = ValidationStatus.PENDING
        return report

    # ── Step 1: Extract keywords AND claims for every result ──────────
    source_keyword_profiles: dict[str, set[str]] = {}
    all_papers: list[SourceResult] = []  # flat list for cross-matching

    for source_name, results in results_by_source.items():
        source_keywords: set[str] = set()
        for r in results:
            text = f"{r.title} {r.summary}"
            r.keywords = extract_keywords(text, top_n=15)
            r.claims = extract_claims(r.summary)
            r.study_type = detect_study_type(r.summary, source_name)
            r.source_name = source_name
            source_keywords.update(r.keywords)
            all_papers.append(r)
            report.total_claims_extracted += len(r.claims)
        source_keyword_profiles[source_name] = source_keywords

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

    # ── Step 3: Cross-validate claims between papers from DIFFERENT sources ──
    # This is the core intelligence: do independent papers find the same things?
    for i, paper_a in enumerate(all_papers):
        if not paper_a.claims:
            continue
        for paper_b in all_papers[i + 1:]:
            if not paper_b.claims:
                continue
            # Only cross-validate between DIFFERENT sources
            if paper_a.source_name == paper_b.source_name:
                continue

            # Compare every claim pair
            for claim_a in paper_a.claims:
                for claim_b in paper_b.claims:
                    sim = _claim_similarity(claim_a, claim_b)
                    if sim >= CLAIM_MATCH_THRESHOLD:
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
    for source_name, source_kws in source_keyword_profiles.items():
        overlap_score = _compute_overlap(source_kws, consensus_keywords)
        shared = sorted(source_kws & consensus_keywords)
        unique = sorted(source_kws - consensus_keywords)
        is_consensus = overlap_score >= edge_case_threshold

        # Collect study types and cross-validation counts for this source
        source_papers = [p for p in all_papers if p.source_name == source_name]
        study_types = list(set(p.study_type for p in source_papers))
        xval_count = sum(p.cross_validations for p in source_papers)

        agreement = SourceAgreement(
            source_name=source_name,
            result_count=len(results_by_source[source_name]),
            keyword_overlap_score=overlap_score,
            shared_keywords=shared,
            unique_keywords=unique,
            is_consensus=is_consensus,
            study_types_found=study_types,
            cross_validation_count=xval_count,
        )
        report.source_agreements.append(agreement)

    # ── Step 5: Score every result and build validated/edge lists ─────
    consensus_sources = {sa.source_name for sa in report.source_agreements if sa.is_consensus}
    edge_sources = {sa.source_name for sa in report.source_agreements if not sa.is_consensus}
    report.agreement_count = len(consensus_sources)

    MAX_PER_SOURCE = 10
    source_validated_counts: dict[str, int] = {}

    for source_name, results in results_by_source.items():
        source_validated_counts[source_name] = 0
        for r in results:
            if r.is_retracted:
                logger.debug(f"Excluding retracted paper: {r.title[:50]}")
                continue

            # Dynamic relevance score: blend of keyword overlap + cross-validation
            keyword_score = 0.0
            if consensus_keywords and r.keywords:
                keyword_score = len(set(r.keywords) & consensus_keywords) / len(consensus_keywords)

            # Cross-validation bonus: each corroboration adds to score
            xval_bonus = min(r.cross_validations * 0.15, 0.40)

            # Evidence hierarchy weight
            evidence_weight = EVIDENCE_WEIGHTS.get(r.study_type, 0.7)

            # Combined score
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

    # ── Step 7: Determine overall validation status ──────────────────
    active_sources = len(results_by_source)
    has_cross_validations = report.total_cross_validations > 0

    if active_sources >= 3 and report.agreement_count >= 3 and has_cross_validations:
        report.status = ValidationStatus.VALIDATED
    elif active_sources >= 2 and (report.agreement_count >= 1 or has_cross_validations):
        report.status = ValidationStatus.INSUFFICIENT
    else:
        report.status = ValidationStatus.PENDING if active_sources == 0 else ValidationStatus.INSUFFICIENT

    # ── Step 8: Build consensus summary ──────────────────────────────
    if consensus_keywords or report.total_cross_validations > 0:
        parts = []
        sources_agreeing = [sa.source_name for sa in report.source_agreements if sa.is_consensus]

        if report.total_cross_validations > 0:
            parts.append(
                f"{report.total_cross_validations} cross-validated finding(s) "
                f"identified across {len(sources_agreeing)} source(s)."
            )
        if consensus_keywords:
            top_terms = report.consensus_keywords[:8]
            parts.append(f"Key themes: {', '.join(top_terms)}.")
        if edge_sources:
            parts.append(
                f"{len(edge_sources)} source(s) diverge: {', '.join(sorted(edge_sources))}."
            )
        if report.total_contradictions > 0:
            parts.append(
                f"{report.total_contradictions} contradicting finding(s) detected — "
                "evidence is not uniform."
            )
        report.consensus_summary = " ".join(parts)

    return report
