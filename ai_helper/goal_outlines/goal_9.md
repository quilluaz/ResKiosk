# Goal 9 — Retrieval quality improvements without heavy reranking (keep feedback bias; focus on retrieval stack)

### 1) Outcome

Improve retrieval quality **without adding a heavy reranker (e.g., cross-encoder) this increment**, by keeping the existing **feedback-adjusted ranking (bias)** as an explicit, tunable layer and relying on the retrieval architecture improvements delivered in Goals 4–6.

- **What changes**: quality gains come from hybrid + multi-path + clarification + constrained rewrite, with feedback bias applied as a separate, controlled signal (not a reranker).
- **Who benefits**: residents (more relevant evidence/answers), operators (predictable behavior), maintainers (tunable + explainable ranking shifts).
- **What success looks like**:
  - precision improves on an evaluation set compared to the pre-Goal-4 baseline
  - bias impact is measurable, bounded, and can be enabled/disabled
  - when bias is enabled, ranking remains reproducible given a fixed KB version/config **and a fixed bias state**

---

### 2) Why this matters

- **Current limitation**: the current “RLHF” mechanism is a **scalar bias** adjustment on retrieval scores (feedback-adjusted ranking), not a true reranker; quality improvements should primarily come from retrieval architecture changes.
- **Risk addressed**: adding a heavy reranker in the hot path increases latency/complexity and makes failures harder to debug, before we have baseline observability and safer interaction flow.
- **Value**: this goal preserves the ability to incorporate feedback while keeping the increment focused on high-leverage, auditable improvements from Goals 4–6.

---

### 3) Scope

- Keep **feedback-adjusted ranking** as a distinct layer applied to retrieval candidates (post-retrieval, pre-final ranking output).
- Ensure feedback bias works with:
  - **hybrid retrieval** output (Goal 4)
  - **multi-path** output and merge (Goal 5)
  - **clarification-before-rewrite** flow (Goal 6) and pipeline order (Goal 12)
- Calibrate/tune bias-related parameters and gating against the new retrieval stack outputs (hybrid + multi-path), including:
  - safe ranges / caps for how much bias can move an item
  - rules for when bias is applied (enabled flag, intent gates if needed)
  - deterministic tie-break rules after bias is applied
- Add monitoring/logging to measure bias impact versus baseline rankings (raw vector / hybrid / multi-path without bias).

---

### 4) Non-goals

- Introducing a cross-encoder reranker or LLM reranking in the hot path.
- Online RL training / policy optimization (this goal keeps “feedback bias” as a scoring adjustment layer only).
- Expanding feedback into a general “learning to rank” framework this increment.

---

### 5) System Impact

#### a. Data / Schema

- **No new KB schema required** specifically for this goal.
- Feedback bias source of truth remains the existing bias storage (e.g., `article_biases`) and should be treated as a **versioned/timestamped state** for reproducibility.
- If bias state is mutable over time, logs must capture enough identifiers to reproduce the decision (see Logging & Metrics).

#### b. API / Interfaces

- Retrieval/ranking internals should be able to represent (at least in logs; optionally in internal payloads):
  - baseline scores/ranks (pre-bias)
  - bias contribution
  - post-bias scores/ranks
  - whether bias was enabled and which configuration was used

#### c. UX / Behavior

- Resident-facing behavior should remain consistent with safety/clarification policy:
  - bias must not bypass hard rules/filters (Goal 7) or clarification flow (Goal 6)
  - any “learning” effect should not create surprising behavior shifts without being observable in metrics/logs

---

### 6) Integration Points

- **Depends on**:
  - Goal 4 (hybrid retrieval) and Goal 5 (multi-path) as the primary sources of retrieval quality gains
  - Goal 10 (metrics/logging) to measure changes and prevent regressions
- **Affects**:
  - Goal 11 (caching): cache keys/validity may need to incorporate bias enablement and (if applicable) bias state versioning
  - Goal 12 (pipeline order): bias should apply after the canonical pipeline produces the final retrieval candidates for ranking

---

### 7) Edge Cases / Failure Modes

- **Bias table missing/unavailable**: fall back to baseline ranking; log “bias unavailable” deterministically.
- **Bias enabled but stale/partial**: apply only available bias entries; log coverage (how many candidates had bias entries).
- **Bias overwhelms retrieval evidence**: enforce caps/guards so bias cannot move low-relevance items into the top results beyond defined limits; log when caps trigger.
- **Non-determinism due to mutable bias**: if bias changes over time, ensure the decision is reproducible by logging bias state identifiers (or snapshot/version) used for the request.

---

### 8) Logging & Metrics

Minimum requirements to make bias impact measurable and safe:

- **Bias status**:
  - bias enabled/disabled flag
  - bias configuration parameters (e.g., alpha/scale, caps)
  - bias state identifier (timestamp/version/snapshot ID) sufficient for reproducibility
- **Impact measurement (per request)**:
  - top-k before bias vs after bias (IDs + ranks/scores)
  - count of rank changes in top-k (and whether top-1 changed)
  - per-item: `{ evidence_id, baseline_score/rank, bias_value, post_bias_score/rank }` (bounded to top-k for size)
- **Regression metrics** (aggregated over an eval set / time):
  - top-1 / top-k accuracy vs baseline
  - “bias-caused flip rate” (how often bias changes top-1 or materially reorders top-k)
  - latency impact (ensure bias layer does not add meaningful latency)

---

### 9) Determinism / Constraints

- For a fixed KB version/config and fixed normalized query + filters + resolved intents/paths:
  - **bias disabled** ⇒ deterministic ranking as defined by Goals 4–5 merge + tie-break rules
  - **bias enabled** ⇒ deterministic ranking given a **fixed bias state** and explicit tie-break rules (e.g., `(final_score desc, evidence_id asc)`)
- Bias must not violate hard filtering/precedence rules (Goal 7).

---

### 10) Definition of Done (DoD)

- Feedback-adjusted ranking remains a **separate, explicit** layer that can be enabled/disabled.
- Bias layer works correctly with hybrid and multi-path retrieval outputs and does not break determinism guarantees.
- Logs allow:
  - reproducing a decision (including bias state/config)
  - quantifying bias impact (top-1/top-k changes vs baseline)
- A small evaluation set/workflow exists to compare baseline vs bias-enabled ranking quality (offline evaluation is acceptable this goal).

---

### 11) Open Decisions

- What is the authoritative “bias state identifier” for reproducibility (e.g., updated_at cutoff, snapshot version, or explicit bias_version)?
- What caps/guards should apply to prevent bias from overpowering relevance (global cap vs intent-specific cap)?
- Where bias is applied in the ranking stack when multi-path is enabled:
  - per-path before merge, after merge, or both (pick one minimum viable and log it)
- How bias interacts with caching keys in Goal 11 (include enabled flag only vs include bias state versioning).

---

## Evaluation / Benchmark Plan (optional module; recommended for Goal 9)

- Curate a small evaluation set representing:
  - exact-term queries (hybrid benefit)
  - compound queries (multi-path benefit)
  - ambiguous queries that trigger clarification
- Compare:
  - baseline (no bias) vs bias-enabled rankings
  - “flip rate” for top-1 and stability of top-k ordering
- Define pass/fail thresholds for:
  - minimum precision lift without heavy reranking
  - maximum allowed bias-driven top-1 flip rate in safety/medical intents (if applicable)

