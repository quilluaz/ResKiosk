# ResKiosk AAIH Increment — 8-Week Sprint Plan

**Final codebase submission date:** June 20  
**Feature-complete cutoff:** June 14  
**Final stabilization window:** June 15–June 20  
**Planning window:** 8 weekly sprints  
**Sprint 1 status:** Delivered fully  
**Required scope:** Feature implementation completed by Sprint 7, with Sprint 8 reserved for end-to-end testing, benchmarking, regression, critical bug fixes, and final submission  
**Adjustment reason:** Sprint 6 and Sprint 7 are intentionally lighter because most of the team will be busy with graduation for a majority of those weeks.  
**Deferred/stretch scope:** Safe caching and advanced feedback-bias tuning

## Sprint Schedule

| Sprint   | Dates         | Main Focus                                                        |
| -------- | ------------- | ----------------------------------------------------------------- |
| Sprint 1 | Apr 27–May 3  | Pipeline backbone + filtering foundation — **Delivered**           |
| Sprint 2 | May 4–May 10  | Clarification UX + validation foundation + publish gate start      |
| Sprint 3 | May 11–May 17 | Validation completion + hybrid retrieval + core logging            |
| Sprint 4 | May 18–May 24 | Multi-path retrieval + observability completion                    |
| Sprint 5 | May 25–May 31 | Metrics wrap-up + multimodal schema + early image/admin prep       |
| Sprint 6 | Jun 1–Jun 7   | Light week: image asset completion + admin status + kiosk safety   |
| Sprint 7 | Jun 8–Jun 14  | Light week: multimodal retrieval + image-first demo path           |
| Sprint 8 | Jun 15–Jun 20 | E2E testing, benchmarking, regression, final fixes, final package  |

---

# Sprint 1 — Apr 27–May 3

## Sprint Goal

Establish the backend foundation: canonical query pipeline, initial logging skeleton, taxonomy model, metadata fields, and hard retrieval safety rules. This sprint should leave the backend ready for controlled filtering and clarification in later work.

## Sprint Status

**Delivered fully.**

## Assigned Stories

### Slice 0 — Backbone Contract

1. **Story 1 - Create canonical pipeline orchestrator** — 8 pts
2. **Story 2 - Add pipeline stage logging skeleton** — 5 pts
3. **Story 3 - Add clarification pause state to query flow** — 5 pts

### Slice 1 — Controlled Scope Foundation

4. **Story 1 - Define taxonomy v1 data model** — 5 pts
5. **Story 2 - Add metadata fields for retrieval filtering** — 8 pts
6. **Story 3 - Enforce hard retrieval rules** — 5 pts
7. **Story 4 - Apply UI and inferred intent filters with precedence** — 5 pts
8. **Story 5 - Log filter decisions and candidate counts** — 3 pts

## Sprint 1 Total

**44 story points**  
**8 stories**

## Sprint Outcome

By the end of Sprint 1, ResKiosk should have a single controlled backend query path, initial structured logging, taxonomy/filter metadata, and resident-facing hard rules that prevent disabled or unpublished evidence from being returned.

---

# Sprint 2 — May 4–May 10

## Sprint Goal

Build the clarify-first interaction layer and move trusted metadata publishing forward earlier. This sprint should make ambiguity resolution deterministic and create the first enforceable publish gate foundation.

## Assigned Stories

### Slice 2 — Clarify-first UX

1. **Story 1 - Implement clarification trigger policy** — 5 pts
2. **Story 2 - Return taxonomy-backed clarification chips** — 5 pts
3. **Story 3 - Add kiosk clarification chip UI** — 5 pts
4. **Story 4 - Implement clarification retry contract** — 8 pts
5. **Story 5 - Persist clarification resolution** — 3 pts
6. **Story 6 - Log clarification lifecycle events** — 3 pts

### Slice 3 — Trusted KB Publish

7. **Story 1 - Implement metadata validation rule engine** — 8 pts
8. **Story 2 - Add validation status and audit storage** — 8 pts
9. **Story 3 - Gate KB publish using validation results** — 8 pts

