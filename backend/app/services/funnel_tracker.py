"""
Funnel Stage Tracker

Tracks user progression through the freemium conversion funnel.
Logs to usage_analytics with action="funnel_stage".

Funnel stages:
  1. landed - user visits the site
  2. name_captured - user enters name
  3. disclaimer_accepted - user accepts medical disclaimer
  4. first_search - user performs first search (free)
  5. email_captured - user enters email (after 1st search)
  6. second_search - user performs second search (final free)
  7. signup_cta_shown - signup call-to-action is displayed
  8. registered - user creates account
"""

import logging
from typing import Optional

from app.services.analytics_writer import log_usage_event, schedule_analytics_task

logger = logging.getLogger(__name__)

# Valid funnel stages
FUNNEL_STAGES = [
    "landed",
    "name_captured",
    "disclaimer_accepted",
    "first_search",
    "email_captured",
    "second_search",
    "signup_cta_shown",
    "registered",
]


def get_funnel_stage_enum() -> list[str]:
    """Return the list of valid funnel stages."""
    return FUNNEL_STAGES


async def track_funnel_stage(
    session_id: str,
    tenant_id: str,
    stage: str,
    user_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> bool:
    """
    Track a user/session reaching a funnel stage.

    Args:
        session_id: Session identifier
        tenant_id: Tenant identifier
        stage: One of FUNNEL_STAGES
        user_id: Optional user ID (None for anonymous)
        metadata: Optional additional context

    Returns:
        True if stage is valid, False otherwise
    """
    if stage not in FUNNEL_STAGES:
        logger.warning(f"Invalid funnel stage: {stage}")
        return False

    # Build metadata
    full_metadata = metadata or {}
    full_metadata["session_id"] = session_id
    full_metadata["stage"] = stage

    # Schedule async write
    schedule_analytics_task(
        log_usage_event(
            tenant_id=tenant_id,
            user_id=user_id,
            action="funnel_stage",
            metadata=full_metadata,
        )
    )

    logger.debug(f"Tracked funnel stage: {stage} (session={session_id}, user={user_id})")
    return True
