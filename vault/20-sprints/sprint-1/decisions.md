---
title: "Sprint 1 — Decisions"
tags: [type/decision, sprint/1]
sprint: 1
generated_at: "2026-05-11T07:32:20Z"
generated: true
---

# Sprint 1 — Key decisions

## 0.1-D1: Single canonical pipeline path

**Status:** Accepted  
**Date:** 2026-05-03  
**Related stories:** 0.1, 0.2, 0.3

### Context
Prior to Sprint 1, query handling in ResKiosk may have had multiple code paths or inline processing that made it difficult to add consistent logging, clarification pauses, and stage-level observability.

### Decision
All hub query handling now flows through a single canonical pipeline orchestrator with defined stages:

1. Query normalization
2. Intent classification
3. Clarification check (pause if needed)
4. Query rewrite (optional, for noisy queries)
5. Retrieval (semantic search + filters)
6. Response formatting (LLM)
7. Translation

This canonical path is the ONLY way queries are processed — no parallel code paths, no inline shortcuts.

### Consequences
**Benefits:**
- Consistent logging at every stage
- Ability to pause pipeline at clarification stage without reaching retrieval
- Testable stage order
- Single place to add future pipeline enhancements (hybrid retrieval, multi-path, caching)

**Drawbacks:**
- Slightly more rigid — adding stages requires updating the orchestrator
- All queries go through same path even if some stages could be skipped for simple queries

### Related notes
- [[10-architecture/voice-pipeline]]
- [[20-sprints/sprint-1/user-stories#0.1]]

---

## 0.3-D2: Clarification pause state

**Status:** Accepted  
**Date:** 2026-05-03  
**Related stories:** 0.3

### Context
Sprint 1 laid the foundation for Sprint 2's clarification UX. The system needed a way to pause the query pipeline before retrieval when the user's intent is ambiguous, and resume later with additional context.

### Decision
The query flow now supports a `needs_clarification` state:
- When triggered, the pipeline skips rewrite, retrieval, and formatting stages
- Returns a structured response with `needs_clarification: true` and clarification options
- Includes resume context (e.g., original query, detected intents, session ID)
- Non-clarification queries flow through unchanged

The pause happens AFTER intent classification but BEFORE retrieval.

### Consequences
**Benefits:**
- Safe pause point — no wasted retrieval or LLM calls for ambiguous queries
- Resume context allows later stages to pick up where they left off
- Existing direct-answer queries unaffected

**Drawbacks:**
- Adds complexity to API response contract (now has multiple shapes: direct answer, needs clarification, error)
- Kiosk must handle clarification state (implemented in Sprint 2)

### Related notes
- [[10-architecture/clarification-system]]
- [[20-sprints/sprint-1/user-stories#0.3]]

---

## 1.1-D3: Hierarchical taxonomy v1 model

**Status:** Accepted  
**Date:** 2026-05-01  
**Related stories:** 1.1, 1.2, 1.4

### Context
Controlled scope filtering requires a stable way to categorize KB items and map them to intents. The taxonomy needs to support:
- Hierarchical categories (e.g., food > meals > breakfast)
- Intent-to-taxonomy mappings
- Clarification chip compatibility (used in Sprint 2)
- UI and inferred filter selection

### Decision
Implemented taxonomy v1 with:
- Stable taxonomy node IDs (integers or UUIDs)
- Labels (human-readable, e.g., "Food & Meals")
- Parent/child hierarchy (tree structure)
- Intent mappings (which intents map to which taxonomy nodes)
- Chip compatibility flag (can this node be shown as a clarification chip?)

KB items reference taxonomy nodes via `taxonomy_id` foreign key.

### Consequences
**Benefits:**
- Stable IDs survive label changes
- Hierarchical structure supports future drill-down or generalization logic
- Intent-to-taxonomy mapping makes inferred filtering deterministic
- Chip compatibility enables Sprint 2's clarification UX

**Drawbacks:**
- Taxonomy changes (adding/removing nodes) require migrations or admin tooling
- Initial taxonomy design constrains future retrieval behavior

### Related notes
- [[10-architecture/data-models]]
- [[20-sprints/sprint-1/user-stories#1.1]]
- [[20-sprints/sprint-1/user-stories#1.2]]

---

## 1.3-D4: Hard retrieval rules as first-class safety gate

**Status:** Accepted  
**Date:** 2026-05-03  
**Related stories:** 1.3, 1.4

### Context
In a disaster shelter context, serving disabled or unpublished KB content to residents could provide outdated, incorrect, or dangerous information. The system needed a non-negotiable safety gate.

### Decision
Hard retrieval rules are applied FIRST, before any other filtering logic:
1. Exclude where `enabled = false`
2. Exclude where `published = false` or `publish_status != 'published'`

These rules:
- Are NOT configurable by operators
- Cannot be overridden by UI or inferred filters
- Are logged every time they exclude content
- Are safety-critical and tested

UI filters and inferred filters are applied AFTER hard rules pass.

### Consequences
**Benefits:**
- Guarantees disabled/unpublished content never reaches residents
- Provides audit trail of exclusions
- Clear separation between safety-critical rules and soft filtering
- Testable, deterministic behavior

**Drawbacks:**
- No "draft mode" or "preview unpublished" for operators in resident-facing flow (admin console needed for that)

### Related notes
- [[10-architecture/semantic-search]]
- [[20-sprints/sprint-1/user-stories#1.3]]

---

## 1.4-D5: Filter precedence: hard > UI > inferred

**Status:** Accepted  
**Date:** 2026-05-03  
**Related stories:** 1.4, 1.5

### Context
Multiple filter sources (hard safety rules, explicit UI selections, inferred intent-based filters) can conflict. The system needed a deterministic precedence order to ensure predictable behavior.

### Decision
Filter precedence hierarchy:
1. **Hard rules** — safety-critical, always applied first, non-negotiable
2. **UI filters** — explicitly selected by operator or kiosk user (e.g., taxonomy node selection)
3. **Inferred filters** — taxonomy nodes or scope inferred from intent classification

Later filters cannot override or widen earlier filters. If UI filter selects "food" taxonomy node, inferred filter cannot expand to "medical + food".

All filter decisions are logged with source (hard/UI/inferred) and resulting candidate counts.

### Consequences
**Benefits:**
- Deterministic, repeatable filtering behavior
- UI selections take precedence over automated inference (human-in-the-loop)
- Safety rules always applied regardless of other filters
- Full audit trail of filter decisions

**Drawbacks:**
- No automatic fallback widening if UI filter produces zero results (that's a future feature)
- Intent inference cannot "correct" overly narrow UI selections

### Related notes
- [[10-architecture/semantic-search]]
- [[20-sprints/sprint-1/user-stories#1.4]]
- [[20-sprints/sprint-1/user-stories#1.5]]
