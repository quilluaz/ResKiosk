# Implementation Slices Sequence (AAIH Increment)

This document defines **vertical implementation slices** (a.k.a. vertical cuts) to execute the AAIH product increment safely.

Why slices (before writing stories):

- The goals are **interdependent** and **system-level** (pipeline + retrieval + metadata + validation + multimodal).
- Slices prevent fragmented stories that are not independently testable and that can accidentally break the canonical flow (especially Goals **6**, **7**, **12**).
- Each slice is designed to be **demoable**, **testable**, and to produce a stable contract for the next slice.

Scope note:

- We already have an existing backend + DB. The early slices **extend** the current system rather than rebuilding it.
- This increment has a global constraint: **no semantic chunking** (retrieval unit remains one `kb_articles` row).

---

## Slice 0 — Backbone contract (canonical pipeline + logging skeleton)

**Intent**: Create the stable orchestration layer so every later feature plugs into one correct pipeline.

- **Includes goals**: Goal 12 (canonical order), Goal 10 (logging skeleton)
- **Depends on**: none
- **Delivers**
  - A single “canonical pipeline” path for hub query handling:
    - normalize → intent → (optional clarification gate) → constrained rewrite → retrieval
  - Minimal event/log schema capturing each stage’s outputs (enough to reproduce and debug).
- **Exit criteria (demo/test)**
  - One representative query shows all pipeline stage outputs in logs.
  - Pipeline can “pause” for clarification without running rewrite/retrieval prematurely.

---

## Slice 1 — Controlled scope foundation (Goal 7 + minimal schema)

**Intent**: Make retrieval **safe and scoped** before improving accuracy; establish the “filter contract” used by clarification, validation, hybrid retrieval, and multi-path.

- **Includes goals**: Goal 7 (metadata schema + filtering policy), plus the **minimum schema changes required** to represent it
- **Depends on**: Slice 0
- **Delivers**
  - Metadata dimensions and precedence rules:
    - **Hard system rules** > **User UI filters** > **Inferred intent**
  - Controlled taxonomy v1 (stable IDs) and deterministic mappings:
    - intent → taxonomy node(s)
    - UI chip option → taxonomy node(s) (IDs)
  - Filtering enforcement applies consistently to the retrieval call(s) (even if retrieval is still vector-only).
  - Logging shows applied filters and reasons (auditability).
- **Exit criteria (demo/test)**
  - For the same query + KB version, you can reproduce “why evidence was included/excluded.”
  - Changing a UI filter predictably scopes results (and this is logged).

---

## Slice 2 — Clarify-first UX (true clarification gate + retry contract)

**Intent**: Turn ambiguity handling into a deterministic, low-friction UX that constrains downstream rewrite/retrieval.

- **Includes goals**: Goal 6 (clarification UX), Goal 12 (gate enforcement), Goal 10 (logging)
- **Depends on**: Slice 0, Slice 1
- **Delivers**
  - Clarification triggers (MVP): low intent confidence / unclear intent + low score / missing required scope.
  - Hub → kiosk clarification response with **2–3 chip options** (stable IDs).
  - Kiosk → hub retry contract carrying chip selection so the pipeline resumes deterministically.
  - Persistence of resolution to `clarification_resolutions`.
- **Exit criteria (demo/test)**
  - 3–5 “unclear” scenarios resolve in 1–2 steps.
  - Logs show clarification occurred **before** rewrite and retrieval.

---

## Slice 3 — Trusted KB publish (metadata validation gate + audit trail)

**Intent**: Ensure only **approved metadata** affects resident-facing filtering and retrieval.

- **Includes goals**: Goal 8 (validation gate), Goal 10 (logging/audit)
- **Depends on**: Slice 1 (filter/taxonomy model), Slice 0 (logging backbone)
- **Delivers**
  - Rule-based + statistical checks producing a deterministic result set for the same KB snapshot/config.
  - Publish gating: metadata classified as **approved vs quarantined** (blocked from affecting retrieval until reviewed).
  - Human review workflow (MVP): approve / reject / override with reasons, tied to KB version.
  - Optional offline/batch LLM-judge support (explicitly not hot path).
- **Exit criteria (demo/test)**
  - A “bad metadata” example is quarantined and does not affect resident retrieval.
  - Review decision is auditable and tied to the published KB version.

---

## Slice 4 — Deterministic retrieval core (BM25 + fusion + explainability)

**Intent**: Improve answer accuracy and determinism using hybrid retrieval, now that scope and safety are enforced.

- **Includes goals**: Goal 4 (hybrid BM25 + vectors), Goal 9 (quality via retrieval stack), Goal 10 (path contribution logging), Goal 7 (filters applied)
- **Depends on**: Slice 0, Slice 1
- **Delivers**
  - Lexical retrieval path (BM25-like) over defined KB fields.
  - Fusion strategy (e.g., RRF) with deterministic tie-breaks.
  - Logging shows lexical vs vector contributions per evidence item.
