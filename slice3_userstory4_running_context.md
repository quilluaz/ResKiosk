# Slice 3 — Story 4: MVP metadata review workflow

## Story

As a shelter operator, I want to review quarantined metadata so that I can approve, reject, or override items before they affect retrieval.

## Acceptance Criteria

- Console or admin API can list quarantined/needs-review metadata items.
- Operator can approve an item.
- Operator can reject an item.
- Operator can override with a required reason code.
- Review decision updates validation status.
- Review decision is recorded in the audit trail.

---

## Status: DONE ✓

Admin API implemented. Requires authenticated console user (`Authorization: Bearer`).

---

## Subtasks

- Subtask 1 — Add `hub/validation/review.py` (queue builder, detail builder, apply review)
- Subtask 2 — Add Pydantic models for queue, detail, and apply response
- Subtask 3 — Register admin routes in `hub/api/routes_admin.py`
- Subtask 4 — Invalidate retrieval quarantine cache after a successful review commit

---

## What was built

### Subtask 1 — Validation review module (`hub/validation/review.py`)

**Purpose:** Centralize all review-queue logic so routes stay thin and the same rules as publish are reused without duplication.

**`get_system_kb_version(db)`**  
Reads `system_version.kb_version` so list/detail/apply responses are tied to the hub’s current KB version (Goal 8 / Goal 10: versioned audit context).

**`latest_validation_status_row(db, kb_item_id)`**  
Returns the most recent `kb_item_validation_status` row for an article (`ORDER BY id DESC`). Used to decide whether an item should still appear in the queue after an operator has already approved it (including override → approved).

**`build_review_queue(db)`**  
- Loads targets via `load_validation_targets`, taxonomy reference via `load_taxonomy_reference`, then runs `validate_metadata` (same pipeline as `/admin/publish` gate in `hub/validation/metadata.py`).  
- Keeps only items whose **live** derived status is `quarantined` or `needs_review`.  
- **Excludes** items whose latest persisted status is `approved` (so the queue reflects “still needs attention” from an operator perspective, not raw rule output alone).  
- Returns failed rules only (compact payload for the console) and sorts by `kb_item_id` for stable ordering.

**`build_article_validation_detail(db, kb_item_id)`**  
- 404 path is handled by the route when the article does not exist (`detail` dict empty).  
- Recomputes **live** status and full rule result list for that one article.  
- Appends **persisted** rows from `kb_validation_results` and **`kb_review_decisions`** (audit trail) ordered by primary key so the timeline is inspectable.

**`apply_metadata_review(...)`**  
- Validates `decision ∈ {approved, rejected, override}`; for **`override`**, requires non-empty `reason_code` (AC: override with required reason).  
- Ensures the KB article exists.  
- Maps decision → new `kb_item_validation_status.status`: **`approved`** for `approved` and `override` (override means “accept despite automated failures”), **`rejected`** for `reject`.  
- Inserts one **`KBItemValidationStatus`** row and one **`KBReviewDecision`** row with `reviewer_id` from the authenticated user (`username` or `user_id` string).  
- Returns `(validation_status_after, status_row, decision_row)` so the route can `flush()` and read `decision_row.id` for the response.

---

### Subtask 2 — Pydantic API contracts (`hub/models/api_models.py`)

**Purpose:** Typed request/response bodies for OpenAPI, console codegen, and consistent JSON shapes.

| Model | Role |
|--------|------|
| `MetadataRuleResultPublic` | Single rule outcome: `rule_id`, `severity`, `passed`, `message` (mirrors in-memory rule results from `metadata.py`). |
| `MetadataReviewQueueItem` | One queue row: `kb_item_id`, `live_status`, `kb_version`, optional `latest_db_status`, `failed_rules` (uses `Field(default_factory=list)` to avoid mutable default pitfalls). |
| `MetadataReviewQueueResponse` | `items` + top-level `kb_version` for the queue snapshot. |
| `MetadataArticleSnapshot` | Minimal article fields for the detail view (question, answer, category, tags string, authority, scope, enabled, status). |
| `MetadataValidationArticleDetail` | Bundles snapshot + `live_status` + `live_rule_results` + two JSON-friendly lists: persisted validation results and review decisions (dicts with ISO timestamps for DB datetimes). |
| `MetadataReviewApplyResponse` | Confirms apply: `status`, `kb_item_id`, `validation_status_after`, `review_decision_id`. |

**Note:** `KBReviewDecisionCreate` (Story 2) remains the POST body for `/admin/validation/review`; Story 4 did not introduce a second request DTO.

---

### Subtask 3 — Admin HTTP surface (`hub/api/routes_admin.py`)

