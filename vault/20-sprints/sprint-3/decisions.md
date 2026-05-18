---
title: "Sprint 3 — Decisions"
tags: [type/decision, sprint/3]
sprint: 3
generated_at: "2026-05-11T11:37:24Z"
generated: true
---

# Sprint 3 — Key decisions

## 3-D1: Story 6A.1 (log schema) ships **first**, before any Slice 4 work

**Status:** Accepted
**Date:** 2026-05-11 (sprint kickoff)
**Related stories:** 6A.1, 4.1, 4.2, 4.3, 4.5, 6A.8
**Source:** `slice6a_story1_running_context.md`

### Context
Slice 4 introduces three new retrieval paths (lexical, vector, fusion) that need to write per-path top-k IDs, scores, ranks, and latency to `query_logs`. Slice 6A.1 adds those columns. If Slice 4 work starts before 6A.1 lands, there is no schema target — Person 3 (lexical) and Person 4 (fusion) end up either logging to text blobs that have to be re-migrated, or skipping logging entirely (failing 4.5).

### Decision
6A.1 is the first story landed in Sprint 3, ahead of 4.1. All 17 new columns are added in one migration even though some (lexical_*, vector_*, fusion_*) won't be written for several days. The schema is the interface contract.

### Consequences
- Person 5 (assumed owner of 6A.1) is on the critical path for the first half of Sprint 3.
- 4.5 (contribution logging) and 6A.8 (fallback logging) can land anytime after 6A.1 with no dependency on full Slice 4 functionality.
- Some columns sit nullable until Slice 4 finishes — acceptable trade for parallelism.

### Related notes
- [[20-sprints/sprint-3/user-stories|6A.1 story detail]]
- [[30-decisions/slice-6a]] — Slice 6A design

---

## 3-D2: Log up to **top-5** candidates per retrieval path

**Status:** Accepted
**Date:** 2026-05-11
**Related stories:** 6A.1, 4.5
**Source:** `slice6a_story1_running_context.md`

### Context
Hybrid retrieval has three rankings to log: lexical top-k, vector top-k, fused top-k. The query_logs row must stay bounded (AC6 of 6A.1). Realistic options: top-3, top-5, top-10.

### Decision
Cap stored rankings at top-5 per path. JSON arrays of IDs, scores, and ranks, each capped at 5 elements. Stored as `TEXT` columns containing JSON.

### Consequences
- Enough signal to debug "why did this article win" and to evaluate ranking stability between paths.
- Roughly 15 small JSON arrays per log row — manageable size.
- If we ever need top-10 for offline evaluation, we can store it separately in an evaluation-specific table without bloating `query_logs`.

---

## 3-D3: Lexical index uses **SQLite FTS5 with BM25** rather than an external search service

**Status:** Proposed (per Goal 4 outline; final pick happens in Story 4.1)
**Date:** 2026-05-11
**Related stories:** 4.1, 4.2
**Source:** `ai_helper/goal_outlines/goal_4.md` §11 "Open Decisions"

### Context
Hybrid retrieval needs a lexical scorer. Three viable options:
1. SQLite FTS5 — built into the DB we already use, BM25 ranking included
2. External index file (e.g., Whoosh, Tantivy via Python bindings)
3. External search service (Elasticsearch, OpenSearch)

ResKiosk runs offline on a single Windows laptop packaged as `ResKiosk-Hub.exe`. The KB is ~1k–5k articles per the increment assumptions. Option 3 is over-engineered. Option 2 adds a new dependency. Option 1 reuses existing infrastructure.

### Decision (proposed)
Use SQLite FTS5 with built-in BM25 ranking. Build the FTS index from `kb_articles.question + kb_articles.tags` (matching what the embedder uses for vector embeddings — `answer` body is intentionally excluded per `embedder.py::get_embeddable_text()`). Rebuild the FTS index on every `kb_version` bump.

### Consequences
- Zero new dependencies, zero new build-spec changes for PyInstaller.
- FTS5 is mature and deterministic; tokenization config (`unicode61`, `remove_diacritics=2`) is reproducible.
- BM25 in FTS5 returns negative scores by convention (lower is better). Code must invert or convert to a consistent positive-better space before fusion.
- Trade-off: limited to whatever FTS5 supports — no custom analyzer chain, no field-level boosts (mitigated by RRF using ranks, not raw scores).

### Open follow-ups
- Confirm whether `answer` body should remain excluded from FTS (it's excluded from embeddings on purpose, but lexical retrieval might benefit from it). Currently leaning: keep excluded to match retrieval-unit assumption.

### Related notes
- [[30-decisions/slice-4]] — Slice 4 design
- [[00-pre-sprint-baseline/architecture|baseline architecture]] — what's already in place

---

## 3-D4: RRF (Reciprocal Rank Fusion) over weighted-score normalization

**Status:** Proposed (per Goal 4 outline; final pick happens in Story 4.3)
**Date:** 2026-05-11
**Related stories:** 4.3
**Source:** `ai_helper/goal_outlines/goal_4.md`

### Context
Fusion strategies for combining lexical and vector rankings:
1. **Reciprocal Rank Fusion (RRF):** uses ranks, not raw scores. `score(doc) = sum(1/(k+rank_path))`. Robust to score-scale differences across paths.
2. **Weighted score normalization:** normalize each path's scores to [0,1], then weighted sum. Requires per-path scaling, sensitive to score distribution shifts.
3. **Cascade:** run lexical first, take its top-N as candidates for vector reranking. Loses recall.

### Decision (proposed)
RRF with `k=60` (conventional default). It is rank-based so the wildly different score scales between FTS5 BM25 and MiniLM cosine similarity don't matter. Tie-break: `(fused_score desc, kb_articles.id asc)` for stable ordering.

### Consequences
- Stable ordering for fixed `(kb_version, query, filters)` regardless of relative score drift.
- Trivial to log: `fusion_strategy="rrf"`, `fusion_k=60`.
- Cannot down-weight a path that turns out to be noisy — would have to switch strategies entirely.
- Story 4.7 (stretch) for feedback-adjusted ranking is intentionally a separate layer applied after fusion, not within fusion. Matches the Goal 9 + Goal 4.7 contract.

### Related notes
- [[30-decisions/slice-4]] — Slice 4 design
