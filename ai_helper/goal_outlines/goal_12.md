# Goal 12 — Canonical pipeline order (normalize → intent → optional clarification → constrained rewrite → retrieval)

### 1) Outcome

Enforce the canonical hub pipeline order:

**normalize → intent → (optional) clarification → constrained rewrite → retrieval**

- **What changes**: ordering becomes an explicit, enforceable requirement (not “whatever runs first”), and each step’s outputs are captured for debugging and evaluation.
- **Who benefits**: residents (safer, less confusing behavior), operators (more predictable UX), maintainers (auditable logs and reproducible behavior).
- **What success looks like**:
  - clarification (when triggered) occurs **before** any rewrite that could change scope
  - rewrites respect constraints / hard rules and do not expand into disallowed topics
  - logs contain normalized query, detected intent, clarification (if any), and rewrite inputs/outputs in a reproducible way

---

### 2) Why this matters

- **Current limitation**: normalization/intent/rewrite exist, but the **ordering and constraints are not enforced** as a product requirement.
- **Risk addressed**: rewriting too early can expand or distort the user’s meaning, bypass clarification, and increase unsafe or irrelevant retrieval (especially for medical/safety).
- **Value**: correct ordering reduces ambiguity, improves retrieval quality (hybrid + multi-path), and makes behavior measurable (Goal 10) and cacheable safely (Goal 11).

#### Current codebase reality (for alignment)

Today’s hub pipeline is **not** the canonical order yet:

- `hub/retrieval/search.py:retrieve()` performs **normalize → intent → retrieval → needs_clarification gating**.
- `hub/retrieval/rewriter.py` is only invoked **after an initial retrieval attempt** (via the query route), and only in specific low-confidence cases behind `RESKIOSK_QUERY_REWRITE`.

This goal is the spec for restructuring so clarification becomes a true **hard gate** and rewrite happens **before** the retrieval attempt that “counts” for the resident-facing answer (and for logging/metrics determinism).

---

### 3) Scope

- Make the pipeline order **canonical and enforced** for every hub request that reaches retrieval:
  - normalization happens first
  - intent classification runs on the normalized query
  - clarification decision happens after intent (and after initial retrieval signals if that is part of the trigger), and if clarification is required the pipeline stops and returns clarification options
  - rewrite happens only after clarification is resolved (or explicitly skipped), and must be constrained
  - retrieval executes only after the constrained rewrite stage completes (or is safely skipped/falls back)
- Ensure rewrite is **constrained** by:
  - hard system rules (do not invent topics, do not override hard safety constraints)
  - resolved intent (and/or selected clarification choice when present)
  - any explicit user UI constraints (if applicable)
- Add minimum viable logging to make each step auditable and reproducible (see Logging & Metrics).
- Keep behavior compatible with:
  - Goal 6 clarification UX (chips)
  - Goal 7 filtering policy precedence (hard rules > UI > inferred)
  - Goal 4/5 retrieval improvements (hybrid + multi-path)

---

### 4) Non-goals

- Replacing the existing intent classifier with a new model.
- Adding new clarification UX patterns beyond what Goal 6 specifies.
- Introducing an LLM planner/agent loop or multi-step tool execution.
- Implementing semantic chunking (retrieval unit remains a `kb_articles` row this increment).

---

### 5) System Impact

#### a. Data / Schema

- **No new core KB schema required** for this goal.
- Expect **logging/event schema additions** (likely in or alongside `query_logs`) so we can store:
  - normalized query
  - detected intent (+ confidence, if available)
  - clarification state (triggered? selected option? resolved intent/category)
  - rewrite constraints + rewrite output (or a stable hash of these if storage needs to be bounded)

#### b. API / Interfaces

- Hub → kiosk should be able to return a **clarification response** that cleanly stops the pipeline before rewrite/retrieve continues (Goal 6).
- Kiosk → hub follow-up should carry the **clarification selection** so the pipeline can resume deterministically.
- Internal interfaces should surface (and logs must capture) step outputs needed to reproduce behavior across a fixed KB version/config.

#### c. UX / Behavior

