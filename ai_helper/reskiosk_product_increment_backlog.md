# ResKiosk AAIH Increment — 90 Work Items Backlog

This file lists the current ResKiosk AAIH product increment backlog as Jira-ready work items grouped by execution slice/epic.

## Backlog Summary

- **Total work items:** 90
- **Total story points:** 468
- **Required MVP work items:** 78
- **Required MVP story points:** 401
- **Deferred/stretch work items:** 12
- **Deferred/stretch story points:** 67

## Slice Summary

| Slice / Epic | Goals | Work Items | Points | Required Points | Deferred Points |
|---|---|---:|---:|---:|---:|
| Slice 0 — Backbone Contract | Goal 12, Goal 10 | 3 | 18 | 18 | 0 |
| Slice 1 — Controlled Scope Foundation | Goal 7 | 5 | 26 | 26 | 0 |
| Slice 2 — Clarify-first UX | Goal 6, Goal 10, Goal 12 | 6 | 29 | 29 | 0 |
| Slice 3 — Trusted KB Publish | Goal 8, Goal 10 | 6 | 40 | 40 | 0 |
| Slice 4 — Deterministic Retrieval Core | Goal 4, Goal 7, Goal 9, Goal 10 | 7 | 37 | 32 | 5 |
| Slice 5 — Compound Correctness | Goal 5, Goal 4, Goal 7, Goal 10, Goal 12 | 8 | 42 | 42 | 0 |
| Slice 6A — Observability & Trust | Goal 10 | 9 | 40 | 40 | 0 |
| Slice 6B — Safe Caching | Goal 11 | 8 | 44 | 0 | 44 |
| Slice 7A — Multimodal Schema | Goal 3, Goal 10 | 7 | 34 | 34 | 0 |
| Slice 7B — Image Asset Lifecycle | Goal 2, Goal 10, Goal 11 | 10 | 52 | 47 | 5 |
| Slice 7C — Image Embeddings & Semantic Retrieval | Goal 1, Goal 7, Goal 8, Goal 10 | 10 | 53 | 53 | 0 |
| Slice 7D — Kiosk Image Rendering & Multimodal Demo | Goal 1, Goal 2, Goal 10 | 11 | 53 | 40 | 13 |

---

# Slice 0 — Backbone Contract

**Related goals:** Goal 12, Goal 10

| ID | Work Item | Points | Status | Sprint | Labels | Acceptance Snapshot |
|---|---|---:|---|---|---|---|
| 0.1 | **Create canonical pipeline orchestrator** | 8 | Required | Sprint 1 | `backend, pipeline, goal-12, slice-0` | Route all hub query handling through one canonical pipeline path; preserve existing /query behavior; prove stage order with tests. |
| 0.2 | **Add pipeline stage logging skeleton** | 5 | Required | Sprint 1 | `backend, logging, pipeline, goal-10, slice-0` | Capture normalized query, intent, clarification trigger, rewrite state, retrieval source/score where available; keep payload bounded. |
| 0.3 | **Add clarification pause state to query flow** | 5 | Required | Sprint 1 | `backend, api, clarification, pipeline, goal-6, goal-12, slice-0` | Return structured needs-clarification response; skip rewrite/retrieval while paused; include resume context; keep non-clarification flow unchanged. |

---

# Slice 1 — Controlled Scope Foundation

**Related goals:** Goal 7

| ID | Work Item | Points | Status | Sprint | Labels | Acceptance Snapshot |
|---|---|---:|---|---|---|---|
| 1.1 | **Define taxonomy v1 data model** | 5 | Required | Sprint 1 | `backend, db, taxonomy, filtering, goal-7, slice-1` | Represent stable taxonomy IDs, labels, intent mappings, and chip compatibility without breaking current retrieval. |
| 1.2 | **Add metadata fields for retrieval filtering** | 8 | Required | Sprint 1 | `backend, db, db-migration, metadata, filtering, goal-7, slice-1` | Add taxonomy, authority/source, and scope/context metadata; backfill safely; preserve text-only retrieval. |
| 1.3 | **Enforce hard retrieval rules** | 5 | Required | Sprint 1 | `backend, retrieval, filtering, safety-critical, goal-7, slice-1` | Exclude enabled=false and non-published content before UI/inferred filters; log exclusion reasons; preserve valid published results. |
| 1.4 | **Apply UI and inferred intent filters with precedence** | 5 | Required | Sprint 1 | `backend, retrieval, filtering, taxonomy, logging, goal-7, slice-1` | Apply hard > UI > inferred precedence deterministically; log filter source and decisions. |
| 1.5 | **Log filter decisions and candidate counts** | 3 | Required | Sprint 1 | `backend, logging, filtering, observability, goal-7, goal-10, slice-1` | Log hard rules, selected taxonomy node, inferred nodes, candidate counts, widening/fallback events, and query-log linkage. |

---

# Slice 2 — Clarify-first UX

**Related goals:** Goal 6, Goal 10, Goal 12

