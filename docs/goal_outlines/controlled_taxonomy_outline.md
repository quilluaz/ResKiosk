# Controlled Taxonomy Outline (AAIH Increment)

## Purpose

Standardize topic classification across:

- **Knowledge Base (KB) items** (text articles now; images later)
- **Hub-to-hub messages**
- **Intent outputs** (classifier results used in retrieval)

So that retrieval can be **more accurate**, **more deterministic**, and **more explainable** for a fixed KB version/config.

This is **not** a “true knowledge graph” (entities + relations + traversal). It is a **controlled taxonomy** (graph-capable hierarchy) used as metadata and filters.

---

## Design goals (what “good” looks like)

- **Reproducible**: for the same KB version + config, the same query yields the same candidate sets and ordering (except explicitly enabled feedback/bias features).
- **Effective**: fewer cross-topic false positives; better compound handling via structured routing.
- **Auditable**: logs can show which taxonomy nodes were applied and why (UI vs intent inference vs hard rules).
- **Practical**: small initial scope, easy to migrate existing content, minimal UI disruption.

Non-goals for this increment:

- Automatic entity extraction / relation inference
- Graph traversal reasoning (“A is connected to B” queries)
- Large ontology management tools

---

## Key concepts (terms)

- **Taxonomy node**: a canonical topic label with a stable ID.
- **Graph taxonomy**: nodes can have **multiple parents** (so this is a DAG, not a strict tree).
- **Assignment**: linking content (KB item/message) to one or more taxonomy nodes.
- **Intent → taxonomy mapping**: deterministic mapping from intent labels to taxonomy nodes.

---

## Minimum viable product (MVP) scope

### 1) Canonical taxonomy storage (DAG-capable)

Introduce a dedicated taxonomy table (or equivalent) with:

- stable ID
- display name
- optional description
- optional “active” flag
- optional ordering/priority metadata

And a “parent edges” table for multi-parent:

- parent_node_id → child_node_id

Constraints:

- enforce **acyclic** parent relationships (no loops)
- allow multi-parent where needed

### 2) Assignments across the system (multi-assign supported)

KB items:

- allow linking each KB item to **N taxonomy nodes**

Hub messages:

- link each message to **1 taxonomy node** (or N if required later)

Intent:

- maintain a deterministic mapping table/config:
  - intent_label → [taxonomy_node_id...]

### 3) Retrieval uses taxonomy as structured filters (Goal 7 alignment)

Implement and log filter precedence:

1. **Hard system rules** (safety/guardrails) override all
2. **User UI filters** (admin console / kiosk chip selection)
3. **Inferred intent mapping** fills missing constraints

Retrieval should:

- optionally restrict candidate set by taxonomy node(s)
- still fallback safely when filters would produce empty/too-small candidate sets

### 4) Clarification chips become taxonomy nodes (Goal 6 alignment)

When clarifying, the system should present **taxonomy-backed choices** (node IDs + display names), not free-text labels.

Persist user selections as:

- session → selected taxonomy node(s)
- plus the derived intent (if needed)

### 5) Validation gate touchpoint (Goal 8 alignment)

Before publish:

- validate that taxonomy assignments exist for required KB items or required sections
- enforce minimal rules (e.g., “medical/first aid content must have at least one health-related node”)
- quarantine or block publish if critical content lacks assignments

---

## Data model sketch (implementation-neutral)

### Tables

- `taxonomy_nodes`
  - `id` (int/uuid)
  - `name` (unique, normalized)
  - `description`
  - `is_active`
  - `created_at`, `updated_at`

- `taxonomy_edges`
  - `parent_id`
  - `child_id`

- `kb_item_taxonomy` (join table)
  - `kb_item_id`
  - `taxonomy_node_id`
  - optional: `source` (manual/import/auto)
  - optional: `confidence`

- `message_taxonomy` (or replace message `category_id`)
  - `message_id`
  - `taxonomy_node_id`

- `intent_taxonomy_map`
  - `intent_label`
  - `taxonomy_node_id`

Notes:

