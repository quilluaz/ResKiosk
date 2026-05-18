---
title: "Sprint 1 — User Stories"
tags: [type/user-story, sprint/1, status/done]
sprint: 1
generated_at: "2026-05-11T07:32:20Z"
generated: true
---

# Sprint 1 — User Stories

| ID | Story | Points | Slice | Status |
|----|-------|--------|-------|--------|
| 0.1 | Create canonical pipeline orchestrator | 8 | slice/0 | status/done |
| 0.2 | Add pipeline stage logging skeleton | 5 | slice/0 | status/done |
| 0.3 | Add clarification pause state to query flow | 5 | slice/0 | status/done |
| 1.1 | Define taxonomy v1 data model | 5 | slice/1 | status/done |
| 1.2 | Add metadata fields for retrieval filtering | 8 | slice/1 | status/done |
| 1.3 | Enforce hard retrieval rules | 5 | slice/1 | status/done |
| 1.4 | Apply UI and inferred intent filters with precedence | 5 | slice/1 | status/done |
| 1.5 | Log filter decisions and candidate counts | 3 | slice/1 | status/done |

---

## Story detail

### 0.1 — Create canonical pipeline orchestrator
**Points:** 8  
**Slice:** [[30-decisions/slice-0|Slice 0 — Backbone Contract]]  
**Goal:** goal/12  
**Labels:** `backend`, `pipeline`, `goal-12`, `slice-0`

**Acceptance snapshot:**
Route all hub query handling through one canonical pipeline path; preserve existing /query behavior; prove stage order with tests.

**Status:** ✅ Done  
**Evidence:** Commit a326ebb (2026-05-03) — "Slice 0 : Story 1 (Canonical Pipeline) complete"

> 🔍 Inferred: The canonical pipeline orchestrator likely lives in `hub/retrieval/` or `hub/api/` and coordinates the flow: normalize → intent → clarification check → rewrite (optional) → retrieval → formatting.

---

### 0.2 — Add pipeline stage logging skeleton
**Points:** 5  
**Slice:** [[30-decisions/slice-0|Slice 0 — Backbone Contract]]  
**Goal:** goal/10  
**Labels:** `backend`, `logging`, `pipeline`, `goal-10`, `slice-0`

**Acceptance snapshot:**
Capture normalized query, intent, clarification trigger, rewrite state, retrieval source/score where available; keep payload bounded.

**Status:** ✅ Done  
**Evidence:** Commit 70256b3 (2026-05-03) — "Completed Person 2: Story 2 - Add pipeline stage logging skeleton and Story 5 - Log filter decisions and candidate counts"

> 🔍 Inferred: Logging is likely structured and stored in a query_log table or similar, with fields for request_id, timestamp, stage name, stage-specific metadata.

---

### 0.3 — Add clarification pause state to query flow
**Points:** 5  
**Slice:** [[30-decisions/slice-0|Slice 0 — Backbone Contract]]  
**Goal:** goal/6, goal/12  
**Labels:** `backend`, `api`, `clarification`, `pipeline`, `goal-6`, `goal-12`, `slice-0`

**Acceptance snapshot:**
Return structured needs-clarification response; skip rewrite/retrieval while paused; include resume context; keep non-clarification flow unchanged.

**Status:** ✅ Done  
**Evidence:** Commit 4f29463 (2026-05-03) — "Feat: Added Clarification Pause State to Query Flow"

> 🔍 Inferred: The API response now includes a `needs_clarification` flag or similar status field. When set, the pipeline skips retrieval and formatter stages, instead returning clarification options and context to resume later.

---

### 1.1 — Define taxonomy v1 data model
**Points:** 5  
**Slice:** [[30-decisions/slice-1|Slice 1 — Controlled Scope Foundation]]  
**Goal:** goal/7  
**Labels:** `backend`, `db`, `taxonomy`, `filtering`, `goal-7`, `slice-1`

**Acceptance snapshot:**
Represent stable taxonomy IDs, labels, intent mappings, and chip compatibility without breaking current retrieval.

**Status:** ✅ Done  
**Evidence:** Commit 97c82ae (2026-05-01) — "slide 1 story 1 completed"

> 🔍 Inferred: A new `taxonomy` or `taxonomy_nodes` table was added to the SQLite schema. Likely includes fields: `id`, `label`, `parent_id`, `intent_mappings`, `chip_compatible`. This represents the hierarchical taxonomy structure used for filtering KB items (e.g., food > meals > breakfast).

