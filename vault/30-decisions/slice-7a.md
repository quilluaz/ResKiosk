---
title: "Slice 7A — Multimodal Schema"
aliases: ["slice 7a", "multimodal schema"]
tags: [type/decision, slice/7a, goal/3, goal/10, status/proposed]
sprint: 5
generated_at: "2026-05-11T11:37:24Z"
generated: true
---

# Slice 7A — Multimodal Schema

**Related goals:** Goal 3 (KB schema rework for multimodal retrieval), Goal 10 (Modality-aware evidence logging), integration with Goal 7 (filtering)
**Sprint:** Sprint 5 (May 25–31) — proposed
**Status:** ⏳ Proposed (not yet started)
**Work items:** 7
**Story points:** 34

---

## Overview

Slice 7A introduces the **minimum schema changes** needed for ResKiosk to represent both text and image evidence without breaking the existing text-only KB. This is **schema-only work** — no embedding, no retrieval, no rendering. Slices 7B (assets), 7C (embeddings), and 7D (kiosk) build on top.

Today, every KB article is implicitly text. `kb_articles` has a `question`, `answer`, and a single `embedding` BLOB. There is no modality field, no image asset linkage, no separate evidence identity for image content. Slice 7A adds the structural foundation in an **additive, backward-compatible** way: existing text rows keep working unchanged.

---

## Why schema first

Per `implementation_slices_sequence.md`: "Slice 7A comes first because image retrieval and image assets require a modality-aware schema and evidence contract." If image assets (7B) or embeddings (7C) are built before the schema is multimodal-ready, those features end up writing into ad-hoc fields that need re-migration later.

---

## Work items

| ID | Work Item | Points | Status |
|----|-----------|--------|--------|
| 7A.1 | Add multimodal KB item schema | 8 | ⏳ Proposed |
| 7A.2 | Add stable multimodal evidence identity | 5 | ⏳ Proposed |
| 7A.3 | Prepare image asset reference fields | 5 | ⏳ Proposed |
| 7A.4 | Add forward-compatible segmentation fields | 3 | ⏳ Proposed |
| 7A.5 | Update evidence response contract for modality | 5 | ⏳ Proposed |
| 7A.6 | Backfill existing KB articles as text modality | 5 | ⏳ Proposed |
| 7A.7 | Add modality-aware evidence logging | 3 | ⏳ Proposed |

---

## Anticipated changes (provisional)

> 🔍 Inferred: Specific column names and table choices happen in Sprint 5. Working assumptions below from the increment goals doc and backlog acceptance snapshots.

### kb_articles
- `modality TEXT NOT NULL DEFAULT 'text'` — `text` | `image`
- `image_asset_id TEXT NULLABLE` — FK to forthcoming `kb_image_assets` table (created in 7B)
- `parent_article_id TEXT NULLABLE` — forward-compat segmentation (7A.4)
- `chunk_index INTEGER NULLABLE` — forward-compat segmentation (7A.4)

### Evidence identity (7A.2)
- Existing `kb_articles.id` stays the evidence ID for text rows.
- Image evidence gets its own stable ID, likely `evidence_id` separate from `id` — discriminated by `modality`.
- Evidence IDs tied to `kb_version` so a published KB has a fixed set of evidence IDs.

### Response contract (7A.5)
Existing `EvidenceItem` (or equivalent) gains:
- `modality: "text" | "image"`
- `evidence_id: str` (independent of `source_id` for backward compat)
- `render_ref: { thumbnail_url, original_url } | None` (None for text)

Text-only clients keep working: `modality` defaults to `"text"`, image-specific fields are absent.

### Backfill (7A.6)
All existing `kb_articles` rows updated:
- `modality = 'text'`
- `enabled`, `status`, `embedding` all preserved
- No retrieval behavior change for existing rows

### Modality-aware logging (7A.7)
`query_logs` (or sibling evidence log) gains:
- `evidence_modalities TEXT (JSON)` — array of `["text", "image", ...]` matching final evidence order
- Top-K caps per [[20-sprints/sprint-3/decisions|3-D2]]

---

## Open decisions for Sprint 5

- Single `kb_articles` table with `modality` field vs separate `kb_image_evidence` table — current lean: extend `kb_articles` for simplicity
- Whether `evidence_id` is its own column or computed (e.g., `f"{modality}:{id}"`)
- How segmentation fields (7A.4) interact with the increment-wide "no semantic chunking" rule — answer: present in schema, never populated this increment

---

## Dependencies

**Depends on:**
- [[30-decisions/slice-0]] — Canonical pipeline (where modality flows through)
- [[30-decisions/slice-1]] — Filter policy (modality may become a filter dimension)
- [[30-decisions/slice-3]] — Trusted KB publish (image evidence must also pass validation)
- [[30-decisions/slice-6a|Slice 6A]] — Observability (evidence logging extension)

**Blocks:**
- [[30-decisions/slice-7b|Slice 7B]] — Image asset lifecycle needs `image_asset_id` field to point to
- [[30-decisions/slice-7c|Slice 7C]] — Image embeddings need modality-tagged evidence
- [[30-decisions/slice-7d|Slice 7D]] — Kiosk needs modality field in response contract

---

## Related notes

- [[20-sprints/sprint-5/_index|Sprint 5]]
- [[30-decisions/goals|Goals — Goal 3]]
- `ai_helper/goal_outlines/goal_3.md` — full goal spec
