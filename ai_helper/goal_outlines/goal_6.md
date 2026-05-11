# Goal 6 — Clarification UX before rewriting

### 1) Outcome

Implement a **clarification flow** that triggers on low-confidence/ambiguous requests and offers fast UI choices (chips) to resolve intent/scope **before** the pipeline continues to rewrite + retrieval.

- **What changes**: instead of guessing when the request is unclear, the hub returns a structured clarification prompt with 2–3 chip options and a deterministic retry contract.
- **Who benefits**: residents (fewer wrong answers / fewer retries), operators (visibility into what was unclear), maintainers (more deterministic downstream behavior).
- **What success looks like**:
  - ambiguity is resolved within **1–2 steps** for defined scenarios
  - clarification selections are persisted and logged (session → resolved intent/category)
  - clarification occurs **before** any rewrite, and this order is enforced and observable

---

### 2) Why this matters

- **Current limitation**: clarification exists but is not fully productized; ambiguity handling is limited and can lead to wrong answers.
- **Risk addressed**: in emergencies, incorrect guidance erodes trust and increases repeated attempts; ambiguous scope questions are common in kiosk settings.
- **Value**: a fast, deterministic clarification step increases accuracy, reduces unnecessary retrieval load, and produces structured signals that improve filtering/metrics goals downstream.

---

### 3) Scope

- Define **clarification triggers** (minimum viable):
  - low intent confidence / ambiguous intent classification
  - “unclear” intent with low best retrieval score (existing baseline behavior)
  - missing required scope for certain intents (e.g., “where is it?” without a referent)
- Define **chip option sets**:
  - return **2–3** options max (plus an optional fallback such as “Say that differently”)
  - chip ordering must be deterministic for the same inputs (session context + normalized query + intent/confidence + KB version/config)
- Implement a **clarification response + retry contract** between kiosk and hub:
  - hub returns a clarification prompt and chip options
  - kiosk sends back the user’s chip selection (and optionally revised text) to continue the flow
- Implement **persistence** of the user’s clarification resolution to `clarification_resolutions`.
- Enforce pipeline order for affected requests:
  - normalize → intent → **optional clarification** → constrained rewrite → retrieval
- Ensure **observability**:
  - represent clarification events in logs, including triggers, options presented, selection, and downstream impact.

---

### 4) Non-goals

- Multi-turn conversational chat beyond the clarification step (no general dialogue manager).
- Free-form follow-up question generation by an LLM in the hot path (chips are the primary UX).
- Expanding taxonomy design or metadata filtering policy (covered by Goal 7), except where needed to represent chip choices consistently.
- Full analytics UI for operators (capture the data; visualizations can come later).

---

### 5) System Impact

#### a. Data / Schema

**Existing**

- `clarification_resolutions` exists (stores `session_id`, `resolved_intent`, `language`, …).
- `query_logs` exists and should capture the clarification step as part of the request lifecycle.

**New / updated (required by this goal)**

- Ensure `clarification_resolutions` can record the **exact user selection** used to constrain the retry (minimum viable: `session_id`, `resolved_intent`, `language`, and a stable identifier for the chosen option).
- Ensure logging captures:
  - whether clarification was triggered and why
  - options shown (IDs/labels)
  - selected option (ID/label)
  - downstream resolved intent/category used for rewrite + retrieval

#### b. API / Interfaces

**Hub → kiosk**

- Return a structured clarification prompt with:
  - a short question/prompt string
  - `clarification_options` (2–3 chip objects with stable identifiers)
  - a marker indicating the request is paused awaiting clarification

**Kiosk → hub (retry)**

- Send the selected option identifier (and optionally user-provided revised text) so the hub can proceed deterministically.

#### c. UX / Behavior

- **Resident (kiosk)**:
  - when the hub requests clarification, show **2–3 tap chips** that are short and action-oriented
  - after selection, proceed immediately to the clarified answer (no extra typing required)
- **Operator**:
  - clarification resolutions are reviewable via stored data (future UI), enabling prompt/content improvements

---

### 6) Integration Points

- **Depends on**:
  - intent classification confidence outputs (existing)
  - (optional) retrieval score floors for “unclear” fallback detection (existing baseline)
