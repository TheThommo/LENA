"""
Eval runner — executes golden/holdout cases against current PULSE + brief path.

Holdout must only be invoked explicitly (Phase 6). Golden is for Phase 2–5.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from evals.assertions import AssertionResult, run_assertion

EVALS_ROOT = Path(__file__).resolve().parent
GOLDEN_DIR = EVALS_ROOT / "golden"
HOLDOUT_DIR = EVALS_ROOT / "holdout"


@dataclass
class CaseResult:
    case_id: str
    passed: bool
    assertion_results: list[AssertionResult] = field(default_factory=list)
    confidence: float = 0.0
    status: str = ""
    notes: str = ""

    @property
    def failed(self) -> list[AssertionResult]:
        return [a for a in self.assertion_results if not a.passed]


def load_cases(suite: str) -> list[dict[str, Any]]:
    directory = GOLDEN_DIR if suite == "golden" else HOLDOUT_DIR
    cases = []
    for path in sorted(directory.glob("*.json")):
        with path.open() as f:
            data = json.load(f)
        data["_path"] = str(path)
        cases.append(data)
    return cases


def _sources_to_results(raw: dict[str, list[dict]]) -> dict[str, list]:
    from app.core.pulse_engine import SourceResult

    out: dict[str, list] = {}
    for source_name, items in raw.items():
        out[source_name] = [
            SourceResult(
                source_name=source_name,
                title=item.get("title") or "",
                summary=item.get("summary") or item.get("abstract") or "",
                url=item.get("url") or "",
                doi=item.get("doi"),
                year=item.get("year"),
                authors=list(item.get("authors") or []),
            )
            for item in items
        ]
    return out


def _diverging_sources(pulse) -> list[str]:
    names = []
    for sa in pulse.source_agreements:
        if not sa.is_consensus:
            names.append(sa.source_name)
    # Also parse consensus_summary "diverge:" clause
    summary = pulse.consensus_summary or ""
    if "diverge" in summary.lower():
        # keep source_agreements as canonical
        pass
    return names


def _compose_brief(case: dict[str, Any], pulse) -> str:
    """
    Brief under test.

    Phase 2 (pre-fix): prefer recorded production brief when present so
    synthesis defects are measurable offline without an LLM key. Once the
    claim-bound composer exists, it takes precedence when available.
    """
    # Prefer new pipeline composer when registered
    try:
        from evals.compose import compose_brief_from_claims

        composed = compose_brief_from_claims(case, pulse)
        if composed:
            return composed
    except Exception:
        pass

    if case.get("recorded_brief"):
        return case["recorded_brief"]

    # Fallback: mirror current production theme-line behaviour
    parts = []
    parts.append(f"Direct answer for: {case.get('query', pulse.query)}")
    parts.append("\n## Key Findings\n")
    for r in pulse.validated_results[:5]:
        snippet = (r.summary or "")[:240]
        parts.append(f"- ({r.source_name}) {r.title}: {snippet}")
    if pulse.consensus_keywords:
        parts.append(
            f"\nKey themes: {', '.join(pulse.consensus_keywords[:8])}."
        )
    parts.append("\n## Bottom Line\n")
    parts.append(f"- See consensus: {pulse.consensus_summary}")
    return "\n".join(parts)


def _extract_claims_for_ctx(pulse) -> list[dict[str, Any]]:
    """
    Provenance-shaped claims. Uses new claim pipeline when present;
    otherwise maps raw pulse claims (no ids/spans) so D11 fails at baseline.
    """
    try:
        from evals.compose import claims_for_eval

        claims = claims_for_eval(pulse)
        if claims is not None:
            return claims
    except Exception:
        pass

    claims: list[dict[str, Any]] = []
    for r in list(pulse.validated_results) + list(pulse.edge_cases):
        for c in r.claims or []:
            claims.append(
                {
                    "claim_id": None,
                    "source_ids": [r.source_name] if r.source_name else [],
                    "span": None,
                    "text": c,
                }
            )
    return claims


def _divergence_flags(pulse) -> list[dict[str, Any]]:
    try:
        from evals.compose import divergence_flags_for_eval

        flags = divergence_flags_for_eval(pulse)
        if flags is not None:
            return flags
    except Exception:
        pass
    # Baseline: only keyword-edge sources — no real contradiction/supersession objects
    flags = []
    for sa in pulse.source_agreements:
        if not sa.is_consensus:
            flags.append(
                {
                    "source": sa.source_name,
                    "reason": "keyword_edge",
                    "classification": "ABSENCE",
                    "topic": "",
                }
            )
    return flags


async def run_case(case: dict[str, Any]) -> CaseResult:
    from app.core.pulse_engine import run_pulse_validation

    results_by_source = _sources_to_results(case["sources"])
    # Allow cases to declare sources_attempted > returned (coverage math)
    pulse = await run_pulse_validation(
        query=case["query"],
        results_by_source=results_by_source,
        subject_terms=case.get("subject_terms"),
    )
    attempted = case.get("sources_attempted")
    if attempted:
        pulse._sources_attempted = int(attempted)
        pulse.refresh_status()

    conf = pulse.confidence_ratio
    status = pulse.status.value if hasattr(pulse.status, "value") else str(pulse.status)
    brief = _compose_brief(case, pulse)
    claims = _extract_claims_for_ctx(pulse)
    diverging = _diverging_sources(pulse)
    ranked_titles = [r.title for r in pulse.validated_results]
    source_names = [r.source_name for r in pulse.validated_results]
    # Include all returned sources for routing checks
    source_names = list(dict.fromkeys(list(results_by_source.keys()) + source_names))

    # Optional routing simulation hook (Phase 3 D8 may populate ranked by class)
    if case.get("force_ranked_sources"):
        source_names = case["force_ranked_sources"]
    if case.get("force_ranked_titles"):
        ranked_titles = case["force_ranked_titles"]

    ctx = {
        "brief": brief,
        "claims": claims,
        "confidence": conf,
        "status": status,
        "diverging_sources": diverging,
        "divergence_flags": _divergence_flags(pulse),
        "source_names": source_names,
        "themes": list(pulse.consensus_keywords or []),
        "ranked_titles": ranked_titles,
        "pulse": pulse,
        "case": case,
    }

    results: list[AssertionResult] = []
    for spec in case.get("assertions", []):
        results.append(run_assertion(spec, ctx))

    passed = all(r.passed for r in results) if results else False
    return CaseResult(
        case_id=case["id"],
        passed=passed,
        assertion_results=results,
        confidence=conf,
        status=status,
    )


async def run_suite(suite: str) -> list[CaseResult]:
    if suite == "holdout":
        # Soft guard — caller must pass --allow-holdout
        pass
    cases = load_cases(suite)
    out: list[CaseResult] = []
    for case in cases:
        out.append(await run_case(case))
    return out


def format_report(results: list[CaseResult], suite: str) -> str:
    total = len(results)
    n_pass = sum(1 for r in results if r.passed)
    lines = [f"SUITE {suite.upper()}: {n_pass}/{total} pass", ""]
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        lines.append(f"  [{mark}] {r.case_id}  confidence={r.confidence:.2f} status={r.status}")
        for a in r.assertion_results:
            am = "ok" if a.passed else "FAIL"
            defect = f" ({a.defect_id})" if a.defect_id else ""
            lines.append(f"      [{am}] {a.name}{defect}: {a.detail}")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="PULSE eval harness")
    parser.add_argument("--suite", choices=["golden", "holdout"], default="golden")
    parser.add_argument(
        "--allow-holdout",
        action="store_true",
        help="Required to run the holdout suite (Phase 6 only).",
    )
    parser.add_argument("--case", help="Run a single case id")
    args = parser.parse_args(argv)

    if args.suite == "holdout" and not args.allow_holdout:
        print(
            "REFUSED: holdout suite is sealed until Phase 6. "
            "Re-run with --allow-holdout.",
            file=sys.stderr,
        )
        return 2

    # Ensure backend root on path
    backend_root = EVALS_ROOT.parent
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    if str(EVALS_ROOT.parent) not in sys.path:
        sys.path.insert(0, str(EVALS_ROOT.parent))
    # evals package lives under backend/
    sys.path.insert(0, str(backend_root))

    async def _go():
        results = await run_suite(args.suite)
        if args.case:
            results = [r for r in results if r.case_id == args.case]
        print(format_report(results, args.suite))
        return 0 if results and all(r.passed for r in results) else 1

    return asyncio.run(_go())


if __name__ == "__main__":
    raise SystemExit(main())
