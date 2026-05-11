## ResKiosk — Product Increment Goals (AAIH)

> **This section is the current source of truth for the increment goals.**  

# ResKiosk — Product Increment Overview (AAIH Hackathon 2026)

## Introduction

ResKiosk is an evacuation-center information kiosk system designed to help shelter residents get accurate, actionable guidance during emergencies (e.g., registration steps, food/water schedules, medical help, facility locations, and safety procedures) even in constrained or offline environments.

For AI for ASEAN Hackathon 2026, we are planning and delivering a product increment that upgrades ResKiosk’s AI capabilities to better support real shelter workflows and higher-stakes scenarios. :contentReference[oaicite:0]{index=0}  

---

## Focus of this Product Increment

- **Multimodal knowledge base**
  - Ingest, store, and retrieve images as first-class KB evidence
  - Includes originals, thumbnails, and versioned invalidation

- **Semantic image retrieval**
  - Enable image ↔ text semantic search
  - Use cases: landmarks, buildings, first-aid visuals

- **More reliable retrieval**
  - Hybrid retrieval (BM25 + vectors)
  - Multi-path retrieval for compound queries

- **Safer interaction flow**
  - Clarification UX improvements
  - Enforced pipeline:
    ```
    normalize → intent → (optional) clarification → constrained rewrite
    ```

- **Measurement**
  - MVP metrics + logging for:
    - grounding
    - evidence match
    - latency

---

## Global Assumptions

- **English at retrieval boundary**
  - All inputs translated via NLLB-200 before retrieval

- **Scale**
  - ~1k–5k KB articles

- **Schema decision**
  - No semantic chunking this increment
  - Retrieval unit = one `kb_articles` row

- **Stable ranking**
  - Deterministic for fixed KB version/config
  - Exception: explicit feedback bias

---

## Prioritization (Build Order)

1. **Product Goal C — Safety & Controlled Interaction**
2. **Product Goal A — Accuracy & Reliability**
3. **Product Goal D — Observability & Trust**
4. **Product Goal B — Visual Guidance / Multimodal**

---

# Goals Breakdown

---

## Goal 1 — Semantic Image Search (CLIP/SigLIP)

### Currently
- Text-only embedding retrieval
- No image encoder

### Why
- Visual guidance needed for navigation and first aid

### Outcome
- Image ↔ text semantic search
- Image evidence returned in responses

### Success Criteria
- Relevant images retrieved with stable IDs
- First-aid and navigation queries return correct images

---

## Goal 2 — Image Storage as First-Class KB Assets

### Currently
- Images not modeled as first-class assets

### Outcome
- Images stored with:
  - original + thumbnail
  - content hash
  - kb_version linkage

### Success Criteria
- Publish invalidates image caches correctly
- Image evidence references remain stable

---

## Goal 3 — KB Schema Rework for Multimodal Retrieval

### Currently
- Schema only supports text embeddings

### Outcome
Schema supports:
- modality (text/image)
- asset references
- metadata for filtering
- forward-compatible segmentation fields

### Success Criteria
- Safe migrations
- Stable IDs across versions

---

## Goal 4 — Hybrid Retrieval (BM25 + Vectors)

### Currently
- Vector-only retrieval

### Outcome
- Hybrid lexical + vector retrieval
- Deterministic fusion (e.g., RRF)

### Success Criteria
- Exact-term queries improve
- Stable rankings per KB version

---

## Goal 5 — Multi-Path Retrieval

### Currently
- Single-pass retrieval

### Outcome
- Split queries into multiple intents
- Merge results with priority rules

### Success Criteria
- Compound queries handled correctly
- Evidence attributed per path

---

## Goal 6 — Clarification UX Before Rewriting

### Currently
- Limited ambiguity handling

### Outcome
- UI clarification chips before retrieval

### Success Criteria
- Ambiguity resolved in 1–2 steps
- Clarifications logged

---

## Goal 7 — Metadata Schema + Filtering Policy

### Currently
- Filtering not formally enforced

### Outcome
Filtering precedence:
1. Hard rules
2. UI filters
3. Inferred intent

### Success Criteria
- Filters logged and explainable
- Predictable behavior

---

## Goal 8 — Metadata Validation Gate

### Currently
- No validation before publish

### Outcome
- Rule-based + human-reviewed validation pipeline

### Success Criteria
- Low-confidence metadata quarantined
- Audit trail exists

---

## Goal 9 — Retrieval Quality Improvements

### Currently
- Feedback bias only (not true reranking)

### Outcome
- Improve via:
  - hybrid retrieval
  - multi-path
  - clarification

### Success Criteria
- Precision improves without reranker
- Bias remains controlled and measurable

---

## Goal 10 — MVP Metrics + Logging

### Currently
- Basic logs only

### Outcome
Track:
- grounding
- hallucination proxy
- evidence match
- latency

### Success Criteria
- Metrics computable per KB version

---

## Goal 11 — Safer Caching Patterns

### Currently
- In-memory caches only

### Outcome
- Version-aware caching
- TTL + invalidation hooks

### Success Criteria
- No stale answers
- Cache behavior observable

---

## Goal 12 — Canonical Pipeline Order

### Currently
- Pipeline not enforced

### Outcome
Enforced order: normalize → intent → clarification → constrained rewrite → retrieval


### Success Criteria
- Clarification occurs before rewrite
- All stages logged deterministically

---

# Product Goals (Epics)

## Product Goal A — Accuracy & Reliability
- Goal 4
- Goal 5
- Goal 9

## Product Goal B — Visual Guidance
- Goal 1
- Goal 2
- Goal 3

## Product Goal C — Safety & Controlled Interaction
- Goal 6
- Goal 7
- Goal 8
- Goal 12

