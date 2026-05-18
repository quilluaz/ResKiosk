---
title: "Data Models — Database Schema"
aliases: ["data models", "database schema", "db schema"]
tags: [type/architecture, component/hub, layer/db, status/active]
generated_at: "2026-05-15T08:48:57Z"
generated: true
---

# Data Models — Database Schema

**File:** `hub/db/schema.py`  
**Database:** SQLite  
**Updated:** Sprint 1 (Stories 1.1, 1.2), Sprint 2 (clarification + validation tables), Sprint 3 (6A.1 — 15 structured logging columns; validation completion)  
**Status:** Active

---

## Taxonomy data model (Sprint 1, Story 1.1)

ResKiosk uses a hierarchical taxonomy system for categorizing KB items and controlling retrieval filtering.

### TaxonomyNode

**Purpose:** Represents a single taxonomy category node

```python
class TaxonomyNode(Base):
    __tablename__ = "taxonomy_nodes"
    
    id = Column(String, primary_key=True)  # e.g. rk.tax.health_medical.medical_services
    label = Column(Text, nullable=False)   # Human-readable, e.g. "Medical Services"
    description = Column(Text, nullable=True)
    is_active = Column(Integer, default=1)  # 1=active, 0=inactive
    sort_order = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Key design decisions:**
- **Stable string IDs** — IDs like `rk.tax.food.meals.breakfast` survive label changes
- **Hierarchical naming** — Dot notation indicates parent-child structure
- **is_active flag** — Deactivate nodes without deleting them

### TaxonomyEdge

**Purpose:** Defines parent-child relationships (DAG structure)

```python
class TaxonomyEdge(Base):
    __tablename__ = "taxonomy_edges"
    
    parent_id = Column(String, ForeignKey("taxonomy_nodes.id"), primary_key=True)
    child_id = Column(String, ForeignKey("taxonomy_nodes.id"), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Key design decisions:**
- **DAG structure** — Multi-parent allowed (e.g., "first aid" could be under both "medical" and "safety")
- **Acyclic by policy** — Must remain acyclic; enforced by application logic, not DB constraint
- **Composite primary key** — (parent_id, child_id) uniquely identifies each edge

### KBItemTaxonomy

**Purpose:** Many-to-many mapping of KB articles to taxonomy nodes

```python
class KBItemTaxonomy(Base):
    __tablename__ = "kb_item_taxonomy"
    
    kb_item_id = Column(Integer, ForeignKey("kb_articles.id"), primary_key=True)
    taxonomy_node_id = Column(String, ForeignKey("taxonomy_nodes.id"), primary_key=True)
    source = Column(Text, nullable=True)  # manual | import | legacy_category | auto
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Key design decisions:**
- **Many-to-many** — A KB article can belong to multiple taxonomy nodes
- **Source tracking** — How was this assignment made? (manual, auto, legacy migration)
- **Confidence score** — For auto-assigned taxonomy nodes (future use)

### IntentTaxonomyMap

**Purpose:** Maps intent labels to taxonomy nodes for inferred filtering

```python
class IntentTaxonomyMap(Base):
    __tablename__ = "intent_taxonomy_map"
    
    intent_label = Column(String, primary_key=True)
    taxonomy_node_id = Column(String, ForeignKey("taxonomy_nodes.id"), primary_key=True)
    rank = Column(Integer, default=1)  # 1=primary, 2+=secondary
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Key design decisions:**
- **Many-to-many** — One intent can map to multiple taxonomy nodes
- **Rank ordering** — Primary vs secondary mappings (e.g., "food" intent → primary: rk.tax.food, secondary: rk.tax.announcements)
- **Deterministic inference** — When intent is "food", system automatically infers taxonomy filter

---

## KB article metadata (Sprint 1, Story 1.2)

### KBArticle

**Purpose:** Main searchable Knowledge Base — all answers come from here

```python
class KBArticle(Base):
    __tablename__ = "kb_articles"
    
    id           = Column(Integer, primary_key=True, autoincrement=True)
    question     = Column(Text, nullable=False)
    answer       = Column(Text, nullable=False)
    category     = Column(Text)  # Legacy field, superseded by taxonomy
    tags         = Column(Text)  # Comma-separated
    enabled      = Column(Integer, default=1)  # 1=active, 0=disabled
    source       = Column(Text, default="manual")
    created_at   = Column(Integer)  # Unix timestamp
    last_updated = Column(Integer)  # Unix timestamp
    embedding    = Column(LargeBinary, nullable=True)  # Serialized MiniLM vector
    status       = Column(String, nullable=True)
    created_by   = Column(Text, default="System Generated")
    updated_by   = Column(Text, nullable=True)
    
    # ── Sprint 1, Story 1.2: Filterable metadata (additive) ──
    authority    = Column(String, nullable=True)  # official|shelter_staff|volunteer|unknown
    scope        = Column(String, nullable=True)  # shelter_local|general
    center_id    = Column(String, nullable=True)  # Future-friendly scoping
    hub_id       = Column(String, nullable=True)  # Future-friendly scoping
```

**New metadata fields (Sprint 1):**

| Field | Purpose | Example values |
|-------|---------|----------------|
| `authority` | Who authored/verified this content? | official, shelter_staff, volunteer, unknown |
| `scope` | Geographic/organizational scope | shelter_local, general, region_specific |
| `center_id` | Which shelter/evacuation center? | Used for multi-center deployments |
| `hub_id` | Which hub authored this? | Used for hub-to-hub KB sharing |

**Hard retrieval rules (Sprint 1, Story 1.3):**
- `enabled = 1` — REQUIRED for retrieval (safety-critical)
- `status = 'published'` or NULL — REQUIRED for retrieval (safety-critical)

> 🔍 Inferred: The `status` field may contain values like "draft", "published", "archived", "quarantined" (from Sprint 2-3 validation work)

---

## Query logging (Sprint 1, Story 0.2)

### QueryLog

**Purpose:** Logs every voice query made by kiosks

```python
class QueryLog(Base):
    __tablename__ = "query_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=True)
    kiosk_id = Column(String)
    
    # Query text fields
    transcript_original = Column(Text)       # Original language transcript
    transcript_english = Column(Text, nullable=True)  # Translated to EN
    raw_transcript = Column(Text, nullable=True)      # Query text passed to retrieve
    normalized_transcript = Column(Text, nullable=True)  # After normalize_query
    language = Column(String)
    
    # Retrieval results
    kb_version = Column(Integer)
    retrieval_score = Column(Float, nullable=True)
    answer_type = Column(String)  # DIRECT_MATCH | NEEDS_CLARIFICATION | NO_MATCH
    source_id = Column(Integer, nullable=True)  # Matched KB article ID
    
    # Rewrite tracking
    rewrite_attempted = Column(Boolean, default=False)
    rewritten_query = Column(Text, nullable=True)
    
    # Mode tracking
    formatter_mode = Column(String, nullable=True)  # cloud|local
    stt_mode = Column(String, nullable=True)        # cloud|local
    tts_mode = Column(String, nullable=True)        # cloud|local
    connectivity_state = Column(String, nullable=True)  # ONLINE|OFFLINE
    cloud_consent_mode = Column(String, nullable=False, default="disabled")
    
    # Performance
    latency_ms = Column(Float)
    
    # ── Sprint 1, Story 1.5: Filter decision logging (additive) ──
    ui_selection_source = Column(String, nullable=True)  # taxonomy|legacy_category|none
    ui_selected_taxonomy_node_id = Column(String, nullable=True)
    ui_selected_taxonomy_node_label = Column(Text, nullable=True)
    inferred_taxonomy_node_ids = Column(Text, nullable=True)  # JSON array string
    widening_step = Column(String, nullable=True)  # none|remove_inferred|broaden_ui|safe_fallback
    widening_reason = Column(Text, nullable=True)

    # ── Sprint 2: Clarification logging (Story 2.6) ──
    clarification_triggered = Column(Boolean, nullable=True)
    clarification_trigger_reason = Column(String, nullable=True)  # low_confidence|unclear_intent|missing_scope
    clarification_options_shown = Column(Text, nullable=True)  # JSON list of {id, label}

    # ── Sprint 3, Story 6A.1: Structured observability columns (15 new, commit d129eb6) ──
    # Intent (AC4) — wired in routes_query.py
    intent_label = Column(String, nullable=True)
    intent_confidence = Column(Float, nullable=True)
    # Lexical retrieval path (AC5 hybrid) — populated by Story 4.5
    lexical_top_k_ids = Column(Text, nullable=True)     # JSON array, top-5
    lexical_top_k_scores = Column(Text, nullable=True)  # JSON array of BM25 scores
    lexical_top_k_ranks = Column(Text, nullable=True)   # JSON array of ranks 1–5
    lexical_latency_ms = Column(Float, nullable=True)
    # Vector retrieval path (AC5 hybrid) — populated by Story 4.5
    vector_top_k_ids = Column(Text, nullable=True)
    vector_top_k_scores = Column(Text, nullable=True)   # cosine scores
    vector_top_k_ranks = Column(Text, nullable=True)
    # Fusion (AC5 hybrid) — populated by Story 4.5
    fusion_strategy = Column(String, nullable=True)     # e.g. "rrf"
    fusion_top_k_ids = Column(Text, nullable=True)
    fusion_top_k_scores = Column(Text, nullable=True)   # RRF scores
    fusion_top_k_ranks = Column(Text, nullable=True)
    # Failure / fallback (AC5 outcome) — populated by Story 6A.8
    fallback_reason = Column(String, nullable=True)     # no_results|low_confidence|validation_blocked|retrieval_error|rewrite_error
    failed_stage = Column(String, nullable=True)        # normalize|intent|clarification|rewrite|retrieval|fusion|format

    created_at = Column(Integer)  # Unix timestamp
```

**Filter logging fields (Sprint 1, Story 1.5):**

| Field | Purpose |
|-------|---------|
| `ui_selection_source` | How was the filter selected? (taxonomy, legacy_category, none) |
| `ui_selected_taxonomy_node_id` | Explicitly selected taxonomy node ID |
| `ui_selected_taxonomy_node_label` | Human-readable label for selected node |
| `inferred_taxonomy_node_ids` | JSON array of taxonomy nodes inferred from intent |
| `widening_step` | Did we need to widen the filter? (none, remove_inferred, broaden_ui, safe_fallback) |
| `widening_reason` | Why did widening occur? (e.g., "zero results") |

**Structured observability fields (Sprint 3, Story 6A.1 — commit `d129eb6`):**

Added as interface contract for Slice 4 hybrid retrieval and Story 6A.8 fallback logging. Only `intent_label` and `intent_confidence` are wired in this story; the rest are schema-only until the corresponding writers ship. All top-k arrays are capped at 5 elements per [[20-sprints/sprint-3/decisions|3-D2]]. See [[30-decisions/slice-6a|Slice 6A]] for full design rationale and the dedup against Sprint 2 clarification fields (6A-D6).

---

## Clarification resolution (Sprint 1, Story 0.3 foundation)

### ClarificationResolution

**Purpose:** Gold label when user selects a category after clarification

```python
class ClarificationResolution(Base):
    __tablename__ = "clarification_resolutions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=False)
    raw_transcript = Column(Text, nullable=True)
    resolved_intent = Column(String, nullable=False)
    language = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Purpose:** Tracks clarification resolution for future intent model improvement

> 🔍 Inferred: This table is populated during Sprint 2's clarification UX implementation (Story 2.5)

---

## Validation and review workflow (Sprint 2-3, Slice 3)

### KBItemValidationStatus

**Purpose:** Stores validation results per KB article

```python
class KBItemValidationStatus(Base):
    __tablename__ = "kb_item_validation_status"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    kb_item_id = Column(Integer, ForeignKey("kb_articles.id"), nullable=False)
    status = Column(String, nullable=False)  # approved|needs_review|quarantined|rejected
    kb_version = Column(Integer, nullable=True)
    rule_results = Column(Text, nullable=True)  # JSON serialized RuleResult list
    created_at = Column(Integer, nullable=True)  # Unix timestamp
```

**Status values:**
- `approved` — Passed all validation rules (or manually approved)
- `needs_review` — Has WARNING-level failures, needs human review
- `quarantined` — Has ERROR-level failures, blocked from publish
- `rejected` — Human reviewer confirmed as invalid

**Key behaviors:**
- Latest row (by `id DESC`) is authoritative
- Historical rows preserved for audit trail
- Queried by `_get_quarantined_item_ids()` for retrieval exclusion (Story 3.5)

**Added:** Sprint 2, Story 3.2

---

### KBReviewDecisions

**Purpose:** Audit trail of human review actions

```python
class KBReviewDecisions(Base):
    __tablename__ = "kb_review_decisions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    kb_item_id = Column(Integer, ForeignKey("kb_articles.id"), nullable=False)
    kb_version = Column(Integer, nullable=True)
    reviewer = Column(String, nullable=True)  # Operator username/email
    action = Column(String, nullable=False)   # approved|rejected|override
    reason = Column(Text, nullable=True)      # Human-entered reason for decision
    created_at = Column(Integer, nullable=True)  # Unix timestamp
```

**Actions:**
- `approved` — Override validation failure, mark as safe to publish
- `rejected` — Confirm validation failure, mark as invalid
- `override` — Approve with logged reason (e.g., "False positive: domain-specific abbreviation")

**Added:** Sprint 3, Story 3.4

> 🔍 Inferred: Schema structure based on `hub/validation/review.py` implementation.

---

## Related notes

- [[10-architecture/semantic-search]] — How filtering uses taxonomy
- [[10-architecture/voice-pipeline]] — How QueryLog is populated
- [[10-architecture/validation-pipeline]] — Validation and quarantine system (Sprint 2-3)
- [[10-architecture/hybrid-retrieval]] — Lexical + vector fusion (Sprint 3)
- [[20-sprints/sprint-1/user-stories#1.1]] — Story 1.1: Define taxonomy v1 data model
- [[20-sprints/sprint-1/user-stories#1.2]] — Story 1.2: Add metadata fields for retrieval filtering
- [[20-sprints/sprint-2/user-stories]] — Stories 3.1, 3.2: Validation engine and storage
- [[20-sprints/sprint-3/user-stories]] — Story 6A.1: Structured logging columns
- [[20-sprints/sprint-1/decisions#1.1-D3]] — Decision: Hierarchical taxonomy v1 model

---

## Evidence

| Commit | Date | Author | Message |
|--------|------|--------|---------|
| 97c82ae | 2026-05-01 | keithruezyl1 | slide 1 story 1 completed |
| ded5b36 | 2026-05-01 | keithruezyl1 | slice 1 user story 2 delivered |
| 70256b3 | 2026-05-03 | Isaac | Completed Person 2: Story 2 - Add pipeline stage logging skeleton and Story 5 - Log filter decisions and candidate counts |
| beabff3 | 2026-05-09 | (Sprint 2) | slice 3 story 1 delivered (validation engine) |
| d129eb6 | 2026-05-11 | keithruezyl1 | slice 6a story 1 delivered, pre sprint 2 merge (structured logging) |
| ca74223 | 2026-05-15 | whitefangggggg | Slice 3 Story 4 (review workflow) |
