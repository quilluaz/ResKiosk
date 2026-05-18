---
title: "Increment Goals (AAIH 2026) — Index"
aliases: ["goals", "12 goals", "product goals"]
tags: [type/decision, status/active]
sprint: null
generated_at: "2026-05-11T11:37:24Z"
generated: true
---

# Increment Goals (AAIH 2026)

ResKiosk's AAIH product increment is organized around **12 numbered goals** grouped into **4 product-goal epics**. Build order is set by the four epics' priority, with Goal 12 (canonical pipeline) and Goal 7 (filtering) front-loaded because everything else depends on them.

This note is an **index** — each goal has a detailed outline at `ai_helper/goal_outlines/goal_<N>.md` in the repo. The Sprint 1 post-sprint doc and the increment goals doc are also worth reading directly.

**Source documents:**
- `ai_helper/aaih-increment-goals.md` — full goal definitions (source of truth)
- `ai_helper/goal_outlines/goal_<N>.md` — deep-dive per goal
- `ai_helper/implementation_slices_sequence.md` — how goals are sliced for delivery
- `ai_helper/sprint-plan.md` — when each goal lands

---

## Product-goal epics (priority order)

| Priority | Epic | Goals | Why first/last |
|---------:|------|-------|----------------|
| 1 | **Goal C — Safety & Controlled Interaction** | 6, 7, 8, 12 | Safety-critical: pipeline order, filtering, clarification, publish validation must be enforced before accuracy improvements |
| 2 | **Goal A — Accuracy & Reliability** | 4, 5, 9 | Hybrid retrieval + multi-path raise quality only on a safe foundation |
| 3 | **Goal D — Observability & Trust** | 10, 11 | Measure before optimizing further (10), then cache safely (11) |
| 4 | **Goal B — Visual Guidance / Multimodal** | 1, 2, 3 | Highest reach but requires schema, retrieval, and measurement to be solid first |

---

## 12 numbered goals

### Goal 1 — Semantic image search (CLIP/SigLIP)
- **Was:** text-only embedding retrieval, no image encoder
- **Outcome:** image ↔ text semantic search with image evidence in responses
- **Sprints:** 5 (model selection), 7 (embeddings + retrieval), 7 (kiosk render)
- **Slices:** [[30-decisions/slice-7c|7C]], [[30-decisions/slice-7d|7D]]

### Goal 2 — Image storage as first-class KB assets
- **Was:** images not modeled as first-class assets
- **Outcome:** durable image assets with original + thumbnail + content hash + kb_version linkage
- **Sprints:** 5–7
- **Slices:** 7B, 7D

### Goal 3 — KB schema rework for multimodal retrieval
- **Was:** schema supports only text embeddings
- **Outcome:** modality field, asset refs, forward-compatible segmentation fields
- **Sprints:** 5
- **Slices:** 7A

### Goal 4 — Hybrid retrieval (BM25 + vectors)
- **Was:** vector-only retrieval, no lexical path
- **Outcome:** hybrid lexical + vector with deterministic RRF fusion
- **Sprints:** 3 (this sprint)
- **Slices:** [[30-decisions/slice-4|Slice 4]] ← active
- **Detail:** `ai_helper/goal_outlines/goal_4.md`

### Goal 5 — Multi-path retrieval
- **Was:** single-pass retrieval that flattens compound queries
- **Outcome:** compound queries split into intent-scoped paths + deterministic merge
- **Sprints:** 4
- **Slices:** 5

### Goal 6 — Clarification UX before rewriting
- **Was:** limited ambiguity handling — pipeline guessed instead of asking
- **Outcome:** UI clarification chips before rewrite/retrieval; chip selection resumes pipeline
- **Sprints:** 1 (pause state), 2 (full UX) — ✅ delivered
- **Slices:** [[30-decisions/slice-0|Slice 0]] (pause state), [[30-decisions/slice-2|Slice 2]] (full UX)

### Goal 7 — Metadata schema + filtering policy
- **Was:** filtering not formally enforced
- **Outcome:** precedence rules — Hard rules > UI filters > Inferred intent — logged and explainable
- **Sprints:** 1 — ✅ delivered
- **Slices:** [[30-decisions/slice-1|Slice 1]]