| ID | Work Item | Points | Status | Sprint | Labels | Acceptance Snapshot |
|---|---|---:|---|---|---|---|
| 2.1 | **Implement clarification trigger policy** | 5 | Required | Sprint 2 | `backend, intent, clarification, logging, goal-6, goal-10, goal-12, slice-2` | Trigger on low confidence, unclear intent + low score, or missing required scope; use stable reason codes and deterministic behavior. |
| 2.2 | **Return taxonomy-backed clarification chips** | 5 | Required | Sprint 2 | `backend, api, clarification, taxonomy, goal-6, goal-7, goal-12, slice-2` | Return 2–3 stable chip options mapped to taxonomy nodes; mark request as paused; deterministic chip ordering. |
| 2.3 | **Add kiosk clarification chip UI** | 5 | Required | Sprint 2 | `kiosk, ui, clarification, android, goal-6, slice-2` | Show prompt and 2–3 selectable chips; submit selected option; avoid final answer until resolved. |
| 2.4 | **Implement clarification retry contract** | 8 | Required | Sprint 2 | `backend, api, kiosk, clarification, pipeline, goal-6, goal-12, slice-2` | Send selected option and original context; resolve selection to taxonomy/intent; resume pipeline only after clarification is resolved. |
| 2.5 | **Persist clarification resolution** | 3 | Required | Sprint 2 | `backend, db, logging, clarification, goal-6, goal-10, slice-2` | Store option ID/label or recoverable label, session ID, resolved intent/taxonomy, language, and query-log linkage. |
| 2.6 | **Log clarification lifecycle events** | 3 | Required | Sprint 2 | `backend, logging, clarification, pipeline, goal-6, goal-10, goal-12, slice-2` | Log trigger, reason codes, options, selection, resolved node/intent, and proof that rewrite/retrieval waited. |

---

# Slice 3 — Trusted KB Publish

**Related goals:** Goal 8, Goal 10

| ID | Work Item | Points | Status | Sprint | Labels | Acceptance Snapshot |
|---|---|---:|---|---|---|---|
| 3.1 | **Implement metadata validation rule engine** | 8 | Required | Sprint 2 | `backend, validation, metadata, kb-publish, safety-critical, goal-8, slice-3` | Evaluate taxonomy, authority, scope, caption/label quality; return rule ID, severity, result, message; offline deterministic behavior. |
| 3.2 | **Add validation status and audit storage** | 8 | Required | Sprint 2 | `backend, db, db-migration, validation, audit, goal-8, goal-10, slice-3` | Persist approved/quarantined/needs_review/rejected states, rule results, review decisions, and KB version/publish attempt linkage. |
| 3.3 | **Gate KB publish using validation results** | 8 | Required | Sprint 3 | `backend, api, kb-publish, validation, safety-critical, goal-8, slice-3` | Run validation before publish; return pass/blocked/warning; quarantine excluded from retrieval; preserve current published KB on failure. |
| 3.4 | **Build MVP metadata review workflow** | 8 | Required | Sprint 3 | `console, backend, api, validation, review-workflow, audit, goal-8, slice-3` | List quarantined/needs-review items; approve/reject/override with reason; write audit trail. |
| 3.5 | **Exclude quarantined metadata from retrieval** | 5 | Required | Sprint 3 | `backend, retrieval, filtering, validation, safety-critical, goal-7, goal-8, slice-3` | Ignore quarantined/rejected metadata in resident retrieval while approved metadata remains usable; log validation-state exclusions. |
| 3.6 | **Log validation and publish audit events** | 3 | Required | Sprint 3 | `backend, logging, audit, validation, kb-publish, goal-8, goal-10, slice-3` | Log run ID/version, checked counts, status counts, modality/taxonomy breakdown, publish outcome, and review links. |

---

# Slice 4 — Deterministic Retrieval Core

**Related goals:** Goal 4, Goal 7, Goal 9, Goal 10

| ID | Work Item | Points | Status | Sprint | Labels | Acceptance Snapshot |
|---|---|---:|---|---|---|---|
| 4.1 | **Build lexical retrieval index** | 8 | Required | Sprint 3 | `backend, retrieval, bm25, lexical-search, kb-version, goal-4, slice-4` | Build rebuildable version-aware lexical index from defined KB fields; fallback safely if missing/stale; log index behavior. |
| 4.2 | **Implement BM25-like lexical scoring** | 5 | Required | Sprint 3 | `backend, retrieval, bm25, ranking, logging, goal-4, slice-4` | Return top-k lexical IDs/scores/ranks; deterministic tokenization/normalization; handle empty results; capture latency. |
| 4.3 | **Fuse lexical and vector results with RRF** | 8 | Required | Sprint 3 | `backend, retrieval, fusion, rrf, vector-search, bm25, goal-4, goal-9, slice-4` | Fuse lexical/vector rankings with explicit strategy; log parameters; handle overlap and single-path cases; stable tie-breaks. |
| 4.4 | **Apply filter policy to hybrid retrieval** | 5 | Required | Sprint 3 | `backend, retrieval, filtering, hybrid-search, safety-critical, goal-4, goal-7, goal-8, slice-4` | Apply hard/UI/inferred filters to lexical and vector paths; never return disabled/unpublished/quarantined evidence. |
| 4.5 | **Add hybrid retrieval contribution logging** | 3 | Required | Sprint 3 | `backend, logging, retrieval, observability, fusion, goal-4, goal-10, slice-4` | Log lexical top-k, vector top-k, fusion strategy/params, fused top-k, tie-break decisions; cap stored top-k. |
| 4.6 | **Create exact-term retrieval evaluation set** | 3 | Required | Sprint 3 | `backend, testing, evaluation, retrieval, goal-4, goal-9, goal-10, slice-4` | Create fixed queries with expected evidence IDs; compare vector-only vs hybrid; report accuracy/stability. |
| 4.7 | **Tune feedback-adjusted ranking as a separate layer** | 5 | Stretch/Deferred | Stretch | `backend, retrieval, feedback-bias, ranking, logging, safety-critical, goal-9, slice-4` | Keep feedback bias configurable, bounded, post-candidate, filter-safe, and logged with baseline/bias/final score. |

