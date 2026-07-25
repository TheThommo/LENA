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
async def test_g01_e1_e2_e3_floor_asserts():
    """G01: E1 dedup, E2 lead, E3 no verbatim dump all pass floor asserts."""
    from evals.runner import run_suite

    results = await run_suite("golden", force_offline_rubric=True, case_filter="G01")
    assert results, "G01 missing"
    for r in results:
        by_name = {a.name: a for a in r.assertion_results}
        assert by_name["dedup_correct"].passed, by_name["dedup_correct"].detail
        assert by_name["distinct_source_count_accurate"].passed, by_name[
            "distinct_source_count_accurate"
        ].detail
        assert by_name["relevance_lead"].passed, by_name["relevance_lead"].detail
        assert by_name["no_verbatim_dump"].passed, by_name["no_verbatim_dump"].detail


@pytest.mark.asyncio
async def test_holdout_not_imported_by_default():
    """Guard: holdout runner refuses without --allow-holdout."""
    from evals.runner import main

    rc = main(["--suite", "holdout"])
    assert rc == 2
