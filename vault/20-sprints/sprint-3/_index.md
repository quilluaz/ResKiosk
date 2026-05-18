---
title: "Sprint 3 — ResKiosk AAIH"
aliases: ["sprint 3", "sprint-3", "current sprint"]
tags: [type/sprint-summary, sprint/3, status/active]
sprint: 3
generated_at: "2026-05-15T08:48:57Z"
generated: true
---

# Sprint 3 — Validation completion + hybrid retrieval + early observability

**Dates:** May 11 – May 17, 2026
**Goal:** Complete the trusted publish gate, stand up the deterministic hybrid retrieval core (lexical BM25 + RRF fusion), and pull core structured logging earlier so retrieval changes are observable while they are being built.
**Status:** 🔄 Active (Day 5 of 7)
**Planned:** 11 stories, 59 points
**Delivered:** 9 stories, 53 points
**Remaining:** 2 stories, 6 points (3.6, 4.5, 6A.8)

## Stories
[[20-sprints/sprint-3/user-stories]]

## Decisions
[[20-sprints/sprint-3/decisions]]

## Slices covered
- **[[30-decisions/slice-3|Slice 3 — Trusted KB Publish]]** (completing — stories 3.3–3.6)
- **[[30-decisions/slice-4|Slice 4 — Deterministic Retrieval Core]]** (starting — stories 4.1–4.6)
- **[[30-decisions/slice-6a|Slice 6A — Observability & Trust]]** (starting — stories 6A.1, 6A.8)

## Sprint scope at a glance

### Slice 3 finish (4 stories, 24 pts)
The validation foundation built in Sprint 2 (3.1 rule engine, 3.2 audit storage, 3.3 publish gate) needs to become end-to-end usable. Sprint 3 closes the loop:
- **3.4** Console review workflow for quarantined / needs_review articles (8 pts)
- **3.5** Hard exclusion of quarantined articles from retrieval (5 pts)
- **3.6** Structured publish-audit logging (3 pts)
- 3.3 already landed on day 1 — see [[20-sprints/sprint-2/decisions|2-D4]] for why it's counted as Sprint 2 work.

### Slice 4 hybrid retrieval (6 stories, 32 pts)
First major retrieval improvement of the increment. Adds a lexical (BM25-like) path alongside the existing MiniLM vector path, then fuses them with RRF.
- **4.1** Build lexical retrieval index — version-aware, rebuildable from `kb_articles` (8 pts)
- **4.2** BM25-like lexical scoring with deterministic tokenization (5 pts)
- **4.3** RRF fusion with explicit strategy + stable tie-breaks (8 pts)
- **4.4** Apply hard/UI/inferred filter precedence to both paths (5 pts)
- **4.5** Log lexical/vector/fusion contributions per evidence item (3 pts)
- **4.6** Exact-term retrieval evaluation set for measuring lift (3 pts)

### Slice 6A early observability (2 stories, 11 pts)
Pulled into Sprint 3 (originally Sprint 4) so Slice 4's hybrid logs have a schema target.
- **6A.1** Complete structured query log schema (8 pts) — adds intent, clarification, lexical/vector/fusion, fallback columns. Per [`slice6a_story1_running_context.md`](../../../slice6a_story1_running_context.md), this is the interface contract for Person 3 (lexical), Person 4 (fusion), and Person 5's later stories.
- **6A.8** Failure and fallback outcome logging (3 pts) — `fallback_reason` and `failed_stage` columns populated when retrieval can't produce a confident answer.

## Story → owner mapping (best-effort)

> 🔍 Inferred from `slice6a_story1_running_context.md` and Sprint 1 git history. The team has at least 5 contributors. Mapping below is provisional and should be confirmed with each person.

| Person | Stories assumed |
|--------|-----------------|
| Person 3 | 4.1, 4.2 (lexical index + BM25 scoring) |
| Person 4 | 4.3 (RRF fusion) |
| Person 5 | 6A.1, 4.5, 6A.8 (logging schema + contribution logs + fallback logs) |
| Others | 3.4, 3.5, 3.6, 4.4, 4.6 (validation finish + filter policy + eval set) |

## Critical-path note

Story **6A.1 must land first**. The lexical, vector, and fusion columns added in 6A.1 are interface contracts for stories 4.1–4.5. If 6A.1 slips, the rest of Slice 4 builds against an absent schema and stories 4.5 (contribution logging) and 6A.8 (failure logging) have no target columns to write to. See [[20-sprints/sprint-3/decisions|3-D1]] for the full sequencing call.

## What shipped

### Day 1 (May 11)
- `d129eb6` — Story 6A.1: Complete structured query log schema ✅
- `0fd6ffb` — Story 3.3: Gate KB publish using validation results ✅ (carried from Sprint 2)

### Day 3 (May 13)
- `52db9bc` — Stories 4.1 & 4.2: Lexical retrieval index + BM25 scoring ✅
- `b8735ed` — Story 3.5 support: exclude_ids filter for lexical search

### Day 5 (May 15)
- `ca74223` — Story 3.4: MVP metadata review workflow ✅
- `c34c373` — Stories 3.5 & 4.4: Exclude quarantined from retrieval + filter policy ✅
- `deebebd` + `d37098b` — Stories 4.3 & 4.6: RRF fusion + evaluation set ✅

**Sprint 3 velocity:** 53 points delivered across 5 days (10.6 pts/day)

## Deferred from Sprint 3

| ID | Story | Points | Disposition |
|----|-------|--------|-------------|
| 4.7 | Tune feedback-adjusted ranking as a separate layer | 5 | Stretch — see `ai_helper/sprint-plan.md` |

## What "Done" looks like

By 2026-05-17 (Sunday), ResKiosk should be able to:
- **Refuse to publish** a KB that has quarantined articles, and surface the failures in the admin console (3.3, 3.4)
- **Never retrieve a quarantined article** even with `enabled=1` (3.5)
- **Produce a per-publish audit log** that captures who, when, version, pass/fail counts (3.6)
- **Retrieve via both BM25 and MiniLM in parallel**, fuse with RRF, and produce deterministic top-k rankings (4.1–4.4)
- **Explain each result** via per-item lexical/vector/fusion contribution scores in logs (4.5)
- **Measure exact-term retrieval improvement** against a fixed evaluation set (4.6)
- **Log every query with 15 new structured columns** including intent, retrieval contributions, and fallback reason (6A.1 ✅ shipped `d129eb6`; 6A.8 in progress). Clarification logging remains in Sprint 2's `clarification_options_shown` / `ClarificationResolution` (see [[30-decisions/slice-6a|6A-D6]]).

## Related notes

- [[30-decisions/slice-3]] — Trusted KB Publish design
- [[30-decisions/slice-4]] — Deterministic Retrieval Core design (new in this sprint)
- [[30-decisions/slice-6a]] — Observability & Trust design (new in this sprint)
- [[20-sprints/sprint-2/_index|Sprint 2]] — what this sprint builds on
- [[00-pre-sprint-baseline/_index|Pre-sprint baseline]] — system snapshot before this work