---

# Slice 5 — Compound Correctness

**Related goals:** Goal 5, Goal 4, Goal 7, Goal 10, Goal 12

| ID | Work Item | Points | Status | Sprint | Labels | Acceptance Snapshot |
|---|---|---:|---|---|---|---|
| 5.1 | **Detect compound queries using top-2 intents** | 5 | Required | Sprint 4 | `backend, intent, compound-query, logging, goal-5, goal-10, slice-5` | Expose top-2 intents/confidences; set compound flag above thresholds; preserve single-path flow otherwise; log thresholds. |
| 5.2 | **Build intent-scoped retrieval path queries** | 5 | Required | Sprint 4 | `backend, retrieval, compound-query, pipeline, filtering, goal-5, goal-7, goal-12, slice-5` | Create deterministic path query per intent with enrichment/constraints; respect clarification selection and filters; log path queries. |
| 5.3 | **Run retrieval separately per compound path** | 8 | Required | Sprint 4 | `backend, retrieval, multi-path, hybrid-search, logging, goal-5, goal-4, goal-7, goal-10, slice-5` | Run retrieval per path; apply filters per path; return top-k IDs/scores/ranks/candidate counts; handle zero-result path. |
| 5.4 | **Merge compound path results deterministically** | 8 | Required | Sprint 4 | `backend, retrieval, multi-path, merge, ranking, safety-critical, goal-5, goal-10, slice-5` | Implement explicit priority, dedupe, tie-breaks; prioritize safety/medical when present; log merge decisions. |
| 5.5 | **Add evidence attribution for compound results** | 5 | Required | Sprint 4 | `backend, retrieval, evidence, logging, observability, goal-5, goal-10, slice-5` | Attach producing path/intent, path rank/score, merged rank/score; preserve duplicate visibility; cap top-k. |
| 5.6 | **Support primary and secondary compound response outputs** | 5 | Required | Sprint 4 | `backend, api, response-formatting, compound-query, safety-critical, goal-5, slice-5` | Represent primary/secondary evidence/guidance; allow medical/safety to become primary; preserve single-intent behavior. |
| 5.7 | **Log compound lifecycle and merge decisions** | 3 | Required | Sprint 4 | `backend, logging, multi-path, compound-query, observability, goal-5, goal-10, slice-5` | Log compound trigger, intents/confidences, path queries/results, merge strategy, dedupe, final ordering, and query-log link. |
| 5.8 | **Create compound retrieval evaluation scenarios** | 3 | Required | Sprint 4 | `backend, testing, evaluation, compound-query, goal-5, goal-10, slice-5` | Create 3–5 scenarios with expected primary/secondary evidence; compare single vs multi-path; confirm deterministic ranking. |

---

# Slice 6A — Observability & Trust

**Related goals:** Goal 10

| ID | Work Item | Points | Status | Sprint | Labels | Acceptance Snapshot |
|---|---|---:|---|---|---|---|
| 6A.1 | **Complete structured query log schema** | 8 | Required | Sprint 4 | `backend, db, logging, observability, metrics, goal-10, slice-6a` | Capture request ID, timestamp, KB version, normalized query, intent(s), clarification/rewrite/retrieval/filter/hybrid/multi-path metadata. |
| 6A.2 | **Add latency breakdown logging** | 5 | Required | Sprint 4 | `backend, logging, latency, performance, observability, goal-10, slice-6a` | Capture overall/retrieval/rewrite/clarification/hybrid/multi-path timings; use null/absent for missing stages. |
| 6A.3 | **Capture final evidence list and stability fields** | 5 | Required | Sprint 4 | `backend, logging, evidence, retrieval, stability, goal-10, slice-6a` | Log final evidence IDs, ranks, scores, modality, and path attribution; cap top-k. |
| 6A.4 | **Implement MVP metrics export workflow** | 5 | Required | Sprint 5 | `backend, metrics, export, evaluation, observability, goal-10, slice-6a` | Export/query metrics by KB version, intent, modality; include evidence stability and latency; run locally. |
| 6A.5 | **Create grounding proxy review fields** | 3 | Required | Sprint 5 | `backend, metrics, grounding, review, trust, goal-10, slice-6a` | Support retrieved evidence links, manual supported/unsupported labels, reviewer notes, filtering by KB version/intent; no hot-path LLM. |
| 6A.6 | **Create fixed evaluation query set** | 3 | Required | Sprint 5 | `backend, testing, evaluation, metrics, goal-10, slice-6a` | Include exact-term, compound, clarification, safety/medical queries with expected evidence/behavior; version with code/test assets. |
| 6A.7 | **Generate basic KPI report by KB version** | 5 | Required | Sprint 5 | `backend, metrics, reporting, kpi, observability, goal-10, slice-6a` | Report counts, p50/p95 latency, retrieval latency, fallbacks, clarification triggers, evidence stability/match where available. |
| 6A.8 | **Add failure and fallback outcome logging** | 3 | Required | Sprint 4 | `backend, logging, failure-handling, fallback, observability, goal-10, slice-6a` | Log failures, reason codes, failed stage, partial logs, and session/query linkage. |
| 6A.9 | **Format hub query logs for readable operational observability** | 3 | Required | Sprint 4 | `backend, logging, observability, hub, developer-experience, operations, goal-10, slice-6a` | Make live hub/log stream readable with stable IDs, stage labels, outcomes, source/score/version, and no large/raw payloads. |

