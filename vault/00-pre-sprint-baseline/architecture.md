---
title: "Baseline Architecture — Folder Layout & Entry Points"
aliases: ["baseline architecture"]
tags: [type/architecture, status/done, frozen, component/hub, component/console, component/kiosk]
sprint: null
generated_at: "2026-05-11T07:53:18Z"
generated: true
frozen: true
---

# Baseline Architecture — Folder Layout & Entry Points

**⚠️ FROZEN BASELINE — Do not modify. Snapshot as of Sprint 2 completion (2026-05-10).**

---

## Repository Root Structure

```
ResKiosk/
├── hub/                    # Python/FastAPI backend
├── console/                # React/Vite admin dashboard
├── kiosk/                  # Android Kotlin app
├── docs/                   # Architecture & pipeline docs
├── requirements.txt        # Python dependencies
├── CLAUDE.md               # Developer mode instructions
├── CLAUDE.agent.md         # Autonomous agent constitution
├── vault/                  # Obsidian knowledge vault (agent writes here)
└── second-brain-agent.sh   # Agent launcher script
```

---

## Hub (Python/FastAPI Backend)

### Folder Layout

```
hub/
├── main.py                    # FastAPI app entry point
├── launcher.py                # Ollama + Uvicorn orchestrator
├── api/                       # Route handlers (all endpoints)
│   ├── routes_query.py        # POST /query (main voice pipeline)
│   ├── routes_kb.py           # GET /kb/version, /kb/snapshot
│   ├── routes_admin.py        # Admin endpoints (evac, KB mgmt)
│   ├── routes_system.py       # GET /admin/ping, system info
│   ├── routes_emergency.py    # Emergency alert lifecycle
│   ├── routes_messages.py     # Hub-to-hub messaging
│   ├── routes_lora.py         # LoRa serial config/control
│   ├── routes_network.py      # Network config (hotspot/router mode)
│   └── routes_auth.py         # User login, profile setup
├── retrieval/                 # Core retrieval logic
│   ├── pipeline.py            # Canonical query pipeline orchestrator
│   ├── search.py              # Semantic retrieval (MiniLM + cosine)
│   ├── intent.py              # Prototype-based intent classifier
│   ├── embedder.py            # MiniLM model loading, embed_text()
│   ├── translator.py          # NLLB-200 bidirectional translation
│   ├── formatter.py           # LLM response formatter (translategemma)
│   ├── rewriter.py            # LLM query rewriter (llama3.2)
│   ├── normalizer.py          # Query normalization (synonyms, lowercase)
│   ├── rlhf_bias.py           # RLHF bias computation (offline)
│   └── inventory.py           # Inventory-specific retrieval logic
├── validation/                # KB metadata validation (Sprint 2)
│   ├── __init__.py
│   └── metadata.py            # Rule engine, publish gate logic
├── services/                  # Shared business logic
│   ├── connectivity.py        # Network state tracking
│   ├── llm_router.py          # Cloud/local LLM selection
│   ├── cloud_stt.py           # Cloud STT wrapper (unused in offline mode)
│   ├── cloud_tts.py           # Cloud TTS wrapper (unused in offline mode)
│   ├── cloud_formatter.py     # Cloud LLM formatter (unused in offline mode)
│   └── cloud_quota.py         # Cloud usage tracking (unused in offline mode)
├── db/                        # Database layer
│   ├── schema.py              # SQLAlchemy ORM models (all tables)
│   ├── session.py             # SessionLocal factory, Base
│   ├── init_db.py             # Database initialization
│   ├── seed.py                # Seed data (categories, default user)
│   ├── evac_sync.py           # Evac info → KB article sync
│   └── migrate_schema.py      # Schema migration runner
├── models/                    # Pydantic request/response models
│   └── api_models.py          # All API DTOs
├── core/                      # Shared utilities
│   ├── crypto.py              # AES-256-GCM encryption (LoRa messages)
│   ├── logger_stream.py       # Log capture for console display
│   ├── lora_serial.py         # ESP32+LoRa serial manager
│   └── network_manager.py     # Network config helpers
├── taxonomy/                  # Taxonomy definitions (Goal 7)
│   └── taxonomy_v1.json       # DAG structure, chip policy
├── tests/                     # Unit/integration tests
│   ├── test_pipeline_order.py
│   ├── test_clarification_response.py
│   ├── test_metadata_validation.py
│   └── test_publish_gate.py
└── bulk_kb_import.py          # Bulk KB CSV import utility
```

