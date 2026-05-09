# Goal 10 — MVP metrics + logging for grounding, evidence match, and latency

### 1) Outcome

Implement **minimum viable metrics + logging** so we can objectively measure:

- grounding (supported-by-evidence rate)
- evidence match & stability (which evidence was used, and whether it stays stable per KB version/config)
- latency breakdown (at least retrieval vs overall; expand as feasible)

- **What changes**: the hub records structured, query-attributable events/fields (not just free-text) that enable repeatable evaluation.
- **Who benefits**: maintainers (regression detection), stakeholders (readiness visibility), residents (higher-quality answers over time).
- **What success looks like**:
  - logs support metric computation **per KB version, intent, and modality**
  - we can reproduce “what happened” for a single query (normalization → intent → clarification → rewrite → retrieval → response)
  - latency can be broken down into at least **retrieve latency** and **overall latency**, with room for additional stages

---

### 2) Why this matters

- **Current limitation**: `query_logs` has basic fields (including `latency_ms`), but MVP instrumentation is not complete for evaluation (grounding/evidence match/stability/latency breakdown).
- **Risk addressed**: without metrics, retrieval/model changes become subjective; regressions are hard to detect and debug.
- **Value**: enables safe iteration on Goals 4–9 and validates Goal 12’s pipeline ordering by making each step observable.

---

### 3) Scope

Minimum viable instrumentation must cover:

- **Evidence IDs + scores**
  - record the final returned evidence list with stable IDs
  - record retrieval scores and any fusion/merge metadata when applicable (hybrid / multi-path)
- **Pipeline step observability**
  - normalized query
  - intent label(s) + confidence
  - clarification triggered? options shown? resolution (selected option) when used
  - constrained rewrite input/output (when rewrite is performed) and constraints applied
- **Latency breakdown**
  - at minimum: retrieval time vs overall request time
  - where feasible: separate timings for normalize, intent, clarification, rewrite, retrieval, response synthesis
- **Metric-enabling fields**
  - grounded/support rate inputs (at least enough to support sampled/manual review; optional offline checks)
  - hallucination proxy inputs (unsupported spans vs retrieved evidence — MVP can be rule-based or offline batch)
  - evidence match/stability inputs (top evidence IDs, rank positions, and deltas between retrieval paths/fusion if present)

This goal includes defining the **event/field schema** and implementing instrumentation at key hub integration points (routes + retrieval + rewrite/clarification) so the data is persisted and queryable.

---

### 4) Non-goals

- Building a full analytics dashboard UI this increment (export/query is sufficient for MVP).
- Running LLM-as-judge in the hot path (allowed only as **offline/batch** support).
- Perfect grounding detection; MVP focuses on **capturing evidence + structure** needed to compute proxies and sampled/manual labels.
- Introducing heavy observability infrastructure unless already part of repo constraints.

---

### 5) System Impact

#### a. Data / Schema

**Existing (confirmed tables referenced by this increment doc)**

- `query_logs` (includes `latency_ms` and `kb_version`)
- `feedback_logs` (per interaction)
- `clarification_resolutions` (clarification analytics)
- KB versioning: `kb_meta.kb_version`, `system_version.kb_version`

**New / extended (required by this goal)**

- Extend `query_logs` and/or add closely related log storage to capture, per query:
  - **normalized query**
  - **intent output**: label(s) + confidence(s); compound marker when applicable
  - **clarification**: triggered boolean; option IDs/labels shown; selected option ID/label (if resolved)
  - **rewrite**: whether applied; constrained rewrite output; constraints applied (by name/ID if defined elsewhere)
  - **retrieval**:
    - final returned evidence IDs (stable IDs) + ranks + scores
    - per-path attribution when multi-path is enabled (Goal 5)
    - lexical vs vector contributions and fusion details when hybrid is enabled (Goal 4)
    - applied filters and widening/fallback steps when filtering policy is enabled (Goal 7)
  - **latency**:
    - overall latency
    - retrieval latency (minimum)
    - optional per-stage timings where feasible

Design constraint for MVP: **prefer additive fields** and avoid schema changes that require a large migration surface area unless necessary.

#### b. API / Interfaces

- Ensure hub → kiosk responses can be associated to a **single query log record** (stable query/session identifiers) so feedback and audits can join correctly.
- Internal contracts should carry:
  - stable evidence IDs (and modality where applicable)
  - retrieval scores (and fusion/path metadata when applicable)
  - any “decision flags” (clarification triggered, fallback used, cache hit/miss if Goal 11 is active)

#### c. UX / Behavior

- No new kiosk UX is required for MVP beyond what Goals 6/7 already introduce.
- Where feedback UX exists (thumbs/etc.), ensure it links to the same query/session identifiers recorded in logs.

---

### 6) Integration Points

- **Depends on**:
  - Goal 12 pipeline order (normalize → intent → optional clarification → constrained rewrite) to define event ordering
  - Existing KB versioning (`kb_meta.kb_version`, `system_version.kb_version`) for metric slicing and stability checks
