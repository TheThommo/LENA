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
async def test_golden_suite_runs_and_reports():
    from evals.runner import format_report, run_suite

    results = await run_suite("golden")
    report = format_report(results, "golden")
    print("\n" + report)
    assert results, "golden suite produced no cases"
    # Phase 2 baseline expectation: GOLD-001 must fail key assertions
    g1 = next(r for r in results if r.case_id == "GOLD-001")
    failed_names = {a.name for a in g1.failed}
    assert "qualifier_preserved" in failed_names or "forbidden_unqualified" in failed_names, (
        "GOLD-001 must fail ApoE4 qualifier assertion against unfixed code"
    )
    assert "divergence_absent" in failed_names, (
        "GOLD-001 must fail CDC divergence_absent against unfixed code"
    )


@pytest.mark.asyncio
async def test_holdout_not_imported_by_default():
    """Guard: holdout runner refuses without --allow-holdout."""
    from evals.runner import main

    rc = main(["--suite", "holdout"])
    assert rc == 2
