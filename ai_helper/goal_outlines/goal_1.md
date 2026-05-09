# Goal 1 — Semantic image search (CLIP/SigLIP)

### 1) Outcome

Enable **image ↔ text semantic search** so the hub can retrieve relevant KB image evidence for an English query, using a vision-language embedding model (e.g., **CLIP / SigLIP**).

- **What changes**: images become semantically retrievable evidence (not just static attachments).
- **Who benefits**: shelter residents (navigation + first-aid visuals), operators (clearer guidance delivery), maintainers (measurable multimodal retrieval behavior).
- **What success looks like**:
  - given an English query, retrieval returns relevant image results with **stable evidence IDs/refs** and **scores**
  - directional / landmark queries and first-aid queries retrieve correct images in top results on a defined test set

---

### 2) Why this matters

- **Current limitation**: retrieval is **text-embedding cosine similarity only**; there is **no image encoder** in the hub, so images cannot be searched semantically.
- **Risk addressed**: text-only answers are often insufficient for navigation or procedural tasks; low-utility answers increase retries and reduce trust.
- **Value**: provides reliable visual guidance (landmarks/buildings, first-aid steps) where imagery is the “ground truth” residents need to follow.

---

### 3) Scope

- Select and integrate a vision-language embedding model suitable for deployment constraints (e.g., CLIP/SigLIP).
- Generate and persist **image embeddings** during KB ingest/publish (or equivalent content pipeline step).
- Add an image-retrieval path that supports:
  - **text → image** search (required for Goal 1)
  - **image → image** (optional if it falls out naturally from the same vector space; not required for kiosk MVP)
- Return image evidence in a stable, loggable form (IDs/refs + scores) so downstream answer generation and kiosk UI can render images deterministically.
- Create a small, explicit evaluation set of image queries with expected top results for regression checks.

---

### 4) Non-goals

- Full “image storage as first-class assets” lifecycle (original + thumbnail + invalidation): covered by **Goal 2**.
- KB schema rework for multimodal items and forward-compatible modality modeling: covered by **Goal 3**.
- Hybrid BM25 + vector fusion and multi-path fan-out retrieval: covered by **Goals 4–5**.
- Multilingual image retrieval at the embedding boundary (global assumption remains **English at retrieval boundary**).
- Online learning/reranking for images (feedback bias remains separate backlog work).

---

### 5) System Impact

#### a. Data / Schema

- **New stored artifacts (minimum viable)**:
  - image embedding vector(s) for each KB image item (or each image asset that is eligible evidence)
  - an image evidence identifier that is stable across retrieval/logging and resolvable to a renderable asset
- **Versioning expectation**:
  - image embeddings must be attributable to a KB version / publish cycle for reproducibility (exact schema mechanics may be introduced in Goal 3; for Goal 1, log and persist enough to identify “which corpus” produced the result)

#### b. API / Interfaces

- **Hub retrieval interface**:
  - add a retrieval mode or evidence type that can return images as evidence items
  - return fields needed for downstream steps:
    - stable evidence ID/reference
    - modality/type indicator (image)
    - similarity score (and optionally rank)
    - render reference (URL/path/asset key) where available

#### c. UX / Behavior

- **Kiosk**:
  - when an answer cites image evidence, the kiosk can render it inline (exact “thumbnail/original” details belong to Goal 2)
  - if only images are relevant (e.g., “show me X building”), kiosk may display an image-first response with minimal text framing

---

### 6) Integration Points

- **Depends on / aligns with**:
  - Goal 10 (metrics/logging): image evidence IDs/scores must be logged
  - Goal 2 (image storage): once implemented, retrieval should return the asset refs expected by the kiosk (thumbnail/original)
  - Goal 3 (schema rework): modality-aware evidence references should converge to the unified KB item model
- **Affects**:
  - answer grounding/citations: “image evidence” must be traceable and stable for auditability
  - evaluation harness: adds a new modality to regression checks

---