### Hub Entry Points

#### 1. `hub/main.py`
**Purpose**: FastAPI application factory, CORS, router registration, static file serving

**Key Functions**:
- `on_startup()`: Initializes DB, embeds missing articles, prewarms models, auto-connects LoRa
- `_embed_missing_articles()`: Generates embeddings for KB articles without them
- `_prewarm_models()`: Loads MiniLM, IntentClassifier, NLLB, warms Ollama in background
- `_lora_auto_connect()`: Attempts LoRa serial reconnection from saved config
- `get_base_path()`: Handles PyInstaller bundled vs source repo paths

**Routes Included**:
- `/query` — Voice query pipeline (routes_query)
- `/kb/*` — KB snapshot, version (routes_kb)
- `/admin/*` — Admin operations (routes_admin)
- `/emergency/*` — Emergency alerts (routes_emergency)
- `/messages/*` — Hub messaging (routes_messages)
- `/lora/*` — LoRa config (routes_lora)
- `/network/*` — Network config (routes_network)
- `/auth/*` — User auth (routes_auth)
- `/console` — Served static files (React build)

#### 2. `hub/launcher.py`
**Purpose**: Orchestrates Ollama server + Uvicorn hub server in parallel processes

**Why it exists**: Ensures Ollama is running before hub starts, handles graceful shutdown

---

## Console (React/Vite Admin Dashboard)

### Folder Layout

```
console/
├── src/
│   ├── main.jsx               # React entry point
│   ├── App.jsx                # Router setup, layout
│   ├── pages/                 # All page components
│   │   ├── Dashboard.jsx      # Hub status, quick stats, evac info
│   │   ├── KBViewer.jsx       # KB article list, search, edit, create
│   │   ├── ShelterConfig.jsx  # Evac info editor, freshness tracking
│   │   ├── EmergencyCalls.jsx # Emergency alert monitoring
│   │   ├── LogsViewer.jsx     # Query logs, feedback logs
│   │   ├── QueryTracker.jsx   # Query log analysis
│   │   ├── FAQManager.jsx     # FAQ tracker display
│   │   ├── HubMessages.jsx    # Hub-to-hub messages
│   │   ├── NetworkSetup.jsx   # Network config UI
│   │   ├── Login.jsx          # Auth screen
│   │   └── ProfileSetup.jsx   # First-login profile setup
│   ├── components/            # Reusable UI components (modals, cards)
│   └── utils/                 # API client, helpers
├── public/                    # Static assets
├── index.html                 # SPA shell
├── package.json               # npm dependencies
└── vite.config.js             # Vite build config
```

### Console Entry Point

**`console/src/main.jsx`** → Renders `<App />` into `#root`

**`console/src/App.jsx`** → React Router setup:
- `/` → Dashboard
- `/kb` → KBViewer
- `/config` → ShelterConfig
- `/emergency` → EmergencyCalls
- `/logs` → LogsViewer
- `/query-tracker` → QueryTracker
- `/faq` → FAQManager
- `/messages` → HubMessages
- `/network` → NetworkSetup
- `/login` → Login
- `/profile-setup` → ProfileSetup

**API Communication**: All pages use Axios to call hub endpoints (e.g., `GET http://<hub-ip>:8000/kb/snapshot`)

---

## Kiosk (Android Kotlin App)

### Folder Layout