- **Exit criteria (demo/test)**
  - Exact-term test set improves measurably.
  - Rankings are stable for the same KB version/config/query.

---

## Slice 5 — Compound correctness (multi-path retrieval + deterministic merge)

**Intent**: Handle compound queries by decomposing into intent-scoped retrieval paths, then merging with explicit priority rules.

- **Includes goals**: Goal 5 (multi-path retrieval), Goal 4 (hybrid per-path), Goal 7 (filters per-path), Goal 12 (pipeline), Goal 10 (observability)
- **Depends on**: Slice 4, Slice 1, Slice 0 (and Slice 2 if clarification is required for the scenario)
- **Delivers**
  - Minimum viable decomposition: use top-2 intents to form two path queries.
  - Run retrieval per path, then merge deterministically (priority + dedupe + explicit strategy).
  - Evidence attribution includes producing path/intent and per-path rank/score.
- **Exit criteria (demo/test)**
  - A defined compound scenario (e.g., “high fever + nearest doctor”) returns correct primary + secondary outputs.
  - Logs show per-path evidence and final merge decision.

---

## Slice 6A — Observability & trust (MVP metrics completion)

**Intent**: Make system quality measurable and validate stability before introducing caching state.

- **Includes goals**: Goal 10 (metrics/logging complete enough to compute KPIs)
- **Depends on**: Slice 0 (logging backbone); benefits strongly from Slices 1–5
- **Delivers**
  - Logging completeness for computing MVP KPIs:
    - grounding proxy
    - evidence/source match & stability
    - latency breakdown
  - Minimum viable export/reporting workflow (even if manual queries) to summarize KPIs by KB version/intent/modality.
- **Exit criteria (demo/test)**
  - A basic “metrics report” can be generated per KB version.

---

## Slice 6B — Safe caching (version-aware, observable, correctness-first)

**Intent**: Add performance improvements only after metrics demonstrate stable, correct behavior.

- **Includes goals**: Goal 11 (version-aware caching)
- **Depends on**: Slice 6A (metrics completion), Slice 0 (pipeline backbone)
- **Delivers**
  - Cache keys include normalized query + resolved intent/filters + KB/config version.
  - TTL + invalidation hooks on KB publish/config updates; hit/miss logged.
  - Optional lightweight safety check for high-stakes intents before serving cached outputs (implementation-dependent).
- **Exit criteria (demo/test)**
  - Cache invalidates on publish/config update; no stale answers served after version change.
  - Cache behavior is observable and does not hide regressions (hit/miss + key fields are logged).

---

## Slice 7A — Multimodal Schema

**Intent**: Introduce the minimum schema and evidence contract changes needed for ResKiosk to represent both text and image evidence without breaking existing text-only knowledge base behavior.

- **Includes goals**:
  - Goal 3 — KB schema rework for multimodal retrieval
  - Goal 10 — Modality-aware evidence logging support
  - Integration with Goal 7 metadata/filtering model
- **Depends on**:
  - Slice 0 — Backbone contract
  - Slice 1 — Controlled scope foundation
  - Slice 3 — Trusted KB publish
  - Slice 6A — Observability & trust
- **Delivers**
  - KB schema support for evidence modality, minimum text and image
  - Stable evidence identifiers for text and image evidence
  - Image asset reference fields or link structure prepared for Slice 7B
  - Forward-compatible segmentation fields without enabling semantic chunking
  - Backward-compatible behavior for existing text-only KB articles
  - Modality-aware evidence response shape
- **Exit criteria (demo/test)**
  - Existing text-only KB content remains retrievable.
  - Evidence objects can represent modality as text or image.
  - Image evidence can reference asset records once Slice 7B exists.
  - Evidence IDs remain stable and loggable.
  - Migration is additive or safely backward-compatible.

---

## Slice 7B — Image Asset Lifecycle

**Intent**: Store KB images as first-class assets with stable identity, thumbnails, content hashes, and KB version linkage so visual evidence can be displayed, audited, and invalidated safely.

- **Includes goals**:
  - Goal 2 — Image storage as first-class KB assets
  - Goal 11 — Version-aware invalidation integration where relevant to image artifacts
  - Goal 10 — Asset lifecycle logging
  - Integration with Slice 7A multimodal schema
- **Depends on**:
  - Slice 7A — Multimodal Schema
- **Delivers**
  - Durable image asset records with stable asset IDs
  - Original image reference
  - Thumbnail reference for kiosk display
  - Content hash for identity, dedupe, and integrity checks
  - MIME type, size, timestamps, and minimal audit fields
  - KB version linkage for publish-time invalidation
  - Deterministic thumbnail generation
  - Publish-time invalidation or refresh behavior for image-derived artifacts
