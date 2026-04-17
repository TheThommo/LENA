"""
LENA Guardrails

Four tiers of pre-search content filtering, checked in priority order:

1. SELF-HARM — highest priority. Hard block + crisis resources.
2. PROFANITY / ABUSE — hard block, ask for respect.
3. GREETING — warm welcome + sign-up CTA.
4. OFF-TOPIC — NARROW hard block for queries with genuinely zero health
   angle (coding, maths, hacking). Anything ambiguous (weather, sports,
   food, travel) passes through to the LLM, which is smart enough to
   find the health angle or deflect with humour via the system prompt.
5. MEDICAL ADVICE — search runs, but preamble added.

DESIGN RULE for off-topic: if you can imagine a scenario where the query
has a health angle, do NOT hard-block it. A 50-year-old with hypertension
playing golf in 50°C heat IS a health question (heat stroke, hydration,
cardiovascular risk). Let the LLM decide.
"""

from typing import Optional


# ── Self-Harm ────────────────────────────────────────────────────────────

_SELF_HARM_PHRASES = [
    "kill myself", "want to die", "end my life", "suicide",
    "suicidal", "self harm", "self-harm", "cutting myself",
    "hurting myself", "don't want to live", "not worth living",
    "end it all", "take my own life", "better off dead",
    "no reason to live", "overdose myself", "jump off",
    "harm myself", "hurt myself",
]


def check_self_harm(query: str) -> tuple[bool, Optional[str]]:
    """Detect self-harm / suicidal ideation. Highest priority."""
    q = query.lower()
    if any(phrase in q for phrase in _SELF_HARM_PHRASES):
        return True, (
            "I can hear that you're going through something really difficult "
            "right now, and I want you to know that you matter.\n\n"
            "**Please reach out to someone who can help:**\n\n"
            "- **Contact your nearest emergency service** (000 in Australia, "
            "911 in the US, 999 in the UK, 112 in the EU)\n"
            "- **Talk to a healthcare professional** — your GP, a hospital "
            "emergency department, or a mental health crisis team\n"
            "- **Reach out to a trusted family member or friend** right now\n"
            "- **Crisis helplines:** Lifeline (13 11 14 AU), "
            "988 Suicide & Crisis Lifeline (US), Samaritans (116 123 UK)\n\n"
            "You don't have to go through this alone. Professional support "
            "can make a real difference, and people around you care more "
            "than you might realise.\n\n"
            "I'm a research tool and I'm not equipped to provide the support "
            "you need right now — but the people above are. Please reach out."
        )
    return False, None


# ── Profanity / Abuse ────────────────────────────────────────────────────

_PROFANITY_TOKENS = {
    "fuck", "fucking", "fucked", "fucker", "fucks",
    "shit", "shitting", "bullshit",
    "bitch", "bitches",
    "asshole", "arsehole",
    "dick", "dickhead",
    "cunt",
    "bastard",
    "damn", "dammit",
    "stfu", "gtfo", "wtf",
    "piss off", "screw you",
}

_SLUR_TOKENS = {
    "nigger", "nigga", "faggot", "fag", "retard", "retarded",
    "tranny", "spic", "kike", "chink", "wetback", "raghead",
}


def check_profanity(query: str) -> tuple[bool, Optional[str]]:
    """Detect profanity, slurs, or abusive language."""
    tokens = set(query.lower().split())
    q_lower = query.lower()

    if tokens & _SLUR_TOKENS:
        return True, (
            "I'm here to help with health research, and I work best when "
            "we keep things respectful. That kind of language isn't "
            "something I can engage with. If you have a medical or health "
            "question, I'm ready to help."
        )

    if tokens & _PROFANITY_TOKENS or any(p in q_lower for p in ("piss off", "screw you")):
        return True, (
            "I'm here to help with health research, and I work best when "
            "we keep things respectful. If you have a medical question, "
            "I'm ready — just ask."
        )

    return False, None


# ── Greetings ────────────────────────────────────────────────────────────

_GREETING_PATTERNS = {
    "hi", "hello", "hey", "howdy", "hiya", "yo", "sup",
    "good morning", "good afternoon", "good evening",
    "hi there", "hello there", "hey there",
    "hi lena", "hello lena", "hey lena",
    "what's up", "whats up",
    "how are you", "how r u",
    "greetings",
}


