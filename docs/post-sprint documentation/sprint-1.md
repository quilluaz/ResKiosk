# Sprint 1 Post-Sprint Summary
**Sprint Goal**: Build the deterministic hub pipeline foundation and establish the core metadata structure required for controlled query processing and KB integrity.

---

## What ResKiosk Could Do Before Sprint 1

- Resident queries were processed ad hoc — no enforced stage order between normalize, intent, rewrite, and retrieval.
- Rewrite and retrieval could run even when clarification was needed, producing premature answers for ambiguous queries.
- KB articles had no taxonomy assignments, no authority/scope metadata, and no filtering rules.
- Retrieval returned results from disabled or unpublished articles alongside valid content.
- No structured logging captured what happened at each pipeline stage, making debugging and reproduction nearly impossible.
- Filter decisions were implicit and untraceable — there was no way to explain why a result was included or excluded.

---

## What Changed in Sprint 1

Sprint 1 covered two implementation slices in full: **Slice 0 (Backbone Contract)** and **Slice 1 (Controlled Scope Foundation)**. Together they replaced the informal query path with a structured, observable, metadata-aware pipeline.

---

### Slice 0 — Backbone Contract
*Goal: One canonical pipeline path that all queries pass through, with logging at every stage.*

#### Story 1 — Create Canonical Pipeline Orchestrator
**What it does**: All hub query handling now passes through a single `QueryPipeline` class in `hub/retrieval/pipeline.py`. The pipeline enforces a strict stage order: `normalize → intent → retrieve → clarification_gate → [rewrite → retrieve_retry]`.

**Key changes**:
- `hub/retrieval/pipeline.py` created with `QueryPipeline` class representing the canonical stage sequence.
- `hub/api/routes_query.py` refactored to call `pipeline.run()` instead of calling normalize/search/rewrite inline.
- Intent classification extracted from `search.py::retrieve()` into the pipeline itself so the stage is explicit and guarded.
- Clarification decision moved to occur **before** rewrite — rewrite cannot run until clarification is resolved.
- Guards added: retrieval does not run a second pass when clarification is required.
- `hub/tests/test_pipeline_order.py` added to confirm stage ordering is enforced.

**Before → After**: Queries took an implicit path through scattered function calls. Now every query takes one traceable path through named, ordered stages.

---

#### Story 2 — Add Pipeline Stage Logging Skeleton
**What it does**: Each pipeline stage now emits an `INFO`-level log line with a structured, bounded payload so query execution can be reproduced and debugged from logs alone.

**Key changes**:
- Stage 1 (normalize): logs `normalized=<text>`
- Stage 2 (intent): logs `intent=<label> confidence=<score>`
- Stage 3 (retrieve): logs `source_id=<id>` field added to output
- Stage 4 (clarification_gate): logs `clarification_triggered=True/False`
- Stage 5 (rewrite): logs `rewrite_applied=True/False`
- Stage 6 (retrieve_retry): logs `source_id` and `confidence` fields
- All text fields capped at 120 characters — raw article body and answer text are never logged.
- All 7 existing `test_pipeline_order.py` tests verified to still pass after promotion.

**Before → After**: Pipeline stages emitted DEBUG-level noise with no consistent shape. Now every stage emits a single INFO line with enough detail to reconstruct what happened for any given query.

---

#### Story 3 — Add Clarification Pause State to Query Flow
**What it does**: When a query is ambiguous, the hub now returns a structured `NEEDS_CLARIFICATION` response instead of attempting a rewrite and potentially returning a wrong answer. The response carries enough context to resume the request after the resident clarifies.

**Key changes**:
- `ClarificationContext` response model added to `hub/models/api_models.py` — holds intent, categories, and a follow-up token.
- `QueryResponse` extended with `clarification_context` field (populated only when `answer_type == NEEDS_CLARIFICATION`).
- `pipeline_status` field added to `PipelineResult` so the route handler knows whether to early-return or continue.
- Route handler in `routes_query.py` detects clarification pause via `pipeline_status` and early-returns without running rewrite or retrieval.
- Logging hook prepared in pipeline for Person 2 to attach clarification resolution logging in Sprint 2.
- Tests added for `pipeline_status` values and the clarification response contract.
- All existing non-clarification query paths verified unaffected.

