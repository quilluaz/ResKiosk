---
title: "Validation Pipeline — Trusted KB Publish Gate"
aliases: ["validation", "metadata validation", "publish gate", "quarantine"]
tags: [type/architecture, component/hub, layer/validation, sprint/2, sprint/3, slice/3]
sprint: 2
generated_at: "2026-05-15T08:48:57Z"
generated: true
---

# Validation Pipeline — Trusted KB Publish Gate

Built across **Sprint 2** (Stories 3.1, 3.2) and **Sprint 3** (Stories 3.3–3.6).

ResKiosk's validation pipeline ensures that only quality-checked KB articles are published and retrievable. The system validates metadata, enforces safety rules, and provides a human review workflow for edge cases.

---

## Architecture overview

```
KB Article (draft/updated)
    ↓
[Metadata Validation Rule Engine] (Story 3.1)
    ├─→ Taxonomy rules
    ├─→ Authority/scope rules
    ├─→ Content quality rules
    ↓
Validation Result: approved | needs_review | quarantined | rejected
    ↓
[Validation Status Storage] (Story 3.2)
    ↓
[Publish Gate] (Story 3.3)
    ├─→ PASS → publish proceeds
    ├─→ WARNING → publish proceeds with flag
    ├─→ BLOCKED → publish aborted, return failure_reasons
    ↓
[Review Workflow] (Story 3.4) — human operator reviews quarantined/needs_review
    ├─→ approve → status = approved
    ├─→ reject → status = rejected
    ├─→ override → status = approved + reason logged
    ↓
[Retrieval Exclusion] (Story 3.5)
    └─→ Quarantined/rejected articles NEVER retrievable
```

---

## Components

### 1. Metadata Validation Rule Engine (`hub/validation/metadata.py`)

**Function:** `validate_metadata(targets, known_ids, active_ids)`

**Evaluates 10 rules** across three categories:

#### Taxonomy assignment rules
- **Rule T1:** All assigned taxonomy nodes must exist in `taxonomy_v1.json`
- **Rule T2:** All assigned nodes must be active (not deprecated)
- **Rule T3:** At least one primary taxonomy node must be assigned

#### Authority/scope rules
- **Rule A1:** `authority_level` must be a known value (e.g., `official`, `community`, `inferred`)
- **Rule A2:** `scope` must be a known value (e.g., `general`, `shelter_specific`, `emergency`)

#### Content quality rules
- **Rule Q1:** `question` field must not be empty
- **Rule Q2:** `answer` field must not be empty
- **Rule Q3:** `question` must be at least 10 characters
- **Rule Q4:** `answer` must be at least 20 characters
- **Rule Q5:** If multimodal (`image_asset_id` present), caption/label must exist

**Severity levels:**
- `ERROR` → triggers `quarantined` status
- `WARNING` → triggers `needs_review` status

**Output:** `MetadataValidationRun` containing:
- `run_id`: UUID
- `timestamp`: ISO-8601
- `items`: List of `MetadataValidationItem` (one per article)

Each `MetadataValidationItem` includes:
- `article_id`
- `status`: `approved` | `needs_review` | `quarantined` | `rejected`
- `rule_results`: List of `RuleResult` (rule_id, severity, passed, message)

**Offline behavior:** Runs deterministically without DB writes; results are stored separately.

---

### 2. Validation Status Storage (`hub/db/schema.py`)

**Table:** `kb_item_validation_status`

Schema:
```sql
CREATE TABLE kb_item_validation_status (
    id INTEGER PRIMARY KEY,
    kb_item_id INTEGER NOT NULL,
    status TEXT NOT NULL,  -- 'approved', 'needs_review', 'quarantined', 'rejected'
    kb_version INTEGER,
    created_at INTEGER,
    FOREIGN KEY (kb_item_id) REFERENCES kb_articles(id)
);
```

**Persistence:** Each validation run writes a row per article. The **latest** row (by `id DESC`) is authoritative.

**Audit trail:** Historical rows are preserved for publish attempt reconstruction.

---

### 3. Publish Gate (`hub/api/routes_admin.py`)

**Endpoint:** `POST /admin/publish`

**Process:**
1. Load validation targets from `kb_articles`
2. Run `validate_metadata()`
3. Check gate status:
   - **PASS:** No quarantined items → proceed to publish
   - **WARNING:** Some `needs_review` items → proceed but flag in response
   - **BLOCKED:** Any `quarantined` items → abort, return HTTP 422 with `failure_reasons`
4. If PASS/WARNING:
   - Increment `SystemVersion.kb_version`
   - Rebuild semantic corpus
   - Rebuild lexical index (Sprint 3)
   - Write publish audit log (Story 3.6, in progress)

**Response:**
```json
{
  "status": "blocked",
  "kb_version": 7,
  "failure_reasons": [
    "Article 42: Rule T1 failed (unknown taxonomy node)",
    "Article 89: Rule Q2 failed (answer too short)"
  ]
}
```