def check_greeting(query: str) -> tuple[bool, Optional[str]]:
    """Detect casual greetings and respond warmly like a person would."""
    q = query.lower().strip().rstrip("!?.,:;")
    if q in _GREETING_PATTERNS:
        return True, (
            "Hey there! Welcome to LENA.\n\n"
            "I'm your research companion — I help people navigate the world of "
            "medical and health-science evidence. Whether you're a clinician, "
            "a student, a researcher, or just someone who wants solid answers "
            "about their health, I've got you.\n\n"
            "To start searching, **sign up for free** or **log in** if you "
            "already have an account. It only takes a moment, and your first "
            "searches are on us.\n\n"
            "What would you like to explore today?"
        )
    return False, None


# ── Off-Topic ────────────────────────────────────────────────────────────
#
# DESIGN RULE: this list is intentionally TINY. It only contains queries
# that have ZERO conceivable health angle. Anything ambiguous (weather,
# sports, cooking, travel, finance) passes through to the LLM, which
# handles it via the system prompt — either finding the health angle
# or deflecting with humour.
#
# DO NOT add "weather", "golf", "recipe", "exercise", "travel" etc.
# A 50-year-old with hypertension playing golf in 50°C heat IS a health
# question (heat stroke, rehydration, cardiovascular risk under exertion).
# The LLM is smart enough to figure this out. The hard-block list is not.

_OFFTOPIC_PHRASES = [
    # Pure coding / tech — no health angle
    "write me code", "write a script", "fix my code", "debug this",
    "python error", "javascript error", "build a website", "create an app",
    "merge conflict", "git commit", "sql query",
    # Pure maths homework
    "solve this equation", "math homework", "calculus problem",
    "algebra help", "integrate this function",
    # Hacking / illegal
    "how to hack", "crack password", "bypass security",
    # Pure creative writing (not health-related)
    "write me a poem", "write me a story", "write me an essay",
    # Entertainment media requests (no health angle)
    "movie recommendation", "book recommendation",
    "what should i watch",
    # Translation (not health-related)
    "translate this", "translate to",
]


def _normalize(text: str) -> str:
    """Strip apostrophes/smart-quotes so 'what's' matches 'whats'."""
    return text.replace("'", "").replace("\u2018", "").replace("\u2019", "").replace("`", "")


def check_off_topic(query: str) -> tuple[bool, Optional[str]]:
    """
    Hard-block queries with genuinely zero health angle.

    IMPORTANT: this is a narrow, high-confidence filter. Anything that
    COULD have a health interpretation (weather, sports, food, travel)
    passes through to the LLM, which handles ambiguity via the system
    prompt — either finding the health angle or deflecting with humour.
    """
    q_norm = _normalize(query.lower())

    if any(_normalize(phrase) in q_norm for phrase in _OFFTOPIC_PHRASES):
        return True, (
            "Ha — I appreciate the creative question, but my expertise is "
            "strictly in medical and health-science research. For that one, "
            "you'd be better off asking ChatGPT, Google, or a very patient "
            "friend!\n\n"
            "What I *can* do is cross-reference 250 million+ peer-reviewed "
            "papers across 6 biomedical databases in seconds. Got a health "
            "question? That's where I shine."
        )

    return False, None


# ── Medical Advice ───────────────────────────────────────────────────────

_ADVICE_TRIGGER_PHRASES = [
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
    """Check if a query is asking for personal medical advice."""
    q = query.lower()
    return any(phrase in q for phrase in _ADVICE_TRIGGER_PHRASES)


def get_warm_redirect(query: str) -> str:
    """Warm redirect for medical advice queries. Search still runs."""
    return (
        "I can see this is something that matters to you, and I want to "
        "make sure you get the best guidance possible. What I can do is "
        "share what the research literature says about this topic, so you're "
        "informed when you speak with your healthcare team. But for anything "
        "specific to your situation — your doctor or specialist is the best "
        "person to advise you, because they know your full history.\n\n"
        "Here's what the published evidence says:"
    )


# ── Combined Check ───────────────────────────────────────────────────────

def run_all_guardrails(query: str) -> tuple[Optional[str], Optional[str]]:
    """
    Run all guardrails in priority order. Returns:
      (guardrail_type, message) if triggered.
      (None, None) if no guardrail fires.
    """
    triggered, msg = check_self_harm(query)
    if triggered:
        return "self_harm", msg

    triggered, msg = check_profanity(query)
    if triggered:
        return "profanity", msg

    triggered, msg = check_greeting(query)
    if triggered:
        return "greeting", msg

    triggered, msg = check_off_topic(query)
    if triggered:
        return "off_topic", msg

    if check_for_advice_request(query):
        return "medical_advice", get_warm_redirect(query)

    return None, None
