"""
Simple in-memory per-IP rate limiter.

Used to prevent brute-force against sensitive endpoints such as /auth/login
and /auth/forgot-password. Sliding window tracked per (bucket, ip).

This is in-memory and per-process, so across multiple workers it is lenient by
a factor of N workers — still dramatically better than no gate at all. For
production with >1 worker, prefer a Redis-backed limiter.
"""

import time
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple
from fastapi import HTTPException, Request, status


_BUCKETS: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(request: Request, bucket: str, max_hits: int, window_seconds: int) -> None:
    """Raise HTTP 429 if the caller has exceeded the allowed hits in the window."""
    ip = _client_ip(request)
    key = (bucket, ip)
    now = time.time()

    dq = _BUCKETS[key]
    # Drop entries older than the window
    cutoff = now - window_seconds
    while dq and dq[0] < cutoff:
        dq.popleft()

    if len(dq) >= max_hits:
        retry_after = int(dq[0] + window_seconds - now) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many attempts. Retry in {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )

    dq.append(now)
