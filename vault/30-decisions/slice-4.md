---
title: "Slice 4 — Deterministic Retrieval Core"
aliases: ["slice 4", "hybrid retrieval", "BM25 + RRF"]
tags: [type/decision, slice/4, goal/4, goal/7, goal/9, goal/10, status/active]
sprint: 3
generated_at: "2026-05-11T11:37:24Z"
generated: true
---

# Slice 4 — Deterministic Retrieval Core

**Related goals:** Goal 4 (Hybrid retrieval), Goal 9 (Quality via retrieval stack), Goal 7 (Filtering applied), Goal 10 (Observability)
**Sprint:** Sprint 3 (May 11–17) — starting
**Status:** 🔄 Active
**Work items:** 6 (required) + 1 stretch
**Story points:** 32 required + 5 stretch

---

## Overview

Slice 4 is the first major retrieval improvement of the AAIH increment. Before Slice 4, ResKiosk's retrieval is **vector-only** — `SentenceTransformer all-MiniLM-L6-v2` produces a single embedding compared against an in-memory matrix of article vectors using `sentence_transformers.util.cos_sim` (per the [[00-pre-sprint-baseline/_index|baseline]]). Exact-term queries like "where is St. Luke's clinic" or "registration form M-12" can underperform because the embedding space doesn't reward rare proper-noun matches.

Slice 4 adds a parallel **lexical (BM25-like) retrieval path** running over the same `kb_articles` corpus, then fuses the two rankings with **Reciprocal Rank Fusion (RRF)** to produce one stable top-k list. Both paths obey the Slice 1 filter precedence (hard > UI > inferred), and every fusion decision is logged for explainability.

---

## Goals served

### Goal 4 — Hybrid retrieval with BM25 + vectors
Reproducible ranking from two fused retrieval paths. Exact-term queries (names, procedures, locations) become reliable while semantic recall is preserved.

### Goal 7 — Filtering policy
Both lexical and vector paths must respect the same hard / UI / inferred filter precedence. Disabled, unpublished, or quarantined articles cannot reach fusion.

### Goal 9 — Retrieval quality improvements
Hybrid retrieval is the first lever pulled to improve quality without adding a heavy reranker. Feedback-adjusted ranking (4.7) is intentionally deferred as a separate layer applied after fusion.

### Goal 10 — Observability
Per-item contribution logging (lexical rank/score, vector rank/score, fused rank/score) makes ranking decisions inspectable.

---

## Work items

| ID | Work Item | Points | Status |
|----|-----------|--------|--------|
| 4.1 | Build lexical retrieval index | 8 | 🔄 Active |
| 4.2 | Implement BM25-like lexical scoring | 5 | 🔄 Active |
| 4.3 | Fuse lexical and vector results with RRF | 8 | 🔄 Active |
| 4.4 | Apply filter policy to hybrid retrieval | 5 | 🔄 Active |
| 4.5 | Add hybrid retrieval contribution logging | 3 | 🔄 Active |
| 4.6 | Create exact-term retrieval evaluation set | 3 | 🔄 Active |
| 4.7 | Tune feedback-adjusted ranking as a separate layer | 5 | ⏸ Stretch / deferred |

See [[20-sprints/sprint-3/user-stories|Sprint 3 user stories]] for per-story acceptance criteria.

---

## Key design decisions

### 4-D1: SQLite FTS5 with built-in BM25 (proposed)

Reuses the existing SQLite database — no new dependencies, no new PyInstaller spec entries, no new daemon to run. FTS5 is mature and deterministic; its `unicode61` tokenizer with `remove_diacritics=2` produces reproducible tokenization across queries. The increment scale (~1k–5k articles) is well within FTS5's comfortable range.

See [[20-sprints/sprint-3/decisions|3-D3]] for full reasoning.

### 4-D2: RRF over weighted-score normalization (proposed)

RRF uses ranks rather than raw scores, so the wildly different score scales between FTS5 BM25 (often negative, lower is better) and MiniLM cosine similarity (0..1, higher is better) don't need normalization. `k=60` is the conventional default. Tie-break: `(fused_score desc, kb_articles.id asc)` for stable ordering.

See [[20-sprints/sprint-3/decisions|3-D4]] for full reasoning.

### 4-D3: Lexical index is **version-aware** and rebuilt at every publish

The FTS index lives in the same SQLite DB and is rebuilt when `kb_version` increments via `POST /admin/publish`. If the index is missing or its version doesn't match the current `kb_version`, retrieval falls back to **vector-only** with a logged degradation event. This matches the Goal 4 §7 "lexical index missing/stale" failure-mode expectation.

> 🔍 Inferred: The implementation likely uses an FTS5 `external content` table linked to `kb_articles`, with rebuild triggered by the same publish hook that currently invalidates `_corpus_cache` for vector embeddings. The version tag could be stored in `kb_meta` or a simple sidecar table.

### 4-D4: Filters apply to **both paths before fusion**, not after

