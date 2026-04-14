"""
Outlier Authors Service

Loads backend/app/data/outlier_authors.json (peer-reviewed authors whose
work often diverges from mainstream consensus) and provides a matcher
against result authors.

Matching strategy: last-name + first-initial (case-insensitive). This is
the canonical disambiguation PubMed itself uses ("McCullough PA") and
tolerates variance between sources (e.g. "Peter A. McCullough" in
OpenAlex vs "McCullough PA" in PubMed).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from functools import lru_cache
from typing import Iterable

from app.core.logging import get_logger

logger = get_logger("lena.outlier_authors")


_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "outlier_authors.json"


def _normalise_key(last: str, first_initial: str) -> str:
    return f"{last.lower().strip()}|{first_initial.lower().strip()}"


def _name_to_key(full_name: str) -> str | None:
    """Extract (lastname, first-initial) from a name string.

    Handles both "Peter A. McCullough" and "McCullough PA" / "McCullough P".
    Returns None if a key can't be produced.
    """
    if not full_name:
        return None
    # Strip punctuation except spaces and hyphens
    cleaned = re.sub(r"[^\w\s\-]", " ", full_name).strip()
    parts = [p for p in cleaned.split() if p]
    if len(parts) < 2:
        return None

    # Heuristic: if last token is ALL CAPS or 1-3 letters, treat as PubMed
    # format "LastName Initials" ("McCullough PA").
    last_tok = parts[-1]
    if last_tok.isupper() and len(last_tok) <= 4:
        last = parts[0]
        first_initial = last_tok[0]
    else:
        # Treat as Western "First [Middle] Last"
        last = parts[-1]
        first_initial = parts[0][0]
    return _normalise_key(last, first_initial)


@lru_cache(maxsize=1)
def _load_index() -> tuple[dict[str, dict], dict]:
    """Load outlier_authors.json and build a lookup index."""
    try:
        raw = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning(f"outlier_authors.json not found at {_DATA_PATH}")
        return ({}, {})
    except Exception as e:
        logger.error(f"Failed to parse outlier_authors.json: {e}")
        return ({}, {})

    index: dict[str, dict] = {}
    for tier_key in ("tier_1_extensive", "tier_2_some_publications"):
        for entry in raw.get(tier_key, []):
            key = _name_to_key(entry.get("name", ""))
            if key:
                index[key] = {
                    "name": entry.get("name"),
                    "tier": tier_key,
                    "credentials": entry.get("credentials"),
                    "specialties": entry.get("specialties", []),
                    "notes": entry.get("notes", ""),
                }
    return (index, raw)


def result_authors_match_outlier(authors: Iterable[str]) -> list[dict]:
    """Return outlier-author metadata dicts for any authors on a result.

    Empty list means no match.
    """
    index, _ = _load_index()
    if not index or not authors:
        return []
    hits: dict[str, dict] = {}
    for author in authors:
        key = _name_to_key(author)
        if key and key in index:
            hits[key] = index[key]
    return list(hits.values())


def is_outlier_result(authors: Iterable[str]) -> bool:
    """True if any author on the result is in the outlier list."""
    return bool(result_authors_match_outlier(authors))


def get_outlier_metadata() -> dict:
    """Expose the raw JSON for admin/debug endpoints."""
    _, raw = _load_index()
    return raw
