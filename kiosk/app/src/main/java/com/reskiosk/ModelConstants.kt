package com.reskiosk

/**
 * Single source of truth for model directory names and download URLs.
 * Used by SetupScreen (downloads) and MainKioskScreen (existence checks).
 */
object ModelConstants {
    // ── STT Models ──
    // English-primary streaming Zipformer — highest EN accuracy in sherpa-onnx
    const val STT_DIR_EN = "sherpa-onnx-streaming-zipformer-en-2023-06-26"
    const val STT_URL_EN = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-en-2023-06-26.tar.bz2"

    // Japanese Zipformer (ReazonSpeech; same encoder/decoder/joiner layout as streaming)
    const val STT_DIR_JA = "sherpa-onnx-zipformer-ja-reazonspeech-2024-08-01"
    const val STT_URL_JA = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-zipformer-ja-reazonspeech-2024-08-01.tar.bz2"

    // Whisper medium — multilingual (covers Spanish, German, French for batch STT)
    // Archive contains both full and int8 quantized models; we use int8 at runtime
    const val STT_DIR_WHISPER = "sherpa-onnx-whisper-medium"
    const val STT_URL_WHISPER = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-medium.tar.bz2"

    // Legacy alias so SetupScreen references don't break
    const val STT_DIR_BILINGUAL = STT_DIR_EN
    const val STT_URL_BILINGUAL = STT_URL_EN

    // ── TTS Models (5 languages: en, ja, es, de, fr) ──
    const val TTS_DIR_EN = "vits-piper-en_US-lessac-medium"
    const val TTS_URL_EN = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-en_US-lessac-medium.tar.bz2"

    const val TTS_DIR_ES = "vits-piper-es_ES-davefx-medium"
    const val TTS_URL_ES = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-es_ES-davefx-medium.tar.bz2"

    const val TTS_DIR_DE = "vits-piper-de_DE-thorsten-medium"
    const val TTS_URL_DE = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-de_DE-thorsten-medium.tar.bz2"

    const val TTS_DIR_FR = "vits-piper-fr_FR-siwis-medium"
    const val TTS_URL_FR = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-fr_FR-siwis-medium.tar.bz2"

    // Japanese Kokoro (multilingual) voice. Required for native Japanese TTS output.
    const val TTS_DIR_JA = "kokoro-multi-lang-v1_0"
    const val TTS_URL_JA = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_0.tar.bz2"

    // ── Punctuation Models ──
    const val PUNCTUATION_DIR = "sherpa-onnx-punct-ct-transformer-zh-en-vocab272727-2024-04-12"
    const val PUNCTUATION_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/punctuation-models/sherpa-onnx-punct-ct-transformer-zh-en-vocab272727-2024-04-12.tar.bz2"

    // ── Base directory ──
    const val MODELS_BASE_DIR = "sherpa-models"

    /**
     * Returns the STT model directory name for the given language code.
     * English → English Zipformer, Japanese → JA Zipformer, es/de/fr → Whisper medium
     */
    fun sttDirForLanguage(langCode: String): String = when (langCode) {
        "en" -> STT_DIR_EN
        "ja" -> STT_DIR_JA
        else -> STT_DIR_WHISPER  // Whisper covers es, de, fr
    }
}