## Product Goal D — Observability & Trust
- Goal 10
- Goal 11

## Session notes: codebase + `reskiosk_db.md` (do not delete — working context)

### Confirmed from codebase

- **Embeddings:** `hub/retrieval/embedder.py` loads `SentenceTransformer` from bundled **`all-MiniLM-L6-v2`**. Only **`embed_text()`** exists — **no image encoder**. `get_embeddable_text()` uses **question + tags only** (answer body excluded on purpose).
- **Retrieval:** `hub/retrieval/search.py` — **single** query embedding vs **in-memory matrix** of article vectors; **`sentence_transformers.util.cos_sim`**. **No BM25**, no Elasticsearch/OpenSearch, no SQLite FTS for articles.
- **“RLHF”:** Env-gated **`RESKIOSK_RLHF_ENABLED`**. Applies **per-article bias** from `article_biases` to cosine scores (`RLHF_ALPHA`). **Not** online learning / policy gradients; **not** a cross-encoder reranker.
- **Compound queries:** `classify_top2` + `_resolve_compound_intents` can mark compound and merge **both intents’ enrichment strings into one `search_query`**. Still **one** embedding and **one** retrieval pass — **no parallel** sub-queries.
- **Clarification:** `needs_clarification()` returns true only when **`intent == "unclear"`** AND **best retrieval score &lt; `CLARIFICATION_FLOOR`** (and not suppressed by compound shortcut). “Ambiguous scope” is **not** a separate coded trigger — it’s approximated by **unclear intent + low score**.
- **Caching today:** In-memory **`_corpus_cache`** (embeddings) and **`_shelter_config_cache`**; invalidated on publish/admin paths. **No** response-level FAQ cache yet (your item 15 is greenfield).

### `reskiosk_db.md` — fields relevant to backlog

- **`kb_articles`:** `id`, `question`, `answer`, `category`, `tags`, `enabled`, `source`, `created_at`, `last_updated`, **`embedding` (BLOB)**, `status`, `created_by`, `updated_by`.
- **Versioning:** **`kb_meta.kb_version`**, **`query_logs.kb_version`**, **`system_version.kb_version`** — use these for **cache invalidation** and audit trails.
  - **Codebase note:** `/admin/publish` currently bumps **`system_version.kb_version`** (and invalidates the in-memory corpus cache). `kb_meta` exists but is not currently updated by publish.
- **Feedback / “RLHF” bias:** `feedback_logs` (per interaction), **`article_biases`** (`source_id`, `bias`, `updated_at`).
- **Clarification analytics:** **`clarification_resolutions`** (`session_id`, `resolved_intent`, `language`, …).
- **Shelter/runtime config:** **`evac_info`**, **`structured_config`** — align metadata filters and pre-filters with what you already store here before inventing new tables.

### Recommendations captured from discussion (for next design pass)

- **1b Embeddings:** MiniLM **does not** embed images. Practical pattern: **text** (EN/tl/ceb) via multilingual sentence model *or* keep MiniLM short-term + **separate** CLIP/SigLIP **or** image→caption/OCR→same text pipeline. True single “lightweight” model for **photo of building + Tagalog query** with SOTA text quality is uncommon — **dual path** is the usual tradeoff.
- **6b/c Images:** Store **original** + **thumbnail** (kiosk UI); add **content hash** / `kb_version` for invalidation. PII policy TBD.
- **8b Metadata (starter set):** Leverage existing: `source_id`, `category`, `tags`, `status`, `enabled`, `last_updated`, `kb_version` (session/query). New work: **`modality`**, **`locale`**, **`parent_article_id`** (PDF multi-article), **`chunk_index`**, image asset refs — extend schema deliberately (versioned migrations).
- **9a LLM-as-judge:** Optional **offline** or **human-review queue** to avoid latency bloat; rules + confidence first.
- **10b “Optimal” reranker:** Phase 1: **hybrid + RRF** + thresholding. Phase 2: **cross-encoder** on top-k only if metrics show need. Keep **bias-from-feedback** as separate tunable layer; rename stakeholder-facing “RLHF” → **“feedback-adjusted ranking”** unless you add real RL.
- **12c MVP metrics (example set):** (1) **Answer supported rate** — claims checkable against `article_data` / retrieved text. (2) **Hallucination proxy** — unsupported spans vs context (LLM or rule-based for MVP). (3) **Citation / source match** — `source_id` stability vs top-1 raw cosine. (4) **Latency** — STT + retrieve + TTS from `query_logs.latency_ms` / breakdown fields. (5) **Thumb feedback rate** optional.
- **13a Filters:** Yes, combine **UI + inferred intent + hard rules** — precedence should be explicit (e.g. hard safety &gt; user filter &gt; inferred).
- **14c Staged filtering:** With **~1k–5k** articles and SQLite-scale corpus, **likely defer** staged ANN pre/post filter until profiling shows **latency or index** pain; still add **metadata columns** early if you know filters are coming.
- **15c Cache safety:** Do **not** use “other sessions’ thumbs” as primary truth for correctness. Prefer **`kb_version` + TTL** + optional **re-validate top answer** against current retrieval hash.
- **18c Clarification UX:** Offer **2–3 tap chips** (categories / “which building”) before free-text re-query; keep **one** fallback “Say that differently” with example.
- **19a Rewrite:** **Structured filters** for high-stakes (medical, child safety); **NL rewrite** for noisy STT. Order: normalize → intent → **optional clarification** → rewrite with constraints.
- **16b / 20b Compound merge:** **Retrieve top-k per sub-intent** (or split query) then **RRF** or **priority merge** (safety/medical first); parallel **fan-out** only after you have **multiple retrieval keys** (not one concatenated embedding).