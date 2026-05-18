---
title: "Slice 1 — Controlled Scope Foundation"
aliases: ["slice 1", "controlled scope foundation"]
tags: [type/decision, slice/1, goal/7, status/done]
sprint: 1
generated_at: "2026-05-11T07:32:20Z"
generated: true
---

# Slice 1 — Controlled Scope Foundation

**Related goals:** Goal 7 (Controlled Scope & Filtering)  
**Sprint:** Sprint 1 (Apr 27–May 3)  
**Status:** ✅ Completed  
**Work items:** 5  
**Story points:** 26

---

## Overview

Slice 1 established the taxonomy and metadata foundation for controlled retrieval filtering in ResKiosk. It ensures that residents only receive relevant, published, enabled KB content — and never see disabled or unpublished information.

This slice implements the "filtered retrieval" layer that sits between semantic search and the final response.

---

## Goals

### Goal 7 — Controlled Scope & Filtering
Enable operators to control what content is visible to residents through:
- Hard safety rules (enabled=true, published=true)
- Taxonomy-based categorical filtering
- Authority/source metadata filtering
- Scope/context constraints (e.g., "this shelter only")

Filtering must be deterministic, logged, and never bypassable for safety-critical rules.

---

## Work items

| ID | Work Item | Points | Status |
|----|-----------|--------|--------|
| 1.1 | Define taxonomy v1 data model | 5 | ✅ Done |
| 1.2 | Add metadata fields for retrieval filtering | 8 | ✅ Done |
| 1.3 | Enforce hard retrieval rules | 5 | ✅ Done |
| 1.4 | Apply UI and inferred intent filters with precedence | 5 | ✅ Done |
| 1.5 | Log filter decisions and candidate counts | 3 | ✅ Done |

See [[20-sprints/sprint-1/user-stories]] for detailed acceptance criteria.

---

## Architectural impact

### Taxonomy v1 data model

Hierarchical taxonomy structure:
- **Stable node IDs** — survive label changes
- **Labels** — human-readable category names (e.g., "Food & Meals")
- **Parent/child hierarchy** — tree structure (e.g., food > meals > breakfast)
- **Intent mappings** — which intents map to which taxonomy nodes
- **Chip compatibility** — can this node be shown as a clarification chip?

KB items reference taxonomy nodes via `taxonomy_id` foreign key.

### Metadata fields

KB items now have:
- `taxonomy_id` — category/taxonomy node
- `authority_source` — e.g., "Red Cross", "WHO", "Local Admin"
- `scope_context` — e.g., "General", "This Shelter Only", "Region-specific"
- `enabled` — boolean, can this item be retrieved?
- `published` — boolean, is this item published and resident-facing?

### Filter precedence hierarchy

1. **Hard rules** (safety-critical, always applied first)
   - Exclude `enabled = false`
   - Exclude `published = false`
2. **UI filters** (explicitly selected by operator or kiosk user)
   - Selected taxonomy node
   - Selected authority/source
   - Selected scope/context
3. **Inferred filters** (inferred from intent classification)
   - Taxonomy nodes mapped to detected intent
   - Scope inferred from query context

Later filters cannot override earlier filters. If UI selects "food", inferred filter cannot expand to "medical + food".

### Filter logging

Every retrieval logs:
- `hard_rules_applied` — list of exclusion rules
- `ui_filter_taxonomy_id` — explicitly selected node (if any)
- `inferred_taxonomy_ids` — nodes inferred from intent
- `candidate_count_pre_filter` — items before filtering
- `candidate_count_post_filter` — items after filtering
- `widening_triggered` — did system relax filters due to zero results?
- `query_log_id` — link to parent query log

---

## Key decisions

- [[20-sprints/sprint-1/decisions#1.1-D3]] — Hierarchical taxonomy v1 model
- [[20-sprints/sprint-1/decisions#1.3-D4]] — Hard retrieval rules as first-class safety gate
- [[20-sprints/sprint-1/decisions#1.4-D5]] — Filter precedence: hard > UI > inferred

---

## Related slices

- **[[30-decisions/slice-0|Slice 0 — Backbone Contract]]** — Pipeline orchestrator (Sprint 1)
- **[[30-decisions/slice-2|Slice 2 — Clarify-first UX]]** — Taxonomy-backed clarification chips (Sprint 2)
- **[[30-decisions/slice-3|Slice 3 — Trusted KB Publish]]** — Validation-based filtering (Sprint 2-3)

---

## Related architecture

- [[10-architecture/semantic-search]] — Retrieval pipeline with filtering
- [[10-architecture/data-models]] — KB item schema, taxonomy schema
- [[10-architecture/api-surface]] — /query endpoint, filter parameters

---

## Evidence

| Commit | Date | Author | Message |
|--------|------|--------|---------|
| 97c82ae | 2026-05-01 | keithruezyl1 | slide 1 story 1 completed |
| ded5b36 | 2026-05-01 | keithruezyl1 | slice 1 user story 2 delivered |
| 70256b3 | 2026-05-03 | Isaac | Completed Person 2: Story 2 - Add pipeline stage logging skeleton and Story 5 - Log filter decisions and candidate counts |