---

### 1.2 — Add metadata fields for retrieval filtering
**Points:** 8  
**Slice:** [[30-decisions/slice-1|Slice 1 — Controlled Scope Foundation]]  
**Goal:** goal/7  
**Labels:** `backend`, `db`, `db-migration`, `metadata`, `filtering`, `goal-7`, `slice-1`

**Acceptance snapshot:**
Add taxonomy, authority/source, and scope/context metadata; backfill safely; preserve text-only retrieval.

**Status:** ✅ Done  
**Evidence:** Commit ded5b36 (2026-05-01) — "slice 1 user story 2 delivered"

> 🔍 Inferred: The `kb_items` or `articles` table was extended with new metadata columns:
> - `taxonomy_id` — foreign key to taxonomy table
> - `authority_source` — e.g., "Red Cross", "WHO", "Local Admin"
> - `scope_context` — e.g., "General", "This Shelter Only", "Region-specific"
> 
> A migration script backfilled existing KB items with default/null values to preserve backward compatibility.

---

### 1.3 — Enforce hard retrieval rules
**Points:** 5  
**Slice:** [[30-decisions/slice-1|Slice 1 — Controlled Scope Foundation]]  
**Goal:** goal/7  
**Labels:** `backend`, `retrieval`, `filtering`, `safety-critical`, `goal-7`, `slice-1`

**Acceptance snapshot:**
Exclude enabled=false and non-published content before UI/inferred filters; log exclusion reasons; preserve valid published results.

**Status:** ✅ Done  
**Evidence:** Part of filtering work completed by May 3

> 🔍 Inferred: Hard rules are applied in the retrieval pipeline before any other filtering logic:
> 1. Exclude where `enabled = false`
> 2. Exclude where `published = false` or `publish_status != 'published'`
> 
> These exclusions happen regardless of user intent or UI filters, forming a safety-critical gate. Exclusion reasons are logged for audit.

---

### 1.4 — Apply UI and inferred intent filters with precedence
**Points:** 5  
**Slice:** [[30-decisions/slice-1|Slice 1 — Controlled Scope Foundation]]  
**Goal:** goal/7  
**Labels:** `backend`, `retrieval`, `filtering`, `taxonomy`, `logging`, `goal-7`, `slice-1`

**Acceptance snapshot:**
Apply hard > UI > inferred precedence deterministically; log filter source and decisions.

**Status:** ✅ Done  
**Evidence:** Part of filtering work completed by May 3

> 🔍 Inferred: Filter precedence hierarchy:
> 1. **Hard rules** — safety-critical, always applied first
> 2. **UI filters** — explicitly selected taxonomy nodes or filters from kiosk/console UI
> 3. **Inferred filters** — taxonomy nodes or context inferred from intent classification
> 
> Later filters cannot override earlier ones. If UI filter selects "food", inferred filter cannot expand to "medical". Deterministic application order ensures repeatable results.

---

### 1.5 — Log filter decisions and candidate counts
**Points:** 3  
**Slice:** [[30-decisions/slice-1|Slice 1 — Controlled Scope Foundation]]  
**Goal:** goal/7, goal/10  
**Labels:** `backend`, `logging`, `filtering`, `observability`, `goal-7`, `goal-10`, `slice-1`

**Acceptance snapshot:**
Log hard rules, selected taxonomy node, inferred nodes, candidate counts, widening/fallback events, and query-log linkage.

**Status:** ✅ Done  
**Evidence:** Commit 70256b3 (2026-05-03) — "Completed Person 2: Story 2 - Add pipeline stage logging skeleton and Story 5 - Log filter decisions and candidate counts"

> 🔍 Inferred: Filter logging captures:
> - `hard_rules_applied` — list of exclusion rules (e.g., ["enabled=false", "unpublished"])
> - `ui_filter_taxonomy_id` — explicitly selected taxonomy node (if any)
> - `inferred_taxonomy_ids` — nodes inferred from intent (if any)
> - `candidate_count_pre_filter` — total KB items before filtering
> - `candidate_count_post_filter` — items remaining after all filters
> - `widening_triggered` — boolean, did the system need to relax filters due to zero results?
> - `query_log_id` — link to parent query log record
