---
title: "Slice 0 — Backbone Contract"
aliases: ["slice 0", "backbone contract"]
tags: [type/decision, slice/0, goal/12, goal/10, status/done]
sprint: 1
generated_at: "2026-05-11T07:32:20Z"
generated: true
---

# Slice 0 — Backbone Contract

**Related goals:** Goal 12 (Pipeline Safety & Control), Goal 10 (Observability & Trust)  
**Sprint:** Sprint 1 (Apr 27–May 3)  
**Status:** ✅ Completed  
**Work items:** 3  
**Story points:** 18

---

## Overview

Slice 0 established ResKiosk's canonical query processing backbone — a single controlled pipeline path with initial logging and the architectural foundation for clarification pauses. This slice created the "contract" that all future query handling must follow.

---

## Goals

### Goal 12 — Pipeline Safety & Control
Ensure all queries flow through a single, testable, auditable path with no parallel processing or inline shortcuts. This prevents bypasses of safety rules and makes the system's behavior deterministic.

### Goal 10 — Observability & Trust
Capture structured logs at every pipeline stage so operators can understand query lifecycle, troubleshoot failures, and audit system behavior.

---

## Work items

| ID | Work Item | Points | Status |
|----|-----------|--------|--------|
| 0.1 | Create canonical pipeline orchestrator | 8 | ✅ Done |
| 0.2 | Add pipeline stage logging skeleton | 5 | ✅ Done |
| 0.3 | Add clarification pause state to query flow | 5 | ✅ Done |

See [[20-sprints/sprint-1/user-stories]] for detailed acceptance criteria.

---

## Architectural impact

### Canonical pipeline stages

All queries now flow through these stages in order:

1. **Normalization** — lowercase, synonym expansion, domain corrections
2. **Intent classification** — prototype-based intent detection with confidence scores
3. **Clarification check** — pause if ambiguous (implemented in Sprint 2)
4. **Query rewrite** — optional LLM rewrite for noisy transcripts
5. **Retrieval** — semantic search + filtering
6. **Formatting** — LLM-based response phrasing
7. **Translation** — NLLB translation to user's language

### Logging structure

The pipeline stage logging skeleton captures:
- Request ID (for tracing)
- Timestamp
- Normalized query
- Intent classification results (top intent, confidence)
- Clarification trigger status
- Rewrite state (triggered? rewritten query?)
- Retrieval metadata (source, score, candidate count)

Logs are structured (likely JSON or structured DB rows) for later querying.

### Clarification pause state

When clarification is needed:
- Pipeline stops BEFORE retrieval
- Returns `needs_clarification: true` response
- Includes clarification options and resume context
- Non-clarification queries pass through unchanged

This foundation enables Sprint 2's clarification UX.

---

## Key decisions

- [[20-sprints/sprint-1/decisions#0.1-D1]] — Single canonical pipeline path
- [[20-sprints/sprint-1/decisions#0.3-D2]] — Clarification pause state

---

## Related slices

- **[[30-decisions/slice-1|Slice 1 — Controlled Scope Foundation]]** — Filtering and taxonomy (Sprint 1)
- **[[30-decisions/slice-2|Slice 2 — Clarify-first UX]]** — Clarification trigger and chip UI (Sprint 2)

---

## Related architecture

- [[10-architecture/voice-pipeline]] — End-to-end query flow
- [[10-architecture/intent-system]] — Intent classification
- [[10-architecture/clarification-system]] — Clarification trigger and resolution (Sprint 2+)
- [[10-architecture/api-surface]] — /query endpoint contract

---

## Evidence

| Commit | Date | Author | Message |
|--------|------|--------|---------|
| a326ebb | 2026-05-03 | whitefangggggg | Slice 0 : Story 1 (Canonical Pipeline) complete |
| 70256b3 | 2026-05-03 | Isaac | Completed Person 2: Story 2 - Add pipeline stage logging skeleton and Story 5 - Log filter decisions and candidate counts |
| 4f29463 | 2026-05-03 | Selina Mae Genosolango | Feat: Added Clarification Pause State to Query Flow |
