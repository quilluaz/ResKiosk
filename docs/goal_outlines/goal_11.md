# Goal 11 — Safer caching patterns (version + TTL + refresh hooks)

### 1) Outcome

Implement **safe, observable caching** for retrieval/answer responses so the kiosk is faster **without serving outdated or unsafe results**.

- **What changes**: introduce response-level caching keyed by normalized query + resolved request context and **scoped to KB/config versions**, with TTL and explicit invalidation/refresh hooks.
- **Who benefits**: residents (faster responses without stale guidance), admins (publishes take effect quickly), maintainers (auditable cache behavior).
- **What success looks like**:
  - cached responses are never served across **KB version** boundaries
  - cache behavior is observable (hit/miss, bypass, invalidation reasons)
  - publish/config updates trigger deterministic invalidation (or safe refresh) quickly

---

### 2) Why this matters

- **Current limitation**: caches exist for corpus/config in-memory, but **response-level caching** is not implemented as a product goal.
- **Risk addressed**: caching the wrong thing can amplify harm—**a fast wrong answer is worse than a slow correct answer**, especially after a KB publish.
- **Value**: carefully keyed + invalidated caches reduce latency while preserving safety and reproducibility (and improve UX under constrained conditions).

---

### 3) Scope

- Define **cacheable artifacts** (minimum viable):
  - retrieval/answer response objects returned to kiosk/hub callers
- Define **cache keys** that incorporate:
  - normalized query text
  - resolved intent (including compound structure where applicable)
  - applied filters (UI + inferred + hard rules, as applicable)
  - **KB version**
  - relevant **config version** (or a stable config hash/version identifier)
- Define a **TTL policy** (minimum viable: short TTL + safe defaults; per-intent overrides allowed if already modeled).
- Implement **publish/config update invalidation hooks** so cached entries are not served after:
  - KB publish increments version
  - relevant config changes are applied (shelter/runtime config)
- Add minimal **observability** for cache decisions (hit/miss/bypass and why).
- Optional (but in-scope if feasible): a **lightweight re-validation check** for safety-critical intents before serving a cached response (e.g., compare top evidence IDs against a quick fresh retrieval under the same constraints).

---

### 4) Non-goals

- Distributed cache cluster rollout (e.g., Redis) unless already required by repo constraints.
- Long-term persistence of cached responses across process restarts.
- Using “other sessions’ thumbs” / feedback as the primary correctness signal for cached responses.
- A complex cache warm-up system or precompute pipeline.

---

### 5) System Impact

#### a. Data / Schema

- **No new KB schema required**.
- If cache event logs require persistence beyond existing logs, add minimal fields/events to support:
  - cache key components (or a hashed cache key)
  - hit/miss/bypass
  - TTL used
  - invalidation trigger reason (KB publish vs config update vs TTL expiry)

#### b. API / Interfaces

- Cache keys must be computed from **post-normalize** and **post-resolution** inputs:
  - normalized query
  - intent / compound resolution
  - applied filters
  - KB version + config version
- Any response contract that includes evidence IDs should remain unchanged; caching must preserve the same evidence references and metadata the kiosk relies on.

#### c. UX / Behavior

- Users should experience lower latency for repeated/FAQ-style queries.
- After an admin publishes KB changes, kiosks should stop serving old cached responses quickly (invalidation/refresh), prioritizing correctness over speed.

---

### 6) Integration Points

- **Depends on**:
  - KB versioning/publish flow (KB version increments on publish)
  - normalized query + intent resolution outputs (pipeline order)
- **Affects**:
  - Goal 4/5 (hybrid + multi-path): cache keys must incorporate the resolved compound/path structure and any fusion parameters that change outputs
  - Goal 7 (filtering policy): cache key must include applied filters (hard/UI/inferred)
  - Goal 10 (metrics/logging): cache outcomes must be measurable and attributable
  - Goal 12 (pipeline order): caching should occur after normalize → intent → (optional clarification) → constrained rewrite so keys are stable and safe

---

### 7) Edge Cases / Failure Modes

- **KB publish happened** but cache still returns old response:
  - must be prevented by version-scoped keys and/or publish-triggered invalidation
- **Config changes** not reflected in cache:
  - config version/hash must be in key; config update must invalidate relevant cache scope
- **Ambiguous or clarification-required queries**:
  - do not cache pre-clarification ambiguous responses as if they were stable answers
- **Compound queries**:
  - ensure cache key captures the resolved compound structure (e.g., top intents, applied priority rules) so a different resolution doesn’t reuse the wrong cached entry
- **Safety-critical intents**:
  - prefer bypass or re-validation before serving cached results if correctness risk is high
- **Cache stampede** under load:
  - optional single-flight / request coalescing for identical keys; must not break determinism/logging

---

### 8) Logging & Metrics

Log enough to audit cache behavior and correlate performance gains:

- cache decision: `hit | miss | bypass`
- reason for bypass (e.g., safety-critical intent, clarification pending, disabled by config)
- key components (or hashed key) and the resolved inputs:
  - normalized query
  - resolved intent(s) / compound marker
  - applied filters summary
  - KB version
  - config version/hash
- TTL selected and remaining age (if available)
- invalidation events:
  - trigger type (KB publish / config update / TTL expiry)
  - affected scope (version, prefix) if applicable
- performance:
  - latency saved (cache hit path vs miss path) where measurable

---

### 9) Determinism / Constraints

- For a fixed KB version/config + same normalized query + same resolved intent/filters ⇒ cache key is stable.
- Never serve cached responses across KB version boundaries.
- Cache behavior must be observable and must not hide changes in retrieval behavior (log hit/miss/bypass).

---

### 10) Definition of Done (DoD)

- Cache key includes: normalized query, resolved intent/compound structure, applied filters, KB version, and config version/hash.
- Cache TTL policy is implemented with safe defaults.
- KB publish/config update causes deterministic invalidation or safe refresh (no stale serving across versions).
- Cache hit/miss/bypass is logged with enough context to audit behavior.
- Safety/clarification edge cases are handled (no caching unsafe/ambiguous responses as stable answers).

---

### 11) Open Decisions

- What exact “config version” signal to use in cache keys (existing version table vs hash of relevant config payload).
- Which intents are considered safety-critical for bypass/re-validation (and the minimum viable rule set).
- Whether to implement single-flight/coalescing on cache miss for identical keys in this increment.

---

## Caching / Invalidation (optional deep-spec module; recommended for Goal 11)

### Cache key (minimum viable)

Compose a cache key from:

- `normalized_query`
- `resolved_intent` (and compound resolution fields when compound)
- `applied_filters` (UI/inferred/hard rule outcomes)
- `kb_version`
- `config_version`

Notes:

- Prefer storing/logging a **hashed key** and logging the decomposed components separately (to avoid long keys and to keep logs legible).
- If any component is missing/unknown, **bypass caching** and log why (fail closed).

### TTL policy (minimum viable)

- Default TTL: short (minutes), with optional per-intent overrides only if already modeled/configured.
- TTL must never override KB/config version boundaries (version changes still invalidate).

### Invalidation triggers (minimum viable)

- **KB publish**:
  - increment KB version
  - invalidate cache entries scoped to older KB version(s)
- **Config update**:
  - bump config version/hash
  - invalidate cache entries for prior config version(s)

### Optional re-validation hook (safety)

Before serving a cached response in safety-critical intents:

- run a lightweight retrieval check under the same constraints
- compare top evidence IDs (or a short evidence signature) against the cached response
- if mismatch exceeds a threshold, bypass cache and recompute; log the mismatch and decision

