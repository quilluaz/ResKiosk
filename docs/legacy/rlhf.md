# RLHF in ResKiosk (Current Implementation)

This document explains how "RLHF" currently works in ResKiosk today.

## Executive Summary

ResKiosk does **not** run full model fine-tuning RLHF.

What is implemented is an **RLHF-style retrieval bias layer**:
- Kiosk feedback (`thumbs up` / `thumbs down`) is logged.
- A periodic rebuild job converts feedback counts into per-article bias scores.
- During retrieval, cosine similarity can be adjusted using those bias scores.

So the learning effect is on **ranking KB articles**, not on training the LLM itself.

---

## Components

### 1) Feedback capture

**Kiosk**
- File: `kiosk/app/src/main/java/com/reskiosk/viewmodel/KioskViewModel.kt`
- User can rate assistant responses:
  - `sendFeedbackLike(...)` posts `label = +1`
  - `sendFeedbackDislike(...)` posts `label = -1`
- Payload includes:
  - `query_log_id`
  - `source_id`
  - `session_id`
  - `language`
  - `kiosk_id`
  - `center_id`

**Hub endpoint**
- File: `hub/api/routes_query.py`
- Endpoint: `POST /feedback`
- Stores entries in `feedback_logs`.

### 2) Data storage

**Schema**
- File: `hub/db/schema.py`

Relevant tables:
- `feedback_logs`
  - `query_log_id`, `source_id`, `label`, `language`, `kiosk_id`, `center_id`, `created_at`
- `article_biases`
  - `source_id` (PK), `bias`, `updated_at`
- `query_logs` (shadow analysis fields)
  - `rlhf_top_source_id`, `rlhf_top_score`

### 3) Bias rebuild job

**Rebuilder script**
- File: `hub/retrieval/rlhf_bias.py`
- Entry point: `rebuild()`
- This is **offline/periodic**, not auto-triggered per feedback event.

Algorithm per `source_id`:
1. Count positives (`label > 0`) and negatives (`label < 0`).
2. If events `< RESKIOSK_RLHF_MIN_EVENTS`:
   - decay previous bias toward 0
3. Else:
   - compute `raw = log((pos + 1) / (neg + 1))`
   - blend with previous bias using decay
4. Clamp final bias to `[-1, 1]`
5. Upsert into `article_biases`
6. Remove biases for deleted KB articles

Concurrency:
- Uses a lock file (`rlhf_bias.lock`) to avoid concurrent rebuilds.

### 4) Retrieval-time bias application

**Retriever**
- File: `hub/retrieval/search.py`
- In `retrieve(...)`, raw cosine scores are computed first.
- If RLHF is enabled:
  - load article biases (`article_biases`)
  - apply adjustment per article:
    - `adjusted = raw_cosine + RESKIOSK_RLHF_ALPHA * bias`
  - clamp adjusted score to `[0, 1]`
  - ranking/gating then uses adjusted scores
- If disabled/failure:
  - raw cosine scores are used

Bias cache:
- Bias rows are cached in memory with TTL (`RESKIOSK_RLHF_BIAS_TTL_SECS`).

---

## Environment Variables

### Retrieval-time controls (`hub/retrieval/search.py`)
- `RESKIOSK_RLHF_ENABLED` (default: `false`)
- `RESKIOSK_RLHF_ALPHA` (default: `0.10`)
- `RESKIOSK_RLHF_BIAS_TTL_SECS` (default: `1800`)

### Rebuild job controls (`hub/retrieval/rlhf_bias.py`)
- `RESKIOSK_RLHF_MIN_EVENTS` (default: `3`)
- `RESKIOSK_RLHF_DECAY` (default: `0.9`)
- `RESKIOSK_RLHF_LOCK_DIR` (default: current working directory)

---

## Operational Notes

### What improves immediately
- User `dislike` has an immediate UX effect because retry excludes previously selected `source_id` (`exclude_source_ids` flow).

### What improves over time
- Only after running the rebuild job will historical feedback change future ranking.

### Important limitation
- This is **ranking bias**, not policy/model fine-tuning RLHF.
- LLM generation style/content is unchanged by feedback unless article ranking changes.

---

## Runbook

### 1) Enable RLHF-style scoring in retrieval
Set env:
- `RESKIOSK_RLHF_ENABLED=true`
- optionally tune `RESKIOSK_RLHF_ALPHA`

### 2) Rebuild biases from feedback
Run:

```powershell
python -m hub.retrieval.rlhf_bias
```

### 3) Verify
- Check logs for:
  - `[RLHF] Loaded <n> article biases from DB.`
- Inspect DB:
  - `feedback_logs` contains events
  - `article_biases` has non-zero rows
- Query responses include:
  - `query_log_id`
  - `rlhf_top_source_id`
  - `rlhf_top_score`

---

## Current Gaps / Next Improvements

1. No automatic scheduler for rebuilds (cron/task scheduler should run `hub.retrieval.rlhf_bias`).
2. No per-intent/per-language bias segmentation (currently per-article global).
3. No admin observability page for bias values and feedback distribution.
4. No advanced credit assignment (single scalar label only).
5. No true LLM fine-tuning loop (this is retrieval-ranker adaptation only).

---

## Cloud Metadata in Query Logs (Currently Unused)

Cloud integration is currently disabled. The following `query_logs` fields may exist in schema but are not actively populated by cloud routes:
- `formatter_mode`
- `stt_mode`
- `tts_mode`
- `connectivity_state`
- `cloud_consent_mode`

These fields are orthogonal to RLHF behavior; RLHF scoring logic is unchanged.
