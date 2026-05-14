# Goal 5 — Multi-path (split/dual) retrieval for compound queries

### 1) Outcome

Implement **multi-path retrieval** for compound queries by **splitting** a request into multiple intent-scoped retrieval sub-queries, running retrieval per sub-query, then **merging** results with explicit priority + determinism.

- **What changes**: compound handling shifts from “single enriched query → single retrieval” to “multiple intent-scoped queries → multiple retrieval passes → deterministic merge”.
- **Who benefits**: residents (more complete and correct handling of multi-part asks), operators (predictable behavior for urgent cases), maintainers (inspectable evidence attribution per path).
- **What success looks like**:
  - compound queries return evidence that clearly covers each sub-intent (medical + location + safety, etc.)
  - the system produces consistent “primary vs secondary” outputs under the same KB version/config
  - logs can show which retrieval path produced each evidence item and why it was chosen

---

### 2) Why this matters

- **Current limitation**: compound queries are effectively “flattened” into one search string, which can cause one sub-intent to dominate retrieval and suppress critical evidence (especially medical/safety).
- **Risk addressed**: incomplete or wrong prioritization in emergencies (e.g., location info returned without medical safety guidance, or vice versa).
- **Value**: multi-path retrieval makes the system’s reasoning auditable, supports clear intent priority rules, and sets up reliable behavior for clarification + filtering + metrics.

---

### 3) Scope

- Define what counts as a **compound** query and how it is **decomposed** into retrieval paths (minimum viable: top-2 intents already produced by intent classification).
- For each retrieval path:
  - build a **path query** (normalized + intent-specific enrichment/rewrite constraints as applicable)
  - run retrieval (vector-only initially; must remain compatible with Goal 4 hybrid retrieval when enabled)
  - capture a path-local top-k with scores + evidence IDs
- Implement **deterministic merge**:
  - choose a **primary path** (priority rules; safety/medical must be expressible)
  - merge evidence lists via an explicit strategy (e.g., priority-first + deterministic dedupe, and/or RRF across paths)
  - enforce stable tie-breaks
- Implement **evidence attribution**:
  - every returned evidence item includes its producing path/intent and position/score within that path (and, if fused, the merge score/position)
- Ensure compatibility with:
  - Goal 7 filtering policy (filters must be applied consistently per path)
  - Goal 10 logging/metrics (path-level observability)
  - Goal 12 pipeline order (normalize → intent → optional clarification → constrained rewrite)

---

### 4) Non-goals

- Full planner/agent execution (tool use, multi-step action graphs).
- LLM-based decomposition in the hot path (use deterministic classifier outputs + rules this increment).
- Arbitrary “N-path” fanout for many intents; start with a bounded number of paths (minimum viable: 2).
- Cross-encoder reranking as a requirement (Goal 9 explicitly avoids heavy reranking this increment).

---

### 5) System Impact

#### a. Data / Schema

- **No new KB schema required** specifically for multi-path retrieval.
- **Logging additions** are expected (Goal 10) to represent:
  - per-path query text (normalized + intent-enriched form)
  - per-path top-k evidence IDs + ranks/scores
  - merge strategy + parameters and final ranked outputs

#### b. API / Interfaces

- Hub → kiosk response must be able to represent:
  - multiple intents/paths considered (at least top-2)
  - evidence items with **path attribution**
  - optional “secondary guidance” / follow-up prompts/actions derived from non-primary paths (e.g., “Also: nearest medical desk is …”)

#### c. UX / Behavior

- For urgent/safety-relevant compounds, the kiosk experience should be able to:
  - present a **primary** answer (safety/medical prioritized when indicated)
  - present **secondary** guidance without burying critical instructions
  - optionally offer an escalation action *only if it already exists elsewhere in the kiosk UX* (Goal 5 does not introduce a new escalation product surface)

---

### 6) Integration Points

- **Depends on**:
  - intent classification outputs that can identify at least top-2 intents (existing behavior)
