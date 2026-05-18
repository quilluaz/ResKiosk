---
title: "Baseline Dependencies — Python, npm, Android"
aliases: ["baseline dependencies", "packages"]
tags: [type/architecture, status/done, frozen, layer/infra]
sprint: null
generated_at: "2026-05-11T07:53:18Z"
generated: true
frozen: true
---

# Baseline Dependencies — Python, npm, Android

**⚠️ FROZEN BASELINE — Do not modify. Snapshot as of Sprint 2 completion (2026-05-10).**

---

## Hub (Python) — requirements.txt

**File**: `requirements.txt`  
**Python version**: 3.10+

### Core Web Framework

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.109.0 | Web framework, async HTTP server, OpenAPI schema |
| `uvicorn` | 0.27.0 | ASGI server for FastAPI |
| `websockets` | >=12.0 | WebSocket support (SSE for emergency stream) |
| `sqlalchemy` | 2.0.25 | ORM, database abstraction |
| `requests` | 2.31.0 | HTTP client for external APIs |
| `python-multipart` | 0.0.6 | Multipart form-data parsing (file uploads) |
| `jinja2` | 3.1.3 | Template engine (unused in baseline, kept for future) |
| `aiofiles` | 23.2.1 | Async file I/O (log streaming, model downloads) |

### AI / ML

| Package | Version | Purpose |
|---------|---------|---------|
| `sentence-transformers` | >=2.6.1 | MiniLM embeddings (all-MiniLM-L6-v2) |
| `transformers` | >=4.38.0 | Hugging Face pipeline (NLLB-200 translation) |
| `torch` | >=2.1.0 | PyTorch CPU-only (NLLB inference backend) |
| `numpy` | >=1.26.3 | Numerical arrays (embedding vectors, cosine sim) |

**Models Used**:
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (384-dim, 80MB)
- **Translation**: `facebook/nllb-200-distilled-600M` (600MB)
- **LLM (via Ollama)**: `translategemma:4b` (formatter), `llama3.2:3b` (rewriter)

### Serial / LoRa

| Package | Version | Purpose |
|---------|---------|---------|
| `pyserial` | >=3.5 | Serial port communication (ESP32+LoRa via USB) |

### Encryption

| Package | Version | Purpose |
|---------|---------|---------|
| `cryptography` | >=42.0.0 | AES-256-GCM encryption for hub-to-hub LoRa messages |

### Utilities

| Package | Version | Purpose |
|---------|---------|---------|
| `qrcode` | 7.4.2 | QR code generation (hub connection URL for kiosks) |
| `pillow` | >=10.2.0 | Image processing (QR code rendering) |
| `huggingface_hub` | >=0.21.0 | Model download from Hugging Face Hub |

### Build & Packaging

| Package | Version | Purpose |
|---------|---------|---------|
| `pyinstaller` | 6.3.0 | Bundle hub into ResKiosk-Hub.exe with embedded Python |

---

## Console (React) — package.json

**File**: `console/package.json`  
**Package manager**: npm  
**Node version**: (inferred) 18+

### Production Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `react` | ^18.2.0 | UI library |
| `react-dom` | ^18.2.0 | React DOM renderer |
| `react-router-dom` | ^6.20.0 | Client-side routing (Dashboard, KBViewer, etc.) |
| `axios` | ^1.6.0 | HTTP client for hub API calls |
| `lucide-react` | ^0.300.0 | Icon library (replaces react-icons) |
| `qrcode.react` | ^3.1.0 | QR code component (hub connection display) |

### Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `vite` | ^5.0.0 | Build tool, dev server, HMR |
| `@vitejs/plugin-react` | ^4.2.0 | Vite React plugin (JSX transform, Fast Refresh) |
| `@types/react` | ^18.2.0 | TypeScript type definitions for React |
| `@types/react-dom` | ^18.2.0 | TypeScript type definitions for React DOM |

### Scripts

| Script | Command | Purpose |
|--------|---------|---------|
| `dev` | `vite` | Start Vite dev server at http://localhost:5173 |
| `build` | `vite build` | Production build → `console/dist/` |
| `preview` | `vite preview` | Preview production build locally |

---

## Kiosk (Android) — build.gradle

**File**: `kiosk/app/build.gradle`  
**Gradle version**: (inferred) 8.0+  
**Kotlin version**: 1.8.10 (from kotlinCompilerExtensionVersion 1.4.3)

### Android SDK

| Setting | Value |
|---------|-------|
| `namespace` | `com.reskiosk` |
| `compileSdk` | 34 (Android 14) |
| `minSdk` | 26 (Android 8.0 Oreo) |
| `targetSdk` | 34 (Android 14) |
| `applicationId` | `com.reskiosk` |
| `versionCode` | 1 |
| `versionName` | "1.0" |

### Java/Kotlin

| Setting | Value |
|---------|-------|
| `sourceCompatibility` | JavaVersion.VERSION_1_8 |
| `targetCompatibility` | JavaVersion.VERSION_1_8 |
| `jvmTarget` | '1.8' |

### Compose

| Setting | Value |
|---------|-------|
| `kotlinCompilerExtensionVersion` | '1.4.3' (Kotlin 1.8.10 compatible) |
| `compose-bom` | 2023.06.01 |

