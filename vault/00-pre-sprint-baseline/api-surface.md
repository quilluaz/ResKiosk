---
title: "Baseline API Surface — All FastAPI Routes"
aliases: ["baseline api", "endpoints"]
tags: [type/endpoint, status/done, frozen, layer/api]
sprint: null
generated_at: "2026-05-11T07:53:18Z"
generated: true
frozen: true
---

# Baseline API Surface — All FastAPI Routes

**⚠️ FROZEN BASELINE — Do not modify. Snapshot as of Sprint 2 completion (2026-05-10).**

All HTTP endpoints exposed by the Hub FastAPI server (`hub/main.py`). Base URL: `http://<hub-ip>:8000`

---

## Query & Voice Pipeline

### POST `/query`
**Purpose**: Main voice query pipeline endpoint — kiosks send transcripts, receive answers  
**File**: `hub/api/routes_query.py`  
**Request**: `QueryRequest` (transcript, language, kb_version, optional taxonomy selection)  
**Response**: `QueryResponse` (answer_text_en, answer_text_localized, answer_type, confidence, clarification options)  
**Flow**: Translation → normalization → intent classification → semantic retrieval → clarification gate → LLM formatting → translation back

### DELETE `/query/session/{session_id}`
**Purpose**: Clear session history for a given session_id  
**File**: `hub/api/routes_query.py`  
**Response**: 204 No Content

### POST `/feedback`
**Purpose**: Submit RLHF-style feedback on query results  
**File**: `hub/api/routes_query.py`  
**Request**: `FeedbackRequest` (query_log_id, source_id, label, language, kiosk_id)  
**Response**: 200 OK

### GET `/faq/suggestions`
**Purpose**: Get top frequently asked questions for kiosk carousel  
**File**: `hub/api/routes_query.py`  
**Response**: `List[FaqSuggestionItem]` (source_id, question, count)  
**Query params**: `limit` (default: 5), `language` (optional filter)

---

## Knowledge Base

### GET `/kb/version`
**Purpose**: Check current KB version (kiosks poll this to know when to refresh)  
**File**: `hub/api/routes_kb.py`  
**Response**: `KBVersionResponse` (kb_version, updated_at)

### GET `/kb/snapshot`
**Purpose**: Full KB sync payload (all enabled articles + shelter config)  
**File**: `hub/api/routes_kb.py`  
**Response**: `KBSnapshot` (kb_version, articles[], structured_config)  
**Used by**: Kiosks on first launch or after detecting version mismatch

---

## Admin — KB Management

### POST `/admin/article`
**Purpose**: Create new KB article  
**File**: `hub/api/routes_admin.py`  
**Request**: `ArticleCreate` (question, answer, category, tags, metadata)  
**Response**: `ArticleResponse` (201 Created, full article with ID)  
**Side effects**: Generates embedding, invalidates corpus cache

### PUT `/admin/article/{id}`
**Purpose**: Update existing KB article  
**File**: `hub/api/routes_admin.py`  
**Request**: `ArticleUpdate` (partial update, all fields optional)  
**Response**: `ArticleResponse` (updated article)  
**Side effects**: Regenerates embedding if question/answer changed, invalidates cache

### DELETE `/admin/article/{id}`
**Purpose**: Soft-delete KB article (sets enabled=0)  
**File**: `hub/api/routes_admin.py`  
**Response**: 204 No Content  
**Side effects**: Invalidates corpus cache

### POST `/admin/publish`
**Purpose**: Publish KB changes (increments kb_version, runs validation, applies publish gate — Sprint 2)  
**File**: `hub/api/routes_admin.py`  
**Request**: Optional `x-admin-user` header for audit trail  
**Response**: `{ kb_version: int, published_at: int, validation_summary: {...} }`  
**Side effects**: Increments `system_version.kb_version`, clears caches

