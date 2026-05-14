# Slice 4 — Story 7: Tune feedback-adjusted ranking as a separate layer

## Story

As the retrieval system, I want feedback-adjusted ranking to remain a separate bounded layer so that feedback can influence ranking without overpowering retrieval evidence.

## Acceptance Criteria

- Feedback bias remains enabled/disabled by configuration.
- Bias is applied only after baseline retrieval candidates are available.
- Bias contribution is capped or bounded.
- Bias does not bypass hard filters or validation status.
- Logs capture baseline score, bias value, and final score where bias applies.
- Ranking remains deterministic for a fixed KB version/config/query and fixed bias state.

---

## Status: DONE ✓

All ACs implemented. No linter errors. AC1 and AC2 were already satisfied; ACs 3–6 required changes.

---

## Subtasks

- Subtask 1 — Add `RLHF_BIAS_MAX_DELTA` explicit cap constant
- Subtask 2 — Add quarantine guard cache and helper
- Subtask 3 — Refactor bias application block (cap, guard, bias_detail, deterministic sort)
- Subtask 4 — Add bias log columns to `QueryLog` ORM and migration
- Subtask 5 — Write bias log fields in both query log paths

---

## What was built

### Subtask 1 — Explicit cap constant
**File:** `hub/retrieval/search.py`

Added `RLHF_BIAS_MAX_DELTA` (default `0.15`, env-configurable as `RESKIOSK_RLHF_MAX_DELTA`). This makes the bound on bias contribution explicit and independently tunable from `RLHF_ALPHA`. Previously, the only bound was a clamp to `[0, 1]` after applying `alpha * b` — there was no cap on the *delta* itself.

### Subtask 2 — Quarantine guard cache
**File:** `hub/retrieval/search.py`

Added `_get_quarantined_item_ids(db)` with a TTL cache matching `RLHF_BIAS_TTL_SECS`. Queries `kb_item_validation_status` for items with `status IN ('quarantined', 'rejected')`. Returns an empty set when the table has no rows (safe for deployments without validation data). Called at the start of the bias block when `RLHF_ENABLED`.

### Subtask 3 — Bias application block refactor
**File:** `hub/retrieval/search.py`

Restructured the bias block from a simple loop to a documented, bounded layer:

- `article_ids` extracted before the bias block (needed for both bias and deterministic sort)
- `raw_top1_id` computed from `raw_scores` for `bias_top1_changed` comparison
- **AC3**: delta capped as `max(-MAX_DELTA, min(MAX_DELTA, RLHF_ALPHA * b))` before adding to baseline
- **AC4**: `b` set to `0.0` for any article in `quarantined` set — bias cannot rescue a blocked item
- **AC5**: `_bias_detail_map` built per-item: `{id, baseline, bias_value, delta, final}` for items with non-zero bias
- **AC6**: deterministic sort replaced `np.argsort`: `sorted(enumerate(scores), key=lambda x: (-x[1], article_ids[x[0]]))` — tie-break is `article_id asc`
- `bias_detail` trimmed to top-k IDs after sort (bounded log size)
- All 5 return dicts updated to carry `bias_enabled`, `bias_applied_count`, `bias_top1_changed`, `bias_detail`

### Subtask 4 — Schema + migration
**Files:** `hub/db/schema.py`, `hub/db/migrate_schema.py`

Added 4 columns to `QueryLog`:

| Column | Type | Purpose |
|---|---|---|
| `bias_enabled` | Boolean | Was the bias layer active for this request |
| `bias_applied_count` | Integer | How many candidates had non-zero bias applied |
| `bias_top1_changed` | Boolean | Did bias change the top-1 result vs raw cosine |
| `bias_detail` | Text | JSON array of per-item detail for top-k candidates |

Idempotent `ALTER TABLE` entries added to the `query_logs` migration dict.

### Subtask 5 — Write bias fields in log paths
**File:** `hub/api/routes_query.py`

`bias_enabled`, `bias_applied_count`, `bias_top1_changed`, and `bias_detail` (JSON) written in both the pause path log and the normal path log, sourced from `result.get(...)`.

---

## Key decisions

- **`RLHF_BIAS_MAX_DELTA` is independent from `RLHF_ALPHA`**: alpha scales the raw bias value; max_delta caps the score movement. Both are individually tunable via env vars. This gives operators two levers: sensitivity (alpha) and ceiling (max_delta).
- **Quarantine guard uses the same TTL as the bias cache**: they share `RLHF_BIAS_TTL_SECS`. This means both reflect the same operational snapshot — avoids a scenario where bias is stale but the quarantine list is fresh (or vice versa).
- **Bias detail trimmed to top-k only**: the full corpus can be thousands of articles. Logging per-item detail for the entire corpus would be unbounded. Trimming to the top-k (5) IDs after sort keeps logs bounded and meaningful.
- **`bias_top1_changed` is computed against raw cosine top-1, not hybrid top-1**: this story operates on the current vector-only retrieval stack. When hybrid retrieval is enabled (Goal 4), the "baseline" will be the hybrid-fused score, not raw cosine — that comparison should be updated then.
- **AC6 sort is deterministic by design**: `article_id` is an integer PK that is stable within a KB version. Tie-breaking by `id asc` means equal-score articles always rank in the same order for the same KB state.

---

## AC trace

| AC | How it's met |
|---|---|
| Enabled/disabled by config | `RLHF_ENABLED` env flag — unchanged, already existed |
| Applied only after baseline candidates available | Bias block runs after `scores` (cosine similarities) are computed — unchanged |
| Contribution capped or bounded | `RLHF_BIAS_MAX_DELTA` cap on delta + [0,1] clamp on final score |
| Does not bypass hard filters or validation status | Quarantine guard: `b = 0.0` for quarantined/rejected items |
| Logs capture baseline, bias value, final score | `query_logs.bias_detail` JSON per top-k item |
| Deterministic for fixed state | `(-score, article_id asc)` sort replaces `np.argsort` |

---

## Open / follow-on

- When hybrid retrieval (Goal 4) is integrated, `raw_top1_id` / `bias_top1_changed` should compare against the hybrid-fused baseline, not raw cosine.
- `bias_detail` is `NULL` when bias is disabled (no loop runs). Consumers should treat NULL as "bias not applied" rather than "no data."
- The quarantine guard defaults to an empty set when `kb_item_validation_status` is empty (fresh deploys with no validation runs). No behavior change on existing deployments.
- A small evaluation workflow (eval set + bias flip rate metric) is specified in Goal 9 DoD but not implemented here — that is an offline/batch concern and belongs to a separate observability story.
