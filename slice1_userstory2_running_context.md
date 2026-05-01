# Slice 1 — User Story 2 Running Context (Person 4: Taxonomy & Metadata Schema Owner)

This file is the **single running context** for Sprint 1 **Story 2** (“Add metadata fields for retrieval filtering”) and related Goal 7 alignment.

**Rule (per Keith):** Before making any important decision, consult this file first. After every action/decision, update this file with the relevant context.

---

## Source-of-truth docs (read)

- `docs/goal_outlines/goal_7.md`
- `docs/goal_outlines/controlled_taxonomy_outline.md`
- (code reality checks) `hub/db/schema.py`, `hub/db/migrate_schema.py`, `hub/db/seed.py`, `hub/retrieval/search.py`, `hub/models/api_models.py`

---

## Story 2 (Sprint 1) — Add metadata fields for retrieval filtering

### User story (paraphrase)

As the retrieval system, we want KB items to expose **filterable metadata** so resident-facing answers can be scoped safely and predictably.

### Acceptance criteria (from ticket screenshot + Goal 7)

- KB items can represent **taxonomy assignment**.
- KB items can represent **authority/source classification**.
- KB items can represent **scope/context**.
- Existing KB articles are safely **backfilled with default metadata**.
- Migration does **not break** existing text-only retrieval.
- Metadata fields are compatible with **future validation** and **multimodal** work.

---

## Subtasks (one sentence each)

- Add authority/source metadata fields to KB items using a small, controlled enum (`official|shelter_staff|volunteer|unknown`) with safe defaults.
- Add scope/context metadata fields to KB items (`shelter_local|general`) with safe defaults and future-friendly hooks for `center_id`/`hub_id`.
- Ensure metadata is represented in DB schema with additive, idempotent migrations and does not break existing retrieval.
- Backfill existing KB articles deterministically with default authority/scope values.
- Surface metadata in the hub API models for KB read/write (so console can edit later) without breaking existing clients.
- Add minimal logging hooks (if needed) so future filtering decisions can be audited (Goal 7 alignment).
- Smoke test: init/migrate idempotency + retrieval unaffected on existing KB.

---

## Decisions log

### D1 — Storage strategy for authority/scope metadata

- **Decision**: Store Story 2 metadata as **queryable columns on `kb_articles`** (not a JSON blob and not a separate metadata table in v1).
- **Fields (minimum viable)**:
  - `authority` enum string: `official|shelter_staff|volunteer|unknown`
  - `scope` enum string: `shelter_local|general`
  - optional future hooks: `center_id`, `hub_id` (nullable TEXT)
- **Why**:
  - easiest to migrate safely (additive columns)
  - simple to query/filter later for retrieval and console filtering
  - forward-compatible with validation (Goal 8) and multimodal schema work (Goal 3)

---

## Implementation status

- [x] DB schema for authority/scope added (`kb_articles.authority`, `kb_articles.scope`, optional `center_id`, `hub_id`)
- [x] Idempotent migrations added (`hub/db/migrate_schema.py` and `hub/db/init_db.py`)
- [x] Seed/backfill defaults added (`hub/db/seed.py` `_backfill_kb_metadata_defaults`)
- [x] API models updated to include metadata (`hub/models/api_models.py`)
- [x] Admin create/update endpoints accept metadata (`hub/api/routes_admin.py`)
- [x] Smoke tests pass and retrieval behavior unchanged (DB init/migrate, backfill, admin create/update)

---

## Story 2 completion status

**Status: DONE (delivered).**

Acceptance criteria coverage:

- **Taxonomy assignment representable**: already supported from Story 1 via `kb_item_taxonomy` and taxonomy seeds.
- **Authority/source classification**: implemented on `kb_articles.authority` with safe defaults and admin API support.
- **Scope/context**: implemented on `kb_articles.scope` with safe defaults and future-friendly hooks (`center_id`, `hub_id`).
- **Safe backfill for existing KB**: `_backfill_kb_metadata_defaults` runs idempotently during `init_db()` seeding.
- **No retrieval regression**: changes are additive columns + backfill; existing retrieval paths continue to function.
- **Future compatibility**: columns are queryable and align with Goal 7/Goal 8 validation and Goal 3 multimodal forward-compat needs.

---

## Jira-ready summary paragraph (Story 2)

Delivered Story 2 (“Add metadata fields for retrieval filtering”) by adding first-class, filterable KB metadata for Goal 7 without breaking existing retrieval. Implemented authority/source classification and scope/context as additive, queryable columns on `kb_articles` (`authority` with controlled values `official|shelter_staff|volunteer|unknown`, `scope` with `shelter_local|general`, plus nullable `center_id`/`hub_id` hooks for future scoping). Added idempotent migrations for existing deployments and an idempotent backfill step that safely defaults existing KB rows (e.g., `evac_sync` content defaults to `authority=shelter_staff` and `scope=shelter_local`, otherwise `authority=unknown` and `scope=general`). Updated hub API models and admin create/update endpoints to accept and return these fields so the console can manage them, and validated via DB init/migration + backfill and admin create/update smoke tests that existing text-only retrieval remains unaffected while the metadata is now available for upcoming filtering enforcement and validation work.