- **Exit criteria (demo/test)**
  - Image assets are stored with original reference, thumbnail reference, content hash, and KB version linkage.
  - Thumbnail generation uses deterministic parameters.
  - Missing or broken image assets are not returned as valid evidence.
  - KB publish invalidates or refreshes image-derived artifacts safely.
  - Asset lifecycle events are logged.

---

## Slice 7C — Image Embeddings & Semantic Retrieval

**Intent**: Enable text-to-image semantic retrieval using a locally hosted vision-language embedding model so English retrieval-boundary queries can return relevant image evidence.

- **Includes goals**:
  - Goal 1 — Semantic image search
  - Goal 10 — Image retrieval logging and evaluation support
  - Integration with Goal 7 filtering and Goal 8 validation gating
- **Depends on**:
  - Slice 7A — Multimodal Schema
  - Slice 7B — Image Asset Lifecycle
  - Slice 1 — Controlled scope foundation
  - Slice 3 — Trusted KB publish
- **Delivers**
  - Selected and configured CLIP/SigLIP-style image embedding model
  - Local/offline model loading path
  - Image preprocessing rules
  - Image embedding generation and persistence for eligible KB image assets
  - Text-to-image retrieval path returning image evidence IDs, scores, ranks, and render references
  - Similarity threshold and deterministic tie-break behavior
  - Filtering and validation enforcement for image evidence
  - Image retrieval logging with model/version, evidence IDs, scores, thresholds, and latency
- **Exit criteria (demo/test)**
  - English text queries can retrieve relevant image evidence.
  - Image retrieval returns stable evidence IDs, scores, ranks, and render references.
  - Disabled, unpublished, or quarantined image evidence is not returned.
  - Retrieval is deterministic for a fixed KB version, model version, config, and query.
  - Image retrieval decisions are logged with enough detail for debugging and evaluation.

---

## Slice 7D — Kiosk Image Rendering & Multimodal Demo

**Intent**: Integrate image evidence into the resident-facing kiosk experience and create demo/regression scenarios that prove visual guidance works for navigation, landmarks, and first-aid use cases.

- **Includes goals**:
  - Goal 1 — Image evidence display and image-first response behavior
  - Goal 2 — Thumbnail/original asset consumption
  - Goal 10 — Multimodal evaluation and demo metrics
- **Depends on**:
  - Slice 7B — Image Asset Lifecycle
  - Slice 7C — Image Embeddings & Semantic Retrieval
- **Delivers**
  - Kiosk rendering for image evidence returned by the hub
  - Thumbnail-first display behavior
  - Graceful handling of missing or broken image references
  - Image-first response behavior for visual questions
  - Minimal text framing for image-first answers
  - Multimodal demo and regression test set
  - Landmark/building, wayfinding, and first-aid visual test scenarios
  - Console/admin image asset status display and confirmation UX where needed
- **Exit criteria (demo/test)**
  - Kiosk can display returned image evidence offline/local-network.
  - Existing text-only answers still render normally.
  - “Show me [building]” can return and display correct landmark image evidence.
  - “How do I bandage a wound?” can return and display correct first-aid visual evidence.
  - Low-confidence image matches are not presented as authoritative.
  - Demo/regression test set produces deterministic results for a fixed KB snapshot.

---

## Recommended execution order

**Slice 0 → Slice 1 → Slice 2 → Slice 3 → Slice 4 → Slice 5 → Slice 6A → Slice 6B → Slice 7A → Slice 7B → Slice 7C → Slice 7D**

Rationale:

- Start by enforcing the canonical pipeline (Goal 12) and logging skeleton (Goal 10).
- Next, define scoping/taxonomy/filtering (Goal 7) because it becomes the contract for clarification, validation, and retrieval changes.
- Then productize clarification (Goal 6) and publish-time validation (Goal 8) so unsafe/incorrect metadata cannot leak into retrieval.
- Only after scope + safety are in place do we improve retrieval accuracy (Goal 4) and compound handling (Goal 5).
- Complete metrics (Goal 10) before multimodal so image evidence is measurable and loggable.
- Add caching (Goal 11) for performance, but note it is **not a strict blocker** for multimodal delivery unless explicitly required later.
- Slice 7A comes first because image retrieval and image assets require a modality-aware schema and evidence contract.
- Slice 7B follows because image assets (thumbnails, hashes, KB-versioned invalidation) must exist before embeddings can be generated reliably.
- Slice 7C follows because semantic image retrieval depends on both the multimodal schema and the asset lifecycle, and must respect filtering + validation gating.
- Slice 7D comes last because kiosk rendering and demo scenarios depend on stable image evidence payloads, render references, and retrieval behavior.

