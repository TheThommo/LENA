"""
Pytest entry for the GOLDEN suite only.

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
async def test_golden_suite_runs():
    from evals.runner import format_report, run_suite

    results = await run_suite("golden")
    report = format_report(results, "golden")
    print("\n" + report)
    assert results, "golden suite produced no cases"
    assert len(results) >= 12


@pytest.mark.asyncio
async def test_holdout_not_imported_by_default():
    """Guard: holdout runner refuses without --allow-holdout."""
    from evals.runner import main

    rc = main(["--suite", "holdout"])
    assert rc == 2


@pytest.mark.asyncio
async def test_d1_qualifier_assertions_pass():
    """D1: dosage/genotype qualifiers preserved product-wide (not query-specific)."""
    from evals.runner import run_suite

    results = await run_suite("golden")
    by_id = {r.case_id: r for r in results}
    for case_id in ("GOLD-001", "GOLD-002"):
        case = by_id[case_id]
        d1 = [
            a
            for a in case.assertion_results
            if a.defect_id == "D1" or a.name in ("qualifier_preserved", "forbidden_unqualified")
        ]
        assert d1, f"{case_id} missing D1 assertions"
        failed = [a for a in d1 if not a.passed]
        assert not failed, f"{case_id} D1 failures: {[a.detail for a in failed]}"