- Keep existing free-text KB category fields temporarily for migration/back-compat, but treat them as deprecated once assignments exist.
- Prefer node IDs in hot paths (retrieval, logging) to prevent “category string drift.”

---

## Migration plan (low risk)

### Phase 0: Add taxonomy tables + seed a minimal set

- Create taxonomy schema + seed nodes
- Add join tables
- Add admin endpoints (read-only first)

### Phase 1: Backfill assignments from existing data

Sources:

- KB:
  - existing category strings (legacy)
  - existing tags
  - known system-generated buckets (e.g., shelter config sync)
- Messages:
  - seeded message categories (e.g., resource request, medical alert)
- Intent:
  - map existing intent labels to taxonomy nodes

Backfill outputs:

- a deterministic mapping file/script (repeatable) that can be re-run
- a report: % assigned, % ambiguous, % missing

### Phase 2: Dual-write + read-preference

- Console writes taxonomy assignments for new/edited KB items
- Retrieval prefers taxonomy assignments if present; otherwise falls back to legacy values

### Phase 3: Deprecate free-text category usage

- stop using free-text category strings for filtering/clarification
- keep legacy fields for display/back-compat only (or remove later)

---

## Retrieval integration plan (high-level)

### Candidate set filtering

- Add an optional filter: `taxonomy_node_ids`
- Translate selected nodes into allowed KB item IDs via join table
- Apply filter before:
  - BM25 index lookup (Goal 4)
  - vector similarity scoring

### Multi-path retrieval (Goal 5)

- For compound queries:
  - run one path per intent
  - each path applies that intent’s taxonomy node filter(s)
  - merge results by explicit rules (priority + fusion)

### Tie-breaking and determinism

- Always include deterministic tie-breakers (e.g., `(score desc, kb_item_id asc)`).
- Log applied taxonomy filters and candidate counts per path.

---

## Console / operator UX (minimal)

- Display taxonomy assignments on KB items
- Provide:
  - search/select taxonomy nodes
  - multi-select (N nodes) per KB item
  - “missing taxonomy” filter for audit
- For messages:
  - map message “category” dropdown to taxonomy nodes (or show taxonomy directly)

Out of scope (for now):

- drag/drop taxonomy editor UI
- complex permissioning for taxonomy changes

---

## API changes (minimal)

- Add endpoints to:
  - list taxonomy nodes + edges
  - assign/unassign taxonomy nodes for a KB item
  - (optional) bulk assignment import/export

- Update query/retrieval payloads to:
  - accept `selected_taxonomy_node_id(s)` for clarification retry
  - return `clarification_taxonomy_options` (IDs + display names)

---

## Observability + metrics (Goal 10 alignment)

Add logging fields to support evaluation:

- intent label(s) + confidence
- taxonomy node IDs applied:
  - hard-rule
  - user-selected
  - inferred via intent map
- candidate counts before/after filtering
- evidence IDs returned (text/image) with taxonomy node IDs

Suggested offline checks:

- “stability test”: fixed KB snapshot + fixed queries → stable top-k IDs
- “filter correctness”: taxonomy filters reduce cross-topic retrieval errors on an eval set

---

## Risks and mitigations

- **Taxonomy drift**: mitigate via controlled node list + review gate.
- **Over-filtering** (empty results): mitigate via deterministic fallback rules and logging.
- **Multi-parent complexity**: mitigate by limiting DAG usage initially; require justification for multi-parent edges.
- **Legacy content mismatch**: mitigate via backfill report + “missing taxonomy” audit UI.

---

## Definition of done (increment-ready)

- Taxonomy schema exists; nodes seeded; edges supported (acyclic).
- KB items can be assigned to taxonomy nodes (multi-assign).
- Message categories are mapped to taxonomy nodes.
- Intent → taxonomy mapping exists and is used in retrieval as a filter/routing input.
- Clarification options are taxonomy-backed (IDs, not strings).
- Logs show applied taxonomy filters and evidence attribution.
- Publish gate can validate required taxonomy metadata (integration point with Goal 8).

