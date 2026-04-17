"""
LENA Guardrails

Three tiers of pre-search content filtering, checked in priority order:

1. SELF-HARM — highest priority. If triggered, the search is blocked and
   LENA responds with a crisis message encouraging the user to seek
   immediate help. No research results are shown.

2. PROFANITY / ABUSE — if triggered, the search is blocked and LENA
   asks the user to keep things respectful. No research results shown.

3. MEDICAL ADVICE — if triggered, LENA still runs the search but wraps
   the response in a warm redirect to the user's healthcare team,
   emphasising that the evidence is informational, not prescriptive.

4. OFF-TOPIC — if triggered, the search is blocked and LENA responds
   with a light, humorous deflection and restates her speciality.
   No research results are shown.

Each checker returns a (triggered: bool, message: str) tuple. The
orchestrator checks them in order and short-circuits on the first hit.
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

# Slurs and hate speech (non-exhaustive, covers the most common)
_SLUR_TOKENS = {
    "nigger", "nigga", "faggot", "fag", "retard", "retarded",
    "tranny", "spic", "kike", "chink", "wetback", "raghead",
}


def check_profanity(query: str) -> tuple[bool, Optional[str]]:
    """Detect profanity, slurs, or abusive language."""
    tokens = set(query.lower().split())
    q_lower = query.lower()

    # Check slurs first (zero tolerance)
    if tokens & _SLUR_TOKENS:
        return True, (
            "I'm here to help with health research, and I work best when "
            "we keep things respectful. That kind of language isn't "
            "something I can engage with. If you have a medical or health "
            "question, I'm ready to help."
        )

    # Check general profanity
    if tokens & _PROFANITY_TOKENS or any(p in q_lower for p in ("piss off", "screw you")):
        return True, (
            "I'm here to help with health research, and I work best when "
            "we keep things respectful. If you have a medical question, "
            "I'm ready — just ask."
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
    """
    Warm redirect when someone asks for medical advice.
    The search still runs — LENA shows evidence but frames it as
    informational, not prescriptive.
    """
    return (
        "I can see this is something that matters to you, and I want to "
        "make sure you get the best guidance possible. What I can do is "
        "share what the research literature says about this topic, so you're "
        "informed when you speak with your healthcare team. But for anything "
        "specific to your situation — your doctor or specialist is the best "
        "person to advise you, because they know your full history.\n\n"
        "Here's what the published evidence says:"
    )


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

# Broad categories that are clearly NOT healthcare / biomedical.
# We check both token-level and phrase-level. The bar is intentionally
# high — ambiguous queries (e.g. "mercury in fish") should NOT trigger
# this because they have a health angle. Only fire for queries that
# are unambiguously non-medical.
_OFFTOPIC_PHRASES = [
    # Sports
    "football score", "soccer score", "basketball score", "cricket score",
    "tennis score", "golf score", "golf leaderboard", "golf today",
    "who won the game", "who won the match", "what team",
    "premier league", "champions league", "world cup score",
    "nba", "nfl", "formula 1", "f1 results",
    # Weather
    "what's the weather", "whats the weather", "weather like in",
    "weather forecast", "weather today", "is it raining",
    "temperature in", "will it rain",
    # Finance
    "stock price", "crypto price", "bitcoin price", "share price",
    "market today", "forex",
    # Coding / tech
    "write me a poem", "write me code", "write a script",
    "fix my code", "debug this", "python error", "javascript error",
    "build a website", "create an app",
    # Cooking
    "recipe for", "how to cook", "baking instructions",
    "best restaurant", "food delivery",
    # Maths / homework
    "solve this equation", "math homework", "calculus problem",
    "algebra help",
    # Entertainment
    "tell me a joke", "tell me a story", "sing me",
    "movie recommendation", "book recommendation", "netflix",
    "what should i watch", "best movies",
    # Translation
    "translate this", "translate to",
    # Travel (non-health)
    "travel itinerary", "flight to", "hotel in",
    "best places to visit", "tourist attractions",
    # Hacking / illegal
    "how to hack", "crack password", "bypass security",
]

# Healthcare-adjacent terms — if any of these appear alongside an
# off-topic phrase, we DON'T fire (gives benefit of the doubt).
_HEALTH_RESCUE_TOKENS = {
    "health", "medical", "clinical", "disease", "cancer", "heart",
    "brain", "drug", "medication", "therapy", "treatment", "symptom",
    "diagnosis", "patient", "hospital", "study", "trial", "evidence",
    "research", "pubmed", "cochrane", "vitamin", "supplement", "diet",
    "nutrition", "exercise", "mental", "anxiety", "depression",
    "blood", "immune", "infection", "vaccine", "pain", "chronic",
    "acute", "syndrome", "disorder", "condition", "surgery",
    "rehabilitation", "prognosis", "epidemiology", "pathology",
    "pharmaceutical", "dosage", "side effect", "contraindication",
}


def _normalize(text: str) -> str:
    """Strip apostrophes/smart-quotes so 'what's' matches 'whats'."""
    return text.replace("'", "").replace("'", "").replace("'", "").replace("`", "")


def check_off_topic(query: str) -> tuple[bool, Optional[str]]:
    """Detect clearly non-healthcare queries."""
    q = query.lower()
    q_norm = _normalize(q)

    # If any health-rescue token is present, assume good intent
    if any(token in q for token in _HEALTH_RESCUE_TOKENS):
        return False, None

    # Check both raw and apostrophe-normalized forms
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


# ── Combined Check ───────────────────────────────────────────────────────

def run_all_guardrails(query: str) -> tuple[Optional[str], Optional[str]]:
    """
    Run all guardrails in priority order. Returns:
      (guardrail_type, message) if triggered — "self_harm", "profanity",
      "off_topic", or "medical_advice".
      (None, None) if no guardrail fires.

    The orchestrator can use guardrail_type to decide whether to block
    the search entirely or just prepend the message.
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
