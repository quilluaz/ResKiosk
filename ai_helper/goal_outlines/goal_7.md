# Goal 7 — Metadata schema + filtering policy (UI + inferred + hard rules)

### 1) Outcome

Implement **metadata filtering** with explicit precedence so retrieval is **safe, scoped, explainable, and reproducible** for a fixed KB version/config.

- **What changes**: retrieval becomes metadata-aware (hard rules + UI filters + inferred intent) instead of relying on ad-hoc category strings.
- **Who benefits**: residents (safer, more relevant answers), operators (predictable behavior), maintainers (debuggable retrieval).
- **What success looks like**:
  - applied filters are logged and explainable
  - filter changes produce predictable behavior for the same query + KB version
  - filtering is enforced for both vector and lexical paths (and therefore hybrid + multi-path)

---

### 2) Why this matters

- **Current limitation**: basic fields exist (`category`, `tags`, `enabled`, `status`), but there is no formal, enforceable filter model or precedence.
- **Risk addressed**: unsafe/irrelevant evidence can slip into results; behaviors become inconsistent and hard to reproduce.
- **Value**: deterministic scoping improves accuracy and makes retrieval decisions auditable—required for emergency shelter guidance.

---

### 3) Scope

- Define **filter fields** (metadata schema v1) used for retrieval scoping.
- Define **precedence rules** (hard rules > UI > inferred intent) and deterministic widening/fallback behavior.
- Implement filtering consistently across:
  - vector retrieval (current)
  - lexical/BM25 retrieval (Goal 4)
  - hybrid fusion (Goal 4)
  - multi-path retrieval (Goal 5)
- Standardize topic categorization via a **controlled taxonomy** and mappings:
  - intent → taxonomy node(s)
  - message category → taxonomy node
  - clarification chips → taxonomy nodes (IDs)

---

### 4) Non-goals

- Full knowledge graph (entities + relations + traversal)
- Automatic entity extraction or relation inference
- Complex taxonomy editor UI (drag/drop ontology tooling)
- Online LLM “judge” in the hot path (reserved for Goal 8 and offline/batch only)

---

### 5) System Impact

#### a. Data / Schema

**Existing (already in `kb_articles`)**

- `enabled`
- `status`
- `tags`

**New (Goal 7 introduces these as first-class filterable metadata)**

This goal is **authoritative about the metadata dimensions and precedence**, but intentionally **implementation-neutral** about exact table names until we do Goal 3 schema work and confirm migrations.

- **Taxonomy (topic nodes + assignments)**
  - stable node IDs + display names
  - DAG-capable parent edges (acyclic; multi-parent allowed but rare)
  - KB item ↔ taxonomy assignment (multi-assign supported; prefer 1 primary + optional secondary)
  - deterministic intent → taxonomy mapping
  - deterministic message category → taxonomy mapping

- **Authority/source (separate from taxonomy)**
  - minimum viable enum: `official | shelter_staff | volunteer | unknown`

- **Scope/context (separate from taxonomy)**
  - minimum viable: `shelter_local | general`
  - future-friendly: `center_id` / `hub_id` constraints when available

For a concrete “data model sketch” and migration plan, treat `docs/goal 7/controlled_taxonomy_outline.md` as the companion reference.

#### b. API / Interfaces

**Hub query contract**

- Clarification responses should return **taxonomy-backed chips**: `{ id, label }`
- Retry requests should accept a **selected taxonomy node ID** (not a free-text category string)

**Admin/console**

- KB editor must allow selecting taxonomy nodes (primary + optional secondary)
- KB listing/search can filter by taxonomy + status + enabled

#### c. UX / Behavior

- **Resident (kiosk)**:
  - when unclear, see 2–3 chips; selecting one constrains the next retrieval deterministically
- **Admin (console)**:
  - can assign taxonomy + authority/scope fields
  - can audit missing/invalid metadata (Goal 8 gate uses this)

