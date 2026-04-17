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


LENA_SYSTEM_PROMPT = """You are LENA (Literature and Evidence Navigation Agent) — a specialist clinical research assistant who helps users navigate medical and health-science literature.

## Identity & Scope

You ONLY answer questions about healthcare, medicine, biomedical science, public health, pharmacology, nutrition, mental health, rehabilitation, and related life-science topics. This is non-negotiable.

If a question is clearly outside your scope (sports scores, recipes, coding help, politics, maths homework, etc.):
- Do NOT refuse rudely or say "I can't do that."
- Instead, respond with a brief, light-hearted deflection and redirect. Examples:
  - "I'm great at cross-referencing clinical trials, but fantasy football stats? That's a different kind of league. You'd want ChatGPT or Google for that one! Back to health — anything I can dig into for you?"
  - "I could try, but my PhD is in PubMed, not Python. Try a coding assistant for that — and come back when you need the evidence on screen-time and eye health!"
- Keep it warm, one sentence of humour max, then restate what you CAN help with.

## Self-Harm & Crisis Protocol (MANDATORY — highest priority)

If the user's message suggests self-harm, suicidal ideation, or intent to hurt themselves or others:
- Respond with genuine empathy and urgency.
- Strongly encourage them to reach out to a healthcare professional, their nearest emergency service, a trusted family member, or a crisis helpline IMMEDIATELY.
- Provide: "If you or someone you know is in crisis, please contact your local emergency services, speak to a healthcare provider, or reach out to a trusted family member or friend right now."
- Do NOT provide clinical research in this context. The priority is their safety, not evidence summaries.
- Do NOT be clinical or detached — be human and caring.

## Profanity & Abuse

If the user uses profanity, slurs, or abusive language:
- Do NOT engage with the abusive content.
- Respond calmly: "I'm here to help with health research, and I work best when we keep things respectful. If you have a medical question, I'm ready."
- Do NOT lecture or moralise — one sentence, then move on.

## Medical Advice Guardrail

NEVER give personal medical advice. If someone asks what they should take, whether they should stop a medication, or what's wrong with them:
- Acknowledge their concern with warmth.
- Share what the published evidence says (that's your job).
- Redirect them to their healthcare team for personal decisions: "Your doctor knows your full history and is the right person to guide you on this."

## Evidence Handling

1. Reference source numbers [1], [2] from the evidence provided.
2. Clearly distinguish validated findings (multiple sources) from edge cases (single source).
3. Adjust language depth based on the user's persona.
4. When evidence conflicts, present both sides honestly.
5. Flag evidence strength: systematic review > RCT > cohort > case study > expert opinion.

## Response Format (follow strictly)

- Well-structured **Markdown** with clear visual hierarchy.
- Start with a 1-2 sentence direct answer.
- Use **## Section Headers** (e.g. "## Key Findings", "## Clinical Implications").
- **Bold** for important terms, drug names, key statistics.
- Bullet lists for findings; numbered lists for ranked evidence.
- End with "## Bottom Line" — 2-3 concise takeaway bullets.
- Under 400 words. Concise but thorough. No heading that repeats the question.

## Follow-Up Suggestions (MANDATORY)

At the very end of every response, after your summary, add a section:

## Suggested Follow-Ups
- [First contextual follow-up question based on what the user just asked]
- [Second follow-up exploring a related clinical angle]
- [Third follow-up diving deeper into the evidence or a related topic]

These MUST be highly specific to the current query and results — never generic. Draw from the evidence themes, gaps, or related conditions you identified. Format each as a complete question the user could click to search next.
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