### 7) Edge Cases / Failure Modes

- **No image candidates**:
  - return “no image evidence found” with a safe fallback (text-only retrieval/answer if available), and log the absence
- **Ambiguous visual query** (e.g., “show me the clinic” without which clinic):
  - surface clarification prompt if multiple near-ties exist and kiosk supports chips (Goal 6); otherwise return top-N with labels/captions if available
- **Low-confidence match**:
  - enforce a minimum similarity floor; below floor, do not present as authoritative “this is X”; instead present as “possible matches”
- **Mixed evidence**:
  - if both text and images are returned, ensure deterministic ordering and explicit modality labeling
- **Missing/broken render ref**:
  - if an image evidence item cannot be resolved to a renderable asset, drop it and log the reason (do not show broken UI)

---

### 8) Logging & Metrics

Log enough to debug multimodal retrieval behavior and support Goal 10 metrics:

- query:
  - normalized English query text (post-translation boundary)
  - resolved intent (if available at this stage) and session identifiers
  - KB version/config identifiers used for retrieval
- retrieval (image path):
  - model name/version used for image embeddings and query encoding
  - top-k image evidence IDs/refs with scores + ranks
  - thresholds applied (min score, cutoffs)
  - latency breakdown (image retrieval vs total retrieval)
- outcome:
  - whether the response displayed images, how many, and which evidence IDs were used

---

### 9) Determinism / Constraints

- **Stable ranking**: for a fixed KB version/config + fixed model weights, image retrieval results should be reproducible.
- **Tie-break rules**: define an explicit stable tie-break for identical (or near-identical) scores, e.g. `(score desc, evidence_id asc)`.
- **Safety constraints**:
  - do not over-assert identity on low-confidence matches
  - never return evidence that is disabled/unpublished (enforcement policy should align with Goal 7 hard rules once implemented)

---

### 10) Definition of Done (DoD)

- Hub supports text → image semantic retrieval with a selected vision-language model.
- Image embeddings are generated for eligible KB images and are queryable at runtime.
- Retrieval responses include stable image evidence IDs/refs and scores.
- A small evaluation set exists with expected top results; regression check can run deterministically on a fixed KB snapshot.
- Logging captures model/version, KB version/config, top-k evidence IDs/scores, and latency.

---

### 11) Open Decisions

- Which model to standardize on (CLIP vs SigLIP) given deployment constraints and licensing; what image preprocessing is required.
- Where image embeddings live in the system before Goal 3 schema unifies modality (temporary table vs extension to existing KB storage).
- Similarity floor / “possible matches” policy for low-confidence results.
- Whether to return top-1 only vs top-N images for image-first queries (and what N is kiosk-safe).

---

## Evaluation / Benchmark Plan

### Minimum viable evaluation set (v1)

- **Query types**:
  - landmark/building identification (“show me the Andres Bonifacio building”)
  - first aid (“how do I bandage a wound”)
  - directional/wayfinding within a shelter context (“where is the registration desk” when image evidence exists)
- **Dataset format**:
  - a fixed list of English queries
  - expected top-1 (or top-3) image evidence IDs
  - optional notes for acceptable alternates (near-duplicates)

### Pass/fail criteria (v1)

- Top-1 accuracy for a small curated set (or top-3 if the domain is inherently ambiguous).
- Regression guard: results for the fixed KB snapshot must not change without an intentional model/config change.

---

## Contract / Payload Shape

### Image evidence item (hub → kiosk / hub internal)

Minimum fields required for Goal 1 delivery:

- `evidence_id` (stable)
- `modality: "image"`
- `score` (similarity; numeric)
- `render_ref` (URL/path/asset key; exact shape can evolve with Goal 2)
- optional: `title` / `label` / `caption` if available, to help kiosk display a disambiguating list

### Retrieval response (image path)

- `image_evidence: [ ...image evidence items... ]`
- `kb_version` (and any config/version identifiers required for reproducibility + logging)

