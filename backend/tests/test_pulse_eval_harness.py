"""
Pytest entry for the GOLDEN suite only (Phase 2 answer-quality eval).

Holdout is intentionally not collected here — Phase 6 runs it via:
  python -m evals.runner --suite holdout --allow-holdout
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.mark.asyncio
async def test_golden_suite_runs_and_is_strict():
    """Baseline: current pipeline must not fully pass the answer-quality battery."""
    from evals.runner import format_report, run_suite

    results = await run_suite("golden", force_offline_rubric=True)
    report = format_report(results, "golden")
    print("\n" + report)
    assert results, "golden suite produced no cases"
    # 16 cases; some expand to multiple personas
    assert len(results) >= 16
    # Phase 2 checkpoint: battery must catch current failures (not all-green)
    assert not all(r.passed for r in results), "eval is too weak if current code fully passes"


@pytest.mark.asyncio
async def test_g01_fails_rubric_dedup_and_relevance_lead():
    """Known production failure signature for the US/EU lecanemab case."""
    from evals.runner import run_suite

    results = await run_suite("golden", force_offline_rubric=True, case_filter="G01")
    assert results, "G01 missing"
    for r in results:
        assert r.rubric and not r.rubric.passed, f"{r.case_id} rubric should fail"
        dedup = [a for a in r.assertion_results if a.name == "dedup_correct"]
        assert dedup and not dedup[0].passed, f"{r.case_id} dedup_correct should fail"
        lead = [a for a in r.assertion_results if a.name == "relevance_lead"]
        assert lead and not lead[0].passed, f"{r.case_id} relevance_lead should fail"


@pytest.mark.asyncio
async def test_holdout_not_imported_by_default():
    """Guard: holdout runner refuses without --allow-holdout."""
    from evals.runner import main

    rc = main(["--suite", "holdout"])
    assert rc == 2
