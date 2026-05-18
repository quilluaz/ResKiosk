---
title: "Pre-Sprint Baseline — ResKiosk System Snapshot"
aliases: ["baseline", "sprint 0 state"]
tags: [type/architecture, status/done, frozen]
sprint: null
generated_at: "2026-05-11T07:53:18Z"
generated: true
frozen: true
---

# Pre-Sprint Baseline — ResKiosk System Snapshot

**⚠️ THIS DOCUMENTATION IS FROZEN. It represents ResKiosk as it existed after Sprint 2 completion (May 10, 2026). DO NOT MODIFY.**

This baseline captures the state of the ResKiosk system before Sprint 3 begins, providing a reference point for understanding what foundation the AAIH increment was built upon.

---

## System Overview

ResKiosk is an **offline-first, voice-powered information kiosk** for disaster shelters and evacuation centers. Displaced individuals speak in their native language and receive spoken answers about shelter services — no internet required.

### Core Purpose

Enable non-technical displaced persons to access critical shelter information through natural voice conversations in their native language, with degraded-but-functional offline operation when internet connectivity is lost.

### Three-Component Architecture

ResKiosk consists of three tightly integrated components:

#### 1. Hub (Python/FastAPI Backend)
- **Location**: `hub/`
- **Purpose**: Central intelligence — query processing, semantic search, translation, LLM formatting, emergency coordination
- **Key Technologies**: FastAPI, SQLAlchemy, SQLite, Sentence-Transformers (MiniLM), NLLB-200, Ollama (local LLMs)
- **Runs on**: Windows 10/11 laptop or desktop at the shelter (packaged as `ResKiosk-Hub.exe`)

#### 2. Console (React/Vite Admin Dashboard)
- **Location**: `console/`
- **Purpose**: Staff-facing web UI for KB management, shelter config, emergency monitoring, logs
- **Key Technologies**: React 18, Vite, React Router, Axios, Lucide React
- **Access**: Browser at `http://<hub-ip>:8000/console/` (served as static files from hub)

#### 3. Kiosk (Android Tablet App)
- **Location**: `kiosk/`
- **Purpose**: Displaced-person-facing voice interface — offline STT/TTS, emergency detection, query submission
- **Key Technologies**: Kotlin, Jetpack Compose, Sherpa-ONNX (local STT/TTS), Retrofit
- **Runs on**: Android tablets (minSdk 26, targetSdk 34)

---

## Communication Model

```
┌─────────────┐
│   Console   │ ─── HTTP ──→ ┌──────┐
│ (Browser)   │              │ Hub  │
└─────────────┘              │      │
                             │      │
┌─────────────┐              │      │
│   Kiosk     │ ─── HTTP ──→ │      │
│ (Android)   │ ←── JSON ─── │      │
└─────────────┘              └──────┘
      ↓
  Local STT/TTS
  (Sherpa-ONNX)
```

- **Hub as Central Server**: The hub runs a local LAN HTTP server (default port 8000)
- **Kiosks → Hub**: Android tablets connect to hub via user-configured IP, send voice queries as JSON, receive formatted answers
- **Console → Hub**: Admin staff access the console through the hub's web server (same port)
- **LoRa Fallback**: Hub-to-hub communication via ESP32+LoRa transceivers for resilient messaging when primary network fails (added in Sprint 1–2)

---

## Key Subsystems (as of Sprint 2 completion)

### Voice Pipeline
1. **Kiosk captures audio** (16kHz, Sherpa-ONNX streaming STT for EN / batch Whisper for ja/es/de/fr)
2. **STT post-processing** (fillers, dedup, fuzzy domain correction, punctuation)
3. **Emergency detection** (Tier 1/2 keyword matching before sending to hub)
4. **POST /query to hub** with transcript + metadata
5. **Hub translation** (NLLB: user language → EN)
6. **Normalization** (lowercase, synonyms, domain-specific corrections)
7. **Intent classification** (prototype-based, 23+ intents, cosine similarity)
8. **Semantic retrieval** (MiniLM embeddings, cosine sim against KB matrix, RLHF bias optional)
9. **Gating logic**: DIRECT_MATCH / NEEDS_CLARIFICATION / NO_MATCH
10. **Clarification system** (Sprint 2: taxonomy-backed chip selection, pause-and-resume)
11. **LLM formatter** (translategemma:4b for response phrasing, optional rewriter for noisy queries)
12. **Hub translation** (NLLB: EN → user language)
13. **Response JSON** returned to kiosk
14. **Kiosk TTS** (Sherpa VITS for en/es/de/fr, Android System TTS for ja)
15. **Chat bubble display** with response text

