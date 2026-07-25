# CHECKPOINT 3 — Platform-wide fix sites (read-only)

**Date:** 2026-07-25  
**Branch:** `cursor/pulse-phase2-eval-1f1a`  
**Rule:** one shared, topic-agnostic fix site per defect. No drug/disease/query special-casing.

Target pipeline order:

`retrieve → DEDUP → extract claims → score claim relevance → reconcile → score PULSE → compose → self-check → render`

---

## Defect → single fix site

| ID | Defect | Fix site (file · function) | Topic-agnostic? |
|----|--------|----------------------------|-----------------|
| **E1** | Same work in multiple DBs counted as independent sources | **New** shared dedup step in `search_orchestrator.run_search` **before** `run_pulse_validation`, plus counting in `pulse_engine.run_pulse_validation` (cross-val loop ~L637) must use **work_id** (DOI→PMID→normalized title), not `source_name` alone | Yes — identity keys only |
| **E2** | Irrelevant claims lead the brief | `claim_pipeline.run_claim_pipeline` / new `score_claim_relevance(query, claims)` then `claims_for_composition` ordered by relevance×coverage of decomposed sub-questions — **not** retrieval rank | Yes — query-token / sub-question overlap, no disease names |
| **E3** | Verbatim claim dump | `claim_pipeline.compose_brief` — constrained LLM (or structured) prose over selected claims; keep `verify_brief` + `no_verbatim_dump` | Yes |
| **E4** | Question parts unanswered | New `decompose_query(query)` in `claim_pipeline` (or thin helper module); brief must cover each part or state absence; feeds E2 selection | Yes — structural decomposition (compare, mechanism, status, …) |
| **E5** | False-positive divergence | `claim_pipeline.reconcile_claims` — only same-proposition groups; raise similarity / require shared proposition; drop token-fragment topics | Yes |
| **E6** | Missed real contradiction / supersession | `claim_pipeline.reconcile_claims` + `_classify_members` — polarity + timeframe on same proposition; surface via `surfaceable_edge_cases` | Yes |
| **E7** | Token n-gram themes | `pulse_engine.run_pulse_validation` theme block (~L739) — real clusters from claim groups or **omit** | Yes |
| **E8** | Query type ≠ source-class priority | `search_orchestrator.plan_sources_for_query` / `classify_query_type` — already partial; ensure ranking/composition prefer planned class (label vs trial vs literature) without topic names | Yes — class mapping only |
| **E9** | Confidence ↔ status coherent | `pulse_engine.status_for_confidence` + `PULSEReport.refresh_status` — **preserve**; keep golden assertions | Yes — already rubric-pure |

---

## Explicit non-sites

- No per-persona pipeline forks (`persona.py` stays delivery-only).
- No query/drug/disease branches in dedup, relevance, or reconcile.
- No schema migration without owner ask.
- Retrieval clients untouched unless Phase 4 proves retrieval drops correct works (Phase 1/2 baseline did not).

---

## CHECKPOINT 3 — **PASS**

Every defect E1–E9 maps to one shared, topic-agnostic site. Safe to enter Phase 4 repair loop (one defect at a time, golden battery after each).

**OWNER:** approve Checkpoint 3 to start Phase 4 at **E1**.
