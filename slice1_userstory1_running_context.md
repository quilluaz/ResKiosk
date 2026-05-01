# Slice 1 — Goal 7 Context (Person 4: Taxonomy & Metadata Schema Owner)

This file is the **single running context** for Sprint 1 Story 1 (“Define taxonomy v1 data model”) and related Goal 7 alignment.

**Rule (per Keith):** Before making any important decision, consult this file first. After every action/decision, update this file with the relevant context.

---

## Source-of-truth docs (read)

- `docs/goal_outlines/goal_7.md`
- `docs/goal_outlines/controlled_taxonomy_outline.md`
- (code reality checks) `hub/db/schema.py`, `hub/models/api_models.py`, `hub/retrieval/search.py`, `hub/api/routes_query.py`

---

## Story 1 (Sprint 1) — Define taxonomy v1 data model

### What Story 1 includes (scope)

- Define **taxonomy v1 categories** (main + subcategories) used across:
  - KB items
  - hub-to-hub messages
  - intent outputs (for deterministic mapping)
- Define:
  - **stable taxonomy node IDs**
  - **display labels**
  - **parent/child structure** (DAG-capable, acyclic; multi-parent allowed but rare)
  - **intent → taxonomy node mappings**
  - clarification chip compatibility (chips map to taxonomy node IDs)
- Ensure the model is **deterministic** and **backward-compatible** with current “category string” behavior until fully migrated.

### Acceptance criteria highlights (from story + Goal 7)

- Taxonomy v1 includes stable IDs + display labels.
- Includes main categories required for shelter guidance.
- Intent-to-taxonomy mappings represented.
- UI chip options can map to taxonomy node IDs.
- Taxonomy data can be loaded deterministically.
- Existing retrieval behavior is not broken by adding taxonomy model.

---

## Story 1 completion status

**Status: DONE (delivered).**

**What was delivered (mapped to acceptance criteria):**

- **Stable IDs + display labels**: `rk.tax.*` IDs + `taxonomy_nodes.label`, seeded from `hub/taxonomy/taxonomy_v1.json`.
- **Main categories required**: encoded in `hub/taxonomy/taxonomy_v1.json` per `docs/goal_outlines/goal_7.md`.
- **Intent → taxonomy mappings**: normalized DB table `intent_taxonomy_map` seeded deterministically.
- **UI chip options map to taxonomy node IDs**:
  - additive API fields: `QueryResponse.clarification_options: [{id,label}]`
  - deterministic selection per Goal 7 chip defaults + conditional replacement.
- **Deterministic loading**: committed seed JSON + idempotent seeding/backfill in `init_db()`.
- **No retrieval regression**: legacy `selected_category` + `clarification_categories` still supported; taxonomy additions are additive.

**Note (non-blocker):**
- Whether a given query triggers `NEEDS_CLARIFICATION` depends on current thresholds/scoring; when it does, chip selection is deterministic.

---

## Current codebase reality (compat constraints)

- KB today uses free-text `kb_articles.category` (string-like).
- Clarification today returns `clarification_categories: List[str]`.
- Retry today uses `selected_category: Optional[str]` and maps it to intent via a legacy string map (`CLARIFICATION_CATEGORY_TO_INTENT`).

Implication: taxonomy IDs must be introduced **without breaking** today’s string-based clarification/retry flow. Plan is to add taxonomy IDs alongside legacy category strings, then shift contracts later.

---

## Decisions log

### D1 — Taxonomy ID namespace prefix: `rk.tax.`

- **Decision**: Use stable taxonomy IDs prefixed with **`rk.tax.`**.
- **Why**:
  - avoids confusion/collision with existing legacy `category` usage and “category strings”
  - clearly denotes “taxonomy node ID” (not a label)
  - project-level namespacing (“rk”) reduces future collisions if IDs appear outside the hub
- **Example**: `rk.tax.health_medical.medical_services`

---

### D2 — Taxonomy seed artifact location + lifecycle

- **Decision**: Keep the canonical taxonomy as a committed JSON seed file at:
  - `hub/taxonomy/taxonomy_v1.json`
- **Why here**:
  - close to the hub code that will load/seed it (single source used by migrations/backfill and runtime reads)
  - avoids burying an operational artifact under `docs/` (docs can reference it, but runtime should not depend on docs paths)
  - supports determinism: the same repo version implies the same taxonomy seed
- **Lifecycle**:
  - **Do not delete** after implementation; treat as **necessary documentation + runtime seed**.
  - When taxonomy evolves, create a new file (e.g. `taxonomy_v2.json`) and keep v1 for audit/back-compat.

---

