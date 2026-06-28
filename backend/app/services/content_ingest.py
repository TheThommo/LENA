"""
Fetch and extract text from URLs, PDFs, and images for product / label research.

Used when users paste medicine links (e.g. SAHPRA), upload supplement labels,
or attach PDFs to a search query.
"""

from __future__ import annotations

import base64
import io
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import httpx
from lxml import html as lxml_html

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("lena.content_ingest")

URL_PATTERN = re.compile(r"https?://[^\s<>\"{}|\\^`\[\]]+", re.IGNORECASE)
MAX_URL_CHARS = 14_000
MAX_ATTACH_CHARS = 16_000
FETCH_TIMEOUT = 20.0
MAX_FETCH_BYTES = 2_000_000


@dataclass
class IngestedContent:
    kind: str  # url | pdf | image | text
    source: str  # url or filename
    title: str
    text: str
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "source": self.source,
            "title": self.title,
            "text": self.text[:500] + ("…" if len(self.text) > 500 else ""),
            "chars": len(self.text),
            "error": self.error,
        }


def extract_urls(text: str) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for match in URL_PATTERN.findall(text or ""):
        url = match.rstrip(".,);]")
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def strip_urls(text: str) -> str:
    cleaned = URL_PATTERN.sub(" ", text or "")
    return re.sub(r"\s+", " ", cleaned).strip()


def _html_to_text(content: bytes) -> tuple[str, str]:
    parser = lxml_html.HTMLParser(encoding="utf-8")
    doc = lxml_html.fromstring(content, parser=parser)
    for xpath in ("//script", "//style", "//nav", "//footer", "//header", "//noscript"):
        for node in doc.xpath(xpath):
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)
    title_nodes = doc.xpath("//title/text()")
    title = title_nodes[0].strip() if title_nodes else "Web page"
    text = doc.text_content()
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text).strip()
    return title, text


async def fetch_url_content(url: str) -> IngestedContent:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return IngestedContent("url", url, url, "", error="Invalid URL")

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=FETCH_TIMEOUT,
            headers={"User-Agent": "LENA-ResearchBot/1.0 (+https://lena-app.up.railway.app)"},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = (resp.headers.get("content-type") or "").lower()
            raw = resp.content[:MAX_FETCH_BYTES]

            if "pdf" in content_type or url.lower().endswith(".pdf"):
                text = _extract_pdf_text(raw)
                title = url.split("/")[-1] or "PDF document"
                return IngestedContent("url", url, title, text[:MAX_URL_CHARS])

            if "html" in content_type or "text/" in content_type or not content_type:
                title, text = _html_to_text(raw)
                if not text and "json" in content_type:
                    text = raw.decode("utf-8", errors="replace")[:MAX_URL_CHARS]
                return IngestedContent("url", url, title, text[:MAX_URL_CHARS])

            return IngestedContent(
                "url", url, url, "",
                error=f"Unsupported content type: {content_type or 'unknown'}",
            )
    except Exception as exc:
        logger.warning("URL fetch failed for %s: %s", url, exc)
        return IngestedContent("url", url, url, "", error=str(exc))


def _extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    reader = PdfReader(io.BytesIO(data))
    parts = []
    for page in reader.pages[:30]:
        parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


async def ingest_upload(filename: str, content_type: str, data: bytes) -> IngestedContent:
    name = filename or "upload"
    mime = (content_type or "").lower()

    if mime.startswith("text/") or name.lower().endswith((".txt", ".csv", ".md")):
        text = data.decode("utf-8", errors="replace").strip()
        return IngestedContent("text", name, name, text[:MAX_ATTACH_CHARS])

    if "pdf" in mime or name.lower().endswith(".pdf"):
        text = _extract_pdf_text(data)
        if not text:
            return IngestedContent("pdf", name, name, "", error="Could not extract text from PDF")
        return IngestedContent("pdf", name, name, text[:MAX_ATTACH_CHARS])

    if mime.startswith("image/") or name.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
        text = await _extract_image_text(data, mime or "image/jpeg")
        if not text:
            return IngestedContent("image", name, name, "", error="Could not read text from image")
        return IngestedContent("image", name, name, text[:MAX_ATTACH_CHARS])

    return IngestedContent("text", name, name, "", error=f"Unsupported file type: {mime or 'unknown'}")


