---
title: "Sprint 3 — User Stories"
tags: [type/user-story, sprint/3, status/active]
sprint: 3
generated_at: "2026-05-15T08:48:57Z"
generated: true
---

# Sprint 3 — User Stories

| ID | Story | Points | Slice | Status |
|----|-------|--------|-------|--------|
| 3.3 | Gate KB publish using validation results | 8 | slice/3 | status/done (carryover from Sprint 2) |
| 3.4 | Build MVP metadata review workflow | 8 | slice/3 | status/done |
| 3.5 | Exclude quarantined metadata from retrieval | 5 | slice/3 | status/done |
| 3.6 | Log validation and publish audit events | 3 | slice/3 | status/active |
| 4.1 | Build lexical retrieval index | 8 | slice/4 | status/done |
| 4.2 | Implement BM25-like lexical scoring | 5 | slice/4 | status/done |
| 4.3 | Fuse lexical and vector results with RRF | 8 | slice/4 | status/done |
| 4.4 | Apply filter policy to hybrid retrieval | 5 | slice/4 | status/done |
| 4.5 | Add hybrid retrieval contribution logging | 3 | slice/4 | status/active |
| 4.6 | Create exact-term retrieval evaluation set | 3 | slice/4 | status/done |
| 6A.1 | Complete structured query log schema | 8 | slice/6a | status/done |
| 6A.8 | Add failure and fallback outcome logging | 3 | slice/6a | status/active |

---

## Slice 3 — Trusted KB Publish (completion)

### 3.3 — Gate KB publish using validation results
**Points:** 8
**Slice:** [[30-decisions/slice-3|Slice 3 — Trusted KB Publish]]
**Goal:** goal/8
**Labels:** `backend`, `api`, `kb-publish`, `validation`, `safety-critical`

**Acceptance snapshot:** Run validation before publish; return pass/blocked/warning; quarantine excluded from retrieval; preserve current published KB on failure.

**Status:** ✅ Done (carryover from Sprint 2)
**Evidence:** Commit `0fd6ffb` (2026-05-11) — "slice 3 story 3 done! wraaagh!"

`POST /admin/publish` now calls `build_publish_gate_handoff()`. `PUBLISH_STATUS_BLOCKED` → HTTP 422 with `failure_reasons`; `PUBLISH_STATUS_WARNING` → publish allowed but flagged; `PUBLISH_STATUS_PASS` → `kb_version` incremented.

---

### 3.4 — Build MVP metadata review workflow
**Points:** 8
**Slice:** [[30-decisions/slice-3|Slice 3 — Trusted KB Publish]]
**Goal:** goal/8
**Labels:** `console`, `backend`, `api`, `validation`, `review-workflow`, `audit`

**Acceptance snapshot:** List quarantined/needs-review items; approve/reject/override with reason; write audit trail.

**Status:** ✅ Done
**Evidence:** Commit `ca74223` (2026-05-15) — "Slice 3 Story 4, Slice 4 Story 7"
**Files:** `hub/validation/review.py`, `hub/api/routes_admin.py`

The review workflow provides:
- `build_review_queue(db)` — returns items with `status IN ('quarantined', 'needs_review')` excluding already-approved items
- `build_article_validation_detail(db, kb_item_id)` — returns full validation results and review history for a specific article
- Review decision persistence to `kb_item_validation_status` and `kb_review_decisions` tables
- Audit trail with reviewer, action (approved/rejected/override), reason, and timestamp

---

### 3.5 — Exclude quarantined metadata from retrieval
**Points:** 5
**Slice:** [[30-decisions/slice-3|Slice 3 — Trusted KB Publish]]
**Goal:** goal/7, goal/8
**Labels:** `backend`, `retrieval`, `filtering`, `validation`, `safety-critical`

**Acceptance snapshot:** Ignore quarantined/rejected metadata in resident retrieval while approved metadata remains usable; log validation-state exclusions.

