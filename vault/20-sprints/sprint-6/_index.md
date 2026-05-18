---
title: "Sprint 6 — ResKiosk AAIH"
aliases: ["sprint 6", "sprint-6"]
tags: [type/sprint-summary, sprint/6, status/proposed]
sprint: 6
generated_at: "2026-05-11T11:37:24Z"
generated: true
---

# Sprint 6 — Image asset completion + admin/kiosk safety (graduation-light)

**Dates:** Jun 1 – Jun 7, 2026
**Goal (planned):** Complete image asset lifecycle, add admin asset/status visibility, and finish kiosk image safety work. Intentionally lighter due to team graduation commitments.
**Status:** ⏳ Proposed
**Planned:** 10 stories, 44 points
**Source:** `ai_helper/sprint-plan.md`

## Stories
[[20-sprints/sprint-6/user-stories]]

## Decisions
_To be created during sprint execution._

## Slices covered (planned)
- **[[30-decisions/slice-7b|Slice 7B — Image Asset Lifecycle]]** (finishing — 7B.5–7B.10)
- **[[30-decisions/slice-7d|Slice 7D — Kiosk Image Rendering]]** (kiosk safety: 7D.4, 7D.6, 7D.10, 7D.11)

## Why "graduation-light"

Most of the team is busy with graduation during this week. Sprint 6 is sized at 44 pts vs Sprint 5's 87 pts. Scope kept narrow:
- Finish image asset processing states + KB version linkage + invalidation
- Kiosk image safety: failure placeholders, text-only fallback, optimized loading
- Admin asset status display

## Risk / preservation order

If Sprint 6 slips (per `sprint-plan.md`):
1. Processing states (7B.5) — strict prerequisite for Sprint 7 retrieval
2. KB version linkage (7B.6) and artifact invalidation (7B.7)
3. Optimized renditions (7B.10)
4. Admin status display (7D.6) — can defer

## Sprint outcome (planned)

- Hub has `pending` / `ready` / `failed` / `rejected` image states
- KB-versioned image assets with publish invalidation
- Kiosk safely handles broken/missing images with placeholders
- Text-only fallback verified when image evidence is unavailable
- Admin can see image asset readiness status

## Related notes

- [[20-sprints/sprint-5/_index|Sprint 5]] — image asset work started here
- [[30-decisions/slice-7b|Slice 7B]] — Image Asset Lifecycle
- [[30-decisions/slice-7d|Slice 7D]] — Kiosk Image Rendering
