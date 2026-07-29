"""G16 GUARD: personal advice → warm redirect, no Key Findings brief."""

from app.core.claim_pipeline import ClaimGroup, compose_brief
from app.core.guardrails import check_for_advice_request, get_warm_redirect


def test_g16_query_triggers_advice_guardrail():
    q = (
        "I've been getting chest pain when I walk upstairs — "
        "should I stop taking my beta blocker?"
    )
    assert check_for_advice_request(q) is True


def test_compose_brief_returns_warm_redirect_only():
    q = (
        "I've been getting chest pain when I walk upstairs — "
        "should I stop taking my beta blocker?"
    )
    brief = compose_brief(q, [])
    assert brief == get_warm_redirect(q)
    assert "## Key Findings" not in brief
    assert "Bottom Line" not in brief
    low = brief.lower()
    assert any(tok in low for tok in ("doctor", "care", "urgent", "emergency", "team"))
    assert "concern" in low


def test_compose_brief_non_advice_still_builds_sections():
    brief = compose_brief("what are the side effects of metformin?", [])
    assert "## Key Findings" in brief