### POST `/admin/import`
**Purpose**: Bulk KB import from CSV  
**File**: `hub/api/routes_admin.py`  
**Request**: Multipart form-data with CSV file  
**Response**: `{ imported: int, skipped: int, errors: [...] }`  
**Side effects**: Creates articles, generates embeddings, invalidates cache

---

## Admin — Shelter Operations Config

### GET `/admin/evac`
**Purpose**: Get current shelter operations config (EvacInfo single row)  
**File**: `hub/api/routes_admin.py`  
**Response**: `EvacInfoResponse` (food_schedule, sleeping_zones, medical_station, etc.)

### PUT `/admin/evac`
**Purpose**: Update shelter operations config  
**File**: `hub/api/routes_admin.py`  
**Request**: Partial update of EvacInfo fields  
**Response**: `EvacInfoUpdateResponse` (updated config + kb_version + evac_sync summary)  
**Side effects**: Syncs changes to KB articles (evac_sync), increments kb_version, invalidates shelter config cache

### GET `/admin/evac/freshness`
**Purpose**: Get freshness status for all evac info sections (Sprint 2)  
**File**: `hub/api/routes_admin.py`  
**Response**: `EvacFreshnessResponse` (freshness_days, sections[], expired_sections[])  
**Used by**: Console to show which sections are stale (>7 days)

### POST `/admin/evac/freshness/confirm`
**Purpose**: Confirm freshness review for specified sections (Sprint 2)  
**File**: `hub/api/routes_admin.py`  
**Request**: `EvacFreshnessConfirmRequest` (sections[], note)  
**Response**: `EvacFreshnessResponse` (updated freshness status)  
**Side effects**: Updates `info_metadata.freshness` timestamps

### GET `/admin/emergency_mode`
**Purpose**: Get current emergency mode status  
**File**: `hub/api/routes_admin.py`  
**Response**: `EmergencyModeResponse` (active: bool, activated_at: int)

### POST `/admin/emergency_mode`
**Purpose**: Toggle emergency mode on/off  
**File**: `hub/api/routes_admin.py`  
**Request**: `EmergencyModeUpdateRequest` (active: bool)  
**Response**: `EmergencyModeResponse` (updated status)  
**Side effects**: Updates `evac_info.emergency_mode` JSON

---

## Admin — FAQ Tracker

### GET `/admin/faq-tracker`
**Purpose**: Get all FAQ tracker entries  
**File**: `hub/api/routes_admin.py`  
**Response**: `List[FAQTrackerItem]` (source_id, question, count, language, etc.)

### DELETE `/admin/faq-tracker/{faq_id}`
**Purpose**: Delete single FAQ entry  
**File**: `hub/api/routes_admin.py`  
**Response**: 204 No Content

### DELETE `/admin/faq-tracker`
**Purpose**: Clear all FAQ entries  
**File**: `hub/api/routes_admin.py`  
**Response**: 204 No Content

---

## Emergency System

### POST `/emergency`
**Purpose**: Create new emergency alert from kiosk  
**File**: `hub/api/routes_emergency.py`  
**Request**: `EmergencyRequest` (kiosk_id, kiosk_location, transcript, language, tier, alert_id_local)  
**Response**: `{ id: int, status: str }` (201 Created)  
**Side effects**: Inserts `emergency_alerts` row with status=ACTIVE

### GET `/emergency/stream`
**Purpose**: Server-Sent Events (SSE) stream of active emergency alerts  
**File**: `hub/api/routes_emergency.py`  
**Response**: text/event-stream (continuous)  
**Used by**: Console EmergencyCalls page for real-time updates

### GET `/emergency/active`
**Purpose**: Get all active emergency alerts (status != RESOLVED, DISMISSED)  
**File**: `hub/api/routes_emergency.py`  
**Response**: `List[EmergencyAlert]` (JSON array)