- **Affects**:
  - Goal 12 (canonical pipeline order): clarification must happen before rewrite; ordering must be enforced and logged
  - Goal 5 (multi-path retrieval): ambiguous compounds should prefer clarification over guessing priority when intent signals conflict
  - Goal 7 (filtering policy): clarification chips should be compatible with (or mapped to) a stable taxonomy/category representation
  - Goal 10 (metrics/logging): clarification triggers and outcomes must be measurable
  - Goal 11 (caching): cache keys must incorporate the clarification selection (so cached answers aren’t served to the wrong clarified meaning)

---

### 7) Edge Cases / Failure Modes

- **User ignores or can’t decide**:
  - provide a deterministic fallback chip (e.g., “Show common topics”) or a “Say that differently” retry path
- **Repeated clarification loops**:
  - cap clarification attempts (e.g., max 2) and then fall back to a safe generic response or escalation UX
- **Options too broad / too narrow**:
  - enforce 2–3 options max; ensure options are distinct and not overlapping synonyms
- **Conflicting signals** (compound + unclear):
  - prefer clarification rather than guessing a primary intent when confidence is low
- **Offline / partial context**:
  - chips must still be renderable and actionable without needing network-dependent enrichment

---

### 8) Logging & Metrics

Minimum viable logging to support Goal 10:

- normalized query (and language), session identifier, KB version/config version
- intent outputs (top labels + confidences)
- clarification:
  - triggered (boolean) + trigger reason(s)
  - options shown: `{ id, label }[]`
  - selection: `{ id, label }`
  - resulting resolved intent/category used downstream
- latency breakdown: additional time attributable to clarification step vs baseline
- downstream outcomes:
  - whether the clarified request produced a successful retrieval/answer vs a fallback response

---

### 9) Determinism / Constraints

- For the same normalized input + same session context + same KB/config versions, the clarification trigger decision and chip ordering must be **reproducible**.
- Clarification must occur **before** rewrite; rewrite must not “expand” scope prior to a user selection in ambiguous cases.
- Tie-break rules (when multiple chip sets are eligible) must be stable and logged.

---

### 10) Definition of Done (DoD)

- Clarification can be triggered by the defined minimum-viable conditions (confidence/ambiguity/low-score/missing-scope).
- Hub returns a structured clarification payload with **2–3** chip options and a deterministic ordering.
- Kiosk can submit a chip selection; hub resumes the pipeline using that selection **before rewrite**.
- `clarification_resolutions` stores the resolution and can be joined back to a session/request for analysis.
- Logs include trigger reason(s), options shown, selection, and downstream resolved intent/category.
- Clarification resolves ambiguity within **1–2 steps** on a defined test set of scenarios.

---

### 11) Open Decisions

- Exact trigger policy: thresholds for intent confidence, retrieval score floor, and missing-scope rules per intent.
- Clarification option identity model:
  - intent-backed IDs vs taxonomy-backed IDs (align with Goal 7)
  - whether options are global or intent-specific sets
- Retry contract shape:
  - whether to allow optional free-text refinement alongside chip selection
  - how to represent/retain the original query vs clarified query in logs
- Maximum clarification loop count and the safe fallback experience when the cap is reached.

---

## Contract / Payload Shape (optional module; recommended for Goal 6)

### Clarification response (hub → kiosk)

Minimum viable fields:

- `needs_clarification: true`
- `clarification_prompt: string`
- `clarification_options: [{ id, label }]` (2–3 items; stable IDs)
- `clarification_context` (optional): data needed to resume the request deterministically (e.g., prior intent candidates)

### Clarification retry (kiosk → hub)

Minimum viable fields:

- `selected_clarification_option_id: <id>`
- `original_session_id: <session_id>`
- `user_text_override` (optional): if the user rephrases instead of selecting a chip

Logging requirements:

- store option IDs/labels presented and selected
- store trigger reason(s)
- store resulting resolved intent/category used for rewrite + retrieval

---

## Workflow / Review States (optional module; light)

### Clarification attempt lifecycle (per session/request)

- **No clarification**: request proceeds normally.
- **Clarification requested**: hub pauses and returns chips.
- **Clarification resolved**: kiosk submits selection; hub resumes pipeline.
- **Clarification aborted**: user cancels, times out, or exceeds loop cap; hub returns safe fallback/escalation UX.

