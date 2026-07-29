"""
Internal PULSE eval endpoints — use the server's chat LLM key (Railway).

Rate-limited so a public caller cannot freely burn credits. Intended for
cloud-agent / CI verification when the agent env has no local key.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger("lena.pulse_eval")

router = APIRouter(prefix="/internal", tags=["internal"])

# Soft rate limit: enough for golden (19) + holdout (8) with headroom, not a free LLM proxy.
_MAX_GRADE_PER_HOUR = 80
_MAX_SUITE_PER_HOUR = 4
_grade_hits: list[float] = []
_suite_hits: list[float] = []
_suite_lock = asyncio.Lock()
_suite_cache: dict[str, dict[str, Any]] = {}


def _prune(hits: list[float], window_s: float = 3600.0) -> None:
    cutoff = time.time() - window_s
    while hits and hits[0] < cutoff:
        hits.pop(0)


def _allow(hits: list[float], limit: int) -> bool:
    _prune(hits)
    if len(hits) >= limit:
        return False
    hits.append(time.time())
    return True


def _mirror_llm_env() -> None:
    """Ensure evals.rubric / SDKs see keys from Settings."""
    if settings.openai_api_key:
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
    if settings.anthropic_api_key:
        os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)
    os.environ.setdefault("LLM_PROVIDER", settings.llm_provider or "anthropic")
    os.environ.setdefault("LLM_MODEL", settings.llm_model or "claude-sonnet-5")


class GradeRequest(BaseModel):
    query: str
    persona: str = "general"
    answer_key: dict[str, Any] = Field(default_factory=dict)
    brief: str = ""


@router.post("/pulse-grade")
async def pulse_grade(body: GradeRequest):
    """Grade one brief with the server chat LLM key."""
    if not settings.chat_configured:
        raise HTTPException(
            status_code=503,
            detail="No chat LLM key configured (ANTHROPIC_API_KEY or OPENAI_API_KEY)",
        )
    if not _allow(_grade_hits, _MAX_GRADE_PER_HOUR):
        raise HTTPException(status_code=429, detail="pulse-grade rate limit exceeded")

    _mirror_llm_env()
    from evals.rubric import grade_rubric_llm

    result = await grade_rubric_llm(
        query=body.query,
        persona=body.persona,
        answer_key=body.answer_key,
        brief=body.brief,
    )
    out = result.to_dict()
    out["provider"] = settings.chat_provider
    out["model"] = settings.chat_model
    return out


@router.post("/pulse-eval")
@router.get("/pulse-eval")
async def pulse_eval(
    suite: Literal["golden", "holdout"] = Query("holdout"),
    case: Optional[str] = Query(None),
    force: bool = Query(False, description="Bypass cache and re-run"),
):
    """
    Run a PULSE suite on this host (uses Railway chat LLM for rubric grading).
    Cached per suite(+case) for one hour unless force=1.
    """
    if not settings.chat_configured:
        raise HTTPException(
            status_code=503,
            detail="No chat LLM key configured (ANTHROPIC_API_KEY or OPENAI_API_KEY)",
        )

    cache_key = f"{suite}:{case or '*'}"
    if not force and cache_key in _suite_cache:
        cached = _suite_cache[cache_key]
        if time.time() - cached["ts"] < 3600:
            return {**cached["payload"], "cached": True}

    if not _allow(_suite_hits, _MAX_SUITE_PER_HOUR):
        raise HTTPException(status_code=429, detail="pulse-eval rate limit exceeded")

    async with _suite_lock:
        import sys
        from pathlib import Path

        _mirror_llm_env()
        # Avoid recursive remote-grade when the suite runs on Railway itself.
        os.environ["PULSE_GRADE_REMOTE"] = "0"

        # evals/ is sibling of app/ in the image (/app/evals)
        root = Path(__file__).resolve().parents[3]  # /app
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))

        from evals.runner import format_report, run_suite

        results = await run_suite(suite, case_filter=case)
        report = format_report(results, suite)
        n_pass = sum(1 for r in results if r.passed)
        floors_ok = sum(
            1
            for r in results
            if r.assertion_results and all(a.passed for a in r.assertion_results)
        )
        rubric_scores = [r.rubric.overall for r in results if r.rubric]
        avg = sum(rubric_scores) / len(rubric_scores) if rubric_scores else 0.0
        modes = sorted({(r.rubric.mode if r.rubric else "?") for r in results})

        payload: dict[str, Any] = {
            "suite": suite,
            "pass": n_pass,
            "total": len(results),
            "floors_ok": floors_ok,
            "rubric_avg": round(avg, 1),
            "rubric_modes": modes,
            "provider": settings.chat_provider,
            "model": settings.chat_model,
            "openai_configured": bool(settings.openai_api_key),
            "anthropic_configured": bool(settings.anthropic_api_key),
            "report": report,
            "cases": [
                {
                    "id": r.case_id,
                    "passed": r.passed,
                    "persona": r.persona,
                    "confidence": r.confidence,
                    "status": r.status,
                    "rubric_overall": r.rubric.overall if r.rubric else None,
                    "rubric_mode": r.rubric.mode if r.rubric else None,
                    "rubric_scores": r.rubric.scores if r.rubric else None,
                    "rubric_detail": r.rubric.detail if r.rubric else None,
                    "floor_pass": bool(
                        r.assertion_results
                        and all(a.passed for a in r.assertion_results)
                    ),
                    "floor_fails": [
                        {
                            "name": a.name,
                            "detail": a.detail,
                            "defect_id": a.defect_id,
                        }
                        for a in (r.assertion_results or [])
                        if not a.passed
                    ],
                    "lead": (r.brief or "").strip().splitlines()[:1][0][:200]
                    if (r.brief or "").strip()
                    else "",
                }
                for r in results
            ],
        }
        _suite_cache[cache_key] = {"ts": time.time(), "payload": payload}
        logger.info(
            "pulse-eval suite=%s provider=%s model=%s pass=%s/%s floors=%s rubric_avg=%.1f",
            suite,
            settings.chat_provider,
            settings.chat_model,
            n_pass,
            len(results),
            floors_ok,
            avg,
        )
        return {**payload, "cached": False}