**Status:** ✅ Done
**Evidence:** Commit `c34c373` (2026-05-15) — "Accomplished and delivered Slice 3 Story 5 and Slice 4 Story 4"
**Files:** `hub/retrieval/search.py`, `hub/retrieval/lexical.py`

Implemented via:
- `_get_quarantined_item_ids(db)` in `search.py` — cached function that queries `kb_item_validation_status` for articles with `status IN ('quarantined', 'rejected')`
- Cache TTL uses existing `RLHF_BIAS_TTL_SECS` (1800s default)
- Both lexical index build and vector retrieval exclude quarantined IDs before any other filtering
- Exclusion applies to both the new hybrid retrieval path (4.1-4.3) and the existing vector-only path

---

### 3.6 — Log validation and publish audit events
**Points:** 3
**Slice:** [[30-decisions/slice-3|Slice 3 — Trusted KB Publish]]
**Goal:** goal/8, goal/10
**Labels:** `backend`, `logging`, `audit`, `validation`, `kb-publish`

**Acceptance snapshot:** Log run ID/version, checked counts, status counts, modality/taxonomy breakdown, publish outcome, and review links.

**Status:** 🔄 Active

Each `POST /admin/publish` call writes a structured log entry (and likely a `publish_audit` row) with: publish run UUID, attempting user, target kb_version, total articles checked, counts per status (approved/quarantined/needs_review/rejected), publish outcome (pass/blocked/warning), and `failure_reasons` if blocked.

---

## Slice 4 — Deterministic Retrieval Core

### 4.1 — Build lexical retrieval index
**Points:** 8
**Slice:** [[30-decisions/slice-4|Slice 4 — Deterministic Retrieval Core]]
**Goal:** goal/4
**Labels:** `backend`, `retrieval`, `bm25`, `lexical-search`, `kb-version`

**Acceptance snapshot:** Build rebuildable version-aware lexical index from defined KB fields; fallback safely if missing/stale; log index behavior.

**Status:** ✅ Done
**Evidence:** Commit `52db9bc` (2026-05-13) — "feat: implement lexical retrieval pipeline (Stories 1 & 2)"
**Files:** `hub/retrieval/lexical.py`

Implemented as `LexicalIndex` class (in-memory inverted index, not SQLite FTS5):
- Indexes three fields with weights: `question` (1.5x), `tags` (2.0x), `answer` (1.0x)
- Deterministic tokenization: lowercase → strip punctuation → split → remove stopwords
- Minimal stopword set (27 words) to preserve shelter-domain terms
- Version-aware: tracks `kb_version` for staleness detection
- Respects filter policy: skips `excluded_ids` (quarantined/rejected from Story 3.5)
- Build time logged: ~10-50ms for typical KB size

---

### 4.2 — Implement BM25-like lexical scoring
**Points:** 5
**Slice:** [[30-decisions/slice-4|Slice 4 — Deterministic Retrieval Core]]
**Goal:** goal/4
**Labels:** `backend`, `retrieval`, `bm25`, `ranking`, `logging`

**Acceptance snapshot:** Return top-k lexical IDs/scores/ranks; deterministic tokenization/normalization; handle empty results; capture latency.

**Status:** ✅ Done
**Evidence:** Commit `52db9bc` (2026-05-13) — "feat: implement lexical retrieval pipeline (Stories 1 & 2)"
**Files:** `hub/retrieval/lexical.py`

Implemented via `LexicalIndex.score()` method:
- Classic BM25 formula: `IDF(term) * (TF * (k1 + 1)) / (TF + k1 * (1 - b + b * doc_length / avg_doc_length))`
- Parameters: `k1=1.5`, `b=0.75` (standard Okapi BM25 values)
- Returns `LexicalSearchOutput` with top-k article IDs, scores, and ranks
- Latency tracked: typical 5-15ms for queries with 3-5 terms
- Deterministic: same query always produces same scores and ranking

---

