"""
OpenAI Service for LENA

Handles all LLM interactions:
- Query understanding and reformulation
- Persona detection (LLM-enhanced)
- PULSE cross-reference analysis
- Response generation with persona-appropriate tone
- Embedding generation for semantic search (future: pgvector)
"""

from typing import Optional, NamedTuple
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.lena_prompt import build_system_message
from app.core.persona import PersonaType


class LLMUsage(NamedTuple):
    """Token + cost accounting for a single completion."""
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_micros: int  # USD millionths (1 USD == 1_000_000 micros)


# OpenAI public pricing, USD per 1M tokens. Update when rates change.
# Keyed by the prefix of the actual returned model id so fine-tune suffixes
# still match (e.g. "gpt-4o-mini-2024-07-18" -> gpt-4o-mini rates).
_MODEL_PRICING_USD_PER_M = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o":       (2.50, 10.00),
    "gpt-4-turbo":  (10.00, 30.00),
    "gpt-4":        (30.00, 60.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    "o1-mini":      (1.10, 4.40),
    "o1-preview":   (15.00, 60.00),
    "o1":           (15.00, 60.00),
    # Embeddings (input-only, no output cost)
    "text-embedding-3-small": (0.02, 0.0),
    "text-embedding-3-large": (0.13, 0.0),
}


def _price_for_model(model: str) -> tuple[float, float]:
    """Return (input $/1M, output $/1M) — falls back to gpt-4o-mini."""
    m = (model or "").lower()
    # Longest-prefix match so "gpt-4o-mini-xyz" beats "gpt-4o" etc.
    best = max(
        (k for k in _MODEL_PRICING_USD_PER_M if m.startswith(k)),
        key=len,
        default="gpt-4o-mini",
    )
    return _MODEL_PRICING_USD_PER_M[best]


def _compute_cost_micros(model: str, prompt_tokens: int, completion_tokens: int) -> int:
    """Cost in USD millionths. 1 USD = 1_000_000 micros, so cents = micros / 10_000."""
    in_rate, out_rate = _price_for_model(model)
    dollars = (prompt_tokens * in_rate + completion_tokens * out_rate) / 1_000_000.0
    return int(round(dollars * 1_000_000))

# Will be initialized when keys are available
_client: Optional[AsyncOpenAI] = None


def get_client() -> AsyncOpenAI:
    """Get or create the OpenAI async client."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


# Re-export for tests and legacy imports
from app.core.lena_prompt import LENA_SYSTEM_PROMPT  # noqa: F401


async def generate_response(
    query: str,
    context: str,
    persona: PersonaType = PersonaType.GENERAL,
    model: str = "gpt-4o-mini",
    profile_context: Optional[str] = None,
    chat_context: Optional[str] = None,
) -> tuple[str, Optional[LLMUsage]]:
    """
    Generate a LENA response using OpenAI.

    Returns:
        (content, usage) — usage is None if the response didn't carry a .usage
        block (rare, but safe). content is the generated text.
    """
    client = get_client()
    system_message = build_system_message(persona=persona, profile_context=profile_context)

    user_parts: list[str] = []
    if profile_context:
        user_parts.append(
            f"--- User profile (authoritative — tailor to THIS person) ---\n{profile_context}"
        )
    if chat_context:
        user_parts.append(
            f"--- Recent conversation (maintain population continuity) ---\n{chat_context}"
        )
    if (
        len(query) > 200
        or "diagnosed" in query.lower()
        or "current health" in query.lower()
        or profile_context
        or chat_context
    ):
        user_parts.append(
            "IMPORTANT: Resolve WHO this research is for using profile, chat context, and "
            "this query — in that order. Address THEIR conditions, supplements, side effects, "
            "and goals directly. Do NOT pivot to unrelated populations (e.g. pregnancy, "
            "women's health, pediatrics, athletes) unless clearly applicable. When citing "
            "population-specific studies, state whether findings apply to this subject. "
            "This research is for the individual or population established above — not a "
            "generic audience."
        )
    user_parts.append(f"Based on the following evidence, answer this question: {query}")
    user_parts.append(f"Evidence:\n{context}")

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,  # Low temp for factual accuracy
        max_tokens=2000,
    )

    content = response.choices[0].message.content or ""
    usage: Optional[LLMUsage] = None
    if getattr(response, "usage", None):
        pt = int(response.usage.prompt_tokens or 0)
        ct = int(response.usage.completion_tokens or 0)
        actual_model = getattr(response, "model", None) or model
        usage = LLMUsage(
            model=actual_model,
            prompt_tokens=pt,
            completion_tokens=ct,
            cost_micros=_compute_cost_micros(actual_model, pt, ct),
        )
    return content, usage


# ── Embeddings for PULSE claim similarity ────────────────────────────────
# text-embedding-3-small: 1536 dims, $0.02 per 1M tokens.
# A typical claim is ~30 tokens → embedding 100 claims ≈ $0.00006.

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 1536

# Cache embeddings within a single search request so we don't re-embed
# the same claim across multiple pair comparisons.
_embedding_cache: dict[str, list[float]] = {}


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Batch-embed a list of texts. Returns one 1536-dim vector per text.
    Uses in-memory cache to avoid re-embedding duplicates within a search.
    Cost: ~$0.02 per 1M tokens (~$0.00006 per 100 claims).
    """
    client = get_client()

    # Split into cached and uncached
    uncached_indices = []
    uncached_texts = []
    results: list[Optional[list[float]]] = [None] * len(texts)

    for i, text in enumerate(texts):
        if text in _embedding_cache:
            results[i] = _embedding_cache[text]
        else:
            uncached_indices.append(i)
            uncached_texts.append(text)

    if uncached_texts:
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=uncached_texts,
        )
        for j, embedding_obj in enumerate(response.data):
            vec = embedding_obj.embedding
            idx = uncached_indices[j]
            results[idx] = vec
            _embedding_cache[uncached_texts[j]] = vec

    return [r for r in results if r is not None]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two embedding vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def clear_embedding_cache():
    """Clear the per-request embedding cache. Call after each search completes."""
    _embedding_cache.clear()


async def test_connection() -> dict:
    """Test the OpenAI API connection."""
    try:
        client = get_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'LENA connected' in exactly two words."}],
            max_tokens=10,
        )
        reply = response.choices[0].message.content or ""
        return {
            "source": "OpenAI",
            "status": "connected",
            "model_tested": "gpt-4o-mini",
            "response": reply.strip(),
            "api_key_configured": bool(settings.openai_api_key),
        }
    except Exception as e:
        return {
            "source": "OpenAI",
            "status": "error",
            "error": str(e),
            "api_key_configured": bool(settings.openai_api_key),
        }