- If clarification triggers, the kiosk should present 2–3 fast choices (chips) and the hub should **not** proceed to rewrite until the user selects one.
- For non-clarification cases, the user experience should remain fast; rewrite is used only to improve retrieval robustness, not to alter the user’s intent.

---

### 6) Integration Points

- **Depends on**:
  - Goal 6 (clarification flow + resolution logging)
  - Goal 10 (metrics/logging) for consistent event fields and analysis
- **Affects**:
  - Goal 4/5 retrieval (pipeline produces the query forms retrieval uses; ordering affects quality)
  - Goal 7 filtering (intent + clarification selection feed inferred constraints; must not be bypassed)
  - Goal 11 caching (cache keys should incorporate the resolved pipeline state, not raw user text only)

---

### 7) Edge Cases / Failure Modes

- **Ambiguous input**: if intent is unclear and the clarification trigger fires, return clarification without rewrite; log the trigger inputs deterministically.
- **Clarification suppressed incorrectly**: if the system proceeds without clarification in a case that would normally trigger it, log why (e.g., “compound shortcut”, thresholds).
- **Rewrite expands scope**: enforce constraints; if rewrite cannot comply, fall back to using the normalized query (or a safe minimal rewrite) and log the fallback.
- **Non-English input**: ensure ordering respects the global assumption that translation to English happens upstream of retrieval; the pipeline should operate at the retrieval boundary consistently.
- **Compound queries**: ensure clarification (when applicable) still occurs before rewrite and before any multi-path decomposition that depends on intent confidence.

---

### 8) Logging & Metrics

Minimum viable logging to support observability and reproducibility:

- **Inputs**:
  - raw user text (or a stable reference if raw is not stored)
  - normalized query
  - language at the retrieval boundary (English) if tracked
  - KB version / system version references already used for auditability
- **Intent step**:
  - detected intent label(s) + confidence(s)
- **Clarification step**:
  - clarification triggered? (bool)
  - trigger reasons/threshold values used (as bounded enums/fields)
  - clarification options returned (IDs/labels)
  - user selection + resolved intent/category (when selected)
- **Rewrite step**:
  - constraints applied (intent + selected clarification + hard rule flags)
  - rewrite output (or hash) and any fallback reason
- **Timing**:
  - step latency breakdown (normalize/intent/clarify/rewrite/retrieve) where feasible

---

### 9) Determinism / Constraints

- For a fixed KB version/config and the same normalized query + same clarification selection, pipeline outputs should be **reproducible**.
- Clarification must be a **hard gate**: if it triggers, rewrite must not run until clarification is resolved.
- Rewrite must be **constrained** (no topic expansion) and must not violate hard rules (safety/medical constraints, enabled/status gating, etc.).

---

### 10) Definition of Done (DoD)

- Pipeline order is enforced end-to-end as: normalize → intent → optional clarification → constrained rewrite.
- Clarification, when triggered, occurs before rewrite and blocks the rest of the pipeline until resolved.
- Rewrite constraints are enforced; non-compliant rewrites fall back safely and are logged.
- Logs include normalized query, intent, clarification (if any), and rewrite inputs/outputs sufficient to reproduce the decision.

---

### 11) Open Decisions

- Exact “clarification trigger” definition once the pipeline is strictly ordered (e.g., based on intent confidence, retrieval score floor, and/or ambiguity signals).
- How rewrite constraints are represented (structured flags vs taxonomy IDs vs both) and what minimal set is required for safety-critical intents.
- Whether to store full rewrite text vs storing a bounded representation (e.g., hashes + key fields) to control log size.

---

## Policy / Rules (optional module; minimal for Goal 12)

### Canonical ordering (authoritative)

1. **Normalize** input to the retrieval boundary form.
2. **Classify intent** on the normalized query.
3. **Clarify (optional)** if triggers indicate ambiguity/low-confidence; if triggered, return chips and stop.
4. **Rewrite (constrained)** using the resolved intent/selection and hard rules; then proceed to retrieval.

### Rewrite constraints (minimum viable)

- Must not introduce new topics/entities not present in the user’s request or chosen clarification.
- Must preserve safety/medical scope when those intents are present (do not “soften” or redirect).
- Must remain compatible with downstream filtering policy (hard rules > UI > inferred).
