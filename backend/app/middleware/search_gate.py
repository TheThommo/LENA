"""
Search Gate Middleware

Enforces demo freemium limits on the /api/search/ endpoints.

Rules (demo mode 2026-04-18):
- Authenticated user: allow up to free_search_limit_registered per rolling
  24h. Above limit -> pro_required CTA. (Pro cap is enforced by billing
  once Stripe is live - not by this middleware.)
- Anonymous visitor: identified by an IP+UA fingerprint hash, plus the
  JS session cookie when present. Allowed: 1 free search AFTER
  acknowledging the disclaimer inline. The fingerprint makes the gate
  refresh / incognito resistant.
- No session token at all: the very first /api/search lands here. We
  auto-create a fingerprint row and return a disclaimer_required
  guardrail the frontend renders as a LENA chat message.
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID
from typing import Callable, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse

from app.db.repositories.session_repo import SessionRepository
from app.db.repositories.anon_fingerprint_repo import (
    AnonFingerprintRepository,
    compute_fingerprint,
)
from app.db.supabase import get_supabase_admin_client
from app.models import SessionUpdate
from app.services.funnel_tracker import track_funnel_stage

logger = logging.getLogger(__name__)


def _client_ip(request: Request) -> str:
    """Best-effort client IP extraction. Honours X-Forwarded-For then falls
    back to the direct socket. Railway/edge proxies set XFF, so prefer it."""
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP", "")
    if real_ip:
        return real_ip.strip()
    if request.client and request.client.host:
        return request.client.host
    return ""


async def _registered_search_count_last_24h(user_id: str) -> int:
    """Count registered user's searches in the last 24h window via
    search_logs. Cheap: indexed on (user_id, created_at)."""
    client = get_supabase_admin_client()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    try:
        resp = (
            client.table("search_logs")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .gte("created_at", cutoff)
            .execute()
        )
        return resp.count or 0
    except Exception as e:
        logger.warning(f"registered 24h count failed (non-blocking): {e}")
        return 0


def _guardrail_response(
    guardrail_type: str,
    guardrail_msg: str,
    query: str,
) -> JSONResponse:
    """
    Build a complete guardrail response that satisfies the frontend
    SearchResponse interface. Every field the frontend might access
    (sources_queried, sources_failed, total_results, etc.) must be
    present to avoid "Cannot read properties of undefined" crashes.
    """
    return JSONResponse(
        status_code=200,
        content={
            "search_id": None,
            "session_id": None,
            "query": query,
            "persona": {"detected": "general", "display_name": "General", "tone": "", "depth": ""},
            "guardrail_triggered": True,
            "guardrail_type": guardrail_type,
            "guardrail_message": guardrail_msg,
            "llm_summary": None,
            "pulse_report": None,
            "sources_queried": [],
            "sources_failed": {},
            "total_results": 0,
            "response_time_ms": 0,
        },
    )


def _extract_bearer_token(request: Request) -> Optional[str]:
    """Extract the raw Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


def _try_decode_jwt(token: str) -> Optional[dict]:
    """
    Try to decode the token as a LENA JWT.
    Returns the payload dict if valid, None otherwise.
    """
    try:
        from app.core.auth import verify_token
        return verify_token(token)
    except Exception:
        return None


def extract_session_id(request: Request) -> Optional[str]:
    """
    Extract session ID from Authorization header or X-Session-ID header.
    Token format: "session_{uuid}" or "session_{uuid}_authorized"
    """
    # Check Authorization header (Bearer token)
    token = _extract_bearer_token(request)
    if token and token.startswith("session_"):
        # Extract UUID from "session_{uuid}" or "session_{uuid}_authorized"
        parts = token.split("_")
        if len(parts) >= 2:
            try:
                return str(UUID(parts[1]))
            except (ValueError, IndexError):
                pass

    # Check X-Session-ID header
    session_id_header = request.headers.get("X-Session-ID", "")
    if session_id_header:
        try:
            return str(UUID(session_id_header))
        except ValueError:
            pass

    return None


class SearchGateMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces freemium search limits.
    Only applies to /api/search/ endpoints.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check search gate before allowing request."""

        # Only apply to search endpoints (skip OPTIONS preflight requests)
        if not request.url.path.startswith("/api/search") or request.method == "OPTIONS":
            return await call_next(request)

        from app.core.config import settings as _settings

        # ── Pre-auth guardrails ──────────────────────────────────────
        # Self-harm, profanity, and off-topic checks run BEFORE session
        # validation so they work for anonymous visitors who haven't
        # completed the disclaimer. These are hard blocks — no search
        # runs, no session needed.
        query_param = request.query_params.get("q", "")
        if query_param:
            from app.core.guardrails import run_all_guardrails
            guardrail_type, guardrail_msg = run_all_guardrails(query_param)
            if guardrail_type and guardrail_type != "medical_advice":
                return _guardrail_response(guardrail_type, guardrail_msg, query_param)

        # ── Authenticated (JWT) path ──
        bearer = _extract_bearer_token(request)
        if bearer and not bearer.startswith("session_"):
            jwt_payload = _try_decode_jwt(bearer)
            if jwt_payload and jwt_payload.get("user_id"):
                user_id_str = str(jwt_payload["user_id"])
                request.state.user_id = user_id_str

                # 24h rolling quota for registered (demo free tier).
                used = await _registered_search_count_last_24h(user_id_str)
                reg_limit = _settings.free_search_limit_registered
                if used >= reg_limit:
                    return _guardrail_response(
                        "registered_limit",
                        f"You've used your **{reg_limit} free searches** in the last 24 hours.\n\n"
                        "Upgrade to **Pro** for unlimited searches, saved results, project folders, "
                        "and export. Your free tier resets daily - come back tomorrow if you'd like.",
                        query_param,
                    )

                # Link session if present (so admin funnel counts stay accurate).
                session_id = extract_session_id(request)
                if session_id:
                    try:
                        session = await SessionRepository.get_by_id(UUID(session_id))
                        if session:
                            new_count = (session.search_count or 0) + 1
                            await SessionRepository.update(
                                UUID(session_id),
                                SessionUpdate(search_count=new_count),
                            )
                            request.state.session_id = session_id
                            request.state.session = session
                        else:
                            request.state.session_id = None
                            request.state.session = None
                    except Exception:
                        request.state.session_id = None
                        request.state.session = None
                else:
                    request.state.session_id = None
                    request.state.session = None

                return await call_next(request)

        # ── Anonymous path ──
        # Build the IP+UA fingerprint first. Even if the visitor has no
        # session cookie (first-hit), this gives us a stable row to count
        # against. Refresh / incognito / cleared localStorage all resolve
        # here.
        ip = _client_ip(request)
        ua = request.headers.get("User-Agent", "")
        fp_hash = compute_fingerprint(ip, ua)

        try:
            fp_row = await AnonFingerprintRepository.get_or_create(
                fingerprint_hash=fp_hash, ip_address=ip, user_agent=ua
            )
        except Exception as e:
            logger.warning(f"fingerprint lookup failed (non-blocking): {e}")
            fp_row = {"search_count": 0, "disclaimer_accepted_at": None}

        fp_search_count = int(fp_row.get("search_count") or 0)
        fp_disclaimer = fp_row.get("disclaimer_accepted_at")

        # Session lookup (may be absent on very first hit)
        session_id = extract_session_id(request)
        session = None
        if session_id:
            try:
                session = await SessionRepository.get_by_id(UUID(session_id))
            except Exception:
                session = None

        disclaimer_ok = bool(
            (session and session.disclaimer_accepted_at) or fp_disclaimer
        )

        # Disclaimer required first. Return a LENA-style chat message the
        # frontend renders inline with an "I accept" action.
        if not disclaimer_ok:
            return _guardrail_response(
                "disclaimer_required",
                "Before I dive in, a quick note: I share **research evidence**, not medical "
                "advice. Accept the disclaimer and I'll run your first search on the house.",
                query_param,
            )

        # Free anon quota already spent -> signup CTA.
        anon_limit = _settings.free_search_limit_anon
        if fp_search_count >= anon_limit:
            if session:
                await track_funnel_stage(
                    session_id=str(session.id),
                    tenant_id=str(session.tenant_id),
                    stage="signup_cta_shown",
                )
            return _guardrail_response(
                "signup_required",
                "That was your free preview - hope it was useful!\n\n"
                "**Create a free account** (takes 30 seconds) to keep searching. "
                "You'll get 5 searches a day, saved history, and project folders.",
                query_param,
            )

        # Allowed: increment the fingerprint counter AND the session counter.
        try:
            new_fp_count = await AnonFingerprintRepository.increment_search(fp_hash)
        except Exception as e:
            logger.warning(f"fp increment failed (non-blocking): {e}")
            new_fp_count = fp_search_count + 1

        if session:
            try:
                new_session_count = (session.search_count or 0) + 1
                await SessionRepository.update(
                    UUID(session_id),
                    SessionUpdate(search_count=new_session_count),
                )
                if new_session_count == 1:
                    await track_funnel_stage(
                        session_id=str(session.id),
                        tenant_id=str(session.tenant_id),
                        stage="first_search",
                    )
            except Exception as e:
                logger.warning(f"session increment failed (non-blocking): {e}")

        request.state.session_id = session_id
        request.state.session = session
        request.state.anon_fingerprint = fp_hash
        request.state.anon_search_count = new_fp_count

        return await call_next(request)
