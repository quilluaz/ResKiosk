---
title: "Sprint 5 — ResKiosk AAIH"
aliases: ["sprint 5", "sprint-5"]
tags: [type/sprint-summary, sprint/5, status/proposed]
sprint: 5
generated_at: "2026-05-11T11:37:24Z"
generated: true
---

# Sprint 5 — Metrics wrap-up + multimodal schema + early image prep

**Dates:** May 25 – May 31, 2026
**Goal (planned):** Finish metrics/reporting, establish the multimodal schema foundation, and front-load early image asset/model/payload/admin work before graduation-heavy weeks. The **intentional heavy sprint** used to de-risk Sprints 6 and 7.
**Status:** ⏳ Proposed
**Planned:** 17 stories, 87 points (largest sprint in the increment)
**Source:** `ai_helper/sprint-plan.md`

## Stories
[[20-sprints/sprint-5/user-stories]]

## Decisions
_To be created during sprint execution._

## Slices covered (planned)
- **[[30-decisions/slice-6a|Slice 6A — Observability & Trust]]** (finishing — 6A.6, 6A.7)
- **[[30-decisions/slice-7a|Slice 7A — Multimodal Schema]]** (full — 7 stories)
- **[[30-decisions/slice-7b|Slice 7B — Image Asset Lifecycle]]** (starting — 4 stories: 7B.1–7B.4)
- **Slice 7C — Image Embeddings** (only 7C.1 — model selection spike)
- **[[30-decisions/slice-7d|Slice 7D — Kiosk Image Rendering]]** (early — 7D.2 kiosk payload, 7D.7 demo scenarios)

## Why this sprint is heavy

Graduation weeks (Sprint 6 + Sprint 7) reduce team capacity. Sprint 5 front-loads everything that can land before then:
- All multimodal **schema** changes (Slice 7A) — backward-compatible migrations need to be done early so Slice 7B and Slice 7C have something to build on
- Image **upload + thumbnail + hash** plumbing (Slice 7B start)
- Image **embedding model selection** (7C.1 spike) — Sprint 7 can't generate embeddings without a chosen model
- Kiosk **payload contract** for image evidence (7D.2) — kiosk and hub can develop image rendering in parallel after this

## Risk

If Sprint 5 slips, the recommended preservation order (per `sprint-plan.md`):
1. Multimodal schema (7A.1–7A.5) — strict prerequisite
2. Stable evidence identity (7A.2)
3. Image upload API + thumbnails + content hashing (7B.2, 7B.3, 7B.4)
4. Admin upload path (7D.5)
5. Demo scenarios (7D.7) — can defer to Sprint 6

## Related notes

- [[30-decisions/slice-7a|Slice 7A]] — Multimodal Schema
- [[30-decisions/slice-7b|Slice 7B]] — Image Asset Lifecycle
- [[30-decisions/slice-7c|Slice 7C]] — Image Embeddings & Semantic Retrieval
- [[30-decisions/slice-7d|Slice 7D]] — Kiosk Image Rendering & Multimodal Demo
- [[30-decisions/slice-6a|Slice 6A]] — Observability finishing here
