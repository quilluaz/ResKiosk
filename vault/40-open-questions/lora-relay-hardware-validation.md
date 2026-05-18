---
title: "Open Question — LoRa/RELAY hardware validation completeness"
aliases: ["lora hardware", "relay validation"]
tags: [type/open-question, status/active]
sprint: null
generated_at: "2026-05-11T11:37:24Z"
generated: true
---

# Open: How complete and field-tested is the LoRa/RELAY workflow with actual hardware?

**Source:** `slice0_userstory_running_context.md` §10
**Raised:** 2026-05-11
**Status:** Unresolved
**Owner:** TBD (Sting421 has done the most LoRa work per git log)

---

## Why this matters

LoRa is the resilient-fallback transport when LAN fails. It's also the most hardware-dependent part of the system — depends on attached ESP32+LoRa transceivers via serial or Bluetooth. The codebase has LoRa integration (`hub/services/lora_manager.py`-equivalents, AES-256-GCM encryption, hub-to-hub messaging) but it's unclear:

- How much of it has been exercised end-to-end with **real hardware**, not mocks
- Whether encryption + ACK handshakes survive realistic radio conditions
- Whether range, throughput, and reliability meet shelter needs
- Whether the console's LoRa monitoring/messaging UI matches actual on-air behavior

---

## What we know from the codebase

- LoRa-related commits exist across Sprint 0 → Sprint 2 (commits `0355d99`, `b1baaa2`, `d4fc405`, etc.) by Sting421
- LoRa config UI exists in the console
- AES-256-GCM encryption added per commit `139e7a1`
- CLAUDE.md explicitly flags: *"LoRa serial manager is hardware-dependent — mock it for local dev/testing"*

This suggests dev sessions use mocks; field validation status is unknown.

---

## What we'd need to answer it

- A hardware test log: which hubs have been paired, over what range, with what success rate
- A bench test result for: throughput, ACK reliability, encryption overhead, reconnection behavior
- An updated `docs/` page reflecting current LoRa capabilities and gotchas

---

## Where this surfaces

- Sprint 8 E2E test plan — should LoRa be in the test matrix or skipped as too hardware-dependent?
- AAIH demo planning — is LoRa a demo-worthy feature or "available but not demo-prominent"?
- Any real shelter deployment — LoRa needs known-good baseline before being relied on

---

## Related

- [[10-architecture/users-and-scope]] — Technical Operators user type owns LoRa
- [[00-pre-sprint-baseline/_index]] — references LoRa as part of the three-component stack
