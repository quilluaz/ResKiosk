package com.reskiosk.tts

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import com.k2fsa.sherpa.onnx.OfflineTts
import com.k2fsa.sherpa.onnx.OfflineTtsConfig
import com.k2fsa.sherpa.onnx.OfflineTtsModelConfig
import com.k2fsa.sherpa.onnx.OfflineTtsVitsModelConfig
import com.reskiosk.ModelConstants
import java.io.File
import java.util.Locale
import java.util.concurrent.ConcurrentLinkedQueue

class SherpaTtsEngine private constructor(
    context: Context,
    private val modelsDir: File,
    private val modelType: ModelType,
    private val modelName: String = "",
    private val langCode: String = "",
    private val preferredSpeakerId: Int = 0,
    private val speed: Float = 0.95f
) {
    private enum class ModelType { VITS, SYSTEM_JA }

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
                    modelsDir = modelsBase,
                    modelType = ModelType.SYSTEM_JA,
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
    }

    private var sherpaTts: OfflineTts? = null
    private var sampleRate = 22050
    private var activeSpeakerId = 0
    private var audioTrack: AudioTrack? = null

    private var systemTts: TextToSpeech? = null
    @Volatile private var systemTtsReady = false
    @Volatile private var systemTtsAvailable = false
    @Volatile private var systemSpeaking = false
    private val pendingSystemUtterances = ConcurrentLinkedQueue<String>()

    @Volatile private var isStopped = false

    init {
        try {
            when (modelType) {
                ModelType.VITS -> initVits()
                ModelType.SYSTEM_JA -> initSystemJapaneseTts(context)
            }
        } catch (e: Exception) {
            Log.e("SherpaTTS", "Failed to init TTS", e)
        }
    }

    private fun initVits() {
        if (!modelsDir.exists()) {
            Log.e("SherpaTTS", "Models not found in filesDir. Setup required: ${modelsDir.absolutePath}")
            return
        }

        Log.i("SherpaTTS", "Loading VITS from FilesDir: $modelsDir")
        val config = buildVitsConfig()
        if (config == null) {
            Log.e("SherpaTTS", "VITS config unavailable; speech will be skipped for this language.")
            return
        }

        sherpaTts = OfflineTts(assetManager = null, config = config)
        sampleRate = sherpaTts?.sampleRate() ?: sampleRate
        val speakerCount = (sherpaTts?.numSpeakers() ?: 1).coerceAtLeast(1)
        activeSpeakerId = preferredSpeakerId.coerceIn(0, speakerCount - 1)
        Log.i("SherpaTTS", "Initialized VITS lang=$langCode speed=$speed speaker=$activeSpeakerId/$speakerCount")

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

    private fun initSystemJapaneseTts(context: Context) {
        Log.i("SherpaTTS", "Initializing Android System TTS for Japanese")
        systemTts = TextToSpeech(context) { status ->
            if (status != TextToSpeech.SUCCESS) {
                Log.e("SherpaTTS", "System JA TTS init failed with status=$status")
                systemTtsAvailable = false
                systemTtsReady = false
                return@TextToSpeech
            }

            val tts = systemTts
            if (tts == null) {
                systemTtsAvailable = false
                systemTtsReady = false
                return@TextToSpeech
            }

            val locale = Locale("ja", "JP")
            val availability = tts.isLanguageAvailable(locale)
            if (availability != TextToSpeech.LANG_AVAILABLE &&
                availability != TextToSpeech.LANG_COUNTRY_AVAILABLE &&
                availability != TextToSpeech.LANG_COUNTRY_VAR_AVAILABLE
            ) {
                Log.e("SherpaTTS", "Japanese system voice not available (availability=$availability)")
                systemTtsAvailable = false
                systemTtsReady = false
                return@TextToSpeech
            }

            tts.language = locale
            tts.setSpeechRate(speed)
            tts.setPitch(1.0f)
            tts.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) {
                    systemSpeaking = true
                }

                override fun onDone(utteranceId: String?) {
                    systemSpeaking = false
                }

                @Deprecated("Deprecated in Java")
                override fun onError(utteranceId: String?) {
                    systemSpeaking = false
                }

                override fun onError(utteranceId: String?, errorCode: Int) {
                    systemSpeaking = false
                }
            })

            systemTtsAvailable = true
            systemTtsReady = true
            Log.i("SherpaTTS", "System JA TTS ready (rate=$speed pitch=1.0)")
            drainPendingSystemUtterances()
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

    fun hasRequiredVoice(): Boolean {
        return when (modelType) {
            ModelType.VITS -> sherpaTts != null
            ModelType.SYSTEM_JA -> systemTtsAvailable
        }
    }

    fun speak(text: String) {
        if (text.isBlank()) return
        isStopped = false
        val normalizedText = normalizeForTts(text)

        when (modelType) {
            ModelType.VITS -> speakWithVits(normalizedText)
            ModelType.SYSTEM_JA -> speakWithSystemJaTts(normalizedText)
        }
    }

    private fun speakWithVits(text: String) {
        if (sherpaTts == null) {
            Log.e("SherpaTTS", "VITS engine not initialized; skipping speech.")
            return
        }

        Log.i("SherpaTTS", "Speaking with VITS (speed=$speed, sid=$activeSpeakerId): $text")

        Thread {
            try {
                var started = false
                sherpaTts?.generateWithCallback(text, sid = activeSpeakerId, speed = speed) { samples ->
                    if (isStopped) {
                        return@generateWithCallback 0
                    }

                    if (!started) {
                        try {
                            audioTrack?.play()
                            started = true
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
                Log.e("SherpaTTS", "Error generating VITS audio", e)
            }
        }.start()
    }

    private fun speakWithSystemJaTts(text: String) {
        if (!systemTtsAvailable) {
            Log.e("SherpaTTS", "Japanese system voice unavailable; skipping speech.")
            return
        }
        if (!systemTtsReady) {
            pendingSystemUtterances.add(text)
            return
        }

        try {
            val id = "reskiosk-ja-${System.currentTimeMillis()}"
            Log.i("SherpaTTS", "Speaking with System JA TTS (rate=$speed): $text")
            systemTts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, id)
        } catch (e: Exception) {
            Log.e("SherpaTTS", "Error speaking with System JA TTS", e)
        }
    }

    private fun drainPendingSystemUtterances() {
        val latest = pendingSystemUtterances.pollLastOrNull() ?: return
        pendingSystemUtterances.clear()
        speakWithSystemJaTts(latest)
    }

    private fun normalizeForTts(text: String): String {
        return text
            .replace("\r\n", "\n")
            .replace("\n", " ")
            .replace(Regex("\\s+"), " ")
            .trim()
            .replace("...", ". ")
            .replace("..", ". ")
    }

    fun isPlaying(): Boolean {
        return when (modelType) {
            ModelType.VITS -> !isStopped && audioTrack?.playState == AudioTrack.PLAYSTATE_PLAYING
            ModelType.SYSTEM_JA -> !isStopped && (systemSpeaking || systemTts?.isSpeaking == true)
        }
    }

    fun stop() {
        isStopped = true
        when (modelType) {
            ModelType.VITS -> {
                try {
                    audioTrack?.pause()
                    audioTrack?.flush()
                } catch (e: Exception) {
                    Log.e("SherpaTTS", "Error stopping VITS playback", e)
                }
            }
            ModelType.SYSTEM_JA -> {
                try {
                    pendingSystemUtterances.clear()
                    systemTts?.stop()
                    systemSpeaking = false
                } catch (e: Exception) {
                    Log.e("SherpaTTS", "Error stopping system JA TTS", e)
                }
            }
        }
    }

    fun release() {
        stop()
        sherpaTts?.release()
        audioTrack?.release()
        systemTts?.shutdown()
        sherpaTts = null
        audioTrack = null
        systemTts = null
        systemTtsReady = false
        systemTtsAvailable = false
        systemSpeaking = false
    }

    private fun <T> ConcurrentLinkedQueue<T>.pollLastOrNull(): T? {
        var last: T? = null
        while (true) {
            val next = this.poll() ?: break
            last = next
        }
        return last
    }
}
