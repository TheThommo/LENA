"""
Supplement verification routes — credibility checks against FDA, DSLD, PubMed.

Exposes the trust-score engine to the frontend so users can verify any
supplement before purchasing or consuming it.
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.logging import get_logger
from app.services.supplement_verifier import verify_supplement

logger = get_logger("lena.supplements")

router = APIRouter(prefix="/supplements", tags=["supplements"])


class VerificationResponse(BaseModel):
    """Structured verification result returned to the frontend."""
    supplement_name: str
    brand: Optional[str] = None
    trust_score: int
    trust_level: str
    trust_breakdown: dict
    dsld: dict
    fda_recalls: dict
    adverse_events: dict
    clinical_evidence: dict
    verification_time_ms: float


@router.get("/verify", response_model=VerificationResponse)
async def verify(
    name: str = Query(..., min_length=1, max_length=200, description="Supplement name (e.g. 'Vitamin D', 'ashwagandha')"),
    brand: Optional[str] = Query(None, max_length=200, description="Brand name to narrow search"),
):
    """
    Verify a supplement across multiple FDA and research databases.

    Returns a trust score (0-100) with breakdown:
    - DSLD registration (NIH label database)
    - FDA recall history (enforcement actions)
    - Adverse event reports (CAERS)
    - Clinical evidence (PubMed + Cochrane)

    Trust levels:
    - verified (85-100): Strong multi-source backing
    - caution (60-84): Mixed signals
    - warning (30-59): Significant red flags
    - alert (0-29): High risk or no data
    """
    result = await verify_supplement(name=name, brand=brand, include_clinical=True)
    return VerificationResponse(**result.to_dict())
