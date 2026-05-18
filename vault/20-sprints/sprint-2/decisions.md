---
title: "Sprint 2 — Decisions"
tags: [type/decision, sprint/2]
sprint: 2
generated_at: "2026-05-11T14:42:01Z"
generated: true
---

# Sprint 2 — Key decisions

## 2-D1: Clarification chips map to **stable taxonomy node IDs**, not free-text labels

**Status:** Accepted
**Date:** ~2026-05-04 (Sprint 2 start)
**Related stories:** 2.2, 2.4, 2.5

### Context
The Sprint 1 taxonomy work (Story 1.1) established stable namespaced IDs (`rk.tax.<category>.<subcategory>`). The clarification UX needed a wire-level identifier the kiosk could send back unchanged after the resident's tap.

### Decision
Each clarification chip carries a stable taxonomy node ID in its `id` field. The kiosk submits that ID on retry. The hub resolves it deterministically via `intent_taxonomy_map` to a resolved intent before resuming the pipeline.

### Consequences
- Chip labels can be translated per-language without changing wire identifiers.
- `clarification_resolutions` rows can be analyzed cross-language by node ID.
- Adds a hard dependency on the taxonomy from Slice 1 — chip changes must go through the taxonomy seed, not ad-hoc text.

### Related notes
- [[30-decisions/slice-1]] — Taxonomy v1 model
- [[30-decisions/slice-2]] — Slice 2 design

---

## 2-D2: Validation runs at **publish time**, not at every write

**Status:** Accepted
**Date:** ~2026-05-09 (when story 3.1 landed)
**Related stories:** 3.1, 3.2, 3.3

### Context
Two plausible places to run metadata validation: (a) on every `kb_articles` insert/update, or (b) only when staff clicks "Publish". (a) gives faster feedback but adds latency to every edit and can produce noisy intermediate quarantine states.

### Decision
Validation runs **only on `POST /admin/publish`** via the validation rule engine. Articles can sit in `draft` or `needs_review` freely without re-validation churn. The publish gate is the right checkpoint because that is when content actually starts affecting residents.

### Consequences
- `status` field tracks validation state independently from `enabled`.
- Editing UX stays fast — no per-keystroke validation.
- Staff get a single, comprehensive validation report per publish attempt rather than scattered per-article errors.
- Trade-off: validation lag — a draft can sit broken indefinitely until someone tries to publish.

### Related notes
- [[30-decisions/slice-3]] — Slice 3 design (3-D2 captures the same decision in more detail)

---

## 2-D3: Quarantined articles are a **hard retrieval block** equivalent to `enabled=0`

**Status:** Accepted
**Date:** ~2026-05-09
**Related stories:** 3.2, 3.5 (Sprint 3)

### Context
An article can have `enabled=1` (staff intends for it to be active) but still fail validation (e.g., missing taxonomy assignment). Three options: (a) treat quarantine as a soft warning, (b) gate the publish step only, (c) hard-exclude from retrieval regardless of `enabled`.

### Decision
Quarantined articles are unconditionally excluded from retrieval, in addition to being blocked from publish. The exclusion is added to the Slice 1 hard-rule layer (precedence: hard > UI > inferred).

### Consequences
- Story 3.5 (Sprint 3) will add `status != 'quarantined'` to the hard-rule filter in `hub/retrieval/search.py`.
- Even if a staff member manually flips `enabled=1` on a quarantined row, residents still cannot see it. Safety default wins.
- Logs must include `hard_rule:quarantined` as an exclusion reason code.

### Related notes
- [[30-decisions/slice-1]] — hard rule precedence
- [[30-decisions/slice-3]] — 3-D1 (same decision recorded in slice context)

---

## 2-D4: Story 3.3 is **deferred-by-completion**, not re-planned

**Status:** Accepted (retrospective)
**Date:** 2026-05-11
**Related stories:** 3.3

### Context
The Sprint 2 plan listed 3.3 as in-scope (53 pts including it). The validation engine (3.1) and storage (3.2) only landed on May 9, leaving roughly one working day to wire the publish route to the gate. Story 3.3 was 90% built when Sprint 2 closed but the final route handler change committed on May 11 (commit `0fd6ffb`).

### Decision
Count 3.3 as Sprint 2 work that completed on Sprint 3 day 1, not as a Sprint 3 story. Sprint 3 backlog continues with 3.4–3.6 as originally planned, no compression.

### Consequences
- Sprint 2 final delivery: 8 stories, 45 pts (versus 9 stories, 53 pts planned).
- No re-shuffling of Sprint 3 (still 11 stories, 59 pts).
- The pattern of "validation work landing late in the sprint, route wiring landing day 1 of the next" is worth watching — if it repeats with 3.6 audit logging, we should pull validation earlier in the sprint.
