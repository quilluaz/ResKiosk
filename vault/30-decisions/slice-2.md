---
title: "Slice 2 — Clarify-first UX"
aliases: ["slice 2", "clarify-first UX"]
tags: [type/decision, slice/2, goal/6, goal/10, goal/12, status/done]
sprint: 2
generated_at: "2026-05-11T07:53:18Z"
generated: true
---

# Slice 2 — Clarify-first UX

**Related goals:** Goal 6 (Clarification & Disambiguation), Goal 10 (Observability), Goal 12 (Pipeline Safety)  
**Sprint:** Sprint 2 (May 4–May 10)  
**Status:** ✅ Completed  
**Work items:** 6  
**Story points:** 29

---

## Overview

Slice 2 built out the full clarification experience that was scaffolded in Slice 0 (Story 0.3). Where Sprint 1 established the _pause state_ in the pipeline, Slice 2 made it actually usable: taxonomy-backed chip selection, kiosk UI, session pause/resume, and proper logging.

The central design insight: rather than returning a low-confidence answer, the hub asks the user to pick a topic category. This turns an uncertain situation into a deterministic one on the second pass.

---

## Goals

### Goal 6 — Clarification & Disambiguation
When a query is ambiguous, prompt the user with specific category chips rather than guessing. Chips must be meaningful (taxonomy-backed) and limited to 3 to avoid overwhelming a stressed user.

### Goal 10 — Observability & Trust
Log clarification events structurally so operators can see how often clarification fires and which categories users select.

### Goal 12 — Pipeline Safety & Control
Clarification must gate the rewrite and retry stages — a paused pipeline must not continue to stage 5 or 6.

---

## Work Items

| ID | Work Item | Points | Status |
|----|-----------|--------|--------|
| 2.1 | Define clarification trigger policy | 5 | ✅ Done |
| 2.2 | Implement taxonomy-backed chip selection | 8 | ✅ Done |
| 2.3 | Build clarification chip UI on kiosk | 5 | ✅ Done |
| 2.4 | Implement session pause/resume | 5 | ✅ Done |
| 2.5 | Log clarification events | 3 | ✅ Done |
| 2.6 | Add clarification resolution to DB | 3 | ✅ Done |

See [[20-sprints/sprint-2/user-stories]] for full acceptance criteria.

---

## Key Decisions

### 2-D1: Taxonomy-backed chips over free-text categories

**Decision:** Clarification chips are selected from `taxonomy_v1.json` using a deterministic policy (default set + conditional replacements), not from free-text category strings.

**Why:** Free-text categories are fragile — any rename in the KB would silently break the chip logic. Taxonomy node IDs are stable (`rk.tax.*`), so chips stay correct even as KB content evolves.

**Consequence:** The kiosk must send back `selected_taxonomy_node_id` (not just `selected_category`) to enable precise filtering on the second retrieval pass.

---

### 2-D2: Max 3 chips per clarification prompt

**Decision:** Hard cap at 3 chips regardless of how many nodes could theoretically match.

**Why:** ResKiosk users are stressed, displaced, and often not native speakers. A 3-chip choice is a simple decision; 5+ chips would create cognitive overload. 3 covers the most common ambiguous scenarios (food/medical/registration).

**Consequence:** The chip selection policy must be opinionated about which 3 to show. The `conditional_replacements` mechanism allows one default to be swapped when signals strongly indicate a specific sub-domain.

---

### 2-D3: ClarificationResolution table for training data

**Decision:** Every successful clarification resolution (user selects a chip) is written to `clarification_resolutions` as a gold-label record.

**Why:** These are high-quality supervised signals: the user's original query plus the correct intent they picked. Accumulating this table enables future intent classifier fine-tuning.

**Consequence:** `clarification_resolutions` should never be deleted. It is training data.

---

### 2-D4: Clarification rewrite-block is a hard invariant

**Decision:** When `pipeline_status == "paused"` (clarification triggered), the pipeline returns immediately at Stage 4. Rewrite (Stage 5) and retrieve_retry (Stage 6) are never executed.

**Why:** Running the rewriter on an ambiguous query would produce a rewritten query that might falsely resolve to a match — bypassing the clarification intent. The whole point of clarification is to admit uncertainty and ask the user.

**Consequence:** `QueryPipeline.run()` has an explicit early `return result` at Stage 4 when clarification fires. Tests in `hub/tests/test_pipeline_order.py` assert this invariant.

---

## Architectural Impact

### New Pydantic Models (hub/models/api_models.py)

- `ClarificationContext` — full context for pause/resume (original query, intent, confidence, chips, session ID)
- `TaxonomyOption` — `{ id, label }` chip descriptor
- `QueryResponse.clarification_context` — optional field, populated only on `NEEDS_CLARIFICATION`
- `QueryResponse.clarification_options` — list of `TaxonomyOption` (taxonomy-backed)

### New DB Table

- `clarification_resolutions` — logs gold-label intent selections for future training

### Updated Files

| File | Change |
|------|--------|
| `hub/retrieval/pipeline.py` | Stage 4 clarification gate enforces early return |
| `hub/retrieval/search.py` | `_deterministic_clarification_node_ids()` + chip policy loader |
| `hub/models/api_models.py` | `ClarificationContext`, `TaxonomyOption`, updated `QueryResponse` |
| `hub/db/schema.py` | `ClarificationResolution` table |
| `hub/api/routes_query.py` | Populates `clarification_context`, logs resolutions |
| `kiosk/.../MainKioskScreen.kt` | Chip UI rendering + selection handler |
| `kiosk/.../KioskViewModel.kt` | Handles `NEEDS_CLARIFICATION` response, triggers re-query |

---

## Thresholds

| Threshold | EN | Non-EN |
|-----------|----|--------|
| Direct match (above = answer) | 0.60 | 0.50 |
| Clarification floor (below = no match) | 0.40 | 0.38 |
| In between → `NEEDS_CLARIFICATION` | ✅ | ✅ |

---

## Evidence

| Commit | Date | Author | Message |
|--------|------|--------|---------|
| 4f29463 | 2026-05-03 | Selina Mae Genosolango | Feat: Added Clarification Pause State to Query Flow |
| beabff3 | 2026-05-09 | keithruezyl1 | slice 3 story 1 delivered |
| 0fd6ffb | 2026-05-11 | keithruezyl1 | slice 3 story 3 done! wraaagh! |

> 🔍 Inferred: Stories 2.1–2.6 are attributed to Sprint 2 based on dates. Exact per-story commit hashes are not distinguishable from commit messages alone, but the clarification system is confirmed active in the codebase.

---

## Related

- [[30-decisions/slice-0]] — Backbone Contract (Sprint 1 — established the pause state)
- [[30-decisions/slice-3]] — Trusted KB Publish (Sprint 2–3 — validation pipeline)
- [[10-architecture/clarification-system]] — Living architecture doc for the clarification system
- [[10-architecture/voice-pipeline]] — Full pipeline including clarification gate
- [[10-architecture/intent-system]] — Intent classifier driving clarification decisions
