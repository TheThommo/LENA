"""
BioRender figures — NOT scored by PULSE.

OAuth-backed MCP at https://mcp.services.biorender.com/mcp.
Without user OAuth / BIORENDER_ACCESS_TOKEN, returns empty list with
auth_required metadata for the frontend (does not crash the pipeline).
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("lena.sources.biorender")

MCP_URL = "https://mcp.services.biorender.com/mcp"


@dataclass
class BiorenderFigure:
    id: str
    title: str
    thumbnail_url: str
    url: str
    caption: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


async def search_biorender(
    query: str,
    max_results: int = 8,
    access_token: Optional[str] = None,
) -> tuple[list[BiorenderFigure], dict[str, Any]]:
    """
    Search BioRender for related scientific figures.

    Returns (figures, meta). meta may include auth_required=True when
    no OAuth token is available.
    """
    token = access_token or settings.biorender_access_token
    if not token:
        return [], {
            "auth_required": True,
            "message": "BioRender figures require user OAuth (BIORENDER_ACCESS_TOKEN).",
            "mcp_url": MCP_URL,
        }

    # MCP JSON-RPC style tools/call — best-effort; isolated from PULSE
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "search_figures",
            "arguments": {"query": query, "limit": max_results},
        },
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(MCP_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        logger.warning("BioRender MCP call failed: %s", exc)
        return [], {"error": str(exc), "auth_required": False}

    figures: list[BiorenderFigure] = []
    # MCP content is nested; accept several shapes
    content = data.get("result") or data.get("content") or data
    rows = []
    if isinstance(content, dict):
        rows = content.get("figures") or content.get("items") or content.get("results") or []
        if not rows and isinstance(content.get("content"), list):
            for block in content["content"]:
                if isinstance(block, dict) and block.get("type") == "text":
                    # unstructured — skip parse
                    pass
    elif isinstance(content, list):
        rows = content

    for row in rows:
        if not isinstance(row, dict):
            continue
        fid = str(row.get("id") or row.get("figure_id") or "")
        title = row.get("title") or row.get("name") or "BioRender figure"
        thumb = row.get("thumbnail_url") or row.get("thumbnail") or row.get("image_url") or ""
        url = row.get("url") or row.get("share_url") or ""
        if not fid and not thumb:
            continue
        figures.append(
            BiorenderFigure(
                id=fid or thumb,
                title=title,
                thumbnail_url=thumb,
                url=url,
                caption=(row.get("caption") or "")[:300],
            )
        )
        if len(figures) >= max_results:
            break
    return figures, {"auth_required": False, "count": len(figures)}
