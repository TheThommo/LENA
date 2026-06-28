"""Tests for discover/suggestions filtering."""

from app.api.routes.discover import _is_suggestible_query, _project_prompts


def test_rejects_long_personal_health_dump():
    q = (
        "Current health context Diagnosed with hypertension; blood pressure previously "
        "averaged around 142/90. I take magnesium glycinate 200mg daily..."
    )
    assert not _is_suggestible_query(q)


def test_accepts_short_clinical_question():
    assert _is_suggestible_query(
        "What does the evidence say about magnesium for hypertension?"
    )


def test_project_prompts_are_short_and_themed():
    prompts = _project_prompts("Energy", "general")
    assert len(prompts) == 3
    assert all("Energy" in p for p in prompts[:2])
    assert all(len(p) <= 120 for p in prompts)
