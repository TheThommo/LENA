"""
Search routes - the core LENA query endpoint.
"""

from fastapi import APIRouter, Query
from typing import Optional
import uuid

from app.core.persona import PersonaType, detect_persona_from_query, get_persona_config
from app.core.logging import get_logger
from app.services.search_orchestrator import run_search
from app.services.analytics_writer import log_search_event, schedule_analytics_task
from app.services.topic_classifier import classify_query_topic
from app.services.funnel_tracker import track_funnel_stage

logger = get_logger("lena.search")

router = APIRouter(prefix="/search", tags=["search"], redirect_slashes=False)


@router.get("/")
async def search_literature(
    q: str = Query(..., description="Search query"),
    persona: Optional[PersonaType] = Query(None, description="User persona override"),
    sources: Optional[str] = Query(None, description="Comma-separated source filter"),
    max_results: int = Query(10, ge=1, le=50, description="Max results per source"),
    include_alt_medicine: bool = Query(True, description="Include alternative medicine results"),
    session_id: Optional[str] = Query(None, description="Session identifier for analytics"),
    tenant_id: Optional[str] = Query("default", description="Tenant identifier"),
):
    """
    Search medical literature across all sources.

    This is the main LENA endpoint. It:
    1. Detects or uses the provided persona
    2. Checks medical advice guardrail
    3. Queries all (or filtered) data sources in parallel
    4. Runs PULSE cross-reference validation with keyword overlap scoring
    5. Filters by alternative medicine toggle if needed
    6. Logs analytics (fire-and-forget)
    7. Returns results with validation status and persona context
    """
    # Step 1: Detect persona
    detected_persona = persona or detect_persona_from_query(q)
    persona_config = get_persona_config(detected_persona)

    # Step 2: Parse source filter
    source_list = sources.split(",") if sources else None

    # Step 3: Generate search ID for tracking
    search_id = str(uuid.uuid4())
    session_id = session_id or str(uuid.uuid4())

    # Step 4: Run the full search pipeline (guardrail + parallel queries + PULSE + caching)
    search_result = await run_search(
        query=q,
        max_results_per_source=max_results,
        sources=source_list,
        include_alt_medicine=include_alt_medicine,
    )

    # Step 5: Log analytics (fire-and-forget, never blocks)
    if not search_result.get("guardrail_triggered"):
        response_time_ms = search_result.get("response_time_ms", 0)
        sources_queried = search_result.get("sources_queried", [])
        sources_failed = search_result.get("sources_failed", {})
        sources_succeeded = [s for s in sources_queried if s not in sources_failed]
        total_results = search_result.get("total_results", 0)
        pulse_status = search_result.get("pulse_report", {}).get("status", "pending")

        # Log search event
        schedule_analytics_task(
            log_search_event(
                search_id=search_id,
                session_id=session_id,
                query=q,
                persona=detected_persona.value,
                tenant_id=tenant_id,
                response_time_ms=response_time_ms,
                sources_queried=sources_queried,
                sources_succeeded=sources_succeeded,
                total_results=total_results,
                pulse_status=pulse_status,
            )
        )

        # Classify topics and log separately (for trending dashboard)
        topics = classify_query_topic(q)
        logger.debug(f"Search topics: {topics}")

    # Step 6: Build response with persona context
    return {
        "search_id": search_id,
        "session_id": session_id,
        "query": q,
        "persona": {
            "detected": detected_persona.value,
            "display_name": persona_config.display_name,
            "tone": persona_config.tone,
            "depth": persona_config.depth,
        },
        **search_result,
    }
