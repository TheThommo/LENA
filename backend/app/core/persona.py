"""
Persona Detection Module

Identifies the user's profession/role and adjusts LENA's response
style accordingly. Same data, different delivery.

Supported personas:
- medical_student: Educational framing, explains terminology
- clinician: Clinical focus, treatment relevance, brief
- pharmacist: Drug interactions, dosing, formulary focus
- researcher: Methodology focus, statistical detail, citations
- lecturer: Teaching-ready framing, slide-friendly summaries
- physiotherapist: Rehabilitation focus, functional outcomes
- patient: Plain language, empathetic, no jargon, care team redirect
- general: Balanced middle ground
"""

from enum import Enum
from dataclasses import dataclass


class PersonaType(str, Enum):
    MEDICAL_STUDENT = "medical_student"
    CLINICIAN = "clinician"
    PHARMACIST = "pharmacist"
    RESEARCHER = "researcher"
    LECTURER = "lecturer"
    PHYSIOTHERAPIST = "physiotherapist"
    PATIENT = "patient"
    GENERAL = "general"


@dataclass
class PersonaConfig:
    persona_type: PersonaType
    display_name: str
    tone: str
    depth: str
    system_prompt_modifier: str


PERSONA_CONFIGS: dict[PersonaType, PersonaConfig] = {
    PersonaType.MEDICAL_STUDENT: PersonaConfig(
        persona_type=PersonaType.MEDICAL_STUDENT,
        display_name="Medical Student",
        tone="educational and encouraging",
        depth="detailed with terminology explanations",
        system_prompt_modifier=(
            "The user is a medical student. Explain findings clearly, "
            "define key terms when first used, and connect evidence to "
            "clinical learning objectives. Use a supportive, teaching tone."
        ),
    ),
    PersonaType.CLINICIAN: PersonaConfig(
        persona_type=PersonaType.CLINICIAN,
        display_name="Clinician",
        tone="direct and clinical",
        depth="concise with treatment relevance",
        system_prompt_modifier=(
            "The user is a practicing clinician. Be concise and clinically "
            "relevant. Focus on treatment implications, evidence strength, "
            "and practical takeaways. Skip basic explanations."
        ),
    ),
    PersonaType.PHARMACIST: PersonaConfig(
        persona_type=PersonaType.PHARMACIST,
        display_name="Pharmacist",
        tone="precise and drug-focused",
        depth="detailed on pharmacology",
        system_prompt_modifier=(
            "The user is a pharmacist. Emphasise drug interactions, dosing "
            "evidence, contraindications, and formulary relevance. Include "
            "pharmacokinetic details when available."
        ),
    ),
    PersonaType.RESEARCHER: PersonaConfig(
        persona_type=PersonaType.RESEARCHER,
        display_name="Researcher",
        tone="analytical and methodological",
        depth="full depth with statistical detail",
        system_prompt_modifier=(
            "The user is a researcher. Focus on methodology, study design, "
            "sample sizes, statistical significance, and limitations. "
            "Always include full citations and DOIs."
        ),
    ),
    PersonaType.LECTURER: PersonaConfig(
        persona_type=PersonaType.LECTURER,
        display_name="Lecturer / Educator",
        tone="structured and presentation-ready",
        depth="teaching-level summaries",
        system_prompt_modifier=(
            "The user is a lecturer or educator. Structure findings in a "
            "teaching-friendly format. Include key takeaways suitable for "
            "slides, and suggest discussion points where appropriate."
        ),
    ),
    PersonaType.PHYSIOTHERAPIST: PersonaConfig(
        persona_type=PersonaType.PHYSIOTHERAPIST,
        display_name="Physiotherapist",
        tone="functional and rehabilitation-focused",
        depth="outcome-oriented",
        system_prompt_modifier=(
            "The user is a physiotherapist. Focus on functional outcomes, "
            "rehabilitation protocols, exercise-based interventions, and "
            "return-to-function metrics."
        ),
    ),
    PersonaType.PATIENT: PersonaConfig(
        persona_type=PersonaType.PATIENT,
        display_name="Patient / Public",
        tone="warm, empathetic, plain language",
        depth="simplified, no jargon",
        system_prompt_modifier=(
            "The user appears to be a patient or member of the public. "
            "Use plain, warm language. Avoid medical jargon entirely. "
            "IMPORTANT: Never give medical advice. If the query crosses "
            "into advice territory, acknowledge their concern with genuine "
            "empathy and warmly redirect them to speak with their care team."
        ),
    ),
    PersonaType.GENERAL: PersonaConfig(
        persona_type=PersonaType.GENERAL,
        display_name="General",
        tone="balanced and accessible",
        depth="moderate detail",
        system_prompt_modifier=(
            "Provide a balanced, accessible summary of the evidence. "
            "Define technical terms briefly and include citations."
        ),
    ),
}


def get_persona_config(persona_type: PersonaType) -> PersonaConfig:
    """Get the configuration for a given persona type."""
    return PERSONA_CONFIGS.get(persona_type, PERSONA_CONFIGS[PersonaType.GENERAL])


# Detection keywords for auto-identifying persona from user queries
PERSONA_DETECTION_KEYWORDS: dict[PersonaType, list[str]] = {
    PersonaType.MEDICAL_STUDENT: [
        "studying", "exam", "board", "usmle", "step 1", "step 2",
        "rotation", "clerkship", "med school", "medical student",
    ],
    PersonaType.CLINICIAN: [
        "my patient", "clinical practice", "prescribe", "treatment plan",
        "differential", "presenting with", "chief complaint", "attending",
    ],
    PersonaType.PHARMACIST: [
        "drug interaction", "formulary", "dispensing", "pharmacist",
        "contraindication", "dosing", "pharmacy",
    ],
    PersonaType.RESEARCHER: [
        "systematic review", "meta-analysis", "methodology", "p-value",
        "sample size", "study design", "literature review", "hypothesis",
    ],
    PersonaType.LECTURER: [
        "lecture", "teaching", "curriculum", "slides", "students",
        "course", "seminar", "tutorial",
    ],
    PersonaType.PHYSIOTHERAPIST: [
        "rehab", "rehabilitation", "physiotherapy", "physical therapy",
        "range of motion", "functional outcome", "exercise protocol",
    ],
    PersonaType.PATIENT: [
        "i have", "i was diagnosed", "my doctor said", "should i take",
        "is it safe", "i'm worried", "symptoms", "my condition",
    ],
}


def detect_persona_from_query(query: str) -> PersonaType:
    """
    Simple keyword-based persona detection from a user's query.
    MVP implementation. Will be enhanced with LLM classification later.
    """
    query_lower = query.lower()
    scores: dict[PersonaType, int] = {}

    for persona, keywords in PERSONA_DETECTION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in query_lower)
        if score > 0:
            scores[persona] = score

    if not scores:
        return PersonaType.GENERAL

    return max(scores, key=scores.get)
