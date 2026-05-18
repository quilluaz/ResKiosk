---
title: "Slice 7B — Image Asset Lifecycle"
aliases: ["slice 7b", "image assets", "image storage"]
tags: [type/decision, slice/7b, goal/2, goal/10, goal/11, status/proposed]
sprint: 6
generated_at: "2026-05-11T11:37:24Z"
generated: true
---

# Slice 7B — Image Asset Lifecycle

**Related goals:** Goal 2 (Image storage as first-class KB assets), Goal 11 (Version-aware invalidation, partial), Goal 10 (Asset lifecycle logging)
**Sprint span:** Sprint 5 (start: 7B.1–7B.4) → Sprint 6 (finish: 7B.5–7B.10)
**Status:** ⏳ Proposed (not yet started)
**Work items:** 10 (9 required + 1 stretch)
**Story points:** 52 total — 47 required, 5 stretch

---

## Overview

Slice 7B treats KB images as **first-class assets** with stable identity, content hashes, thumbnails, and KB-version linkage. Without this, images would be ad-hoc files on disk with no integrity, dedupe, or invalidation story.

The slice covers:
- **Storage:** durable `kb_image_assets` records with original ref, thumbnail ref, content hash, MIME, size, timestamps
- **Ingestion:** upload API, content hashing, deterministic thumbnail generation, optimized compressed renditions
- **Lifecycle:** `pending` / `ready` / `failed` / `rejected` states, KB version linkage, publish-time invalidation
- **Observability:** lifecycle event logging

---

## Work items

### Sprint 5 (start — 4 stories, 24 pts)

| ID | Work Item | Points | Status |
|----|-----------|--------|--------|
| 7B.1 | Store image assets as first-class KB assets | 8 | ⏳ Proposed |
| 7B.2 | Add image upload API for KB assets | 5 | ⏳ Proposed |
| 7B.3 | Generate content hashes for image assets | 3 | ⏳ Proposed |
| 7B.4 | Generate deterministic thumbnails for image assets | 8 | ⏳ Proposed |

### Sprint 6 (finish — 6 stories, 28 pts)

| ID | Work Item | Points | Status |
|----|-----------|--------|--------|
| 7B.5 | Add image asset processing states | 5 | ⏳ Proposed |
| 7B.6 | Link image assets to KB version | 5 | ⏳ Proposed |
| 7B.7 | Invalidate image artifacts on KB publish | 5 | ⏳ Proposed |
| 7B.8 | Add admin asset confirmation view | 5 | ⏸ Stretch / deferred |
| 7B.9 | Log image asset lifecycle events | 3 | ⏳ Proposed |
| 7B.10 | Compress uploaded images and generate optimized renditions | 5 | ⏳ Proposed |

---

## Anticipated design (provisional)

> 🔍 Inferred: Schema and storage choices happen in Sprint 5. Below is the working understanding from backlog acceptance snapshots.

### kb_image_assets table (proposed)
```
id              TEXT PRIMARY KEY     -- stable asset ID
original_path   TEXT NOT NULL        -- relative path to original file
thumbnail_path  TEXT NULLABLE        -- thumbnail rendition path
compressed_path TEXT NULLABLE        -- optimized display rendition (7B.10)
content_hash    TEXT NOT NULL        -- SHA-256 of original bytes (7B.3)
mime_type       TEXT NOT NULL
size_bytes      INTEGER NOT NULL
width           INTEGER
height          INTEGER
kb_version      INTEGER NOT NULL     -- version this asset belongs to (7B.6)
status          TEXT NOT NULL        -- pending|ready|failed|rejected (7B.5)
created_at      TIMESTAMP NOT NULL
last_updated    TIMESTAMP
```

### Processing states (7B.5)
- `pending` — uploaded, awaiting thumbnail/compression/hash
- `ready` — all artifacts generated, eligible for retrieval (Sprint 7)
- `failed` — processing error (logged with reason)
- `rejected` — failed validation (admin rejected or auto-rejected for unsupported format/size)

Only `ready` assets are exposed to retrieval. Publish must avoid partial assets.

### Thumbnail generation (7B.4)
- Deterministic params: fixed max-dimension (e.g., 256px), specific resampling filter, specific encoder settings
- Stored as separate file referenced by `thumbnail_path`
- Failure marks asset `failed` with logged reason

### Compressed renditions (7B.10)
- Display-size rendition for kiosk (e.g., 1024px max-dimension)
- Deterministic JPEG quality / WebP settings
- Preserves aspect ratio
- Stored as separate file at `compressed_path`

### KB version linkage + invalidation (7B.6, 7B.7)
- Assets created at KB version N are tagged `kb_version = N`
- `POST /admin/publish` increments `kb_version` AND invalidates old image artifacts
- Stable refs within a version — kiosks polling at version N see consistent assets
- Fail-closed on invalidation failure (don't serve stale image artifacts after version bump)

---

## Upload API (7B.2)

> 🔍 Inferred endpoint: `POST /admin/kb/images/upload` (multipart). Returns asset record with status, errors. Validates MIME type and size before storing. Failures logged with reason. Original file stored under a configured asset directory.

Required fields:
- File payload
- Optional caption / alt-text
- Optional taxonomy / KB linkage

Supported formats (proposed): JPEG, PNG, WebP. Max size: TBD (likely 10MB).

---

## Open decisions for Sprint 5/6

- Asset storage location: local filesystem under hub root vs SQLite BLOB vs separate `assets/` directory packaged with the EXE
- PII policy for uploaded images (per goals doc session notes — "PII policy TBD")
- Whether to allow duplicate uploads (same content hash) — currently lean: dedupe by hash, return existing asset ID
- Whether `compressed_path` is required at `ready` state or optional

---

## Dependencies

**Depends on:**
- [[30-decisions/slice-7a|Slice 7A]] — modality schema must exist (`image_asset_id` field on `kb_articles`)
- [[30-decisions/slice-3]] — Trusted KB publish (image assets participate in publish gate)

**Blocks:**
- [[30-decisions/slice-7c|Slice 7C]] — embeddings need `ready` image assets to encode
- [[30-decisions/slice-7d|Slice 7D]] — kiosk needs thumbnail + compressed refs to render

---

## Related notes

- [[20-sprints/sprint-5/_index|Sprint 5]] (4 stories) and [[20-sprints/sprint-6/_index|Sprint 6]] (6 stories)
- [[30-decisions/goals|Goals — Goal 2]]
- `ai_helper/goal_outlines/goal_2.md` — full goal spec
