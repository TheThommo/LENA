"""
Supplement Verifier — multi-source credibility engine.

Orchestrates parallel checks against FDA, DSLD, PubMed and openFDA to
produce a "Supplement Trust Score" plus a structured verification report.

Trust Score formula (0-100):
  +15  DSLD registered — product exists in NIH label database
  +20  No FDA recalls — clean enforcement history
  +15  Low adverse events — few/no CAERS reports relative to market
  +20  Clinical evidence — PubMed/Cochrane papers on the ingredient
  +10  No Class I recalls — no "dangerous" enforcement action
  +20  Market presence — iHerb ratings, review volume, availability

Score buckets:
  85-100  VERIFIED — strong multi-source backing
  60-84   CAUTION — mixed signals, some concerns
  30-59   WARNING — significant red flags
  0-29    ALERT — high risk / no data
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

from app.core.logging import get_logger
from app.services import ods_dsld, openfda, iherb
from app.services.openfda_enforcement import search_recalls, count_adverse_events, FDARecall

logger = get_logger("lena.supplement_verifier")


@dataclass
class SupplementVerification:
    """Structured verification report for a single supplement query."""

    supplement_name: str
    brand: Optional[str] = None

    # Trust score
    trust_score: int = 0
    trust_level: str = "unknown"  # "verified", "caution", "warning", "alert"
    trust_breakdown: dict = field(default_factory=dict)

    # DSLD check
    dsld_registered: bool = False
    dsld_products_found: int = 0
    dsld_sample_products: list = field(default_factory=list)

    # FDA recalls
    recall_count: int = 0
    class_i_recalls: int = 0
    class_ii_recalls: int = 0
    class_iii_recalls: int = 0
    recent_recalls: list = field(default_factory=list)

    # Adverse events
    adverse_event_total: int = 0
    adverse_deaths: int = 0
    adverse_hospitalizations: int = 0
    adverse_serious: int = 0

    # Clinical evidence (from search orchestrator, filled externally)
    clinical_evidence_count: int = 0
    cochrane_reviews: int = 0

    # iHerb marketplace data
    iherb_brand_summary: dict = field(default_factory=dict)
    iherb_products_found: int = 0
    iherb_avg_rating: float = 0.0
    iherb_total_reviews: int = 0

    # Timing
    verification_time_ms: float = 0

    def to_dict(self) -> dict:
        return {
            "supplement_name": self.supplement_name,
            "brand": self.brand,
            "trust_score": self.trust_score,
            "trust_level": self.trust_level,
            "trust_breakdown": self.trust_breakdown,
            "dsld": {
                "registered": self.dsld_registered,
                "products_found": self.dsld_products_found,
                "sample_products": self.dsld_sample_products,
            },
            "fda_recalls": {
                "total": self.recall_count,
                "class_i": self.class_i_recalls,
                "class_ii": self.class_ii_recalls,
                "class_iii": self.class_iii_recalls,
                "recent": self.recent_recalls,
            },
            "adverse_events": {
                "total": self.adverse_event_total,
                "deaths": self.adverse_deaths,
                "hospitalizations": self.adverse_hospitalizations,
                "serious": self.adverse_serious,
            },
            "clinical_evidence": {
                "papers_found": self.clinical_evidence_count,
                "cochrane_reviews": self.cochrane_reviews,
            },
            "market_presence": {
                "iherb_products_found": self.iherb_products_found,
                "iherb_avg_rating": round(self.iherb_avg_rating, 1),
                "iherb_total_reviews": self.iherb_total_reviews,
                "iherb_brand_url": self.iherb_brand_summary.get("brand_url", ""),
                "iherb_top_products": self.iherb_brand_summary.get("top_products", []),
            } if self.iherb_products_found > 0 else None,
            "verification_time_ms": self.verification_time_ms,
        }


def _compute_trust_score(v: SupplementVerification) -> tuple[int, str, dict]:
    """Compute composite trust score from multi-source signals.

    Weights (total 100):
      DSLD registered        +15
      No FDA recalls         +20
      Low adverse events     +15
      Clinical evidence      +20
      No Class I recalls     +10
      Market presence (iHerb)+20
    """
    score = 0
    breakdown: dict = {}

    # 1. DSLD registration (+15)
    if v.dsld_registered:
        dsld_score = 15
        breakdown["dsld_registered"] = {"points": 15, "status": "pass", "detail": f"{v.dsld_products_found} products in NIH database"}
    else:
        dsld_score = 0
        breakdown["dsld_registered"] = {"points": 0, "status": "fail", "detail": "Not found in NIH Dietary Supplement Label Database"}
    score += dsld_score

    # 2. No FDA recalls (+20)
    if v.recall_count == 0:
        recall_score = 20
        breakdown["fda_recalls"] = {"points": 20, "status": "pass", "detail": "No FDA recalls found"}
    elif v.class_i_recalls > 0:
        recall_score = 0
        breakdown["fda_recalls"] = {"points": 0, "status": "critical", "detail": f"{v.class_i_recalls} Class I (dangerous) recall(s)"}
    elif v.class_ii_recalls > 0:
        recall_score = 8
        breakdown["fda_recalls"] = {"points": 8, "status": "warning", "detail": f"{v.class_ii_recalls} Class II recall(s)"}
    else:
        recall_score = 15
        breakdown["fda_recalls"] = {"points": 15, "status": "minor", "detail": f"{v.class_iii_recalls} Class III (low-risk) recall(s) only"}
    score += recall_score

    # 3. Low adverse events (+15)
    if v.adverse_event_total == 0:
        ae_score = 15
        breakdown["adverse_events"] = {"points": 15, "status": "pass", "detail": "No adverse events reported"}
    elif v.adverse_deaths > 0:
        ae_score = 0
        breakdown["adverse_events"] = {"points": 0, "status": "critical", "detail": f"{v.adverse_deaths} death(s) reported in FDA CAERS"}
    elif v.adverse_serious > 5:
        ae_score = 3
        breakdown["adverse_events"] = {"points": 3, "status": "warning", "detail": f"{v.adverse_serious} serious events, {v.adverse_event_total} total reports"}
    elif v.adverse_event_total > 20:
        ae_score = 7
        breakdown["adverse_events"] = {"points": 7, "status": "caution", "detail": f"{v.adverse_event_total} total adverse event reports"}
    else:
        ae_score = 12
        breakdown["adverse_events"] = {"points": 12, "status": "low", "detail": f"{v.adverse_event_total} reports (within normal range)"}
    score += ae_score

    # 4. Clinical evidence (+20)
    if v.cochrane_reviews > 0:
        ev_score = 20
        breakdown["clinical_evidence"] = {"points": 20, "status": "strong", "detail": f"{v.cochrane_reviews} Cochrane review(s) + {v.clinical_evidence_count} papers"}
    elif v.clinical_evidence_count >= 10:
        ev_score = 17
        breakdown["clinical_evidence"] = {"points": 17, "status": "good", "detail": f"{v.clinical_evidence_count} peer-reviewed papers found"}
    elif v.clinical_evidence_count >= 3:
        ev_score = 12
        breakdown["clinical_evidence"] = {"points": 12, "status": "moderate", "detail": f"{v.clinical_evidence_count} papers found"}
    elif v.clinical_evidence_count >= 1:
        ev_score = 6
        breakdown["clinical_evidence"] = {"points": 6, "status": "limited", "detail": f"Only {v.clinical_evidence_count} paper(s) found"}
    else:
        ev_score = 0
        breakdown["clinical_evidence"] = {"points": 0, "status": "none", "detail": "No peer-reviewed clinical evidence found"}
    score += ev_score

    # 5. No Class I recalls bonus (+10)
    if v.class_i_recalls == 0:
        safety_score = 10
        breakdown["safety_record"] = {"points": 10, "status": "pass", "detail": "No dangerous (Class I) recalls on record"}
    else:
        safety_score = 0
        breakdown["safety_record"] = {"points": 0, "status": "critical", "detail": f"{v.class_i_recalls} dangerous recall(s) — FDA determined these posed serious health risk"}
    score += safety_score

    # 6. Market presence via iHerb (+20)
    if v.iherb_products_found > 0 and v.iherb_avg_rating >= 4.0 and v.iherb_total_reviews >= 100:
        market_score = 20
        breakdown["market_presence"] = {
            "points": 20, "status": "strong",
            "detail": f"{v.iherb_products_found} products on iHerb, {v.iherb_avg_rating:.1f} avg rating, {v.iherb_total_reviews:,} reviews",
        }
    elif v.iherb_products_found > 0 and v.iherb_avg_rating >= 3.5:
        market_score = 15
        breakdown["market_presence"] = {
            "points": 15, "status": "good",
            "detail": f"{v.iherb_products_found} products on iHerb, {v.iherb_avg_rating:.1f} avg rating",
        }
    elif v.iherb_products_found > 0:
        market_score = 10
        breakdown["market_presence"] = {
            "points": 10, "status": "limited",
            "detail": f"{v.iherb_products_found} products on iHerb, {v.iherb_total_reviews} reviews",
        }
    else:
        market_score = 0
        breakdown["market_presence"] = {
            "points": 0, "status": "none",
            "detail": "Not found on iHerb marketplace (may still be sold elsewhere)",
        }
    score += market_score

    # Determine trust level
    if score >= 85:
        level = "verified"
    elif score >= 60:
        level = "caution"
    elif score >= 30:
        level = "warning"
    else:
        level = "alert"

    return score, level, breakdown


async def verify_supplement(
    name: str,
    brand: Optional[str] = None,
    include_clinical: bool = True,
) -> SupplementVerification:
    """Run full multi-source verification for a supplement.

    Queries DSLD, openFDA recalls, openFDA adverse events, and optionally
    PubMed/Cochrane for clinical evidence — all in parallel.

    Args:
        name: Supplement name (e.g. "Vitamin D", "ashwagandha", "NattoMax")
        brand: Optional brand name to narrow searches
        include_clinical: Whether to query PubMed/Cochrane for evidence count

    Returns:
        SupplementVerification with trust score and full breakdown
    """
    start = time.time()
    search_term = f"{brand} {name}".strip() if brand else name
    v = SupplementVerification(supplement_name=name, brand=brand)

    # Launch all checks in parallel.
    # DSLD: search both brand+name AND name-only so generic registrations
    # aren't missed when user specifies a brand. Recalls + adverse events
    # also searched by name-only as a fallback (brand may differ from firm).
    tasks = {
        "dsld": ods_dsld.search_dsld(search_term, max_results=10),
        "recalls": search_recalls(search_term, max_results=30),
        "adverse_counts": count_adverse_events(search_term),
    }
    # Parallel name-only searches when brand is specified
    if brand:
        tasks["dsld_generic"] = ods_dsld.search_dsld(name, max_results=5)
        tasks["recalls_generic"] = search_recalls(name, max_results=15)
        tasks["adverse_counts_generic"] = count_adverse_events(name)

    # Clinical evidence: quick PubMed + Cochrane count
    if include_clinical:
        from app.services import pubmed, cochrane
        tasks["pubmed"] = pubmed.search_pubmed(name, max_results=20)
        tasks["cochrane"] = cochrane.search_cochrane(name, max_results=5)

    # iHerb marketplace data for brand verification
    tasks["iherb"] = iherb.get_brand_summary(
        brand=brand or name,
        supplement_name=name if brand else None,
    )

    task_names = list(tasks.keys())
    task_coros = list(tasks.values())
    results = await asyncio.gather(*task_coros, return_exceptions=True)
    task_results = dict(zip(task_names, results))

    # Process DSLD results — merge brand-specific + generic (dedupe by ID)
    dsld_products = task_results.get("dsld")
    dsld_generic = task_results.get("dsld_generic")
    all_dsld = []
    seen_ids: set = set()
    for batch in [dsld_products, dsld_generic]:
        if isinstance(batch, list):
            for p in batch:
                pid = getattr(p, "dsld_id", None) or getattr(p, "title", "")
                if pid not in seen_ids:
                    seen_ids.add(pid)
                    all_dsld.append(p)
        elif isinstance(batch, Exception):
            logger.warning(f"DSLD check failed: {batch}")
    v.dsld_registered = len(all_dsld) > 0
    v.dsld_products_found = len(all_dsld)
    v.dsld_sample_products = [
        {"name": p.title, "brand": p.brand, "url": p.url}
        for p in all_dsld[:5]
    ]

    # Process FDA recalls — merge brand-specific + generic (dedupe by recall_number)
    all_recalls: list[FDARecall] = []
    seen_recall_nums: set = set()
    for key in ["recalls", "recalls_generic"]:
        batch = task_results.get(key)
        if isinstance(batch, list):
            for r in batch:
                if isinstance(r, FDARecall) and r.recall_number not in seen_recall_nums:
                    seen_recall_nums.add(r.recall_number)
                    all_recalls.append(r)
        elif isinstance(batch, Exception):
            logger.warning(f"FDA recall check failed ({key}): {batch}")

    v.recall_count = len(all_recalls)
    for r in all_recalls:
        sev = r.severity
        if sev == "critical":
            v.class_i_recalls += 1
        elif sev == "moderate":
            v.class_ii_recalls += 1
        elif sev == "low":
            v.class_iii_recalls += 1
    v.recent_recalls = [
        {
            "recall_number": r.recall_number,
            "product": r.product_description[:200],
            "reason": r.reason_for_recall[:300],
            "classification": r.classification,
            "severity": r.severity,
            "firm": r.recalling_firm,
            "date": r.recall_date,
            "status": r.status,
        }
        for r in all_recalls[:5]
    ]

    # Process adverse event counts — take max across brand + generic searches
    # (brand-specific may undercount if the brand name differs from what's in CAERS)
    for key in ["adverse_counts", "adverse_counts_generic"]:
        ae_counts = task_results.get(key)
        if isinstance(ae_counts, dict):
            v.adverse_event_total = max(v.adverse_event_total, ae_counts.get("total", 0))
            v.adverse_deaths = max(v.adverse_deaths, ae_counts.get("deaths", 0))
            v.adverse_hospitalizations = max(v.adverse_hospitalizations, ae_counts.get("hospitalizations", 0))
            v.adverse_serious = max(v.adverse_serious, ae_counts.get("serious", 0))
        elif isinstance(ae_counts, Exception):
            logger.warning(f"Adverse event count failed ({key}): {ae_counts}")

    # Process clinical evidence
    pubmed_ids = task_results.get("pubmed")
    if isinstance(pubmed_ids, list):
        v.clinical_evidence_count += len(pubmed_ids)
    elif isinstance(pubmed_ids, Exception):
        logger.warning(f"PubMed check failed: {pubmed_ids}")

    cochrane_ids = task_results.get("cochrane")
    if isinstance(cochrane_ids, list):
        v.cochrane_reviews = len(cochrane_ids)
        v.clinical_evidence_count += len(cochrane_ids)
    elif isinstance(cochrane_ids, Exception):
        logger.warning(f"Cochrane check failed: {cochrane_ids}")

    # Process iHerb marketplace data
    iherb_result = task_results.get("iherb")
    if isinstance(iherb_result, iherb.IHerbBrandSummary):
        v.iherb_brand_summary = iherb_result.to_dict()
        v.iherb_products_found = iherb_result.products_found
        v.iherb_avg_rating = iherb_result.avg_rating
        v.iherb_total_reviews = iherb_result.total_reviews
    elif isinstance(iherb_result, Exception):
        logger.warning(f"iHerb check failed: {iherb_result}")

    # Compute trust score
    v.trust_score, v.trust_level, v.trust_breakdown = _compute_trust_score(v)
    v.verification_time_ms = (time.time() - start) * 1000

    logger.info(
        f"Supplement verification: '{name}' score={v.trust_score} level={v.trust_level} "
        f"dsld={v.dsld_products_found} recalls={v.recall_count} ae={v.adverse_event_total} "
        f"evidence={v.clinical_evidence_count} iherb={v.iherb_products_found} in {v.verification_time_ms:.0f}ms"
    )

    return v
