---
title: "Sprint 2 — User Stories"
tags: [type/user-story, sprint/2, status/done]
sprint: 2
generated_at: "2026-05-11T14:42:01Z"
generated: true
---

# Sprint 2 — User Stories

| ID | Story | Points | Slice | Status |
|----|-------|--------|-------|--------|
| 2.1 | Implement clarification trigger policy | 5 | slice/2 | status/done |
| 2.2 | Return taxonomy-backed clarification chips | 5 | slice/2 | status/done |
| 2.3 | Add kiosk clarification chip UI | 5 | slice/2 | status/done |
| 2.4 | Implement clarification retry contract | 8 | slice/2 | status/done |
| 2.5 | Persist clarification resolution | 3 | slice/2 | status/done |
| 2.6 | Log clarification lifecycle events | 3 | slice/2 | status/done |
| 3.1 | Implement metadata validation rule engine | 8 | slice/3 | status/done |
| 3.2 | Add validation status and audit storage | 8 | slice/3 | status/done |
| 3.3 | Gate KB publish using validation results | 8 | slice/3 | status/carried-over → Sprint 3 |

---

## Story detail

### 2.1 — Implement clarification trigger policy
**Points:** 5
**Slice:** [[30-decisions/slice-2|Slice 2 — Clarify-first UX]]
**Goal:** goal/6, goal/10, goal/12
**Labels:** `backend`, `intent`, `clarification`, `logging`

**Acceptance snapshot:** Trigger on low confidence, unclear intent + low score, or missing required scope; use stable reason codes and deterministic behavior.

**Status:** ✅ Done

> 🔍 Inferred: The trigger policy lives inside `hub/retrieval/pipeline.py` or a dedicated clarification module called by the pipeline before rewrite. Reason codes are stable strings (e.g., `low_confidence`, `unclear_intent`, `missing_scope`) used both in the response and in logs.

---

### 2.2 — Return taxonomy-backed clarification chips
**Points:** 5
**Slice:** [[30-decisions/slice-2|Slice 2 — Clarify-first UX]]
**Goal:** goal/6, goal/7, goal/12
**Labels:** `backend`, `api`, `clarification`, `taxonomy`

**Acceptance snapshot:** Return 2–3 stable chip options mapped to taxonomy nodes; mark request as paused; deterministic chip ordering.

**Status:** ✅ Done
**Evidence:** Commit `717a46d` (2026-05-10) — "feat: implement taxonomy-backed clarification chips (S2P2)"
**Files:** `hub/api/routes_query.py`, `hub/models/api_models.py`

`ClarificationContext` (added in Sprint 1 Story 0.3) now carries an `options: [{id, label}]` list where each `id` is a stable taxonomy node ID (e.g., `rk.tax.food.meals`). Chip ordering is deterministic via the Goal 7 chip policy (default 3 chips, at most one conditional replacement when strongly indicated).

---

### 2.3 — Add kiosk clarification chip UI
**Points:** 5
**Slice:** [[30-decisions/slice-2|Slice 2 — Clarify-first UX]]
**Goal:** goal/6
**Labels:** `kiosk`, `ui`, `clarification`, `android`

**Acceptance snapshot:** Show prompt and 2–3 selectable chips; submit selected option; avoid final answer until resolved.

**Status:** ✅ Done
**Evidence:** Commit `a0de312` (2026-05-11) — "Delivered Slice 2 Story 3"
**Files:** `kiosk/.../ui/MainKioskScreen.kt`, `kiosk/.../viewmodel/KioskViewModel.kt`, `kiosk/.../network/HubApiClient.kt`

The kiosk now renders clarification chips when the hub response carries `NEEDS_CLARIFICATION` answer type. Tapping a chip POSTs back to `/query` with the original transcript + the selected chip context. The chat bubble area is suppressed until the second-pass response arrives.

---

### 2.4 — Implement clarification retry contract
**Points:** 8
**Slice:** [[30-decisions/slice-2|Slice 2 — Clarify-first UX]]
**Goal:** goal/6, goal/12
**Labels:** `backend`, `api`, `kiosk`, `clarification`, `pipeline`

**Acceptance snapshot:** Send selected option and original context; resolve selection to taxonomy/intent; resume pipeline only after clarification is resolved.

**Status:** ✅ Done

> 🔍 Inferred: The retry request shape includes `original_transcript`, `selected_taxonomy_node_id` (and/or `selected_option_id`), and a follow-up token from the original `ClarificationContext`. The pipeline maps the chip to a resolved intent via `intent_taxonomy_map` (Sprint 1) and proceeds straight to retrieval, bypassing the clarification gate.

