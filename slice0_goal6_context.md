# Slice 0 — Goal 6: Clarification Pause Response — Running Context

## User Story
> As the hub system, I want to return a paused clarification response before rewrite or retrieval so that ambiguous queries are not answered prematurely.

## Dependencies
| Dependency | Status | Notes |
|-----------|--------|-------|
| Person 1 — Pipeline orchestration | ✅ Already delivered | `pipeline.py` with `clarification_gate` consumed as-is |
| Person 2 — Logging clarification pause state | ⏳ Hook prepared | Structured log line + `ClarificationContext` ready for Person 2 |

## Subtasks
- [x] Define `ClarificationContext` Pydantic model with all resume fields
- [x] Add `clarification_context` optional field to `QueryResponse`
- [x] Add `pipeline_status` field to `PipelineResult` ("completed" / "paused")
- [x] Set `pipeline_status = "paused"` at clarification gate in `pipeline.py`
- [x] Build `ClarificationContext` in `routes_query.py` on pause + early-return
- [x] Early-return skips LLM formatting and outbound translation
- [x] Query log still written for paused queries (Person 2 can join)
- [x] Logging hook prepared with structured log line for Person 2
- [x] Add 3 pipeline_status tests to `test_pipeline_order.py`
- [x] Create `test_clarification_response.py` with 7 response contract tests
- [x] Run all tests — 17/17 pass, zero regressions

## Decisions Made
1. **Extend `QueryResponse` (not a new model)** — backward-compatible; kiosks already consume `QueryResponse`. Adding optional fields doesn't break existing clients.
2. **`ClarificationContext` as nested Pydantic model** — typed, serializable, carries all resume fields (`original_query`, `normalized_text`, `detected_intent`, `intent_confidence`, `suggested_categories`, `kb_version`, `session_id`, `pipeline_status`).
3. **No opaque resume token** — local-network offline system; readable context is simpler and debuggable. Existing `is_retry` + `selected_category` + `session_id` pattern remains the resume mechanism.
4. **Early-return on pause** — skip LLM formatting and outbound translation (wasted compute for a "pick a category" response).
5. **`pipeline_status` field on `PipelineResult`** — makes paused state a first-class concept, not inferred from `answer_type`.

## Files Changed
| File | Change |
|------|--------|
| `hub/models/api_models.py` | Added `ClarificationContext` model; added `clarification_context` field to `QueryResponse` |
| `hub/retrieval/pipeline.py` | Added `pipeline_status` to `PipelineResult`; set "paused" at clarification gate |
| `hub/api/routes_query.py` | Build `ClarificationContext` on pause; early-return; logging hook for Person 2 |
| `hub/tests/test_pipeline_order.py` | Added 3 new tests for pipeline_status |
| `hub/tests/test_clarification_response.py` | NEW — 7 tests for response contract |

## What Is Completed
All subtasks are complete. User story is fully delivered.

## What Is Remaining
Nothing — all acceptance criteria met.

---

## Story Implementation Summary

**What was done:**
Delivered a structured clarification pause response for the hub pipeline. When the pipeline detects an ambiguous query (intent = "unclear", retrieval score below clarification floor), it now:

1. Sets `pipeline_status = "paused"` on the `PipelineResult`
2. Skips rewrite and second retrieval (unchanged — Person 1's pipeline orchestration)
3. The route handler detects the paused state and builds a typed `ClarificationContext` with all resume fields
4. Returns immediately — no LLM formatting, no outbound translation (saves compute)
5. Still writes the query log for audit (Person 2 can join on it)
6. Emits a structured log line as Person 2's logging hook

**Acceptance Criteria Verification:**

| AC | Status | Evidence |
|----|--------|----------|
| Hub can return structured needs-clarification response | ✅ | `ClarificationContext` model + `clarification_context` field on `QueryResponse` |
| Rewrite is skipped when clarification required | ✅ | Pipeline stops at `clarification_gate`; `test_clarification_stops_pipeline_before_rewrite`, `test_clarification_sets_pipeline_status_paused` |
| Retrieval is skipped when clarification required | ✅ | No `retrieve_retry` in stage_log; mock_retrieve called once |
| Response includes enough context to resume | ✅ | `ClarificationContext` carries `original_query`, `normalized_text`, `detected_intent`, `intent_confidence`, `suggested_categories`, `kb_version`, `session_id` |
| Existing non-clarification queries unaffected | ✅ | `test_normal_query_sets_pipeline_status_completed`, `test_non_clarification_has_no_context`, all 7 original pipeline tests still pass |

**Test Results:** 17/17 pass (10 pipeline + 7 response contract), zero regressions.
