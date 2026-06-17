"""
User-owned data: profile preferences, saved documents, feature waitlist, share events.
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.core.auth import require_auth, get_current_user
from app.core.logging import get_logger
from app.db.supabase import get_supabase_admin_client

logger = get_logger("lena.user_data")
router = APIRouter(tags=["user-data"])


class PreferencesBody(BaseModel):
    preferences: dict[str, Any] = Field(default_factory=dict)


class DocumentBody(BaseModel):
    doc_key: str = Field(..., min_length=1, max_length=512)
    payload: dict[str, Any]


class FavouriteBody(BaseModel):
    is_favourite: bool


class InterestBody(BaseModel):
    email: EmailStr
    feature: str = Field(..., min_length=1, max_length=64)


class ShareBody(BaseModel):
    search_id: Optional[UUID] = None
    recipient_type: str = Field(..., min_length=1, max_length=32)
    recipient_email: Optional[str] = None
    note: Optional[str] = Field(None, max_length=2000)
    result_title: Optional[str] = Field(None, max_length=500)


@router.get("/profile/preferences")
async def get_profile_preferences(user=Depends(require_auth)):
    client = get_supabase_admin_client()
    user_id = user["user_id"]
    res = (
        client.table("user_profiles")
        .select("preferences, updated_at")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        return {"preferences": {}, "updated_at": None}
    row = res.data[0]
    return {"preferences": row.get("preferences") or {}, "updated_at": row.get("updated_at")}


@router.put("/profile/preferences")
async def put_profile_preferences(body: PreferencesBody, user=Depends(require_auth)):
    client = get_supabase_admin_client()
    user_id = user["user_id"]
    payload = {"user_id": user_id, "preferences": body.preferences}
    client.table("user_profiles").upsert(payload, on_conflict="user_id").execute()
    return {"ok": True}


@router.get("/documents")
async def list_saved_documents(user=Depends(require_auth)):
    client = get_supabase_admin_client()
    user_id = user["user_id"]
    res = (
        client.table("saved_documents")
        .select("doc_key, payload, saved_at")
        .eq("user_id", user_id)
        .order("saved_at", desc=True)
        .execute()
    )
    docs = []
    for row in res.data or []:
        payload = row.get("payload") or {}
        payload.setdefault("id", row["doc_key"])
        payload.setdefault("saved_at", row.get("saved_at"))
        docs.append(payload)
    return {"documents": docs}


@router.post("/documents")
async def upsert_saved_document(body: DocumentBody, user=Depends(require_auth)):
    client = get_supabase_admin_client()
    user_id = user["user_id"]
    saved_at = (body.payload or {}).get("saved_at")
    row = {
        "user_id": user_id,
        "doc_key": body.doc_key,
        "payload": body.payload,
    }
    if saved_at:
        row["saved_at"] = saved_at
    client.table("saved_documents").upsert(row, on_conflict="user_id,doc_key").execute()
    return {"ok": True}


@router.delete("/documents/{doc_key:path}")
async def delete_saved_document(doc_key: str, user=Depends(require_auth)):
    client = get_supabase_admin_client()
    client.table("saved_documents").delete().eq("user_id", user["user_id"]).eq("doc_key", doc_key).execute()
    return {"ok": True}


@router.patch("/documents/{doc_key:path}/favourite")
async def patch_document_favourite(doc_key: str, body: FavouriteBody, user=Depends(require_auth)):
    client = get_supabase_admin_client()
    user_id = user["user_id"]
    res = (
        client.table("saved_documents")
        .select("payload")
        .eq("user_id", user_id)
        .eq("doc_key", doc_key)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Document not found")
    payload = res.data[0].get("payload") or {}
    payload["is_favourite"] = body.is_favourite
    client.table("saved_documents").update({"payload": payload}).eq("user_id", user_id).eq("doc_key", doc_key).execute()
    return {"ok": True}


@router.post("/interest")
async def register_feature_interest(body: InterestBody, user=Depends(get_current_user)):
    client = get_supabase_admin_client()
    row = {
        "email": body.email.strip().lower(),
        "feature": body.feature.strip().lower(),
    }
    if user and user.get("user_id"):
        row["user_id"] = user["user_id"]
    try:
        client.table("feature_interest").insert(row).execute()
    except Exception:
        logger.warning("feature_interest insert failed", exc_info=True)
    return {"ok": True, "message": "You're on the list — we'll notify you when this launches."}


@router.post("/share")
async def log_share_event(body: ShareBody, user=Depends(require_auth)):
    client = get_supabase_admin_client()
    row = {
        "user_id": user["user_id"],
        "recipient_type": body.recipient_type,
        "recipient_email": body.recipient_email,
        "note": body.note,
        "result_title": body.result_title,
    }
    if body.search_id:
        row["search_id"] = str(body.search_id)
    client.table("share_events").insert(row).execute()
    return {"ok": True}