---

# Slice 6B — Safe Caching

**Related goals:** Goal 11

| ID | Work Item | Points | Status | Sprint | Labels | Acceptance Snapshot |
|---|---|---:|---|---|---|---|
| 6B.1 | **Define version-aware cache key structure** | 5 | Stretch/Deferred | Stretch | `backend, caching, kb-version, config-version, pipeline, goal-11, slice-6b` | Key by normalized query, resolved intent/compound, filters, KB version, config version/hash; bypass/log if components missing. |
| 6B.2 | **Implement response-level cache storage** | 8 | Stretch/Deferred | Stretch | `backend, caching, performance, response-cache, evidence, goal-11, slice-6b` | Store response object/evidence refs with KB/config version and TTL; avoid caching ambiguous pre-clarification or error responses. |
| 6B.3 | **Add TTL policy and cache bypass rules** | 5 | Stretch/Deferred | Stretch | `backend, caching, ttl, safety-critical, logging, goal-11, slice-6b` | Implement default TTL, expiry, clarification/missing-version bypass, safety-critical bypass/revalidation, and bypass logging. |
| 6B.4 | **Invalidate cache on KB publish** | 5 | Stretch/Deferred | Stretch | `backend, caching, kb-publish, kb-version, invalidation, goal-11, slice-6b` | Invalidate older KB-version entries; never serve across KB version; fail closed if invalidation fails. |
| 6B.5 | **Invalidate cache on config update** | 5 | Stretch/Deferred | Stretch | `backend, caching, config-version, structured-config, invalidation, goal-11, slice-6b` | Change config version/hash on relevant updates; prevent reuse of prior config entries; log invalidation/bypass. |
| 6B.6 | **Log cache hit, miss, and bypass decisions** | 3 | Stretch/Deferred | Stretch | `backend, caching, logging, observability, goal-11, goal-10, slice-6b` | Log hit/miss/bypass, key hash, decomposed key factors, TTL/age, reason, and query-log linkage. |
| 6B.7 | **Add safety re-validation for cached high-stakes responses** | 8 | Stretch/Deferred | Stretch | `backend, caching, safety-critical, retrieval, validation, logging, goal-11, slice-6b` | Identify safety intents; compare retrieval/evidence signature before cache serve; bypass/recompute on mismatch; log result. |
| 6B.8 | **Add cache behavior tests** | 5 | Stretch/Deferred | Stretch | `backend, testing, caching, invalidation, observability, goal-11, slice-6b` | Test same-key hit, KB/config version miss, no cache for clarification-pending, TTL expiry, and cache logging. |

---

# Slice 7A — Multimodal Schema

**Related goals:** Goal 3, Goal 10

| ID | Work Item | Points | Status | Sprint | Labels | Acceptance Snapshot |
|---|---|---:|---|---|---|---|
| 7A.1 | **Add multimodal KB item schema** | 8 | Required | Sprint 5 | `backend, db, db-migration, multimodal, schema, goal-3, slice-7a` | Represent modality text/image; preserve text articles; support image refs; stable evidence IDs; future segmentation; additive/backward-compatible migration. |
| 7A.2 | **Add stable multimodal evidence identity** | 5 | Required | Sprint 5 | `backend, db, evidence, multimodal, logging, goal-3, goal-10, slice-7a` | Maintain text IDs, define image evidence identity, tie IDs to KB version, keep source_id compatibility, stable within version. |
| 7A.3 | **Prepare image asset reference fields** | 5 | Required | Sprint 5 | `backend, db, image-assets, multimodal, schema, goal-3, goal-2, slice-7a` | Support image asset/key references, future thumbnail/original refs, safe handling of missing/broken refs, kiosk-compatible shape. |
| 7A.4 | **Add forward-compatible segmentation fields** | 3 | Required | Sprint 5 | `backend, db, schema, future-compatible, no-chunking, goal-3, slice-7a` | Add parent/source and segment/chunk fields without enabling semantic chunking; document inactive status; preserve retrieval unit. |
| 7A.5 | **Update evidence response contract for modality** | 5 | Required | Sprint 5 | `backend, api, evidence, multimodal, logging, goal-3, goal-10, slice-7a` | Include evidence_id and modality; keep text compatibility; allow image asset/render refs; log modality. |
| 7A.6 | **Backfill existing KB articles as text modality** | 5 | Required | Sprint 5 | `backend, db, db-migration, backfill, text-evidence, goal-3, slice-7a` | Mark/represent existing articles as text; preserve enabled/status/embeddings/responses; safe existing DB migration. |
| 7A.7 | **Add modality-aware evidence logging** | 3 | Required | Sprint 5 | `backend, logging, evidence, multimodal, observability, goal-3, goal-10, slice-7a` | Record evidence modality with IDs; support mixed evidence; cap top-k; preserve legacy log compatibility. |

---

# Slice 7B — Image Asset Lifecycle

**Related goals:** Goal 2, Goal 10, Goal 11