### D3 — Seed JSON format (taxonomy_v1.json)

- **Decision**: Use a single JSON file with a stable, explicit schema:
  - top-level: `schema_version`, `taxonomy_version`, `generated_from`, `generated_at` (optional), plus sections below
  - `nodes[]`: objects with:
    - `id` (string; stable, e.g. `rk.tax.health_medical.medical_services`)
    - `label` (display name)
    - `parent_ids` (list of string IDs; empty for roots; enables DAG)
    - optional: `description`, `is_active`, `sort_order`
  - `intent_taxonomy_map`: `{ "<intent_label>": { "primary": "<node_id>", "secondary": ["<node_id>"] } }`
  - `message_category_taxonomy_map`: `{ "<message_category_label>": "<node_id>" }`
  - `clarification_chip_defaults`: `{ "default": ["<node_id>", ...], "conditional_replacements": ["<node_id>", ...], "max_options": 3 }`
- **Why**:
  - deterministic + audit-friendly (diffable)
  - supports DAG without needing a separate `edges` section
  - supports Goal 7 mappings + chip defaults in one canonical artifact

---

### D4 — DB representation choices (Sprint 1)

- **Decision**: Store taxonomy node IDs as **TEXT** in SQLite/SQLAlchemy.
- **Decision**: Model intent → taxonomy mappings as a **normalized table with multiple rows per intent** (not a JSON/list blob).
- **Why**:
  - TEXT preserves stable IDs directly (`rk.tax.*`) and keeps logs/debugging readable.
  - Normalized mapping supports FK integrity, easy querying (“which intents map to node X?”), and safe incremental edits.

---

### D5 — Taxonomy DB tables + seeding/backfill approach

- **Decision**: Add minimum viable taxonomy tables to SQLite (via SQLAlchemy `create_all`):
  - `taxonomy_nodes` (TEXT `id` PK, `label`, optional metadata)
  - `taxonomy_edges` (TEXT `parent_id` + `child_id` composite PK)
  - `intent_taxonomy_map` (multiple rows per intent; composite PK `(intent_label, taxonomy_node_id)` + `rank`)
  - `kb_item_taxonomy` (join table; composite PK `(kb_item_id, taxonomy_node_id)` + `source`, `confidence`)
- **Seeding**:
  - seed nodes/edges/intent map from `hub/taxonomy/taxonomy_v1.json` (idempotent upsert)
- **Backfill**:
  - fill `kb_item_taxonomy` from `kb_articles.category` using `hub/taxonomy/legacy_category_map_v1.json`
  - additive + idempotent: only assign taxonomy if a KB article has **no assignment rows yet**
- **Where implemented**:
  - models: `hub/db/schema.py`
  - seed/backfill: `hub/db/seed.py`

---

## Taxonomy v1 (canonical node list)

### Naming conventions

- IDs are dot-separated.
- Segments are lowercase snake_case.
- IDs never change; labels may change.

### Main categories

- `rk.tax.shelter_config` — Shelter Config
- `rk.tax.health_medical` — Health & Medical
- `rk.tax.safety_emergencies` — Safety & Emergencies
- `rk.tax.basic_needs_daily_living` — Basic Needs & Daily Living
- `rk.tax.family_support_services` — Family & Support Services
- `rk.tax.logistics_supplies` — Logistics & Supplies
- `rk.tax.location_navigation` — Location & Navigation
- `rk.tax.system_interaction` — System & Interaction (optional KB-only)

### Subcategories

**Shelter Config** (`parent=rk.tax.shelter_config`)
- `rk.tax.shelter_config.registration_intake` — Registration & Intake
- `rk.tax.shelter_config.shelter_rules_conduct` — Shelter Rules & Conduct
- `rk.tax.shelter_config.schedules` — Schedules
- `rk.tax.shelter_config.announcements_notices` — Announcements & Notices
- `rk.tax.shelter_config.shelter_services_overview` — Shelter Services Overview

**Health & Medical** (`parent=rk.tax.health_medical`)
- `rk.tax.health_medical.first_aid` — First Aid
- `rk.tax.health_medical.symptoms_illness` — Symptoms & Illness
- `rk.tax.health_medical.medications_treatment` — Medications & Treatment
- `rk.tax.health_medical.medical_services` — Medical Services
- `rk.tax.health_medical.mental_health_psychosocial_support` — Mental Health & Psychosocial Support

**Safety & Emergencies** (`parent=rk.tax.safety_emergencies`)
- `rk.tax.safety_emergencies.emergency_procedures` — Emergency Procedures
- `rk.tax.safety_emergencies.security_personal_safety` — Security & Personal Safety
- `rk.tax.safety_emergencies.child_safety` — Child Safety
- `rk.tax.safety_emergencies.public_health_safety` — Public Health Safety

