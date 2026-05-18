---
title: "Baseline Data Models — SQLAlchemy & Pydantic Schemas"
aliases: ["baseline models", "database schema"]
tags: [type/data-model, status/done, frozen, layer/db]
sprint: null
generated_at: "2026-05-11T07:53:18Z"
generated: true
frozen: true
---

# Baseline Data Models — SQLAlchemy & Pydantic Schemas

**⚠️ FROZEN BASELINE — Do not modify. Snapshot as of Sprint 2 completion (2026-05-10).**

---

## SQLAlchemy ORM Models (hub/db/schema.py)

All persistent data stored in SQLite (`reskiosk.db`). Tables defined in `hub/db/schema.py`.

### Core Query & Knowledge Base

#### 1. `KBArticle` (table: `kb_articles`)
**Purpose**: Main searchable knowledge base — all answers come from here

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment article ID |
| `question` | Text | Question text (English) |
| `answer` | Text | Answer text (English) |
| `category` | Text | Legacy category label |
| `tags` | Text | Comma-separated tags |
| `enabled` | Integer | 1 = active, 0 = disabled |
| `source` | Text | "manual" or import source |
| `created_at` | Integer | Unix timestamp |
| `last_updated` | Integer | Unix timestamp |
| `embedding` | LargeBinary | Serialized MiniLM vector (384-dim) |
| `status` | String | "draft" / "published" / "quarantined" (Sprint 2) |
| `created_by` | Text | User who created (default: "System Generated") |
| `updated_by` | Text | User who last edited |
| `authority` | String | "official" / "shelter_staff" / "volunteer" / "unknown" (Sprint 1) |
| `scope` | String | "shelter_local" / "general" (Sprint 1) |
| `center_id` | String | Center scope (future-friendly) |
| `hub_id` | String | Hub scope (future-friendly) |

**Indexes**: Primary key on `id`

#### 2. `QueryLog` (table: `query_logs`)
**Purpose**: Logs every voice query made by kiosks

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment log ID |
| `session_id` | String | Session UUID (for multi-turn tracking) |
| `kiosk_id` | String | Kiosk identifier |
| `transcript_original` | Text | Original query text (user language) |
| `transcript_english` | Text | Translated query text (EN) |
| `raw_transcript` | Text | Query text passed to retrieve (post-translation) |
| `normalized_transcript` | Text | After normalize_query() |
| `language` | String | User language code (en/ja/es/de/fr) |
| `kb_version` | Integer | KB version at query time |
| `retrieval_score` | Float | Cosine similarity score |
| `answer_type` | String | "DIRECT_MATCH" / "NEEDS_CLARIFICATION" / "NO_MATCH" |
| `source_id` | Integer | KB article ID (if matched) |
| `rewrite_attempted` | Boolean | Whether LLM rewriter was triggered |
| `rewritten_query` | Text | Rewritten query text (if rewrite_attempted) |
| `formatter_mode` | String | "cloud" / "local" |
| `stt_mode` | String | "cloud" / "local" (kiosk-reported) |
| `tts_mode` | String | "cloud" / "local" (kiosk-reported) |
| `connectivity_state` | String | "ONLINE" / "OFFLINE" |
| `cloud_consent_mode` | String | "disabled" / "operator" / "session" |
| `latency_ms` | Float | End-to-end query latency |
| `ui_selection_source` | String | "taxonomy" / "legacy_category" / "none" (Sprint 1) |
| `ui_selected_taxonomy_node_id` | String | Taxonomy node ID if user selected chip |
| `ui_selected_taxonomy_node_label` | Text | Taxonomy node label |
| `inferred_taxonomy_node_ids` | Text | JSON array of inferred nodes |
| `widening_step` | String | "none" / "remove_inferred" / "broaden_ui" / "safe_fallback" |
| `widening_reason` | Text | Why widening triggered |
| `rlhf_top_source_id` | Integer | Shadow RLHF top pick (if RLHF enabled) |
| `rlhf_top_score` | Float | Shadow RLHF top score |
| `created_at` | Integer | Unix timestamp |

**Indexes**: Primary key on `id`

#### 3. `FeedbackLog` (table: `feedback_logs`)
**Purpose**: Per-query feedback from kiosks for RLHF-style ranking

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `session_id` | String | Session UUID |
| `query_log_id` | Integer | FK to QueryLog |
| `source_id` | Integer | KB article ID |
| `label` | Integer | -1 = inaccurate, +1 = thumbs-up (future v2) |
| `language` | String | User language |
| `kiosk_id` | String | Kiosk identifier |
| `center_id` | String | Center identifier |
| `created_at` | DateTime | Feedback timestamp |

