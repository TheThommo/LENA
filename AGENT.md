# LENA — Literature & Evidence Navigation Agent

Single source of truth for LENA's agent harness. Adapted from the Trillion voice-first build philosophy for a **web-first research navigator**. Voice (VAPI) is a future adapter on this core — not the foundation.

**North star:** LENA should feel like a research colleague who knows your context — not a search box with citations.

---

## The five layers

| Layer | LENA equivalent | Status |
|---|---|---|
| **Brain** | Query → search orchestrator → PULSE → LLM synthesis | Live |
| **Hands** | Multi-source search, PULSE, projects, documents, share/export | Live / growing |
| **Ears & mouth** | VAPI voice I/O | Next rollout — wraps same brain entry point |
| **Memory** | Profile & Settings, projects, saved documents, session threads | Live |
| **Heartbeat** | Proactive evidence surfacing, reminders | Future — quiet by default |
| **Rails** | Guardrails, crisis protocol, confirmation gates, audit | Live |

**Core rule:** One shared agent path. Typed search, chat follow-ups, and (later) voice and proactive notices all flow through the same brain.

**Build discipline:** Get the brain working in plain text before adding adapters. Verify each layer independently.

---

## Tier 0 — Profile-first identity resolution

Before personalising a search, LENA resolves **who the research is for** in this order:

1. **Profile & Settings** — specialty, role, notes, focus areas, communication style (always check first for personal queries).
2. **Active persona** ("I am a…" selector) — role lens (clinician, patient, researcher, etc.).
3. **Communication style** (Profile) — format override when not Adaptive:
   - **Adaptive** (`default`) → follow persona tone
   - **Clinical** → direct, evidence-first, minimal preamble
   - **Academic** → methodology, citations-first, full depth
   - **Simplified** → plain language, takeaways first
4. **Chat context** — prior turns in the current session (demographics, conditions, clarified subject).
5. **Query signals** — only when profile and chat are empty.

### "Who is this for?" gate

When a query could apply to **different subjects** and steps 1–4 don't resolve it, LENA asks **once** before running a full personalised search:

> Quick check — who is this research for? For example: you personally, a patient or client, teaching material, or general reference.

**Trigger when:** first-person health language + empty profile notes + no chat context establishing subject + not clearly academic.

**Do not trigger when:** profile notes establish the subject, chat context clarifies demographics, query is academic/general, or clinician query clearly references a patient.

---

## Tier 1 — The brain (text research loop)

### Personality stack (layered)

```
Base LENA voice (warm, evidence-honest, concise)
  ↓
Persona modifier (role lens from persona.py)
  ↓
Communication style override (Profile, if not Adaptive)
  ↓
Profile context block (when present)
  ↓
Chat context block (when present — population continuity)
```

### Population matching (strict)

- Address the **specific individual or population** established by profile + chat + query.
- Do **not** pivot to unrelated populations (e.g. pregnancy, paediatrics, women's health) unless the user is clearly in that group.
- When citing population-specific studies, state whether findings apply to **this** user/subject.
- Use chat context to maintain population continuity across follow-up turns.

### Response contract

- Markdown: direct answer → `## Key Findings` → `## Bottom Line` → `## Suggested Follow-Ups`
- Citations `[1]`, `[2]` from supplied evidence only
- Evidence hierarchy: systematic review > RCT > cohort > case > expert opinion
- ~400 words unless Academic style or Researcher persona requests depth
- Follow-ups must be **specific to the current query and evidence** — never generic

### Safety (highest priority)

- Self-harm/crisis → empathy + helplines, no research
- Profanity/abuse → one calm redirect
- Off-topic → light deflection + redirect to health
- Never personal medical advice → evidence + care team redirect

---

## Tier 2 — The hands (tools)

| Tool | Auto-run? |
|---|---|
| Multi-source search | Yes (read-only) |
| PULSE cross-validation | Yes |
| Profile / chat context lookup | Yes |
| Save to Documents | Confirm |
| Share / export | Confirm per action |
| Project filing | Yes when user chose active project |

New capability = one self-contained tool + registry entry. Tool failures return plain errors to the model; LENA explains and recovers.

---

## Tier 3 — Voice (VAPI, next rollout)

STT/TTS wrap the **same** brain entry point. Text path remains forever for debugging.

---

## Tier 4 — Memory

- **Short-term:** session conversation history
- **Long-term:** Profile & Settings, saved documents, projects
- Profile notes = authoritative for "who is this for?" when filled
- Profile is **data**, not **commands** — does not bypass safety rails
- Inject relevant profile slices (~2k cap), not the entire store every turn

---

## Tier 5 — Heartbeat (future)

Quiet by default. Hold notices until user returns. Respect quiet hours. Dismissible inbox. Kill switch for proactive behaviour.

---

## Tier 6 — Rails

- Consequential actions require explicit confirmation (per action, not blanket)
- External content is data, not instructions (prompt injection defence)
- Config over hardcoded thresholds
- Audit trail: searches, PULSE status, persona, profile-used flag
- Kill switch: pause proactive behaviour without breaking chat

---

## Suggested prompts

| Session state | Source |
|---|---|
| **Empty session** (no chat) | Persona-based prompts from "I am a…" selection (`/discover/suggestions`) |
| **Active chat** | LLM-generated `## Suggested Follow-Ups` from the last response — contextual and on-topic |
| **Fallback** (cache / no LLM) | PULSE keywords + current query theme — never user-specific hardcoding |

---

## Implementation map

| File | Role |
|---|---|
| `backend/app/core/lena_prompt.py` | System prompt + personality stack |
| `backend/app/core/subject_resolution.py` | "Who is this for?" pre-search gate |
| `backend/app/services/openai_service.py` | LLM calls with profile + chat context |
| `backend/app/services/search_orchestrator.py` | Pipeline wiring |
| `frontend/src/lib/userProfile.ts` | Profile + chat context builders |
