# Goal 3 — KB schema rework for multimodal retrieval (schema-only; forward-compatible)

### 1) Outcome

Deliver a **versioned KB schema** that can represent **text and image KB evidence** (and future modalities) in a way that is **safe to migrate**, **backward-compatible where required**, and **auditable** via stable evidence identifiers tied to `kb_meta.kb_version`.

- **What changes**: the KB data model becomes **modality-aware** (text vs image), can reference **image assets**, and can store **filtering metadata** needed by later goals—without enabling semantic chunking this increment.
- **Who benefits**: residents (visual evidence can be used safely later), admins (KB can include images as managed items), maintainers (retrieval/logging can evolve without breaking releases).
- **What success looks like**:
  - schema migrations apply cleanly on existing deployments
  - publish increments `kb_meta.kb_version` deterministically
  - retrieval + logs can reference **stable evidence IDs** and **modality** for both text and image KB items

---

### 2) Why this matters

- **Current limitation**: `kb_articles` stores a single `embedding` BLOB and Q/A fields; the schema does not explicitly represent **modality**, **image assets**, or **policy-relevant metadata** required by multimodal + hybrid retrieval.
- **Risk addressed**: bolting multimodal onto an underspecified schema forces ad-hoc fields, makes migrations risky, and prevents deterministic cache invalidation/observability by `kb_version`.
- **Value**: a forward-compatible schema is the foundation for:
  - Goal 1 (semantic image search)
  - Goal 2 (image storage as first-class KB assets)
  - Goal 4+ (hybrid retrieval and consistent filtering/logging)

---

### 3) Scope

- Define a **schema vNext** that supports:
  - **modality**: minimum viable `text | image` (extensible)
  - **image asset references** (original + thumbnail handled by Goal 2; schema must support linking)
  - **metadata fields required for filtering/rules** (Goal 7 consumes these; Goal 3 makes them representable)
  - **forward-compatible segmentation fields** (e.g., parent/segment identifiers) **without enabling chunking** this increment
- Update ingest/publish flows (as needed) so:
  - items are written consistently to the new schema
  - publishing increments `kb_meta.kb_version`
- Update retrieval/logging contracts so evidence references become **modality-aware** and stable.

---

### 4) Non-goals

- Implementing CLIP/SigLIP image embedding (Goal 1)
- Implementing image asset storage/thumbnail generation and invalidation lifecycle (Goal 2)
- Enabling semantic chunking / automatic splitting (explicitly deferred this increment)
- Full filtering policy and taxonomy (Goal 7)
- Any online/offline reranking system beyond existing retrieval (out of scope here)

---

### 5) System Impact

#### a. Data / Schema

**Existing tables (current)**

- `kb_articles` (contains `question`, `answer`, `category`, `tags`, `enabled`, `status`, `source`, `embedding`, timestamps)
- `system_version` (`kb_version`, `last_published`) — **this is what `/admin/publish` currently bumps**
- `kb_meta` (`kb_version`, `updated_at`) — exists in the DB/ORM, but is **not currently bumped** by `/admin/publish`
- `query_logs` (already stores `kb_version` and `source_id` for the top result; note: today `kb_version` is provided by the kiosk request payload)

**Schema vNext (Goal 3 introduces / refactors)**

Goal 3 is authoritative on **what must be representable**, but leaves the exact table strategy as an explicit decision (see Open Decisions).

Minimum representational requirements:

- **Modality**:
  - a field to distinguish `text` vs `image` per KB item
- **Stable evidence identity**:
  - continue to support stable integer IDs (current `kb_articles.id`) as evidence references
  - ensure evidence references can be tied to `kb_meta.kb_version` for auditability/invalidation
- **Asset linkage for images**:
  - fields (or linked table) to reference image original + thumbnail assets created in Goal 2
  - content hash / version linkage must be representable (Goal 2 enforces lifecycle)
- **Forward-compatible segmentation hooks (not active)**:
  - fields to support a future “multi-article from one source” structure (parent + segment index)
  - explicitly **not used for retrieval unit changes** in this increment (retrieval unit remains a KB row)
- **Filterable metadata surface (schema only)**:
  - represent fields that Goal 7 will later enforce (do not implement policy here)

#### b. API / Interfaces

- **Hub retrieval response** must be able to return evidence with:
  - stable evidence ID
  - modality (`text` vs `image`)
  - modality-specific references (e.g., text fields vs image asset refs)
- **Admin/console** must be able to manage KB items that are either:
  - text articles, or
  - image items (asset-backed)

#### c. UX / Behavior

- **Resident (kiosk)**: no new UI required from Goal 3 alone; however, future image evidence display depends on having stable references and modality-aware payloads.
- **Admin (console)**: schema enables future UI updates to manage image KB items; Goal 3 does not require a full editor redesign.

