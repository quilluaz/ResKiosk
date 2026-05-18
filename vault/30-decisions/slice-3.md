---
title: "Slice 3 — Trusted KB Publish"
aliases: ["slice 3", "trusted KB publish", "validation pipeline"]
tags: [type/decision, slice/3, goal/8, goal/10, status/active]
sprint: 3
generated_at: "2026-05-11T07:53:18Z"
generated: true
---

# Slice 3 — Trusted KB Publish

**Related goals:** Goal 8 (KB Quality & Trustworthiness), Goal 10 (Observability & Trust)  
**Sprint:** Split — Sprint 2 (items 3.1–3.2) + Sprint 3 (items 3.3–3.6)  
**Status:** 🔄 In Progress (Sprint 3, May 11–17)  
**Work items:** 6  
**Story points:** 37 total (14 done in Sprint 2, 23 remaining in Sprint 3)

---

## Overview

Slice 3 makes the Knowledge Base trustworthy before it reaches displaced persons. The insight is that a kiosk answering from bad data is worse than no answer at all — so KB content must pass automated validation before it can be published and served by the retrieval system.

The slice introduces a **metadata validation pipeline** that checks every KB article against taxonomy assignments, authority/scope metadata, and content label quality. Articles that fail hard rules are **quarantined** and excluded from retrieval. Articles with warnings need staff review before publish.

---

## Goals

### Goal 8 — KB Quality & Trustworthiness
Ensure only validated, properly-labelled KB articles are served to kiosk users. Prevent low-quality, mislabelled, or incomplete content from reaching the retrieval pipeline.

### Goal 10 — Observability & Trust
Publish events must produce audit logs so operators can trace exactly which articles were approved, which needed review, and which were blocked — and why.

---

## Work Items

| ID | Work Item | Points | Sprint | Status |
|----|-----------|--------|--------|--------|
| 3.1 | Build metadata validation rule engine | 8 | Sprint 2 | ✅ Done |
| 3.2 | Gate article status on validation result | 5 | Sprint 2 | ✅ Done |
| 3.3 | Gate KB publish using validation results | 8 | Sprint 3 | 🔄 In Progress |
| 3.4 | Build MVP metadata review workflow | 8 | Sprint 3 | 🔄 In Progress |
| 3.5 | Exclude quarantined metadata from retrieval | 5 | Sprint 3 | 🔄 In Progress |
| 3.6 | Log validation and publish audit events | 3 | Sprint 3 | 🔄 In Progress |

---

## What Was Delivered in Sprint 2 (3.1, 3.2)

### 3.1 — Metadata Validation Rule Engine

**File:** `hub/validation/metadata.py`

A deterministic rule engine that validates each KB article against 10 rules:

| Rule ID | Severity | What it checks |
|---------|----------|----------------|
| `taxonomy.primary_assignment_missing` | ERROR | Article has at least one taxonomy node assignment |
| `taxonomy.assignment_unknown_node` | ERROR | All assigned taxonomy nodes exist in `taxonomy_nodes` table |
| `taxonomy.assignment_inactive_node` | ERROR | All assigned nodes are active (`is_active=1`) |
| `metadata.authority_missing` | WARNING | `authority` field is populated |
| `metadata.authority_invalid` | ERROR | `authority` is one of: official, shelter_staff, volunteer, unknown |
| `metadata.scope_missing` | WARNING | `scope` field is populated |
| `metadata.scope_invalid` | ERROR | `scope` is one of: shelter_local, general |
| `content.label_empty` | WARNING | `question` and `category` fields are non-empty |
| `content.label_placeholder` | WARNING | No placeholder text (tbd, todo, n/a, placeholder, sample, etc.) |
| `content.label_too_short` | WARNING | question ≥ 5 chars, category ≥ 3 chars, tags ≥ 2 chars |

**Per-article status derivation:**
- Any ERROR failure → `quarantined`
- Only WARNING failures → `needs_review`
- All rules pass → `approved`

**Publish gate status:**
- Any quarantined articles → `PUBLISH_STATUS_BLOCKED` (publish refused)
- Any needs_review → `PUBLISH_STATUS_WARNING` (publish allowed but flagged)
- All approved → `PUBLISH_STATUS_PASS`

### 3.2 — Gate Article Status on Validation Result

Validation results gate the `status` field on `kb_articles`. Articles written as `draft` must be validated and promoted to `approved` (or flagged as `needs_review`/`quarantined`) before the publish gate will allow them through.

---

## What Remains in Sprint 3 (3.3–3.6)

### 3.3 — Gate KB Publish Using Validation Results

