"""Phase 6 holdout D6: temporal supersession with revise-versus / emphasise language."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.claim_pipeline import (  # noqa: E402
    ReconcileClass,
    run_claim_pipeline,
)
from evals.assertions import divergence_present  # noqa: E402


def test_hold004_style_booster_supersession_surfaces():
    papers = [
        SimpleNamespace(
            source_name="cdc",
            title="2022 interim booster snapshot",
            year=2022,
            summary=(
                "2022 interim CDC materials emphasised broad booster uptake "
                "for adults after primary series."
            ),
            study_type="guideline",
        ),
        SimpleNamespace(
            source_name="pubmed",
            title="2024 schedule superseding 2022 booster framing",
            year=2024,
            summary=(
                "Updated 2024 schedules revise booster timing and risk-based "
                "emphasis versus 2022 interim broad booster messaging. Older "
                "2022 snapshots are superseded for current practice."
            ),
            study_type="unknown",
        ),
    ]
    out = run_claim_pipeline(
        papers,
        query="What is the current recommendation on routine boosters for healthy young adults?",
    )
    edges = out.get("edge_cases") or []
    assert any(
        e.get("classification") == ReconcileClass.TEMPORAL_SUPERSESSION.value
        for e in edges
    ), edges
    assert divergence_present(edges, topic="booster", defect_id="D6").passed
