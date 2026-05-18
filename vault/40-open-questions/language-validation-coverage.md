---
title: "Open Question — Language validation coverage"
aliases: ["language coverage", "multilingual validation"]
tags: [type/open-question, status/active]
sprint: null
generated_at: "2026-05-11T11:37:24Z"
generated: true
---

# Open: Which supported languages are fully validated end-to-end across STT, translation, UI, and TTS?

**Source:** `slice0_userstory_running_context.md` §10
**Raised:** 2026-05-11
**Status:** Unresolved
**Owner:** TBD

---

## Why this matters

The product claims support for English, Japanese, Spanish, German, and French (per CLAUDE.md and `00-pre-sprint-baseline`). But each language has **four independent layers** that all need to work:

1. **STT** — Zipformer for EN (streaming), Whisper for JA/ES/DE/FR (batch)
2. **Translation** — NLLB-200 in both directions
3. **UI** — multilingual strings + chip labels + clarification prompts
4. **TTS** — Sherpa VITS for EN/ES/DE/FR, Android System TTS for JA

A language is only truly "supported" if **all four layers** work for it. Any single broken layer means the language is effectively unusable for residents.

---

## What we have evidence for

- EN is the most tested (it's the team's working language and the retrieval-boundary language)
- Per Sprint 1 post-sprint doc: chips and clarification work, but language-specific testing isn't explicitly mentioned
- `docs/TESTING_MULTILINGUAL.md` exists in `docs/legacy/` — should be re-read to extract current coverage

---

## What we'd need to answer it

A coverage matrix:

| Language | STT | Translation in | UI | TTS | Translation out | E2E tested |
|----------|-----|----------------|-----|-----|-----------------|-----------|
| EN | ✓ | n/a | ? | ? | n/a | ? |
| JA | ? | ? | ? | ? (Android Sys TTS) | ? | ? |
| ES | ? | ? | ? | ? (VITS) | ? | ? |
| DE | ? | ? | ? | ? (VITS) | ? | ? |
| FR | ? | ? | ? | ? (VITS) | ? | ? |

For each combination: smoke-tested? Acceptance-tested? Production-grade?

---

## Where this surfaces

- Sprint 4 / Sprint 5 — compound queries and multimodal rollout will surface any latent translation gaps
- Sprint 8 E2E — must run at least one full path per language
- AAIH demo — what language do we present in?

---

## Related

- `docs/legacy/TESTING_MULTILINGUAL.md` — likely contains historic coverage notes
- [[10-architecture/voice-pipeline]]
- [[00-pre-sprint-baseline/dependencies]] — model list per language
