# Goal 2 — Image storage as first-class KB assets (original + thumbnail + versioned invalidation)

### 1) Outcome

Store KB images as **first-class assets** with an **original + thumbnail**, a **content hash**, and **`kb_version` linkage** so image display is fast and publishing new KB versions invalidates/refreshes derived artifacts **deterministically**.

- **What changes**: images stop being “incidental” content and become durable KB evidence with IDs, metadata, and lifecycle rules.
- **Who benefits**: residents (fast, reliable visual guidance), admins (predictable publishing), maintainers (auditable, debuggable assets).
- **What success looks like**:
  - the kiosk consistently loads thumbnails quickly for returned image evidence
  - publishing a new KB version invalidates and refreshes image-derived caches predictably
  - answers/logs reference stable image evidence IDs/refs and scores

---

### 2) Why this matters

- **Current limitation**: KB is centered on `kb_articles`; images are not modeled as first-class assets with lifecycle/invalidation.
- **Risk addressed**: stale or mismatched images after KB changes, slow kiosk image load times, and missing auditability for what image evidence was shown.
- **Value**: reliable visual guidance requires strong asset identity, deterministic refresh rules, and stable references for logging/metrics.

---

### 3) Scope

- Define the **minimum viable data model** for KB image assets:
  - original reference
  - thumbnail reference
  - content hash (for dedupe + integrity)
  - linkage to `kb_version` (for publish-time invalidation)
  - minimal metadata required for audit/debug (e.g., mime type, size, created_at)
- Define **thumbnail generation** requirements:
  - standard sizes for kiosk UI
  - deterministic generation parameters (so same input → same output)
- Define **publish-time invalidation** semantics:
  - what gets invalidated on KB publish
  - what must be recomputed vs what can be reused
- Ensure **logging can reference image evidence IDs** used in answers.

---

### 4) Non-goals

- Full DAM (digital asset management) system (tags, search, albums, permissions)
- Multi-tenant storage separation beyond current deployment assumptions
- Advanced image transforms (multiple renditions, adaptive art direction)
- OCR/caption extraction pipelines (belongs to Goal 1/3+ depending on approach)
- CDN edge optimization work (can be future perf goal after correctness)

---

### 5) System Impact

#### a. Data / Schema

This goal requires a durable representation of image assets with:

- **Stable asset IDs** for logging and evidence refs
- **Asset refs** for original + thumbnail
- **`kb_version` linkage** for deterministic invalidation
- **Content hash** for integrity/dedupe and debugging

Notes / constraints from the increment:

- Retrieval boundary remains English (translation upstream).
- KB scale is ~1k–5k articles; images should remain operational at this scale.

#### b. API / Interfaces

The hub must be able to:

- accept image assets at ingest/publish time (admin path)
- return image evidence results with:
  - a stable image evidence identifier/reference
  - scores (for retrieval explainability)
  - URLs/refs for thumbnail and (optionally) original where permitted

#### c. UX / Behavior

- **Kiosk**:
  - prefers thumbnails for initial display to minimize latency
  - can request original on-demand (if needed for zoom/detail)
- **Admin/console**:
  - can upload images and see confirmation of stored original + generated thumbnail(s)
  - publishing a new KB version provides predictable “what changed” behavior for assets

---

### 6) Integration Points

- **Depends on**:
  - Goal 3 (multimodal schema rework) if the schema is implemented as a unified KB-item model
  - Goal 10 (metrics/logging) to ensure image evidence is captured consistently in query logs
  - Existing KB versioning (`kb_meta.kb_version`, `query_logs.kb_version`, `system_version.kb_version`) for invalidation keys
- **Affects**:
  - Goal 1 (image semantic retrieval): storage + thumbnailing are prerequisites for returning image evidence reliably
  - Goal 11 (safer caching patterns): image caching must incorporate KB versioning and invalidation hooks

---

### 7) Edge Cases / Failure Modes

- **Thumbnail generation fails**:
  - asset should still be stored; kiosk falls back to original (if allowed) or hides the image with a clear placeholder
  - failure must be logged with asset ID and reason
- **Duplicate uploads** (same content hash):
  - either reuse the existing asset or store as a new revision; behavior must be deterministic and logged
- **KB publish during upload**:
  - publish should not reference partially-processed assets; only assets in a “ready” state become eligible evidence
- **Missing files** (db row exists but blob missing):
  - treat as invalid evidence; exclude from retrieval; log anomaly for repair
- **Large images**:
  - enforce size limits and safe downscaling; refuse unsafe formats if needed

---

### 8) Logging & Metrics

Minimum required observability:

- **Asset events**:
  - image uploaded: asset ID, content hash, byte size, mime type, kb_version target
  - thumbnail generated: asset ID, thumb params, output hash/size
  - publish invalidation: old kb_version → new kb_version, counts invalidated/refreshed
- **Query/answer logs**:
  - image evidence IDs returned
  - thumbnail ref used vs original ref used (if applicable)
  - evidence scores and ranking position (for debugging)

---

### 9) Determinism / Constraints

- **Version determinism**: the same `kb_version` + same asset inputs must yield identical thumbnail outputs (given fixed generator settings).
- **Invalidation keying**: caches and derived artifacts must be keyed by `kb_version` (and any relevant generator/config versions).
- **Tie-break / identity**: evidence references must remain stable and reproducible across runs for a fixed KB version.

---

### 10) Definition of Done (DoD)

- Image assets are stored as first-class KB entities with:
  - original + thumbnail refs
  - content hash
  - `kb_version` linkage
- Thumbnail generation is implemented with deterministic parameters and validated on a small test set.
- Publishing a new KB version triggers deterministic invalidation/refresh hooks for image-derived artifacts.
- Hub responses can include stable image evidence references usable by the kiosk.
- Logging captures asset lifecycle events and which image evidence was returned to residents.

---

### 11) Open Decisions

- Where image binaries live (filesystem vs object storage) and how refs are represented in the hub/kiosk contract.
- Exact thumbnail sizes/variants required by kiosk UI (minimum set to ship).
- Whether content-hash duplicates should be de-duped globally or per KB version.
- Whether “ready vs pending” asset state is required for safe publish concurrency (recommended if publish can overlap ingest).

---

## Contract / Payload Shape

### Image evidence (hub → kiosk)

Minimum fields the kiosk needs to render images reliably:

- `evidence_id` (stable)
- `modality = "image"`
- `score`
- `thumbnail_ref` (preferred)
- `original_ref` (optional / gated)
- `kb_version`

Notes:

- Refs may be URLs or internal IDs; the key requirement is stable resolution and loggable identity.

---

## Caching / Invalidation

### Cache keys (minimum viable)

- Derived artifacts (thumbnails) and any image-response caches must include:
  - `kb_version`
  - generator/config version (if thumbnail params can change)
  - asset content hash or asset ID

### Invalidation triggers

- **KB publish** (kb_version increments): invalidate image-derived caches tied to prior versions and refresh deterministically for the newly published version.

---

## Migration / Rollout Plan

- **Phase 0 (prep)**: define schema and refs without changing kiosk behavior (behind a feature flag if needed).
- **Phase 1 (dual write)**: on image upload, store original + thumbnail and log asset events.
- **Phase 2 (read path)**: return image evidence using the new asset refs; kiosk prefers thumbnails.
- **Phase 3 (enforce)**: require assets to be “ready” before publish eligibility; tighten invalidation hooks.

