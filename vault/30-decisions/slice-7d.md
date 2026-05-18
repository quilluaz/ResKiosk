---
title: "Slice 7D — Kiosk Image Rendering & Multimodal Demo"
aliases: ["slice 7d", "kiosk image rendering", "multimodal demo"]
tags: [type/decision, slice/7d, goal/1, goal/2, goal/10, status/proposed]
sprint: 7
generated_at: "2026-05-11T11:37:24Z"
generated: true
---

# Slice 7D — Kiosk Image Rendering & Multimodal Demo

**Related goals:** Goal 1 (Image evidence display, image-first response), Goal 2 (Thumbnail/original asset consumption), Goal 10 (Multimodal eval and demo metrics)
**Sprint span:** Sprint 5 (early: 7D.2 payload, 7D.5 admin upload, 7D.7 demo scenarios) → Sprint 6 (safety: 7D.4, 7D.6, 7D.10, 7D.11) → Sprint 7 (close: 7D.1, 7D.3, 7D.8, 7D.9)
**Status:** ⏳ Proposed (not yet started)
**Work items:** 11 (8 required + 3 stretch/reclassified)
**Story points:** 53 — 40 required, 13 stretch or moved to Sprint 8 testing tasks

---

## Overview

Slice 7D is the **resident-facing multimodal experience**. Hub returns image evidence (Slice 7C), kiosk renders it natively on Android Compose. Includes thumbnail-first display, graceful handling of missing/broken images, image-first response behavior for visual questions, multimodal demo + regression scenarios, and admin console pieces for asset confirmation.

Critical safety property: **text-only fallback always works**. If image retrieval fails, the asset is missing, or the kiosk can't load a thumbnail, the text answer still renders normally. No image failure ever produces a worse experience than text-only.

---

## Why this is the last slice

Per `implementation_slices_sequence.md`: "Slice 7D comes last because kiosk rendering and demo scenarios depend on stable image evidence payloads, render references, and retrieval behavior." Each preceding multimodal slice (7A schema, 7B assets, 7C retrieval) must be solid before kiosk integration starts.

---

## Work items

### Sprint 5 (3 stories, 16 pts) — early prep

| ID | Work Item | Points | Status |
|----|-----------|--------|--------|
| 7D.2 | Add hub-to-kiosk image evidence payload support | 5 | ⏳ Proposed |
| 7D.5 | Add admin image upload and asset confirmation path | 8 | ⏸ Stretch / deferred |
| 7D.7 | Create multimodal demo scenarios | 3 | ⏳ Proposed |

### Sprint 6 (4 stories, 16 pts) — kiosk safety

| ID | Work Item | Points | Status |
|----|-----------|--------|--------|
| 7D.4 | Handle image loading failures and placeholders | 3 | ⏳ Proposed |
| 7D.6 | Display image asset status in admin console | 5 | ⏸ Stretch / deferred |
| 7D.10 | Validate text-only fallback when image evidence is unavailable | 3 | ⏳ Proposed |
| 7D.11 | Optimize kiosk image loading and display | 5 | ⏳ Proposed |

### Sprint 7 (4 stories, 21 pts) — closing

| ID | Work Item | Points | Status |
|----|-----------|--------|--------|
| 7D.1 | Render image evidence in kiosk responses | 8 | ⏳ Proposed |
| 7D.3 | Support image-first response behavior | 5 | ⏳ Proposed |
| 7D.8 | Create multimodal regression test set | 5 | ⏳ Proposed (moved to Sprint 8 testing) |
| 7D.9 | Log kiosk image display outcomes | 3 | ⏳ Proposed (moved to Sprint 8 testing) |

---

## Anticipated design (provisional)

> 🔍 Inferred: Final UI design lands during Sprint 7. Working understanding from goal/slice docs and the kiosk-ui legacy doc.

### Kiosk image rendering (7D.1)
- New Compose surface in `kiosk/.../ui/` rendering image evidence below or beside the chat bubble
- **Prefer thumbnail** for initial render, optional progressive load to compressed rendition
- **Never load original** in normal operation — too large for kiosk display, defeats the thumbnail/compression purpose
- Associates image with the answer text (caption / context label if provided)
- Empty image arrays = no image surface shown, text bubble unchanged