**Indexes**: Primary key on `id`

#### 4. `ArticleBias` (table: `article_biases`)
**Purpose**: Per-article bias value learned from FeedbackLog

| Column | Type | Description |
|--------|------|-------------|
| `source_id` | Integer (PK) | KB article ID |
| `bias` | Float | Learned bias value (default: 0.0) |
| `updated_at` | DateTime | Last bias update |

**Indexes**: Primary key on `source_id`

#### 5. `ClarificationResolution` (table: `clarification_resolutions`)
**Purpose**: Gold label when user selects a category after clarification (Sprint 2)

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `session_id` | String | Session UUID |
| `raw_transcript` | Text | Original query text |
| `resolved_intent` | String | Intent label user selected |
| `language` | String | User language |
| `created_at` | DateTime | Resolution timestamp |

**Indexes**: Primary key on `id`

### Shelter Operations

#### 6. `EvacInfo` (table: `evac_info`)
**Purpose**: Single-row table for all editable shelter operations data

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Always 1 (single row) |
| `food_schedule` | Text | Meal times text |
| `food_distribution_location` | Text | Where meals are served |
| `sleeping_zones` | Text | Sleeping area descriptions |
| `medical_station` | Text | Medical station location/hours |
| `registration_steps` | Text | Registration instructions |
| `announcements` | Text | General announcements |
| `emergency_mode` | Text | Emergency mode status (JSON) |
| `last_updated` | Text | Last edit timestamp |
| `info_metadata` | Text | JSON metadata (freshness stamps, etc.) |

**Indexes**: Primary key on `id`

### Emergency System

#### 7. `EmergencyAlert` (table: `emergency_alerts`)
**Purpose**: Emergency button activations sent from kiosks

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `kiosk_id` | Text | Kiosk identifier |
| `kiosk_location` | Text | Kiosk location snapshot |
| `hub_id` | Text | Hub identifier |
| `transcript` | Text | Voice transcript (if available) |
| `language` | Text | User language (default: "en") |
| `timestamp` | Integer | Unix milliseconds |
| `status` | Text | "ACTIVE" / "ACKNOWLEDGED" / "RESPONDING" / "RESOLVED" / "DISMISSED" |
| `tier` | Integer | 1 = immediate, 2 = confirmed |
| `alert_id_local` | Text | Kiosk UUID for deduplication |
| `acknowledged_at` | Integer | Unix ms (when staff acknowledged) |
| `responding_at` | Integer | Unix ms (when staff marked responding) |
| `dismissed_by_kiosk` | Integer | 0 = no, 1 = yes (kiosk canceled) |
| `dismissed_at` | Integer | Unix ms |
| `resolution_notes` | Text | Staff notes on resolution |
| `resolved_by` | Text | Staff username |
| `retry_count` | Integer | Retry attempts (default: 0) |
| `resolved` | Integer | 0 = open, 1 = resolved (legacy) |
| `resolved_at` | Integer | Unix ms (legacy) |

**Indexes**: Primary key on `id`

### Network & System Config

#### 8. `HubIdentity` (table: `hub_identity`)
**Purpose**: Single-row table for this hub's persistent ID (never exposed to operator editing)

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `hub_id` | Integer | Hub numeric ID |
| `hub_name` | Text | Hub display name |
| `created_at` | DateTime | Creation timestamp |

**Indexes**: Primary key on `id`

#### 9. `NetworkConfig` (table: `network_config`)
**Purpose**: Hub's local Wi-Fi and server configuration

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `network_mode` | Text | "hotspot" or "router" |
| `ip_override` | Text | Manual IP override |
| `port` | Integer | Hub HTTP port (default: 8000) |
| `cloud_enabled` | Integer | 0 = disabled, 1 = enabled |
| `cloud_user_overridden` | Integer | 0 = default, 1 = user changed |
| `cloud_last_changed_at` | Integer | Unix timestamp |
| `last_updated` | Integer | Unix timestamp |

**Indexes**: Primary key on `id`

#### 10. `SystemVersion` (table: `system_version`)
**Purpose**: Tracks current KB version so kiosks know when to refresh

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `kb_version` | Integer | Current KB version number |
| `last_published` | Integer | Unix timestamp of last publish |

**Indexes**: Primary key on `id`

