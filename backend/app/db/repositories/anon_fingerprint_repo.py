"""
Anonymous Fingerprint Repository.

Backs the IP+UA gate for pre-signup searches. Keeps the gate honest even
if the visitor clears localStorage, opens incognito, or rotates the JS
session token - they still resolve to the same fingerprint row.
"""

import hashlib
from typing import Optional
from datetime import datetime

from app.db.supabase import get_supabase_admin_client
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("lena.anon_fp")


def compute_fingerprint(ip: Optional[str], user_agent: Optional[str]) -> str:
    """Return SHA256 hash of (ip | ua | salt). Missing parts become empty strings."""
    salt = settings.anon_fingerprint_salt or ""
    material = f"{ip or ''}|{user_agent or ''}|{salt}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class AnonFingerprintRepository:
    """CRUD for anon_fingerprints table."""

    @staticmethod
    async def get_or_create(
        fingerprint_hash: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> dict:
        """Return the row for this fingerprint, creating it if absent.

        Uses the service-role client because this table is RLS-protected
        and never readable from the public client.
        """
        client = get_supabase_admin_client()
        existing = (
            client.table("anon_fingerprints")
            .select("*")
            .eq("fingerprint_hash", fingerprint_hash)
            .limit(1)
            .execute()
        )
        if existing.data:
            return existing.data[0]

        now_iso = datetime.utcnow().isoformat()
        payload = {
            "fingerprint_hash": fingerprint_hash,
            "first_seen_at": now_iso,
            "last_seen_at": now_iso,
            "search_count": 0,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }
        inserted = (
            client.table("anon_fingerprints")
            .insert(payload)
            .execute()
        )
        if inserted.data:
            return inserted.data[0]
        # Rare: insert race - re-read.
        re_read = (
            client.table("anon_fingerprints")
            .select("*")
            .eq("fingerprint_hash", fingerprint_hash)
            .limit(1)
            .execute()
        )
        return re_read.data[0] if re_read.data else payload

    @staticmethod
    async def record_disclaimer(fingerprint_hash: str) -> None:
        """Stamp disclaimer acceptance on the fingerprint row."""
        client = get_supabase_admin_client()
        try:
            client.table("anon_fingerprints").update(
                {
                    "disclaimer_accepted_at": datetime.utcnow().isoformat(),
                    "last_seen_at": datetime.utcnow().isoformat(),
                }
            ).eq("fingerprint_hash", fingerprint_hash).execute()
        except Exception as e:
            logger.warning(f"anon_fp record_disclaimer failed (non-blocking): {e}")

    @staticmethod
    async def increment_search(fingerprint_hash: str) -> int:
        """Increment search_count. Returns the new count, or 0 on failure."""
        client = get_supabase_admin_client()
        try:
            row = (
                client.table("anon_fingerprints")
                .select("search_count")
                .eq("fingerprint_hash", fingerprint_hash)
                .limit(1)
                .execute()
            )
            current = (row.data[0].get("search_count") or 0) if row.data else 0
            new_count = current + 1
            client.table("anon_fingerprints").update(
                {
                    "search_count": new_count,
                    "last_seen_at": datetime.utcnow().isoformat(),
                }
            ).eq("fingerprint_hash", fingerprint_hash).execute()
            return new_count
        except Exception as e:
            logger.warning(f"anon_fp increment_search failed (non-blocking): {e}")
            return 0

    @staticmethod
    async def mark_converted(fingerprint_hash: str, user_id: str) -> None:
        """Link this fingerprint to the user they signed up as."""
        client = get_supabase_admin_client()
        try:
            client.table("anon_fingerprints").update(
                {"converted_user_id": user_id}
            ).eq("fingerprint_hash", fingerprint_hash).execute()
        except Exception as e:
            logger.warning(f"anon_fp mark_converted failed (non-blocking): {e}")
