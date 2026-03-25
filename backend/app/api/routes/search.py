"""
Search routes - the core LENA query endpoint.
"""

from fastapi import APIRouter, Query
from typing import Optional

from app.core.persona import PersonaType, detect_persona_from_query

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/")
async def search_literature(
    q: str = Query(..., description="Search query"),
    persona: Optional[PersonaType] = Query(None, description="User persona override"),
    sources: Optional[str] = Query(None, description="Comma-separated source filter"),
    max_results: int = Query(10, ge=1, le=50, description="Max results per source"),
):
    """
    Search medical literature across all sources.

    This is the main LENA endpoint. It:
    1. Detects or uses the provided persona
    2. Queries all (or filtered) data sources
    3. Runs PULSE cross-reference validation
    4. Returns results with validation status

    MVP: Returns raw results from each source.
    V2: Will include PULSE validation and LLM synthesis.
    """
    # Detect persona if not provided
    detected_persona = persona or detect_persona_from_query(q)

    # Placeholder response structure
    return {
        "query": q,
        "persona": detected_persona,
        "pulse_status": "pending",
        "message": "Search endpoint scaffolded. Wire up in next milestone.",
        "sources_to_query": (
            sources.split(",") if sources
            else ["pubmed", "clinical_trials", "cochrane", "who_iris", "cdc"]
        ),
        "max_results_per_source": max_results,
    }