| ID | Work Item | Points | Status | Sprint | Labels | Acceptance Snapshot |
|---|---|---:|---|---|---|---|
| 7B.1 | **Store image assets as first-class KB assets** | 8 | Required | Sprint 6 | `backend, db, image-assets, multimodal, goal-2, slice-7b` | Store stable asset ID, original ref, MIME type, size, timestamp; link to KB/evidence; exclude broken assets. |
| 7B.2 | **Add image upload API for KB assets** | 5 | Required | Sprint 6 | `backend, api, image-upload, image-assets, validation, goal-2, slice-7b` | Accept supported formats, validate size/MIME, store original ref, create asset record, return status/errors, log failures. |
| 7B.3 | **Generate content hashes for image assets** | 3 | Required | Sprint 6 | `backend, image-assets, content-hash, integrity, goal-2, slice-7b` | Generate/store deterministic hash; define duplicate behavior; block readiness/log on hash failure; usable for cache/artifact identity. |
| 7B.4 | **Generate deterministic thumbnails for image assets** | 8 | Required | Sprint 6 | `backend, image-assets, thumbnail, kiosk, logging, goal-2, slice-7b` | Generate fixed thumbnail rendition; store ref; deterministic output; log failures; mark processing state appropriately. |
| 7B.5 | **Add image asset processing states** | 5 | Required | Sprint 6 | `backend, db, image-assets, processing-state, safety-critical, goal-2, goal-8, slice-7b` | Support pending/ready/failed/rejected; only ready assets resident-facing; publish avoids partial assets; log transitions/reasons. |
| 7B.6 | **Link image assets to KB version** | 5 | Required | Sprint 6 | `backend, db, kb-version, image-assets, audit, goal-2, goal-10, slice-7b` | Tie assets/artifacts to KB version; stable refs within version; logs identify version; old assets not current unless valid. |
| 7B.7 | **Invalidate image artifacts on KB publish** | 5 | Required | Sprint 6 | `backend, kb-publish, kb-version, image-assets, invalidation, goal-2, goal-11, slice-7b` | Invalidate/refresh prior-version image artifacts; include KB version/hash in keys; fail closed on invalidation failure; log events. |
| 7B.8 | **Add admin asset confirmation view** | 5 | Stretch/Deferred | Stretch | `console, image-assets, admin, thumbnail, goal-2, slice-7b` | Show upload status, original/thumbnail preview/ref, hash/identity, errors, and readiness confirmation. |
| 7B.9 | **Log image asset lifecycle events** | 3 | Required | Sprint 6 | `backend, logging, image-assets, audit, observability, goal-2, goal-10, slice-7b` | Log upload, thumbnail generation, processing transitions, validation/readiness failures, invalidation; join by asset ID/version. |
| 7B.10 | **Compress uploaded images and generate optimized renditions** | 5 | Required | Sprint 6 | `backend, image-assets, compression, renditions, thumbnail, performance, logging, goal-2, slice-7b` | Generate compressed display-size rendition, deterministic settings, store ref/dimensions/size/hash, preserve aspect ratio, log failures. |

---

# Slice 7C — Image Embeddings & Semantic Retrieval

**Related goals:** Goal 1, Goal 7, Goal 8, Goal 10

| ID | Work Item | Points | Status | Sprint | Labels | Acceptance Snapshot |
|---|---|---:|---|---|---|---|
| 7C.1 | **Select and configure image embedding model** | 5 | Required | Sprint 5 | `backend, ml-model, clip, siglip, image-search, spike, goal-1, slice-7c` | Document model choice, local loading path, version logging, preprocessing, smoke test, and licensing/deployment constraints. |
| 7C.2 | **Implement image embedding generation service** | 8 | Required | Sprint 7 | `backend, image-search, embeddings, ml-model, multimodal, logging, goal-1, slice-7c` | Load model, accept ready asset, preprocess image, return vector dimension, handle failures safely, log model/version/errors. |
| 7C.3 | **Persist image embeddings with model and KB version metadata** | 8 | Required | Sprint 7 | `backend, db, embeddings, image-search, kb-version, goal-1, goal-2, goal-8, slice-7c` | Store embeddings with asset/evidence ID, KB version, model version; invalidate/regenerate on changes; exclude unsafe assets. |
| 7C.4 | **Generate image embeddings during ingest or publish** | 5 | Required | Sprint 7 | `backend, image-search, embeddings, kb-publish, logging, goal-1, goal-2, slice-7c` | Process eligible ready assets during ingest/publish; don't expose until ready/unavailable; deterministic behavior; log events. |
| 7C.5 | **Implement text-to-image semantic retrieval path** | 8 | Required | Sprint 7 | `backend, retrieval, image-search, multimodal, safety-critical, goal-1, goal-7, goal-8, slice-7c` | Encode English query, return top-k image IDs/scores/ranks/render refs; threshold low confidence; deterministic tie-breaks; enforce gates. |
| 7C.6 | **Merge image evidence with text evidence response structure** | 5 | Required | Sprint 7 | `backend, api, evidence, multimodal, logging, goal-1, goal-3, goal-10, slice-7c` | Include image_evidence with ID/modality/score/rank/render ref; deterministic mixed ordering; preserve text-only responses. |
| 7C.7 | **Apply filtering and validation gates to image retrieval** | 5 | Required | Sprint 7 | `backend, retrieval, filtering, validation, image-search, safety-critical, goal-1, goal-7, goal-8, slice-7c` | Exclude disabled/unpublished/quarantined/rejected/non-ready images; apply filters; log candidate counts/decisions. |
| 7C.8 | **Add image retrieval thresholds and deterministic tie-breaks** | 3 | Required | Sprint 7 | `backend, retrieval, image-search, thresholds, determinism, logging, goal-1, slice-7c` | Configure similarity threshold, possible-match behavior, near-tie rule, score/evidence_id tie-breaks; log decisions. |
| 7C.9 | **Log image retrieval evidence and model metadata** | 3 | Required | Sprint 7 | `backend, logging, image-search, observability, goal-1, goal-10, slice-7c` | Log normalized query, model/version, top-k image IDs/scores/ranks, thresholds, display/suppression, latency, query-log link. |
| 7C.10 | **Create image retrieval evaluation set** | 3 | Required | Sprint 7 | `backend, testing, evaluation, image-search, multimodal, goal-1, goal-10, slice-7c` | Create landmark/first-aid/navigation queries with expected top-1/top-3 image IDs; fixed snapshot; report accuracy/stability. |