**Before → After**: Ambiguous queries fell through to rewrite/retrieval and produced low-confidence or wrong answers. Now they pause cleanly at the clarification gate with a resumable response.

---

### Slice 1 — Controlled Scope Foundation
*Goal: Give KB articles stable taxonomy, filterable metadata, and enforced retrieval rules so that scope is controlled before accuracy work begins.*

#### Story 1 — Define Taxonomy v1 Data Model
**What it does**: Established a controlled vocabulary of shelter topics with stable, namespaced IDs that filtering, clarification chips, validation, and retrieval can all share.

**Key changes**:
- `hub/taxonomy/taxonomy_v1.json` added — main categories and subcategories with stable IDs in the format `rk.tax.<category>.<subcategory>`.
- `hub/taxonomy/legacy_category_map_v1.json` added — deterministic mapping from existing `kb_articles.category` strings to taxonomy IDs for safe backfill.
- DB schema extended with `taxonomy_nodes`, `taxonomy_edges` (DAG), `kb_item_taxonomy` (article assignments), and `intent_taxonomy_map` tables — all using TEXT IDs, not integers.
- `init_db()` updated with idempotent seeding so deployments load taxonomy deterministically.
- Existing KB rows backfilled with taxonomy assignments where `category` string maps to a known node; rows without a match are left unassigned (not silently broken).
- `/query` response extended with `selected_taxonomy_node_id` and `clarification_options: [{id, label}]` fields added additively — legacy `selected_category` and `clarification_categories` fields preserved for backward compatibility with older kiosks.
- Clarification chip selection made deterministic via Goal 7 chip policy: default 3 chips, at most one conditional replacement when strongly indicated.
- `query_logs` schema extended with `ui_selection_source` (taxonomy vs legacy), `selected_taxonomy_node_id`, `inferred_taxonomy_node_ids` placeholders for observability.

**Before → After**: Categories were free-text strings with no stable IDs. Filtering, clarification, and retrieval used different representations of the same concepts. Now all subsystems share one controlled vocabulary with stable IDs.

---

#### Story 2 — Add Metadata Fields for Retrieval Filtering
**What it does**: KB articles now carry first-class filterable metadata fields (`authority`, `scope`, `center_id`, `hub_id`) that future filtering enforcement and validation can rely on.

**Key changes**:
- `kb_articles` schema extended with four new nullable columns:
  - `authority`: `official | shelter_staff | volunteer | unknown`
  - `scope`: `shelter_local | general`
  - `center_id`, `hub_id`: nullable string hooks for future multi-center scoping
- Idempotent migration added so existing deployments gain these columns safely.
- Backfill defaults applied: `evac_sync`-sourced articles default to `authority=shelter_staff, scope=shelter_local`; all other existing articles default to `authority=unknown, scope=general`.
- Admin create/update API endpoints updated to accept and return these fields.
- Console admin UI updated to surface the new fields.
- Existing text-only retrieval verified unaffected — new columns are nullable and not used in retrieval scoring yet.

**Before → After**: KB articles had no structured source or scope metadata. Articles from different authorities were indistinguishable at retrieval time. Now each article carries explicit authority and scope that filtering and validation can act on.

---

#### Story 3 — Enforce Hard Retrieval Rules
**What it does**: Retrieval now enforces non-negotiable exclusion rules before any other filtering — disabled and unpublished articles can never reach a resident.

**Key changes**:
- Hard rule 1: Articles with `enabled = false` are excluded from retrieval candidate set.
- Hard rule 2: Articles with `status` other than `published` are excluded from retrieval candidate set.
- Hard rules run first, before UI filters and inferred intent filters, establishing the correct precedence.
- Each excluded article is logged with a reason code (`hard_rule:disabled` or `hard_rule:unpublished`) so exclusions are explainable.
- Vector retrieval scoring only runs against articles that have passed hard rules.
- Existing published, enabled articles verified retrievable with no regression.

**Before → After**: Disabled and draft articles could appear in retrieval results if their embedding matched the query. Now they are unconditionally excluded before any scoring occurs.

---

#### Story 4 — Apply UI and Inferred Intent Filters with Precedence
**What it does**: When a resident or operator selects a taxonomy filter (via UI chip), or when the pipeline infers an intent, those filters are applied in a defined, deterministic precedence order.

