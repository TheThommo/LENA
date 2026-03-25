"""
Medical Advice Guardrail

LENA never gives medical advice. But she does it warmly, not robotically.
When someone crosses that line, she acknowledges what they're going through
and redirects to their care team with genuine warmth.
"""

# Patterns that suggest the user is asking for medical advice
ADVICE_TRIGGER_PHRASES = [
    "should i take",
    "should i stop taking",
    "is it safe to",
    "can i take",
    "what medication",
    "what should i do about",
    "do i have",
    "am i at risk",
    "should i be worried",
    "is this normal",
    "what treatment",
    "should i see a doctor",
    "how do i treat",
    "can you diagnose",
    "what's wrong with me",
    "should i go to the er",
    "is this serious",
    "will this go away",
    "what dose should",
]


def check_for_advice_request(query: str) -> bool:
    """Check if a query is asking for medical advice."""
    query_lower = query.lower()
    return any(phrase in query_lower for phrase in ADVICE_TRIGGER_PHRASES)


def get_warm_redirect(query: str) -> str:
    """
    Generate a warm, empathetic redirect when someone asks for medical advice.
    This is the template. In production, the LLM will personalise this
    based on the specific question asked.
    """
    return (
        "I can see this is something that matters to you, and I want to "
        "make sure you get the best guidance possible. What I can do is "
        "share what the research literature says about this topic, so you're "
        "informed when you speak with your healthcare team. But for anything "
        "specific to your situation, your doctor or specialist will be the "
        "best person to advise you, because they know your full history.\n\n"
        "Would you like me to pull up the latest research on this topic instead?"
    )