Filtering happens before scoring in each path. Hard rules (enabled, status, quarantined) and UI/inferred filters reduce the candidate set per path independently. Fusion then receives already-filtered top-k lists. This prevents a quarantined article from accidentally winning a path's ranking and "polluting" the fused output.

### 4-D5: Feedback-adjusted ranking is a **separate post-fusion layer**, not part of fusion

The existing `article_biases` table (used by RLHF env-gate today) continues to be a separate, optional layer applied **after** RRF fusion, before final top-k selection. This decouples the bias mechanism from the fusion math and matches Story 4.7's "as a separate layer" framing.

---

## Hybrid retrieval data flow

```
POST /query
    │
    ▼
canonical pipeline (Slice 0): normalize → intent → clarification gate
    │
    ▼
filter policy (Slice 1): hard > UI > inferred
    │  resolves a candidate filter mask
    ▼
┌───────────────────────┐         ┌───────────────────────┐
│ Lexical path (4.1+4.2)│         │ Vector path (existing)│
│  FTS5 BM25 over       │         │  MiniLM cosine sim    │
│  question + tags      │         │  vs corpus matrix     │
│  apply filter mask    │         │  apply filter mask    │
│  top-K (default 50)   │         │  top-K (default 50)   │
└───────────┬───────────┘         └───────────┬───────────┘
            │ lexical_top_k (ids, scores, ranks)  │ vector_top_k (ids, scores, ranks)
            ▼                                     ▼
        ┌────────────────────────────────────────────┐
        │ RRF fusion (4.3)                           │
        │  score(d) = Σ 1 / (k=60 + rank_path)       │
        │  tie-break: (score desc, id asc)           │
        └─────────────────┬──────────────────────────┘
                          │ fusion_top_k
                          ▼
              optional: feedback-adjusted ranking (4.7 stretch)
                          │
                          ▼
              final top-k → formatter → response
```

---

## Logging schema (interface with Slice 6A.1)

Story 4.5 populates these columns on `query_logs` (added by 6A.1):

| Column | Type | Source |
|--------|------|--------|
| `lexical_top_k_ids` | TEXT (JSON array, cap 5) | 4.2 output |
| `lexical_top_k_scores` | TEXT (JSON array) | 4.2 output |
| `lexical_top_k_ranks` | TEXT (JSON array) | 4.2 output |
| `lexical_latency_ms` | REAL | 4.2 timing |
| `vector_top_k_ids` | TEXT (JSON array, cap 5) | existing vector path |
| `vector_top_k_scores` | TEXT (JSON array) | existing vector path |
| `vector_top_k_ranks` | TEXT (JSON array) | existing vector path |
| `fusion_strategy` | TEXT | 4.3 (e.g., `"rrf"`) |
| `fusion_top_k_ids` | TEXT (JSON array, cap 5) | 4.3 output |
| `fusion_top_k_scores` | TEXT (JSON array) | 4.3 output |
| `fusion_top_k_ranks` | TEXT (JSON array) | 4.3 output |

Top-5 cap matches [[20-sprints/sprint-3/decisions|3-D2]].

---

## Evaluation criteria (Story 4.6)

A fixed evaluation set with at least three query archetypes:
- **Exact proper nouns** — clinic names, building names, registration form IDs
- **Procedural terms** — "registration steps", "first aid for burns"
- **Mixed exact + descriptive** — "where do I get the M-12 form for kids"

Comparison metrics:
- Top-3 / Top-5 accuracy (expected `kb_articles.id` in result set)
- Determinism — identical top-k ordering across repeated runs on same `kb_version`
- Latency — total retrieve time before vs after hybrid

Regression criteria: no degradation beyond a defined threshold on baseline semantic queries while improving exact-term query accuracy.

---

## Dependencies

**Depends on:**
- [[30-decisions/slice-0]] — Canonical pipeline (where hybrid retrieval is invoked)
- [[30-decisions/slice-1]] — Filter precedence (which hybrid retrieval must obey)
- [[30-decisions/slice-3]] — Quarantine status (which hybrid retrieval must exclude via 3.5)
- 6A.1 (logging schema) — strict prerequisite for 4.5

**Affects:**
- [[30-decisions/slice-6a|Slice 6A]] — provides the contribution log target
- Future Slice 5 (multi-path) — fusion must be extendable to per-intent paths
- Future Slice 7C (image retrieval) — fusion pattern will be reused for text+image fusion

---

## Related notes

- [[20-sprints/sprint-3/_index|Sprint 3 index]]
- [[20-sprints/sprint-3/user-stories|Sprint 3 user stories]] — full acceptance criteria per story
- [[20-sprints/sprint-3/decisions|3-D3, 3-D4]] — proposed FTS5 + RRF decisions
- [[30-decisions/slice-6a|Slice 6A]] — observability layer that captures hybrid decisions
- [[00-pre-sprint-baseline/_index|baseline]] — vector-only retrieval as it stands today
- `ai_helper/goal_outlines/goal_4.md` — full goal spec including non-goals and open decisions
