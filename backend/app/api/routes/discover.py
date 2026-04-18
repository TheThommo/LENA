"""
Discovery endpoints — public (no auth required).

Powers the welcome page suggested prompts and trending topics.
All data comes from real search_logs, not hardcoded strings.
When search_logs is empty (cold start), returns curated fallbacks
so the welcome page isn't blank on day one.
"""

from datetime import date, timedelta
from collections import Counter
from typing import Optional

from fastapi import APIRouter, Query
from app.db.supabase import get_supabase_admin_client
from app.core.logging import get_logger

logger = get_logger("lena.discover")
router = APIRouter(prefix="/discover", tags=["discover"])


# ── Curated fallbacks for cold start ─────────────────────────────────
# Used ONLY when search_logs has no data. Replaced by real data as soon
# as the first searches happen.

_FALLBACK_PROMPTS = {
    "general": [
        "What does the evidence say about intermittent fasting and longevity?",
        "How effective are probiotics for gut health?",
        "Compare evidence for natural anxiety treatments",
    ],
    "clinician": [
        "Latest RCTs on SGLT2 inhibitors for heart failure",
        "Evidence for early mobilisation after hip replacement",
        "Drug interactions with DOACs in elderly patients",
    ],
    "medical_student": [
        "Pathophysiology of Type 2 diabetes — key mechanisms",
        "Compare ACE inhibitors vs ARBs as first-line hypertension treatment",
        "Latest guidelines for managing acute asthma exacerbation",
    ],
    "pharmacist": [
        "Drug interactions with direct oral anticoagulants",
        "Biosimilar efficacy compared to reference biologics",
        "Pharmacogenomics evidence for warfarin dosing",
    ],
    "researcher": [
        "Systematic reviews on immunotherapy in solid tumours",
        "Meta-analysis methodology for heterogeneous clinical trials",
        "Evidence gaps in rare disease therapeutic development",
    ],
    "lecturer": [
        "Evidence-based medicine teaching methodologies",
        "Simulation-based education outcomes in clinical training",
        "Competency assessment tools for medical education",
    ],
    "physiotherapist": [
        "Manual therapy vs exercise for chronic low back pain",
        "Exercise prescription evidence for type 2 diabetes management",
        "Dry needling evidence for myofascial trigger points",
    ],
    "neuroscientist": [
        "Neuroplasticity mechanisms in stroke recovery",
        "fMRI evidence for default mode network in depression",
        "Gut-brain axis and neurodegenerative disease pathways",
    ],
    "alternative_practitioner": [
        "Clinical evidence for curcumin in inflammatory conditions",
        "Systematic reviews on acupuncture for chronic pain",
        "Ashwagandha adaptogenic effects — RCT evidence",
    ],
    "patient": [
        "Natural remedies for sleep — what does the research say?",
        "Is magnesium supplementation backed by clinical evidence?",
        "How does exercise compare to medication for mild depression?",
    ],
}

_FALLBACK_TRENDING = [
    {"topic": "GLP-1 receptor agonists", "count": 0, "is_fallback": True},
    {"topic": "Long COVID treatment", "count": 0, "is_fallback": True},
    {"topic": "AI in diagnostic imaging", "count": 0, "is_fallback": True},
]


@router.get("/suggestions")
async def get_suggestions(
    persona: Optional[str] = Query("general", description="User persona for tailored suggestions"),
):
    """
    Suggested search prompts for the welcome page.

    Logic:
    1. If search_logs has data: return the most popular queries for
       this persona (or all personas if not enough persona-specific).
    2. If search_logs is empty (cold start): return curated fallbacks.

    No auth required — this is public.
    """
    try:
        client = get_supabase_admin_client()
        seven_days_ago = (date.today() - timedelta(days=7)).isoformat()

        # Try persona-specific popular queries first
        q = (
            client.table("search_logs")
            .select("query, persona")
            .gte("created_at", seven_days_ago)
            .order("created_at", desc=True)
            .limit(200)
        )
        if persona and persona != "general":
            q = q.eq("persona", persona)
        res = q.execute()
        rows = res.data or []

        if len(rows) < 3:
            # Not enough persona-specific data — try all personas
            res_all = (
                client.table("search_logs")
                .select("query")
                .gte("created_at", seven_days_ago)
                .order("created_at", desc=True)
                .limit(200)
                .execute()
            )
            rows = res_all.data or []

        if not rows:
            # Cold start — use curated fallbacks
            return {
                "suggestions": _FALLBACK_PROMPTS.get(persona or "general", _FALLBACK_PROMPTS["general"]),
                "source": "curated",
            }

        # Count and return top 3 unique queries
        query_counts = Counter()
        for r in rows:
            q_text = (r.get("query") or "").strip()
            if q_text and len(q_text) > 10:
                query_counts[q_text] += 1

        top = [q for q, _ in query_counts.most_common(5)]
        if len(top) < 3:
            # Supplement with fallbacks
            fallbacks = _FALLBACK_PROMPTS.get(persona or "general", _FALLBACK_PROMPTS["general"])
            for fb in fallbacks:
                if fb not in top:
                    top.append(fb)
                if len(top) >= 3:
                    break

        return {
            "suggestions": top[:3],
            "source": "search_data" if query_counts else "curated",
        }

    except Exception as e:
        logger.error("Failed to get suggestions", exc_info=True)
        return {
            "suggestions": _FALLBACK_PROMPTS.get(persona or "general", _FALLBACK_PROMPTS["general"]),
            "source": "curated",
        }


@router.get("/trending")
async def get_trending():
    """
    Trending topics for the welcome page.

    Compares this week's search volume by topic against last week.
    The count shown is THIS week's search count. The trend arrow
    indicates whether it's up or down vs last week.

    No auth required — this is public.
    """
    try:
        client = get_supabase_admin_client()
        now = date.today()
        this_week_start = (now - timedelta(days=7)).isoformat()
        last_week_start = (now - timedelta(days=14)).isoformat()
        last_week_end = (now - timedelta(days=7)).isoformat()

        # This week's queries
        this_week = (
            client.table("search_logs")
            .select("query")
            .gte("created_at", this_week_start)
            .execute()
        )

        # Last week's queries (for trend comparison)
        last_week = (
            client.table("search_logs")
            .select("query")
            .gte("created_at", last_week_start)
            .lte("created_at", last_week_end)
            .execute()
        )

        this_counts = Counter()
        for r in this_week.data or []:
            q = (r.get("query") or "").strip().lower()
            if q and len(q) > 5:
                # Group by broad topic (first 3-4 significant words)
                words = [w for w in q.split() if len(w) > 3][:4]
                topic = " ".join(words).title() if words else q.title()
                this_counts[topic] += 1

        last_counts = Counter()
        for r in last_week.data or []:
            q = (r.get("query") or "").strip().lower()
            if q and len(q) > 5:
                words = [w for w in q.split() if len(w) > 3][:4]
                topic = " ".join(words).title() if words else q.title()
                last_counts[topic] += 1

        if not this_counts:
            return {"trending": _FALLBACK_TRENDING, "source": "curated"}

        trending = []
        for topic, count in this_counts.most_common(5):
            last_count = last_counts.get(topic, 0)
            trend = "up" if count > last_count else ("down" if count < last_count else "flat")
            trending.append({
                "topic": topic,
                "count": count,
                "trend": trend,
                "is_fallback": False,
            })

        return {"trending": trending[:5], "source": "search_data"}

    except Exception as e:
        logger.error("Failed to get trending", exc_info=True)
        return {"trending": _FALLBACK_TRENDING, "source": "curated"}
