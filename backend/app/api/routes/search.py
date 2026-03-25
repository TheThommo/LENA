"""
Search routes - the core LENA query endpoint.
"""

from fastapi import APIRouter, Query
from typing import Optional

from app.core.persona import PersonaType, detect_persona_from_query, get_persona_config
from app.services.search_orchestrator import run_search

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
    2. Checks medical advice guardrail
    3. Queries all (or filtered) data sources in parallel
    4. Runs PULSE cross-reference validation with keyword overlap scoring
    5. Returns results with validation status and persona context
    """
    # Step 1: Detect persona
    detected_persona = persona or detect_persona_from_query(q)
    persona_config = get_persona_config(detected_persona)

    # Step 2: Parse source filter
    source_list = sources.split(",") if sources else None

    # Step 3: Run the full search pipeline (guardrail + parallel queries + PULSE)
    search_result = await run_search(
        query=q,
        max_results_per_source=max_results,
        sources=source_list,
    )

    # Step 4: Build response with persona context
    return {
        "query": q,
        "persona": {
            "detected": detected_persona.value,
            "display_name": persona_config.display_name,
            "tone": persona_config.tone,
            "depth": persona_config.depth,
        },
        **search_result,
    }