```
kiosk/
└── app/
    ├── build.gradle            # Dependencies (Sherpa-ONNX, Retrofit, Compose)
    └── src/main/java/com/reskiosk/
        ├── MainActivity.kt            # App entry, navigation host
        ├── ModelConstants.kt          # STT/TTS model metadata
        ├── viewmodel/
        │   └── KioskViewModel.kt      # State machine, full query pipeline
        ├── ui/                        # Composables
        │   ├── MainKioskScreen.kt     # Voice UI (listening, speaking, chat)
        │   ├── LanguageScreen.kt      # Language picker
        │   ├── SetupScreen.kt         # First-run setup (Hub URL, center/kiosk ID)
        │   ├── HubScreen.kt           # Hub connection QR scan
        │   ├── SettingsScreen.kt      # Settings menu
        │   └── PortraitCaptureActivity.kt  # QR scanner activity
        ├── audio/
        │   └── AudioRecorder.kt       # 16kHz PCM recording, 1.5s ring buffer
        ├── stt/
        │   ├── SherpaSttEngine.kt     # Sherpa-ONNX STT wrapper (Zipformer/Whisper)
        │   ├── SttPostProcessor.kt    # Filler removal, dedup, fuzzy correction
        │   ├── IntonationDetector.kt  # Question tone detection
        │   └── QuestionWordDetector.kt # Question word detection
        ├── tts/
        │   └── SherpaTtsEngine.kt     # Sherpa-ONNX TTS wrapper (VITS)
        ├── emergency/
        │   ├── EmergencyDetector.kt   # Tier 1/2 keyword matching
        │   └── EmergencyStrings.kt    # Multilingual emergency phrases
        ├── network/
        │   └── HubApiClient.kt        # Retrofit HTTP client
        ├── translate/
        │   └── MlKitTranslator.kt     # Unused ML Kit wrapper
        └── utils/
            └── ModelDownloader.kt     # STT/TTS model download from Hub
```

### Kiosk Entry Point

**`MainActivity.kt`** → Sets up Compose navigation:
- `SetupScreen` (if not configured)
- `LanguageScreen` (language selection)
- `MainKioskScreen` (main voice UI)
- `SettingsScreen` (config changes)
- `HubScreen` (QR scan for Hub connection)

**`KioskViewModel.kt`** → Core state machine:
- **States**: Idle → Listening → Processing → Speaking → Emergency
- **Query pipeline**:
  1. Capture audio → SherpaSttEngine → SttPostProcessor
  2. EmergencyDetector checks transcript
  3. If not emergency → POST to `/query`
  4. Parse response → SherpaTtsEngine speaks answer
  5. Display chat bubble with text

---

## Component Communication

### Kiosk → Hub Query Flow

```
┌────────────────────────────────────────────────────────────────┐
│ Kiosk (Android)                                                │
│   AudioRecorder → SherpaSttEngine → SttPostProcessor           │
│   → EmergencyDetector → HubApiClient.submitQuery()            │
└─────────────────────────────┬──────────────────────────────────┘
                              │ POST /query
                              │ JSON: { transcript, language, kb_version, ... }
                              ↓
┌────────────────────────────────────────────────────────────────┐
│ Hub (FastAPI)                                                  │
│   routes_query.py → QueryPipeline → search.retrieve()         │
│   → IntentClassifier → semantic search → LLM formatter        │
│   → translator → QueryResponse JSON                           │
└─────────────────────────────┬──────────────────────────────────┘
                              │ HTTP 200
                              │ JSON: { answer_text_en, answer_text_localized, ... }
                              ↓
┌────────────────────────────────────────────────────────────────┐
│ Kiosk (Android)                                                │
│   Parse response → SherpaTtsEngine.speak()                     │
│   → Update chat UI with answer                                 │
└────────────────────────────────────────────────────────────────┘
```

### Console → Hub Admin Flow

```
┌────────────────────────────────────────────────────────────────┐
│ Console (React)                                                │
│   KBViewer.jsx → Axios.post('/admin/kb/articles', {...})      │
└─────────────────────────────┬──────────────────────────────────┘
                              │ POST /admin/kb/articles
                              │ JSON: { question, answer, category, ... }
                              ↓
┌────────────────────────────────────────────────────────────────┐
│ Hub (FastAPI)                                                  │
│   routes_admin.py → schema.KBArticle (SQLAlchemy)             │
│   → db.commit() → embedder.embed_text() → invalidate cache    │
│   → _increment_kb_version()                                    │
└─────────────────────────────┬──────────────────────────────────┘
                              │ HTTP 200
                              │ JSON: { id, question, answer, ... }
                              ↓
┌────────────────────────────────────────────────────────────────┐
│ Console (React)                                                │
│   Refresh KB list → Display success toast                      │
└────────────────────────────────────────────────────────────────┘
```

