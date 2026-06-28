"""Ingest URLs, PDFs, and images for product / label research."""

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.content_ingest import ingest_upload

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("")
async def ingest_document(file: UploadFile = File(...)):
    """
    Extract text from an uploaded label, PDF, or image.
    Returns plain text the frontend can attach to the next search.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    data = await file.read()
    if len(data) > 5_000_000:
        raise HTTPException(status_code=413, detail="File too large (max 5 MB)")

    result = await ingest_upload(file.filename, file.content_type or "", data)
    if result.error and not result.text:
        raise HTTPException(status_code=422, detail=result.error)

    return {
        "kind": result.kind,
        "filename": result.source,
        "title": result.title,
        "text": result.text,
        "chars": len(result.text),
    }