async def _extract_image_text(data: bytes, mime: str) -> str:
    if not settings.openai_api_key:
        return ""
    try:
        from app.services.openai_service import get_client

        b64 = base64.b64encode(data).decode("ascii")
        client = get_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extract ALL readable text from this medicine label, supplement label, "
                            "or health product document. Include product name, active ingredients, "
                            "dosages, warnings, and manufacturer. Return plain text only."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                ],
            }],
            max_tokens=2000,
            temperature=0,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as exc:
        logger.warning("Vision extract failed: %s", exc)
        return ""


async def ingest_urls_from_query(query: str) -> list[IngestedContent]:
    urls = extract_urls(query)
    if not urls:
        return []
    results: list[IngestedContent] = []
    for url in urls[:3]:
        results.append(await fetch_url_content(url))
    return results


def format_attached_context(blocks: list[IngestedContent]) -> str:
    if not blocks:
        return ""
    lines = ["--- Attached documents / links ---"]
    for block in blocks:
        if block.error and not block.text:
            lines.append(f"[{block.kind.upper()}] {block.source}\n  (Could not read: {block.error})")
            continue
        header = f"[{block.kind.upper()}] {block.title}"
        if block.source != block.title:
            header += f" ({block.source})"
        lines.append(f"{header}\n{block.text}")
    return "\n\n".join(lines)


async def ingest_attached_context_header(
    raw_header: Optional[str],
    filename: Optional[str] = None,
    kind: Optional[str] = None,
) -> list[IngestedContent]:
    """Parse pre-ingested attachment text from X-LENA-Attached-Context header."""
    if not raw_header or not raw_header.strip():
        return []
    name = (filename or "Attached document").strip()
    attach_kind = (kind or "text").strip()
    return [IngestedContent(attach_kind, name, name, raw_header.strip()[:MAX_ATTACH_CHARS])]


# Known active ingredients / drug names for product-context search steering.
_KNOWN_INGREDIENTS: tuple[str, ...] = (
    "paracetamol", "acetaminophen", "aspirin", "acetylsalicylic", "caffeine",
    "ibuprofen", "naproxen", "codeine", "diphenhydramine", "phenylephrine",
    "pseudoephedrine", "metformin", "omeprazole", "amoxicillin", "prednisone",
    "warfarin", "heparin", "insulin", "morphine", "tramadol", "doxycycline",
    "lisinopril", "atorvastatin", "levothyroxine", "amlodipine", "metoprolol",
    "salicylate", "salicylates",
)

_INGREDIENT_LINE = re.compile(
    r"(?:active\s+ingredient|composition|contains|ingredients?)\s*[:\-]\s*([^\n.]{3,120})",
    re.IGNORECASE,
)


def extract_search_terms_from_context(blocks: list[IngestedContent]) -> tuple[list[str], list[str]]:
    """Extract primary (ingredient/product) and secondary terms from attached content.

    Returns (primary_terms, secondary_terms). Primary terms drive literature
    queries and strict relevance filtering when a product URL/label is attached.
    """
    if not blocks:
        return [], []

    combined = " ".join(
        f"{b.title} {b.text}" for b in blocks if b.text and not b.error
    ).lower()
    if not combined.strip():
        return [], []

    primary: list[str] = []
    seen: set[str] = set()

    def _add(term: str, bucket: list[str]) -> None:
        t = term.strip().lower()
        if len(t) < 3 or t in seen:
            return
        seen.add(t)
        bucket.append(t)

    for ing in _KNOWN_INGREDIENTS:
        if ing in combined:
            _add(ing, primary)

    for match in _INGREDIENT_LINE.finditer(combined):
        segment = match.group(1).lower()
        for ing in _KNOWN_INGREDIENTS:
            if ing in segment:
                _add(ing, primary)
        for token in re.findall(r"[a-z][a-z0-9-]{2,}", segment):
            if token in _KNOWN_INGREDIENTS:
                _add(token, primary)

    secondary: list[str] = []
    for block in blocks:
        title = (block.title or "").strip()
        if title and title.lower() not in ("web page", "attached document", "upload"):
            for token in re.findall(r"[a-z][a-z0-9-]{2,}", title.lower()):
                if token not in {"headache", "powder", "powders", "medicine", "tablet", "capsule"}:
                    _add(token, secondary)

    return primary, secondary

