"""
Subject resolution — "Who is this for?" pre-search gate.

Runs before expensive search when a personal-health query cannot be
matched to a population from profile or chat context. See AGENT.md.
"""

from __future__ import annotations

import re
from typing import Optional

# First-person / personal health signals
_PERSONAL_SIGNALS: tuple[str, ...] = (
    "i have",
    "i was diagnosed",
    "i've been diagnosed",
    "my condition",
    "my symptoms",
    "for me",
    "my supplements",
    "my medication",
    "i take",
    "i'm taking",
    "im taking",
    "i am taking",
    "my doctor",
    "should i take",
    "should i stop",
    "is it safe for me",
    "can i take",
    "what dose should i",
    "my blood pressure",
    "my heart",
    "my eyes",
    "current health",
    "my health",
)

# Clearly academic / general — no subject clarification needed
_ACADEMIC_CLEAR: tuple[str, ...] = (
    "systematic review",
    "meta-analysis",
    "meta analysis",
    "randomized controlled",
    "randomised controlled",
    "rct ",
    " rct",
    "clinical trial design",
    "guidelines for",
    "compare efficacy",
    "evidence base for",
    "pathophysiology of",
    "mechanism of action",
    "teaching",
    "lecture on",
    "curriculum",
)

# Clinician framing a third-party subject
_THIRD_PARTY_CLEAR: tuple[str, ...] = (
    "my patient",
    "patient presenting",
    "for a patient",
    "this patient",
    "client presenting",
    "my client",
)

# Chat / profile lines that establish a subject
_SUBJECT_ESTABLISHED_MARKERS: tuple[str, ...] = (
    "personal health",
    "conditions:",
    "diagnosed",
    "hypertension",
    "diabetes",
    "male",
    "female",
    "years old",
    "y/o",
    "for you personally",
    "for myself",
    "for my patient",
    "for teaching",
    "general reference",
    "who is this for",
    "research for:",
)

_CLARIFICATION_MESSAGE = (
    "Quick check — **who is this research for?**\n\n"
    "For example:\n"
    "- **You personally** (tell me age, sex, and relevant conditions)\n"
    "- **A patient or client** (brief clinical context)\n"
    "- **Teaching or presentation** material\n"
    "- **General reference** (no personal tailoring)\n\n"
    "Once I know, I'll tailor the evidence to the right population."
)


def _has_personal_health_signal(query: str) -> bool:
    q = query.lower()
    if any(sig in q for sig in _PERSONAL_SIGNALS):
        return True
    # Long narrative personal prompts (e.g. pasted health history)
    if len(query) > 200 and re.search(r"\b(i|my)\b", q):
        return True
    return False


def _is_academically_clear(query: str) -> bool:
    q = query.lower()
    return any(phrase in q for phrase in _ACADEMIC_CLEAR)


def _is_third_party_clear(query: str) -> bool:
    q = query.lower()
    return any(phrase in q for phrase in _THIRD_PARTY_CLEAR)


def _profile_establishes_subject(profile_context: Optional[str]) -> bool:
    if not profile_context:
        return False
    pl = profile_context.lower()
    if "personal health / context notes:" in pl:
        # Notes section present and non-empty
        for line in profile_context.splitlines():
            if line.lower().startswith("personal health / context notes:"):
                notes = line.split(":", 1)[1].strip()
                if len(notes) > 15:
                    return True
    return any(m in pl for m in _SUBJECT_ESTABLISHED_MARKERS)


def _chat_establishes_subject(chat_context: Optional[str]) -> bool:
    if not chat_context or len(chat_context.strip()) < 40:
        return False
    cl = chat_context.lower()
    return any(m in cl for m in _SUBJECT_ESTABLISHED_MARKERS)


def _query_establishes_subject(query: str) -> bool:
    """User answered the clarification or gave enough demographics inline."""
    q = query.lower()
    if any(
        p in q
        for p in (
            "for me personally",
            "for myself",
            "general reference",
            "for teaching",
            "for my patient",
            "for a patient",
            "no personal tailoring",
        )
    ):
        return True
    if re.search(r"\b\d{2,3}\s*(yo|y/?o|years?\s*old)\b", q):
        return True
    if re.search(r"\b\d{2}[mf]\b", q):
        return True
    if re.search(r"\b(male|female)\b", q) and len(q) > 40:
        return True
    return False


def needs_subject_clarification(
    query: str,
    persona: str = "general",
    profile_context: Optional[str] = None,
    chat_context: Optional[str] = None,
) -> bool:
    """
    Return True when we should ask "Who is this for?" before searching.

    Skips clarification when profile, chat, or query already establish subject.
    """
    if not _has_personal_health_signal(query):
        return False
    if _query_establishes_subject(query):
        return False
    if _is_academically_clear(query):
        return False
    if _is_third_party_clear(query):
        return False
    if _profile_establishes_subject(profile_context):
        return False
    if _chat_establishes_subject(chat_context):
        return False

    # Patient persona + first-person query: subject is likely the asker,
    # but without profile/chat we still lack demographics for population match.
    if persona == "patient" and _has_personal_health_signal(query):
        return True

    # Clinician without "my patient" and without profile → ambiguous
    if persona in ("clinician", "pharmacist", "physiotherapist"):
        return True

    # General / student / researcher with personal health narrative
    if persona in ("general", "medical_student", "researcher", "lecturer",
                   "neuroscientist", "alternative_practitioner"):
        return True

    return False


def get_subject_clarification_message() -> str:
    return _CLARIFICATION_MESSAGE