---

# Slice 7D — Kiosk Image Rendering & Multimodal Demo

**Related goals:** Goal 1, Goal 2, Goal 10

| ID | Work Item | Points | Status | Sprint | Labels | Acceptance Snapshot |
|---|---|---:|---|---|---|---|
| 7D.1 | **Render image evidence in kiosk responses** | 8 | Required | Sprint 7 | `kiosk, android, ui, image-rendering, multimodal, goal-1, goal-2, slice-7d` | Render hub image evidence, prefer thumbnails, associate with answer, handle missing/broken refs, preserve text-only rendering, no public internet dependency. |
| 7D.2 | **Add hub-to-kiosk image evidence payload support** | 5 | Required | Sprint 5 | `kiosk, android, api, multimodal, image-rendering, goal-1, goal-2, goal-3, slice-7d` | Kiosk response model supports image evidence ID/modality/score/rank/render refs; prefer thumbnail; preserve text payload compatibility. |
| 7D.3 | **Support image-first response behavior** | 5 | Required | Sprint 7 | `kiosk, backend, api, image-first, clarification, logging, goal-1, goal-6, goal-10, slice-7d` | Hub marks image-first; kiosk displays with minimal text; no authoritative low-confidence matches; near-ties can show options/clarify; log behavior. |
| 7D.4 | **Handle image loading failures and placeholders** | 3 | Required | Sprint 6 | `kiosk, android, ui, image-rendering, error-handling, goal-1, goal-2, slice-7d` | Show placeholder/hide image block on missing refs; fallback to original if allowed; no crash; keep text visible; log/report errors. |
| 7D.5 | **Add admin image upload and asset confirmation path** | 8 | Stretch/Deferred | Stretch | `console, backend, api, image-upload, image-assets, admin, goal-2, slice-7d` | Console upload, original/thumbnail preview, hash/identity, KB/taxonomy linkage, clear error display/logs. |
| 7D.6 | **Display image asset status in admin console** | 5 | Stretch/Deferred | Stretch | `console, admin, image-assets, processing-state, validation, goal-2, goal-8, slice-7d` | Show pending/ready/failed/rejected, error reason, publish eligibility, KB/taxonomy linkage, backend consistency. |
| 7D.7 | **Create multimodal demo scenarios** | 3 | Required | Sprint 5 | `demo, testing, evaluation, image-search, multimodal, goal-1, goal-10, slice-7d` | Include landmark, navigation, first-aid scenarios with expected image evidence; fixed KB/assets; repeatable deterministic demo. |
| 7D.8 | **Create multimodal regression test set** | 5 | Required | Sprint 7 | `testing, evaluation, regression, kiosk, image-rendering, multimodal, goal-1, goal-10, slice-7d` | Regression tests for image queries, hub payload fields, kiosk render/safe handling, fixed KB/model/config. |
| 7D.9 | **Log kiosk image display outcomes** | 3 | Required | Sprint 7 | `kiosk, logging, image-rendering, observability, goal-1, goal-10, slice-7d` | Log displayed/suppressed/failed/placeholder outcomes, displayed evidence ID, query/session linkage where feasible, no raw image data. |
| 7D.10 | **Validate text-only fallback when image evidence is unavailable** | 3 | Required | Sprint 6 | `kiosk, backend, fallback, image-rendering, safety-critical, goal-1, slice-7d` | Text answer still works if no image/retrieval failure/invalid image; suppress bad images; log fallback reason; hide technical errors. |
| 7D.11 | **Optimize kiosk image loading and display** | 5 | Required | Sprint 6 | `kiosk, android, image-rendering, compression, performance, safety-critical, goal-1, goal-2, slice-7d` | Prefer thumbnail/display rendition, preserve aspect ratio, allow larger/original only if allowed, no generative enhancement, render safety/medical/maps faithfully. |

---

# Recommended Sprint Allocation

## Sprint 1

**Total:** 44 story points, 8 work items

| ID | Work Item | Points | Slice |
|---|---|---:|---|
| 0.1 | Create canonical pipeline orchestrator | 8 | Slice 0 — Backbone Contract |
| 0.2 | Add pipeline stage logging skeleton | 5 | Slice 0 — Backbone Contract |
| 0.3 | Add clarification pause state to query flow | 5 | Slice 0 — Backbone Contract |
| 1.1 | Define taxonomy v1 data model | 5 | Slice 1 — Controlled Scope Foundation |
| 1.2 | Add metadata fields for retrieval filtering | 8 | Slice 1 — Controlled Scope Foundation |
| 1.3 | Enforce hard retrieval rules | 5 | Slice 1 — Controlled Scope Foundation |
| 1.4 | Apply UI and inferred intent filters with precedence | 5 | Slice 1 — Controlled Scope Foundation |
| 1.5 | Log filter decisions and candidate counts | 3 | Slice 1 — Controlled Scope Foundation |

