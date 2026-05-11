# Goal 4 — Hybrid retrieval with BM25 + vectors (reproducible ranking)

### 1) Outcome

Implement **hybrid retrieval** (lexical BM25-like + vector similarity) with **reproducible ranking** for a fixed KB version/config, so exact-term queries (names, procedures, locations) are reliably retrieved while preserving semantic recall.

- **What changes**: retrieval becomes a fused result set from two retrieval paths (lexical + vector) rather than vector-only.
- **Who benefits**: residents (more accurate results for exact terms), operators (predictable behavior), maintainers (debuggable retrieval decisions).
- **What success looks like**:
  - exact-term queries consistently surface correct KB items in top results on a defined test set
  - rankings are stable for the same KB version/config + same normalized query/filters
  - logs clearly show lexical vs vector contributions and the fusion decision

---

### 2) Why this matters

- **Current limitation**: retrieval is **vector-only**; there is no lexical index/BM25, so queries with rare proper nouns or exact phrases can underperform.
- **Risk addressed**: inconsistent recall for high-stakes, location- and procedure-specific queries reduces trust and increases retries.
- **Value**: hybrid retrieval improves recall for exact terms while increasing debuggability (lexical matches are inspectable), and forms the foundation for Goals 5/7 (multi-path + filtering) without requiring heavy reranking.

---

### 3) Scope

- Implement a **lexical retrieval path** over KB content used for retrieval (minimum viable: fields already used for embedding such as `kb_articles.question` + `kb_articles.tags`; optionally include additional fields if policy allows).
- Implement a **fusion strategy** (e.g., Reciprocal Rank Fusion / RRF or an equivalent explicit method) to combine lexical and vector rankings into a single top-k list.
- Enforce **determinism** for a fixed KB version/config:
  - stable tokenization/normalization for the lexical path
  - stable fusion parameters and tie-break rules
- Ensure the hybrid stack can accept (or is compatible with) **filtering policy** (Goal 7) even if filters are minimal initially (`enabled`, `status`, etc.).
- Add minimum viable **instrumentation** so Goal 10 metrics can attribute which path produced each evidence item and why.

---

### 4) Non-goals

- Deploying a heavyweight search cluster (e.g., Elasticsearch/OpenSearch) unless already required by repo constraints (prefer smallest viable solution for this increment).
- Adding a cross-encoder reranker or LLM reranker in the hot path (explicitly deferred; focus is retrieval architecture).
- Semantic chunking of KB articles (global increment assumption: retrieval unit remains a `kb_articles` row).
- Changing the canonical pipeline order (handled in Goal 12).

---

### 5) System Impact

#### a. Data / Schema

**Existing**

- `kb_articles` remains the retrieval unit (`kb_articles.id`, `question`, `tags`, `enabled`, `status`, `embedding`).
- Versioning already exists via `kb_meta.kb_version` and is recorded in `query_logs.kb_version`.

**New (Goal 4 introduces or requires)**

- A **lexical index** for KB retrieval fields.
  - Storage choice is implementation-dependent (e.g., SQLite FTS virtual table vs an on-disk index file), but it must be:
    - rebuildable from `kb_articles`
    - version-aware (keyed by KB publish/version) or otherwise invalidated on publish
    - compatible with existing publish/refresh flows that update `kb_meta.kb_version`

#### b. API / Interfaces

- **Hub internal retrieval interface**: retrieval results should carry enough information to support:
  - per-item contribution metadata (lexical rank/score, vector rank/score, fused score/rank)
  - stable evidence identifier (`kb_articles.id` / the same identifier currently logged as `query_logs.source_id`)
- **No required kiosk contract change** for basic operation, but logging/payload plumbing should support future explainability/debug views.

#### c. UX / Behavior

- User-facing behavior should improve for exact-term queries (building names, clinic names, procedures).
- In ambiguous cases, this goal does not replace clarification (Goal 6); it only improves retrieval quality under the existing flow.

---

### 6) Integration Points

