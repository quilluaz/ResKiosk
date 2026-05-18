---
title: "Slice 6A — Observability & Trust"
aliases: ["slice 6a", "observability", "MVP metrics"]
tags: [type/decision, slice/6a, goal/10, status/active]
sprint: 3
generated_at: "2026-05-11T14:42:01Z"
generated: true
---

# Slice 6A — Observability & Trust

**Related goals:** Goal 10 (MVP metrics + logging)
**Sprint span:** Sprint 3 (6A.1, 6A.8) → Sprint 4 (6A.2, 6A.3, 6A.8, 6A.9) → Sprint 5 (6A.4, 6A.5, 6A.6, 6A.7)
**Status:** 🔄 Active (Sprint 3 portion starting)
**Work items:** 9
**Story points:** 40 total — 11 in Sprint 3, 21 in Sprint 4, 8 in Sprint 5

---

## Overview

Slice 6A makes ResKiosk's retrieval and pipeline behavior **measurable**. Sprint 1 added unstructured text logs at every pipeline stage (`[Filter]`-tagged lines, `INFO` stage events). Slice 6A promotes those text logs to **structured columns** on `query_logs` so we can compute KPIs per KB version and per intent, debug retrieval changes while they're being built, and prove the canonical pipeline is being respected.

The sprint plan pulls Stories **6A.1 and 6A.8 forward from Sprint 4 into Sprint 3** because Slice 4's hybrid retrieval work needs structured log columns to write to as it ships. Without those columns, retrieval changes are observable only in text logs, defeating the whole point of measuring quality during the change.

---

## Goal served

### Goal 10 — MVP metrics + logging

Track:
- **Grounding** — does the response actually use the retrieved evidence?
- **Hallucination proxy** — unsupported spans vs context
- **Evidence match** — citation / source_id stability vs top-1 raw cosine
- **Latency** — STT + retrieve + TTS + per-stage breakdown

Success: metrics computable per KB version. See [[30-decisions/goals|Goals index]] for the full Goal 10 framing.

---

## Work items (full slice across sprints)

### Sprint 3 (this sprint)

| ID | Work Item | Points | Status |
|----|-----------|--------|--------|
| 6A.1 | Complete structured query log schema | 8 | ✅ Done (commit `d129eb6`, 2026-05-11) |
| 6A.8 | Add failure and fallback outcome logging | 3 | 🔄 Active |

### Sprint 4 (upcoming)

| ID | Work Item | Points | Sprint |
|----|-----------|--------|--------|
| 6A.2 | Add latency breakdown logging | 5 | Sprint 4 |
| 6A.3 | Capture final evidence list and stability fields | 5 | Sprint 4 |
| 6A.9 | Format hub query logs for readable operational observability | 3 | Sprint 4 |

### Sprint 5 (upcoming)

| ID | Work Item | Points | Sprint |
|----|-----------|--------|--------|
| 6A.4 | Implement MVP metrics export workflow | 5 | Sprint 5 |
| 6A.5 | Create grounding proxy review fields | 3 | Sprint 5 |
| 6A.6 | Create fixed evaluation query set | 3 | Sprint 5 |
| 6A.7 | Generate basic KPI report by KB version | 5 | Sprint 5 |

---

## Key design decisions

### 6A-D1: Structured columns, not JSON blobs in a single `payload` field

**Decision:** Add explicit, typed columns to `query_logs` (or a sibling table) for each new field — `intent_label`, `intent_confidence`, `lexical_top_k_*`, `fusion_*`, etc. Do not collapse everything into a single `metadata JSON` column.

**Why:**
- Structured columns let SQL queries do `WHERE intent_label = 'food' AND fallback_reason IS NOT NULL` directly, without JSON parsing per row.
- Top-k arrays (IDs, scores, ranks) stay as JSON arrays in TEXT because they are vector-valued — but only for that specific use case.
- Easier to add column-level NOT NULL / type constraints in future sprints.

**Trade-off:** More columns means more schema migrations. Acceptable given we control the deployment.

---

### 6A-D2: Top-5 cap on retrieval-path arrays

See [[20-sprints/sprint-3/decisions|3-D2]] for full reasoning. Each `lexical_top_k_*`, `vector_top_k_*`, `fusion_top_k_*` array is capped at 5 elements as JSON-in-TEXT.

---

### 6A-D3: All new columns are **nullable**

**Decision:** Every new column added by 6A.1 is nullable.

**Why:**
- Existing rows in `query_logs` cannot be backfilled — the data wasn't captured.
- Stages that don't run for a given query (e.g., clarification didn't trigger; hybrid retrieval not yet wired) leave their columns NULL rather than writing meaningless defaults.
- Distinguish "didn't happen" (NULL) from "happened with empty result" (`[]`).

**Consequence:** Aggregation queries must use `COUNT(intent_label)` rather than `COUNT(*)` and explicitly handle NULL semantics.

---

### 6A-D4: Hybrid + fallback columns added in 6A.1 even though their writers ship later

**Decision:** All 15 new columns in 6A.1 land in one migration on day 1, including `lexical_*`, `vector_*`, `fusion_*`, `fallback_reason`, and `failed_stage`. The columns sit nullable until Slice 4 (stories 4.2, 4.3, 4.5) and Story 6A.8 populate them.

**Why:** Schema is the interface contract for Person 3, Person 4, and Story 4.5. Adding columns piecemeal would force multiple migrations and risk Slice 4 stories landing against an absent target.

See [[20-sprints/sprint-3/decisions|3-D1]] for the sequencing call.

---

### 6A-D6: Clarification logging deduplicated against Sprint 2's canonical fields