- **Affects**:
  - Goal 4 (hybrid retrieval): each path must be able to run hybrid and produce fusion metadata
  - Goal 6 (clarification): compound + unclear cases must remain compatible with “clarify before rewrite”
  - Goal 7 (filtering policy): filters must apply per path consistently and be logged
  - Goal 10 (metrics/logging): adds path attribution; enables per-intent evaluation
  - Goal 11 (caching): cache keys must incorporate resolved compound structure (paths + filters + KB version)
  - Goal 12 (pipeline order): decomposition must occur after intent detection (and after clarification when required)

---

### 7) Edge Cases / Failure Modes

- **One path returns zero candidates**: still return results from the other path; log empty path deterministically.
- **Duplicate evidence across paths**: deterministic dedupe rule (e.g., keep the higher-priority path attribution, log that it appeared in multiple paths).
- **Conflicting intent signals**: apply priority policy; if too ambiguous, trigger clarification (Goal 6) rather than guessing.
- **Merge instability**: tie-break rules must be explicit (e.g., priority, then merged score, then stable evidence ID).
- **Path explosion**: cap number of paths (bounded fanout); log truncation when more are detected.

---

### 8) Logging & Metrics

Minimum logging to make multi-path explainable and evaluable:

- normalized query, KB version
- detected intents (at least top-2) + confidences
- for each path:
  - path intent label
  - path query text (post-normalize, post-constraints)
  - applied filters (per Goal 7)
  - top-k evidence IDs + ranks/scores and candidate counts
- merge:
  - merge strategy name + parameters
  - final returned evidence IDs + final ranks/scores
  - per-evidence attribution: `{ evidence_id, producing_intent, producing_path_rank, merged_rank }`

---

### 9) Determinism / Constraints

- Fixed KB version/config + same normalized query + same resolved intent set + same filters ⇒ reproducible path top-k and merged ordering.
- Merge must specify stable tie-breaks (example: `(priority desc, merged_score desc, evidence_id asc)`).
- Safety constraints must be representable via deterministic priority rules (see Policy/Rules module below).

---

### 10) Definition of Done (DoD)

- Compound queries execute at least **two** retrieval paths (top-2 intents) and merge deterministically.
- Each returned evidence item is attributable to a specific retrieval path/intent in logs (and in the response contract if needed).
- Merge strategy and tie-breaks are explicit and logged.
- Handles zero-results and duplicate-evidence cases deterministically.
- Works with vector-only retrieval and remains compatible with enabling hybrid retrieval (Goal 4) and filtering (Goal 7).

---

### 11) Open Decisions

- Exact decomposition rule: intent top-2 only vs allowing a small bounded set (top-3) when confidence is high.
- Merge strategy: strict priority-first vs RRF across paths vs hybrid (priority bucket + RRF within bucket).
- How “urgency / SOS offer” is detected and represented (rule-based vs intent-level signals; ensure it’s logged).
- Response UX contract for “secondary outputs” (inline vs separate section vs action chips).

---

## Policy / Rules (optional module; recommended for Goal 5)

### Decomposition (minimum viable)

- If request is marked compound (top-2 intents are both above threshold), create two paths:
  - Path A: intent 1
  - Path B: intent 2
- Each path produces its own retrieval query and retrieval result list (top-k).

### Priority (minimum viable)

- Safety/medical-relevant intents must be eligible to become **primary** when present.
- Priority must be deterministic and logged (e.g., “medical > safety > shelter ops > general info”, exact ordering to be finalized in Open Decisions).

### Dedupe rule (minimum viable)

- Evidence duplicates across paths are merged deterministically and retain the chosen primary attribution (log that it was multi-path-visible).

---

## Contract / Payload Shape (optional module; recommended for Goal 5)

Minimum viable additions to represent multi-path results:

- Return detected intents (top-2) with confidences.
- Return evidence items including producing intent/path attribution.
- If secondary guidance is presented, represent it explicitly rather than burying it in unstructured text.

