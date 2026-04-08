"""
Tests for Topic Classifier Module

Tests classification of medical queries into specialty categories.

Run with: pytest tests/test_topic_classifier.py -v
"""

import pytest
from app.services.topic_classifier import classify_query_topic


class TestTopicClassification:
    """Test query classification into topics."""

    # ===== Cardiovascular =====
    def test_classify_heart_failure(self):
        """Query about heart failure should match cardiovascular."""
        topics = classify_query_topic("heart failure treatment")
        assert "cardiovascular" in topics

    def test_classify_cardiac(self):
        """Query about cardiac should match cardiovascular."""
        topics = classify_query_topic("cardiac arrhythmia")
        assert "cardiovascular" in topics

    def test_classify_hypertension(self):
        """Query about hypertension should match cardiovascular."""
        topics = classify_query_topic("hypertension management")
        assert "cardiovascular" in topics

    def test_classify_stroke(self):
        """Query about stroke should match cardiovascular."""
        topics = classify_query_topic("stroke prevention")
        assert "cardiovascular" in topics

    # ===== Oncology =====
    def test_classify_cancer(self):
        """Query about cancer should match oncology."""
        topics = classify_query_topic("cancer treatment options")
        assert "oncology" in topics

    def test_classify_tumor(self):
        """Query about tumor should match oncology."""
        topics = classify_query_topic("tumor biopsy")
        assert "oncology" in topics

    def test_classify_chemotherapy(self):
        """Query about chemotherapy should match oncology."""
        topics = classify_query_topic("chemotherapy side effects")
        assert "oncology" in topics

    # ===== Neurology =====
    def test_classify_alzheimer(self):
        """Query about Alzheimer's should match neurology."""
        topics = classify_query_topic("Alzheimer's disease")
        assert "neurology" in topics

    def test_classify_parkinson(self):
        """Query about Parkinson's should match neurology."""
        topics = classify_query_topic("Parkinson's progression")
        assert "neurology" in topics

    def test_classify_seizure(self):
        """Query about seizure should match neurology."""
        topics = classify_query_topic("seizure management")
        assert "neurology" in topics

    def test_classify_migraine(self):
        """Query about migraine should match neurology."""
        topics = classify_query_topic("migraine prevention")
        assert "neurology" in topics

    # ===== Infectious Disease =====
    def test_classify_infection(self):
        """Query about infection should match infectious_disease."""
        topics = classify_query_topic("bacterial infection treatment")
        assert "infectious_disease" in topics

    def test_classify_covid(self):
        """Query about COVID should match infectious_disease."""
        topics = classify_query_topic("COVID-19 variants")
        assert "infectious_disease" in topics

    def test_classify_pneumonia(self):
        """Query about pneumonia should match infectious_disease."""
        topics = classify_query_topic("pneumonia antibiotics")
        assert "infectious_disease" in topics

    def test_classify_hiv(self):
        """Query about HIV should match infectious_disease."""
        topics = classify_query_topic("HIV treatment")
        assert "infectious_disease" in topics

    # ===== Mental Health =====
    def test_classify_depression(self):
        """Query about depression should match mental_health."""
        topics = classify_query_topic("depression treatment")
        assert "mental_health" in topics

    def test_classify_anxiety(self):
        """Query about anxiety should match mental_health."""
        topics = classify_query_topic("anxiety disorders")
        assert "mental_health" in topics

    def test_classify_bipolar(self):
        """Query about bipolar should match mental_health."""
        topics = classify_query_topic("bipolar disorder")
        assert "mental_health" in topics

    def test_classify_ptsd(self):
        """Query about PTSD should match mental_health."""
        topics = classify_query_topic("PTSD therapy")
        assert "mental_health" in topics

    # ===== Pediatrics =====
    def test_classify_child(self):
        """Query about child should match pediatrics."""
        topics = classify_query_topic("child development")
        assert "pediatrics" in topics

    def test_classify_infant(self):
        """Query about infant should match pediatrics."""
        topics = classify_query_topic("infant vaccination")
        assert "pediatrics" in topics

    def test_classify_autism(self):
        """Query about autism should match pediatrics."""
        topics = classify_query_topic("autism spectrum disorder")
        assert "pediatrics" in topics

    # ===== Orthopedics =====
    def test_classify_fracture(self):
        """Query about fracture should match orthopedics."""
        topics = classify_query_topic("bone fracture")
        assert "orthopedics" in topics

    def test_classify_arthritis(self):
        """Query about arthritis should match orthopedics."""
        topics = classify_query_topic("arthritis treatment")
        assert "orthopedics" in topics

    def test_classify_knee_injury(self):
        """Query about knee should match orthopedics."""
        topics = classify_query_topic("knee ligament injury")
        assert "orthopedics" in topics

    # ===== Dermatology =====
    def test_classify_skin(self):
        """Query about skin should match dermatology."""
        topics = classify_query_topic("skin disease")
        assert "dermatology" in topics

    def test_classify_psoriasis(self):
        """Query about psoriasis should match dermatology."""
        topics = classify_query_topic("psoriasis treatment")
        assert "dermatology" in topics

    def test_classify_acne(self):
        """Query about acne should match dermatology."""
        topics = classify_query_topic("acne scars")
        assert "dermatology" in topics

    # ===== Endocrinology =====
    def test_classify_diabetes(self):
        """Query about diabetes should match endocrinology."""
        topics = classify_query_topic("diabetes management")
        assert "endocrinology" in topics

    def test_classify_thyroid(self):
        """Query about thyroid should match endocrinology."""
        topics = classify_query_topic("thyroid disease")
        assert "endocrinology" in topics

    def test_classify_hormone(self):
        """Query about hormone should match endocrinology."""
        topics = classify_query_topic("hormone therapy")
        assert "endocrinology" in topics

    # ===== Respiratory =====
    def test_classify_asthma(self):
        """Query about asthma should match respiratory."""
        topics = classify_query_topic("asthma control")
        assert "respiratory" in topics

    def test_classify_lung(self):
        """Query about lung should match respiratory."""
        topics = classify_query_topic("lung disease")
        assert "respiratory" in topics

    def test_classify_copd(self):
        """Query about COPD should match respiratory."""
        topics = classify_query_topic("COPD exacerbation")
        assert "respiratory" in topics

    # ===== Gastroenterology =====
    def test_classify_stomach(self):
        """Query about stomach should match gastroenterology."""
        topics = classify_query_topic("stomach ulcer")
        assert "gastroenterology" in topics

    def test_classify_ibd(self):
        """Query about IBD should match gastroenterology."""
        topics = classify_query_topic("inflammatory bowel disease")
        assert "gastroenterology" in topics

    def test_classify_gerd(self):
        """Query about GERD should match gastroenterology."""
        topics = classify_query_topic("acid reflux treatment")
        assert "gastroenterology" in topics

    # ===== Alternative Medicine =====
    def test_classify_herbal(self):
        """Query about herbal should match alternative_medicine."""
        topics = classify_query_topic("herbal medicine")
        assert "alternative_medicine" in topics

    def test_classify_acupuncture(self):
        """Query about acupuncture should match alternative_medicine."""
        topics = classify_query_topic("acupuncture for pain")
        assert "alternative_medicine" in topics

    def test_classify_supplements(self):
        """Query about supplements should match alternative_medicine."""
        topics = classify_query_topic("supplement efficacy")
        assert "alternative_medicine" in topics

    def test_classify_turmeric(self):
        """Query about turmeric should match alternative_medicine."""
        topics = classify_query_topic("turmeric herbal remedy")
        assert "alternative_medicine" in topics

    # ===== Fitness & Wellness =====
    def test_classify_exercise(self):
        """Query about exercise should match fitness_wellness."""
        topics = classify_query_topic("exercise benefits")
        assert "fitness_wellness" in topics

    def test_classify_yoga(self):
        """Query about yoga should match fitness_wellness."""
        topics = classify_query_topic("yoga for anxiety")
        assert "fitness_wellness" in topics

    def test_classify_fitness(self):
        """Query about fitness should match fitness_wellness."""
        topics = classify_query_topic("fitness training")
        assert "fitness_wellness" in topics

    # ===== Nutrition =====
    def test_classify_diet(self):
        """Query about diet should match nutrition."""
        topics = classify_query_topic("diet for diabetes")
        assert "nutrition" in topics

    def test_classify_vitamin(self):
        """Query about vitamin should match nutrition."""
        topics = classify_query_topic("vitamin deficiency")
        assert "nutrition" in topics

    def test_classify_protein(self):
        """Query about protein should match nutrition."""
        topics = classify_query_topic("protein requirements")
        assert "nutrition" in topics