---

## Key Architectural Patterns

### Hub Patterns

1. **Dependency Injection**: FastAPI `Depends(get_db)` for DB sessions
2. **Model Prewarming**: Background threads warm ML models at startup to reduce first-query latency
3. **Cache Invalidation**: `invalidate_corpus_cache()` / `invalidate_shelter_config_cache()` on KB/evac edits
4. **SQLite as Single Source of Truth**: All persistent state (KB, logs, config, emergencies) in one SQLite file
5. **Canonical Pipeline**: `QueryPipeline` in `retrieval/pipeline.py` orchestrates all stages with logging

### Console Patterns

1. **SPA Routing**: React Router for client-side navigation
2. **API-First**: All data fetched/mutated via Axios calls to hub endpoints
3. **Stateless Components**: Minimal local state, refresh from server on mount
4. **Token-based Auth**: JWT token stored in localStorage after login

### Kiosk Patterns

1. **ViewModel State Machine**: All business logic in `KioskViewModel`, UI is pure Compose
2. **Offline-First**: STT/TTS runs locally, only query processing requires hub
3. **Ring Buffer Pre-Capture**: AudioRecorder keeps 1.5s buffer before user speaks to avoid clipped speech
4. **Emergency Short-Circuit**: EmergencyDetector runs *before* sending query to hub to minimize latency

---

## Deployment Topology

### Production Setup (Typical Shelter)

```
                   ┌─────────────────────────────────┐
                   │  Hub Laptop (Windows 10/11)     │
                   │  ▸ ResKiosk-Hub.exe running     │
                   │  ▸ Ollama server embedded       │
                   │  ▸ SQLite DB at ./reskiosk.db   │
                   │  ▸ LAN IP: 192.168.4.1          │
                   └────────────┬────────────────────┘
                                │
                      Wi-Fi Hotspot (SSID: ResKiosk-Hub)
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
   ┌─────▼─────┐          ┌─────▼─────┐         ┌─────▼─────┐
   │ Kiosk #1  │          │ Kiosk #2  │   ...   │ Kiosk #N  │
   │ (Android) │          │ (Android) │         │ (Android) │
   └───────────┘          └───────────┘         └───────────┘

   ┌─────────────────────────────────────────────────────────┐
   │  Admin Console (any device on same network)             │
   │  Browser → http://192.168.4.1:8000/console/             │
   └─────────────────────────────────────────────────────────┘
```

### LoRa Fallback (Hub-to-Hub)

```
┌──────────┐          ┌──────────┐          ┌──────────┐
│  Hub A   │ ◄─LoRa─► │ Relay    │ ◄─LoRa─► │  Hub B   │
│          │          │ (ESP32)  │          │          │
└──────────┘          └──────────┘          └──────────┘
```

Each hub can have an ESP32+LoRa transceiver connected via USB serial for resilient hub-to-hub messaging when primary network fails.

---

## Build & Packaging

### Hub
- **Dev**: `uvicorn hub.main:app --reload`
- **Prod**: `python hub/launcher.py` (launches Ollama + Uvicorn)
- **Packaging**: PyInstaller spec creates `ResKiosk-Hub.exe` with embedded Python, models, console static files

### Console
- **Dev**: `npm run dev` (Vite dev server at http://localhost:5173)
- **Build**: `npm run build` → outputs to `console/dist/`
- **Deployment**: Hub serves `console/dist/` at `/console` path

### Kiosk
- **Dev**: Android Studio → Run on emulator/device
- **Build**: `./gradlew assembleRelease`
- **Deployment**: APK installed on shelter tablets, models downloaded from hub on first run

---

## Related Baseline Documents

- [[00-pre-sprint-baseline/_index]] — System overview
- [[00-pre-sprint-baseline/data-models]] — All SQLAlchemy models, tables
- [[00-pre-sprint-baseline/api-surface]] — Complete FastAPI route catalog
- [[00-pre-sprint-baseline/dependencies]] — requirements.txt, package.json, build.gradle
