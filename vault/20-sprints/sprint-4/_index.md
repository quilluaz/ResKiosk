---
title: "Sprint 4 — ResKiosk AAIH"
aliases: ["sprint 4", "sprint-4"]
tags: [type/sprint-summary, sprint/4, status/proposed]
sprint: 4
generated_at: "2026-05-11T11:37:24Z"
generated: true
---

# Sprint 4 — Multi-path retrieval + observability completion

**Dates:** May 18 – May 24, 2026
**Goal (planned):** Implement compound query handling and complete the main observability foundation before multimodal work accelerates. Make multi-intent questions auditable, measurable, and explainable.
**Status:** ⏳ Proposed (not yet started)
**Planned:** 13 stories, 63 points
**Source:** `ai_helper/sprint-plan.md`

## Stories
[[20-sprints/sprint-4/user-stories]]

## Decisions
_To be created during sprint execution._

## Slices covered (planned)
- **[[30-decisions/slice-5|Slice 5 — Compound Correctness]]** (starting — stories 5.1–5.8)
- **[[30-decisions/slice-6a|Slice 6A — Observability & Trust]]** (continuing — stories 6A.2, 6A.3, 6A.4(?), 6A.5(?), 6A.9)

> Note: the sprint plan lists 6A.4 and 6A.5 here, but the backlog table places 6A.4 and 6A.5 in Sprint 5. Discrepancy to confirm during Sprint 4 planning. The vault `slice-6a.md` reflects the backlog placement (6A.4/6A.5 = Sprint 5).

## Sprint scope at a glance

### Slice 5 — Compound queries (8 stories, 42 pts)
First handling of multi-intent queries beyond the existing single-pass concatenation. Uses the top-2 intents from the classifier to form two retrieval paths, runs hybrid retrieval (Slice 4) per path, and merges with deterministic priority.

### Slice 6A — Observability completion (5 stories, 21 pts)
Latency breakdown, final evidence capture, readable hub logs, and grounding proxy fields make Sprint 5's metrics export workable.

## Sprint outcome (planned)

By 2026-05-24, ResKiosk should:
- Detect compound queries via top-2 intents and run retrieval **per intent path**
- **Merge multi-path results deterministically** with safety/medical priority
- Attribute evidence to its producing path/intent
- Capture **latency breakdowns** per pipeline stage
- Produce **readable live hub logs** for operators during demos

## Related notes

- [[20-sprints/sprint-3/_index|Sprint 3]] — what this builds on
- [[30-decisions/slice-5|Slice 5]] — Compound Correctness design
- [[30-decisions/slice-6a|Slice 6A]] — Observability & Trust (continued)
