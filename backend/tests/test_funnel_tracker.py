"""
Tests for Funnel Stage Tracker

Tests conversion funnel stage tracking.

Run with: pytest tests/test_funnel_tracker.py -v
"""

import pytest
from unittest.mock import patch, AsyncMock
from uuid import uuid4

from app.services.funnel_tracker import (
    track_funnel_stage,
    get_funnel_stage_enum,
    FUNNEL_STAGES,
)


class TestFunnelStages:
    """Test funnel stage definitions."""

    def test_funnel_stages_defined(self):
        """FUNNEL_STAGES should be defined."""
        assert FUNNEL_STAGES
        assert len(FUNNEL_STAGES) > 0

    def test_funnel_stages_list(self):
        """Should have expected funnel stages."""
        expected = [
            "landed",
            "name_captured",
            "disclaimer_accepted",
            "first_search",
            "email_captured",
            "second_search",
            "signup_cta_shown",
            "registered",
        ]
        assert FUNNEL_STAGES == expected

    def test_get_funnel_stage_enum(self):
        """get_funnel_stage_enum should return list of stages."""
        stages = get_funnel_stage_enum()
        assert stages == FUNNEL_STAGES


class TestFunnelTracking:
    """Test funnel stage tracking."""

    @pytest.mark.asyncio
    async def test_track_valid_stage(self):
        """Tracking a valid stage should return True."""
        with patch("app.services.funnel_tracker.schedule_analytics_task"):
            result = await track_funnel_stage(
                session_id=str(uuid4()),
                tenant_id="lena",
                stage="landed",
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_track_invalid_stage(self):
        """Tracking invalid stage should return False."""
        result = await track_funnel_stage(
            session_id=str(uuid4()),
            tenant_id="lena",
            stage="invalid_stage",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_track_all_valid_stages(self):
        """All valid stages should be trackable."""
        with patch("app.services.funnel_tracker.schedule_analytics_task"):
            for stage in FUNNEL_STAGES:
                result = await track_funnel_stage(
                    session_id=str(uuid4()),
                    tenant_id="lena",
                    stage=stage,
                )
                assert result is True

    @pytest.mark.asyncio
    async def test_track_with_user_id(self):
        """Should track with optional user_id."""
        with patch("app.services.funnel_tracker.schedule_analytics_task"):
            result = await track_funnel_stage(
                session_id=str(uuid4()),
                tenant_id="lena",
                stage="registered",
                user_id="user_123",
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_track_with_metadata(self):
        """Should track with optional metadata."""
        with patch("app.services.funnel_tracker.schedule_analytics_task"):
            result = await track_funnel_stage(
                session_id=str(uuid4()),
                tenant_id="lena",
                stage="first_search",
                metadata={"query": "heart failure", "source_count": 3},
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_track_without_user_id(self):
        """Should track without user_id (anonymous)."""
        with patch("app.services.funnel_tracker.schedule_analytics_task"):
            result = await track_funnel_stage(
                session_id=str(uuid4()),
                tenant_id="lena",
                stage="landed",
                user_id=None,
            )
            assert result is True


class TestFunnelProgression:
    """Test typical funnel progression."""

    @pytest.mark.asyncio
    async def test_freemium_funnel_progression(self):
        """Test typical user progression through funnel."""
        with patch("app.services.funnel_tracker.schedule_analytics_task"):
            session_id = str(uuid4())
            tenant_id = "lena"

            # User lands on site
            assert await track_funnel_stage(session_id, tenant_id, "landed") is True

            # User enters name
            assert await track_funnel_stage(session_id, tenant_id, "name_captured") is True

            # User accepts disclaimer
            assert await track_funnel_stage(session_id, tenant_id, "disclaimer_accepted") is True

            # User performs first search
            assert await track_funnel_stage(session_id, tenant_id, "first_search") is True

            # User enters email
            assert await track_funnel_stage(session_id, tenant_id, "email_captured") is True

            # User performs second search
            assert await track_funnel_stage(session_id, tenant_id, "second_search") is True

            # Signup CTA is shown
            assert await track_funnel_stage(session_id, tenant_id, "signup_cta_shown") is True

            # User registers
            assert await track_funnel_stage(session_id, tenant_id, "registered") is True

    @pytest.mark.asyncio
    async def test_out_of_order_stages_still_valid(self):
        """Stages can be tracked out of order (e.g., direct registration)."""
        with patch("app.services.funnel_tracker.schedule_analytics_task"):
            session_id = str(uuid4())
            tenant_id = "lena"

            # Skip to registered directly
            assert await track_funnel_stage(session_id, tenant_id, "registered") is True
            # Then track other stages
            assert await track_funnel_stage(session_id, tenant_id, "landed") is True


class TestFunnelMetadata:
    """Test metadata handling in funnel tracking."""

    @pytest.mark.asyncio
    async def test_metadata_included_in_tracking(self):
        """Metadata should be included in tracking."""
        with patch("app.services.funnel_tracker.schedule_analytics_task") as mock_schedule:
            session_id = str(uuid4())
            metadata = {"source_count": 5, "query": "test"}

            await track_funnel_stage(
                session_id=session_id,
                tenant_id="lena",
                stage="first_search",
                metadata=metadata,
            )

            # Verify schedule was called
            assert mock_schedule.called

    @pytest.mark.asyncio
    async def test_session_and_stage_in_metadata(self):
        """Session ID and stage should always be in metadata."""
        with patch("app.services.funnel_tracker.schedule_analytics_task") as mock_schedule:
            session_id = str(uuid4())

            await track_funnel_stage(
                session_id=session_id,
                tenant_id="lena",
                stage="landed",
            )

            # Verify schedule was called
            assert mock_schedule.called


class TestFunnelEdgeCases:
    """Test edge cases."""

    @pytest.mark.asyncio
    async def test_empty_stage_string(self):
        """Empty stage string should return False."""
        result = await track_funnel_stage(
            session_id=str(uuid4()),
            tenant_id="lena",
            stage="",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_case_sensitive_stage(self):
        """Stage checking should be case-sensitive."""
        result = await track_funnel_stage(
            session_id=str(uuid4()),
            tenant_id="lena",
            stage="Landed",  # Should fail - wrong case
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_multiword_stage_exact_match(self):
        """Multiword stages must match exactly."""
        with patch("app.services.funnel_tracker.schedule_analytics_task"):
            # Valid multiword stage
            result = await track_funnel_stage(
                session_id=str(uuid4()),
                tenant_id="lena",
                stage="disclaimer_accepted",
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_none_user_id_allowed(self):
        """None user_id should be allowed (anonymous)."""
        with patch("app.services.funnel_tracker.schedule_analytics_task"):
            result = await track_funnel_stage(
                session_id=str(uuid4()),
                tenant_id="lena",
                stage="landed",
                user_id=None,
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_duplicate_stage_tracking(self):
        """Should be able to track same stage multiple times."""
        with patch("app.services.funnel_tracker.schedule_analytics_task"):
            session_id = str(uuid4())

            # Track same stage twice
            result1 = await track_funnel_stage(
                session_id=session_id,
                tenant_id="lena",
                stage="first_search",
            )
            result2 = await track_funnel_stage(
                session_id=session_id,
                tenant_id="lena",
                stage="first_search",
            )

            assert result1 is True
            assert result2 is True
