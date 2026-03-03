package com.reskiosk.tts

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.util.Log
import com.k2fsa.sherpa.onnx.OfflineTts
import com.k2fsa.sherpa.onnx.OfflineTtsConfig
import com.k2fsa.sherpa.onnx.OfflineTtsKokoroModelConfig
import com.k2fsa.sherpa.onnx.OfflineTtsModelConfig
import com.k2fsa.sherpa.onnx.OfflineTtsVitsModelConfig
import com.reskiosk.ModelConstants
import java.io.File

class SherpaTtsEngine private constructor(
    context: Context,
    private val modelsDir: File,
    private val modelType: ModelType,
    private val modelName: String = "",
    private val langCode: String = "",
    private val speed: Float = 0.95f
) {
    private enum class ModelType { VITS, KOKORO }

    companion object {
        fun forLanguage(context: Context, langCode: String): SherpaTtsEngine {
            val modelsBase = File(context.filesDir, ModelConstants.MODELS_BASE_DIR)
            return when (langCode) {
                "en" -> SherpaTtsEngine(
                    context = context,
                    modelsDir = File(modelsBase, ModelConstants.TTS_DIR_EN),
                    modelType = ModelType.VITS,
                    modelName = onnxNameFromDir(ModelConstants.TTS_DIR_EN),
                    speed = 0.95f
                )
                "es" -> SherpaTtsEngine(
                    context = context,
                    modelsDir = File(modelsBase, ModelConstants.TTS_DIR_ES),
                    modelType = ModelType.VITS,
                    modelName = onnxNameFromDir(ModelConstants.TTS_DIR_ES),
                    speed = 0.92f
                )
                "de" -> SherpaTtsEngine(
                    context = context,
                    modelsDir = File(modelsBase, ModelConstants.TTS_DIR_DE),
                    modelType = ModelType.VITS,
                    modelName = onnxNameFromDir(ModelConstants.TTS_DIR_DE),
                    speed = 0.95f
                )
                "fr" -> SherpaTtsEngine(
                    context = context,
                    modelsDir = File(modelsBase, ModelConstants.TTS_DIR_FR),
                    modelType = ModelType.VITS,
                    modelName = onnxNameFromDir(ModelConstants.TTS_DIR_FR),
                    speed = 0.95f
                )
                "ja" -> SherpaTtsEngine(
                    context = context,
                    modelsDir = File(modelsBase, ModelConstants.TTS_DIR_JA),
                    modelType = ModelType.KOKORO,
                    langCode = "ja",
                    speed = 1.0f
                )
                else -> SherpaTtsEngine(
                    context = context,
                    modelsDir = File(modelsBase, ModelConstants.TTS_DIR_EN),
                    modelType = ModelType.VITS,
                    modelName = onnxNameFromDir(ModelConstants.TTS_DIR_EN),
                    speed = 0.95f
                )
            }
        }

        private fun onnxNameFromDir(dirName: String): String {
            val prefix = dirName.removePrefix("vits-piper-")
            return "$prefix.onnx"
        }

        private fun findFirstExisting(baseDir: File, fileNames: List<String>): File? {
            for (name in fileNames) {
                val candidate = File(baseDir, name)
                if (candidate.exists()) {
                    return candidate
                }
            }
            return null
        }
    }

    private var tts: OfflineTts? = null
    private var sampleRate = 22050
    private var audioTrack: AudioTrack? = null
    @Volatile private var isStopped = false

    init {
        try {
            if (!modelsDir.exists()) {
                Log.e("SherpaTTS", "Models not found in filesDir. Setup Required: ${modelsDir.absolutePath}")
            } else {
                Log.i("SherpaTTS", "Loading from FilesDir: $modelsDir")
                val config = when (modelType) {
                    ModelType.VITS -> buildVitsConfig()
                    ModelType.KOKORO -> buildKokoroConfig()
                }

                if (config == null) {
                    Log.e("SherpaTTS", "TTS config unavailable; speech will be skipped for this language.")
                } else {
                    tts = OfflineTts(assetManager = null, config = config)
                    sampleRate = tts?.sampleRate() ?: sampleRate

                    // 2-second AudioTrack buffer for smooth streaming playback
                    audioTrack = AudioTrack.Builder()
                        .setAudioAttributes(
                            AudioAttributes.Builder()
                                .setUsage(AudioAttributes.USAGE_MEDIA)
                                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                                .build()
                        )
                        .setAudioFormat(
                            AudioFormat.Builder()
                                .setEncoding(AudioFormat.ENCODING_PCM_FLOAT)
                                .setSampleRate(sampleRate)
                                .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                                .build()
                        )
                        .setBufferSizeInBytes(sampleRate * 4 * 2)
                        .setTransferMode(AudioTrack.MODE_STREAM)
                        .build()
                }
            }
        } catch (e: Exception) {
            Log.e("SherpaTTS", "Failed to init TTS", e)
        }
    }

    private fun buildVitsConfig(): OfflineTtsConfig? {
        val modelPath = File(modelsDir, modelName)
        val tokensPath = File(modelsDir, "tokens.txt")
        val dataPath = File(modelsDir, "espeak-ng-data")

        if (!modelPath.exists() || !tokensPath.exists()) {
            Log.e("SherpaTTS", "VITS model is missing/corrupt in ${modelsDir.absolutePath}")
            return null
        }

        return OfflineTtsConfig(
            model = OfflineTtsModelConfig(
                vits = OfflineTtsVitsModelConfig(
                    model = modelPath.absolutePath,
                    tokens = tokensPath.absolutePath,
                    dataDir = dataPath.absolutePath,
                ),
                numThreads = 2,
                debug = false,
                provider = "cpu",
            ),
            maxNumSentences = 1
        )
    }

    private fun buildKokoroConfig(): OfflineTtsConfig? {
        val modelPath = findFirstExisting(modelsDir, listOf("model.onnx", "kokoro.onnx"))
        val voicesPath = findFirstExisting(modelsDir, listOf("voices.bin", "voices.binfp16", "voices.binfp32"))
        val tokensPath = findFirstExisting(modelsDir, listOf("tokens.txt"))
        val dataPath = File(modelsDir, "espeak-ng-data")
        val lexiconPath = findFirstExisting(modelsDir, listOf("lexicon.txt", "lexicon-us-en.txt"))
        val dictDir = File(modelsDir, "dict")

        if (modelPath == null || voicesPath == null || tokensPath == null) {
            Log.e("SherpaTTS", "Kokoro model is missing/corrupt in ${modelsDir.absolutePath}")
            return null
        }

        return OfflineTtsConfig(
            model = OfflineTtsModelConfig(
                kokoro = OfflineTtsKokoroModelConfig(
                    model = modelPath.absolutePath,
                    voices = voicesPath.absolutePath,
                    tokens = tokensPath.absolutePath,
                    dataDir = if (dataPath.exists()) dataPath.absolutePath else "",
                    lexicon = lexiconPath?.absolutePath ?: "",
                    lang = langCode,
                    dictDir = if (dictDir.exists()) dictDir.absolutePath else "",
                    lengthScale = 1.0f,
                ),
                numThreads = 2,
                debug = false,
                provider = "cpu",
            ),
            maxNumSentences = 1
        )
    }

    /**
     * Streams TTS output and starts playback immediately.
     */
    fun speak(text: String) {
        if (text.isEmpty()) return
        if (tts == null) {
            Log.e("SherpaTTS", "TTS engine not initialized; skipping speech.")
            return
        }

        isStopped = false
        Log.i("SherpaTTS", "Speaking (speed=${speed}): $text")

        Thread {
            try {
                var isStarted = false
                tts?.generateWithCallback(text, sid = 0, speed = speed) { samples ->
                    if (isStopped) {
                        return@generateWithCallback 0
                    }

                    if (!isStarted) {
                        try {
                            audioTrack?.play()
                            isStarted = true
                        } catch (e: Exception) {
                            Log.e("SherpaTTS", "Error starting AudioTrack", e)
                        }
                    }

                    if (samples.isNotEmpty()) {
                        audioTrack?.write(samples, 0, samples.size, AudioTrack.WRITE_BLOCKING)
                    }

                    1
                }
            } catch (e: Exception) {
                Log.e("SherpaTTS", "Error generating audio", e)
            }
        }.start()
    }

    fun isPlaying(): Boolean {
        return !isStopped && audioTrack?.playState == AudioTrack.PLAYSTATE_PLAYING
    }

    fun stop() {
        isStopped = true
        try {
            audioTrack?.pause()
            audioTrack?.flush()
        } catch (e: Exception) {
            Log.e("SherpaTTS", "Error stopping playback", e)
        }
    }

    fun release() {
        stop()
        tts?.release()
        audioTrack?.release()
        tts = null
        audioTrack = null
    }
}
