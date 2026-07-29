"""Unit tests for Anthropic Sonnet 5 chat provider wiring."""

from app.core.config import Settings


def test_chat_provider_prefers_anthropic_when_key_present():
    s = Settings(
        anthropic_api_key="sk-ant-test",
        openai_api_key="sk-test",
        llm_provider="anthropic",
        llm_model="claude-sonnet-5",
    )
    assert s.chat_provider == "anthropic"
    assert s.chat_model == "claude-sonnet-5"
    assert s.chat_configured is True


def test_chat_provider_falls_back_to_openai():
    s = Settings(
        anthropic_api_key=None,
        openai_api_key="sk-test",
        llm_provider="anthropic",
        llm_model="claude-sonnet-5",
    )
    assert s.chat_provider == "openai"
    assert s.chat_model == "gpt-4o-mini"


def test_openai_provider_keeps_gpt_model():
    s = Settings(
        anthropic_api_key="sk-ant-test",
        openai_api_key="sk-test",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
    )
    assert s.chat_provider == "openai"
    assert s.chat_model == "gpt-4o-mini"