### GET `/emergency/history`
**Purpose**: Get all emergency alerts (including resolved/dismissed)  
**File**: `hub/api/routes_emergency.py`  
**Response**: `List[EmergencyAlert]` (JSON array)  
**Query params**: `limit` (optional)

### GET `/emergency/{alert_id}/status`
**Purpose**: Get lifecycle status of specific alert  
**File**: `hub/api/routes_emergency.py`  
**Response**: `EmergencyStatusResponse` (status, acknowledged_at, responding_at, etc.)

### PATCH `/emergency/{alert_id}/acknowledge`
**Purpose**: Mark alert as acknowledged (staff saw it)  
**File**: `hub/api/routes_emergency.py`  
**Response**: `{ id: int, status: str }` (status=ACKNOWLEDGED)  
**Side effects**: Sets `acknowledged_at` timestamp

### PATCH `/emergency/{alert_id}/responding`
**Purpose**: Mark alert as responding (staff on the way)  
**File**: `hub/api/routes_emergency.py`  
**Response**: `{ id: int, status: str }` (status=RESPONDING)  
**Side effects**: Sets `responding_at` timestamp

### POST `/emergency/{alert_id}/resolve`
**Purpose**: Resolve emergency alert (mark complete)  
**File**: `hub/api/routes_emergency.py`  
**Request**: `EmergencyResolveRequest` (resolution_notes, resolved_by)  
**Response**: `{ id: int, status: str }` (status=RESOLVED)  
**Side effects**: Sets `resolved_at` timestamp, `resolved=1`

### PATCH `/emergency/{alert_id}/dismiss`
**Purpose**: Dismiss emergency alert (false alarm or canceled by kiosk)  
**File**: `hub/api/routes_emergency.py`  
**Response**: `{ id: int, status: str }` (status=DISMISSED)  
**Side effects**: Sets `dismissed_at` timestamp

---

## Hub-to-Hub Messaging

### GET `/messages`
**Purpose**: Get all hub messages (filtered by query params)  
**File**: `hub/api/routes_messages.py`  
**Response**: `List[MessageResponse]`  
**Query params**: `status`, `priority`, `category_id`, `source_hub_id`, `target_hub_id`, `limit`

### GET `/messages/categories`
**Purpose**: Get all message categories  
**File**: `hub/api/routes_messages.py`  
**Response**: `List[CategoryResponse]` (category_id, category_name, description)

### GET `/messages/hubs`
**Purpose**: Get all registered hubs  
**File**: `hub/api/routes_messages.py`  
**Response**: `List[HubResponse]` (hub_id, hub_name, location)

### GET `/messages/{message_id}`
**Purpose**: Get single message by ID  
**File**: `hub/api/routes_messages.py`  
**Response**: `MessageResponse`

### POST `/messages`
**Purpose**: Create new hub-to-hub message  
**File**: `hub/api/routes_messages.py`  
**Request**: `MessageCreate` (category_id, target_hub_id, subject, content, priority)  
**Response**: `MessageResponse` (201 Created)  
**Side effects**: Inserts `hub_messages` row, can trigger LoRa transmission if target is remote

### PUT `/messages/{message_id}`
**Purpose**: Update message (typically status change)  
**File**: `hub/api/routes_messages.py`  
**Request**: `MessageUpdate` (status: "read" / "published" / "rejected")  
**Response**: `MessageResponse` (updated message)

### DELETE `/messages/{message_id}`
**Purpose**: Delete message  
**File**: `hub/api/routes_messages.py`  
**Response**: 204 No Content

---

## LoRa Communication

### GET `/status` (LoRa)
**Purpose**: Get current LoRa connection status  
**File**: `hub/api/routes_lora.py`  
**Response**: `{ connected: bool, port: str, baud_rate: int, encryption_enabled: bool }`

### GET `/ports` (LoRa)
**Purpose**: List available serial ports for LoRa connection  
**File**: `hub/api/routes_lora.py`  
**Response**: `{ ports: List[str] }` (e.g., ["COM3", "COM4"])

