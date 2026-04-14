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


def _name_to_keys(full_name: str) -> set[str]:
    """Extract all plausible (lastname, first-initial) keys from a name.

    Real-world variants we must handle simultaneously:
        "Peter A. McCullough"         — Western ordering (OpenAlex, bios)
        "McCullough PA"               — PubMed "LastName Initials"
        "McCullough Peter A"          — PubMed expanded form (LENA's PubMed parser emits this)
        "McCullough, P."              — bibliographic comma form
        "Peter McCullough"            — no middle initial

    We return ALL candidate keys rather than guess at ordering, because
    a wrong guess silently drops the match. The index is indexed the same
    way, so any overlap in the candidate set is a real hit.
    """
    if not full_name:
        return set()
    cleaned = re.sub(r"[^\w\s\-]", " ", full_name).strip()
    parts = [p for p in cleaned.split() if p]
    if len(parts) < 2:
        return set()

    keys: set[str] = set()

    def _looks_like_initials(tok: str) -> bool:
        return tok.isupper() and 1 <= len(tok) <= 4

    # Candidate 1: Western — first token is given name, last token is surname
    keys.add(_normalise_key(parts[-1], parts[0][0]))

    # Candidate 2: PubMed 2-token — "Surname Initials"
    if len(parts) == 2 and _looks_like_initials(parts[1]):
        keys.add(_normalise_key(parts[0], parts[1][0]))

    # Candidate 3: PubMed expanded — "Surname Given [MiddleInitial]"
    # Trailing token is short+upper → treat preceding token as the given name.
    if len(parts) >= 3 and _looks_like_initials(parts[-1]):
        # first_initial from parts[1] (given name), surname from parts[0]
        keys.add(_normalise_key(parts[0], parts[1][0]))

    return keys


def _name_to_key(full_name: str) -> str | None:
    """Back-compat: return one representative key (Western form)."""
    keys = _name_to_keys(full_name)
    return next(iter(keys), None) if keys else None


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
            meta = {
                "name": entry.get("name"),
                "tier": tier_key,
                "credentials": entry.get("credentials"),
                "specialties": entry.get("specialties", []),
                "notes": entry.get("notes", ""),
            }
            # Index under every plausible key form so incoming authors
            # can be matched regardless of ordering convention.
            for key in _name_to_keys(entry.get("name", "")):
                index[key] = meta
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
        for key in _name_to_keys(author):
            if key in index:
                hits[key] = index[key]
                break
    return list(hits.values())


def is_outlier_result(authors: Iterable[str]) -> bool:
    """True if any author on the result is in the outlier list."""
    return bool(result_authors_match_outlier(authors))


def get_outlier_metadata() -> dict:
    """Expose the raw JSON for admin/debug endpoints."""
    _, raw = _load_index()
    return raw
