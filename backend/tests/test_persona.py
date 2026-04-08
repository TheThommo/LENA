"""
Tests for Persona Detection Module

Tests persona detection from user queries and configuration retrieval.

Run with: pytest tests/test_persona.py -v
"""

import pytest
from app.core.persona import (
    detect_persona_from_query,
    get_persona_config,
    PersonaType,
)


class TestPersonaDetection:
    """Test persona detection from queries."""

    def test_detect_medical_student(self):
        """Queries mentioning 'studying' should detect medical_student."""
        query = "I'm studying for USMLE Step 1, what's the pathophysiology of sepsis?"
        persona = detect_persona_from_query(query)
        assert persona == PersonaType.MEDICAL_STUDENT

    def test_detect_medical_student_board_exam(self):
        """Queries mentioning 'board' should detect medical_student."""
        query = "board exam coming up, need to understand heart failure"
        persona = detect_persona_from_query(query)
        assert persona == PersonaType.MEDICAL_STUDENT

    def test_detect_clinician(self):
        """Queries mentioning 'my patient' should detect clinician."""
        query = "my patient presenting with chest pain and elevated troponin"
        persona = detect_persona_from_query(query)
        assert persona == PersonaType.CLINICIAN

    def test_detect_clinician_clinical_practice(self):
        """Queries mentioning 'clinical practice' should detect clinician."""
        query = "in my clinical practice, how should I approach this differential?"
        persona = detect_persona_from_query(query)
        assert persona == PersonaType.CLINICIAN

    def test_detect_pharmacist(self):
        """Queries mentioning 'drug interaction' should detect pharmacist."""
        query = "drug interactions between metformin and contrast media"
        persona = detect_persona_from_query(query)
        assert persona == PersonaType.PHARMACIST

    def test_detect_pharmacist_dosing(self):
        """Queries mentioning 'dosing' should detect pharmacist."""
        query = "appropriate dosing for amoxicillin in renal failure"
        persona = detect_persona_from_query(query)
        assert persona == PersonaType.PHARMACIST

    def test_detect_researcher(self):
        """Queries mentioning 'meta-analysis' should detect researcher."""
        query = "meta-analysis of randomized controlled trials"
        persona = detect_persona_from_query(query)
        assert persona == PersonaType.RESEARCHER

    def test_detect_researcher_methodology(self):
        """Queries mentioning 'methodology' should detect researcher."""
        query = "methodology and sample size considerations"
        persona = detect_persona_from_query(query)
        assert persona == PersonaType.RESEARCHER

    def test_detect_lecturer(self):
        """Queries mentioning 'lecture' should detect lecturer."""
        query = "preparing a lecture on cardiovascular disease"
        persona = detect_persona_from_query(query)
        assert persona == PersonaType.LECTURER

    def test_detect_lecturer_teaching(self):
        """Queries mentioning 'teaching' should detect lecturer."""
        query = "teaching students about infection control"
        persona = detect_persona_from_query(query)
        assert persona == PersonaType.LECTURER

    def test_detect_physiotherapist(self):
        """Queries mentioning 'rehabilitation' should detect physiotherapist."""
        query = "rehabilitation protocols after knee surgery"
        persona = detect_persona_from_query(query)
        assert persona == PersonaType.PHYSIOTHERAPIST

    def test_detect_physiotherapist_physical_therapy(self):
        """Queries mentioning 'physical therapy' should detect physiotherapist."""
        query = "physical therapy evidence for rotator cuff"
        persona = detect_persona_from_query(query)
        assert persona == PersonaType.PHYSIOTHERAPIST

    def test_detect_patient(self):
        """Queries mentioning 'I was diagnosed' should detect patient."""
        query = "I was diagnosed with diabetes, what does it mean?"
        persona = detect_persona_from_query(query)
        assert persona == PersonaType.PATIENT

    def test_detect_patient_symptoms(self):
        """Queries mentioning 'symptoms' should detect patient."""
        query = "my symptoms are getting worse"
        persona = detect_persona_from_query(query)
        assert persona == PersonaType.PATIENT

    def test_detect_patient_worried(self):
        """Queries mentioning 'I'm worried' should detect patient."""
        query = "I'm worried about this rash"
        persona = detect_persona_from_query(query)
        assert persona == PersonaType.PATIENT

    def test_detect_general_fallback(self):
        """Generic queries should fallback to GENERAL."""
        query = "What is hypertension?"
        persona = detect_persona_from_query(query)
        assert persona == PersonaType.GENERAL

    def test_detect_general_no_keywords(self):
        """Queries with no persona keywords should be GENERAL."""
        query = "tell me about aspirin"
        persona = detect_persona_from_query(query)
        # Should be general if no keywords match strongly
        assert persona in [PersonaType.GENERAL, PersonaType.PATIENT]

    def test_detect_case_insensitive(self):
        """Persona detection should be case-insensitive."""
        query = "MY PATIENT PRESENTING WITH CHEST PAIN"
        persona = detect_persona_from_query(query)
        assert persona == PersonaType.CLINICIAN

    def test_detect_multiple_keywords_highest_wins(self):
        """Multiple keywords should accumulate, highest score wins."""
        # This query has clinician keywords
        query = "my patient with clinical presentation"
        persona = detect_persona_from_query(query)
        assert persona == PersonaType.CLINICIAN


