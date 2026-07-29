"""Phase 6 holdout D10: do not conflate approvals with guidelines."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.claim_pipeline import run_claim_pipeline  # noqa: E402
from evals.assertions import approvals_not_called_guidelines  # noqa: E402


def test_contrastive_approval_or_guideline_question_is_not_conflation():
    brief = (
        "## Sub-questions\n"
        "- When did the FDA approve empagliflozin for HFrEF, and is that an "
        "approval or a guideline: The FDA approved empagliflozin in 2022.\n"
    )
    assert approvals_not_called_guidelines(brief, defect_id="D10").passed


def test_true_conflation_still_fails():
    brief = (
        "## Bottom Line\n"
        "- Follow European guidelines for lecanemab approval eligibility.\n"
    )
    assert not approvals_not_called_guidelines(brief, defect_id="D10").passed


def test_hold007_style_brief_passes_d10():
    papers = [
        SimpleNamespace(
            source_name="pubmed",
            title="FDA approval of empagliflozin for HFrEF in 2022",
            year=2022,
            summary=(
                "The FDA approved empagliflozin to reduce cardiovascular death "
                "and heart failure hospitalisation in adults with HFrEF in 2022. "
                "Society guidelines separately advise on implementation."
            ),
            study_type="unknown",
        ),
        SimpleNamespace(
            source_name="dailymed",
            title="Empagliflozin label — HFrEF indication",
            year=2023,
            summary=(
                "US labelling includes indication to reduce risk of cardiovascular "
                "death and hospitalisation for heart failure in adults with HFrEF."
            ),
            study_type="unknown",
        ),
        SimpleNamespace(
            source_name="openalex",
            title="Guideline versus label distinction for SGLT2 inhibitors",
            year=2023,
            summary=(
                "Authors distinguish FDA approval language from advisory "
                "heart-failure guidelines."
            ),
            study_type="unknown",
        ),
    ]
    out = run_claim_pipeline(
        papers,
        query=(
            "When did the FDA approve empagliflozin for HFrEF, and is that an "
            "approval or a guideline?"
        ),
    )
    result = approvals_not_called_guidelines(out["brief"], defect_id="D10")
    assert result.passed, result.detail
