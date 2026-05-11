# ResKiosk — Standard Goal Delivery Outline Template

This template defines how each goal should be documented for full delivery. It ensures consistency, clarity, and execution readiness across all goals.

---

# Universal Goal Template (Required for All Goals)

## Goal X — [Goal Name]

### 1) Outcome
Describe what the system must achieve.
- What changes
- Who benefits
- What success looks like

---

### 2) Why this matters
Explain why this goal exists.
- Current limitation or problem
- Risk being addressed
- Value to users or system

---

### 3) Scope
Define what is included in this goal.
- Core implementation items
- Behavior changes
- System boundaries

---

### 4) Non-goals
Explicitly state what is NOT included.
- Prevents scope creep

---

### 5) System Impact

#### a. Data / Schema
- Database changes
- Models/entities
- Versioning changes
- Metadata additions

#### b. API / Interfaces
- Endpoint changes
- Request/response updates
- Internal contracts (hub/kiosk/console)

#### c. UX / Behavior
- Kiosk behavior
- Console/admin behavior
- User-facing changes

---

### 6) Integration Points
Describe dependencies and interactions.
- Depends on other goals
- Affects downstream systems
- Shared contracts

---

### 7) Edge Cases / Failure Modes
Describe what can go wrong and expected handling.
- Invalid input
- Missing data/models
- Empty results
- Conflicts
- Fallback behavior

---

### 8) Logging & Metrics
Define what must be logged and measured.
- Key events
- IDs/scores/decisions
- Success/failure paths
- Metrics enabled

---

### 9) Determinism / Constraints
Define system guarantees.
- Tie-break rules
- Ordering guarantees
- Version constraints
- Safety constraints

---

### 10) Definition of Done (DoD)
Testable completion criteria.
- Feature works end-to-end
- Logs are present
- Edge cases handled
- Constraints enforced

---

### 11) Open Decisions
List unresolved implementation questions.
- Keep short and actionable

---

# Optional Deep-Spec Modules (Use Only When Needed)

Add these sections ONLY if the goal requires deeper specification.

---

## Policy / Rules
Use when defining:
- Precedence logic
- Enforcement rules
- Fallback behavior

Include:
- Rule hierarchy
- Override conditions
- Prohibited behaviors

---

## Taxonomy / Controlled Vocabulary
Use when defining:
- Categories
- Mappings
- Classification rules

Include:
- Category structure
- Stable IDs
- Mapping rules
- Multi-assignment rules

---

## Evaluation / Benchmark Plan
Use when measuring performance.

Include:
- Evaluation dataset
- Expected outputs
- Regression criteria
- Pass/fail thresholds

---

## Contract / Payload Shape
Use when changing data exchange formats.

Include:
- Request structure
- Response structure
- Required fields
- Version compatibility

---

## Workflow / Review States
Use for admin-controlled or gated processes.

Include:
- States (draft, approved, etc.)
- Transitions
- Approval/rejection flow
- Audit requirements

---

## Caching / Invalidation
Use when performance and freshness matter.

Include:
- Cache keys
- TTL policy
- Invalidation triggers
- Revalidation rules

---

## Migration / Rollout Plan
Use when modifying schema or core behavior.

Include:
- Migration steps
- Backward compatibility
- Rollout sequence
- Rollback strategy

---

# Usage Guidelines

## Apply Three Levels of Depth

### Light Goals
- Use only the Universal Template

### Medium Goals
- Add 1–2 deep-spec modules

### Heavy Goals
- Add multiple deep-spec modules

---

## Recommended Mapping

- Heavy: Goals 3, 5, 7, 8
- Medium: Goals 1, 2, 4, 6, 10
- Light: Goals 9, 11, 12

---

# Notes

- Do NOT over-specify all goals
- Keep structure consistent
- Add depth only where necessary
- Use Goal 7 as the reference for heavy-spec goals

---

End of template

