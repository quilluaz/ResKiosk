# ResKiosk Android Kiosk

## Documentation

- `docs/kiosk-ui.md` - Kiosk UI behavior (start screen, chat modes, loading overlay, SOS hold-to-confirm).
- `docs/emergency-calls.md` - End-to-end emergency lifecycle across kiosk, hub, and console.
- `docs/intent-classification.md` - Intent and retrieval classification behavior.
- `docs/rlhf.md` - RLHF-style feedback and retrieval-bias behavior.
- `docs/PIPELINE_END_TO_END.md` - Full speech-to-response pipeline.

## Model Configuration

Hub LLM model selection now supports split formatter/rewriter models:

- `RESKIOSK_FORMAT_MODEL` (formatter; default fallback: `translategemma:4b`)
- `RESKIOSK_REWRITE_MODEL` (query rewriter; default fallback: `llama3.2:3b`)

Backward compatibility is preserved:

- If the new vars are unset, both modules fall back to `RESKIOSK_LLM_MODEL`.

## Cloud Integration (Paused)

Cloud integration is currently disabled. The system runs fully offline-first and does not expose cloud endpoints or UI controls. This section is retained for future re-enable work.

## Hub connection

The Hub is started from **TO RUN** (`start_hub.vbs`) on the laptop. In the app, set **Hub URL** under **Hub Connection**; you can copy it from `http://localhost:8000` -> Network Setup.

Hub URL handling in kiosk:
- accepts `host:port` or full URL
- auto-prefixes `http://` when missing
- defaults to port `8000` when omitted
- validates and rejects malformed host entries
- probes `GET /admin/ping`, then falls back to `GET /health`

## Dashboard Emergency Mode

Emergency Mode is controlled from Dashboard (not Shelter Config).

- **Activate** opens a confirmation modal.
- On activation, hub publishes mode state to kiosks via `GET /admin/ping` polling.
- Kiosks show a 5-second emergency overlay, play a one-time local alarm, then keep animated top/bottom emergency banners until deactivated.

## Dependencies
This project requires the following dependencies in `app/build.gradle.kts`:

```kotlin
dependencies {
    // ... standard android deps ...
    
    // Sherpa ONNX (STT/TTS)
    implementation("com.k2fsa.sherpa.onnx:sherpa-onnx:1.10.16") 
    
    // Google ML Kit (Translation)
    implementation("com.google.mlkit:translate:17.0.2")
    
    // Jetpack Compose
    implementation("androidx.activity:activity-compose:1.8.0")
    implementation(platform("androidx.compose:compose-bom:2023.08.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
}
```

## Assets (Manual Download Required)
For offline STT/TTS, you must place model files in `app/src/main/assets/`.

### STT Models (Sherpa)
Download `sherpa-onnx-streaming-zipformer-en-2023-02-21.tar.bz2` (or similar small English model).
Extract inside assets:
- `tokens.txt`
- `encoder-epoch-99-avg-1.onnx`
- `decoder-epoch-99-avg-1.onnx`
- `joiner-epoch-99-avg-1.onnx`

### TTS Models (Sherpa)
Download `vits-piper-en_US-amy-low.tar.bz2`.
Extract inside assets:
- `en_US-amy-low.onnx`
- `en_US-amy-low.onnx.json`
- `tokens.txt`

## Permissions
Ensure `AndroidManifest.xml` has:
- `<uses-permission android:name="android.permission.INTERNET" />` (For Hub comms)
- `<uses-permission android:name="android.permission.RECORD_AUDIO" />`