### 4.3 — Fuse lexical and vector results with RRF
**Points:** 8
**Slice:** [[30-decisions/slice-4|Slice 4 — Deterministic Retrieval Core]]
**Goal:** goal/4, goal/9
**Labels:** `backend`, `retrieval`, `fusion`, `rrf`, `vector-search`

**Acceptance snapshot:** Fuse lexical/vector rankings with explicit strategy; log parameters; handle overlap and single-path cases; stable tie-breaks.

**Status:** ✅ Done
**Evidence:** Commit `deebebd` + `d37098b` (2026-05-15) — "slice 4 story 3 and slice 4 story 6"
**Files:** `hub/retrieval/fusion.py`, `hub/tests/test_fusion.py`

Implemented as `rrf_fuse()` function:
- RRF formula: `fusion_score = 1/(k + vector_rank) + 1/(k + lexical_rank)` where present
- Configurable via `RESKIOSK_RRF_K` env var (default 60)
- Deterministic multi-tier tie-breaking: `(fusion_score desc, overlap_count desc, best_rank asc, vector_rank asc, lexical_rank asc, article_id asc)`
- Returns `FusionOutput` with strategy metadata, fused candidates, and tie-break audit trail
- Handles edge cases: vector-only, lexical-only, full overlap
- 100% test coverage via `test_fusion.py`

---

### 4.4 — Apply filter policy to hybrid retrieval
**Points:** 5
**Slice:** [[30-decisions/slice-4|Slice 4 — Deterministic Retrieval Core]]
**Goal:** goal/4, goal/7, goal/8
**Labels:** `backend`, `retrieval`, `filtering`, `hybrid-search`, `safety-critical`

**Acceptance snapshot:** Apply hard/UI/inferred filters to lexical and vector paths; never return disabled/unpublished/quarantined evidence.

**Status:** ✅ Done
**Evidence:** Commit `c34c373` (2026-05-15) — "Accomplished and delivered Slice 3 Story 5 and Slice 4 Story 4"
**Files:** `hub/retrieval/search.py`, `hub/retrieval/lexical.py`

Filter policy integration:
- Lexical index build: excludes quarantined/rejected IDs via `excluded_ids` parameter (Story 3.5)
- Hard filter at build time: `enabled == 1` only
- Vector path: existing hard filter policy unchanged (`enabled`, `status`, quarantined)
- Both paths respect Sprint 1's filter precedence (hard > UI > inferred)
- Safety guarantee: quarantined articles never enter either the lexical index or vector corpus

---

### 4.5 — Add hybrid retrieval contribution logging
**Points:** 3
**Slice:** [[30-decisions/slice-4|Slice 4 — Deterministic Retrieval Core]]
**Goal:** goal/4, goal/10
**Labels:** `backend`, `logging`, `retrieval`, `observability`, `fusion`

**Acceptance snapshot:** Log lexical top-k, vector top-k, fusion strategy/params, fused top-k, tie-break decisions; cap stored top-k.

**Status:** 🔄 Active
**Depends on:** 6A.1 (target columns must exist)

Populates the `lexical_top_k_*`, `vector_top_k_*`, `fusion_*` columns added by 6A.1. Cap = top 5 per path per the [[20-sprints/sprint-3/decisions|3-D2]] decision on bounded logging.

---

### 4.6 — Create exact-term retrieval evaluation set
**Points:** 3
**Slice:** [[30-decisions/slice-4|Slice 4 — Deterministic Retrieval Core]]
**Goal:** goal/4, goal/9, goal/10
**Labels:** `backend`, `testing`, `evaluation`, `retrieval`

**Acceptance snapshot:** Create fixed queries with expected evidence IDs; compare vector-only vs hybrid; report accuracy/stability.

**Status:** ✅ Done
**Evidence:** Commit `deebebd` + `d37098b` (2026-05-15) — "slice 4 story 3 and slice 4 story 6"
**Files:** `hub/eval/exact_term_retrieval_eval.py`, `hub/eval/data/exact_term_retrieval_eval_v1.json`, `hub/tests/test_exact_term_retrieval_eval.py`