---

### 6) Integration Points

- **Depends on**:
  - existing KB versioning (`kb_meta.kb_version`) and publish behavior
- **Unblocks / supports**:
  - Goal 1 (image ↔ text semantic search): needs modality + image evidence representation
  - Goal 2 (image assets): needs a place to attach assets + hashes + version linkage
  - Goal 7 (filtering): needs metadata fields to exist in a queryable form
  - Goal 10 (metrics/logging): needs modality-aware evidence logging fields
- **Touches**:
  - retrieval layer (evidence representation and selection)
  - logging layer (`query_logs` evidence fields may need extension beyond `source_id`)

---

### 7) Edge Cases / Failure Modes

- **Mixed-version deployments**:
  - hub/kiosk/console must not crash if a DB has been migrated but a client is older (contract versioning required; see Contract / Payload Shape)
- **Missing assets for image KB items**:
  - retrieval must not return broken asset references; should fail closed (exclude item or return safe fallback) and log the reason
- **Partial migrations / rollback**:
  - migrations must be reversible or support a safe rollback strategy (see Migration / Rollout Plan)
- **Legacy rows without new fields populated**:
  - default values + backfill strategy must preserve behavior for text-only retrieval

---

### 8) Logging & Metrics

Minimum logging changes required so later goals can measure multimodal behavior safely:

- log **evidence modality** alongside evidence IDs
- log **KB version** consistently (already present in `query_logs.kb_version`)
- log enough to trace asset references for image evidence (IDs/refs, not raw binaries)

---

### 9) Determinism / Constraints

- **Version determinism**: publish must increment the authoritative KB version in a single place and the hub must attach that version to logs.
- **Stable evidence identity**: evidence references used by retrieval/logging must remain stable across requests within a fixed `kb_version`.
- **Schema-only constraint**: do not introduce chunking/segmentation behaviors into the retrieval unit this increment.

---

### 10) Definition of Done (DoD)

- Schema migrations land that can represent:
  - modality (`text | image`)
  - image asset references (sufficient for Goal 2 to populate)
  - forward-compatible segmentation hooks (unused by retrieval this increment)
  - metadata surface needed for later filtering enforcement
- Existing text-only KB content remains retrievable (no regression in basic retrieval behavior).
- Publish increments the authoritative KB version deterministically (current code uses `system_version.kb_version`; this goal may move authority to `kb_meta.kb_version` if desired) and retrieval/logging can reference stable evidence IDs plus modality.
- Retrieval response payloads can return modality-aware evidence references without breaking existing consumers (via compatibility strategy).

---

### 11) Open Decisions

- **Table strategy**:
  - extend `kb_articles` in place vs introduce a new generalized KB item table and keep `kb_articles` as a compatibility view/alias
- **Evidence logging shape**:
  - keep `query_logs.source_id` as “top evidence” while adding additional fields for multimodal/top-k evidence vs introduce a separate evidence log table
- **Metadata storage**:
  - dedicated columns for filterable fields vs a JSON metadata blob (trade-off: queryability and determinism vs flexibility)
- **Asset reference type**:
  - file path vs content-addressed ID vs DB row reference (must align with Goal 2’s storage approach)

---

## Contract / Payload Shape

### Evidence object (hub → kiosk/console)

Goal 3 requires the hub to be able to represent evidence as a **modality-aware** object.

Minimum required fields:

- `evidence_id` (stable)
- `modality` (`text` or `image`)
- `score` (retrieval score)

Modality-specific fields:

- For `text`: fields sufficient to render citations/snippets safely (exact selection deferred; must not leak private/admin-only fields)
- For `image`: references to original + thumbnail assets (shape aligned with Goal 2)

### Backward compatibility

- Provide a compatibility mapping so existing clients that only understand a single `source_id` can still function during rollout (exact approach decided during implementation).

---

## Migration / Rollout Plan

### Migration phases (recommended)

- **Phase 0 — Additive schema**:
  - add new fields/tables in a way that does not break current reads/writes
  - backfill modality defaults for existing text rows
- **Phase 1 — Dual-write (if needed)**:
  - write both legacy-compatible fields and new schema fields during ingest/publish
- **Phase 2 — Switch reads**:
  - update hub retrieval + logging to use modality-aware evidence references
- **Phase 3 — Cleanup (optional, later)**:
  - remove dead fields only once all clients are migrated (not required for Goal 3 completion)

### Rollback strategy

- Ensure a rollback does not corrupt existing KB content:
  - schema changes should be reversible or safely ignorable by older code
  - publish/version increments remain consistent