**Safety guarantee:** Quarantined articles are **never** published, even with `enabled=1`.

---

### 4. Review Workflow (`hub/validation/review.py`)

**Functions:**
- `build_review_queue(db)` — returns items with `status IN ('quarantined', 'needs_review')`, excluding already-approved items
- `build_article_validation_detail(db, kb_item_id)` — returns full validation results and review history for a specific article

**Review actions:**
- **Approve:** Override validation failure, set `status = approved`
- **Reject:** Confirm validation failure, set `status = rejected`
- **Override:** Approve with logged reason (e.g., "False positive: shelter-specific abbreviation")

**Audit table:** `kb_review_decisions`

Schema (inferred):
```sql
CREATE TABLE kb_review_decisions (
    id INTEGER PRIMARY KEY,
    kb_item_id INTEGER NOT NULL,
    kb_version INTEGER,
    reviewer TEXT,
    action TEXT,  -- 'approved', 'rejected', 'override'
    reason TEXT,
    created_at INTEGER,
    FOREIGN KEY (kb_item_id) REFERENCES kb_articles(id)
);
```

> 🔍 Inferred: Console UI for review workflow (Story 3.4) is likely in progress. Backend API routes exist in `routes_admin.py`.

---

### 5. Retrieval Exclusion (`hub/retrieval/search.py`, `hub/retrieval/lexical.py`)

**Function:** `_get_quarantined_item_ids(db)`

**What it does:**
- Queries `kb_item_validation_status` for latest rows with `status IN ('quarantined', 'rejected')`
- Returns a set of article IDs to exclude from retrieval
- **Cached** for performance (TTL: 1800s, reuses `RLHF_BIAS_TTL_SECS`)

**Integration:**
- **Lexical index build** (Story 4.1): `LexicalIndex.build(db, excluded_ids=quarantined_ids)` — quarantined articles never enter the index
- **Vector corpus build** (existing): Quarantined articles excluded from semantic corpus
- **Hard filter precedence:** Quarantine exclusion runs **before** UI and inferred filters

**Safety guarantee:** Even if an article has `enabled=1`, it will **never** be retrieved if quarantined/rejected.

**Logging:** Exclusions logged with reason code `hard_rule:quarantined` or `hard_rule:rejected`.

---

## Configuration

No environment variables (hardcoded rules and severity levels).

**Taxonomy reference:** `hub/taxonomy/taxonomy_v1.json`

---

## Observability (Story 3.6, in progress)

**Publish audit log** (target structure):
- Run ID / UUID
- Attempting user
- Target `kb_version`
- Total articles checked
- Counts per status: `approved`, `quarantined`, `needs_review`, `rejected`
- Publish outcome: `pass`, `blocked`, `warning`
- `failure_reasons` (if blocked)

> 🔍 Inferred: Story 3.6 (validation and publish audit events) is listed as active in Sprint 3. Schema and logging wiring are likely in progress but not yet fully committed as of 2026-05-15.

---

## Validation rule details

| Rule ID | Severity | Check | Example failure |
|---------|----------|-------|----------------|
| **T1** | ERROR | Taxonomy node exists | `rk.tax.unknown` |
| **T2** | WARNING | Taxonomy node is active | `rk.tax.deprecated.old_category` |
| **T3** | ERROR | At least one taxonomy node assigned | `taxonomy_node_ids = []` |
| **A1** | WARNING | `authority_level` is known | `authority_level = "unofficial"` |
| **A2** | WARNING | `scope` is known | `scope = "invalid_scope"` |
| **Q1** | ERROR | `question` not empty | `question = ""` |
| **Q2** | ERROR | `answer` not empty | `answer = ""` |
| **Q3** | WARNING | `question` length ≥ 10 | `question = "Food?"` |
| **Q4** | WARNING | `answer` length ≥ 20 | `answer = "In cafeteria"` |
| **Q5** | WARNING | Multimodal items have caption | `image_asset_id != null` but `caption = ""` |

**Status assignment logic:**
- Any ERROR → `quarantined`
- Any WARNING (no ERRORs) → `needs_review`
- All PASS → `approved`

---

## Data models

See [[10-architecture/data-models]] for full schema.

**New tables (Sprint 2-3):**
- `kb_item_validation_status` — validation results per article
- `kb_review_decisions` — human review audit trail

**New columns (Sprint 2, Slice 3 foundation):**
- `kb_articles.authority_level` — source authority metadata
- `kb_articles.scope` — applicability scope metadata
- `kb_articles.taxonomy_node_ids` — JSON array of taxonomy IDs

---

## Related notes

- [[10-architecture/data-models]] — full schema including validation tables
- [[10-architecture/hybrid-retrieval]] — quarantine exclusion in lexical index (Story 3.5)
- [[20-sprints/sprint-2/user-stories]] — Stories 3.1, 3.2
- [[20-sprints/sprint-3/user-stories]] — Stories 3.3, 3.4, 3.5, 3.6
- [[30-decisions/slice-3]] — Slice 3 design decisions
