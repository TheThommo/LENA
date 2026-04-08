"""
PULSE Engine (Published Literature Source Evaluation)

The cross-reference validation engine. LENA queries multiple sources,
compares results, and flags when one source diverges from consensus.

- 4+ consistent results = "Validated"
- A divergent result = flagged as "Edge Case"
- Fewer than 3 sources agreeing = "Insufficient Validation"
"""

import re
import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

logger = logging.getLogger("lena.pulse")


class ValidationStatus(str, Enum):
    VALIDATED = "validated"
    EDGE_CASE = "edge_case"
    INSUFFICIENT = "insufficient_validation"
    PENDING = "pending"


# Common medical/scientific stop words to filter out during keyword extraction
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

# Minimum word length for keywords
MIN_KEYWORD_LENGTH = 3


@dataclass
class SourceResult:
    """A single result from one data source."""
    source_name: str
    title: str
    summary: str
    url: Optional[str] = None
    doi: Optional[str] = None
    year: Optional[int] = None
    relevance_score: float = 0.0
    keywords: list[str] = field(default_factory=list)
    is_retracted: bool = False


@dataclass
class SourceAgreement:
    """Tracks how much a source's results overlap with the consensus."""
    source_name: str
    result_count: int
    keyword_overlap_score: float  # 0.0 to 1.0
    shared_keywords: list[str] = field(default_factory=list)
    unique_keywords: list[str] = field(default_factory=list)
    is_consensus: bool = True


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

    @property
    def confidence_ratio(self) -> float:
        if self.source_count == 0:
            return 0.0

        # Base confidence = agreement_count / source_count
        base_confidence = self.agreement_count / self.source_count

        # RULE 3: Conflicting evidence (edge cases exist) lowers confidence
        if self.edge_cases:
            # Penalty factor based on edge case count
            penalty = len(self.edge_cases) / max(1, len(self.validated_results) + len(self.edge_cases))
            base_confidence = base_confidence * (1.0 - (penalty * 0.25))

        return base_confidence

    def to_dict(self) -> dict:
        """Serialise the report to a dictionary for API responses."""
        return {
            "query": self.query,
            "status": self.status.value,
            "confidence_ratio": round(self.confidence_ratio, 2),
            "source_count": self.source_count,
            "agreement_count": self.agreement_count,
            "consensus_keywords": self.consensus_keywords[:20],
            "validated_count": len(self.validated_results),
            "edge_case_count": len(self.edge_cases),
            "consensus_summary": self.consensus_summary,
            "source_agreements": [
                {
                    "source": sa.source_name,
                    "result_count": sa.result_count,
                    "overlap_score": round(sa.keyword_overlap_score, 2),
                    "shared_keywords": sa.shared_keywords[:10],
                    "unique_keywords": sa.unique_keywords[:10],
                    "is_consensus": sa.is_consensus,
                }
                for sa in self.source_agreements
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
                }
                for r in self.edge_cases
            ],
        }


def extract_keywords(text: str, top_n: int = 15) -> list[str]:
    """
    Extract meaningful keywords from text using frequency analysis.

    Strips stop words, filters short tokens, and returns the most
    frequent terms as a simple keyword set.
    """
    if not text:
        return []

    # Lowercase and split on non-alpha characters
    words = re.findall(r"[a-z]{3,}", text.lower())

    # Filter stop words and very short words
    filtered = [w for w in words if w not in STOP_WORDS and len(w) >= MIN_KEYWORD_LENGTH]

    # Count and return top N
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
    Cross-reference results from multiple sources using keyword overlap.

    How it works:
    1. Extract keywords from each result's title + summary
    2. Build a per-source keyword profile (union of all result keywords)
    3. Build a consensus keyword set (keywords appearing in 3+ sources)
    4. Score each source against the consensus
    5. Sources below the edge_case_threshold are flagged as edge cases

    Args:
        query: The original search query
        results_by_source: Dict mapping source name to list of SourceResults
        edge_case_threshold: Overlap score below which a source is an edge case

    Returns:
        PULSEReport with validated results, edge cases, and agreement data
    """
    report = PULSEReport(query=query)
    report.source_count = len(results_by_source)

    if report.source_count == 0:
        report.status = ValidationStatus.PENDING
        return report

    # Step 1: Extract keywords for every result and build source profiles
    source_keyword_profiles: dict[str, set[str]] = {}

    for source_name, results in results_by_source.items():
        source_keywords: set[str] = set()
        for r in results:
            text = f"{r.title} {r.summary}"
            r.keywords = extract_keywords(text, top_n=15)
            source_keywords.update(r.keywords)
            r.source_name = source_name
        source_keyword_profiles[source_name] = source_keywords

    # Step 2: Build consensus keywords (appear in 3+ sources, or majority)
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

    # Step 3: Score each source against the consensus
    for source_name, source_kws in source_keyword_profiles.items():
        overlap_score = _compute_overlap(source_kws, consensus_keywords)
        shared = sorted(source_kws & consensus_keywords)
        unique = sorted(source_kws - consensus_keywords)

        is_consensus = overlap_score >= edge_case_threshold

        agreement = SourceAgreement(
            source_name=source_name,
            result_count=len(results_by_source[source_name]),
            keyword_overlap_score=overlap_score,
            shared_keywords=shared,
            unique_keywords=unique,
            is_consensus=is_consensus,
        )
        report.source_agreements.append(agreement)

    # Step 4: Sort results into validated vs edge cases
    consensus_sources = {sa.source_name for sa in report.source_agreements if sa.is_consensus}
    edge_sources = {sa.source_name for sa in report.source_agreements if not sa.is_consensus}
    report.agreement_count = len(consensus_sources)

    for source_name, results in results_by_source.items():
        # Score individual results by how many of their keywords match consensus
        for r in results:
            # Skip retracted papers entirely
            if r.is_retracted:
                logger.debug(f"Excluding retracted paper: {r.title[:50]}")
                continue

            if consensus_keywords and r.keywords:
                # Calculate base relevance score
                base_score = len(set(r.keywords) & consensus_keywords) / len(consensus_keywords)

                # RULE 1: Single-source cap at 0.60
                if len(results_by_source) == 1:
                    base_score = min(base_score, 0.60)

                # RULE 2: Systematic reviews (Cochrane) weighted 1.25x
                if source_name == "cochrane":
                    base_score = min(base_score * 1.25, 1.0)

                r.relevance_score = base_score
            else:
                r.relevance_score = 0.0

        if source_name in consensus_sources:
            report.validated_results.extend(results)
        else:
            report.edge_cases.extend(results)

    # Sort validated results by relevance score (best first)
    report.validated_results.sort(key=lambda r: r.relevance_score, reverse=True)

    # Step 5: Determine overall validation status
    if report.agreement_count >= 3:
        report.status = ValidationStatus.VALIDATED
    elif report.agreement_count >= 1:
        report.status = ValidationStatus.INSUFFICIENT
    else:
        report.status = ValidationStatus.PENDING

    # Step 6: Build a consensus summary
    if consensus_keywords:
        top_terms = report.consensus_keywords[:10]
        sources_agreeing = [sa.source_name for sa in report.source_agreements if sa.is_consensus]
        report.consensus_summary = (
            f"{len(sources_agreeing)} of {report.source_count} sources agree on "
            f"key themes: {', '.join(top_terms)}."
        )
        if edge_sources:
            report.consensus_summary += (
                f" {len(edge_sources)} source(s) diverge and are flagged as edge cases: "
                f"{', '.join(sorted(edge_sources))}."
            )

    return report
