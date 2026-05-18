---
title: "Sprint 7 — ResKiosk AAIH"
aliases: ["sprint 7", "sprint-7", "feature-complete sprint"]
tags: [type/sprint-summary, sprint/7, status/proposed]
sprint: 7
generated_at: "2026-05-11T11:37:24Z"
generated: true
---

# Sprint 7 — Multimodal retrieval + image-first demo (feature-complete cutoff)

**Dates:** Jun 8 – Jun 14, 2026
**Goal (planned):** Deliver the core multimodal image workflow before the feature-complete cutoff. Image embeddings, text-to-image retrieval, evidence response integration, image-first behavior, and kiosk display.
**Status:** ⏳ Proposed
**Planned:** 10 stories, 58 points
**Source:** `ai_helper/sprint-plan.md`

**⚠️ Feature-complete cutoff is Jun 14 — anything not shipped by end of Sprint 7 moves to Sprint 8 as a testing task or is dropped.**

## Stories
[[20-sprints/sprint-7/user-stories]]

## Decisions
_To be created during sprint execution._

## Slices covered (planned)
- **[[30-decisions/slice-7c|Slice 7C — Image Embeddings & Semantic Retrieval]]** (full — 7C.2–7C.10, minus 7C.1 done in Sprint 5)
- **[[30-decisions/slice-7d|Slice 7D — Kiosk Image Rendering]]** (closing — 7D.1, 7D.3, 7D.8, 7D.9)

## Critical workflow this sprint enables

```
admin uploads image  (Sprint 5–6 plumbing)
       │
       ▼
embedding generation  (Sprint 7: 7C.2, 7C.4)
       │
       ▼
text query  (existing pipeline)
       │
       ▼
text-to-image retrieval  (Sprint 7: 7C.5)
       │
       ▼
fusion with text evidence  (Sprint 7: 7C.6)
       │
       ▼
filtering + thresholds  (Sprint 7: 7C.7, 7C.8)
       │
       ▼
kiosk renders image evidence  (Sprint 7: 7D.1)
       │
       ▼
image-first response when appropriate  (Sprint 7: 7D.3)
```

## Risk / preservation order

If Sprint 7 slips (per `sprint-plan.md`):
1. Image embedding generation (7C.2) — without it, nothing else works
2. Text-to-image retrieval (7C.5)
3. Kiosk image rendering (7D.1)
4. Image-first response behavior (7D.3)
5. Expanded evaluation coverage — can move to Sprint 8 testing tasks

## Sprint outcome (planned)

- Hub encodes image assets during ingest/publish
- Image embeddings persisted with model + KB version metadata
- English text queries can return image evidence
- Filtering and validation gates apply to image retrieval
- Kiosk displays image evidence for the demo path
- Image-first response behavior for visual questions
- Multimodal regression test set in place

## Moved to Sprint 8 testing tasks

These were originally Sprint 7 features but are reclassified as testing tasks (no feature dev in Sprint 8):
- 7C.10 — Image retrieval evaluation set (3 pts)
- 7D.8 — Multimodal regression test set (5 pts)
- 7D.9 — Kiosk image display outcome logs (3 pts)

## Related notes

- [[30-decisions/slice-7c|Slice 7C]] — Image Embeddings & Semantic Retrieval
- [[30-decisions/slice-7d|Slice 7D]] — Kiosk Image Rendering & Multimodal Demo
- [[20-sprints/sprint-5/_index|Sprint 5]] — model selection (7C.1) prerequisite
- [[20-sprints/sprint-6/_index|Sprint 6]] — image asset lifecycle prerequisite
- [[20-sprints/sprint-8/_index|Sprint 8]] — testing tasks reclassified from this sprint
