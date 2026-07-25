# CHECKPOINT 2 — Answer-quality eval baseline (Phase 2)

**Date:** 2026-07-25  
**Branch:** `cursor/pulse-phase2-eval-1f1a`  
**Pipeline changes:** none (eval only)  
**Rubric mode this run:** `offline` (no `OPENAI_API_KEY` in agent env). LLM grader is implemented and used automatically when a key is present.

---

## Verdict: **PASS (eval is strict enough)**

Current shared pipeline scores **0/19** golden persona-runs. The eval is **not** flattering broken behaviour into a pass.

### G01 lecanemab / donanemab US–EU (required signature)

| Gate | Result |
|------|--------|
| Rubric fail (does not fully answer US+EU) | **FAIL** — overall 69.4; coverage 50 (&lt; floor 60) |
| `dedup_correct` (same DOI in pubmed + europe_pmc) | **FAIL** |
| `relevance_lead` (must cue **both** US and EU groups) | **FAIL** — lead is Europe-only approval sentence |
| Also | `no_verbatim_dump` **FAIL** (verbatim claim concatenation) |

Personas run: `pharmacist`, `clinician` — both fail the same way.

---

## Full golden tally

| Metric | Value |
|--------|--------|
| Persona-runs | 19 (16 cases; G01/G06/G09 expand) |
| Pass (rubric ∧ floor) | **0 / 19** |
| Rubric average | **55.6** |
| Holdout | **not run** (sealed until Phase 6) |

Artifacts:
- `/opt/cursor/artifacts/golden_baseline_phase2.txt`
- `/opt/cursor/artifacts/golden_baseline_phase2.json`

### Per-case (abbrev)

| Case | Personas | Rubric avg | Notable floor fails |
|------|----------|------------|---------------------|
| G01 | pharmacist, clinician | 69 | dedup, relevance_lead, no_verbatim_dump |
| G02 | pharmacist | 66 | no_verbatim_dump |
| G03 | clinician | 73 | (rubric overall &lt;80) |
| G04 | researcher | 60 | coverage/correctness floors |
| G05 | researcher | 59 | relevance_lead (wrong lead paper) |
| G06 | alt practitioner, patient | ~52 | coverage/correctness |
| G07 | physiotherapist | ~57 | — |
| G08 | patient | — | persona/coverage risk |
| G09 | neuroscientist, pharmacist | ~59 | coverage |
| G10 | pharmacist | 46 | no_verbatim_dump; weak coverage of boxed warnings |
| G11 | clinician | 66 | no_verbatim_dump |
| G12 | general | 31 | off-topic lead (hearing loss); absence behaviour weak |
| G13 | researcher | 45 | **dedup** + **distinct_source_count** (inflated xv) + verbatim |
| G14 | medical_student | 62 | coverage/correctness |
| G15 | lecturer | 61 | no_verbatim_dump |
| G16 | patient | 32 | guardrail not engaged; no warm redirect |

---

## What was built (Phase 2)

| Piece | Path |
|-------|------|
| Rubric grader (5 criteria, ≥80 overall, ≥60 floor) | `backend/evals/rubric.py` |
| Mechanical floor (E1–E3, E5, E9, STALE, …) | `backend/evals/assertions.py` |
| Runner (rubric ∧ floor; holdout sealed) | `backend/evals/runner.py` |
| Golden fixtures G01–G16 | `backend/evals/golden/G*.json` |
| Fixture builder | `backend/evals/build_golden_v2.py` |
| Legacy v1 cases | `backend/evals/golden/_legacy_v1/` |
| Answer keys (human) | `docs/PULSE_GOLDEN_ANSWER_KEYS.md` |

---

## OWNER GATE

Confirm:
1. Eval design + keys + this baseline capture “answers the question well.”
2. Offline rubric is acceptable for this agent baseline; re-run with `OPENAI_API_KEY` before trusting persona scores in CI.
3. **No pipeline fixes until you approve Checkpoint 2.**

Then Phase 3 (read-only fix-site map) → Phase 4 repair loop.