#### 11. `KBMeta` (table: `kb_meta`)
**Purpose**: KB metadata (tracks version info separately from SystemVersion)

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `kb_version` | Integer | KB version |
| `updated_at` | DateTime | Last update timestamp |

**Indexes**: Primary key on `id`

#### 12. `StructuredConfig` (table: `structured_config`)
**Purpose**: Key-value configuration store for hub settings

| Column | Type | Description |
|--------|------|-------------|
| `key` | String (PK) | Config key |
| `value` | Text | Config value (often JSON) |
| `updated_at` | DateTime | Last update timestamp |

**Indexes**: Primary key on `key`

### Hub-to-Hub Messaging & Registry

#### 13. `Hub` (table: `hub`)
**Purpose**: Registry of all shelter hubs / evacuation centers

| Column | Type | Description |
|--------|------|-------------|
| `hub_id` | Integer (PK) | Auto-increment |
| `device_id` | Text (unique) | Unique hardware/device identifier |
| `hub_name` | Text (unique) | Hub display name |
| `location` | Text | Hub location description |
| `created_at` | Integer | Unix timestamp |

**Indexes**: Primary key on `hub_id`, unique on `device_id`, unique on `hub_name`

#### 14. `HubMessage` (table: `hub_messages`)
**Purpose**: Central table for all communication between hubs

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `category_id` | Integer | FK to Category |
| `source_hub_id` | Integer | FK to Hub (sender) |
| `target_hub_id` | Integer | FK to Hub (receiver, NULL = broadcast) |
| `subject` | Text | Message subject |
| `content` | Text | Message body |
| `priority` | Text | "normal" / "urgent" / "emergency" |
| `status` | Text | "pending" / "delivered" / "read" / "published" / "rejected" |
| `sent_at` | Integer | Unix timestamp |
| `received_at` | Integer | Unix timestamp |
| `published_at` | Integer | Unix timestamp |
| `location` | Text | Location context |
| `created_by` | Text | User who created (future: FK to user.user_id) |
| `hop_count` | Integer | LoRa hop count |
| `ttl` | Integer | Time-to-live for message propagation |
| `received_via` | Text | "lora" / "manual" / "wifi-local" |
| `details` | Text | JSON for category-specific fields |

**Indexes**: Primary key on `id`, FK on `category_id`, `source_hub_id`, `target_hub_id`

#### 15. `Category` (table: `categories`)
**Purpose**: Preloaded message categories for hub-to-hub messaging

| Column | Type | Description |
|--------|------|-------------|
| `category_id` | Integer (PK) | Auto-increment |
| `category_name` | Text (unique) | Category label |
| `description` | Text | Category description |

**Indexes**: Primary key on `category_id`, unique on `category_name`

#### 16. `Kiosk` (table: `kiosk`)
**Purpose**: Physical kiosk/tablet devices registered under a hub

| Column | Type | Description |
|--------|------|-------------|
| `kiosk_id` | Integer (PK) | Auto-increment |
| `hub_id` | Integer | FK to Hub |
| `kiosk_name` | Text | Kiosk display name |
| `location` | Text | Kiosk location |
| `status` | Text | "online" / "offline" / "maintenance" |
| `last_seen` | Integer | Unix timestamp |
| `created_at` | Integer | Unix timestamp |

**Indexes**: Primary key on `kiosk_id`, FK on `hub_id`

#### 17. `KioskRegistry` (table: `kiosk_registry`)
**Purpose**: Auto-discovered kiosks on the network (separate from managed Kiosk table)

| Column | Type | Description |
|--------|------|-------------|
| `kiosk_id` | Text (PK) | Kiosk identifier |
| `kiosk_name` | Text | Kiosk display name |
| `ip_address` | Text | Kiosk IP address |
| `hub_id` | Text | Hub identifier |
| `first_seen` | DateTime | First discovery timestamp |
| `last_seen` | DateTime | Last seen timestamp |

**Indexes**: Primary key on `kiosk_id`

### LoRa Communication

#### 18. `LoraConfig` (table: `lora_config`)
**Purpose**: Persisted ESP+LoRa connection settings for auto-reconnect

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `port` | Text | Serial port path (e.g., COM3) |
| `baud_rate` | Integer | Baud rate (default: 115200) |
| `connection_type` | Text | "serial" or "bluetooth" |
| `auto_connect` | Integer | 1 = reconnect on startup, 0 = manual |
| `last_connected` | Integer | Unix timestamp |

