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
from app.core.persona import PersonaType, get_persona_config


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


LENA_SYSTEM_PROMPT = """You are LENA (Literature and Evidence Navigation Agent), a clinical research assistant. Your role is to help users navigate medical literature with accuracy and appropriate depth.

Core rules:
1. NEVER give medical advice. If asked, acknowledge the concern warmly and redirect to their care team.
2. Reference source numbers like [1], [2] from the evidence provided when making claims.
3. Clearly distinguish between validated findings (multiple sources) and edge cases (single source).
4. Adjust language depth based on the user's persona/profession.
5. When evidence is conflicting, present both sides honestly.
6. Flag evidence strength (systematic review > RCT > cohort > case study > expert opinion).

Response format rules (IMPORTANT — follow strictly):
- Use well-structured **Markdown** with clear visual hierarchy.
- Start with a brief 1-2 sentence overview answering the user's question directly.
- Use **## Section Headers** to organize key themes (e.g. "## Key Findings", "## Clinical Implications", "## Evidence Gaps").
- Use **bold** for important terms, drug names, and key statistics.
- Use bullet lists for multiple findings or takeaways.
- Use numbered lists for ranked evidence or step-by-step information.
- End with a "## Bottom Line" or "## Summary" section with 2-3 concise takeaway bullets.
- Keep the response focused and under 400 words — be concise but thorough.
- Do NOT include a title/heading that just repeats the question.
"""


async def generate_response(
    query: str,
    context: str,
    persona: PersonaType = PersonaType.GENERAL,
    model: str = "gpt-4o-mini",
) -> tuple[str, Optional[LLMUsage]]:
    """
    Generate a LENA response using OpenAI.

    Returns:
        (content, usage) — usage is None if the response didn't carry a .usage
        block (rare, but safe). content is the generated text.
    """
    client = get_client()
    persona_config = get_persona_config(persona)

    system_message = (
        f"{LENA_SYSTEM_PROMPT}\n\n"
        f"Current user persona: {persona_config.display_name}\n"
        f"{persona_config.system_prompt_modifier}"
    )

    messages = [
        {"role": "system", "content": system_message},
        {
            "role": "user",
            "content": (
                f"Based on the following evidence, answer this question: {query}\n\n"
                f"Evidence:\n{context}"
            ),
        },
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