- **Affects**:
  - Goal 4 (hybrid retrieval): requires lexical/vector/fusion logging for analysis
  - Goal 5 (multi-path): requires per-path attribution to evaluate compound handling
  - Goal 6 (clarification): requires logging triggers/options/resolutions
  - Goal 7 (filtering policy): requires logging applied filters and widening/fallback reasons
  - Goal 11 (caching): requires cache hit/miss + key factors to be observable (if caching is added)

---

### 7) Edge Cases / Failure Modes

- **Partial logs** (exception mid-pipeline): record a failure status and whatever stage data is available; avoid silent drops.
- **Missing evidence IDs**: if response is returned without evidence references, log an explicit reason code (e.g., “no_results”, “fallback_message”, “error”).
- **Multi-path / hybrid complexity**: ensure logging remains bounded (cap top-k lists; log truncation deterministically).
- **PII risk**: avoid logging raw user text beyond what is needed for debugging; prefer normalized/processed forms and stable identifiers where possible.
- **Offline/unavailable services**: stage timing should degrade gracefully (missing stages logged as null/absent, not misleading zeros).

---

### 8) Logging & Metrics

#### Minimum logging events/fields (MVP)

- **Query identity**
  - `session_id` / request ID
  - timestamp
  - `kb_version`
- **Pipeline**
  - normalized query string
  - intent label(s) + confidence(s)
  - clarification: triggered? options shown? selected option?
  - rewrite: triggered? constrained output? constraints applied?
- **Retrieval**
  - final evidence IDs + ranks + scores
  - candidate counts (pre/post filtering, when filters are applied)
  - hybrid details (lexical top-k + vector top-k + fusion strategy/params) when enabled
  - multi-path details (per-path evidence lists + merge strategy/params) when enabled
- **Latency**
  - overall latency (existing `latency_ms` or equivalent)
  - retrieval latency (new field if not present)
  - optional: per-stage timings (normalize/intent/clarify/rewrite/retrieve/respond)
- **Outcome**
  - success/failure status
  - “no results” / fallback reason when applicable

#### MVP metrics enabled by the logs

- **Grounded answer rate**: sampled/manual (and optional offline checks) using stored evidence IDs + retrieved text references.
- **Hallucination proxy**: unsupported spans vs retrieved evidence (MVP computed offline or rule-based).
- **Evidence match & stability**:
  - evidence ID agreement across runs for the same (normalized query, KB version, config)
  - top-1 / top-k stability deltas when enabling/disabling hybrid, filtering, feedback bias, etc.
- **Latency**:
  - p50/p95 overall
  - p50/p95 retrieval
  - stage breakdown where available

---

### 9) Determinism / Constraints

- For a fixed KB version/config, logs must be sufficient to **replay/debug** the retrieval decision:
  - normalized query
  - applied filters and precedence decisions (when enabled)
  - evidence lists with stable IDs and scores/ranks
- Ensure logging does not introduce nondeterministic identifiers that block joining (use stable IDs, not ephemeral object addresses).
- Keep payload sizes bounded (cap stored top-k; log truncation explicitly).

---

### 10) Definition of Done (DoD)

- Query logs capture enough structure to compute metrics **per KB version, intent, and modality**.
- Each query records:
  - normalized query
  - intent output (label + confidence; top-2 when compound is used)
  - clarification trigger + resolution details when applicable
  - constrained rewrite output when rewrite is used
  - returned evidence IDs + scores/ranks
  - overall latency and at least retrieval latency
- Hybrid/multi-path/filtering decisions (when enabled) are logged with sufficient detail to attribute evidence to path/fusion/filtering.
- A minimal evaluation workflow exists:
  - a small query set
  - a way to capture labels/notes (via `feedback_logs` and/or manual review process)
  - a repeatable way to compute or export summary metrics (script or query)

---

### 11) Open Decisions

- Where to store structured “per-path / per-stage / per-evidence” logging:
  - additional columns on `query_logs` vs a related log table keyed by `query_logs.id`
- Minimum viable representation for “hallucination proxy” inputs (what spans/fields to persist vs compute offline).
- The exact privacy/retention policy for storing normalized query text and intermediate artifacts (rewrite outputs, clarification options).

---

## Evaluation / Benchmark Plan (optional module; recommended for Goal 10)

- Define a **small fixed query set** that covers:
  - exact-term queries (hybrid relevance)
  - compound queries (multi-path attribution)
  - unclear queries (clarification logging)
  - safety/medical queries (policy-sensitive flows)
- For each query, record:
  - expected primary evidence IDs (where feasible)
  - whether the answer is supported (manual label)
  - latency expectations (baseline p50/p95)
- Regression criteria (MVP):
  - evidence ID stability does not degrade for fixed KB version/config
  - no increase in unsupported-answer rate on the labeled set
  - latency does not regress beyond an agreed threshold

