# ResKiosk Hub — Query + Response Logging Flow (Current Codebase)

This document describes (as implemented today) how kiosk queries are processed by the Hub, how responses are shaped, and how **`query_logs`**, **FAQ tracking**, and **RLHF-style feedback bias** are recorded and applied.

Primary code references:

- `hub/api/routes_query.py` — `/query`, `/feedback`, `/faq/suggestions`
- `hub/models/api_models.py` — request/response payload schemas
- `hub/retrieval/search.py` — retrieval scoring, `confidence_raw`, RLHF bias application, clarification gating
- `hub/retrieval/rlhf_bias.py` — periodic rebuild of `article_biases` from `feedback_logs`
- `hub/db/schema.py` — ORM models for `query_logs`, `feedback_logs`, `article_biases`, `faq_tracker`

---

## 1) End-to-end query pipeline (Hub)

Entry route: `POST /query` in `hub/api/routes_query.py`.

High-level flow:

1. Receive kiosk query payload (`QueryRequest`)
2. Choose raw text:
   - Prefer `transcript_english` if present; else use `transcript_original`
3. If `language != "en"`, translate inbound text to English (NLLB layer via `translator.translate`)
4. Call retrieval: `search.retrieve(...)`
5. If retrieval returns `NO_MATCH` or `NEEDS_CLARIFICATION`, attempt a rewrite via `query_rewriter.maybe_rewrite(...)` and (if rewritten) retry retrieval once
6. If a verified KB article was returned (`DIRECT_MATCH` + `article_data`), optionally format the answer with the LLM formatter (`formatter.format_response(...)`)
7. Optionally translate the final answer back to `language`
8. Persist a `query_logs` row and return `QueryResponse`

---

## 2) Request and response payload shapes

### 2.1 `QueryRequest` (kiosk → hub)

Defined in `hub/models/api_models.py` (`QueryRequest`).

Key fields (as used by the hub):

- `transcript_original`: the kiosk’s original transcript
- `transcript_english`: optional pre-translated transcript
- `language`: kiosk-reported language of the resident’s request
- `kb_version`: kiosk KB version (for hub-side logging + versioning context)
- `is_retry`, `selected_category`, `exclude_source_ids`: used to support clarification flows and “next result” retry behavior
- `session_id`: used for in-memory history (LLM formatting context)

### 2.2 `QueryResponse` (hub → kiosk)

Defined in `hub/models/api_models.py` (`QueryResponse`).

Returned fields:

- `answer_text_en`: authoritative English answer text
- `answer_text_localized`: optional translated answer (if translation changed the output)
- `answer_type`: `DIRECT_MATCH | NEEDS_CLARIFICATION | NO_MATCH`
- `confidence`: retrieval confidence score (see scoring below)
- `source_id`: KB article ID selected as evidence (when applicable)
- `clarification_categories`: list of category strings for clarification UI (when applicable)
- `query_log_id`: DB ID for correlating feedback
- `rlhf_top_source_id`, `rlhf_top_score`: “shadow” RLHF top pick fields (see RLHF section)
- `follow_up_prompt`, `follow_up_intent`: compound-intent follow-up prompt fields (when applicable)

---

## 3) How `query_logs` is written (and what’s stored)

`query_logs` is written inside `POST /query` after the answer is produced.

ORM model: `hub/db/schema.py` `QueryLog` (table `query_logs`).

Values written by the route (not exhaustive of all columns that exist):

- `kiosk_id`, `session_id`
- `transcript_original`
- `raw_transcript`: the raw input text used before translation selection
- `transcript_english`: the English text used for retrieval (translated or already English)
- `normalized_transcript`: currently set to the same value as `transcript_english` in the route (not necessarily the `normalize_query(...)` output)
- `language`
- `kb_version`
- `answer_type`
- `source_id`
- `rewrite_attempted`, `rewritten_query` (if a rewrite occurred)
- `latency_ms`
- `retrieval_score`: set from `confidence_raw` if present, otherwise `confidence`
- RLHF shadow fields: `rlhf_top_source_id`, `rlhf_top_score`

---

## 4) Retrieval scoring: `confidence`, `confidence_raw`, and `retrieval_score`

Retrieval implementation: `hub/retrieval/search.py` `retrieve(...)`.

### 4.1 Vector similarity baseline

- A query vector is computed via `embedder.embed_text(search_query)`.
- Similarity is computed as cosine similarity against the cached corpus embedding matrix:
  - `scores = util.cos_sim(query_vec, corpus["matrix"])[0].numpy()`
- These cosine similarities are in practice treated as a score in \([0, 1]\) by later clamping behavior (see RLHF adjustment).

### 4.2 RLHF-style bias adjustment (optional; env gated)

If `RESKIOSK_RLHF_ENABLED=true`:

1. A cached bias map `{source_id: bias}` is loaded via `_get_article_biases(db)` (TTL-based cache).
2. Each article score is adjusted:

   \[
   \text{adj} = \text{raw\_cosine} + (\text{RLHF\_ALPHA} \times \text{bias})
   \]