### POST `/connect` (LoRa)
**Purpose**: Connect to ESP32+LoRa transceiver via serial  
**File**: `hub/api/routes_lora.py`  
**Request**: `{ port: str, baud_rate: int }` (baud_rate default: 115200)  
**Response**: `{ success: bool, message: str }`  
**Side effects**: Opens serial connection, saves to `lora_config` table

### POST `/disconnect` (LoRa)
**Purpose**: Disconnect from LoRa transceiver  
**File**: `hub/api/routes_lora.py`  
**Response**: `{ success: bool }`

### POST `/send` (LoRa)
**Purpose**: Send message via LoRa (with encryption if enabled)  
**File**: `hub/api/routes_lora.py`  
**Request**: `{ message: str, target_hub_id: int (optional) }`  
**Response**: `{ success: bool, sent_bytes: int }`

### POST `/send_ack` (LoRa)
**Purpose**: Send acknowledgment for received LoRa message  
**File**: `hub/api/routes_lora.py`  
**Request**: `{ message_id: str }`  
**Response**: `{ success: bool }`

### POST `/send_raw` (LoRa)
**Purpose**: Send raw AT command to LoRa module (debug/testing)  
**File**: `hub/api/routes_lora.py`  
**Request**: `{ command: str }`  
**Response**: `{ response: str }`

### GET `/log` (LoRa)
**Purpose**: Get LoRa transmission log  
**File**: `hub/api/routes_lora.py`  
**Response**: `{ log: List[LogEntry] }` (timestamp, direction, message)

### POST `/auto-connect` (LoRa)
**Purpose**: Enable/disable auto-connect on hub startup  
**File**: `hub/api/routes_lora.py`  
**Request**: `{ enabled: bool }`  
**Response**: `{ success: bool }`  
**Side effects**: Updates `lora_config.auto_connect`

### GET `/encryption` (LoRa)
**Purpose**: Get current encryption settings  
**File**: `hub/api/routes_lora.py`  
**Response**: `{ enabled: bool, algorithm: str }`

### POST `/encryption` (LoRa)
**Purpose**: Enable/configure encryption for LoRa messages  
**File**: `hub/api/routes_lora.py`  
**Request**: `{ enabled: bool, key: str (optional) }`  
**Response**: `{ success: bool }`  
**Side effects**: Stores AES-256-GCM key in `structured_config`

### DELETE `/encryption` (LoRa)
**Purpose**: Disable encryption and delete key  
**File**: `hub/api/routes_lora.py`  
**Response**: 204 No Content

---

## Network & Kiosk Registry

### GET `/network/info`
**Purpose**: Get hub's network configuration (IP, port, mode)  
**File**: `hub/api/routes_network.py`  
**Response**: `NetworkInfo` (ip, port) + `{ mode: "hotspot" | "router" }`

### POST `/register_kiosk`
**Purpose**: Register/update kiosk in auto-discovery registry  
**File**: `hub/api/routes_network.py`  
**Request**: `{ kiosk_id: str, kiosk_name: str, ip_address: str }`  
**Response**: `{ success: bool }`  
**Side effects**: Upserts `kiosk_registry` row

### PUT `/network/kiosk/{kiosk_id}/name`
**Purpose**: Update kiosk name in registry  
**File**: `hub/api/routes_network.py`  
**Request**: `{ name: str }`  
**Response**: `{ success: bool }`

### POST `/network/kiosk/name`
**Purpose**: Batch update kiosk name (alternative endpoint)  
**File**: `hub/api/routes_network.py`  
**Request**: `{ kiosk_id: str, name: str }`  
**Response**: `{ success: bool }`

---

## User Authentication (Sprint 2)

### POST `/login`
**Purpose**: User login (admin console)  
**File**: `hub/api/routes_auth.py`  
**Request**: `LoginRequest` (username, password)  
**Response**: `LoginResponse` (token, user_id, username, fname, lname, is_first_login)  
**Auth**: JWT token issued on success

