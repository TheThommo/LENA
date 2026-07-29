"""Smoke tests for Railway-backed pulse-eval routes."""

from fastapi.testclient import TestClient

from app.main import app


def test_pulse_eval_requires_openai_key(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "openai_api_key", None)
    client = TestClient(app)
    r = client.get("/api/internal/pulse-eval", params={"suite": "holdout"})
    assert r.status_code == 503


def test_pulse_grade_requires_openai_key(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "openai_api_key", None)
    client = TestClient(app)
    r = client.post(
        "/api/internal/pulse-grade",
        json={"query": "q", "persona": "general", "answer_key": {}, "brief": "b"},
    )
    assert r.status_code == 503