**Decision:** Story 6A.1 originally planned 17 columns including `clarification_categories_offered` and `clarification_node_id_selected`. After the Sprint 2 merge, these were dropped in favor of Sprint 2's existing fields:
- `clarification_options_shown` (Sprint 2 — richer `{id, label}` shape) supersedes `clarification_categories_offered`
- `ui_selected_taxonomy_node_id` (existing) + `ClarificationResolution.selected_option_id` (Sprint 2 table) supersede `clarification_node_id_selected`

**Final column count: 15** (not 17).

**Why:** Sprint 2 already established clarification logging as part of Slice 2 Story 2.6. Duplicating the schema would have created two parallel canonical sources and required reconciliation in every downstream query. Sprint 2 wins by recency and by having strictly richer payload shape.

**Where to look for clarification data in `query_logs`:**
- What was offered → `clarification_options_shown` (Sprint 2)
- What was selected pre-query → `ui_selected_taxonomy_node_id` (existing)
- What was selected via resolution → `ClarificationResolution` table joined by `session_id`/`query_log_id` (Sprint 2)

---

### 6A-D5: Failure reason codes are **a fixed, documented enum**

**Decision:** `fallback_reason` accepts only one of:
- `no_results` — retrieval returned zero candidates after filtering
- `low_confidence` — top score below clarification floor
- `validation_blocked` — publish-blocked KB version, retrieval served stale or none
- `retrieval_error` — exception during retrieval
- `rewrite_error` — LLM rewriter failed

`failed_stage` accepts pipeline stage names: `normalize`, `intent`, `clarification`, `rewrite`, `retrieval`, `fusion`, `format`.

**Why:** Enables aggregation queries by reason without per-row string parsing. The enum is small enough to memorize and grep for.

**Consequence:** Any new failure mode must extend this enum, not invent new codes ad-hoc. Adding `image_retrieval_error` in Slice 7C, for example, would be a documented enum extension.

---

## query_logs schema additions (Story 6A.1 — ✅ shipped)

From [`slice6a_story1_running_context.md`](../../slice6a_story1_running_context.md). Final 15 columns after dedup (see 6A-D6):

| Column | Type | Populated by | Status |
|--------|------|--------------|--------|
| `intent_label` | TEXT | `routes_query.py` in 6A.1 | ✅ Wired |
| `intent_confidence` | REAL | `routes_query.py` in 6A.1 | ✅ Wired |
| `lexical_top_k_ids` | TEXT (JSON) | Story 4.5 | ⏳ Schema only |
| `lexical_top_k_scores` | TEXT (JSON) | Story 4.5 | ⏳ Schema only |
| `lexical_top_k_ranks` | TEXT (JSON) | Story 4.5 | ⏳ Schema only |
| `lexical_latency_ms` | REAL | Story 4.5 | ⏳ Schema only |
| `vector_top_k_ids` | TEXT (JSON) | Story 4.5 | ⏳ Schema only |
| `vector_top_k_scores` | TEXT (JSON) | Story 4.5 | ⏳ Schema only |
| `vector_top_k_ranks` | TEXT (JSON) | Story 4.5 | ⏳ Schema only |
| `fusion_strategy` | TEXT | Story 4.5 | ⏳ Schema only |
| `fusion_top_k_ids` | TEXT (JSON) | Story 4.5 | ⏳ Schema only |
| `fusion_top_k_scores` | TEXT (JSON) | Story 4.5 | ⏳ Schema only |
| `fusion_top_k_ranks` | TEXT (JSON) | Story 4.5 | ⏳ Schema only |
| `fallback_reason` | TEXT | Story 6A.8 | ⏳ Schema only |
| `failed_stage` | TEXT | Story 6A.8 | ⏳ Schema only |

**Test coverage:** `hub/tests/test_query_log_schema.py` — 7 tests covering column presence, nullability, types, instantiation with new fields, backward-compatible legacy instantiation, and migration coverage. All pass; 38 pre-existing tests unaffected.

---

## What's deferred to Sprint 4 / Sprint 5

- **6A.2 (latency breakdown):** per-stage timing — Sprint 4.
- **6A.3 (final evidence list + stability fields):** captures the final top-k chosen *after* fusion + bias + formatting, separate from the per-path top-k captured in 6A.1.
- **6A.9 (readable hub logs):** the operator-facing log stream gets stable IDs, stage labels, and bounded payloads. Distinct from the structured column work — this is about live `INFO` logs.
- **6A.4–6A.7 (metrics export, grounding proxy, eval set, KPI report):** the reporting layer built on top of all the columns. Sprint 5.

---

## Dependencies

**Depends on:**
- [[30-decisions/slice-0]] — Canonical pipeline (provides the stage events to log)
- [[30-decisions/slice-1]] — Filter logging (already adds `[Filter]` text — 6A promotes to structured)
- [[30-decisions/slice-2]] — Clarification logging (Sprint 2 added text logs — 6A.1 promotes to columns)

**Blocks:**
- [[30-decisions/slice-4|Slice 4]] — Stories 4.5 and 4.3 contribution logs need 6A.1's columns
- Future quality reporting (Sprint 5+) — needs the columns to compute over

---

## Related notes

- [[20-sprints/sprint-3/_index|Sprint 3 index]]
- [[20-sprints/sprint-3/user-stories|6A.1 + 6A.8 story detail]]
- [[20-sprints/sprint-3/decisions|3-D1 (sequencing) + 3-D2 (top-5 cap)]]
- `slice6a_story1_running_context.md` — Person 5's working source of truth (in repo root)
- `ai_helper/goal_outlines/goal_10.md` — full Goal 10 specification
