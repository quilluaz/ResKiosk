---
title: "Semantic Search — Retrieval & Filtering"
aliases: ["semantic search", "retrieval", "filtering"]
tags: [type/architecture, component/hub, layer/retrieval, status/active]
generated_at: "2026-05-11T07:32:20Z"
generated: true
---

# Semantic Search — Retrieval & Filtering

**File:** `hub/retrieval/search.py`  
**Updated:** Sprint 1 (Stories 1.3, 1.4, 1.5)  
**Status:** Active

---

## Overview

ResKiosk's semantic search pipeline retrieves KB articles using vector embeddings and applies safety-critical filtering rules to ensure only appropriate content reaches residents.

The retrieval system combines:
- **Semantic similarity** — MiniLM embeddings + cosine similarity
- **Hard safety rules** — Enabled=true, published=true (non-bypassable)
- **Filter precedence** — Hard > UI > inferred (deterministic)
- **RLHF bias** — Optional learned ranking adjustment (configurable)

---

## Retrieval pipeline stages

### 1. Query embedding

**Model:** all-MiniLM-L6-v2 (Sentence-Transformers)  
**Dimension:** 384  
**Input:** Normalized English query text

The embedder converts the query into a 384-dimensional vector for cosine similarity comparison against KB article embeddings.

### 2. Hard retrieval rules (Sprint 1, Story 1.3)

**Applied FIRST, before any other filtering logic**

Hard rules are safety-critical and non-negotiable:

1. **Exclude disabled items** — `enabled = 0`
2. **Exclude unpublished items** — `status != 'published'` (or status is NULL and legacy behavior applies)

These rules:
- Cannot be overridden by UI or inferred filters
- Are applied at the SQL query level (before embeddings are even compared)
- Are logged every time they exclude content
- Are tested in `hub/tests/test_hard_retrieval_rules.py` (inferred)

**Rationale:** In a disaster shelter, serving disabled or unpublished content could provide outdated, incorrect, or dangerous information.

