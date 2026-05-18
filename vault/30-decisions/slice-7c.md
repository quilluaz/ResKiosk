---
title: "Slice 7C — Image Embeddings & Semantic Retrieval"
aliases: ["slice 7c", "image embeddings", "text-to-image", "CLIP", "SigLIP"]
tags: [type/decision, slice/7c, goal/1, goal/7, goal/8, goal/10, status/proposed]
sprint: 7
generated_at: "2026-05-11T11:37:24Z"
generated: true
---

# Slice 7C — Image Embeddings & Semantic Retrieval

**Related goals:** Goal 1 (Semantic image search), Goal 7 (Filtering applied to image retrieval), Goal 8 (Validation gating applied), Goal 10 (Image retrieval logging)
**Sprint span:** Sprint 5 (start: 7C.1 model selection only) → Sprint 7 (full: 7C.2–7C.10)
**Status:** ⏳ Proposed (not yet started)
**Work items:** 10
**Story points:** 53

---

## Overview

Slice 7C is the core multimodal capability: **text query → image evidence**. A locally-hosted vision-language embedding model (CLIP or SigLIP, chosen in 7C.1) encodes images at ingest/publish time. At query time, the English-normalized text query is encoded into the same embedding space and matched against image embeddings to retrieve relevant images.

Per the increment's offline-first constraint: **the model must run locally**, no public-internet inference. Per the global English-at-retrieval-boundary rule: text query is already translated to English by NLLB-200 before hitting Slice 7C.

---

## Why dual-path is the chosen tradeoff

From the `aaih-increment-goals.md` session notes: a single multilingual+image model with SOTA quality is uncommon. The practical pattern is:
- **Text retrieval** continues with MiniLM (current baseline, extended by Slice 4 BM25)
- **Image retrieval** uses CLIP/SigLIP separately
- Text and image evidence are merged in the response contract (7C.6)

This is not a unified embedding space — it's two parallel retrieval paths, fused in the response layer.

---

## Work items

### Sprint 5 (1 story, 5 pts) — model selection spike

| ID | Work Item | Points | Status |
|----|-----------|--------|--------|
| 7C.1 | Select and configure image embedding model | 5 | ⏳ Proposed |

### Sprint 7 (9 stories, 48 pts) — full implementation

| ID | Work Item | Points | Status |
|----|-----------|--------|--------|
| 7C.2 | Implement image embedding generation service | 8 | ⏳ Proposed |
| 7C.3 | Persist image embeddings with model and KB version metadata | 8 | ⏳ Proposed |
| 7C.4 | Generate image embeddings during ingest or publish | 5 | ⏳ Proposed |
| 7C.5 | Implement text-to-image semantic retrieval path | 8 | ⏳ Proposed |
| 7C.6 | Merge image evidence with text evidence response structure | 5 | ⏳ Proposed |
| 7C.7 | Apply filtering and validation gates to image retrieval | 5 | ⏳ Proposed |
| 7C.8 | Add image retrieval thresholds and deterministic tie-breaks | 3 | ⏳ Proposed |
| 7C.9 | Log image retrieval evidence and model metadata | 3 | ⏳ Proposed |
| 7C.10 | Create image retrieval evaluation set | 3 | ⏳ Proposed (moved to Sprint 8 as testing task per `sprint-plan.md`) |

---

## Anticipated design (provisional)

> 🔍 Inferred: Model and storage choices land in Sprint 5 (7C.1) and Sprint 7. Below is working understanding from goal/slice docs.

### Model selection (7C.1)
- Candidate models: CLIP (OpenAI variants), SigLIP (Google), open multilingual variants
- Constraints: local inference on Windows EXE deployment, reasonable CPU latency, permissive license
- Output: chosen model name + version + local load path + preprocessing config documented
- Smoke test: round-trip image → embedding → query → retrieval on a tiny test set

### Embedding generation service (7C.2)
- Accepts a `ready`-state image asset (from Slice 7B)
- Preprocesses (resize, normalize per model spec)
- Returns fixed-dimension vector
- Handles failures (corrupt image, model load error) gracefully
- Logs model name, version, error reasons

### Persistence (7C.3)
- New table likely `kb_image_embeddings`:
  ```
  asset_id      TEXT FK to kb_image_assets
  kb_version    INTEGER
  model_name    TEXT
  model_version TEXT
  embedding     BLOB
  created_at    TIMESTAMP
  ```
- Invalidate / regenerate when:
  - asset content_hash changes
  - KB version bumps
  - model version changes

### Retrieval path (7C.5)
- English text query → text-encoder → query embedding
- Cosine similarity against image embedding matrix
- Returns top-k image evidence IDs, scores, ranks, render refs
- Thresholding: similarity floor → don't return low-confidence matches as authoritative
- Tie-breaks: `(score desc, asset_id asc)`

### Filtering + validation gates (7C.7)
- Hard rules (Slice 1) apply: disabled / unpublished / quarantined / non-ready images excluded
- UI filters and inferred filters (Slice 1 precedence) apply to image candidates
- Validation gate (Slice 3) ensures `rejected` images never reach retrieval

### Response merging (7C.6)
- Hub response gains `image_evidence: [...]` alongside text evidence
- Modality field per evidence item (per Slice 7A)
- Deterministic ordering of mixed evidence (text + image)
- Text-only responses preserved when no image evidence returned

### Image retrieval logging (7C.9)
Adds to `query_logs` (or sibling table):
- `image_query_top_k_ids` (TEXT JSON)
- `image_query_top_k_scores` (TEXT JSON)
- `image_query_top_k_ranks` (TEXT JSON)
- `image_model_name`, `image_model_version` (TEXT)
- `image_retrieval_threshold` (REAL)
- `image_retrieval_latency_ms` (REAL)

Top-K cap per [[20-sprints/sprint-3/decisions|3-D2]].

---

## Open decisions for Sprint 5/7

- Exact model (CLIP variant vs SigLIP)
- Embedding dimensionality (affects storage)
- Whether image embeddings live in SQLite BLOB or a separate file/index
- Similarity threshold value
- "Image-first" behavior cutoff (7D.3) — when does image become primary vs supporting?

---

## Dependencies

**Depends on:**
- [[30-decisions/slice-7a|Slice 7A]] — modality schema and evidence contract
- [[30-decisions/slice-7b|Slice 7B]] — ready-state image assets to encode
- [[30-decisions/slice-1]] — filter policy
- [[30-decisions/slice-3]] — publish validation gate

**Blocks:**
- [[30-decisions/slice-7d|Slice 7D]] — kiosk rendering needs the response contract and retrieval to work

---

## Related notes

- [[20-sprints/sprint-5/_index|Sprint 5]] (model spike) and [[20-sprints/sprint-7/_index|Sprint 7]] (full implementation)
- [[30-decisions/goals|Goals — Goal 1]]
- `ai_helper/goal_outlines/goal_1.md` — full goal spec