**Basic Needs & Daily Living** (`parent=rk.tax.basic_needs_daily_living`)
- `rk.tax.basic_needs_daily_living.food_water` — Food & Water
- `rk.tax.basic_needs_daily_living.sleeping_rest_areas` — Sleeping & Rest Areas
- `rk.tax.basic_needs_daily_living.hygiene_supplies` — Hygiene Supplies
- `rk.tax.basic_needs_daily_living.facilities_use` — Facilities Use
- `rk.tax.basic_needs_daily_living.clothing_essentials` — Clothing & Essentials

**Family & Support Services** (`parent=rk.tax.family_support_services`)
- `rk.tax.family_support_services.family_separation_support` — Family Separation Support (non-specific)
- `rk.tax.family_support_services.children_infant_care` — Children & Infant Care
- `rk.tax.family_support_services.elderly_support` — Elderly Support
- `rk.tax.family_support_services.disability_accessibility_special_needs` — Disability & Accessibility (Special Needs)
- `rk.tax.family_support_services.pet_support` — Pet Support

**Logistics & Supplies** (`parent=rk.tax.logistics_supplies`)
- `rk.tax.logistics_supplies.inventory_availability` — Inventory Availability
- `rk.tax.logistics_supplies.resource_requests` — Resource Requests
- `rk.tax.logistics_supplies.donations` — Donations

**Location & Navigation** (`parent=rk.tax.location_navigation`)
- `rk.tax.location_navigation.in_shelter_locations` — In-Shelter Locations
- `rk.tax.location_navigation.maps_wayfinding` — Maps & Wayfinding
- `rk.tax.location_navigation.external_location_address` — External Location / Address

**System & Interaction** (`parent=rk.tax.system_interaction`)
- `rk.tax.system_interaction.kiosk_identity` — Kiosk Identity
- `rk.tax.system_interaction.kiosk_capabilities` — Kiosk Capabilities
- `rk.tax.system_interaction.basic_interaction` — Basic Interaction

---

## Deterministic mappings (v1)

### Intent label → taxonomy node ID

**Conversational**
- `greeting` → `rk.tax.system_interaction.basic_interaction`
- `identity` → `rk.tax.system_interaction.kiosk_identity`
- `capability` → `rk.tax.system_interaction.kiosk_capabilities`
- `small_talk` → `rk.tax.system_interaction.basic_interaction`
- `goodbye` → `rk.tax.system_interaction.basic_interaction`

**Core shelter**
- `food` → `rk.tax.basic_needs_daily_living.food_water`
- `medical` → `rk.tax.health_medical.medical_services` (secondary allowed: `rk.tax.health_medical.first_aid`)
- `registration` → `rk.tax.shelter_config.registration_intake`
- `sleeping` → `rk.tax.basic_needs_daily_living.sleeping_rest_areas`
- `facilities` → `rk.tax.basic_needs_daily_living.facilities_use`
- `safety` → `rk.tax.safety_emergencies.emergency_procedures`
- `lost_person` → `rk.tax.family_support_services.family_separation_support`
- `pets` → `rk.tax.family_support_services.pet_support`
- `donations` → `rk.tax.logistics_supplies.donations`
- `hours` → `rk.tax.shelter_config.schedules`
- `location` → `rk.tax.location_navigation.external_location_address`
- `general_info` → `rk.tax.shelter_config.shelter_services_overview`

**Additional support**
- `inventory` → `rk.tax.logistics_supplies.inventory_availability`
- `mental_health` → `rk.tax.health_medical.mental_health_psychosocial_support`
- `hygiene` → `rk.tax.basic_needs_daily_living.hygiene_supplies`
- `children` → `rk.tax.family_support_services.children_infant_care`
- `special_needs` → `rk.tax.family_support_services.disability_accessibility_special_needs`

### Hub message category → taxonomy node ID

- `Resource Request` → `rk.tax.logistics_supplies.resource_requests`
- `Medical Alert` → `rk.tax.health_medical.medical_services`
- `Status Update` → `rk.tax.shelter_config.announcements_notices`
- `Evacuation Notice` → `rk.tax.safety_emergencies.emergency_procedures`
- `General Communication` → `rk.tax.shelter_config.announcements_notices`

---

## Clarification chips (taxonomy-backed, v1)

### Default set (max 3)

- `rk.tax.basic_needs_daily_living.food_water` — Food & Water
- `rk.tax.health_medical.medical_services` — Medical Services
- `rk.tax.shelter_config.registration_intake` — Registration & Intake

