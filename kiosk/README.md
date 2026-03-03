# ResKiosk Android Kiosk

## Hub connection

The Hub is started from **TO RUN** (`start_hub.vbs`) on the laptop. In the app, set **Hub URL** (e.g. `http://<Hub-IP>:8000`) under **Hub Connection**; you can copy the URL from the Hub’s admin console at **http://localhost:8000** → Network Setup.

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

### Japanese TTS
Japanese speech now uses Android System TTS (not a Sherpa model download).
- Install Japanese voice data on the tablet in Android Text-to-Speech settings.
- If Japanese voice data is missing, Japanese text still works but voice output is disabled.

## Permissions
Ensure `AndroidManifest.xml` has:
- `<uses-permission android:name="android.permission.INTERNET" />` (For Hub comms)
- `<uses-permission android:name="android.permission.RECORD_AUDIO" />`
