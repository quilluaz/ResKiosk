---
title: "Open Question — RLHF feedback bias rebuild cadence"
aliases: ["RLHF cadence", "feedback bias rebuild"]
tags: [type/open-question, status/active]
sprint: null
generated_at: "2026-05-11T11:37:24Z"
generated: true
---

# Open: How often is RLHF-style feedback bias rebuilding actually run in practice?

**Source:** `slice0_userstory_running_context.md` §10
**Raised:** 2026-05-11
**Status:** Unresolved
**Owner:** TBD

---

## Why this matters

The codebase has a "RLHF" feature (env-gated `RESKIOSK_RLHF_ENABLED`) that biases retrieval scores per article using `article_biases.bias`. Per the increment goals doc session notes:

> "RLHF" — Env-gated `RESKIOSK_RLHF_ENABLED`. Applies per-article bias from `article_biases` to cosine scores (`RLHF_ALPHA`). Not online learning / policy gradients; not a cross-encoder reranker.

This means biases come from offline rebuilds, not real-time learning. The questions are:

- **How often** does an operator actually run a rebuild? Daily? Weekly? Never?
- **Where** is the rebuild triggered — console UI, CLI script, manual SQL?
- **What feedback signal** drives it — thumbs-up/down counts? recency-weighted? per-language?
- **What happens** when feedback shifts but rebuild lags — biases get stale and serve outdated preferences

Without answering this, the RLHF feature is effectively "code that exists but operates on unknown data."

---

## What we know

- `feedback_logs` table captures per-interaction feedback (thumbs)
- `article_biases` is the per-article computed bias
- Goal 9 / Story 4.7 is the future tuning work — but explicitly **deferred to stretch** per `sprint-plan.md`
- CLAUDE.md flags: *"RLHF bias matrix is rebuilt offline — real-time feedback has no immediate retrieval effect"*

---

## What we'd need to answer it

- A documented operator runbook: "How to rebuild the feedback bias matrix"
- A console page or CLI command that surfaces rebuild status (last-run timestamp, # rows updated)
- A decision: are we treating RLHF as a demo feature only, or as a live retrieval lever?

---

## Where this surfaces

- AAIH demo — should we mention RLHF or not, given its operational ambiguity?
- Sprint 4.7 (stretch) — if we ever do tune feedback-adjusted ranking, this question must be answered first
- Goal 9 — retrieval quality positioning depends on whether this lever is in use

---

## Possible resolution paths

1. **Decide it's stretch-only** — document that bias rebuild is not part of operational MVP, only demo
2. **Wire it into publish** — automatically rebuild bias matrix on `POST /admin/publish` so it stays fresh-ish
3. **Add a cron / manual rebuild button** — let operators trigger it explicitly when they want

Recommended lean: option 1 for AAIH MVP scope, option 2 or 3 post-MVP.

---

## Related

- [[10-architecture/users-and-scope]]
- [[30-decisions/goals]] — Goal 9 (retrieval quality)
- `docs/legacy/rlhf.md` — historical RLHF documentation
