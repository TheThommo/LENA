"""
Eval runner — answer-quality rubric + mechanical floor.

Holdout must only be invoked explicitly (Phase 6). Golden is for Phase 2–5.
A case PASSES only if rubric gates pass AND every mechanical floor assertion passes.
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
from evals.rubric import RubricResult, grade_rubric

EVALS_ROOT = Path(__file__).resolve().parent
GOLDEN_DIR = EVALS_ROOT / "golden"
HOLDOUT_DIR = EVALS_ROOT / "holdout"


@dataclass
class CaseResult:
    case_id: str
    passed: bool
    assertion_results: list[AssertionResult] = field(default_factory=list)
    rubric: Optional[RubricResult] = None
    confidence: float = 0.0
    status: str = ""
    persona: str = ""
    brief: str = ""
    notes: str = ""
    stale: bool = False

    @property
    def failed(self) -> list[AssertionResult]:
        return [a for a in self.assertion_results if not a.passed]


def load_cases(suite: str) -> list[dict[str, Any]]:
    directory = GOLDEN_DIR if suite == "golden" else HOLDOUT_DIR
    cases = []
    for path in sorted(directory.glob("*.json")):
        # Ignore legacy archive directory files (not in this glob)
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
                pmid=item.get("pmid"),
                year=item.get("year"),
                authors=list(item.get("authors") or []),
            )
            for item in items
        ]
    return out


def _papers_list(pulse) -> list[Any]:
    return list(pulse.validated_results) + list(pulse.edge_cases)


def _diverging_sources(pulse) -> list[str]:
    return [sa.source_name for sa in pulse.source_agreements if not sa.is_consensus]


def _compose_brief(case: dict[str, Any], pulse) -> str:
    """
    Prefer live claim-pipeline composition (production path).
    recorded_brief only when explicitly opted in for offline fixture debugging.
    """
    try:
        from evals.compose import compose_brief_from_claims

        composed = compose_brief_from_claims(case, pulse)
        if composed:
            return composed
    except Exception:
        pass

    if case.get("use_recorded_brief") and case.get("recorded_brief"):
        return case["recorded_brief"]

    # Guardrail cases: claim pipeline may still emit an evidence brief — leave as-is
    # for the rubric to fail. Optional synthetic redirect not injected here.
    parts = []
    parts.append(f"Direct answer for: {case.get('query', pulse.query)}")
    parts.append("\n## Key Findings\n")
    for r in pulse.validated_results[:5]:
        snippet = (r.summary or "")[:240]
        parts.append(f"- ({r.source_name}) {r.title}: {snippet}")
    if pulse.consensus_keywords:
        parts.append(f"\nKey themes: {', '.join(pulse.consensus_keywords[:8])}.")
    parts.append("\n## Bottom Line\n")
    parts.append(f"- See consensus: {pulse.consensus_summary}")
    return "\n".join(parts)


def _extract_claims_for_ctx(pulse) -> list[dict[str, Any]]:
    try:
        from evals.compose import claims_for_eval

        claims = claims_for_eval(pulse)
        if claims is not None:
            return claims
    except Exception:
        pass

    claims: list[dict[str, Any]] = []
    for r in _papers_list(pulse):
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


def _expand_persona_cases(case: dict[str, Any]) -> list[dict[str, Any]]:
    personas = case.get("personas") or [case.get("persona") or "general"]
    out = []
    for p in personas:
        cloned = dict(case)
        cloned["persona"] = p
        cloned["id"] = f"{case['id']}@{p}" if len(personas) > 1 else case["id"]
        out.append(cloned)
    return out


async def run_case(case: dict[str, Any], *, force_offline_rubric: bool = False) -> CaseResult:
    from app.core.pulse_engine import run_pulse_validation
    from app.services.search_orchestrator import plan_sources_for_query, rank_results_for_query

    results_by_source = _sources_to_results(case.get("sources") or {})
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
    papers = _papers_list(pulse)

    ranked_papers = rank_results_for_query(
        case["query"],
        list(pulse.validated_results),
        subject_terms=case.get("subject_terms"),
    )
    ranked_titles = [r.title for r in ranked_papers]
    ranked_source_names = [r.source_name for r in ranked_papers]
    planned = plan_sources_for_query(case["query"], list(results_by_source.keys()))
    source_names = list(dict.fromkeys(planned + list(results_by_source.keys())))

    ctx = {
        "brief": brief,
        "claims": claims,
        "confidence": conf,
        "status": status,
        "diverging_sources": _diverging_sources(pulse),
        "divergence_flags": _divergence_flags(pulse),
        "source_names": source_names,
        "themes": list(pulse.consensus_keywords or []),
        "ranked_titles": ranked_titles,
        "ranked_source_names": ranked_source_names,
        "pulse": pulse,
        "papers": papers,
        "case": case,
    }

    assertion_results: list[AssertionResult] = []
    for spec in case.get("assertions", []):
        assertion_results.append(run_assertion(spec, ctx))

    stale = any(a.name == "key_not_stale" and not a.passed for a in assertion_results)
    floor_pass = all(a.passed for a in assertion_results) if assertion_results else False

    answer_key = case.get("answer_key") or {}
    rubric = await grade_rubric(
        query=case["query"],
        persona=case.get("persona") or "general",
        answer_key=answer_key,
        brief=brief,
        force_offline=force_offline_rubric,
    )

    passed = (not stale) and floor_pass and rubric.passed
    return CaseResult(
        case_id=case["id"],
        passed=passed,
        assertion_results=assertion_results,
        rubric=rubric,
        confidence=conf,
        status=status,
        persona=case.get("persona") or "",
        brief=brief,
        stale=stale,
        notes="STALE key" if stale else "",
    )


async def run_suite(
    suite: str,
    *,
    force_offline_rubric: bool = False,
    case_filter: Optional[str] = None,
) -> list[CaseResult]:
    raw_cases = load_cases(suite)
    expanded: list[dict[str, Any]] = []
    for c in raw_cases:
        expanded.extend(_expand_persona_cases(c))
    if case_filter:
        expanded = [
            c
            for c in expanded
            if c["id"] == case_filter
            or c["id"].startswith(case_filter + "@")
            or c.get("id", "").split("@")[0] == case_filter
        ]
    out: list[CaseResult] = []
    for case in expanded:
        out.append(await run_case(case, force_offline_rubric=force_offline_rubric))
    return out


def format_report(results: list[CaseResult], suite: str) -> str:
    total = len(results)
    n_pass = sum(1 for r in results if r.passed)
    rubric_scores = [r.rubric.overall for r in results if r.rubric]
    avg = sum(rubric_scores) / len(rubric_scores) if rubric_scores else 0.0
    lines = [
        f"SUITE {suite.upper()}: {n_pass}/{total} pass (rubric avg {avg:.1f})",
        "",
    ]
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        if r.stale:
            mark = "STALE"
        rub = r.rubric
        rub_bit = ""
        if rub:
            rub_bit = (
                f" rubric={rub.overall:.0f} mode={rub.mode} "
                f"scores={rub.scores}"
            )
        lines.append(
            f"  [{mark}] {r.case_id} persona={r.persona} "
            f"confidence={r.confidence:.2f} status={r.status}{rub_bit}"
        )
        if rub and rub.detail:
            lines.append(f"      rubric_detail: {rub.detail}")
        for a in r.assertion_results:
            am = "ok" if a.passed else "FAIL"
            defect = f" ({a.defect_id})" if a.defect_id else ""
            lines.append(f"      [{am}] {a.name}{defect}: {a.detail}")
        # Show lead line for debugging relevance
        lead = (r.brief or "").strip().splitlines()[:1]
        if lead:
            lines.append(f"      lead: {lead[0][:160]}")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="PULSE answer-quality eval harness")
    parser.add_argument("--suite", choices=["golden", "holdout"], default="golden")
    parser.add_argument(
        "--allow-holdout",
        action="store_true",
        help="Required to run the holdout suite (Phase 6 only).",
    )
    parser.add_argument("--case", help="Run a single case id (e.g. G01)")
    parser.add_argument(
        "--offline-rubric",
        action="store_true",
        help="Force deterministic offline rubric (also used automatically without OPENAI_API_KEY).",
    )
    parser.add_argument(
        "--json-out",
        help="Write machine-readable results JSON to this path",
    )
    args = parser.parse_args(argv)

    if args.suite == "holdout" and not args.allow_holdout:
        print(
            "REFUSED: holdout suite is sealed until Phase 6. "
            "Re-run with --allow-holdout.",
            file=sys.stderr,
        )
        return 2

    backend_root = EVALS_ROOT.parent
    sys.path.insert(0, str(backend_root))

    async def _go():
        results = await run_suite(
            args.suite,
            force_offline_rubric=args.offline_rubric,
            case_filter=args.case,
        )
        print(format_report(results, args.suite))
        if args.json_out:
            payload = []
            for r in results:
                payload.append(
                    {
                        "case_id": r.case_id,
                        "passed": r.passed,
                        "stale": r.stale,
                        "persona": r.persona,
                        "confidence": r.confidence,
                        "status": r.status,
                        "rubric": r.rubric.to_dict() if r.rubric else None,
                        "assertions": [
                            {
                                "name": a.name,
                                "passed": a.passed,
                                "detail": a.detail,
                                "defect_id": a.defect_id,
                            }
                            for a in r.assertion_results
                        ],
                        "brief": r.brief,
                    }
                )
            Path(args.json_out).write_text(json.dumps(payload, indent=2))
        return 0 if results and all(r.passed for r in results) else 1

    return asyncio.run(_go())


if __name__ == "__main__":
    raise SystemExit(main())