**Indexes**: Primary key on `id`

### User Authentication (Sprint 2)

#### 19. `User` (table: `user`)
**Purpose**: Admin users who can log in and manage the system

| Column | Type | Description |
|--------|------|-------------|
| `user_id` | Integer (PK) | Auto-increment |
| `username` | Text (unique) | Login username |
| `fname` | Text | First name |
| `mname` | Text | Middle name |
| `lname` | Text | Last name |
| `password` | Text | bcrypt-hashed password |
| `is_first_login` | Boolean | True = must complete profile setup |
| `created_at` | Integer | Unix timestamp |

**Indexes**: Primary key on `user_id`, unique on `username`

### FAQ & Analytics

#### 20. `FAQTracker` (table: `faq_tracker`)
**Purpose**: Tracks frequently asked questions grouped by KB article answer (source_id)

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `source_id` | Integer (unique) | KB article ID |
| `source_question` | Text | KB article question (for display) |
| `source_answer` | Text | KB article answer snippet |
| `question_normalized` | Text | Last user query (lowercased) |
| `question_display` | Text | Last user query (original case) |
| `language` | String | Query language |
| `count` | Integer | Number of times asked |
| `first_asked_at` | Integer | Unix timestamp |
| `last_asked_at` | Integer | Unix timestamp |
| `kiosk_id` | String | Kiosk identifier |
| `answer_type` | String | Answer type (DIRECT_MATCH, etc.) |

**Indexes**: Primary key on `id`, unique index on `source_id`

### Taxonomy System (Sprint 1 — Goal 7)

#### 21. `TaxonomyNode` (table: `taxonomy_nodes`)
**Purpose**: Controlled taxonomy node with stable string ID (rk.tax.*)

| Column | Type | Description |
|--------|------|-------------|
| `id` | String (PK) | Stable ID like `rk.tax.health_medical.medical_services` |
| `label` | Text | Display label |
| `description` | Text | Node description |
| `is_active` | Integer | 1 = active, 0 = inactive |
| `sort_order` | Integer | Display order |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last update timestamp |

**Indexes**: Primary key on `id`

#### 22. `TaxonomyEdge` (table: `taxonomy_edges`)
**Purpose**: DAG edge (parent → child). Multi-parent allowed; must remain acyclic by policy.

| Column | Type | Description |
|--------|------|-------------|
| `parent_id` | String (PK) | FK to TaxonomyNode (parent) |
| `child_id` | String (PK) | FK to TaxonomyNode (child) |
| `created_at` | DateTime | Edge creation timestamp |

**Indexes**: Composite primary key on (`parent_id`, `child_id`)

#### 23. `KBItemTaxonomy` (table: `kb_item_taxonomy`)
**Purpose**: Assignment of a KB article to one or more taxonomy nodes

| Column | Type | Description |
|--------|------|-------------|
| `kb_item_id` | Integer (PK) | FK to KBArticle |
| `taxonomy_node_id` | String (PK) | FK to TaxonomyNode |
| `source` | Text | "manual" / "import" / "legacy_category" / "auto" |
| `confidence` | Float | Confidence score (for auto assignments) |
| `created_at` | DateTime | Assignment timestamp |

**Indexes**: Composite primary key on (`kb_item_id`, `taxonomy_node_id`)

#### 24. `IntentTaxonomyMap` (table: `intent_taxonomy_map`)
**Purpose**: Normalized intent → taxonomy mapping (multiple rows per intent label)

| Column | Type | Description |
|--------|------|-------------|
| `intent_label` | String (PK) | Intent string (e.g., "food", "medical") |
| `taxonomy_node_id` | String (PK) | FK to TaxonomyNode |
| `rank` | Integer | 1 = primary, 2+ = secondary |
| `created_at` | DateTime | Mapping creation timestamp |

**Indexes**: Composite primary key on (`intent_label`, `taxonomy_node_id`)

---

## Pydantic Models (hub/models/api_models.py)

Request/response DTOs for FastAPI endpoints.

### KB Article DTOs

#### `ArticleBase`
Base schema for KB article creation/update
- `question: str`
- `answer: str`
- `category: str`
- `tags: List[str]`
- `enabled: bool`
- `status: Optional[str]` ("draft" / "published" / "quarantined")
- `authority: Optional[str]` ("official" / "shelter_staff" / "volunteer" / "unknown")
- `scope: Optional[str]` ("shelter_local" / "general")
- `center_id: Optional[str]`
- `hub_id: Optional[str]`

