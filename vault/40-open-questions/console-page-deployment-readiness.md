---
title: "Open Question — Console page deployment readiness"
aliases: ["console readiness", "console pages"]
tags: [type/open-question, status/active]
sprint: null
generated_at: "2026-05-11T11:37:24Z"
generated: true
---

# Open: Which console pages are considered operationally complete for live deployments?

**Source:** `slice0_userstory_running_context.md` §10
**Raised:** 2026-05-11
**Status:** Unresolved
**Owner:** TBD (Isaac and Sting421 have done the most console work per git log)

---

## Why this matters

The console (`console/src/pages/`) has 11+ page components per the frozen baseline. Each page corresponds to a staff workflow — Dashboard, KBViewer, ShelterConfig, EmergencyCalls, Logs, kiosk monitoring, LoRa monitoring, etc.

Not all pages are at the same maturity level. Some are critical-path for live shelters (KB management, emergency lifecycle). Others may be optional or demo-only (LoRa monitoring, advanced query log views). Without a per-page readiness assessment, staff training and demo prep are guesswork.

---

## What we know

- Console structure landed in Sprint 0/1 (commit `fba598e` "Created User Interface for Hub Console")
- Sprint 2 added some UI modifications (`a36f47f`, `cf6b7e3` UI enhancements)
- Console replaces native dialogs with modals (`9a05b10`)
- Pagination added for KB list (`9a05b10`)
- Multiple pages have been touched but their operational completeness isn't documented

---

## What we'd need to answer it

A per-page assessment:

| Page | Purpose | Staff workflow? | Demo-worthy? | Known issues |
|------|---------|-----------------|--------------|--------------|
| Dashboard | Overview | ? | ? | ? |
| KBViewer | KB CRUD | ✓ | ✓ | Pagination just added |
| ShelterConfig | Shelter ops | ✓ | ✓ | Freshness enforcement exists |
| EmergencyCalls | Live emergency mgmt | ✓ | ✓ | ? |
| Logs | Query log view | ? | ? | Schema expanding (6A.1) |
| Kiosk monitoring | Tablet status | ? | ? | ? |
| LoRa pages | Relay/messaging | ? | ? | See LoRa hardware Q |
| Validation review | Per Story 3.4 | New | ✓ | Sprint 3 active work |
| Image asset view | Per Story 7B.8/7D.6 | Stretch | ? | Sprint 5–6 |

---

## Where this surfaces

- Sprint 3 Story 3.4 (validation review workflow) — adds a new console page that must integrate cleanly
- Sprint 5+ (image asset management) — adds more console surface area
- Sprint 8 E2E — must verify staff-critical pages work end-to-end
- AAIH demo — staff-facing screens are part of the visual story

---

## Possible next steps

1. Quick audit by the console maintainers (Isaac, Sting421) — one row per page, 5-minute fill-in
2. Bake a "console readiness" section into each `vault/20-sprints/sprint-N/_index.md` close-out
3. Pair with [[40-open-questions/production-readiness-by-feature|production-readiness audit]] — same audit, narrower scope

---

## Related

- [[10-architecture/users-and-scope]] — Shelter Staff user type primarily uses console
- [[40-open-questions/production-readiness-by-feature]] — parent audit
- [[00-pre-sprint-baseline/_index]] — references 11 console page components