See [[20-sprints/sprint-1/decisions#1.3-D4]] for full decision context.

### 3. Candidate retrieval

After hard rules filter the KB:
- Compute cosine similarity between query embedding and all eligible KB article embeddings
- Sort by similarity score (descending)
- Apply top-k limit (typically 5-10 candidates)

### 4. Filter precedence (Sprint 1, Story 1.4)

**Hierarchy: hard > UI > inferred**

Filters are applied in strict precedence order. Later filters cannot override earlier filters.

#### Hard filters (precedence 1)
- `enabled = 1`
- `status = 'published'`

#### UI filters (precedence 2)
- Explicitly selected taxonomy node (e.g., user tapped "Food & Meals" chip)
- Explicitly selected authority/source filter
- Explicitly selected scope filter

If UI filter selects `rk.tax.food`, only KB items assigned to that taxonomy node (or its children) are eligible.

#### Inferred filters (precedence 3)
- Taxonomy nodes inferred from intent classification
- Uses IntentTaxonomyMap to map intent → taxonomy nodes

If intent is "food", system looks up intent_taxonomy_map and automatically filters to mapped taxonomy nodes.

**Key invariant:** Inferred filters cannot widen UI filters. If UI selected "food", inferred cannot expand to "medical + food".

See [[20-sprints/sprint-1/decisions#1.4-D5]] for full decision context.

### 5. RLHF bias adjustment (optional)

If RLHF is enabled (env var `RESKIOSK_RLHF_ENABLED=true`):
- Retrieve per-article bias values from `article_biases` table
- Adjust cosine similarity scores: `final_score = cosine_sim + (alpha * bias)`
- Alpha (weight) is configurable via `RESKIOSK_RLHF_ALPHA` (default 0.10)
- Bias values are learned from `feedback_logs` table (thumbs up/down)
- Bias cache has TTL (default 1800 seconds)

RLHF bias is applied AFTER filtering, not before. It cannot resurrect filtered-out articles.

### 6. Gating (answer_type determination)

Based on top candidate score and intent confidence:

| Scenario | answer_type | Behavior |
|----------|-------------|----------|
| Score ≥ direct_match_threshold | `DIRECT_MATCH` | Return answer immediately |
| Score between clarification_floor and threshold | `NEEDS_CLARIFICATION` | Pause pipeline, show taxonomy chips |
| Score < clarification_floor | `NO_MATCH` | Generic fallback message |

**Thresholds (configurable via env vars):**
- EN direct_match_threshold: 0.60
- EN clarification_floor: 0.40
- Non-EN direct_match_threshold: 0.50
- Non-EN clarification_floor: 0.38

### 7. Filter decision logging (Sprint 1, Story 1.5)

Every retrieval logs:
- `hard_rules_applied` — list of exclusion rules that triggered
- `ui_selected_taxonomy_node_id` — explicitly selected taxonomy node (if any)
- `inferred_taxonomy_node_ids` — JSON array of inferred taxonomy nodes
- `candidate_count_pre_filter` — total KB items before filtering
- `candidate_count_post_filter` — items remaining after all filters
- `widening_triggered` — boolean, did system need to relax filters?
- `widening_step` — none | remove_inferred | broaden_ui | safe_fallback
- `query_log_id` — link to parent query log

See [[10-architecture/data-models#QueryLog]] for full schema.

---

## Retrieval API

```python
from hub.retrieval import search

result = search.retrieve(
    db=db_session,
    query_text="normalized English query",
    is_retry=False,
    selected_category=None,  # UI filter (taxonomy node ID or legacy category)
    exclude_source_ids=None,  # Exclude these KB article IDs
    query_language="en"
)

# result dict structure:
{
    "answer_text": str,
    "answer_type": "DIRECT_MATCH" | "NEEDS_CLARIFICATION" | "NO_MATCH",
    "confidence": float,  # Cosine similarity score
    "source_id": int | None,  # Matched KB article ID
    "categories": list | None,  # Clarification chip options (if NEEDS_CLARIFICATION)
    "article_data": dict | None,  # Full KB article data
    "intent": str,
    "intent_confidence": float
}
```

---

## Filter precedence examples

### Example 1: Hard rule takes precedence

**Scenario:** KB article has `enabled=0` and matches query with high similarity

**Result:** Article is excluded by hard rule, never reaches candidate pool

**Log:** `hard_rules_applied: ["enabled=false"]`

### Example 2: UI filter takes precedence over inferred

**Scenario:**
- User explicitly selected taxonomy node `rk.tax.food`
- Intent classifier detects "medical" intent with high confidence
- Intent → taxonomy map would infer `rk.tax.medical`

**Result:** Only food-related articles are eligible. Medical articles are excluded because UI filter (precedence 2) takes precedence over inferred filter (precedence 3).

**Log:**
- `ui_selected_taxonomy_node_id: "rk.tax.food"`
- `inferred_taxonomy_node_ids: ["rk.tax.medical"]`
- `widening_step: "none"` (no widening needed)

### Example 3: Inferred filter with no UI filter

**Scenario:**
- No explicit UI selection
- Intent classifier detects "food" intent
- Intent → taxonomy map infers `rk.tax.food`

**Result:** Only food-related articles are eligible

**Log:**
- `ui_selected_taxonomy_node_id: null`
- `inferred_taxonomy_node_ids: ["rk.tax.food"]`

---

## Hard rule enforcement tests

> 🔍 Inferred: Sprint 1 included test coverage for hard retrieval rules

Expected test file: `hub/tests/test_hard_retrieval_rules.py` or similar

Test cases:
- Disabled article (`enabled=0`) never appears in retrieval results
- Unpublished article (`status != 'published'`) never appears in retrieval results
- Published, enabled article with low similarity still appears in candidate pool (not excluded by hard rules)
- Hard rule exclusions are logged

---

## Related notes

- [[10-architecture/voice-pipeline]] — Pipeline stage that calls retrieval
- [[10-architecture/data-models]] — Taxonomy, QueryLog, KBArticle schema
- [[10-architecture/intent-system]] — Intent classification feeding inferred filters
- [[20-sprints/sprint-1/user-stories#1.3]] — Story 1.3: Enforce hard retrieval rules
- [[20-sprints/sprint-1/user-stories#1.4]] — Story 1.4: Apply UI and inferred intent filters with precedence
- [[20-sprints/sprint-1/user-stories#1.5]] — Story 1.5: Log filter decisions and candidate counts
- [[20-sprints/sprint-1/decisions#1.3-D4]] — Decision: Hard retrieval rules as first-class safety gate
- [[20-sprints/sprint-1/decisions#1.4-D5]] — Decision: Filter precedence: hard > UI > inferred

---

## Evidence

| Commit | Date | Author | Message |
|--------|------|--------|---------|
| ded5b36 | 2026-05-01 | keithruezyl1 | slice 1 user story 2 delivered |
| 70256b3 | 2026-05-03 | Isaac | Completed Person 2: Story 2 - Add pipeline stage logging skeleton and Story 5 - Log filter decisions and candidate counts |