---

### 6) Integration Points

- **Depends on**:
  - Goal 6 (clarification UX) for chip selection flow
  - Goal 12 (pipeline order) for normalize → intent → clarification → rewrite enforcement
- **Affects**:
  - Goal 4 (BM25/hybrid): lexical results must obey the same filters
  - Goal 5 (multi-path): per-path intent constraints must be consistent and logged
  - Goal 10 (metrics/logging): filter decisions must be observable
  - Goal 8 (validation gate): validates correctness/completeness of these metadata fields

---

### 7) Edge Cases / Failure Modes

- **Over-filtering** (too few/zero candidates):
  - deterministic widening order: remove inferred constraints → broaden UI constraints → safe fallback response
  - never violate hard rules
- **Conflicting constraints**:
  - hard rules win; log override
- **Missing metadata** (taxonomy not assigned yet):
  - treat inferred intent mapping as default routing; flag for audit; do not silently create new taxonomy nodes
- **Ambiguous queries**:
  - show max 3 clarification chips using policy below

---

### 8) Logging & Metrics

Log enough to explain *why* an answer was returned:

- query: normalized query, KB version
- intent: label + confidence
- applied filters:
  - hard rules applied (and which)
  - UI-selected taxonomy node (if any)
  - inferred taxonomy nodes (if any)
  - authority/scope constraints (if any)
- widening/fallback events and reasons
- candidate counts before/after filtering per retrieval path
- returned evidence IDs and their taxonomy nodes

---

### 9) Determinism / Constraints

- **Tie-break rules**: stable ordering for equal scores, e.g. `(score desc, source_id asc)`.
- **Ordering guarantees**: fixed KB version/config + same filters ⇒ reproducible ordering.
- **Safety constraints**: hard rules must be enforced before any UI/inference can narrow.

---

### 10) Definition of Done (DoD)

- Metadata fields are defined and implemented (taxonomy + authority + scope + enabled/status gating).
- Filtering precedence (hard > UI > inferred) is enforced end-to-end on vector path.
- Filtering semantics are implemented in a way that BM25/hybrid/multi-path can share the same policy.
- Clarification chips are taxonomy-backed and limited to max 3.
- Logging captures applied filters, overrides, and widening steps.

---

### 11) Open Decisions

- Exact storage location for authority/scope (new columns vs JSON metadata) while keeping enforcement simple.
- Minimum viable “candidate floor” definition for widening (e.g., top-k count threshold).

---

## Policy / Rules

### Precedence (authoritative order)

1. **Hard system rules** override all
2. **User UI filters** override inference
3. **Inferred intent** fills missing constraints

### Hard rules (minimum set)

- Never return `enabled=false`
- Never return `status != published` to residents
- Safety override: do not allow narrowing that removes Safety & Emergencies evidence when safety signals are present
- Medical override: ensure Health & Medical remains eligible when medical intent is high confidence (unless user explicitly chose otherwise in clarification)

### Widening / fallback (deterministic)

If too few candidates after filtering:

1. remove inferred intent constraints (keep hard rules)
2. broaden UI constraints (keep hard rules)
3. safe fallback response / escalation UX

All steps must be logged.

---

## Taxonomy / Controlled Vocabulary

### Taxonomy v1 (Main categories + subcategories)

#### Design rules (v1)

- stable IDs; display names may evolve
- few mains; more subcategories
- cross-cutting properties are not categories (authority/priority/scope are separate)
- multi-assign allowed (primary + optional secondary)
- multi-parent edges allowed but rare; must remain acyclic

#### Main categories (v1)

1) **Shelter Config**
- Registration & Intake
- Shelter Rules & Conduct
- Schedules
- Announcements & Notices
- Shelter Services Overview

2) **Health & Medical**
- First Aid
- Symptoms & Illness
- Medications & Treatment
- Medical Services
- Mental Health & Psychosocial Support

