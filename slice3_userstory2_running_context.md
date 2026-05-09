# Slice 3 — Story 2: Validation results and review decisions storage

## Story

As a maintainer, I want validation results and review decisions stored so that metadata quality can be audited by KB version.

## Acceptance Criteria

- Metadata items can be marked approved, quarantined, needs_review, or rejected.
- Validation results store rule IDs, severity, messages, and timestamps.
- Review decisions store reviewer identity, decision, reason code, and notes.
- Validation and review records are tied to a KB version or publish attempt.
- Existing KB content is not broken by the new validation storage.

---

## Status: DONE ✓

Pure storage layer. All ACs satisfied by new tables, ORM models, and migration. Zero changes to existing tables. No linter errors.

---

## Subtasks

- Subtask 1 — Add 4 new ORM classes to `schema.py`
- Subtask 2 — Add `CREATE TABLE IF NOT EXISTS` migration blocks
- Subtask 3 — Add Pydantic response/create models to `api_models.py`

---

## What was built

### Subtask 1 — ORM models
**File:** `hub/db/schema.py`

Four new SQLAlchemy classes appended after the existing taxonomy models:

| Class | Table | Purpose |
|---|---|---|
| `KBPublishAttempt` | `kb_publish_attempts` | Anchors a validation run to a KB version and timestamp |
| `KBItemValidationStatus` | `kb_item_validation_status` | Per-item status per attempt |
| `KBValidationResult` | `kb_validation_results` | One row per rule check |
| `KBReviewDecision` | `kb_review_decisions` | One row per human reviewer decision |

**Status values (`kb_item_validation_status.status`):** `approved` | `quarantined` | `needs_review` | `rejected`

**Severity values (`kb_validation_results.severity`):** `error` | `warning` | `info`

**Decision values (`kb_review_decisions.decision`):** `approved` | `rejected` | `override`

**Publish attempt status (`kb_publish_attempts.status`):** `pass` | `blocked` | `partial`

### Subtask 2 — Migration
**File:** `hub/db/migrate_schema.py`

Added `CREATE TABLE IF NOT EXISTS` blocks for all four tables (placed before the final `conn.commit()`). New tables use `CREATE TABLE IF NOT EXISTS` rather than `ALTER TABLE` — idempotent and safe on any existing DB.

Indexes added:
- `kb_item_validation_status(kb_item_id)`, `(publish_attempt_id)`
- `kb_validation_results(kb_item_id)`, `(publish_attempt_id)`
- `kb_review_decisions(kb_item_id)`

### Subtask 3 — Pydantic models
**File:** `hub/models/api_models.py`

Added five models:
- `KBPublishAttemptResponse` — read model for publish attempt records
- `KBItemValidationStatusResponse` — read model for per-item status
- `KBValidationResultResponse` — read model for individual rule results
- `KBReviewDecisionCreate` — write model for submitting a human decision (used by future review API)
- `KBReviewDecisionResponse` — read model for review decisions

---

## Key decisions

- **`publish_attempt_id` is the primary join key** for tying validation and review records to a specific publish event. `kb_version` is stored redundantly as a denormalized column so records are readable without a join to `kb_publish_attempts`.
- **No foreign key constraints in SQLite**: SQLite does not enforce FK constraints by default. Referential integrity is maintained by application logic. Columns are named with `_id` suffix to make intent clear.
- **`CREATE TABLE IF NOT EXISTS` for all four tables** (not `ALTER TABLE`): new tables that don't exist yet are safer to create this way; it's idempotent without needing `_get_existing_columns`.
- **`kb_item_validation_status.updated_at`**: SQLAlchemy `onupdate=datetime.utcnow` keeps the timestamp current when a status transitions (e.g., quarantined → approved after review).
- **`KBReviewDecisionCreate` is a separate model from `KBReviewDecisionResponse`**: the write model omits `reviewer_id` (set server-side from auth token) and `decided_at` (set server-side); the read model exposes all fields.

---

## AC trace

| AC | How it's met |
|---|---|
| Items marked approved/quarantined/needs_review/rejected | `kb_item_validation_status.status` |
| Validation results: rule IDs, severity, messages, timestamps | `kb_validation_results`: `rule_id`, `severity`, `message`, `checked_at` |
| Review decisions: reviewer, decision, reason code, notes | `kb_review_decisions`: `reviewer_id`, `decision`, `reason_code`, `notes` |
| Tied to KB version or publish attempt | All tables carry `kb_version` + `publish_attempt_id` |
| Existing KB content not broken | Zero changes to existing tables; all additive |

---

## Open / follow-on

- Validation logic (the rules themselves) is not implemented here — this story is storage only. Rule execution and the publish gate belong in a separate story.
- `kb_publish_attempts` is written by the publish endpoint; the route update is a follow-on story.
- `reason_code` on `KBReviewDecision` is a free string for now. A controlled vocabulary (e.g., `content_correct`, `rule_false_positive`, `safety_risk`) should be defined and enforced in the review API route or as an enum when the review endpoint is built.
- The `partial` publish attempt status (publish allowed with quarantined items excluded) requires retrieval to filter by `kb_item_validation_status.status != 'quarantined'` — that enforcement is in the retrieval layer, not yet wired.