### Goal 8 — Metadata validation gate
- **Was:** no validation before publish
- **Outcome:** rule-based engine + human review workflow; quarantine excluded from retrieval
- **Sprints:** 2 (engine + storage), 3 (publish gate + console + retrieval exclusion + audit)
- **Slices:** [[30-decisions/slice-3|Slice 3]] (3.3 ✅, 3.4–3.6 🔄)

### Goal 9 — Retrieval quality improvements
- **Was:** feedback bias only (not true reranking)
- **Outcome:** improve via hybrid retrieval + multi-path + clarification (no cross-encoder reranker in MVP)
- **Sprints:** 3 (via Goal 4), 4 (via Goal 5), stretch (feedback-adjusted ranking 4.7)
- **Slices:** [[30-decisions/slice-4|Slice 4]], 5

### Goal 10 — MVP metrics + logging
- **Was:** basic unstructured logs only
- **Outcome:** structured query logs computable per KB version covering grounding, evidence match, latency
- **Sprints:** 3 (schema + failure logs), 4 (latency + evidence + readable logs), 5 (export + KPI reports)
- **Slices:** [[30-decisions/slice-6a|Slice 6A]] ← active

### Goal 11 — Safer caching patterns
- **Was:** in-memory caches only (`_corpus_cache`, `_shelter_config_cache`)
- **Outcome:** version-aware response cache with TTL + invalidation hooks on publish/config
- **Status:** ⏸ Deferred / stretch (all of Slice 6B = 44 pts)
- **Slices:** 6B (stretch)

### Goal 12 — Canonical pipeline order
- **Was:** pipeline not enforced; rewrite could run before clarification
- **Outcome:** normalize → intent → clarification → constrained rewrite → retrieval, all logged deterministically
- **Sprints:** 1 — ✅ delivered
- **Slices:** [[30-decisions/slice-0|Slice 0]]

---

## Delivery status snapshot (2026-05-11)

| Goal | Status | Where |
|------|--------|-------|
| 6 | ✅ Delivered | Sprint 1 (pause) + Sprint 2 (chips/UX) |
| 7 | ✅ Delivered | Sprint 1 |
| 12 | ✅ Delivered | Sprint 1 |
| 8 | 🔄 In progress | Sprint 2 (engine) + Sprint 3 (gate + console + exclusion + audit) |
| 4 | 🔄 Starting | Sprint 3 (Slice 4 — hybrid retrieval) |
| 10 | 🔄 Starting | Sprint 3 (Slice 6A schema) + Sprint 4–5 (metrics) |
| 9 | ⏳ Pending | Mostly delivered via Goals 4 + 5; 4.7 deferred |
| 5 | ⏳ Pending | Sprint 4 (Slice 5) |
| 3 | ⏳ Pending | Sprint 5 (Slice 7A) |
| 1 | ⏳ Pending | Sprint 5 (model) + Sprint 7 (retrieval + kiosk) |
| 2 | ⏳ Pending | Sprint 5–7 (Slices 7B + 7D) |
| 11 | ⏸ Deferred / stretch | Slice 6B (44 pts) |

---

## Global assumptions (apply to all goals)

- **English at retrieval boundary** — all non-English inputs translated via NLLB-200 before retrieval.
- **Scale** — ~1k–5k KB articles per shelter.
- **No semantic chunking this increment** — retrieval unit remains one `kb_articles` row.
- **Stable ranking** — deterministic for fixed `(kb_version, config, query, filters)`. Only exception is explicit feedback bias.

---

## Related

- [[00-pre-sprint-baseline/_index|Pre-sprint baseline]] — what existed before any goals were delivered
- [[20-sprints/sprint-1/_index|Sprint 1]] — Goals 6 (pause), 7, 10 (skeleton), 12 delivered
- [[20-sprints/sprint-2/_index|Sprint 2]] — Goal 6 (full UX), Goal 8 (engine + storage) delivered
- [[20-sprints/sprint-3/_index|Sprint 3]] — Goals 4, 8 (finishing), 10 (schema) active
