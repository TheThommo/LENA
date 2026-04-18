"""
Search routes - the core LENA query endpoint.
"""

from fastapi import APIRouter, Query, Request
from typing import Optional
import uuid

from app.core.persona import PersonaType, detect_persona_from_query, get_persona_config
from app.core.logging import get_logger
from app.services.search_orchestrator import run_search
from app.services.analytics_writer import log_search_event, schedule_analytics_task
from app.services.topic_classifier import classify_query_topic
from app.services.funnel_tracker import track_funnel_stage

logger = get_logger("lena.search")

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search_literature(
    request: Request,
    q: str = Query(..., description="Search query"),
    persona: Optional[PersonaType] = Query(None, description="User persona override"),
    sources: Optional[str] = Query(None, description="Comma-separated source filter"),
    max_results: int = Query(10, ge=1, le=50, description="Max results per source"),
    include_alt_medicine: bool = Query(True, description="[Legacy] Include alternative medicine results"),
    modes: Optional[str] = Query(
        None,
        description="Comma-separated result modes: all,supplements,herbal,alternatives,outlier (defaults to 'all')",
    ),
    session_id: Optional[str] = Query(None, description="Session identifier for analytics"),
    project_id: Optional[str] = Query(None, description="File this search under a project (auth users only)"),
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

    # Step 2: Parse source + mode filters
    source_list = sources.split(",") if sources else None
    mode_list = [m.strip() for m in modes.split(",")] if modes else None

    # Step 3: Generate search ID for tracking.
    # session_id stays None for authenticated (JWT) users — the analytics
    # writer validates it against the sessions table before insert so a
    # stale/random UUID no longer breaks the FK.
    search_id = str(uuid.uuid4())

    # ── Resolve tenant_id & user_id from middleware state ──
    # SearchGateMiddleware puts the session object or user_id onto
    # request.state before we arrive here.
    resolved_tenant_id: Optional[str] = None
    resolved_user_id: Optional[str] = None

    # Authenticated path (JWT)
    if hasattr(request.state, "user_id") and request.state.user_id:
        resolved_user_id = str(request.state.user_id)
        # Look up user's default tenant from user_tenants
        try:
            from app.db.repositories.user_repo import UserTenantRepository
            from uuid import UUID as _UUID
            memberships = await UserTenantRepository.get_by_user_id(_UUID(resolved_user_id))
            if memberships:
                resolved_tenant_id = str(memberships[0].tenant_id)
        except Exception:
            pass

    # Anonymous session path
    if not resolved_tenant_id:
        session_obj = getattr(request.state, "session", None)
        if session_obj and hasattr(session_obj, "tenant_id"):
            resolved_tenant_id = str(session_obj.tenant_id)
            session_id = str(session_obj.id)

    # Step 4: Run the full search pipeline (guardrail + parallel queries + PULSE + caching)
    search_result = await run_search(
        query=q,
        max_results_per_source=max_results,
        sources=source_list,
        include_alt_medicine=include_alt_medicine,
        persona=detected_persona.value,
        modes=mode_list,
    )

    # Step 5: Log analytics (fire-and-forget, never blocks)
    if not search_result.get("guardrail_triggered") and resolved_tenant_id:
        response_time_ms = search_result.get("response_time_ms", 0)
        sources_queried = search_result.get("sources_queried", [])
        sources_failed = search_result.get("sources_failed", {})
        sources_succeeded = [s for s in sources_queried if s not in sources_failed]
        total_results = search_result.get("total_results", 0)
        pulse_status = search_result.get("pulse_report", {}).get("status", "pending")

        # Project filing: only allowed for authenticated callers, and only
        # if they own the project. Silently drop the hint for anon users so
        # a forged query param can't forge project membership.
        resolved_project_id: Optional[str] = None
        if project_id and resolved_user_id:
            try:
                from app.db.supabase import get_supabase_admin_client
                admin_client = get_supabase_admin_client()
                owned = (
                    admin_client.table("projects")
                    .select("id")
                    .eq("id", project_id)
                    .eq("user_id", resolved_user_id)
                    .limit(1)
                    .execute()
                )
                if owned.data:
                    resolved_project_id = project_id
            except Exception:
                logger.warning("project_id ownership check failed", exc_info=True)

        # Log search event (includes LLM cost when the summary ran)
        schedule_analytics_task(
            log_search_event(
                search_id=search_id,
                session_id=session_id,
                query=q,
                persona=detected_persona.value,
                tenant_id=resolved_tenant_id,
                user_id=resolved_user_id,
                response_time_ms=response_time_ms,
                sources_queried=sources_queried,
                sources_succeeded=sources_succeeded,
                total_results=total_results,
                pulse_status=pulse_status,
                llm_usage=search_result.get("llm_usage"),
                project_id=resolved_project_id,
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