#### `ArticleCreate`
Inherits from `ArticleBase`

#### `ArticleUpdate`
Partial update schema (all fields optional)

#### `ArticleResponse`
Full article response with DB fields
- Includes all `ArticleBase` fields plus:
- `id: int`
- `source: Optional[str]`
- `created_at: Optional[int]`
- `last_updated: Optional[int]`
- `created_by: Optional[str]`
- `updated_by: Optional[str]`

### Query DTOs

#### `QueryRequest`
Voice query from kiosk
- `center_id: str`
- `kiosk_id: str`
- `transcript_original: str`
- `transcript_english: Optional[str]`
- `language: str`
- `kb_version: int`
- `is_retry: bool`
- `selected_category: Optional[str]`
- `selected_taxonomy_node_id: Optional[str]` (Sprint 1)
- `session_id: Optional[str]`
- `exclude_source_ids: Optional[List[int]]`
- `stt_mode: Optional[str]` ("cloud" / "local")
- `tts_mode: Optional[str]` ("cloud" / "local")
- `cloud_consent_mode: Optional[str]` ("operator" / "session" / "disabled")
- `follow_up_token: Optional[str]`

#### `QueryResponse`
Answer returned to kiosk
- `answer_text_en: str`
- `answer_text_localized: Optional[str]`
- `answer_type: str` ("DIRECT_MATCH" / "NEEDS_CLARIFICATION" / "NO_MATCH")
- `confidence: float`
- `kb_version: int`
- `source_id: Optional[int]`
- `clarification_categories: Optional[List[str]]` (legacy)
- `clarification_options: Optional[List[TaxonomyOption]]` (Sprint 2)
- `query_log_id: Optional[int]`
- `rlhf_top_source_id: Optional[int]`
- `rlhf_top_score: Optional[float]`
- `follow_up_prompt: Optional[str]`
- `follow_up_intent: Optional[str]`
- `clarification_context: Optional[ClarificationContext]` (Sprint 2)

#### `ClarificationContext` (Sprint 2)
Context for clarification pause/resume flow
- `original_query: str`
- `normalized_text: str`
- `detected_intent: str`
- `intent_confidence: float`
- `suggested_categories: List[str]`
- `kb_version: int`
- `session_id: Optional[str]`
- `pipeline_status: str` (always "paused")

#### `TaxonomyOption` (Sprint 1)
Taxonomy node chip for kiosk UI
- `id: str` (taxonomy node ID)
- `label: str` (display text)

### KB Snapshot DTOs

#### `KBSnapshot`
Complete KB sync payload for kiosk
- `kb_version: int`
- `articles: List[ArticleResponse]`
- `structured_config: EvacInfoResponse`

#### `KBVersionResponse`
KB version check response
- `kb_version: int`
- `updated_at: Optional[int]`

### Evac Info DTOs

#### `EvacInfoResponse`
Shelter operations config
- `id: int`
- `food_schedule: Optional[str]`
- `food_distribution_location: Optional[str]`
- `sleeping_zones: Optional[str]`
- `medical_station: Optional[str]`
- `registration_steps: Optional[str]`
- `announcements: Optional[str]`
- `emergency_mode: Optional[str]`
- `last_updated: Optional[str]`
- `metadata: Optional[str]` (JSON)

#### `EvacInfoUpdateResponse`
Extends `EvacInfoResponse` with:
- `kb_version: Optional[int]`
- `published_at: Optional[int]`
- `evac_sync: Optional[EvacSyncSummary]`

#### `EvacFreshnessSection`
Freshness status for one evac info section
- `section: str`
- `last_reviewed_at: Optional[int]`
- `reviewed_by: Optional[str]`
- `age_days: Optional[int]`
- `expires_at: Optional[int]`
- `is_expired: bool`

#### `EvacFreshnessResponse`
Full freshness report
- `freshness_days: int`
- `sections: List[EvacFreshnessSection]`
- `expired_sections: List[str]`

#### `EvacFreshnessConfirmRequest`
Freshness confirmation payload
- `sections: List[str]`
- `note: Optional[str]`

### Emergency DTOs

#### `EmergencyRequest`
Emergency alert from kiosk
- `kiosk_id: str`
- `kiosk_location: str`
- `hub_id: Optional[str]`
- `transcript: Optional[str]`
- `language: str`
- `timestamp: Optional[int]`
- `tier: Optional[int]` (1 or 2)
- `alert_id_local: Optional[str]`
- `retry_count: Optional[int]`

