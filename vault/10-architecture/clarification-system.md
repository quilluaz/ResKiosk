---
title: "Clarification System — Pause, Chip Selection & Resume"
aliases: ["clarification system", "clarification UX"]
tags: [type/architecture, component/hub, component/kiosk, layer/retrieval, status/active]
generated_at: "2026-05-11T07:53:18Z"
generated: true
---

# Clarification System — Pause, Chip Selection & Resume

**Files:** `hub/retrieval/pipeline.py`, `hub/retrieval/search.py`, `hub/api/routes_query.py`  
**Delivered:** Sprint 1 (pause state), Sprint 2 (chip UI, taxonomy-backed selection, full UX)  
**Related stories:** 0.3, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6  
**Status:** Active

---

## Overview

The clarification system is triggered when a user's query is ambiguous — the intent classifier detects a plausible intent but semantic retrieval can't confidently pick a single KB article. Rather than returning a low-confidence answer or a generic "I don't know," the hub pauses the pipeline and returns a structured response asking the user to choose a topic category.

This is a **safety and accuracy feature**: it prevents confident-sounding wrong answers when the system isn't sure what the user means.

---

## When Clarification Triggers

The pipeline enters the clarification path when `search.retrieve()` returns `answer_type == "NEEDS_CLARIFICATION"`. This happens when:

1. The top similarity score is **above the clarification floor** (EN: 0.40, non-EN: 0.38)
2. But **below the direct match threshold** (EN: 0.60, non-EN: 0.50)
3. AND the intent is not a short-circuit intent (greeting, identity, small_talk, goodbye)

The intent confidence gating adds another condition:
- If intent confidence ≥ `INTENT_ACTION_THRESHOLD` (0.35), clarification fires when the above score range is met
- Low-confidence intents may still fire clarification if score is in range

---

## Pipeline Flow

```
query text (EN)
    │
    ▼
[Stage 1] normalize_query()
    │
    ▼
[Stage 2] IntentClassifier.classify_top2()
    │  → intent, intent_confidence
    ▼
[Stage 3] search.retrieve()
    │  → answer_type = NEEDS_CLARIFICATION
    ▼
[Stage 4] clarification_gate
    │  pipeline_status = "paused"
    │  STOP — rewrite and retry do NOT run
    ▼
QueryResponse(
  answer_type = "NEEDS_CLARIFICATION",
  clarification_context = ClarificationContext(...),
  clarification_options = [TaxonomyOption, ...],
  clarification_categories = ["Food & Water", ...]  # legacy string list
)
    │
    ▼
Kiosk receives → displays chip buttons → user taps one
    │
    ▼
POST /query (second request)
  selected_taxonomy_node_id = "rk.tax.basic_needs_daily_living.food_nutrition"
  selected_category = "Food & Water"
  session_id = <same session>
    │
    ▼
Pipeline runs again, this time with selected category/node → DIRECT_MATCH
```

**Critical invariant**: When `clarification_gate` fires, **Stage 5 (rewrite) and Stage 6 (retrieve_retry) are skipped**. This is enforced in `QueryPipeline.run()` with an early `return result`.

---

## Taxonomy-Backed Chip Selection

Chip selection follows a **deterministic policy** defined in `hub/taxonomy/taxonomy_v1.json` under the `clarification_chip_defaults` key.

### Algorithm (`search._deterministic_clarification_node_ids`)

1. Load the policy file (cached in `_taxonomy_policy_cache`)
2. Start with the **default chip set** (max 3 nodes, e.g., Food, Medical, Registration)
3. Check for **conditional replacements**: if the inferred taxonomy nodes, top KB article assignments, or intent hint indicate a specific node strongly, one default chip is replaced
4. Intent → conditional hint mappings:
   - `safety` → `rk.tax.safety_emergencies.emergency_procedures`
   - `facilities` → `rk.tax.basic_needs_daily_living.facilities_use`
   - `sleeping` → `rk.tax.basic_needs_daily_living.sleeping_rest_areas`
   - `location` → `rk.tax.location_navigation.in_shelter_locations`
5. De-duplicate, enforce max 3 chips

### Result Shape

```json
"clarification_options": [
  { "id": "rk.tax.basic_needs_daily_living.food_nutrition", "label": "Food & Water" },
  { "id": "rk.tax.health_medical.medical_services", "label": "Medical Help" },
  { "id": "rk.tax.shelter_registration.registration_intake", "label": "Registration" }
]
```

The kiosk renders these as tappable chip buttons in the `MainKioskScreen` Composable.

---

## Resume Flow (Second Request)

When the user taps a chip, the kiosk sends a new `QueryRequest` with:
- `selected_taxonomy_node_id` — the taxonomy node ID from the chip
- `selected_category` — the human-readable label (legacy fallback)
- `session_id` — same session UUID as the clarification request
- `is_retry: false` — this is a fresh query, not a retry

On the hub, `search.retrieve()` now has a taxonomy node ID to use as a hard filter, which dramatically narrows the candidate set and typically produces a `DIRECT_MATCH`.

---

## ClarificationContext Model

The `ClarificationContext` Pydantic model is returned inside `QueryResponse` only when `answer_type == "NEEDS_CLARIFICATION"`:

| Field | Description |
|-------|-------------|
| `original_query` | Raw query text before normalization |
| `normalized_text` | Post-normalization text |
| `detected_intent` | Intent classifier result |
| `intent_confidence` | Intent classifier confidence score |
| `suggested_categories` | Category chip labels (string list) |
| `kb_version` | KB version at time of pause |
| `session_id` | Session UUID for resumption |
| `pipeline_status` | Always `"paused"` |

---

## Session Management

Session history is stored in-memory in `routes_query.py`:

```python
session_history: dict[str, list[dict]] = {}
```

- Keys: `session_id` strings
- Values: lists of `{"user": ..., "assistant": ...}` dicts
- Sessions are cleared via `DELETE /query/session/{session_id}` (kiosk calls this on new conversations)
- Sessions are **not persisted** — hub restart clears all sessions

`ClarificationResolution` DB table logs the gold label when a user selects a chip (for future ML training data).

---

## Kiosk-Side UX

When `answer_type == "NEEDS_CLARIFICATION"` is received:

1. **Chat bubble** displays a clarification prompt ("Did you mean...?")
2. **Chip row** renders the `clarification_options` as tappable buttons
3. User taps → triggers a new query submission with the selected node ID
4. Kiosk UI transitions back to "Processing" state during the second request

Implemented in `kiosk/.../ui/MainKioskScreen.kt` and managed by `KioskViewModel.kt`.

---

## Observability

Each pipeline run logs:

```
[Pipeline] clarification_gate: clarification_triggered=True pipeline_status=paused categories=[...]
```

or:

```
[Pipeline] clarification_gate: clarification_triggered=False
```

`ClarificationResolution` rows accumulate gold-label training data over time. This table is available for future intent classifier fine-tuning.

---

## Related

- [[10-architecture/voice-pipeline]] — Full end-to-end query flow
- [[10-architecture/intent-system]] — Intent classifier (prototype-based cosine)
- [[10-architecture/semantic-search]] — Retrieval pipeline (thresholds, filtering)
- [[30-decisions/slice-2]] — Slice 2 (Clarify-first UX) decisions
- [[00-pre-sprint-baseline/api-surface]] — `/query` endpoint contract