- **Depends on**:
  - KB publish/versioning (`kb_meta.kb_version`, `system_version.kb_version`) for reproducible ranking and index invalidation.
- **Affects**:
  - Goal 5 (multi-path): fusion and attribution must work per-path (or at least be extendable to).
  - Goal 7 (filtering): lexical retrieval must obey the same filtering rules as vector retrieval.
  - Goal 10 (metrics/logging): needs per-path and fusion observability.
  - Goal 11 (caching): cache keys should include KB version; cached answers should not outlive index/version changes.
  - Goal 12 (pipeline order): hybrid retrieval should be invoked after normalization/intent and after clarification when applicable.

---

### 7) Edge Cases / Failure Modes

- **Lexical index missing/stale**:
  - expected behavior: fail closed to vector-only retrieval (or a safe degraded mode) and log the degradation with KB version and reason.
- **Zero results from lexical path**:
  - expected behavior: vector path still returns results; fusion must handle empty side deterministically.
- **Conflicting rankings** (lexical top differs from vector top):
  - expected behavior: fusion strategy must be explicit and logged; tie-break rules must be stable.
- **Over-filtering** (when Goal 7 is applied):
  - expected behavior: deterministic widening order is owned by Goal 7; Goal 4 must not bypass hard rules.

---

### 8) Logging & Metrics

At minimum, log enough to reproduce and debug the hybrid decision for a given query:

- `query_logs` (existing fields used where possible):
  - normalized query (`query_logs.normalized_transcript`)
  - KB version (`query_logs.kb_version`)
  - top evidence id (`query_logs.source_id`) and score (`query_logs.retrieval_score`)
- Hybrid-specific (new fields or structured payload logged alongside query logs; exact storage TBD):
  - lexical retrieval: top-k IDs + lexical scores/ranks + candidate count
  - vector retrieval: top-k IDs + vector scores/ranks + candidate count
  - fusion: strategy name + parameters (e.g., RRF k) + fused top-k
  - tie-break decisions (when equal)

---

### 9) Determinism / Constraints

- **Stable ranking**: fixed KB version/config + fixed normalized query + fixed filters ⇒ reproducible top-k ordering.
- **Tie-break rules**: define a stable secondary sort for equal fused scores (e.g., `(fused_score desc, kb_articles.id asc)`).
- **Version constraints**: the lexical index must correspond to the same published KB version used by vector embeddings.

---

### 10) Definition of Done (DoD)

- Lexical retrieval path exists and returns top-k candidates from the KB for English queries.
- Hybrid fusion produces a single ranked list with explicit, logged strategy and stable ordering.
- Hybrid retrieval is reproducible for a fixed KB version/config and has deterministic tie-breaks.
- Logs allow attributing each returned evidence item to lexical/vector contributions and fusion outcome.
- Publish/version change invalidates or rebuilds the lexical index so stale results are not served.

---

### 11) Open Decisions

- Lexical implementation choice (e.g., SQLite FTS vs external index) based on deployment constraints and existing code patterns.
- Which KB fields are indexed lexically (minimum: question + tags; confirm whether `answer` is intentionally excluded as it is for embeddings).
- Exact fusion strategy and parameters (RRF vs weighted score normalization vs other), including how to treat feedback-adjusted ranking (if enabled) in relation to fusion.

---

## Evaluation / Benchmark Plan

### Dataset (minimum viable)

- A small, versioned set of test queries with expected top results:
  - exact proper nouns (building/clinic names)
  - procedural terms (registration steps, first aid terms)
  - mixed queries (exact term + descriptive context)

### Metrics

- **Top-k accuracy** on the curated set (e.g., whether expected `kb_articles.id` appears in top-3/top-5).
- **Stability**: repeated runs on same KB version/config produce identical top-k ordering.
- **Latency**: retrieve-only time (and overall time if already tracked) before vs after hybrid.

### Regression criteria

- No regression beyond a defined threshold on baseline semantic queries while improving exact-term query performance.
- Determinism checks pass (identical ordering) for the fixed evaluation snapshot.