### Conditional replacements (swap in when strongly indicated)

- `rk.tax.safety_emergencies.emergency_procedures`
- `rk.tax.basic_needs_daily_living.facilities_use`
- `rk.tax.basic_needs_daily_living.sleeping_rest_areas`
- `rk.tax.location_navigation.in_shelter_locations`

---

## Subtasks checklist (Story 1 → implementation-ready)

### Completed (spec-level)

- [x] Identify Taxonomy v1 categories/subcategories (from Goal 7)
- [x] Choose stable ID scheme and namespace (`rk.tax.`)
- [x] Write canonical node list (IDs + labels + parents)
- [x] Define deterministic mappings (intent → taxonomy; message category → taxonomy)
- [x] Define clarification chip defaults as taxonomy nodes

### Completed (repo artifacts added)

- [x] Added canonical taxonomy seed: `hub/taxonomy/taxonomy_v1.json`
- [x] Added deterministic legacy category mapping seed: `hub/taxonomy/legacy_category_map_v1.json`

### Next (still Story 1, but implementation work)

- [x] Define seed artifact format (JSON) for deterministic loading
- [x] Define initial legacy mapping: existing `kb_articles.category` strings → taxonomy node IDs (deterministic, repeatable)
- [x] Decide minimal DB table strategy for taxonomy storage (nodes, edges, join tables) consistent with `controlled_taxonomy_outline.md`
- [ ] Plan compatibility rollout: dual-read/dual-write (taxonomy-first when present, fallback to legacy strings)
- [ ] Define logging fields to capture applied taxonomy filters + selected node IDs (Goal 7 logging requirements)

---

## Next step (immediate, no code yet)

Produce a concrete, reviewable “implementation spec pack” for Story 1 consisting of:

1) **Seed JSON schema** for `hub/taxonomy/taxonomy_v1.json`
   - required fields per node: `id`, `label`, `parent_ids` (list; enables DAG), optional `description`, `is_active`, `sort_order`
   - include sections for:
     - `nodes`
     - `edges` (optional if `parent_ids` is used)
     - `intent_taxonomy_map`
     - `message_category_taxonomy_map`
     - `clarification_chip_defaults`

2) **Legacy mapping spec** (deterministic)
   - a mapping list for existing `kb_articles.category` strings → taxonomy node IDs
   - normalization rules (casefold, trim, `&` vs `and`, etc.) so backfill is repeatable

3) **DB table plan** (minimum viable)
   - `taxonomy_nodes` (id, label, etc.)
   - `taxonomy_edges` (parent_id, child_id)
   - `kb_item_taxonomy` join table (kb_item_id, taxonomy_node_id, optional source/confidence)
   - `intent_taxonomy_map` (intent_label, taxonomy_node_id)
   - (optional for later) message taxonomy link if needed beyond existing message categories

4) **Compatibility rollout plan**
   - keep current string-based clarification/retry working
   - introduce taxonomy-backed options in parallel, then switch contracts when kiosk supports it

---

## Story implementation summary (current)

We’ve produced the **canonical Taxonomy v1 spec** (stable IDs + labels + hierarchy) and the **deterministic mappings** required by Goal 7 (intent/message category/chip defaults). We also established the ID namespace convention (`rk.tax.`) to avoid collision with legacy “category strings” and to keep future metadata expansions clean.

Repo artifacts now exist for deterministic loading/backfill:

- `hub/taxonomy/taxonomy_v1.json` — canonical taxonomy nodes + mappings + chip defaults
- `hub/taxonomy/legacy_category_map_v1.json` — deterministic mapping from legacy category strings → taxonomy node IDs (with normalization rules and safe fallbacks)

Next implementation steps are to convert this spec into a deterministic seed artifact and design the minimal DB schema + migration/backfill/compat strategy so the existing retrieval/clarification flow is not broken.

---

## Compatibility rollout plan (Goal 7 contract transition)

### Phase 0 (now): additive + no behavior change

- Keep current request/response contract fields:
  - request retry uses `selected_category` (string)
  - clarification returns `clarification_categories` (strings)
- Populate taxonomy tables and backfill `kb_item_taxonomy` from legacy categories.
- Retrieval remains unchanged (vector search still uses embeddings; no taxonomy filtering yet).

### Phase 1: dual-signal contract (additive fields, keep legacy)

- Add additive fields (do not remove legacy yet):
  - response: `clarification_options: [{ id, label }]` (taxonomy-backed)
  - request: `selected_taxonomy_node_id` (taxonomy-backed retry)
