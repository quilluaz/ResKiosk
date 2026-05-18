---
title: "Sprint 8 — ResKiosk AAIH (Submission)"
aliases: ["sprint 8", "sprint-8", "submission sprint"]
tags: [type/sprint-summary, sprint/8, status/proposed]
sprint: 8
generated_at: "2026-05-11T11:37:24Z"
generated: true
---

# Sprint 8 — E2E testing, benchmarking, regression, final submission

**Dates:** Jun 15 – Jun 20, 2026
**Final submission deadline:** Jun 20, 2026
**Goal:** Validate, benchmark, stabilize, and submit. **No planned feature development.** End-to-end testing, benchmarking, regression, critical/blocking bug fixes only.
**Status:** ⏳ Proposed (reserved)
**Planned work:** 19 testing/stabilization tasks, 0 feature story points
**Source:** `ai_helper/sprint-plan.md`

## Stories

This sprint contains **no user stories**. All work is filed as Jira **Tasks**, **Bugs**, or **Test tasks** rather than feature stories.

## Decisions
_To be created during sprint execution._

## Sprint scope at a glance

### End-to-End testing (5 tasks)
1. Full text-query E2E test (input → normalize → intent → retrieval → response → logs)
2. Clarification E2E test (ambiguous query → chips → retry contract → resumed retrieval → resolution log)
3. Hybrid retrieval E2E test (exact-term → vector + lexical → RRF fusion → filter enforcement → contribution logs)
4. Compound query E2E test (top-2 intents → path-level retrieval → deterministic merge → primary/secondary evidence)
5. Multimodal E2E test (image upload → thumbnail/compressed → embedding → text-to-image → kiosk render → image-first response)

### Benchmarking (4 tasks)
6. Query latency (p50/p95 total, retrieval, rewrite, clarification)
7. Hybrid and multi-path retrieval (vector-only vs hybrid; single-path vs multi-path)
8. Image retrieval (embedding generation time, text-to-image latency, top-k accuracy)
9. Kiosk image loading (thumbnail vs compressed rendition; placeholder/fallback)

### Regression + Submission (10 tasks)
10. Regression suite against fixed KB snapshot
11. Final KPI report by KB version
12. Verify hub logs readable during demo flow
13. Validate image retrieval evaluation set
14. Validate multimodal regression set
15. Verify kiosk image display outcomes
16. Fix critical/blocking bugs only
17. Freeze codebase
18. Prepare final submission package
19. Run final demo rehearsal

## Tasks reclassified from earlier sprints

Three Sprint 7 features were moved here as testing/benchmarking tasks (their feature intent is covered by validation work):

| Originally | Reclassified to | Equivalent task |
|------------|-----------------|-----------------|
| 7C.10 — Image retrieval evaluation set (3 pts) | Sprint 8 task | Task 13 — Validate image retrieval evaluation set |
| 7D.8 — Multimodal regression test set (5 pts) | Sprint 8 task | Task 14 — Validate multimodal regression set |
| 7D.9 — Log kiosk image display outcomes (3 pts) | Sprint 8 task | Task 15 — Verify kiosk image display outcomes |

## What MUST be done before this sprint starts

- Sprint 7 feature-complete (Jun 14) — no feature dev in Sprint 8
- All slices delivered or explicitly deferred
- Multimodal demo path proven (Sprint 7)

## Definition of Done for the increment

By 2026-06-20:
- ✅ All E2E test paths verified end-to-end
- ✅ Latency benchmarks documented (p50/p95)
- ✅ Regression suite passes against fixed KB snapshot
- ✅ Final KPI report produced
- ✅ Demo rehearsal completed
- ✅ Codebase frozen
- ✅ Submission package prepared and submitted

## Related notes

- [[20-sprints/sprint-7/_index|Sprint 7]] — feature-complete sprint preceding this
- [[30-decisions/goals|Goals index]] — what's being submitted