### Core Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| `androidx.core:core-ktx` | 1.9.0 | Kotlin extensions for Android |
| `androidx.lifecycle:lifecycle-runtime-ktx` | 2.6.2 | Lifecycle-aware components |
| `androidx.activity:activity-compose` | 1.8.0 | Activity integration with Compose |
| `androidx.compose:compose-bom` | 2023.06.01 | Compose Bill of Materials (version alignment) |
| `androidx.compose.ui:ui` | (from BOM) | Compose UI core |
| `androidx.compose.ui:ui-graphics` | (from BOM) | Graphics primitives |
| `androidx.compose.ui:ui-tooling-preview` | (from BOM) | Compose preview support |
| `androidx.compose.material3:material3` | (from BOM) | Material Design 3 components |
| `androidx.compose.material:material-icons-extended` | (from BOM) | Material icon library (extended set) |

### Navigation

| Dependency | Version | Purpose |
|------------|---------|---------|
| `androidx.navigation:navigation-compose` | 2.7.5 | Compose navigation (screen routing) |

### Networking

| Dependency | Version | Purpose |
|------------|---------|---------|
| `com.squareup.retrofit2:retrofit` | 2.9.0 | HTTP client for hub API |
| `com.squareup.retrofit2:converter-gson` | 2.9.0 | JSON serialization (Gson) |

### Sherpa-ONNX (Local STT/TTS)

| Dependency | Version | Purpose |
|------------|---------|---------|
| `sherpa-onnx` | 1.12.25 (AAR) | Local STT (Zipformer, Whisper) + TTS (VITS) |

**Note**: Sherpa-ONNX is a local AAR file, not fetched from Maven Central. Manually added to `kiosk/app/libs/sherpa-onnx-1.12.25.aar` from GitHub releases.

### Archive Extraction

| Dependency | Version | Purpose |
|------------|---------|---------|
| `org.apache.commons:commons-compress` | 1.26.1 | Extract tar.bz2 model archives from hub |

### ML Kit (Unused in baseline)

| Dependency | Version | Purpose |
|------------|---------|---------|
| `com.google.mlkit:translate` | 17.0.2 | Google ML Kit on-device translation (unused, kept for future) |
| `org.jetbrains.kotlinx:kotlinx-coroutines-play-services` | 1.7.3 | Coroutine support for Google Play Services Tasks |

### QR Code Scanning

| Dependency | Version | Purpose |
|------------|---------|---------|
| `com.journeyapps:zxing-android-embedded` | 4.3.0 | QR code scanner (hub connection setup) |

### Testing

| Dependency | Version | Purpose |
|------------|---------|---------|
| `junit:junit` | 4.13.2 | Unit testing framework |
| `androidx.test.ext:junit` | 1.1.5 | AndroidX JUnit extensions |
| `androidx.test.espresso:espresso-core` | 3.5.1 | UI testing (Espresso) |
| `androidx.compose.ui:ui-test-junit4` | (from BOM) | Compose UI testing |

### Debug Tools

| Dependency | Version | Purpose |
|------------|---------|---------|
| `androidx.compose.ui:ui-tooling` | (from BOM) | Compose tooling (Layout Inspector) |
| `androidx.compose.ui:ui-test-manifest` | (from BOM) | Test manifest for Compose |

---

## Ollama Models (Local LLMs)

**Not in requirements.txt** — managed by Ollama server, preloaded at hub runtime.

| Model | Size | Purpose |
|-------|------|---------|
| `translategemma:4b` | ~2.6GB | Response formatting, tone control |
| `llama3.2:3b` | ~2GB | Query rewriting for noisy STT transcripts |

**Ollama version**: (inferred) 0.1.x+  
**Ollama endpoint**: `http://127.0.0.1:11434/api/chat`

---

## System-Level Dependencies (Inferred)

### Windows 10/11 (Hub)
- **SQLite**: Bundled with Python 3.10+ (no external install)
- **Ollama**: Standalone binary, launched by `hub/launcher.py`
- **VC++ Redistributable**: Required for PyTorch CPU inference (usually pre-installed)

### Android 8.0+ (Kiosk)
- **Sherpa-ONNX models**: Downloaded from hub at first launch
  - Zipformer (EN STT) — ~50MB
  - Whisper (ja/es/de/fr STT) — ~100MB each
  - VITS (en/es/de/fr TTS) — ~30MB each
  - Android System TTS (ja) — OS-provided

---

## Dependency Change Log (Sprint 1–2)

### Added in Sprint 1
- `pyserial` — LoRa serial communication
- `cryptography` — Hub-to-hub encryption
- `qrcode` / `pillow` — Hub connection QR codes

### Added in Sprint 2
- No new Python dependencies
- No new npm dependencies
- No new Android dependencies

### Upgraded in Sprint 2
- `sentence-transformers` — Upgraded from 2.2.x to >=2.6.1 to fix `huggingface_hub.cached_download` deprecation

### Removed in Sprint 2
- None (cloud dependencies still in requirements.txt but unused)

---

## Dependency Security Notes

> 🔍 **Inferred**: As of Sprint 2 completion, no known critical CVEs in dependency tree. However:

- `torch` is CPU-only build to minimize attack surface (no CUDA)
- `cryptography` uses AES-256-GCM (modern AEAD cipher)
- `pyserial` only opens user-configured ports (no auto-scan)
- Android `minSdk 26` ensures no ancient Android vulns (pre-2017)

---

## Related Baseline Documents

- [[00-pre-sprint-baseline/_index]] — System overview
- [[00-pre-sprint-baseline/architecture]] — Folder layout, entry points
- [[00-pre-sprint-baseline/data-models]] — All SQLAlchemy models, Pydantic schemas
- [[00-pre-sprint-baseline/api-surface]] — Complete FastAPI route catalog
