# ResKiosk - TO RUN

**Prerequisites:** Python 3.10+, Node.js (for building the admin console). Run the scripts in order below.

This folder contains the **one-click scripts** to set up and run the ResKiosk Hub and to open the Android Kiosk project. There is no separate `build_hub.bat` — **01_install_deps.bat** does the environment and console build; **start_hub.vbs** (or double‑click **start_hub**) starts the Hub.

**Manual equivalent (no scripts)** — run from project root (the folder that contains `hub/`, `console/`, `kiosk/`, `TO RUN/`):
```bash
# Same as 01_install_deps.bat (venv + deps + console build)
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cd console && npm install && npm run build && cd ..

# Same as 02_download_models.bat (run first time for models)
python packaging\bundle_models.py

# Same as start_hub.vbs (run the Hub)
python -m hub.launcher
# Or: uvicorn hub.main:app --host 0.0.0.0 --port 8000
```

Run the scripts **in order**:

1. `01_install_deps.bat`
   - Creates/updates the Python virtual environment (`venv/`)
   - Installs Python dependencies from `requirements.txt`
   - Installs Node.js dependencies for the admin console in `console/` (if Node.js is installed)
   - Builds the admin console (`npm run build`) so the Hub can serve it from `console/dist/`
   - The console includes: Dashboard (with Hub ID), KB Viewer, Shelter Config (with Inventory table), Network Setup (connected kiosks + kiosk name), **Emergency Calls**, and Logs.

2. `02_download_models.bat`
   - Activates the Python virtual environment
   - Runs `packaging/bundle_models.py`, which:
     - Downloads the sentence embedding model (MiniLM-L6-v2)
     - Downloads the NLLB-200 translation model
      - Sets up Ollama and pulls both hub LLMs:
        - Formatter: `translategemma:4b`
        - Rewriter: `llama3.2:3b`
   - All **model configuration (which models to use)** lives in:
     - `packaging/bundle_models.py`
   - The actual model weights are **not** tracked in git. They are downloaded locally into:
     - `packaging/hub_models/`
     - `packaging/ollama_portable/`

3. `start_hub.vbs` (or double‑click **start_hub**)
   - Starts the Hub in the background (Ollama + FastAPI on port 8000). No console window; output goes to `hub.log` in the project root.
   - Open **http://localhost:8000** in your browser to use the admin console. Use "Turn Off ResKiosk" in the console to stop the hub.
   - On **first run**, the Hub creates the SQLite database and tables (including `hub_identity`, `emergency_alerts`, `kiosk_registry`) and generates a persistent **Hub ID** (shown on the Dashboard).
   - Ensure Windows Firewall allows port 8000 if kiosks on other devices need to connect (add rule manually or run netsh as Administrator if needed).

4. `04_android_kiosk.bat`
   - Opens the **Android Kiosk** project folder (`kiosk/`) so you can open it in Android Studio.
   - Optionally launches Android Studio with the project if it is installed in a standard location.
  - Before running the app: place STT/TTS model files in `kiosk/app/src/main/assets/` (see `kiosk/README.md`). For Japanese speech output, ensure Android Japanese Text-to-Speech voice data is installed on the device. In the app, set **Hub URL** (e.g. `http://<your-PC-IP>:8000`) via the Hub Connection screen so the kiosk can register and use Emergency and queries.

## Features available after setup

- **Dashboard**: Hub ID, KB version, emergency mode toggle.
- **Emergency Calls**: Active emergency alerts from kiosks (with kiosk name/location), Mark Resolved; connected kiosks table with **editable kiosk name** (click to edit). Real-time alerts via SSE.
- **Shelter Config**: Structured **Inventory** table (water, food, blankets, etc.: status, quantity, location, notes) plus other config keys. Publish All saves inventory and invalidates caches.
- **Network Setup**: Hub URL, QR code, connected kiosks (with kiosk name). Kiosks register via heartbeat and get a persistent ID.

## Model Configuration Auto-Update

When model configurations change (for example, switching the LLM or translation model), only the **source files** are edited:

- Hub Ollama model names: `OLLAMA_FORMAT_MODEL` and `OLLAMA_REWRITE_MODEL` in `packaging/bundle_models.py`
- Runtime env vars (with backward compatibility fallback):
  - `RESKIOSK_FORMAT_MODEL`
  - `RESKIOSK_REWRITE_MODEL`
  - fallback: `RESKIOSK_LLM_MODEL`
- Embedder model path: `get_models_path()` / `SecureEmbedder` in `hub/retrieval/embedder.py`
- Android STT/TTS URLs: constants in `kiosk/app/src/main/java/com/reskiosk/ModelConstants.kt`

After you `git pull`, simply re-run:

1. `01_install_deps.bat` (if dependencies changed), then
2. `02_download_models.bat`

The scripts use the **updated configuration** from those source files and will automatically download or update the correct models on your machine.

## Cloud Language Services (Paused)

Cloud integration is currently disabled. The system runs fully offline-first and does not expose cloud endpoints or UI controls.

