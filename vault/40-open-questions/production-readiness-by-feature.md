---
title: "Open Question — Production readiness by feature"
aliases: ["production readiness"]
tags: [type/open-question, status/active]
sprint: null
generated_at: "2026-05-11T11:37:24Z"
generated: true
---

# Open: Which current features are production-ready vs prototype-level?

**Source:** `slice0_userstory_running_context.md` §10 (product validation items)
**Raised:** 2026-05-11
**Status:** Unresolved
**Owner:** TBD (likely tech lead + staff lead jointly)

---

## Why this matters

The product has many features (voice pipeline, multilingual STT/TTS, emergency lifecycle, LoRa messaging, RLHF bias, console pages, KB management). Not all of them have been hardened against real-world conditions. Without a per-feature production-readiness matrix, we risk:

- Deploying a feature to a shelter where it then fails under load
- Skipping testing on a feature we assume is fine
- Over-investing in polish on a feature that's already solid
- Demo confidence that doesn't match field reality

---

## What we'd need to answer it

A simple per-feature matrix:

| Feature | Stage | Tested in | Known limitations | Field-validated? |
|---------|-------|-----------|-------------------|------------------|
| Voice pipeline (EN) | ? | ? | ? | ? |
| Voice pipeline (JA/ES/DE/FR) | ? | ? | ? | ? |
| Clarification chips | ? | ? | ? | ? |
| Emergency Tier 1/2 detection | ? | ? | ? | ? |
| SOS hold-to-confirm | ? | ? | ? | ? |
| KB CRUD via console | ? | ? | ? | ? |
| Shelter config freshness | ? | ? | ? | ? |
| LoRa messaging | ? | ? | ? | ? |
| RLHF bias | ? | ? | ? | ? |

Each row: `prototype` / `functional` / `production-ready` (or finer-grained).

---

## Where this might surface

- During Sprint 8 E2E testing — by then we need to know what's hardened and what's brittle
- During an AAIH demo — we need to know what to feature vs what to avoid
- During a real shelter pilot (if/when one happens) — we need a known-good feature set

---

## Possible next steps

1. **Sprint 5 (heaviest sprint)** is a natural moment to do this audit since the team is doing schema work and revisiting feature surfaces anyway
2. **Sprint 8 entry criterion** could be "production-readiness matrix exists and is reviewed"
3. **Per-sprint close** — each `vault/20-sprints/sprint-N/_index.md` could include a "production readiness changes" section

---

## Related

- [[10-architecture/users-and-scope]] — where this question was captured from
- [[20-sprints/sprint-8/_index]] — sprint that depends on knowing the answer
