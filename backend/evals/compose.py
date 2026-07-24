"""
Eval-facing adapters over app.core.claim_pipeline.

Kept thin so golden/holdout exercise the same composition path as production.
"""

from __future__ import annotations

from typing import Any, Optional


def _papers_from_pulse(pulse) -> list[Any]:
    return list(pulse.validated_results) + list(pulse.edge_cases)


def compose_brief_from_claims(case: dict[str, Any], pulse) -> Optional[str]:
    from app.core.claim_pipeline import run_claim_pipeline

    papers = _papers_from_pulse(pulse)
    if not papers:
        return None
    result = run_claim_pipeline(papers, query=case.get("query") or pulse.query)
    return result.get("brief") or None


def claims_for_eval(pulse) -> Optional[list[dict[str, Any]]]:
    from app.core.claim_pipeline import bind_claims_from_pulse_results

    papers = _papers_from_pulse(pulse)
    claims = bind_claims_from_pulse_results(papers)
    if not claims:
        # Explicit empty list still means pipeline is active (D11 should fail)
        return []
    return [c.to_dict() for c in claims]


def divergence_flags_for_eval(pulse) -> Optional[list[dict[str, Any]]]:
    from app.core.claim_pipeline import (
        bind_claims_from_pulse_results,
        reconcile_claims,
        surfaceable_edge_cases,
    )

    # Prefer flags attached by pulse engine when present
    attached = getattr(pulse, "reconciliation_edge_cases", None)
    if attached is not None:
        return list(attached)

    papers = _papers_from_pulse(pulse)
    groups = reconcile_claims(bind_claims_from_pulse_results(papers))
    return surfaceable_edge_cases(groups)