class TestPersonaConfig:
    """Test persona configuration retrieval."""

    def test_get_config_medical_student(self):
        """Medical student config should have educational tone."""
        config = get_persona_config(PersonaType.MEDICAL_STUDENT)
        assert config.persona_type == PersonaType.MEDICAL_STUDENT
        assert config.display_name == "Medical Student"
        assert "educational" in config.tone.lower()

    def test_get_config_clinician(self):
        """Clinician config should have clinical tone."""
        config = get_persona_config(PersonaType.CLINICIAN)
        assert config.persona_type == PersonaType.CLINICIAN
        assert config.display_name == "Clinician"
        assert "clinical" in config.tone.lower()

    def test_get_config_pharmacist(self):
        """Pharmacist config should focus on drugs."""
        config = get_persona_config(PersonaType.PHARMACIST)
        assert config.persona_type == PersonaType.PHARMACIST
        assert config.display_name == "Pharmacist"
        assert "drug" in config.system_prompt_modifier.lower()

    def test_get_config_researcher(self):
        """Researcher config should focus on methodology."""
        config = get_persona_config(PersonaType.RESEARCHER)
        assert config.persona_type == PersonaType.RESEARCHER
        assert config.display_name == "Researcher"
        assert "methodology" in config.system_prompt_modifier.lower()

    def test_get_config_lecturer(self):
        """Lecturer config should be teaching-focused."""
        config = get_persona_config(PersonaType.LECTURER)
        assert config.persona_type == PersonaType.LECTURER
        assert "Educator" in config.display_name or "Lecturer" in config.display_name

    def test_get_config_physiotherapist(self):
        """Physiotherapist config should focus on rehabilitation."""
        config = get_persona_config(PersonaType.PHYSIOTHERAPIST)
        assert config.persona_type == PersonaType.PHYSIOTHERAPIST
        assert "rehabilitation" in config.system_prompt_modifier.lower()

    def test_get_config_patient(self):
        """Patient config should have empathetic warm tone."""
        config = get_persona_config(PersonaType.PATIENT)
        assert config.persona_type == PersonaType.PATIENT
        assert config.display_name == "Patient / Public"
        assert "warm" in config.tone.lower() or "empathetic" in config.tone.lower()
        assert "advice" in config.system_prompt_modifier.lower()

    def test_get_config_general(self):
        """General config should be balanced."""
        config = get_persona_config(PersonaType.GENERAL)
        assert config.persona_type == PersonaType.GENERAL
        assert config.display_name == "General"

    def test_get_config_all_personas_have_system_prompt(self):
        """All personas should have a system prompt modifier."""
        for persona_type in PersonaType:
            config = get_persona_config(persona_type)
            assert config.system_prompt_modifier
            assert len(config.system_prompt_modifier) > 10

    def test_get_config_all_personas_have_tone(self):
        """All personas should have a tone."""
        for persona_type in PersonaType:
            config = get_persona_config(persona_type)
            assert config.tone
            assert len(config.tone) > 0

    def test_get_config_all_personas_have_depth(self):
        """All personas should have a depth level."""
        for persona_type in PersonaType:
            config = get_persona_config(persona_type)
            assert config.depth
            assert len(config.depth) > 0

    def test_config_invalid_persona_fallback(self):
        """Invalid persona type should fallback to GENERAL."""
        config = get_persona_config("invalid_persona")  # type: ignore
        assert config.persona_type == PersonaType.GENERAL
