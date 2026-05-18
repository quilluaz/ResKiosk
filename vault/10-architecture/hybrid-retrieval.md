---
title: "Hybrid Retrieval — Lexical + Vector Fusion"
aliases: ["hybrid retrieval", "BM25", "RRF", "lexical search"]
tags: [type/architecture, component/hub, layer/retrieval, sprint/3, slice/4]
sprint: 3
generated_at: "2026-05-15T08:48:57Z"
generated: true
---

# Hybrid Retrieval — Lexical + Vector Fusion

Added in **Sprint 3** (Slice 4 — Deterministic Retrieval Core).

ResKiosk's hybrid retrieval system fuses **lexical** (BM25) and **vector** (semantic/MiniLM) search paths using Reciprocal Rank Fusion (RRF) to improve exact-term recall while preserving semantic understanding.

---

## Architecture overview

```
User query (normalized)
    ├─→ Lexical path (BM25)
    │   └─→ LexicalIndex.score() → top-k IDs + scores
    │
    ├─→ Vector path (semantic)
    │   └─→ MiniLM embed → cosine sim → top-k IDs + scores
    │
    └─→ RRF Fusion
        └─→ Fused top-k (deterministic ranking)
```

Both paths respect the **Sprint 1 filter policy** (hard > UI > inferred) and the **Sprint 3 quarantine exclusion** (Story 3.5).

---

## Components

### 1. Lexical Index (`hub/retrieval/lexical.py`)

**Class:** `LexicalIndex`

**What it is:** In-memory inverted index over KB articles with BM25 scoring.

**Indexed fields (weighted):**
- `question` — 1.5x (title/query match is most important)
- `tags` — 2.0x (curated terms are strong signals)
- `answer` — 1.0x (body text for broader coverage)

**Tokenization:** Deterministic pipeline
1. Lowercase
2. Strip punctuation (regex: `[^\w\s]`)
3. Split on whitespace
4. Remove stopwords (minimal 27-word set to preserve shelter-domain terms)

**BM25 parameters:**
- `k1 = 1.5` (term frequency saturation)
- `b = 0.75` (length normalization)

**Build process:**
- Triggered at publish time when `kb_version` increments
- Queries `kb_articles` where `enabled == 1`
- Excludes `quarantined` and `rejected` articles via `excluded_ids` parameter (Story 3.5)
- Build time: ~10-50ms for typical KB size
- Tracks `kb_version` for staleness detection

**Scoring:**
- Classic Okapi BM25: `IDF(term) * (TF * (k1 + 1)) / (TF + k1 * (1 - b + b * doc_length / avg_doc_length))`
- Returns `LexicalSearchOutput` with top-k article IDs, scores, ranks
- Query latency: ~5-15ms for 3-5 term queries

**Fallback:** If index is missing or stale (version mismatch), retrieval falls back to vector-only.

---

### 2. RRF Fusion (`hub/retrieval/fusion.py`)

**Function:** `rrf_fuse(vector_candidates, lexical_candidates, top_k, rrf_k)`

**Formula:**
```
fusion_score(article) = Σ_path [1 / (k + rank_in_path)]
```

Where:
- `k` = RRF constant (default 60, configurable via `RESKIOSK_RRF_K`)
- `rank_in_path` = 1-indexed rank (1 = top result)

An article appearing in both paths gets contributions from both; appearing in one path only gets one contribution.

**Tie-breaking (deterministic, 6-tier):**
1. `fusion_score` (desc)
2. `overlap_count` (desc) — articles in both paths rank higher
3. `best_rank` (asc) — best rank across all paths
4. `vector_rank` (asc)
5. `lexical_rank` (asc)
6. `article_id` (asc) — final stable sort

**Output:** `FusionOutput` dataclass containing:
- `strategy`: `"rrf"`
- `parameters`: `{"k": 60, "top_k": 5}`
- `results`: List of `FusedCandidate` (each with `article_id`, `fusion_score`, `rank`, `vector_rank`, `lexical_rank`, `vector_score`, `lexical_score`, `overlap_count`)
- `tie_breaks`: Audit trail of tie-break decisions

**Edge cases:**
- Vector-only (lexical empty): returns vector results with fusion wrapper
- Lexical-only (vector empty): returns lexical results with fusion wrapper
- Full overlap: both paths contribute equally
- Partial overlap: mixed contributions

---

## Integration with existing retrieval