**Purpose:** Expose the workflow over HTTPS for the React admin (or any authenticated client).

| Route | Handler behavior |
|--------|------------------|
| `GET /admin/validation/review-queue` | Calls `build_review_queue`, maps rows to `MetadataReviewQueueItem`, returns `MetadataReviewQueueResponse`. **`Depends(get_current_user)`** — unauthenticated calls get 401. |
| `GET /admin/validation/articles/{kb_item_id}` | Calls `build_article_validation_detail`; 404 if article missing; otherwise `MetadataValidationArticleDetail`. Same auth dependency. |
| `POST /admin/validation/review` | Body: `KBReviewDecisionCreate`. Calls `apply_metadata_review`, **`db.flush()`** to assign `decision_row.id`, maps `ValueError` → 400 (validation) or 404 (“not found”), other failures → 500 with rollback. **`db.commit()`** on success, then **`invalidate_validation_quarantine_cache()`** so retrieval’s bias/quarantine layer does not wait for TTL. |

**Imports:** `from hub.validation import review as metadata_review` and `invalidate_validation_quarantine_cache` merged into the existing `hub.retrieval.search` import list to avoid duplicate imports.

---

### Subtask 4 — Quarantine cache invalidation (`hub/retrieval/search.py`)

**Purpose:** Slice 4 Story 7 introduced a TTL-backed cache of quarantined/rejected article IDs for the **feedback bias** guard. When an operator **approves** or **overrides**, an article must leave that set immediately; otherwise the hub could keep treating it as blocked for up to `RLHF_BIAS_TTL_SECS`.

**`invalidate_validation_quarantine_cache()`**  
Clears the module-level `_quarantined_ids_cache` and resets `_quarantined_ids_loaded_at` so the next retrieval pass reloads from `kb_item_validation_status`.

**Call site:** Invoked only after a **successful** `commit` on `POST /admin/validation/review` (not on rollback paths).

---

## API (MVP)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/admin/validation/review-queue` | List items with live status `quarantined` or `needs_review`, excluding latest DB row `approved` |
| `GET` | `/admin/validation/articles/{kb_item_id}` | Article snapshot + live rules + persisted `kb_validation_results` + `kb_review_decisions` |
| `POST` | `/admin/validation/review` | Body: `KBReviewDecisionCreate` — applies decision, writes status + audit row |

**POST body** (`KBReviewDecisionCreate`): `kb_item_id`, `kb_version`, `decision` (`approved` \| `rejected` \| `override`), optional `publish_attempt_id`, optional `reason_code` / `notes`. **`reason_code` required when `decision` is `override`.**

**Validation status after apply:** `approved` for `approved` and `override`; `rejected` for `reject`.

---

## Key decisions

- **Queue is driven by live `validate_metadata()`** so operators always see the same semantic state as the publish gate, even if a publish run has not yet written rows to `kb_validation_results` / `kb_item_validation_status`.
- **Queue suppression uses latest persisted `approved`** so human decisions take precedence over still-failing automated checks until metadata is fixed and re-validated (optional follow-up: re-queue if rules pass then regress).
- **Append-only style for status:** each review inserts a **new** `kb_item_validation_status` row rather than updating a single row in place — simpler audit and aligns with “publish attempt” granularity later.
- **Auth on all three endpoints** matches other sensitive admin operations; no anonymous review.
- **Override → `approved` validation status** matches Goal 8 language: override is an explicit human bypass with mandatory reason, not a fourth long-lived status in the DB.

---

## AC trace

| AC | How it's met |
|----|----------------|
| List quarantined / needs-review | `GET .../review-queue` — live statuses `quarantined` \| `needs_review`, minus latest DB `approved` |
| Operator can approve | `POST` with `decision=approved` → new status `approved` + `kb_review_decisions` row |
| Operator can reject | `POST` with `decision=rejected` → status `rejected` + audit row |
| Override requires reason code | `apply_metadata_review` raises if `override` and empty `reason_code` → HTTP 400 |
| Review updates validation status | New `KBItemValidationStatus` row per apply |
| Audit trail | New `KBReviewDecision` row per apply; detail GET lists full history |

---

## Open / follow-on

- **Console UI** is not in this story; wire the React admin to these endpoints when ready.
- **Publish path persistence** of `kb_publish_attempts` / `kb_validation_results` / initial `kb_item_validation_status` remains optional; the detail endpoint already merges live + persisted data when rows exist.
- **Reason code vocabulary** for override is not yet a closed enum (only non-empty string).
- **Optional:** persist validation runs on publish so `publish_attempt_id` is consistently populated end-to-end for joins and reporting.
