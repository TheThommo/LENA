"""Tests for resilient search logging used by Add to Project."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.analytics_writer import (
    _persona_for_searches_table,
    log_search_event,
)


def test_persona_general_maps_to_researcher_for_searches_table():
    assert _persona_for_searches_table("general") == "researcher"
    assert _persona_for_searches_table("researcher") == "researcher"


@pytest.mark.asyncio
async def test_log_search_event_retries_without_optional_columns():
    client = MagicMock()
    table = MagicMock()
    client.table.return_value = table
    select_chain = MagicMock()
    select_chain.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
    table.select.return_value = select_chain

    insert_calls: list[dict] = []

    def insert_side_effect(payload):
        insert_calls.append(payload)
        result = MagicMock()
        if len(insert_calls) == 1:
            result.execute.side_effect = Exception("column llm_model does not exist")
        else:
            result.execute.return_value = MagicMock(data=[{"id": "ok"}])
        return result

    table.insert.side_effect = insert_side_effect

    with patch(
        "app.services.analytics_writer.get_supabase_admin_client",
        return_value=client,
    ), patch(
        "app.services.analytics_writer._session_exists",
        new_callable=AsyncMock,
        return_value=False,
    ):
        ok = await log_search_event(
            search_id="11111111-1111-1111-1111-111111111111",
            session_id=None,
            query="magnesium",
            persona="general",
            tenant_id="22222222-2222-2222-2222-222222222222",
            response_time_ms=1200.0,
            sources_queried=["pubmed"],
            sources_succeeded=["pubmed"],
            total_results=5,
            pulse_status="validated",
            user_id="33333333-3333-3333-3333-333333333333",
            llm_usage={"model": "gpt-4", "prompt_tokens": 1, "completion_tokens": 2},
            project_id="44444444-4444-4444-4444-444444444444",
        )

    assert ok is True
    assert "llm_model" in insert_calls[0]
    assert "llm_model" not in insert_calls[1]
    searches_insert = insert_calls[-1]
    assert searches_insert["persona_used"] == "researcher"
