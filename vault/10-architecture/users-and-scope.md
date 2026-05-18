---
title: "Users and Scope"
aliases: ["users", "scope", "non-scope", "product boundaries"]
tags: [type/architecture, status/active]
sprint: null
generated_at: "2026-05-11T11:37:24Z"
generated: true
---

# Users and Scope

ResKiosk is an **offline-first, local-network kiosk system** for disaster shelters and evacuation centers. This note captures the human side of the product — **who uses it**, **what problem it solves**, and **what's explicitly out of scope**. For the technical snapshot, see [[00-pre-sprint-baseline/_index]].

Source: `slice0_userstory_running_context.md` (product overview content, despite the filename suggesting story tracking).

---

## Problem statement

In disaster and evacuation settings:
- People need **timely, clear information** but staff may be overwhelmed
- **Language differences** slow communication during the moments that matter most
- **Internet connectivity** is often unavailable or unstable

ResKiosk addresses this by providing a **local, offline-first kiosk and hub** that can answer common shelter questions, support multilingual interaction, and escalate emergencies through a structured workflow — with no dependency on cloud services.

---

## Three user types

### 1. Shelter Residents / Displaced Individuals
- People physically inside a shelter or evacuation site
- Need information about: food, registration, medical help, sleeping areas, transportation, announcements, safety, available services
- Interact via the **kiosk** (Android tablet) using voice or text in their native language
- May have low literacy, may be stressed, may not share a common language with staff
- **Primary surface:** [[10-architecture/voice-pipeline|voice pipeline]] + clarification chips

### 2. Shelter Staff / Operators
- Staff or responders on the ground at a shelter
- Maintain the knowledge base, update shelter configuration, review logs, track FAQs, manage emergencies, monitor kiosk connectivity
- Interact via the **admin console** (React/Vite in a browser)
- May be stretched thin — UX should be efficient over feature-rich
- **Primary surface:** Console pages (KB, ShelterConfig, EmergencyCalls, Logs)

### 3. Technical Operators
- Team members responsible for hub deployment and the technical layer
- Handle: hub setup, local deployment, kiosk registration/pairing, model availability, LoRa relay or inter-hub messaging setup
- Interact with the **EXE launcher**, the **console's hub/network pages**, and (where present) **physical LoRa hardware**
- Often the same person as staff in small deployments; distinct role in larger ones
- **Primary surface:** Hub admin endpoints, launcher, ResKiosk RELAY tooling

---

## Current product scope (what IS shipped)

Three integrated components:

| Component | Tech | Purpose |
|-----------|------|---------|
| Hub + Console | Python/FastAPI + React/Vite | Query processing, retrieval, translation, formatting, KB ops, shelter config, emergency lifecycle, kiosk registration, query logging, FAQ tracking, optional LoRa messaging |
| Kiosk Android App | Kotlin/Jetpack Compose | Voice + text input, offline STT/TTS, multilingual UI, answer playback, emergency detection, SOS, session handling, feedback capture |
| ResKiosk RELAY / LoRa | Integrated into hub + console | Optional LoRa transport, monitoring, connection management, AES-256-GCM encryption |

See [[00-pre-sprint-baseline/architecture]] for folder-level detail.

---

## Current core capabilities

- **Voice and text intake** — speak or type depending on kiosk mode
- **Local query processing** — normalize → intent → clarification → retrieval → format → translate, all on-device/on-hub
- **Multilingual support** — translation in both directions via NLLB-200
- **Spoken response delivery** — text + audio playback via VITS / Android System TTS
- **Emergency detection** — Tier 1/2 phrase matching + SOS hold-to-confirm, full lifecycle in console
- **Shelter info and KB management** — staff CRUD via console, freshness enforcement
- **Kiosk + network + messaging ops** — registration, naming, monitoring, LoRa where available
- **Logging, FAQ tracking, feedback capture** — `query_logs`, `feedback_logs`, `article_biases`

---

## Out of scope (explicit non-goals)

The product deliberately does **NOT** include:

- ❌ **Cloud-first or internet-dependent operating modes** — offline-first is a hard constraint; cloud integration is currently disabled in the codebase
- ❌ **Standalone-kiosk answer engine** — kiosks always depend on a local hub for retrieval; they don't run retrieval locally
- ❌ **Commercialization, organizational rollout, procurement strategy** — out of scope for the AAIH increment
- ❌ **Cross-organization deployment policy or governance model** — single-shelter or single-organization deployments only
- ❌ **Production-hardening guarantees across all features, environments, and languages** — the product is in increment-build mode; production-hardening is per-feature

These non-goals matter because they prevent scope creep during sprint planning. When evaluating a proposed story, "does this push us toward a non-goal?" is a valid filter.

---

## Technical boundaries

- **Offline-first** — no cloud calls in normal operation; the system must function with zero internet
- **Local LAN** — primary transport for kiosk ↔ hub and console ↔ hub
- **Optional LoRa** — depends on attached ESP32+LoRa hardware via serial/Bluetooth; not assumed present
- **English at retrieval boundary** — all queries translated to English before retrieval, responses translated back before delivery (NLLB-200)
- **No semantic chunking this increment** — retrieval unit remains one `kb_articles` row
- **Local AI models** — MiniLM (embeddings), NLLB-200 (translation), Ollama-hosted LLMs (formatter + rewriter), Sherpa-ONNX (STT/TTS), planned CLIP/SigLIP for image (Slice 7C)

See [[10-architecture/voice-pipeline]] and [[00-pre-sprint-baseline/dependencies]] for full stack detail.

---

## Open validation questions

Six product-level questions remain unanswered. Each lives as its own note in `40-open-questions/`:

- [[40-open-questions/production-readiness-by-feature]]
- [[40-open-questions/lora-relay-hardware-validation]]
- [[40-open-questions/language-validation-coverage]]
- [[40-open-questions/kiosk-provisioning-consistency]]
- [[40-open-questions/rlhf-feedback-rebuild-cadence]]
- [[40-open-questions/console-page-deployment-readiness]]

---

## Related notes

- [[00-pre-sprint-baseline/_index]] — frozen technical snapshot of the system
- [[30-decisions/goals]] — what the AAIH increment adds to the product
- [[10-architecture/voice-pipeline]] — the resident-facing query path
- [[10-architecture/clarification-system]] — clarification UX layer
