"""Tests for LENA subject resolution gate."""

from app.core.subject_resolution import (
    get_subject_clarification_message,
    needs_subject_clarification,
)


def test_ambiguous_personal_query_without_profile():
    assert needs_subject_clarification(
        "I have hypertension and take magnesium — what does the evidence say?",
        persona="general",
        profile_context=None,
        chat_context=None,
    )


def test_profile_with_notes_skips_clarification():
    profile = "Personal health / context notes: 58M, hypertension, CSR, on magnesium"
    assert not needs_subject_clarification(
        "Should I keep taking magnesium?",
        persona="general",
        profile_context=profile,
        chat_context=None,
    )


def test_chat_context_skips_clarification():
    chat = "User: For me personally — 58M with hypertension and CSR"
    assert not needs_subject_clarification(
        "What about magnesium?",
        persona="general",
        profile_context=None,
        chat_context=chat,
    )


def test_academic_query_skips_clarification():
    assert not needs_subject_clarification(
        "Systematic review of magnesium supplementation in adults with hypertension",
        persona="researcher",
        profile_context=None,
        chat_context=None,
    )


def test_clinician_patient_query_skips_clarification():
    assert not needs_subject_clarification(
        "My patient has hypertension — evidence for magnesium?",
        persona="clinician",
        profile_context=None,
        chat_context=None,
    )


def test_inline_demographics_skips_clarification():
    assert not needs_subject_clarification(
        "For me personally — 58M, hypertension, on magnesium and vitamin D",
        persona="patient",
        profile_context=None,
        chat_context=None,
    )


def test_clarification_message_is_actionable():
    msg = get_subject_clarification_message()
    assert "who is this research for" in msg.lower()
    assert "patient" in msg.lower()