## Sprint 2

**Total:** 45 story points, 8 work items

| ID | Work Item | Points | Slice |
|---|---|---:|---|
| 2.1 | Implement clarification trigger policy | 5 | Slice 2 — Clarify-first UX |
| 2.2 | Return taxonomy-backed clarification chips | 5 | Slice 2 — Clarify-first UX |
| 2.3 | Add kiosk clarification chip UI | 5 | Slice 2 — Clarify-first UX |
| 2.4 | Implement clarification retry contract | 8 | Slice 2 — Clarify-first UX |
| 2.5 | Persist clarification resolution | 3 | Slice 2 — Clarify-first UX |
| 2.6 | Log clarification lifecycle events | 3 | Slice 2 — Clarify-first UX |
| 3.1 | Implement metadata validation rule engine | 8 | Slice 3 — Trusted KB Publish |
| 3.2 | Add validation status and audit storage | 8 | Slice 3 — Trusted KB Publish |

## Sprint 3

**Total:** 56 story points, 10 work items

| ID | Work Item | Points | Slice |
|---|---|---:|---|
| 3.3 | Gate KB publish using validation results | 8 | Slice 3 — Trusted KB Publish |
| 3.4 | Build MVP metadata review workflow | 8 | Slice 3 — Trusted KB Publish |
| 3.5 | Exclude quarantined metadata from retrieval | 5 | Slice 3 — Trusted KB Publish |
| 3.6 | Log validation and publish audit events | 3 | Slice 3 — Trusted KB Publish |
| 4.1 | Build lexical retrieval index | 8 | Slice 4 — Deterministic Retrieval Core |
| 4.2 | Implement BM25-like lexical scoring | 5 | Slice 4 — Deterministic Retrieval Core |
| 4.3 | Fuse lexical and vector results with RRF | 8 | Slice 4 — Deterministic Retrieval Core |
| 4.4 | Apply filter policy to hybrid retrieval | 5 | Slice 4 — Deterministic Retrieval Core |
| 4.5 | Add hybrid retrieval contribution logging | 3 | Slice 4 — Deterministic Retrieval Core |
| 4.6 | Create exact-term retrieval evaluation set | 3 | Slice 4 — Deterministic Retrieval Core |

## Sprint 4

**Total:** 66 story points, 13 work items

| ID | Work Item | Points | Slice |
|---|---|---:|---|
| 5.1 | Detect compound queries using top-2 intents | 5 | Slice 5 — Compound Correctness |
| 5.2 | Build intent-scoped retrieval path queries | 5 | Slice 5 — Compound Correctness |
| 5.3 | Run retrieval separately per compound path | 8 | Slice 5 — Compound Correctness |
| 5.4 | Merge compound path results deterministically | 8 | Slice 5 — Compound Correctness |
| 5.5 | Add evidence attribution for compound results | 5 | Slice 5 — Compound Correctness |
| 5.6 | Support primary and secondary compound response outputs | 5 | Slice 5 — Compound Correctness |
| 5.7 | Log compound lifecycle and merge decisions | 3 | Slice 5 — Compound Correctness |
| 5.8 | Create compound retrieval evaluation scenarios | 3 | Slice 5 — Compound Correctness |
| 6A.1 | Complete structured query log schema | 8 | Slice 6A — Observability & Trust |
| 6A.2 | Add latency breakdown logging | 5 | Slice 6A — Observability & Trust |
| 6A.3 | Capture final evidence list and stability fields | 5 | Slice 6A — Observability & Trust |
| 6A.8 | Add failure and fallback outcome logging | 3 | Slice 6A — Observability & Trust |
| 6A.9 | Format hub query logs for readable operational observability | 3 | Slice 6A — Observability & Trust |

## Sprint 5

**Total:** 63 story points, 14 work items

| ID | Work Item | Points | Slice |
|---|---|---:|---|
| 6A.4 | Implement MVP metrics export workflow | 5 | Slice 6A — Observability & Trust |
| 6A.5 | Create grounding proxy review fields | 3 | Slice 6A — Observability & Trust |
| 6A.6 | Create fixed evaluation query set | 3 | Slice 6A — Observability & Trust |
| 6A.7 | Generate basic KPI report by KB version | 5 | Slice 6A — Observability & Trust |
| 7A.1 | Add multimodal KB item schema | 8 | Slice 7A — Multimodal Schema |
| 7A.2 | Add stable multimodal evidence identity | 5 | Slice 7A — Multimodal Schema |
| 7A.3 | Prepare image asset reference fields | 5 | Slice 7A — Multimodal Schema |
| 7A.4 | Add forward-compatible segmentation fields | 3 | Slice 7A — Multimodal Schema |
| 7A.5 | Update evidence response contract for modality | 5 | Slice 7A — Multimodal Schema |
| 7A.6 | Backfill existing KB articles as text modality | 5 | Slice 7A — Multimodal Schema |
| 7A.7 | Add modality-aware evidence logging | 3 | Slice 7A — Multimodal Schema |
| 7C.1 | Select and configure image embedding model | 5 | Slice 7C — Image Embeddings & Semantic Retrieval |
| 7D.2 | Add hub-to-kiosk image evidence payload support | 5 | Slice 7D — Kiosk Image Rendering & Multimodal Demo |
| 7D.7 | Create multimodal demo scenarios | 3 | Slice 7D — Kiosk Image Rendering & Multimodal Demo |