## Sprint 2 Total

**53 story points**  
**9 stories**

## Sprint Outcome

By the end of Sprint 2, ambiguous requests should pause for clarification, present taxonomy-backed options, resume deterministically after selection, and record clarification events. Metadata validation infrastructure should exist, and the publish flow should begin enforcing validation results.

---

# Sprint 3 — May 11–May 17

## Sprint Goal

Complete trusted publish validation, implement the deterministic hybrid retrieval core, and pull core structured logging earlier so retrieval changes are observable while they are built.

## Assigned Stories

### Slice 3 — Trusted KB Publish

1. **Story 4 - Build MVP metadata review workflow** — 8 pts
2. **Story 5 - Exclude quarantined metadata from retrieval** — 5 pts
3. **Story 6 - Log validation and publish audit events** — 3 pts

### Slice 4 — Deterministic Retrieval Core

4. **Story 1 - Build lexical retrieval index** — 8 pts
5. **Story 2 - Implement BM25-like lexical scoring** — 5 pts
6. **Story 3 - Fuse lexical and vector results with RRF** — 8 pts
7. **Story 4 - Apply filter policy to hybrid retrieval** — 5 pts
8. **Story 5 - Add hybrid retrieval contribution logging** — 3 pts
9. **Story 6 - Create exact-term retrieval evaluation set** — 3 pts

### Slice 6A — Observability & Trust

10. **Story 1 - Complete structured query log schema** — 8 pts
11. **Story 8 - Add failure and fallback outcome logging** — 3 pts

## Sprint 3 Total

**59 story points**  
**11 stories**

## Sprint Outcome

By the end of Sprint 3, publish validation should be enforceable and auditable. Hybrid retrieval should be operational with lexical scoring, vector retrieval, RRF-style fusion, filter compliance, contribution logging, and an exact-term evaluation set. Core query logging should also be in place early enough to support retrieval debugging.

## Moved to Stretch

- **Slice 4 - Story 7 - Tune feedback-adjusted ranking as a separate layer** — 5 pts

---

# Sprint 4 — May 18–May 24

## Sprint Goal

Implement compound query handling and complete the main observability foundation before multimodal work accelerates. This sprint should make multi-intent questions auditable, measurable, and explainable.

## Assigned Stories

### Slice 5 — Compound Correctness

1. **Story 1 - Detect compound queries using top-2 intents** — 5 pts
2. **Story 2 - Build intent-scoped retrieval path queries** — 5 pts
3. **Story 3 - Run retrieval separately per compound path** — 8 pts
4. **Story 4 - Merge compound path results deterministically** — 8 pts
5. **Story 5 - Add evidence attribution for compound results** — 5 pts
6. **Story 6 - Support primary and secondary compound response outputs** — 5 pts
7. **Story 7 - Log compound lifecycle and merge decisions** — 3 pts
8. **Story 8 - Create compound retrieval evaluation scenarios** — 3 pts

### Slice 6A — Observability & Trust

9. **Story 2 - Add latency breakdown logging** — 5 pts
10. **Story 3 - Capture final evidence list and stability fields** — 5 pts
11. **Story 4 - Implement MVP metrics export workflow** — 5 pts
12. **Story 5 - Create grounding proxy review fields** — 3 pts
13. **Story 9 - Format hub query logs for readable operational observability** — 3 pts

## Sprint 4 Total

**63 story points**  
**13 stories**

## Sprint Outcome

By the end of Sprint 4, compound questions should be split into intent-scoped retrieval paths and merged deterministically. The system should also have enough observability to inspect query lifecycle, evidence attribution, fallbacks, latency, and hub log behavior.

---

# Sprint 5 — May 25–May 31

## Sprint Goal

Finish metrics/reporting, establish the multimodal schema foundation, and front-load early image asset/model/payload/admin work before graduation-heavy weeks. This is the intentional high-load sprint used to reduce risk in Sprint 6 and Sprint 7.

## Assigned Stories