### Image-first response (7D.3)
For visual queries (e.g., "show me building 3", "what does a sterile bandage look like"):
- Hub marks the response as image-first (`response_modality: "image_first"` or similar)
- Kiosk displays image prominently with minimal text framing
- Near-tie image matches → fall back to clarification (show options) rather than guess
- Low-confidence single match → don't claim as authoritative

### Failure handling (7D.4)
- Missing or broken image ref → placeholder (e.g., simple icon) OR hide image block entirely
- Text answer always remains visible
- Log the failure but never crash
- Hide technical errors from residents

### Text-only fallback (7D.10)
Explicit regression scenarios:
- Hub returns no image evidence — text answer renders normally
- Hub returns image evidence but kiosk can't load it — placeholder + text answer
- Hub returns rejected/invalid image refs — suppressed, text answer survives
- Image retrieval throws error on hub side — log + return text-only response

### Kiosk loading optimization (7D.11)
- Prefer thumbnail (small, fast) for first paint
- Allow compressed rendition load only if context allows (large display, slow scroll-in)
- Preserve aspect ratio — no kiosk-side enhancement / sharpening
- No generative modifications — safety / medical / maps must render faithfully

---

## Admin console pieces (stretch)

### 7D.5 — Admin image upload + asset confirmation (8 pts, stretch)
Console-side upload form, original/thumbnail preview, hash/identity display, KB/taxonomy linkage, clear error display. Deferred because the API exists (7B.2) but the UI is not on the critical path for the demo.

### 7D.6 — Display image asset status in admin console (5 pts, stretch)
Show `pending` / `ready` / `failed` / `rejected` per asset, error reasons, publish eligibility. Deferred for same reason.

---

## Demo + regression sets (Sprint 5 + Sprint 7)

### 7D.7 — Demo scenarios (Sprint 5)
Per `sprint-plan.md`, ~3 categories:
- **Landmark / building** — "where is St. Luke's clinic" → returns building photo
- **Wayfinding** — "how do I get to the medical tent" → returns map/sign image
- **First-aid visuals** — "how do I bandage a wound" → returns step-by-step images

Demo set uses fixed KB + fixed image assets → deterministic results.

### 7D.8 — Regression set (reclassified to Sprint 8 testing task)
Broader test coverage: image queries, hub payload field correctness, kiosk render correctness, safe handling of broken refs. Fixed KB/model/config snapshot. Per `sprint-plan.md` this is no longer a Sprint 7 feature story.

### 7D.9 — Kiosk display outcome logs (reclassified to Sprint 8 testing task)
Log displayed / suppressed / failed / placeholder outcomes per image evidence item, no raw image data, query/session linkage where feasible.

---

## Open decisions for Sprint 7

- Image-first cutoff: similarity threshold or response-shape-driven?
- Whether to show multiple images stacked, carousel, or grid for multi-image evidence
- Caption / alt-text rendering — below image, overlay, or both?
- How long to keep image cached on kiosk after the response (memory pressure on Android)

---

## Dependencies

**Depends on:**
- [[30-decisions/slice-7a|Slice 7A]] — response contract with modality field
- [[30-decisions/slice-7b|Slice 7B]] — ready image assets with thumbnails
- [[30-decisions/slice-7c|Slice 7C]] — text-to-image retrieval providing evidence

**Affects:**
- Final demo + AAIH submission story — visual guidance is the most visible feature

---

## Related notes

- [[20-sprints/sprint-5/_index|Sprint 5]] (3 stories), [[20-sprints/sprint-6/_index|Sprint 6]] (4 stories), [[20-sprints/sprint-7/_index|Sprint 7]] (4 stories), [[20-sprints/sprint-8/_index|Sprint 8]] (3 reclassified as tests)
- [[30-decisions/goals|Goals — Goal 1, Goal 2]]
- `ai_helper/goal_outlines/goal_1.md`, `ai_helper/goal_outlines/goal_2.md`
- `docs/legacy/kiosk-ui.md` — existing kiosk UI patterns to extend