Evaluation framework:
- **12 test queries** covering exact-term cases: proper nouns (clinic names, building names), exact procedural terms, mixed queries
- Snapshot-based: KB articles + precomputed vector scores frozen in JSON for reproducibility
- In-memory SQLite DB seeded from snapshot (no live model drift)
- Measures top-3 and top-5 accuracy for vector-only vs hybrid
- CLI tool: `python -m hub.eval.exact_term_retrieval_eval [--json-out results.json]`
- Test coverage via `test_exact_term_retrieval_eval.py`

---

## Slice 6A — Observability & Trust (early start)

### 6A.1 — Complete structured query log schema
**Points:** 8
**Slice:** [[30-decisions/slice-6a|Slice 6A — Observability & Trust]]
**Goal:** goal/10
**Labels:** `backend`, `db`, `logging`, `observability`, `metrics`

**Acceptance snapshot:** Capture request ID, timestamp, KB version, normalized query, intent(s), clarification/rewrite/retrieval/filter/hybrid/multi-path metadata.

**Status:** ✅ Done
**Evidence:** Commit `d129eb6` (2026-05-11) — "slice 6a story 1 delivered, pre sprint 2 merge"
**Files:** `hub/db/schema.py`, `hub/db/migrate_schema.py`, `hub/api/routes_query.py`, `hub/tests/test_query_log_schema.py`

**Added 15 columns to `query_logs`** (originally planned 17, then deduplicated by 2 after Sprint 2 merge — see decision below):
- `intent_label`, `intent_confidence` (AC4)
- `lexical_top_k_ids`, `lexical_top_k_scores`, `lexical_top_k_ranks`, `lexical_latency_ms` (AC5 hybrid)
- `vector_top_k_ids`, `vector_top_k_scores`, `vector_top_k_ranks` (AC5 hybrid)
- `fusion_strategy`, `fusion_top_k_ids`, `fusion_top_k_scores`, `fusion_top_k_ranks` (AC5 hybrid)
- `fallback_reason`, `failed_stage` (AC5 outcome — populated by 6A.8)

All new columns are nullable TEXT (JSON arrays) or REAL. Top-K cap = 5.

**In-scope wiring shipped:** `intent_label` and `intent_confidence` are populated by both QueryLog write paths in `routes_query.py` (clarification pause + normal response). Retrieval columns are schema-only — interface contract for Person 3 (lexical), Person 4 (fusion), and Story 4.5.

**Tests:** 7 new tests in `test_query_log_schema.py` covering column presence, nullability, types, instantiation with new fields, backward-compatible legacy instantiation, and migration coverage. All 7 pass, 38 existing tests still pass.

> 🔍 Inferred: The deduplication after Sprint 2 merge removed `clarification_categories_offered` (superseded by Sprint 2's `clarification_options_shown` — richer `{id, label}` shape) and `clarification_node_id_selected` (superseded by existing `ui_selected_taxonomy_node_id` for pre-query, and `ClarificationResolution.selected_option_id` for resolution). Sprint 2's clarification logging is the canonical home for clarification fields.

---

### 6A.8 — Add failure and fallback outcome logging
**Points:** 3
**Slice:** [[30-decisions/slice-6a|Slice 6A — Observability & Trust]]
**Goal:** goal/10
**Labels:** `backend`, `logging`, `failure-handling`, `fallback`, `observability`

**Acceptance snapshot:** Log failures, reason codes, failed stage, partial logs, and session/query linkage.

**Status:** 🔄 Active

Populates `fallback_reason` and `failed_stage` columns (added by 6A.1) with stable reason codes: `no_results`, `low_confidence`, `validation_blocked`, `retrieval_error`, `rewrite_error`. Builds on the Sprint 1 fallback log lines (`fallback=...`) that already exist as text, promoting them to structured columns.