---

### 2.5 — Persist clarification resolution
**Points:** 3
**Slice:** [[30-decisions/slice-2|Slice 2 — Clarify-first UX]]
**Goal:** goal/6, goal/10
**Labels:** `backend`, `db`, `logging`, `clarification`

**Acceptance snapshot:** Store option ID/label or recoverable label, session ID, resolved intent/taxonomy, language, and query-log linkage.

**Status:** ✅ Done

> 🔍 Inferred: `clarification_resolutions` table (already noted in `aaih-increment-goals.md` session notes) gains rows on every chip submission. Fields: `session_id`, `selected_option_id`, `resolved_intent`, `resolved_taxonomy_node_id`, `language`, `query_log_id`, `created_at`.

---

### 2.6 — Log clarification lifecycle events
**Points:** 3
**Slice:** [[30-decisions/slice-2|Slice 2 — Clarify-first UX]]
**Goal:** goal/6, goal/10, goal/12
**Labels:** `backend`, `logging`, `clarification`, `pipeline`

**Acceptance snapshot:** Log trigger, reason codes, options, selection, resolved node/intent, and proof that rewrite/retrieval waited.

**Status:** ✅ Done

> 🔍 Inferred: Builds on Sprint 1's `[Filter]`-tagged log convention with a new `[Clarification]` tag prefix. Each query that triggers clarification produces a sequence of log lines showing trigger reason, options offered, then (on retry) the option selected and resolved node — and the pipeline log shows rewrite/retrieval did not run on the first pass.

---

### 3.1 — Implement metadata validation rule engine
**Points:** 8
**Slice:** [[30-decisions/slice-3|Slice 3 — Trusted KB Publish]]
**Goal:** goal/8
**Labels:** `backend`, `validation`, `metadata`, `kb-publish`, `safety-critical`

**Acceptance snapshot:** Evaluate taxonomy, authority, scope, caption/label quality; return rule ID, severity, result, message; offline deterministic behavior.

**Status:** ✅ Done
**Evidence:** Commit `beabff3` (2026-05-09) — "slice 3 story 1 delivered"
**Files:** `hub/validation/metadata.py`, `hub/validation/__init__.py`, `hub/tests/test_metadata_validation.py`

The engine evaluates **10 rules** across taxonomy assignments, authority/scope metadata, and content label quality. See [[30-decisions/slice-3]] for the full rule table.

---

### 3.2 — Add validation status and audit storage
**Points:** 8
**Slice:** [[30-decisions/slice-3|Slice 3 — Trusted KB Publish]]
**Goal:** goal/8, goal/10
**Labels:** `backend`, `db`, `db-migration`, `validation`, `audit`

**Acceptance snapshot:** Persist approved/quarantined/needs_review/rejected states, rule results, review decisions, and KB version/publish attempt linkage.

**Status:** ✅ Done
**Evidence:** Schema confirmed in `hub/db/schema.py` — `kb_validation_results` table exists
**Files:** `hub/db/schema.py`, `hub/db/migrate_schema.py`

The `kb_validation_results` table persists validation outcomes with KB version linkage. The `clarification_resolutions` table (Story 2.5) records chip selections with query-log linkage. Together these enable historical publish attempt and clarification lifecycle reconstruction.

---

### 3.3 — Gate KB publish using validation results
**Points:** 8
**Slice:** [[30-decisions/slice-3|Slice 3 — Trusted KB Publish]]
**Goal:** goal/8
**Labels:** `backend`, `api`, `kb-publish`, `validation`, `safety-critical`

**Acceptance snapshot:** Run validation before publish; return pass/blocked/warning; quarantine excluded from retrieval; preserve current published KB on failure.

**Status:** ⏭️ Carried over to Sprint 3 — landed `0fd6ffb` on 2026-05-11
**Evidence:** Commit `0fd6ffb` (2026-05-11) — "slice 3 story 3 done! wraaagh!"

> 🔍 Inferred: `POST /admin/publish` now calls `build_publish_gate_handoff()` and returns HTTP 422 with `PublishGateHandoff.failure_reasons` when `PUBLISH_STATUS_BLOCKED`. Counted here as Sprint 2 work (it was on the Sprint 2 plan and the validation engine was finished May 9) but the actual route wiring committed on Sprint 3 day 1. See [[20-sprints/sprint-3/user-stories]] for the Sprint 3 view.