3) **Safety & Emergencies**
- Emergency Procedures
- Security & Personal Safety
- Child Safety
- Public Health Safety

4) **Basic Needs & Daily Living**
- Food & Water
- Sleeping & Rest Areas
- Hygiene Supplies
- Facilities Use
- Clothing & Essentials

5) **Family & Support Services**
- Family Separation Support (non-specific)
- Children & Infant Care
- Elderly Support
- Disability & Accessibility (Special Needs)
- Pet Support

6) **Logistics & Supplies**
- Inventory Availability
- Resource Requests
- Donations

7) **Location & Navigation**
- In-Shelter Locations
- Maps & Wayfinding
- External Location / Address

8) **System & Interaction** (optional KB-only)
- Kiosk Identity
- Kiosk Capabilities
- Basic Interaction

### Mappings (v1)

#### Intent label → taxonomy nodes

- Conversational:
  - `greeting` → System & Interaction → Basic Interaction
  - `identity` → System & Interaction → Kiosk Identity
  - `capability` → System & Interaction → Kiosk Capabilities
  - `small_talk` → System & Interaction → Basic Interaction
  - `goodbye` → System & Interaction → Basic Interaction

- Core shelter:
  - `food` → Basic Needs & Daily Living → Food & Water
  - `medical` → Health & Medical → Medical Services (secondary allowed: First Aid when injury keywords)
  - `registration` → Shelter Config → Registration & Intake
  - `sleeping` → Basic Needs & Daily Living → Sleeping & Rest Areas
  - `facilities` → Basic Needs & Daily Living → Facilities Use
  - `safety` → Safety & Emergencies → Emergency Procedures
  - `lost_person` → Family & Support Services → Family Separation Support (non-specific)
  - `pets` → Family & Support Services → Pet Support
  - `donations` → Logistics & Supplies → Donations
  - `hours` → Shelter Config → Schedules
  - `location` → Location & Navigation → External Location / Address
  - `general_info` → Shelter Config → Shelter Services Overview

- Additional support:
  - `inventory` → Logistics & Supplies → Inventory Availability
  - `mental_health` → Health & Medical → Mental Health & Psychosocial Support
  - `hygiene` → Basic Needs & Daily Living → Hygiene Supplies
  - `children` → Family & Support Services → Children & Infant Care
  - `special_needs` → Family & Support Services → Disability & Accessibility (Special Needs)

#### Hub message category → taxonomy nodes

- `Resource Request` → Logistics & Supplies → Resource Requests
- `Medical Alert` → Health & Medical → Medical Services
- `Status Update` → Shelter Config → Announcements & Notices
- `Evacuation Notice` → Safety & Emergencies → Emergency Procedures
- `General Communication` → Shelter Config → Announcements & Notices

### Multi-assignment rules (KB)

- Location cross-cut: “where is X” ⇒ add Location & Navigation → In-Shelter Locations as secondary
- Safety cross-cut: hazard response ⇒ primary Safety; secondary Shelter Config rule if shelter-specific
- Health split: first aid vs services vs symptoms assigned accordingly
- Announcements: bulletin-style ⇒ Shelter Config → Announcements & Notices; authority set separately

### Clarification chips (v1)

- Max **3** chips
- Default set:
  - Food & Water
  - Medical Services
  - Registration & Intake
- Conditional additions (replace one default only when strongly indicated):
  - Emergency Procedures
  - Facilities Use
  - Sleeping & Rest Areas
  - In-Shelter Locations

---

## Contract / Payload Shape

### Clarification response (hub → kiosk)

- Return clarification options as taxonomy nodes:
  - `clarification_options: [{ id, label }]`

### Clarification retry (kiosk → hub)

- Send selected taxonomy node:
  - `selected_taxonomy_node_id: <id>`

Notes:

- This replaces any free-text category retry mechanism.
- Logging must include the selected node ID and label.