class TestMultipleTopics:
    """Test queries that match multiple topics."""

    def test_multiple_topics_yoga_anxiety(self):
        """Yoga for anxiety should match both fitness_wellness and mental_health."""
        topics = classify_query_topic("yoga for anxiety treatment")
        assert "fitness_wellness" in topics
        assert "mental_health" in topics

    def test_multiple_topics_exercise_heart(self):
        """Exercise for heart should match both fitness_wellness and cardiovascular."""
        topics = classify_query_topic("exercise for heart health")
        assert "fitness_wellness" in topics
        assert "cardiovascular" in topics

    def test_multiple_topics_diet_diabetes(self):
        """Diet for diabetes should match both nutrition and endocrinology."""
        topics = classify_query_topic("diet management diabetes")
        assert "nutrition" in topics
        assert "endocrinology" in topics


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_query(self):
        """Empty query should return general or empty."""
        topics = classify_query_topic("")
        # Should either be empty or default to general
        assert isinstance(topics, list)

    def test_whitespace_only(self):
        """Whitespace-only query should return empty or general."""
        topics = classify_query_topic("   ")
        assert isinstance(topics, list)

    def test_no_matching_topics(self):
        """Query with no matches should include 'general'."""
        topics = classify_query_topic("asdfghjkl zxcvbnm")
        # Should default to general if nothing matches
        assert "general" in topics or len(topics) == 0

    def test_case_insensitive(self):
        """Classification should be case-insensitive."""
        topics_lower = classify_query_topic("heart failure")
        topics_upper = classify_query_topic("HEART FAILURE")
        assert set(topics_lower) == set(topics_upper)

    def test_punctuation_handling(self):
        """Should handle punctuation correctly."""
        topics_with_punct = classify_query_topic("heart failure? treatment!")
        topics_without = classify_query_topic("heart failure treatment")
        assert set(topics_with_punct) == set(topics_without)

    def test_partial_keyword_match(self):
        """Should match partial keywords (substring match)."""
        topics = classify_query_topic("cardiomyopathy")
        # 'cardiac' is in 'cardiomyopathy', should match cardiovascular
        assert "cardiovascular" in topics