### Filter policy (Story 4.4)

The Sprint 1 filter precedence (hard > UI > inferred) wraps **both** retrieval paths:

**Hard filters (applied at index build / corpus load time):**
- `enabled == 1`
- `status == 'published'` (or vector-only fallback for draft testing)
- **NOT** `quarantined` or `rejected` (Story 3.5)

**UI filters (applied post-fusion):**
- User-selected taxonomy nodes
- User-selected intent categories

**Inferred filters (applied post-fusion):**
- Intent-enriched taxonomy hints

**Safety guarantee:** Quarantined articles never enter the lexical index or vector corpus.

---

### Query pipeline integration (`hub/retrieval/search.py`)

1. Normalize query → tokenize for lexical, embed for vector
2. **Parallel retrieval:**
   - Lexical: `lexical_search(db, query, top_k, excluded_ids)` → `LexicalSearchOutput`
   - Vector: `cosine_sim(query_embedding, corpus_matrix)` → top-k IDs + scores
3. **Fusion:** `rrf_fuse(vector_candidates, lexical_candidates)` → `FusionOutput`
4. Apply UI and inferred filters to fused results
5. Return top-k evidence with contribution metadata

**Degradation paths:**
- Lexical index missing/stale → vector-only + logged degradation
- Vector corpus missing → lexical-only (rare, safety fallback)
- Both missing → error logged, no results

---

## Configuration (environment variables)

| Variable | Default | Purpose |
|----------|---------|---------|
| `RESKIOSK_RRF_K` | `60` | RRF constant (higher = flatter fusion) |
| `RESKIOSK_HYBRID_TOP_K` | `5` | Top-k results to return from fusion |

---

## Observability (Story 4.5, partially delivered)

Logged per query (target: `query_logs` table columns added by 6A.1):

**Lexical path:**
- `lexical_top_k_ids` (JSON array)
- `lexical_top_k_scores` (JSON array)
- `lexical_top_k_ranks` (JSON array)
- `lexical_latency_ms` (REAL)

**Vector path:**
- `vector_top_k_ids` (JSON array)
- `vector_top_k_scores` (JSON array)
- `vector_top_k_ranks` (JSON array)

**Fusion:**
- `fusion_strategy` (TEXT) — e.g., `"rrf"`
- `fusion_top_k_ids` (JSON array)
- `fusion_top_k_scores` (JSON array)
- `fusion_top_k_ranks` (JSON array)

> 🔍 Inferred: Story 4.5 (contribution logging) is listed as active in Sprint 3. Wiring to populate these columns is likely in progress but not yet committed as of 2026-05-15.

**Cap:** Top 5 per path (per decision [[20-sprints/sprint-3/decisions|3-D2]]).

---

## Evaluation (Story 4.6)

**Framework:** `hub/eval/exact_term_retrieval_eval.py`

**Test set:** 12 queries in `hub/eval/data/exact_term_retrieval_eval_v1.json`
- Proper nouns (clinic names, building names)
- Exact procedural terms (registration steps)
- Mixed exact + descriptive queries

**Metrics:**
- Top-3 accuracy (vector-only vs hybrid)
- Top-5 accuracy (vector-only vs hybrid)
- Determinism check (same results on repeat runs)

**Reproducibility:** Uses snapshot-based KB + precomputed vector scores (no live model drift).

**CLI:**
```bash
python -m hub.eval.exact_term_retrieval_eval
python -m hub.eval.exact_term_retrieval_eval --json-out results.json
```

---

## Design decisions

See [[30-decisions/slice-4]] for full rationale.

**Key choices:**
- In-memory inverted index (not SQLite FTS5) — simpler rebuild, no schema migration, explicit BM25 control
- Field weights favor `tags` (2.0x) and `question` (1.5x) — curator intent signals rank highest
- Minimal stopword list (27 words) — preserves shelter-domain terms like "shelter", "emergency", "aid"
- RRF over learned fusion — deterministic, no training data needed, interpretable
- Top-k cap of 5 — balances coverage vs log volume

---

## Related notes

- [[10-architecture/semantic-search]] — vector-only retrieval (Sprint 1 baseline)
- [[10-architecture/validation-pipeline]] — quarantine exclusion (Story 3.5)
- [[20-sprints/sprint-3/user-stories]] — Stories 4.1–4.6
- [[30-decisions/slice-4]] — Slice 4 design decisions