**Key changes**:
- Filter precedence explicitly enforced: **hard system rules > user UI filters > inferred intent**.
- UI-selected taxonomy node (from `selected_taxonomy_node_id` in the query request) overrides inferred intent filters — the resident's explicit scope choice is authoritative.
- Inferred intent fills in taxonomy constraints only when no UI filter is present — it never overrides an explicit selection.
- Filter decisions are deterministic for the same query, KB version, and config — same inputs always produce the same filtered candidate set.
- Applied filters logged with their source (`hard`, `UI`, or `inferred`) so every scoping decision is traceable.

**Before → After**: UI filter selections and inferred intent were applied inconsistently with no defined winner when they conflicted. Now the precedence is explicit and logged, making every retrieval scope decision reproducible.

---

#### Story 5 — Log Filter Decisions and Candidate Counts
**What it does**: The retrieval layer now emits structured `[Filter]`-tagged log lines at every decision point, including candidate counts and fallback events, so any retrieval outcome can be explained from the logs.

**Key changes**:
- `[Filter] ui_category='<value>'` logged when a UI-selected taxonomy node is present.
- `[Filter] inferred_taxonomy='<intent>' confidence=<score>` logged when intent inference fills the filter.
- `[Filter] candidates_total=N top_k_scored=K` logged after scoring so narrowing is visible.
- Exclude block refactored into a named hard rule emitting `[Filter] rule=exclude_ids before=N after=M removed=K`.
- Fallback events logged with specific tags:
  - `fallback=all_candidates_excluded` when hard rules remove everything
  - `fallback=clarification_gate best_score=X` when score falls below clarification threshold
  - `fallback=sub_threshold_direct_match best_score=X threshold=Y` for below-threshold direct matches
  - `fallback=no_match best_score=X threshold=Y` for true no-match cases
- All `[Filter]` log lines use the query's implicit `session_id`/request context so they can be joined to the `query_logs` table record without a schema change.
- All 7 existing `test_pipeline_order.py` tests verified passing after refactor.

**Before → After**: Filter behavior was a black box. There was no way to tell from logs whether a result was excluded by a hard rule, a UI filter, or a fallback condition. Now every exclusion and fallback has a named, logged reason.

---

## Sprint 1 at a Glance

| Slice | Story | Delivered |
|---|---|---|
| Slice 0 | Create canonical pipeline orchestrator | ✅ |
| Slice 0 | Add pipeline stage logging skeleton | ✅ |
| Slice 0 | Add clarification pause state to query flow | ✅ |
| Slice 1 | Define taxonomy v1 data model | ✅ |
| Slice 1 | Add metadata fields for retrieval filtering | ✅ |
| Slice 1 | Enforce hard retrieval rules | ✅ |
| Slice 1 | Apply UI and inferred intent filters with precedence | ✅ |
| Slice 1 | Log filter decisions and candidate counts | ✅ |

**8 stories delivered. All subtasks marked DONE.**

---

## What ResKiosk Can Do After Sprint 1

- Every resident query flows through one canonical, ordered pipeline — no stage can run out of sequence.
- Ambiguous queries pause at a clarification gate and return a resumable structured response instead of guessing.
- Every pipeline stage emits a bounded, structured log line — any query execution can be reproduced from logs.
- KB articles carry stable taxonomy assignments, authority/scope metadata, and explicit enabled/published status.
- Retrieval unconditionally excludes disabled and unpublished articles before scoring.
- UI-selected and inferred intent filters are applied in defined precedence order with logged decisions.
- Every retrieval exclusion and fallback event has a named reason code in the logs.

---

## Deferred to Future Sprints

- **Clarification retry contract**: The clarification pause state was added but the kiosk → hub retry flow carrying a chip selection was deferred to Sprint 2 (Slice 2).
- **Filtering enforcement for authority/scope**: Metadata fields were added and backfilled but are not yet applied as active retrieval filters — enforcement is a Sprint 2 goal.
- **Validation gate**: Metadata exists but is not validated before publish — that is Slice 3 (Sprint 2).
- **Hybrid retrieval (BM25)**: Retrieval is still vector-only. Lexical retrieval is a Slice 4 goal.
- **Multi-path retrieval**: Compound query handling still runs a single retrieval pass. Slice 5 work.