### POST `/setup`
**Purpose**: First-time profile setup (after initial login)  
**File**: `hub/api/routes_auth.py`  
**Request**: `ProfileSetupRequest` (first_name, last_name, new_password)  
**Response**: `UserResponse` (updated user profile)  
**Auth**: Requires valid token from initial login  
**Side effects**: Sets `is_first_login=False`, updates password

### GET `/me`
**Purpose**: Get current user profile  
**File**: `hub/api/routes_auth.py`  
**Response**: `UserResponse` (user_id, username, fname, lname, is_first_login)  
**Auth**: Requires valid JWT token

### POST `/logout`
**Purpose**: User logout (client-side token invalidation)  
**File**: `hub/api/routes_auth.py`  
**Response**: 204 No Content  
**Auth**: Optional token (logout always succeeds)

---

## System Health & Control

### GET `/health`
**Purpose**: Basic health check (no auth required)  
**File**: `hub/api/routes_system.py`  
**Response**: `{ status: "ok" }`

### GET `/admin/ping`
**Purpose**: Admin health check with timing (measures DB + model readiness)  
**File**: `hub/api/routes_system.py`  
**Response**: `{ status: "ok", latency_ms: float, timestamp: int }`  
**Auth**: Requires admin token

### POST `/admin/shutdown`
**Purpose**: Graceful hub shutdown (stops Uvicorn + Ollama)  
**File**: `hub/api/routes_system.py`  
**Response**: `{ message: "Shutting down..." }`  
**Auth**: Requires admin token  
**Side effects**: Triggers graceful shutdown of hub process

### POST `/admin/restart`
**Purpose**: Restart hub process (if managed by launcher)  
**File**: `hub/api/routes_system.py`  
**Response**: `{ message: "Restarting..." }`  
**Auth**: Requires admin token  
**Side effects**: Triggers process restart via launcher

---

## Static File Serving

### GET `/console`
**Purpose**: Serve React console SPA (redirects to `/console/`)  
**File**: `hub/main.py` (static file mount)  
**Response**: HTTP 302 redirect to `/console/`

### GET `/console/*`
**Purpose**: Serve console static files (HTML, JS, CSS, assets)  
**File**: `hub/main.py` (StaticFiles mount)  
**Response**: Static file from `console/dist/` or `console_static/` (PyInstaller bundle)

### GET `/favicon.ico`
**Purpose**: Suppress browser favicon requests (returns 204 No Content)  
**File**: `hub/main.py`  
**Response**: 204 No Content

### GET `/`
**Purpose**: Root redirect to console or API status  
**File**: `hub/main.py`  
**Response**: HTTP 302 redirect to `/console/` if console assets exist, otherwise JSON status

---

## Environment-Dependent Endpoints

> 🔍 **Inferred**: The following endpoints exist in the codebase but may be unused or deprecated as of Sprint 2 completion:

### Cloud Endpoints (Disabled)
**Status**: All cloud-related routes (`routes_cloud.py`) are commented out in `hub/main.py` as of the offline-first rollback.

**Previously included** (now inactive):
- `POST /cloud/stt` — Cloud speech-to-text
- `POST /cloud/tts` — Cloud text-to-speech
- `POST /cloud/formatter` — Cloud LLM formatting
- `GET /cloud/quota` — Cloud usage quota
- `POST /cloud/consent` — Cloud consent management

---

## Related Baseline Documents

- [[00-pre-sprint-baseline/_index]] — System overview
- [[00-pre-sprint-baseline/architecture]] — Folder layout, entry points
- [[00-pre-sprint-baseline/data-models]] — All SQLAlchemy models, Pydantic schemas
- [[00-pre-sprint-baseline/dependencies]] — requirements.txt, package.json, build.gradle
