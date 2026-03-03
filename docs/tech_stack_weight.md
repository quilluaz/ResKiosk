# ResKiosk Tech Stack Weight

Measured on: 2026-03-02 (Asia/Manila)  
Machine: Windows, AMD Ryzen 5 5600H (6C/12T), ~19.86 GiB RAM, AMD Radeon(TM) Graphics

## Storage Footprint

| Component | Path | Size (bytes) | Size (human) |
|---|---|---:|---:|
| Hub models bundle | `packaging/hub_models` | 3,277,714,066 | 3.05 GiB |
| Portable Ollama models cache | `packaging/ollama_portable/models` | 0 | 0 B |
| System Ollama models | `C:\Users\Keith\.ollama\models` | 3,697,851,706 | 3.44 GiB |
| Console build output | `console/dist` | 2,381,307 | 2.27 MiB |
| Main DB | `reskiosk.db` | 598,016 | 0.57 MiB |
| Kiosk static assets folder | `kiosk/app/src/main/assets` | 0 | 0 B |
| Built APK output folder | `kiosk/app/build/outputs/apk` | 0 | 0 B |

## Compute Requirements (Observed Practical Baseline)

- CPU: 6 cores / 12 threads is sufficient for local hub + console + Ollama.
- RAM:
  - System has ~19.86 GiB.
  - Practical minimum for smooth local operation with local LLM: 16 GiB recommended.
- GPU:
  - Current run worked on CPU path (no hard GPU requirement observed).
  - 4 GiB-class adapter present, but pipeline does not require dedicated high-end GPU.
- Disk:
  - Current free space observed: ~21.24 GiB on `C:` during measurement.
  - Recommended free space: 15+ GiB if pulling multiple Ollama models and keeping build artifacts.

## Model Provisioning Notes

- Installed and detected at runtime:
  - `llama3.2:3b`
  - `gemma:2b`
- Not installed at measurement time:
  - `translategemma:4b` (formatter default in split-model config, but missing model falls back to raw formatter output path)