#### `EmergencyResolveRequest`
Resolution payload from console
- `resolution_notes: Optional[str]`
- `resolved_by: Optional[str]`

#### `EmergencyModeUpdateRequest`
Emergency mode toggle
- `active: bool`

#### `EmergencyModeResponse`
Emergency mode status
- `active: bool`
- `activated_at: int`

#### `EmergencyStatusResponse`
Alert lifecycle status
- `id: int`
- `status: str` ("ACTIVE" / "ACKNOWLEDGED" / "RESPONDING" / "RESOLVED" / "DISMISSED")
- `acknowledged_at: Optional[int]`
- `responding_at: Optional[int]`
- `dismissed_at: Optional[int]`
- `dismissed_by_kiosk: Optional[int]`
- `resolved_at: Optional[int]`

### Feedback DTOs

#### `FeedbackRequest`
RLHF feedback from kiosk
- `session_id: Optional[str]`
- `query_log_id: int`
- `source_id: Optional[int]`
- `label: int` (-1 = inaccurate, +1 = thumbs-up)
- `language: str`
- `kiosk_id: Optional[str]`
- `center_id: Optional[str]`

### Auth DTOs (Sprint 2)

#### `LoginRequest`
User login
- `username: str`
- `password: str`

#### `LoginResponse`
Auth token response
- `token: str`
- `user_id: int`
- `username: str`
- `fname: Optional[str]`
- `lname: Optional[str]`
- `is_first_login: bool`

#### `ProfileSetupRequest`
First-time profile setup
- `first_name: str`
- `last_name: str`
- `new_password: str`

#### `UserResponse`
User profile info
- `user_id: int`
- `username: str`
- `fname: Optional[str]`
- `lname: Optional[str]`
- `is_first_login: bool`

### Hub Messaging DTOs

#### `MessageCreate`
Create hub-to-hub message
- `category_id: Optional[int]`
- `target_hub_id: Optional[int]` (NULL = broadcast)
- `subject: str`
- `content: str`
- `priority: str` ("normal" / "urgent" / "emergency")

#### `MessageUpdate`
Update message status
- `status: Optional[str]` ("pending" / "read" / "published" / "rejected")

#### `MessageResponse`
Full message details
- `id: int`
- `category_id: Optional[int]`
- `category_name: Optional[str]`
- `source_hub_id: Optional[int]`
- `source_hub_name: Optional[str]`
- `target_hub_id: Optional[int]`
- `target_hub_name: Optional[str]`
- `subject: Optional[str]`
- `content: Optional[str]`
- `priority: Optional[str]`
- `status: Optional[str]`
- `sent_at: Optional[int]`
- `received_at: Optional[int]`
- `published_at: Optional[int]`
- `location: Optional[str]`
- `created_by: Optional[str]`
- `hop_count: Optional[int]`
- `ttl: Optional[int]`
- `received_via: Optional[str]`
- `details: Optional[str]`

#### `CategoryResponse`
Message category
- `category_id: int`
- `category_name: str`
- `description: Optional[str]`

#### `HubResponse`
Hub registry entry
- `hub_id: int`
- `hub_name: str`
- `location: Optional[str]`

### FAQ DTOs

#### `FAQTrackerItem`
FAQ entry
- `id: int`
- `source_id: int`
- `source_question: Optional[str]`
- `source_answer: Optional[str]`
- `question_normalized: Optional[str]`
- `question_display: Optional[str]`
- `language: Optional[str]`
- `count: int`
- `first_asked_at: Optional[int]`
- `last_asked_at: Optional[int]`
- `kiosk_id: Optional[str]`
- `answer_type: Optional[str]`

#### `FaqSuggestionItem`
FAQ suggestion for carousel
- `source_id: int`
- `question: str`
- `count: int`

### Misc DTOs

#### `NetworkInfo`
Hub network info
- `ip: str`
- `port: int`

#### `StructuredConfigUpsert`
Generic config upsert
- `value: Any`

#### `StructuredConfigResponse`
Config key-value pair
- `key: str`
- `value: Any`
- `updated_at: Optional[str]`

---

## Related Baseline Documents

- [[00-pre-sprint-baseline/_index]] — System overview
- [[00-pre-sprint-baseline/architecture]] — Folder layout, entry points
- [[00-pre-sprint-baseline/api-surface]] — Complete FastAPI route catalog
- [[00-pre-sprint-baseline/dependencies]] — requirements.txt, package.json, build.gradle