### Slice 6A — Observability & Trust

1. **Story 6 - Create fixed evaluation query set** — 3 pts
2. **Story 7 - Generate basic KPI report by KB version** — 5 pts

### Slice 7A — Multimodal Schema

3. **Story 1 - Add multimodal KB item schema** — 8 pts
4. **Story 2 - Add stable multimodal evidence identity** — 5 pts
5. **Story 3 - Prepare image asset reference fields** — 5 pts
6. **Story 4 - Add forward-compatible segmentation fields** — 3 pts
7. **Story 5 - Update evidence response contract for modality** — 5 pts
8. **Story 6 - Backfill existing KB articles as text modality** — 5 pts
9. **Story 7 - Add modality-aware evidence logging** — 3 pts

### Slice 7B — Image Asset Lifecycle

10. **Story 1 - Store image assets as first-class KB assets** — 8 pts
11. **Story 2 - Add image upload API for KB assets** — 5 pts
12. **Story 3 - Generate content hashes for image assets** — 3 pts
13. **Story 4 - Generate deterministic thumbnails for image assets** — 8 pts

### Early Integration / Admin Prep

14. **Slice 7C - Story 1 - Select and configure image embedding model** — 5 pts
15. **Slice 7D - Story 2 - Add hub-to-kiosk image evidence payload support** — 5 pts
16. **Slice 7D - Story 5 - Add admin image upload and asset confirmation path** — 8 pts
17. **Slice 7D - Story 7 - Create multimodal demo scenarios** — 3 pts

## Sprint 5 Total

**87 story points**  
**17 stories**

## Sprint Outcome

By the end of Sprint 5, ResKiosk should have metrics/reporting by KB version, a multimodal-ready schema, stable evidence identity, modality-aware payloads/logging, and early image upload/hash/thumbnail capability. Model selection, kiosk payload support, admin upload/confirmation, and demo scenario planning should be completed before the graduation-heavy weeks.

---

# Sprint 6 — Jun 1–Jun 7

## Sprint Goal

Complete image asset lifecycle, add simple admin asset/status visibility, and finish kiosk image safety work with a lighter graduation-aware workload. This sprint should finish the image asset backend needed for retrieval while preparing the kiosk to handle missing, broken, compressed, or unavailable images safely.

## Assigned Stories

### Slice 7B — Image Asset Lifecycle

1. **Story 5 - Add image asset processing states** — 5 pts
2. **Story 6 - Link image assets to KB version** — 5 pts
3. **Story 7 - Invalidate image artifacts on KB publish** — 5 pts
4. **Story 8 - Add admin asset confirmation view** — 5 pts
5. **Story 9 - Log image asset lifecycle events** — 3 pts
6. **Story 10 - Compress uploaded images and generate optimized renditions** — 5 pts

### Slice 7D — Kiosk Image Rendering & Multimodal Demo

7. **Story 4 - Handle image loading failures and placeholders** — 3 pts
8. **Story 6 - Display image asset status in admin console** — 5 pts
9. **Story 10 - Validate text-only fallback when image evidence is unavailable** — 3 pts
10. **Story 11 - Optimize kiosk image loading and display** — 5 pts

## Sprint 6 Total

**44 story points**  
**10 stories**

## Sprint Outcome

By the end of Sprint 6, the hub should have ready/pending/failed/rejected image states, KB-versioned image assets, publish invalidation, asset lifecycle logging, optimized compressed renditions, and basic admin status/confirmation visibility. The kiosk should safely handle broken or unavailable images and preserve text-only fallback behavior.

---

# Sprint 7 — Jun 8–Jun 14

## Sprint Goal

Deliver the core multimodal image workflow before the feature-complete cutoff. This sprint should focus on image embeddings, text-to-image retrieval, evidence response integration, image-first behavior, and kiosk display.

## Assigned Stories

### Slice 7C — Image Embeddings & Semantic Retrieval

