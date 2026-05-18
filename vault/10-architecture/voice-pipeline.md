---
title: "Voice Pipeline — End-to-end Query Flow"
aliases: ["voice pipeline", "query pipeline", "canonical pipeline"]
tags: [type/architecture, component/hub, layer/pipeline, status/active]
generated_at: "2026-05-11T07:32:20Z"
generated: true
---

# Voice Pipeline — End-to-end Query Flow

**File:** `hub/retrieval/pipeline.py`  
**Established:** Sprint 1 (Story 0.1)  
**Status:** Active

---

## Overview

ResKiosk's canonical query pipeline is the ONLY path through which all voice queries flow. It enforces a strict stage order, enables consistent logging, and provides controlled pause points for clarification.

All queries — regardless of language, intent, or complexity — follow this single pipeline.

---

## Pipeline stages (enforced order)

### 1. Normalize
**Module:** `hub/retrieval/normalizer.py`  
**Purpose:** Lowercase, synonym expansion, domain corrections

Normalization prepares the query for intent classification and retrieval:
- Lowercase conversion
- Synonym expansion (e.g., "bathroom" → "restroom toilet bathroom")
- Domain-specific corrections (e.g., "doc" → "doctor")
- Language-aware processing

**Stage constant:** `STAGE_NORMALIZE`

### 2. Intent classification
**Module:** `hub/retrieval/intent.py`  
**Purpose:** Detect user intent with confidence score

Uses prototype-based intent classification with MiniLM embeddings:
- 23+ intent categories (food, medical, registration, etc.)
- Returns top intent and confidence score
- Enables intent-to-taxonomy mapping for filtering
- Logged separately from retrieval internals

**Stage constant:** `STAGE_INTENT`

### 3. Retrieve (first pass)
**Module:** `hub/retrieval/search.py`  
**Purpose:** Semantic search + filtering

Retrieves candidate KB articles using:
- MiniLM semantic embeddings (all-MiniLM-L6-v2)
- Cosine similarity ranking
- Hard retrieval rules (enabled=true, published=true)
- Filter precedence: hard > UI > inferred
- Optional RLHF bias adjustment

Returns:
- `answer_type` — DIRECT_MATCH | NEEDS_CLARIFICATION | NO_MATCH
- `source_id` — matched KB article ID
- `confidence` — retrieval score
- `categories` — clarification options (if needed)

**Stage constant:** `STAGE_RETRIEVE`

### 4. Clarification gate
**Purpose:** Pause pipeline if clarification needed

If `answer_type == "NEEDS_CLARIFICATION"`:
- Pipeline stops HERE
- Returns clarification options (taxonomy-backed chips)
- Does NOT proceed to rewrite or retrieval retry
- Sets `pipeline_status = "paused"`

Non-clarification queries pass through unchanged.

**Stage constant:** `STAGE_CLARIFICATION_GATE`  
**Established:** Sprint 1 (Story 0.3)

### 5. Rewrite (optional)
**Module:** `hub/retrieval/rewriter.py`  
**Purpose:** LLM-based query rewrite for noisy transcripts

Triggers when:
- Low retrieval confidence
- Unclear intent
- STT artifacts detected

Uses Llama 3.2:3b (local Ollama) to rephrase the query.

Only runs if clarification was NOT triggered.

**Stage constant:** `STAGE_REWRITE`

### 6. Retrieve (retry after rewrite)
**Purpose:** Second retrieval pass with rewritten query

If rewrite produced a different query:
- Run retrieval again with the rewritten text
- Use the retry result if successful
- Fall back to original result if retry fails

**Stage constant:** `STAGE_RETRIEVE_RETRY`

---

## Pipeline orchestrator API

```python
from hub.retrieval.pipeline import QueryPipeline

pipeline = QueryPipeline()
result = pipeline.run(
    db=db_session,
    text_en="normalized English query text",
    is_retry=False,
    selected_category=None,  # UI filter (taxonomy node ID)
    exclude_source_ids=None,  # Exclude these KB articles
    query_language="en"
)

# result.pipeline_status: "completed" | "paused"
# result.stage_log: ["normalize", "intent", "retrieve", ...]
# result.retrieve_result: {answer_type, source_id, confidence, ...}
# result.rewrite_happened: bool
# result.rewritten_text: str | None
```

---

## Stage logging

Every pipeline execution logs:
- Request ID (for tracing)
- Timestamp
- `normalized_text` — normalized query
- `intent` + `intent_confidence`
- `answer_type` — DIRECT_MATCH | NEEDS_CLARIFICATION | NO_MATCH
- `source_id` — matched KB article (if any)
- `confidence` — retrieval score
- `rewrite_applied` — boolean
- `rewritten_text` — rewritten query (if any)
- `pipeline_status` — completed | paused

See [[10-architecture/data-models#QueryLog]] for full schema.

---

## Key invariants

1. **Single path rule** — All queries go through this pipeline. No parallel code paths, no inline shortcuts.
2. **Stage order is non-negotiable** — normalize → intent → retrieve → clarification_gate → rewrite → retrieve_retry
3. **Clarification stops the pipeline** — If clarification is needed, rewrite MUST NOT run
4. **Rewrite is optional** — Only triggers for low-confidence or noisy queries
5. **Retry is conditional** — Only runs if rewrite produced a different query

---

## Related notes

- [[10-architecture/intent-system]] — Intent classification
- [[10-architecture/semantic-search]] — Retrieval + filtering
- [[10-architecture/clarification-system]] — Clarification trigger and resolution
- [[10-architecture/data-models]] — QueryLog schema
- [[20-sprints/sprint-1/user-stories#0.1]] — Story 0.1: Create canonical pipeline orchestrator
- [[20-sprints/sprint-1/decisions#0.1-D1]] — Decision: Single canonical pipeline path
- [[20-sprints/sprint-1/decisions#0.3-D2]] — Decision: Clarification pause state

---

## Evidence

| Commit | Date | Author | Message |
|--------|------|--------|---------|
| a326ebb | 2026-05-03 | whitefangggggg | Slice 0 : Story 1 (Canonical Pipeline) complete |
| 4f29463 | 2026-05-03 | Selina Mae Genosolango | Feat: Added Clarification Pause State to Query Flow |
