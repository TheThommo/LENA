"""
Affiliation & co-branding API.

Public validation for partner codes (?ref=DEMO-UNI) used at signup and checkout.
Falls back to in-memory demo data when Supabase tables are not migrated yet.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.db.supabase import get_supabase_admin_client

logger = get_logger("lena.affiliation")

router = APIRouter(prefix="/affiliation", tags=["affiliation"])

PartnerSegment = Literal[
    "university",
    "hospital",
    "clinic",
    "pharmacy",
    "doctors_room",
    "corporate",
    "individual",
]

BenefitType = Literal["percent_discount", "free_months", "trial_extension", "custom"]


class PartnerBrandingResponse(BaseModel):
    code: str
    partner_id: str
    partner_name: str
    partner_slug: str
    segment: PartnerSegment
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    benefit_type: BenefitType
    benefit_value: float
    benefit_description: Optional[str] = None
    co_brand_duration_days: Optional[int] = None
    label: Optional[str] = None


# In-memory fallback when migration 011 not applied yet
_DEMO_CODES: dict[str, PartnerBrandingResponse] = {
    "DEMO-UNI": PartnerBrandingResponse(
        code="DEMO-UNI",
        partner_id="demo-university",
        partner_name="Demo University",
        partner_slug="demo-university",
        segment="university",
        logo_url=None,
        website_url="https://example.edu",
        benefit_type="free_months",
        benefit_value=1,
        benefit_description="1 month free on annual subscription",
        co_brand_duration_days=365,
        label="Student access",
    ),
    "DEMO-HOSP": PartnerBrandingResponse(
        code="DEMO-HOSP",
        partner_id="demo-hospital",
        partner_name="Demo Health System",
        partner_slug="demo-hospital",
        segment="hospital",
        logo_url=None,
        website_url="https://example.health",
        benefit_type="percent_discount",
        benefit_value=20,
        benefit_description="20% off Pro subscription",
        co_brand_duration_days=365,
        label="Clinical staff",
    ),
}


def _normalize_code(code: str) -> str:
    return code.strip().upper().replace(" ", "-")


def _validate_from_db(code: str) -> Optional[PartnerBrandingResponse]:
    try:
        client = get_supabase_admin_client()
        res = (
            client.table("affiliation_codes")
            .select(
                "code, benefit_type, benefit_value, benefit_description, "
                "co_brand_duration_days, label, valid_until, is_active, "
                "partner:partner_organizations(id, slug, name, segment, logo_url, website_url, is_active)"
            )
            .eq("code", code)
            .limit(1)
            .execute()
        )
        if not res.data:
            return None
        row = res.data[0]
        if not row.get("is_active"):
            return None
        valid_until = row.get("valid_until")
        if valid_until:
            until = datetime.fromisoformat(valid_until.replace("Z", "+00:00"))
            if until < datetime.now(timezone.utc):
                return None
        partner = row.get("partner") or {}
        if isinstance(partner, list):
            partner = partner[0] if partner else {}
        if not partner.get("is_active", True):
            return None
        return PartnerBrandingResponse(
            code=row["code"],
            partner_id=str(partner.get("id", "")),
            partner_name=partner.get("name", "Partner"),
            partner_slug=partner.get("slug", ""),
            segment=partner.get("segment", "corporate"),
            logo_url=partner.get("logo_url"),
            website_url=partner.get("website_url"),
            benefit_type=row.get("benefit_type", "custom"),
            benefit_value=float(row.get("benefit_value") or 0),
            benefit_description=row.get("benefit_description"),
            co_brand_duration_days=row.get("co_brand_duration_days"),
            label=row.get("label"),
        )
    except Exception as exc:
        logger.warning("affiliation_db_lookup_failed", extra={"error": str(exc), "code": code})
        return None


def _resolve_code(code: str) -> PartnerBrandingResponse:
    normalized = _normalize_code(code)
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")

    from_db = _validate_from_db(normalized)
    if from_db:
        return from_db

    demo = _DEMO_CODES.get(normalized)
    if demo:
        return demo

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Affiliation code not found or expired")


@router.get("/validate", response_model=PartnerBrandingResponse)
async def validate_affiliation_code(
    code: str = Query(..., min_length=3, max_length=32, description="Affiliation code e.g. DEMO-UNI"),
):
    """
    Validate a partner affiliation code and return co-branding + benefit metadata.

    Used when users land with ?ref=CODE or enter a code at signup.
    """
    return _resolve_code(code)


class ApplyAffiliationBody(BaseModel):
    code: str = Field(..., min_length=3, max_length=32)


@router.post("/apply")
async def apply_affiliation_for_user(
    body: ApplyAffiliationBody,
    # Auth optional for now — wired when billing entitlements land
):
    """
    Placeholder: persist user_affiliations after signup/checkout.

    Returns validated partner branding; full persistence requires migration 011 + auth.
    """
    normalized = _normalize_code(body.code)
    branding = _resolve_code(normalized)
    return {
        "applied": True,
        "branding": branding,
        "message": "Affiliation recorded for co-branding. Billing benefits apply at checkout.",
    }