`POST /admin/publish` must run the full validation suite and refuse to increment `kb_version` if any articles are `quarantined`. The `build_publish_gate_handoff()` function in `hub/validation/metadata.py` already assembles the `PublishGateHandoff` dataclass. Story 3.3 wires this into the publish route so that `PUBLISH_STATUS_BLOCKED` returns HTTP 422 with the failure reasons.

### 3.4 — MVP Metadata Review Workflow

Console UI allowing staff to see which articles have validation failures and what specifically needs to be fixed before publish. Likely adds a panel to `KBViewer.jsx` displaying the `validation_summary` from the publish response, listing quarantined/needs_review articles with their failing rule IDs.

### 3.5 — Exclude Quarantined Articles from Retrieval

Articles with `status = "quarantined"` must not appear in `search.retrieve()` results, even if `enabled = 1`. This adds a hard filter in `hub/retrieval/search.py` on `status != "quarantined"`. It is a **non-bypassable safety filter**, like the `enabled` filter.

### 3.6 — Log Validation and Publish Audit Events

Every publish attempt must produce a structured audit log entry recording who published, when, which articles passed/failed, and whether publish was blocked.

---

## Key Decisions

### 3-D1: Quarantine is a hard retrieval block, not a soft warning

**Decision:** Quarantined articles are excluded from retrieval regardless of `enabled` status.

**Why:** An article can be `enabled=1` (staff intends for it to be active) but still `quarantined` (validation failed). Serving it could harm displaced persons. The safety default is to exclude it until staff fixes the issue.

**Consequence:** Story 3.5 adds a `status != "quarantined"` filter in `search.retrieve()` that is tested and non-bypassable.

---

### 3-D2: Validation runs at publish time, not at write time

**Decision:** Validation runs when staff clicks "Publish", not when an article is created or edited.

**Why:** Running validation on every write would slow down article editing. The publish gate is the right checkpoint — staff can draft freely and validation only blocks the final publish action.

**Consequence:** Articles in `draft` or `needs_review` can exist in the DB but are not yet in the retrieval pool. The `status` field tracks validation state independently from `enabled`.

---

### 3-D3: Publish is blocked (not just warned) on ERROR-severity failures

**Decision:** Any quarantined article causes `POST /admin/publish` to return `PUBLISH_STATUS_BLOCKED` with HTTP 422.

**Why:** WARNING-level issues (missing authority, short labels) may be acceptable for some shelter scenarios. ERROR-level issues (missing taxonomy, invalid authority value) indicate structural problems that would cause retrieval to produce wrong results.

**Consequence:** Staff must fix all quarantined articles before publishing. The console must surface failure reasons clearly (Story 3.4).

---

## Validation Data Flow

```
POST /admin/publish
    │
    ▼
load_validation_targets(db)       — all enabled articles + taxonomy assignments
load_taxonomy_reference(db)       — known and active node IDs
    │
    ▼
validate_metadata(targets, known_nodes, active_nodes)
    │  → MetadataValidationRunResult
    │     .items[]: per-article results (status + rule_results)
    │     .summary: counts + publish_status
    ▼
build_publish_gate_handoff(result)
    │  → PublishGateHandoff
    │     .blocked: bool
    │     .failure_reasons: tuple[str, ...]
    ▼
if blocked → HTTP 422
else → _increment_kb_version(db) → HTTP 200
```

---

## New Files (Sprint 2)

| File | Purpose |
|------|---------|
| `hub/validation/__init__.py` | Package init |
| `hub/validation/metadata.py` | Rule engine, dataclasses, publish gate logic |
| `hub/tests/test_metadata_validation.py` | Unit tests for validation rules |
| `hub/tests/test_publish_gate.py` | Integration tests for publish gate |

---

## Evidence

| Commit | Date | Author | Message |
|--------|------|--------|---------|
| beabff3 | 2026-05-09 | keithruezyl1 | slice 3 story 1 delivered |
| 0fd6ffb | 2026-05-11 | keithruezyl1 | slice 3 story 3 done! wraaagh! |

> 🔍 Inferred: Stories 3.1 and 3.2 are attributed to Sprint 2 based on dates and the presence of `hub/validation/metadata.py` in the codebase. The commit message "slice 3 story 3 done!" (0fd6ffb, May 11) suggests story 3.3 landed at the start of Sprint 3.

---

## Related

- [[30-decisions/slice-1]] — Controlled Scope Foundation (taxonomy schema that validation checks against)
- [[30-decisions/slice-2]] — Clarify-first UX (pipeline gating patterns)
- [[10-architecture/validation-pipeline]] — Living architecture doc for the validation system
- [[10-architecture/semantic-search]] — Where the quarantine exclusion filter lives (Story 3.5)
- [[00-pre-sprint-baseline/api-surface]] — `/admin/publish` endpoint