1. **Story 2 - Implement image embedding generation service** — 8 pts
2. **Story 3 - Persist image embeddings with model and KB version metadata** — 8 pts
3. **Story 4 - Generate image embeddings during ingest or publish** — 5 pts
4. **Story 5 - Implement text-to-image semantic retrieval path** — 8 pts
5. **Story 6 - Merge image evidence with text evidence response structure** — 5 pts
6. **Story 7 - Apply filtering and validation gates to image retrieval** — 5 pts
7. **Story 8 - Add image retrieval thresholds and deterministic tie-breaks** — 3 pts
8. **Story 9 - Log image retrieval evidence and model metadata** — 3 pts

### Slice 7D — Kiosk Image Rendering & Multimodal Demo

9. **Story 1 - Render image evidence in kiosk responses** — 8 pts
10. **Story 3 - Support image-first response behavior** — 5 pts

## Sprint 7 Total

**58 story points**  
**10 stories**

## Sprint Outcome

By the end of Sprint 7, the hub should be able to encode image assets during ingest/publish, persist image embeddings, retrieve image evidence from English text queries, enforce filtering/validation, return image evidence to the kiosk, and support image-first behavior. The kiosk should be able to render image evidence for the demo path.

## Moved to Sprint 8 as Testing/Benchmarking Tasks

These are not planned feature-development stories in Sprint 8. Their intent should be covered by Sprint 8 validation tasks:

- **Slice 7C - Story 10 - Create image retrieval evaluation set** — 3 pts
- **Slice 7D - Story 8 - Create multimodal regression test set** — 5 pts
- **Slice 7D - Story 9 - Log kiosk image display outcomes** — 3 pts

---

# Sprint 8 — Jun 15–Jun 20

## Sprint Goal

Validate, benchmark, stabilize, and submit. This sprint should include no planned feature development. Work should focus on end-to-end testing, benchmarking, regression, critical/blocking bug fixes, documentation, and final submission readiness.

## Assigned Work

These should be Jira **Tasks**, **Bugs**, or **Test tasks**, not feature stories.

### End-to-End Testing

1. **Run full text-query E2E test**
   - query input
   - normalize
   - intent
   - retrieval
   - response
   - logs

2. **Run clarification E2E test**
   - ambiguous query
   - clarification chips
   - retry contract
   - resumed retrieval
   - logged resolution

3. **Run hybrid retrieval E2E test**
   - exact-term query
   - vector + lexical candidates
   - RRF/fusion output
   - filter enforcement
   - contribution logs

4. **Run compound query E2E test**
   - top-2 intent detection
   - path-level retrieval
   - deterministic merge
   - primary/secondary evidence
   - merge logs

5. **Run multimodal E2E test**
   - image upload
   - thumbnail/compressed rendition generation
   - image embedding generation
   - text-to-image retrieval
   - kiosk rendering
   - image-first response behavior

### Benchmarking

6. **Benchmark query latency**
   - p50/p95 total query latency
   - p50/p95 retrieval latency
   - rewrite/clarification latency where applicable

7. **Benchmark hybrid and multi-path retrieval**
   - vector-only vs hybrid
   - single-path vs multi-path
   - exact-term and compound evaluation sets

8. **Benchmark image retrieval**
   - image embedding generation time
   - text-to-image retrieval latency
   - top-k image retrieval accuracy
   - stability for fixed KB/model/config

9. **Benchmark kiosk image loading**
   - thumbnail load time
   - compressed rendition load time
   - placeholder/fallback behavior

### Regression + Submission

10. **Run regression suite against fixed KB snapshot**
11. **Generate final KPI report by KB version**
12. **Verify hub logs are readable during demo flow**
13. **Validate image retrieval evaluation set**
14. **Validate multimodal regression set**
15. **Verify kiosk image display outcomes**
16. **Fix critical/blocking bugs only**
17. **Freeze codebase**
18. **Prepare final submission package**
19. **Run final demo rehearsal**

## Sprint 8 Total

**0 planned feature story points**  
**19 testing/stabilization tasks**

## Sprint Outcome

By June 20, ResKiosk should have been tested end-to-end, benchmarked, regression-checked, stabilized, packaged, and prepared for final codebase submission. No planned feature development should remain in Sprint 8.

