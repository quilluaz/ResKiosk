# Slice / goal context (ResKiosk hackathon)

This file tracks active implementation context when `slice0_userstory_running_context.md` is product-wide and a slice-specific file is needed.

## Sprint 3 — Slice 4 Story 6 (Person 4): Exact-term retrieval evaluation set

### User story (maintainer)

Provide a small, reproducible evaluation set to measure whether hybrid retrieval improves accuracy on exact-term queries without breaking semantic retrieval.

### Subtasks

- [x] Define fixed KB snapshot + query labels (proper noun, procedure, location, mixed, semantic).
- [x] Attach expected evidence article IDs and per-query synthetic cosine scores (corpus order).
- [x] Implement runner comparing vector-only (lexical disabled) vs hybrid (BM25 + RRF).
- [x] Emit top-1 / top-k accuracy and stability metrics for semantic-tagged queries.
- [x] Add automated tests guarding the fixture behavior.

### Decisions

- **Synthetic vector scores** in JSON (per query, aligned with `corpus_article_order`) keep results reproducible across machines without pinning embedding models.
- **SQLite in-memory** DB seeds the same article text the lexical index uses, so BM25 matches the snapshot while the vector path stays fully controlled via patches.
- **Top-1 accuracy** is computed from **fusion rank-1** (`fusion_top_k_ids[0]`), not `source_id`, so scores reflect ranking quality even when clarification gating fires.
- **Stability** (queries with `stability_check: true`): hybrid rank of the gold article must be ≤ vector-only rank (same fusion list semantics with lexical empty for vector-only).

### Completed

- `hub/eval/data/exact_term_retrieval_eval_v1.json` — snapshot + queries.
- `hub/eval/exact_term_retrieval_eval.py` — `run_eval()`, CLI `python -m hub.eval.exact_term_retrieval_eval`.
- `hub/tests/test_exact_term_retrieval_eval.py` — regression tests.

### Remaining

- None for this story scope.

### Story implementation summary

Delivered a versioned JSON fixture (`eval_version`, `snapshot_id`, `kb_version`) and a Python harness that invalidates retrieval caches, builds an in-memory KB, runs each query under vector-only vs hybrid patches, and prints JSON including per-query breakdowns, aggregate top-1/top-k accuracy, and stability counts. Same KB version + same env defaults (`RESKIOSK_*` logged in report) yields reproducible metrics; changing thresholds or RRF env vars is visible in the emitted `config` block.

On the bundled v1 fixture (default env), a sample run produced: vector-only top-1 ≈ 33% and top-k 100%; hybrid top-1 and top-k both 100%; both stability-checked semantic queries preserved gold rank (hybrid rank ≤ vector rank).
