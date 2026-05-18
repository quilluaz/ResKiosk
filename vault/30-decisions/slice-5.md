---
title: "Slice 5 — Compound Correctness"
aliases: ["slice 5", "compound queries", "multi-path retrieval"]
tags: [type/decision, slice/5, goal/5, goal/4, goal/7, goal/10, goal/12, status/proposed]
sprint: 4
generated_at: "2026-05-11T11:37:24Z"
generated: true
---

# Slice 5 — Compound Correctness

**Related goals:** Goal 5 (Multi-path retrieval), Goal 4 (Hybrid per-path), Goal 7 (Filters per-path), Goal 12 (Pipeline), Goal 10 (Observability)
**Sprint:** Sprint 4 (May 18–24) — proposed
**Status:** ⏳ Proposed (not yet started)
**Work items:** 8
**Story points:** 42

---

## Overview

Slice 5 handles **compound queries** — questions that contain more than one intent, e.g. *"I have a high fever, where is the nearest doctor?"* (medical + location), or *"my kid is missing and I need food"* (lost_person + food).

Today (baseline), the intent classifier has `classify_top2` + `_resolve_compound_intents` and can mark compound by merging both intents' enrichment strings into **one** `search_query`. Retrieval still runs **once** against a single concatenated embedding — there is no per-intent retrieval. This works for similar intents but fails when the two intents need fundamentally different evidence (medical advice vs facility location).

Slice 5 splits compound queries into **intent-scoped retrieval paths**, runs hybrid retrieval (Slice 4) on each path independently, then merges the results with explicit priority rules (safety/medical first).

---

## Why this slice depends on Slice 4

Without Slice 4's deterministic hybrid retrieval, multi-path retrieval has no stable per-path scoring base. Slice 5 reuses the Slice 4 fusion (RRF) machinery — each compound path is a full Slice 4 retrieval call, and then a **second merge step** combines paths.

---

## Work items

| ID | Work Item | Points | Status |
|----|-----------|--------|--------|
| 5.1 | Detect compound queries using top-2 intents | 5 | ⏳ Proposed |
| 5.2 | Build intent-scoped retrieval path queries | 5 | ⏳ Proposed |
| 5.3 | Run retrieval separately per compound path | 8 | ⏳ Proposed |
| 5.4 | Merge compound path results deterministically | 8 | ⏳ Proposed |
| 5.5 | Add evidence attribution for compound results | 5 | ⏳ Proposed |
| 5.6 | Support primary and secondary compound response outputs | 5 | ⏳ Proposed |
| 5.7 | Log compound lifecycle and merge decisions | 3 | ⏳ Proposed |
| 5.8 | Create compound retrieval evaluation scenarios | 3 | ⏳ Proposed |

See [[20-sprints/sprint-4/user-stories|Sprint 4 user stories]] when expanded.

---

## Anticipated design (provisional)

> 🔍 Inferred: Final design decisions happen in Sprint 4. The following is the working understanding from `ai_helper/implementation_slices_sequence.md` and the backlog acceptance snapshots.

### Compound trigger
- Classifier exposes top-2 intents with confidences (5.1).
- Compound flag set when:
  - both intents above some threshold (e.g., ≥ 0.4) AND
  - intents differ meaningfully (not just two facets of the same topic)
- Below threshold → single-path retrieval (existing behavior).

### Per-path queries (5.2)
- Each intent produces its own `path_query` with intent-specific enrichment and constraints.
- Filters (UI + inferred per Slice 1) applied per path.
- Clarification selection (Slice 2) respected — if user picked "medical" chip, the medical path's filter is tightened, the other path may be dropped.

### Per-path retrieval (5.3)
- Each path calls Slice 4's hybrid retrieval (lexical + vector + RRF) independently.
- Each path returns its own top-k with full attribution.
- Zero-result path handled deterministically (logged, doesn't poison the merge).

### Deterministic merge (5.4)
- Explicit priority rules:
  - **Safety / medical intents win primary slot** when both paths produce evidence
  - Dedupe by `kb_articles.id` — same article appearing in both paths gets the higher-confidence path's attribution
  - Tie-break stable: `(merged_score desc, path_priority asc, kb_articles.id asc)`
- Output: primary evidence list + secondary evidence list

### Response shape (5.6)
- `primary_evidence: [...]` — the main answer
- `secondary_evidence: [...]` — supporting context for the other intent
- Single-intent queries: secondary stays empty, kiosk renders normally

---

## Logging (Story 5.7 + 6A.3 + 6A.5)

Compound-specific fields needed on `query_logs` (likely additions in Sprint 4 6A.3):

| Field | Type | Source |
|-------|------|--------|
| `compound_triggered` | INTEGER (bool) | 5.1 |
| `compound_intent_1`, `compound_intent_2` | TEXT | 5.1 |
| `compound_confidence_1`, `compound_confidence_2` | REAL | 5.1 |
| `path_1_top_k_ids`, `path_2_top_k_ids` | TEXT (JSON, cap 5) | 5.3 |
| `merge_strategy` | TEXT | 5.4 (e.g., `"safety_priority_dedup"`) |
| `primary_evidence_ids`, `secondary_evidence_ids` | TEXT (JSON) | 5.4 |

> 🔍 Inferred: Whether to extend `query_logs` with these columns or create a sibling `compound_query_logs` table is an open decision for Sprint 4.

---

## Evaluation (Story 5.8)

3–5 compound scenarios with expected primary + secondary evidence. Examples likely include:
- "high fever + nearest doctor" (medical + location)
- "lost child + safety procedures" (lost_person + safety)
- "where is food + when do meals start" (location + hours, same-topic compound)
- Edge case: ambiguous compound that should trigger clarification instead

Comparison: single-path vs multi-path on the same scenarios. Confirm deterministic ranking for fixed `(kb_version, query)`.

---

## Open decisions for Sprint 4

- How to log compound — extend `query_logs` columns vs sibling table
- Threshold for compound trigger (top-2 intent confidence floor)
- Merge strategy concrete rules (safety/medical always primary, or only when scored above secondary?)
- Whether to expose primary/secondary distinction in the kiosk UI or render as one stream

---

## Dependencies

**Depends on:**
- [[30-decisions/slice-0]] — Canonical pipeline (where compound branching slots in)
- [[30-decisions/slice-1]] — Filter precedence (must apply per path)
- [[30-decisions/slice-2]] — Clarification (compound + clarification interaction)
- [[30-decisions/slice-4|Slice 4]] — Hybrid retrieval (reused per path) — **must be working first**

**Affects:**
- [[30-decisions/slice-6a|Slice 6A]] — needs new compound-aware log fields (likely in 6A.3 Sprint 4)

---

## Related notes

- [[20-sprints/sprint-4/_index|Sprint 4]]
- [[30-decisions/goals|Goals — Goal 5]]
- `ai_helper/goal_outlines/goal_5.md` — full goal spec
- `ai_helper/implementation_slices_sequence.md` — slice intent
