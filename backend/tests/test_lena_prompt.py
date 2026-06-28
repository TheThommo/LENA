"""Tests for LENA prompt composition."""

from app.core.lena_prompt import (
    COMMUNICATION_STYLE_MODIFIERS,
    build_system_message,
    parse_communication_style,
)
from app.core.persona import PersonaType


def test_parse_communication_style_from_profile():
    profile = "Specialty: Cardiology\nPreferred response style: clinical"
    assert parse_communication_style(profile) == "clinical"


def test_adaptive_style_not_parsed():
    profile = "Preferred response style: default"
    assert parse_communication_style(profile) is None


def test_build_system_message_includes_persona():
    msg = build_system_message(persona=PersonaType.CLINICIAN)
    assert "Clinician" in msg
    assert "ADAPTIVE" in msg


def test_build_system_message_includes_communication_override():
    profile = "Preferred response style: academic"
    msg = build_system_message(persona=PersonaType.GENERAL, profile_context=profile)
    assert COMMUNICATION_STYLE_MODIFIERS["academic"][:20] in msg


def test_population_matching_in_base_prompt():
    from app.core.lena_prompt import LENA_SYSTEM_PROMPT

    assert "Population Matching" in LENA_SYSTEM_PROMPT
    assert "profile" in LENA_SYSTEM_PROMPT.lower()
