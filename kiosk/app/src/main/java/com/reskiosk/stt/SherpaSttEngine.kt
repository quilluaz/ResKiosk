package com.reskiosk.stt

import android.content.Context
import android.util.Log
import com.k2fsa.sherpa.onnx.EndpointConfig
import com.k2fsa.sherpa.onnx.EndpointRule
import com.k2fsa.sherpa.onnx.OnlineModelConfig
import com.k2fsa.sherpa.onnx.OnlineRecognizer
import com.k2fsa.sherpa.onnx.OnlineRecognizerConfig
import com.k2fsa.sherpa.onnx.OnlineStream
import com.k2fsa.sherpa.onnx.OnlineTransducerModelConfig
import com.k2fsa.sherpa.onnx.OfflineModelConfig
import com.k2fsa.sherpa.onnx.OfflineRecognizer
import com.k2fsa.sherpa.onnx.OfflineRecognizerConfig
import com.k2fsa.sherpa.onnx.OfflineWhisperModelConfig
import com.reskiosk.ModelConstants
import java.io.File

enum class ModelType { ZIPFORMER, WHISPER }

class SherpaSttEngine private constructor(
    private val modelType: ModelType,
    private val onlineRecognizer: OnlineRecognizer?,
    private val offlineRecognizer: OfflineRecognizer?,
    private val hotwords: String = ""
) {
    companion object {
        private const val TAG = "SherpaSTT"

        /**
         * Build the correct STT engine for the given language.
         * - English → English-primary streaming Zipformer
         * - Japanese → Japanese-specific streaming Zipformer
         * - Spanish/German/French → Whisper medium int8 (OfflineRecognizer)
         */
        fun forLanguage(context: Context, langCode: String): SherpaSttEngine {
            val modelsBase = File(context.filesDir, ModelConstants.MODELS_BASE_DIR)
            return when (langCode) {
                "en" -> buildZipformer(modelsBase, ModelConstants.STT_DIR_EN, useBpe = true, preferInt8 = true)
                // Japanese Zipformer package has shown native incompatibilities on some devices.
                // Use Whisper multilingual for stability.
                "ja" -> buildWhisper(modelsBase, "ja")
                else -> buildWhisper(modelsBase, langCode)
            }
        }

        /**
         * Builds a streaming Zipformer recognizer.
         * @param useBpe true for English (BPE tokenization), false for Japanese (char-based)
         */
        private fun buildZipformer(
            modelsBase: File,
            modelDirName: String,
            useBpe: Boolean,
            preferInt8: Boolean,
        ): SherpaSttEngine {
            val modelsDir = File(modelsBase, modelDirName)
            Log.i(TAG, "Contents of $modelsDir: ${modelsDir.listFiles()?.joinToString { it.name }}")
            return try {
                if (!modelsDir.exists()) {
                    Log.e(TAG, "Zipformer models not found at: $modelsDir")
                    return SherpaSttEngine(ModelType.ZIPFORMER, null, null, "")
                }

                val encoderCandidates = if (preferInt8) {
                    listOf(
                        "encoder-epoch-99-avg-1-chunk-16-left-128.int8.onnx",
                        "encoder-epoch-99-avg-1.int8.onnx",
                        "encoder-epoch-99-avg-1-chunk-16-left-128.onnx",
                        "encoder-epoch-99-avg-1.onnx",
                        "encoder.onnx"
                    )
                } else {
                    listOf(
                        "encoder-epoch-99-avg-1-chunk-16-left-128.onnx",
                        "encoder-epoch-99-avg-1.onnx",
                        "encoder.onnx",
                        "encoder-epoch-99-avg-1-chunk-16-left-128.int8.onnx",
                        "encoder-epoch-99-avg-1.int8.onnx"
                    )
                }
                val encoderFile = encoderCandidates.map { File(modelsDir, it) }.firstOrNull { it.exists() }

                val decoderFile = listOf(
                    "decoder-epoch-99-avg-1-chunk-16-left-128.onnx",
                    "decoder-epoch-99-avg-1.onnx",
                    "decoder.onnx"
                ).map { File(modelsDir, it) }.firstOrNull { it.exists() }

                val joinerCandidates = if (preferInt8) {
                    listOf(
                        "joiner-epoch-99-avg-1-chunk-16-left-128.int8.onnx",
                        "joiner-epoch-99-avg-1.int8.onnx",
                        "joiner-epoch-99-avg-1-chunk-16-left-128.onnx",
                        "joiner-epoch-99-avg-1.onnx",
                        "joiner.onnx"
                    )
                } else {
                    listOf(
                        "joiner-epoch-99-avg-1-chunk-16-left-128.onnx",
                        "joiner-epoch-99-avg-1.onnx",
                        "joiner.onnx",
                        "joiner-epoch-99-avg-1-chunk-16-left-128.int8.onnx",
                        "joiner-epoch-99-avg-1.int8.onnx"
                    )
                }
                val joinerFile = joinerCandidates.map { File(modelsDir, it) }.firstOrNull { it.exists() }

                if (encoderFile == null || decoderFile == null || joinerFile == null) {
                    Log.e(TAG, "Zipformer onnx files not found in $modelsDir")
                    return SherpaSttEngine(ModelType.ZIPFORMER, null, null, "")
                }

                val transducerConfig = OnlineTransducerModelConfig(
                    encoder = encoderFile.absolutePath,
                    decoder = decoderFile.absolutePath,
                    joiner = joinerFile.absolutePath,
                )

                // BPE vocab only for English model; Japanese uses char-based tokenization
                val bpeFile = if (useBpe) File(modelsDir, "bpe.model") else null

                val modelConfig = OnlineModelConfig(
                    transducer = transducerConfig,
                    tokens = File(modelsDir, "tokens.txt").absolutePath,
                    numThreads = 4,        // optimal for mid-range phones (6-8 cores)
                    debug = false,
                    modelingUnit = if (useBpe) "bpe" else "cjkchar",
                    bpeVocab = bpeFile?.absolutePath ?: "",
                )

                val endpointConfig = EndpointConfig(
                    rule1 = EndpointRule(mustContainNonSilence = false, minTrailingSilence = 2.4f, minUtteranceLength = 0.0f),
                    rule2 = EndpointRule(mustContainNonSilence = true, minTrailingSilence = 1.2f, minUtteranceLength = 0.0f),
                    rule3 = EndpointRule(mustContainNonSilence = false, minTrailingSilence = 0.0f, minUtteranceLength = 300.0f),
                )

                // TODO: Wire up hotwordsFile/hotwordsScore once the sherpa-onnx Android AAR
                // exposes them cleanly for OnlineRecognizerConfig. Beam search is disabled
                // here on Android due to a native crash in OnlineRecognizer_newFromFile.
                val config = OnlineRecognizerConfig(
                    modelConfig = modelConfig,
                    decodingMethod = "greedy_search",
                    enableEndpoint = false,     // PTT controls endpoint, not VAD
                    endpointConfig = endpointConfig,
                )

                Log.i(
                    TAG,
                    "Initializing OnlineRecognizer with Zipformer ($modelDirName), preferInt8=$preferInt8, " +
                        "encoder=${encoderFile.name}, decoder=${decoderFile.name}, joiner=${joinerFile.name}"
                )
                val recognizer = OnlineRecognizer(assetManager = null, config = config)
                Log.i(TAG, "Zipformer loaded successfully from $modelsDir")

                val hwString = "" // hotwords not supported via AAR currently

                SherpaSttEngine(ModelType.ZIPFORMER, recognizer, null, hwString)
            } catch (e: Exception) {
                Log.e(TAG, "Failed to init Zipformer STT", e)
                SherpaSttEngine(ModelType.ZIPFORMER, null, null, "")
            }
        }

        private fun buildWhisper(modelsBase: File, langCode: String): SherpaSttEngine {
            val modelsDir = File(modelsBase, ModelConstants.STT_DIR_WHISPER)
            return try {
                if (!modelsDir.exists()) {
                    Log.e(TAG, "Whisper models not found at: $modelsDir")
                    return SherpaSttEngine(ModelType.WHISPER, null, null)
                }

                // Prefer int8 (quantized) if available, check both medium and small prefixes
                val encoderFile = listOf(
                    "medium-encoder.int8.onnx", "medium-encoder.onnx",
                    "small-encoder.int8.onnx", "small-encoder.onnx",
                    "encoder.int8.onnx", "encoder.onnx"
                ).map { File(modelsDir, it) }.firstOrNull { it.exists() }

                val decoderFile = listOf(
                    "medium-decoder.int8.onnx", "medium-decoder.onnx",
                    "small-decoder.int8.onnx", "small-decoder.onnx",
                    "decoder.int8.onnx", "decoder.onnx"
                ).map { File(modelsDir, it) }.firstOrNull { it.exists() }

                if (encoderFile == null || decoderFile == null) {
                    Log.e(TAG, "Whisper encoder/decoder not found in $modelsDir")
                    return SherpaSttEngine(ModelType.WHISPER, null, null)
                }

                Log.i(TAG, "Using Whisper encoder: ${encoderFile.name}, decoder: ${decoderFile.name}")

                val whisperConfig = OfflineWhisperModelConfig(
                    encoder = encoderFile.absolutePath,
                    decoder = decoderFile.absolutePath,
                    language = whisperLangCode(langCode),
                    task = "transcribe",   // always transcribe, never translate — NLLB handles translation
                )

                val tokensFile = listOf("medium-tokens.txt", "small-tokens.txt", "tokens.txt")
                    .map { File(modelsDir, it) }.firstOrNull { it.exists() }

                val modelConfig = OfflineModelConfig(
                    whisper = whisperConfig,
                    tokens = tokensFile?.absolutePath ?: File(modelsDir, "tokens.txt").absolutePath,
                    numThreads = 4,
                    debug = false,
                    provider = "cpu",
                )

                val config = OfflineRecognizerConfig(
                    modelConfig = modelConfig,
                    decodingMethod = "greedy_search",  // only option supported by sherpa-onnx Whisper
                )
                val recognizer = OfflineRecognizer(assetManager = null, config = config)
                Log.i(TAG, "Whisper ($langCode) loaded from $modelsDir")
                SherpaSttEngine(ModelType.WHISPER, null, recognizer)
            } catch (e: Exception) {
                Log.e(TAG, "Failed to init Whisper STT", e)
                SherpaSttEngine(ModelType.WHISPER, null, null)
            }
        }

        private fun whisperLangCode(appLangCode: String): String = when (appLangCode) {
            "es" -> "es"      // Spanish
            "de" -> "de"      // German
            "fr" -> "fr"      // French
            "ja" -> "ja"      // Japanese
            else -> "en"
        }
    }

    /**
     * Transcribes a complete audio buffer (push-to-talk style).
     * Routes to the correct recognizer based on model type.
     */
    fun transcribeBuffer(samples: FloatArray): String {
        Log.i(TAG, "transcribeBuffer: ${samples.size} samples (${samples.size / 16000f}s)")
        return when (modelType) {
            ModelType.ZIPFORMER -> transcribeZipformer(samples)
            ModelType.WHISPER -> transcribeWhisper(samples)
        }
    }

    private fun transcribeZipformer(samples: FloatArray): String {
        val rec = onlineRecognizer ?: run {
            Log.e(TAG, "OnlineRecognizer is null – Zipformer model not loaded")
            return ""
        }
        val stream: OnlineStream = rec.createStream(hotwords) ?: return ""
        return try {
            // 0.2s chunks — more frequent partial results, more responsive live transcript
            val chunkSize = 3200
            var offset = 0
            while (offset < samples.size) {
                val end = minOf(offset + chunkSize, samples.size)
                val chunk = samples.copyOfRange(offset, end)
                stream.acceptWaveform(chunk, sampleRate = 16000)
                while (rec.isReady(stream)) {
                    rec.decode(stream)
                }
                offset = end
            }
            // Tail padding: 1.0s of silence so the model flushes all buffered audio
            // Do not reduce — the final word is frequently dropped without this
            val tailPadding = FloatArray(16000)
            stream.acceptWaveform(tailPadding, sampleRate = 16000)
            while (rec.isReady(stream)) {
                rec.decode(stream)
            }
            val result = rec.getResult(stream).text.trim()
            Log.i(TAG, "Zipformer transcript: '$result'")
            result
        } finally {
            stream.release()
        }
    }

    /**
     * Transcribes audio using Whisper. Handles long utterances (>28s) by chunking
     * with 2s overlap to preserve context across Whisper's 30s window limitation.
     */
    private fun transcribeWhisper(samples: FloatArray): String {
        val rec = offlineRecognizer ?: run {
            Log.e(TAG, "OfflineRecognizer is null – Whisper model not loaded")
            return ""
        }
        return try {
            // Under 28 seconds — process as single chunk (well within Whisper's 30s window)
            if (samples.size <= 16000 * 28) {
                val stream = rec.createStream()
                stream.acceptWaveform(samples, sampleRate = 16000)
                rec.decode(stream)
                val result = rec.getResult(stream).text.trim()
                Log.i(TAG, "Whisper transcript: '$result'")
                return result
            }

            // Over 28 seconds — chunk with 2-second overlap to preserve context
            Log.i(TAG, "Whisper long utterance: ${samples.size / 16000f}s — chunking")
            val chunkSamples = 16000 * 28       // 28 seconds per chunk
            val overlapSamples = 16000 * 2      // 2 second overlap
            val results = mutableListOf<String>()
            var start = 0

            while (start < samples.size) {
                val end = minOf(start + chunkSamples, samples.size)
                val chunk = samples.copyOfRange(start, end)
                val stream = rec.createStream()
                stream.acceptWaveform(chunk, sampleRate = 16000)
                rec.decode(stream)
                val chunkResult = rec.getResult(stream).text.trim()
                if (chunkResult.isNotBlank()) {
                    results.add(chunkResult)
                }
                start += chunkSamples - overlapSamples
            }

            val joined = joinChunks(results)
            Log.i(TAG, "Whisper chunked transcript: '$joined'")
            joined
        } catch (e: Exception) {
            Log.e(TAG, "Whisper transcription error", e)
            ""
        }
    }

    /**
     * Joins chunked transcription results, deduplicating the overlap region
     * using a simple longest-suffix-prefix match.
     */
    private fun joinChunks(parts: List<String>): String {
        if (parts.isEmpty()) return ""
        if (parts.size == 1) return parts[0]
        val sb = StringBuilder(parts[0])
        for (i in 1 until parts.size) {
            val prev = parts[i - 1].takeLast(40)
            val curr = parts[i]
            val overlap = longestSuffixPrefix(prev, curr)
            sb.append(" ").append(curr.removePrefix(overlap).trim())
        }
        return sb.toString().trim()
    }

    private fun longestSuffixPrefix(a: String, b: String): String {
        val maxLen = minOf(a.length, b.length)
        for (len in maxLen downTo 1) {
            val suffix = a.takeLast(len)
            if (b.startsWith(suffix)) return suffix
        }
        return ""
    }

    // ─── Live Streaming API ───

    private var activeStream: Any? = null

    @Synchronized
    fun beginStream() {
        activeStream = when (modelType) {
            ModelType.ZIPFORMER -> {
                if (onlineRecognizer == null) Log.e(TAG, "Cannot beginStream: OnlineRecognizer is null")
                onlineRecognizer?.createStream(hotwords)
            }
            ModelType.WHISPER -> {
                if (offlineRecognizer == null) Log.e(TAG, "Cannot beginStream: OfflineRecognizer is null")
                offlineRecognizer?.createStream()
            }
        }
    }


    @Synchronized
    fun feedAndDecodeStream(chunk: FloatArray): String {
        return when (modelType) {
            ModelType.ZIPFORMER -> {
                val stream = activeStream as? OnlineStream ?: return ""
                val rec = onlineRecognizer ?: return ""
                stream.acceptWaveform(chunk, sampleRate = 16000)
                while (rec.isReady(stream)) {
                    rec.decode(stream)
                }
                rec.getResult(stream).text.trim()
            }
            ModelType.WHISPER -> {
                val stream = activeStream as? com.k2fsa.sherpa.onnx.OfflineStream ?: return ""
                stream.acceptWaveform(chunk, sampleRate = 16000)
                // Whisper is batch-only — decode happens once in finishStream(), not per-chunk.
                // Decoding here would block the audio read loop for seconds and cause buffer overflow.
                ""
            }
        }
    }

    @Synchronized
    fun finishStream(): String {
        return when (modelType) {
            ModelType.ZIPFORMER -> {
                val stream = activeStream as? OnlineStream ?: return ""
                val rec = onlineRecognizer ?: return ""
                // Tail padding — 1.0s silence to flush model state
                val tailPadding = FloatArray(16000)
                stream.acceptWaveform(tailPadding, sampleRate = 16000)
                while (rec.isReady(stream)) {
                    rec.decode(stream)
                }
                val result = rec.getResult(stream).text.trim()
                activeStream = null
                stream.release()
                result
            }
            ModelType.WHISPER -> {
                val stream = activeStream as? com.k2fsa.sherpa.onnx.OfflineStream ?: return ""
                val rec = offlineRecognizer ?: return ""
                rec.decode(stream)
                val result = rec.getResult(stream).text.trim()
                activeStream = null
                stream.release()
                result
            }
        }
    }

    @Synchronized
    fun release() {
        onlineRecognizer?.release()
        offlineRecognizer?.release()
    }
}