---

# Overall Assignment Summary

| Sprint   | Stories / Tasks | Story Points | Main Output                                      |
| -------- | --------------: | -----------: | ------------------------------------------------ |
| Sprint 1 |       8 stories |           44 | Pipeline + filtering foundation — delivered      |
| Sprint 2 |       9 stories |           53 | Clarification UX + validation/publish foundation |
| Sprint 3 |      11 stories |           59 | Validation completion + hybrid retrieval/logging |
| Sprint 4 |      13 stories |           63 | Multi-path retrieval + observability             |
| Sprint 5 |      17 stories |           87 | Metrics wrap-up + multimodal schema/assets prep  |
| Sprint 6 |      10 stories |           44 | Image asset completion + admin/kiosk safety prep |
| Sprint 7 |      10 stories |           58 | Multimodal image workflow + kiosk image display  |
| Sprint 8 |        19 tasks |            0 | E2E, benchmarking, regression, final submission  |
| **Total Required Feature Scope** | **78 feature stories + 19 final tasks** | **408** | **Feature-complete by Jun 14; final submission by Jun 20** |

---

# Deferred / Stretch Backlog

These items are not required for the June 20 MVP submission.

## Slice 6B — Safe Caching

1. **Story 1 - Define version-aware cache key structure** — 5 pts
2. **Story 2 - Implement response-level cache storage** — 8 pts
3. **Story 3 - Add TTL policy and cache bypass rules** — 5 pts
4. **Story 4 - Invalidate cache on KB publish** — 5 pts
5. **Story 5 - Invalidate cache on config update** — 5 pts
6. **Story 6 - Log cache hit, miss, and bypass decisions** — 3 pts
7. **Story 7 - Add safety re-validation for cached high-stakes responses** — 8 pts
8. **Story 8 - Add cache behavior tests** — 5 pts

**Deferred total:** 44 pts

## Other Stretch Items

1. **Slice 4 - Story 7 - Tune feedback-adjusted ranking as a separate layer** — 5 pts

**Additional deferred/stretch total:** 5 pts

## Moved to Sprint 8 as Testing/Benchmarking Tasks

These are no longer planned feature-development stories before June 14, but their intent should be covered by Sprint 8 validation tasks:

1. **Slice 7C - Story 10 - Create image retrieval evaluation set** — 3 pts
2. **Slice 7D - Story 8 - Create multimodal regression test set** — 5 pts
3. **Slice 7D - Story 9 - Log kiosk image display outcomes** — 3 pts

**Testing-task equivalent total:** 11 pts

## Total Deferred / Stretch / Reclassified

**60 story points**

---

# Risk Notes

## Capacity Risk

The adjusted required feature scope totals **408 story points before Sprint 8**, with Sprint 8 reserved for validation and submission. This is still aggressive, but the most graduation-sensitive weeks are now lighter than the original plan.

## Highest-Risk Sprints

- **Sprint 5:** This is now the intentional heavy sprint. It front-loads multimodal schema, early asset work, model selection, kiosk payload prep, admin upload/confirmation, and demo scenario planning.
- **Sprint 7:** Even reduced compared with the original, this sprint still carries the core multimodal image workflow and must be protected from scope creep.
- **Sprint 4:** Multi-path retrieval plus observability remains integration-heavy.

## Recommended Buffer Strategy

- Keep Sprint 8 protected for E2E, benchmarking, regression, and final fixes.
- If Sprint 5 slips, preserve multimodal schema, evidence identity, image upload API, thumbnails, content hashing, and admin upload path before optional demo scenario expansion.
- If Sprint 6 slips, preserve processing states, KB version linkage, artifact invalidation, optimized renditions, and basic status visibility before polish.
- If Sprint 7 slips, preserve image embedding generation, text-to-image retrieval, kiosk image rendering, and image-first response behavior before expanded evaluation coverage.
- If Sprint 4 slips, preserve deterministic merge and structured logs before response polish.