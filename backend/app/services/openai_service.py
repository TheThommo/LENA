"""
OpenAI Service for LENA

Handles all LLM interactions:
- Query understanding and reformulation
- Persona detection (LLM-enhanced)
- PULSE cross-reference analysis
- Response generation with persona-appropriate tone
- Embedding generation for semantic search (future: pgvector)
"""

from typing import Optional
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.persona import PersonaType, get_persona_config

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
2. Always cite sources with PMIDs, DOIs, or URLs.
3. Clearly distinguish between validated findings (supported by multiple sources) and edge cases (supported by only one source).
4. Adjust your language based on the user's persona/profession.
5. When evidence is conflicting, present both sides honestly.
6. Flag the strength of evidence (systematic review > RCT > cohort > case study > expert opinion).
"""


async def generate_response(
    query: str,
    context: str,
    persona: PersonaType = PersonaType.GENERAL,
    model: str = "gpt-4o-mini",
) -> str:
    """
    Generate a LENA response using OpenAI.

    Args:
        query: The user's question
        context: Retrieved evidence/literature context
        persona: The detected user persona
        model: OpenAI model to use (gpt-4o-mini for cost efficiency)

    Returns:
        Generated response string
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

    return response.choices[0].message.content or ""


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
