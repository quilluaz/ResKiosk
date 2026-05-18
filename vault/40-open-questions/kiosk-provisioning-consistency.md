---
title: "Open Question — Kiosk provisioning consistency"
aliases: ["kiosk setup", "kiosk provisioning"]
tags: [type/open-question, status/active]
sprint: null
generated_at: "2026-05-11T11:37:24Z"
generated: true
---

# Open: How consistently are kiosk setup, model download, and asset provisioning handled across devices?

**Source:** `slice0_userstory_running_context.md` §10
**Raised:** 2026-05-11
**Status:** Unresolved
**Owner:** TBD

---

## Why this matters

The kiosk app ships with multiple AI models that must be present on-device for offline operation:
- Zipformer STT (EN)
- Whisper STT models (JA/ES/DE/FR)
- VITS TTS voices (EN/ES/DE/FR)
- Various Sherpa-ONNX models

In a real deployment, a tech operator (per [[10-architecture/users-and-scope]]) needs to set up N tablets reliably. Inconsistencies in provisioning mean:

- One tablet works, another doesn't, and the difference isn't obvious
- A model is "downloaded" but corrupt
- Asset paths differ between tablets, causing crashes only in production
- Time-to-deploy at a shelter is dominated by per-tablet manual fixes

---

## What we know

- Android app uses Gradle assetVerify scripts (per `da13786` "asset verification scripts" commit)
- Models are likely bundled or download-on-first-run — exact mechanism unclear from this vault layer
- CLAUDE.md mentions: *"Model prewarming at startup (`hub/main.py`) — changes here affect cold-start time significantly"* — refers to the hub, not kiosks

---

## What we'd need to answer it

- A documented per-device provisioning checklist
- A "kiosk readiness check" endpoint or local probe that confirms all required models are present and valid
- A reproducible fresh-install test on at least 3 tablets

---

## Where this surfaces

- Any multi-tablet pilot
- AAIH demo: how many tablets are we demoing on? Are they all in known-good state?
- Sprint 6 (image asset lifecycle) — the asset story for images will rediscover this same problem class

---

## Related

- [[10-architecture/users-and-scope]] — Technical Operator user type owns provisioning
- [[30-decisions/slice-7b]] — image asset lifecycle (parallel concerns)