### Knowledge Base System
- **Storage**: SQLite `kb_articles` table (question, answer, category, tags, embeddings, metadata)
- **Versioning**: `kb_version` tracked in `system_version` table, kiosks poll for updates
- **Metadata fields** (Sprint 1): `authority`, `scope`, `center_id`, `hub_id` for filtering
- **Taxonomy system** (Sprint 1): DAG-based `taxonomy_nodes`, `taxonomy_edges`, `kb_item_taxonomy`, `intent_taxonomy_map`
- **Validation pipeline** (Sprint 2): Rule-based metadata validation, quarantine logic, publish gating

### Emergency System
- **Kiosk detection**: Tier 1 (immediate) and Tier 2 (confirmed) keyword matching
- **SOS flow**: Hold-to-confirm UI prevents false alarms
- **Hub tracking**: `emergency_alerts` table with lifecycle states (ACTIVE → ACKNOWLEDGED → RESPONDING → RESOLVED → DISMISSED)
- **Console monitoring**: Real-time emergency call list, status updates, resolution notes

### Translation Layer
- **Model**: Facebook NLLB-200-distilled-600M (CPU inference)
- **Languages**: English, Japanese, Spanish, German, French
- **Latency**: ~1-2s per call (pre-warmed at hub startup)
- **Fallback**: If translation fails, query proceeds in original language

### LLM Layer
- **Formatter**: translategemma:4b (response phrasing, tone control)
- **Rewriter**: llama3.2:3b (query cleanup for noisy STT transcripts, triggered on low similarity)
- **Orchestration**: Ollama server managed by `hub/launcher.py`
- **Warm-up**: Background thread at startup reduces first-query latency

---

## What's Been Delivered (Sprints 1–2)

### Sprint 1 (Apr 27–May 3)
**Focus**: Pipeline backbone + filtering foundation

**Delivered**:
- Slice 0 (Backbone Contract): Canonical pipeline orchestrator, stage logging skeleton
- Slice 1 (Controlled Scope Foundation): Taxonomy v1 schema, metadata fields (`authority`, `scope`), filter policy
- All 8 user stories completed (0.1, 0.2, 0.3, 1.1, 1.2, 1.3, 1.4, 1.5)

### Sprint 2 (May 4–May 10)
**Focus**: Clarification UX + validation/publish foundation

**Delivered**:
- Slice 2 (Clarify-first UX): Clarification pause state, taxonomy chip selection, pause/resume flow, kiosk UI
- Slice 3 (Trusted KB Publish, partial): Validation rule engine (stories 3.1, 3.2), publish gate started (3.3 incomplete)
- Stories 2.1–2.6 complete, 3.1–3.2 complete, 3.3 carried over to Sprint 3

---

## Sprint 3 Scope (Current — May 11–17)

**Focus**: Validation completion + hybrid retrieval + logging

**Stories**:
- Slice 3 completion: 3.3–3.6 (validation gate, metadata review workflow, quarantine exclusion, audit logging)
- Slice 4 (Deterministic Retrieval Core): 4.1–4.6 (BM25 lexical index, hybrid fusion, eval set)
- Slice 6A (Observability): 6A.1, 6A.8 (structured log schema, failure logging)

**Total**: 59 story points, 11 stories

---

## Related Baseline Documents

- [[00-pre-sprint-baseline/architecture]] — Folder layout, entry points, how components communicate
- [[00-pre-sprint-baseline/data-models]] — SQLAlchemy models, Pydantic schemas, all tables
- [[00-pre-sprint-baseline/api-surface]] — Every FastAPI route with method, path, purpose
- [[00-pre-sprint-baseline/dependencies]] — requirements.txt, package.json, build.gradle

---

## Baseline Metadata

- **Snapshot date**: 2026-05-11 (after Sprint 2 completion)
- **Branch**: `aaih-keith`
- **Last commit before baseline**: `0fd6ffb` (slice 3 story 3 done! wraaagh!)
- **KB version at baseline**: Tracked in `system_version.kb_version`
- **Hub version**: 0.2
- **Kiosk version**: 1.0

---

**Remember**: This baseline is **frozen**. Living architecture documentation is maintained in `vault/10-architecture/`.