- Hub behavior:
  - if `selected_taxonomy_node_id` exists: treat it as **UI constraint** for the next retrieval attempt (Goal 7 precedence: UI > inferred)
  - else fallback to `selected_category` legacy behavior
- Logging:
  - always log which of the two was used (taxonomy vs legacy) for auditing.

Implementation status:

- **Implemented (additive, backward compatible)**:
  - `hub/models/api_models.py`: added `selected_taxonomy_node_id` to `QueryRequest`; added `clarification_options` to `QueryResponse`
  - `hub/api/routes_query.py`: passes through `selected_taxonomy_node_id` to retrieval; returns `clarification_options` if present
  - `hub/retrieval/search.py`:
    - retry enrichment: appends selected taxonomy node label to the search query
    - clarification: returns deterministic taxonomy-backed `clarification_options` per Goal 7 policy:
      - start from `clarification_chip_defaults.default` (max 3)
      - optionally replace one default with a conditional node when strongly indicated (intent / inferred taxonomy / top-k assigned taxonomy)
      - hydrate `{id,label}` from `taxonomy_nodes`

### Phase 2: taxonomy-first behavior (still backward compatible)

- If a KB item has taxonomy assignments, clarification and filtering logic uses taxonomy IDs first.
- If missing taxonomy assignments, fall back deterministically (intent mapping / legacy category mapping) and flag for audit.

### Phase 3: remove legacy category retry (when clients upgraded)

- Stop using free-text `selected_category` for retry/clarification.
- Keep `kb_articles.category` only for display/backward-compat (or remove later).

---

## Logging/observability plan (Goal 7)

Minimum fields to log per query (additive; preserve existing logs):

- intent: `intent_label`, `intent_confidence`
- applied taxonomy constraints:
  - `ui_selected_taxonomy_node_id` (if any)
  - `ui_selected_taxonomy_node_label` (snapshot for debug)
  - `inferred_taxonomy_node_ids` (from intent map; can log primary+secondary)
  - `hard_rule_flags_applied` (e.g., safety override triggered)
- widening/fallback events:
  - `widening_step` (none | remove_inferred | broaden_ui | safe_fallback)
  - `widening_reason`
- counts:
  - candidate counts before/after filtering (per path once multi-path exists)
- evidence:
  - returned evidence IDs + their taxonomy node IDs (once retrieval uses taxonomy)

Note: implement logging fields in a way BM25/hybrid/multi-path can share later.

Implementation status:

- **Implemented (additive)**:
  - DB: added taxonomy observability columns to `query_logs` via:
    - ORM: `hub/db/schema.py` (`QueryLog.ui_selection_source`, `ui_selected_taxonomy_node_id`, `ui_selected_taxonomy_node_label`, `inferred_taxonomy_node_ids`, `widening_step`, `widening_reason`)
    - migrations: `hub/db/migrate_schema.py` and `hub/db/init_db.py` `_MIGRATIONS`
  - Retrieval: `hub/retrieval/search.py` now returns:
    - `ui_selection_source` (`taxonomy|legacy_category|none`)
    - `ui_selected_taxonomy_node_id` + label (when provided)
    - `inferred_taxonomy_node_ids` (from `intent_taxonomy_map`, ordered by rank)
  - Logging: `hub/api/routes_query.py` persists these into `query_logs` (JSON-encoding `inferred_taxonomy_node_ids` as text)

Smoke test status (local dev):

- `init_db()` is idempotent and migrations apply cleanly.
- When the embedding model is missing locally (`packaging/hub_models` not downloaded), retrieval returns `NO_MATCH` but still:
  - sets `ui_selection_source=taxonomy` when `selected_taxonomy_node_id` is provided
  - logs `ui_selected_taxonomy_node_id` and snapshots its label into `query_logs`

Smoke test status (after `packaging/hub_models` present — MiniLM bundled):

- `hub_models_exists` / `hub_models_nonempty`: **True**
- `load_embedder()`: **OK** (SentenceTransformer loads from `packaging/hub_models`)
- `retrieve(..., 'Where is the medical station?', ...)`: **`DIRECT_MATCH`** (vector path works)
- `retrieve` with nonsense query: **`NO_MATCH`**; `clarification_options` may still be absent if scores/intent never enter the clarification band (expected for some inputs)
- Retry with `selected_taxonomy_node_id`: **`ui_selection_source=taxonomy`**
- `submit_query` for medical-station question: **`DIRECT_MATCH`**; `query_logs.ui_selection_source=none` when no taxonomy retry (expected); Ollama formatter may be unavailable (404) — raw KB text used, unrelated to taxonomy