## Sprint 6

**Total:** 58 story points, 12 work items

| ID | Work Item | Points | Slice |
|---|---|---:|---|
| 7B.1 | Store image assets as first-class KB assets | 8 | Slice 7B — Image Asset Lifecycle |
| 7B.2 | Add image upload API for KB assets | 5 | Slice 7B — Image Asset Lifecycle |
| 7B.3 | Generate content hashes for image assets | 3 | Slice 7B — Image Asset Lifecycle |
| 7B.4 | Generate deterministic thumbnails for image assets | 8 | Slice 7B — Image Asset Lifecycle |
| 7B.5 | Add image asset processing states | 5 | Slice 7B — Image Asset Lifecycle |
| 7B.6 | Link image assets to KB version | 5 | Slice 7B — Image Asset Lifecycle |
| 7B.7 | Invalidate image artifacts on KB publish | 5 | Slice 7B — Image Asset Lifecycle |
| 7B.9 | Log image asset lifecycle events | 3 | Slice 7B — Image Asset Lifecycle |
| 7B.10 | Compress uploaded images and generate optimized renditions | 5 | Slice 7B — Image Asset Lifecycle |
| 7D.4 | Handle image loading failures and placeholders | 3 | Slice 7D — Kiosk Image Rendering & Multimodal Demo |
| 7D.10 | Validate text-only fallback when image evidence is unavailable | 3 | Slice 7D — Kiosk Image Rendering & Multimodal Demo |
| 7D.11 | Optimize kiosk image loading and display | 5 | Slice 7D — Kiosk Image Rendering & Multimodal Demo |

## Sprint 7

**Total:** 69 story points, 13 work items

| ID | Work Item | Points | Slice |
|---|---|---:|---|
| 7C.2 | Implement image embedding generation service | 8 | Slice 7C — Image Embeddings & Semantic Retrieval |
| 7C.3 | Persist image embeddings with model and KB version metadata | 8 | Slice 7C — Image Embeddings & Semantic Retrieval |
| 7C.4 | Generate image embeddings during ingest or publish | 5 | Slice 7C — Image Embeddings & Semantic Retrieval |
| 7C.5 | Implement text-to-image semantic retrieval path | 8 | Slice 7C — Image Embeddings & Semantic Retrieval |
| 7C.6 | Merge image evidence with text evidence response structure | 5 | Slice 7C — Image Embeddings & Semantic Retrieval |
| 7C.7 | Apply filtering and validation gates to image retrieval | 5 | Slice 7C — Image Embeddings & Semantic Retrieval |
| 7C.8 | Add image retrieval thresholds and deterministic tie-breaks | 3 | Slice 7C — Image Embeddings & Semantic Retrieval |
| 7C.9 | Log image retrieval evidence and model metadata | 3 | Slice 7C — Image Embeddings & Semantic Retrieval |
| 7C.10 | Create image retrieval evaluation set | 3 | Slice 7C — Image Embeddings & Semantic Retrieval |
| 7D.1 | Render image evidence in kiosk responses | 8 | Slice 7D — Kiosk Image Rendering & Multimodal Demo |
| 7D.3 | Support image-first response behavior | 5 | Slice 7D — Kiosk Image Rendering & Multimodal Demo |
| 7D.8 | Create multimodal regression test set | 5 | Slice 7D — Kiosk Image Rendering & Multimodal Demo |
| 7D.9 | Log kiosk image display outcomes | 3 | Slice 7D — Kiosk Image Rendering & Multimodal Demo |

## Stretch

**Total:** 67 story points, 12 work items

| ID | Work Item | Points | Slice |
|---|---|---:|---|
| 4.7 | Tune feedback-adjusted ranking as a separate layer | 5 | Slice 4 — Deterministic Retrieval Core |
| 6B.1 | Define version-aware cache key structure | 5 | Slice 6B — Safe Caching |
| 6B.2 | Implement response-level cache storage | 8 | Slice 6B — Safe Caching |
| 6B.3 | Add TTL policy and cache bypass rules | 5 | Slice 6B — Safe Caching |
| 6B.4 | Invalidate cache on KB publish | 5 | Slice 6B — Safe Caching |
| 6B.5 | Invalidate cache on config update | 5 | Slice 6B — Safe Caching |
| 6B.6 | Log cache hit, miss, and bypass decisions | 3 | Slice 6B — Safe Caching |
| 6B.7 | Add safety re-validation for cached high-stakes responses | 8 | Slice 6B — Safe Caching |
| 6B.8 | Add cache behavior tests | 5 | Slice 6B — Safe Caching |
| 7B.8 | Add admin asset confirmation view | 5 | Slice 7B — Image Asset Lifecycle |
| 7D.5 | Add admin image upload and asset confirmation path | 8 | Slice 7D — Kiosk Image Rendering & Multimodal Demo |
| 7D.6 | Display image asset status in admin console | 5 | Slice 7D — Kiosk Image Rendering & Multimodal Demo |

## Sprint 8

Sprint 8 is intentionally reserved for end-to-end testing, benchmarking, regression, critical/blocking bug fixes, code freeze, demo rehearsal, and final submission packaging. It should contain no planned feature story points.