3. The adjusted score is clamped to \([0, 1]\).

Notes:

- When RLHF is disabled or fails, `scores` remain as raw cosine scores.
- The “shadow” fields `rlhf_top_source_id` / `rlhf_top_score` are always populated:
  - if RLHF is enabled, they reflect the RLHF-adjusted top-1
  - otherwise, they default to the raw cosine top-1

### 4.3 `confidence` vs `confidence_raw`

`hub/retrieval/search.py` returns both:

- `confidence`: the **best.score** after any RLHF adjustment (if enabled)
- `confidence_raw`: `best_raw_score`, i.e., the raw cosine max score (before RLHF)

These are returned on all terminal outcomes (`DIRECT_MATCH`, `NEEDS_CLARIFICATION`, `NO_MATCH`) when scores exist.

### 4.4 What gets persisted as `query_logs.retrieval_score`

In `hub/api/routes_query.py`, the value stored is:

- `confidence_raw` if present, else `confidence`

So `query_logs.retrieval_score` is intended to represent the **raw retrieval similarity** even if RLHF bias later affects which answer is chosen.

---

## 5) Clarification and gating (how `answer_type` is chosen)

In `hub/retrieval/search.py`:

- Thresholds depend on language (English vs non-English); the caller passes `query_language`.
- The top result `best.score` is compared against:
  - `threshold` (default `RESKIOSK_SIM_THRESHOLD`, typically 0.60)
  - `clarification_floor` (default `RESKIOSK_CLARIFICATION_FLOOR`, typically 0.40)
- If `needs_clarification(...)` returns true and score is in the band, the hub returns `NEEDS_CLARIFICATION`.

Note: this is the current behavior; future Slice 0 / Goal 12 work will restructure this flow.

---

## 6) FAQ tracking (`faq_tracker`)

After inserting `query_logs`, the route upserts `faq_tracker` for direct matches:

- Keyed by `source_id` (KB article ID) and stores:
  - count, first/last timestamps
  - snapshot display strings (source question, answer snippet)
  - last asked user query (normalized/display)

Endpoints:

- `GET /faq/suggestions` returns top-N most-asked questions (suggestion chips)
- Admin endpoints exist for viewing/deleting FAQ tracker entries (`routes_admin.py`)

---

## 7) Feedback → `feedback_logs` → `article_biases` (RLHF-style loop)

### 7.1 Capturing feedback (`/feedback`)

Route: `POST /feedback` in `hub/api/routes_query.py`.

- Inserts a `feedback_logs` row with:
  - `query_log_id` (correlates to `query_logs.id`)
  - `source_id` (KB article ID being rated)
  - `label` (negative/positive integer; current convention: -1 dislike, +1 like)
  - plus kiosk/session/language metadata

This endpoint only records feedback; it does **not** directly update `article_biases` inline.

### 7.2 Rebuilding biases over time (`hub/retrieval/rlhf_bias.py`)

Bias updates are computed by an offline/periodic rebuild:

- Script function: `rebuild()`
- Computes lifetime counts per article:
  - `pos` = number of feedback rows where `label > 0`
  - `neg` = number of feedback rows where `label < 0`
- If total events \(n = pos + neg\) is less than `RESKIOSK_RLHF_MIN_EVENTS` (default 3):
  - bias decays toward 0: `combined = DECAY_FACTOR * prev_bias`
- Otherwise:
  - compute a smoothed log-ratio:
    \[
    raw = \log\left(\frac{pos + 1}{neg + 1}\right)
    \]
  - blend with a decayed previous bias:
    \[
    combined = (\text{DECAY\_FACTOR} \times prev\_bias) + (1 - \text{DECAY\_FACTOR}) \times raw
    \]
- Clamp final bias to \([-1, 1]\)
- Upsert into `article_biases` and delete biases for KB articles that no longer exist.

### 7.3 Applying biases in retrieval (`hub/retrieval/search.py`)

When RLHF is enabled:

- `article_biases` is loaded into an in-memory dict cache with TTL (`RESKIOSK_RLHF_BIAS_TTL_SECS`, default 1800s).
- Bias influences ranking via the adjusted score:
  - `adj = raw_cosine + RLHF_ALPHA * bias` (clamped to \([0, 1]\))

This is why the system can become “feedback-shaped” over time even though the base retrieval is cosine similarity.

---

## 8) Important caveats (current state)

- `query_logs.normalized_transcript` is currently set in the route to `text` and may not represent the same “normalized” string used in retrieval internals.
- `query_logs.formatter_mode`, `stt_mode`, `tts_mode`, `connectivity_state`, and `cloud_consent_mode` exist in the schema but are not currently populated in the `POST /query` insert path shown above.
- The “canonical pipeline order” (Goal 12) is not fully enforced by current code; clarification and rewrite behavior are implemented as described in `routes_query.py` + `search.py`.

