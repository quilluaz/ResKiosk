package com.reskiosk.viewmodel

import android.app.Application
import android.media.MediaPlayer
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.reskiosk.audio.AudioRecorder
import com.reskiosk.emergency.EmergencyDetector
import com.reskiosk.emergency.EmergencyStrings
import com.reskiosk.network.HubApiClient
import com.reskiosk.network.PingResponse
import com.reskiosk.R
import com.reskiosk.stt.SherpaSttEngine
import com.reskiosk.stt.analyzeIntonation
import com.reskiosk.tts.SherpaTtsEngine
import com.k2fsa.sherpa.onnx.OfflinePunctuation
import com.k2fsa.sherpa.onnx.OfflinePunctuationConfig
import com.k2fsa.sherpa.onnx.OfflinePunctuationModelConfig
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlin.math.sqrt
import java.io.File
import java.util.Collections
import java.util.UUID
import java.net.URI

// States
sealed class KioskState {
    object Idle : KioskState()
    /** Brief state after tap-to-speak until mic is actually capturing (min delay so user doesn't speak too early). */
    object PreparingToListen : KioskState()
    object Listening : KioskState()
    object Transcribing : KioskState()
    object Processing : KioskState()
    data class Speaking(val text: String) : KioskState()
    data class Clarification(val question: String, val options: List<String>) : KioskState()
    data class Error(val message: String) : KioskState()
    object TerminatingSession : KioskState()
    data class EmergencyConfirmation(val transcript: String, val remainingSeconds: Int) : KioskState()
    data class EmergencyCancelWindow(val transcript: String, val remainingSeconds: Int) : KioskState()
    object EmergencyPending : KioskState()
    object EmergencyActive : KioskState()
    object EmergencyAcknowledged : KioskState()
    object EmergencyResponding : KioskState()
    object EmergencyResolved : KioskState()
    data class EmergencyFailed(val retryCount: Int) : KioskState()
    object EmergencyCancelled : KioskState()
}

enum class ChatMode {
    VOICE_ONLY,
    TEXT_ONLY
}

private data class PendingFollowUp(
    val intent: String,
    val prompt: String? = null,
    val baseQueryEnglish: String,
    val baseQueryOriginal: String,
    val primarySourceId: Int? = null,
)

// Data class for Chat Frame
data class ChatMessage(
    val isUser: Boolean,
    val text: String,
    val id: String = "",
    /** Non-null for assistant messages that came from a KB article and can be rated. */
    val queryLogId: Int? = null,
    val sourceId: Int? = null,
    /** null = not yet rated, true = liked, false = disliked */
    val feedbackGiven: Boolean? = null,
    /** Original English query text that produced this response (for correct dislike-retry). */
    val queryTextEnglish: String? = null,
    /** Original transcript that produced this response. */
    val queryTextOriginal: String? = null,
    /** Accumulated exclude_source_ids at the time this response was generated. */
    val excludeSourceIds: List<Int>? = null,
)

// Extension to convert ALL-CAPS STT output to proper sentence case
private fun String.toSentenceCase(): String {
    if (isBlank()) return this
    return lowercase().replaceFirstChar { it.uppercase() }
}

/** Batch (Whisper) languages: no live transcript; use "Listening..." placeholder and min-length guard. */
private fun isBatchLanguage(lang: String): Boolean = lang in listOf("es", "de", "fr")

/** Whisper internal silence markers only (no real words like sonido/sound/noise/ruido). */
private fun isSilenceOnly(transcript: String): Boolean {
    if (transcript.isBlank()) return true
    val normalized = transcript
        .replace(Regex("[\\[\\]\\(\\)]"), "")
        .lowercase()
        .trim()
    if (normalized.isEmpty()) return true
    val silenceTokens = setOf(
        "sil", "silence", "audio en blanco", "silencio", "blank audio", "audio silencioso"
    )
    return normalized in silenceTokens
}


class KioskViewModel(application: Application) : AndroidViewModel(application) {

    private val _uiState = MutableStateFlow<KioskState>(KioskState.Idle)
    val uiState = _uiState.asStateFlow()

    // Preferences
    private val prefs = application.getSharedPreferences("reskiosk_prefs", android.content.Context.MODE_PRIVATE)

    // Heartbeat & Connection
    private var heartbeatJob: Job? = null
    private var failedPings = 0
    private var lastSttMode: String = "local"
    private var lastTtsMode: String = "local"
    private var pendingFollowUp: PendingFollowUp? = null
    private val _hubReachable = MutableStateFlow(false)
    val hubReachable = _hubReachable.asStateFlow()
    private val _hubUrlValidationError = MutableStateFlow<String?>(null)
    val hubUrlValidationError = _hubUrlValidationError.asStateFlow()
    private val _emergencyModeActive = MutableStateFlow(false)
    val emergencyModeActive = _emergencyModeActive.asStateFlow()
    private val _emergencyModeOverlayVisible = MutableStateFlow(false)
    val emergencyModeOverlayVisible = _emergencyModeOverlayVisible.asStateFlow()
    
    // Session State
    private var _sessionId = MutableStateFlow<String?>(null)
    val sessionId = _sessionId.asStateFlow()
    
    private val _chatHistory = MutableStateFlow<List<ChatMessage>>(emptyList())
    val chatHistory = _chatHistory.asStateFlow()

    private val _chatMode = MutableStateFlow(ChatMode.VOICE_ONLY)
    val chatMode = _chatMode.asStateFlow()

    private val _loadingTitle = MutableStateFlow("")
    val loadingTitle = _loadingTitle.asStateFlow()

    private val _loadingSubtitle = MutableStateFlow("")
    val loadingSubtitle = _loadingSubtitle.asStateFlow()

    private val _voiceLevels = MutableStateFlow(List(24) { 0f })
    val voiceLevels = _voiceLevels.asStateFlow()

    private val _emergencyCooldownActive = MutableStateFlow(false)
    val emergencyCooldownActive = _emergencyCooldownActive.asStateFlow()

    private val _faqSuggestions = MutableStateFlow<List<com.reskiosk.network.FaqSuggestion>>(emptyList())
    val faqSuggestions = _faqSuggestions.asStateFlow()

    // Inactivity auto-timeout
    private var inactivityJob: Job? = null
    private val INACTIVITY_TIMEOUT_MS = 60_000L  // 1 minute

    @Volatile
    private var _punctuator: OfflinePunctuation? = null

    init {
        // Persistent kiosk_id: same key as HubClient so heartbeat and query use same ID
        val kioskId = prefs.getString("kiosk_id", null)
            ?: UUID.randomUUID().toString().also { prefs.edit().putString("kiosk_id", it).apply() }
        HubApiClient.setKioskId(kioskId)

        // Start heartbeat if URL exists (runs on IO so it never blocks UI)
        if (getHubUrl().isNotBlank()) {
            startHeartbeat()
            refreshHubConnectionStatus()
        }
        
        // Load punctuation model on background thread to avoid blocking main thread and triggering ANR
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val punctDir = File(application.filesDir, "sherpa-models/" + com.reskiosk.ModelConstants.PUNCTUATION_DIR)
                if (punctDir.exists()) {
                    val modelPath = File(punctDir, "model.onnx").absolutePath
                    val config = OfflinePunctuationConfig(
                        model = OfflinePunctuationModelConfig(
                            ctTransformer = modelPath,
                            numThreads = 1,
                            debug = false,
                            provider = "cpu"
                        )
                    )
                    _punctuator = OfflinePunctuation(assetManager = null, config = config)
                    Log.i("KioskVM", "Punctuation model loaded successfully.")
                } else {
                    Log.w("KioskVM", "Punctuation model directory not found.")
                }
            } catch (e: Exception) {
                Log.e("KioskVM", "Failed to load punctuation model", e)
            }
        }

    }

    private fun startHeartbeat() {
        heartbeatJob?.cancel()
        heartbeatJob = viewModelScope.launch(Dispatchers.IO) {
            while (isActive) {
                val saved = getHubUrl()
                if (saved.isNotBlank()) {
                    val normalized = normalizeHubUrl(saved)
                    if (normalized == null) {
                        _hubUrlValidationError.value = "Invalid URL. Use host:port or http://host:port."
                        _hubReachable.value = false
                        delay(HUB_POLL_INTERVAL_MS)
                        continue
                    }
                    _hubUrlValidationError.value = null
                    if (normalized != saved) {
                        prefs.edit().putString("hub_url", normalized).apply()
                    }
                    try {
                        val (reachable, pingResp) = probeHub(normalized)
                        if (!reachable) throw IllegalStateException("Hub unreachable")
                        failedPings = 0
                        _hubReachable.value = true
                        updateEmergencyModeFromPing(pingResp)
                    } catch (e: Exception) {
                        failedPings++
                        android.util.Log.e("KioskViewModel", "Heartbeat failed ($failedPings)", e)
                        if (failedPings == 3) {
                            // We only log this once when we first hit the threshold.
                            // Do NOT disconnectHub() here so we auto-reconnect once the hub recovers.
                            android.util.Log.e("KioskViewModel", "Connection lost, but keeping hub URL to auto-reconnect.")
                        }
                        if (failedPings >= 3) {
                            _hubReachable.value = false
                        }
                    }
                }
                delay(HUB_POLL_INTERVAL_MS)
            }
        }
    }
    private val _transcript = MutableStateFlow("")
    val transcript = _transcript.asStateFlow()

    // Selected language — restored from SharedPreferences
    private val _selectedLanguage = MutableStateFlow(
        prefs.getString("selected_language", "en") ?: "en"
    )
    val selectedLanguage = _selectedLanguage.asStateFlow()

    // Dark mode — restored from SharedPreferences
    private val _darkModeEnabled = MutableStateFlow(
        prefs.getBoolean("dark_mode_enabled", false)
    )
    val darkModeEnabled = _darkModeEnabled.asStateFlow()

    private val _isChangingLanguage = MutableStateFlow(false)
    val isChangingLanguage = _isChangingLanguage.asStateFlow()

    fun setLanguage(langCode: String) {
        if (langCode == _selectedLanguage.value) return
        _selectedLanguage.value = langCode
        _isChangingLanguage.value = true
        Log.i("KioskVM", "Language set to: $langCode")

        // Persist selection
        prefs.edit().putString("selected_language", langCode).apply()

        // NS: en/ja keep suppression; es/de/fr get raw mic for Whisper
        recorder.setNoiseSuppressionEnabled(langCode == "en" || langCode == "ja")
        val needRestart = _sessionId.value != null
        val currentState = _uiState.value
        val busy = currentState is KioskState.PreparingToListen || currentState is KioskState.Listening || currentState is KioskState.Transcribing
        if (needRestart) {
            if (busy) {
                pendingRecorderRestart = true
            } else {
                recorder.stopContinuousListening()
                recorder.startContinuousListening(viewModelScope)
            }
        }

        // Rebuild STT/TTS engine for selected language on a background thread
        viewModelScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            val oldStt = stt
            stt = null
            oldStt?.release()
            stt = SherpaSttEngine.forLanguage(getApplication(), langCode)
            val oldTts = tts
            tts = null
            oldTts?.release()
            tts = SherpaTtsEngine.forLanguage(getApplication(), langCode)
            withContext(kotlinx.coroutines.Dispatchers.Main) {
                _isChangingLanguage.value = false
                validateCurrentLanguageTts()
                Log.i("KioskVM", "Language engines ready for: $langCode")
            }
        }
    }

    /** If a recorder restart was deferred (language change during Recording/Transcribing), do it now. */
    private fun performPendingRecorderRestartIfNeeded() {
        if (!pendingRecorderRestart || _sessionId.value == null) return
        pendingRecorderRestart = false
        recorder.stopContinuousListening()
        recorder.startContinuousListening(viewModelScope)
    }

    /** Remove the "Listening..." placeholder from chat history (batch UX) and clear the stored id. Call from Main only. */
    private fun removeListeningPlaceholderIfAny() {
        val id = currentListeningPlaceholderId ?: return
        currentListeningPlaceholderId = null
        _chatHistory.value = _chatHistory.value.filter { it.id != id }
    }

    // Dependencies — STT uses factory for language-aware model selection
    private val recorder = AudioRecorder()
    private var stt: SherpaSttEngine? = SherpaSttEngine.forLanguage(application, _selectedLanguage.value)
    private var tts: SherpaTtsEngine? = SherpaTtsEngine.forLanguage(application, _selectedLanguage.value)

    init {
        validateCurrentLanguageTts()
    }

    // State
    private var recordedSamples: MutableList<Float> = Collections.synchronizedList(mutableListOf())
    private var lastQueryEnglish: String? = null
    private var lastQueryOriginal: String? = null
    private var hasSpokenSessionEnding = false

    // Emergency flow state
    private var emergencyAlertId: Int? = null
    private var emergencyAlertLocalId: String? = null
    private var emergencyTranscript: String? = null
    private var emergencyTier: Int = 1
    private var emergencyRetryJob: Job? = null
    private var emergencyPollJob: Job? = null
    private var emergencyConfirmJob: Job? = null
    private var emergencyCancelJob: Job? = null
    private var emergencyCooldownJob: Job? = null
    private var emergencyResolvedAutoEndJob: Job? = null
    private var emergencyModeOverlayJob: Job? = null
    private var emergencyModeReminderJob: Job? = null
    private var emergencyAlarmPlayer: MediaPlayer? = null
    private var emergencyCooldownUntil: Long = 0L
    private var smoothedVoiceLevel: Float = 0f

    private val EMERGENCY_CONFIRM_SECONDS = 20
    private val EMERGENCY_CANCEL_SECONDS = 10
    private val EMERGENCY_POLL_INTERVAL_MS = 15_000L
    private val EMERGENCY_RETRY_INTERVAL_MS = 30_000L
    private val EMERGENCY_COOLDOWN_MS = 60_000L
    private val HUB_POLL_INTERVAL_MS = 5_000L
    private val EMERGENCY_MODE_OVERLAY_MS = 5_000L
    private val EMERGENCY_MODE_REMINDER_INTERVAL_MS = 5 * 60_000L

    /** Defer recorder restart until Idle when language changed during Recording/Transcribing */
    private var pendingRecorderRestart = false
    /** UUID of the "Listening..." user message for batch languages; replaced with transcript in processAudio() */
    private var currentListeningPlaceholderId: String? = null
    /** Cancel this to abort the delay before actually entering Listening (PreparingToListen). */
    private var startListeningJob: Job? = null
    /** For batch: true after first real audio chunk (after pre-buffer skip). Used to add "Listening..." only when we confirm we're hearing. */
    @Volatile
    private var hasReceivedRealAudio = false

    // Preferences

    private fun normalizeHubUrl(url: String): String? {
        val raw = url.trim()
        if (raw.isBlank()) return null
        val candidate = if (raw.contains("://")) raw else "http://$raw"
        return try {
            val uri = URI(candidate)
            val scheme = (uri.scheme ?: "http").lowercase()
            if (scheme != "http" && scheme != "https") return null
            val host = uri.host?.trim()?.lowercase() ?: return null
            if (host.isBlank()) return null
            if (host != "localhost" && !host.contains(".")) return null
            val port = if (uri.port > 0) uri.port else 8000
            URI(scheme, null, host, port, null, null, null).toString().removeSuffix("/")
        } catch (_: Exception) {
            null
        }
    }

    fun getHubUrl(): String = (prefs.getString("hub_url", "") ?: "").trim()

    fun clearHubUrlValidationError() {
        _hubUrlValidationError.value = null
    }

    fun saveHubUrl(url: String): Boolean {
        val normalized = normalizeHubUrl(url)
        if (normalized == null) {
            _hubUrlValidationError.value = "Invalid URL. Use host:port or http://host:port."
            _hubReachable.value = false
            return false
        }
        _hubUrlValidationError.value = null
        prefs.edit().putString("hub_url", normalized).apply()
        android.util.Log.i("KioskViewModel", "Hub URL saved: $normalized, starting heartbeat")
        startHeartbeat()
        refreshHubConnectionStatus()
        return true
    }

    fun setDarkModeEnabled(enabled: Boolean) {
        if (_darkModeEnabled.value == enabled) return
        _darkModeEnabled.value = enabled
        prefs.edit().putBoolean("dark_mode_enabled", enabled).apply()
    }

    fun disconnectHub() {
        prefs.edit().remove("hub_url").apply()
        heartbeatJob?.cancel()
        heartbeatJob = null
        failedPings = 0
        _hubReachable.value = false
        _hubUrlValidationError.value = null
        endSession()
        android.util.Log.i("KioskViewModel", "Hub disconnected, heartbeat stopped")
    }

    private suspend fun probeHub(url: String): Pair<Boolean, PingResponse?> {
        val probeTargets = LinkedHashSet<String>()
        probeTargets.add(url)
        if (url.startsWith("https://")) {
            probeTargets.add("http://${url.removePrefix("https://")}")
        }
        for (target in probeTargets) {
            val api = HubApiClient.getService(target)
            try {
                val pingResp = api.ping()
                if (target != url) {
                    prefs.edit().putString("hub_url", target).apply()
                }
                return Pair(true, pingResp)
            } catch (pingError: Exception) {
                Log.w("KioskViewModel", "Ping check failed for $target: ${pingError.message}")
                try {
                    api.health()
                    try {
                        val kioskId = prefs.getString("kiosk_id", null)
                            ?: UUID.randomUUID().toString().also { prefs.edit().putString("kiosk_id", it).apply() }
                        api.heartbeat(
                            mapOf(
                                "kiosk_id" to kioskId,
                                "status" to "online",
                                "center_id" to "center_1"
                            )
                        )
                    } catch (heartbeatError: Exception) {
                        Log.w("KioskViewModel", "register_kiosk fallback failed: ${heartbeatError.message}")
                    }
                    if (target != url) {
                        prefs.edit().putString("hub_url", target).apply()
                    }
                    return Pair(true, null)
                } catch (healthError: Exception) {
                    Log.w("KioskViewModel", "Health check failed for $target: ${healthError.message}")
                }
            }
        }
        return Pair(false, null)
    }

    private fun updateEmergencyModeFromPing(ping: PingResponse?) {
        val active = ping?.emergencyModeActive == true
        val activatedAt = ping?.emergencyModeActivatedAt ?: 0L
        _emergencyModeActive.value = active
        if (!active) {
            emergencyModeOverlayJob?.cancel()
            emergencyModeReminderJob?.cancel()
            _emergencyModeOverlayVisible.value = false
            return
        }
        ensureEmergencyModeReminder()
        val lastSeen = prefs.getLong("last_seen_emergency_mode_activated_at", 0L)
        if (activatedAt > 0L && activatedAt > lastSeen) {
            prefs.edit().putLong("last_seen_emergency_mode_activated_at", activatedAt).apply()
            triggerEmergencyModeAlert()
        }
    }

    private fun ensureEmergencyModeReminder() {
        if (emergencyModeReminderJob?.isActive == true) return
        emergencyModeReminderJob = viewModelScope.launch {
            while (isActive) {
                delay(EMERGENCY_MODE_REMINDER_INTERVAL_MS)
                if (_emergencyModeActive.value) {
                    triggerEmergencyModeAlert()
                } else {
                    break
                }
            }
        }
    }

    private fun triggerEmergencyModeAlert() {
        emergencyModeOverlayJob?.cancel()
        _emergencyModeOverlayVisible.value = true
        playEmergencyModeAlarmOnce()
        emergencyModeOverlayJob = viewModelScope.launch {
            delay(EMERGENCY_MODE_OVERLAY_MS)
            _emergencyModeOverlayVisible.value = false
        }
    }

    private fun playEmergencyModeAlarmOnce() {
        viewModelScope.launch(Dispatchers.Main) {
            try {
                emergencyAlarmPlayer?.release()
                emergencyAlarmPlayer = MediaPlayer.create(getApplication(), R.raw.emergencycallalert)
                emergencyAlarmPlayer?.setOnCompletionListener { mp ->
                    try {
                        mp.release()
                    } catch (_: Exception) {
                    }
                    if (emergencyAlarmPlayer === mp) {
                        emergencyAlarmPlayer = null
                    }
                }
                emergencyAlarmPlayer?.start()
            } catch (e: Exception) {
                Log.e("KioskViewModel", "Emergency mode alarm playback failed", e)
            }
        }
    }

    fun refreshHubConnectionStatus(onDone: ((Boolean) -> Unit)? = null) {
        val saved = getHubUrl()
        if (saved.isBlank()) {
            _hubReachable.value = false
            onDone?.invoke(false)
            return
        }
        val normalized = normalizeHubUrl(saved)
        if (normalized == null) {
            _hubUrlValidationError.value = "Invalid URL. Use host:port or http://host:port."
            _hubReachable.value = false
            onDone?.invoke(false)
            return
        }
        _hubUrlValidationError.value = null
        if (normalized != saved) {
            prefs.edit().putString("hub_url", normalized).apply()
        }
        viewModelScope.launch(Dispatchers.IO) {
            val (reachable, pingResp) = try {
                probeHub(normalized)
            } catch (e: Exception) {
                Log.e("KioskViewModel", "Hub refresh failed", e)
                Pair(false, null)
            }
            if (reachable) {
                failedPings = 0
                _hubReachable.value = true
                updateEmergencyModeFromPing(pingResp)
            } else {
                failedPings++
                _hubReachable.value = false
            }
            withContext(Dispatchers.Main) {
                onDone?.invoke(reachable)
            }
        }
    }

    // Cloud connectivity polling disabled (offline-first rollback).

    fun setChatMode(mode: ChatMode) {
        _chatMode.value = mode
    }

    private fun beginLoadingOverlay() {
        _loadingTitle.value = EmergencyStrings.getRandom("asking_hub_title", 5, _selectedLanguage.value)
        _loadingSubtitle.value = EmergencyStrings.get("asking_hub_subtitle", _selectedLanguage.value)
    }

    private fun clearLoadingOverlay() {
        _loadingTitle.value = ""
        _loadingSubtitle.value = ""
    }

    private fun resetVoiceLevels() {
        smoothedVoiceLevel = 0f
        _voiceLevels.value = List(24) { 0f }
    }

    private fun updateVoiceLevels(chunk: FloatArray) {
        if (chunk.isEmpty()) return
        var sumSquares = 0.0
        for (sample in chunk) {
            sumSquares += (sample * sample).toDouble()
        }
        val rms = sqrt(sumSquares / chunk.size).toFloat()
        val normalized = (rms * 8f).coerceIn(0f, 1f)
        smoothedVoiceLevel = (smoothedVoiceLevel * 0.84f) + (normalized * 0.16f)

        val current = _voiceLevels.value
        if (current.isEmpty()) {
            _voiceLevels.value = listOf(smoothedVoiceLevel)
            return
        }
        _voiceLevels.value = current.drop(1) + smoothedVoiceLevel
    }

    // --- Inactivity Timer ---
    private fun resetInactivityTimer() {
        if (_sessionId.value == null) return // No session, no timer
        inactivityJob?.cancel()
        inactivityJob = viewModelScope.launch {
            delay(INACTIVITY_TIMEOUT_MS)
            Log.i("KioskVM", "Session inactive for ${INACTIVITY_TIMEOUT_MS / 1000}s, terminating")
            _uiState.value = KioskState.TerminatingSession
            tts?.stop()
            recorder.stopRecording()
            delay(2_000L) // Show overlay briefly
            endSession()
        }
    }

    private fun cancelInactivityTimer() {
        inactivityJob?.cancel()
        inactivityJob = null
    }

    // --- Session API ---
    fun startSession() {
        _sessionId.value = UUID.randomUUID().toString()
        _chatHistory.value = emptyList()
        _uiState.value = KioskState.Idle
        _chatMode.value = ChatMode.VOICE_ONLY
        clearLoadingOverlay()
        resetVoiceLevels()
        hasSpokenSessionEnding = false
        emergencyAlertId = null
        emergencyAlertLocalId = null
        emergencyTranscript = null
        emergencyTier = 1
        emergencyRetryJob?.cancel()
        emergencyPollJob?.cancel()
        emergencyConfirmJob?.cancel()
        emergencyCancelJob?.cancel()
        emergencyCooldownJob?.cancel()
        emergencyResolvedAutoEndJob?.cancel()
        emergencyCooldownUntil = 0L
        _emergencyCooldownActive.value = false
        recorder.setNoiseSuppressionEnabled(_selectedLanguage.value == "en" || _selectedLanguage.value == "ja")
        recorder.startContinuousListening(viewModelScope)

        fetchFaqSuggestions()
        val welcome = EmergencyStrings.get("session_start_welcome", _selectedLanguage.value)
        tts?.stop()
        tts?.speak(welcome)

        resetInactivityTimer()
    }

    fun endSession() {
        val currentSession = _sessionId.value
        val currentEmergencyAlertId = emergencyAlertId
        if (currentEmergencyAlertId != null) {
            sendEmergencyDismissToHub(currentEmergencyAlertId)
        }
        cancelInactivityTimer()
        _sessionId.value = null
        _chatHistory.value = emptyList()
        _uiState.value = KioskState.Idle
        _chatMode.value = ChatMode.VOICE_ONLY
        clearLoadingOverlay()
        resetVoiceLevels()
        _transcript.value = ""
        emergencyAlertId = null
        emergencyAlertLocalId = null
        emergencyTranscript = null
        emergencyTier = 1
        emergencyRetryJob?.cancel()
        emergencyPollJob?.cancel()
        emergencyConfirmJob?.cancel()
        emergencyCancelJob?.cancel()
        emergencyCooldownJob?.cancel()
        emergencyResolvedAutoEndJob?.cancel()
        emergencyCooldownUntil = 0L
        _emergencyCooldownActive.value = false
        _faqSuggestions.value = emptyList()

        if (currentSession != null && !hasSpokenSessionEnding) {
            hasSpokenSessionEnding = true
            val msg = EmergencyStrings.get("session_ending", _selectedLanguage.value)
            tts?.stop()
            tts?.speak(msg)
        }


        
        // Notify Hub to clear memory
        if (currentSession != null) {
            val url = getHubUrl()
            if (url.isNotBlank()) {
                viewModelScope.launch {
                    try {
                        val api = HubApiClient.getService(url)
                        api.endSession(currentSession)
                    } catch (e: Exception) {
                        // Ignore backend connection errors on disconnect
                    }
                }
            }
        }
    }

    // --- FAQ Suggestions ---

    private fun fetchFaqSuggestions() {
        val hubUrl = normalizeHubUrl(getHubUrl()) ?: return
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val api = HubApiClient.getService(hubUrl)
                val items = api.faqSuggestions(limit = 5)
                withContext(Dispatchers.Main) {
                    _faqSuggestions.value = items
                }
            } catch (e: Exception) {
                Log.w("KioskVM", "Failed to fetch FAQ suggestions: ${e.message}")
            }
        }
    }

    fun selectFaqSuggestion(question: String) {
        _faqSuggestions.value = emptyList()
        resetInactivityTimer()

        val msgId = UUID.randomUUID().toString()
        _chatHistory.value = _chatHistory.value + ChatMessage(
            isUser = true,
            text = question,
            id = msgId
        )

        _uiState.value = KioskState.Processing
        _loadingTitle.value = EmergencyStrings.get("searching", _selectedLanguage.value)
        _loadingSubtitle.value = ""

        performQuery(
            queryEnglish = question,
            queryOriginal = question,
            isRetry = false
        )
    }

    // --- Inputs ---

    fun startListening() {
        if (stt == null) {
            Log.w("KioskVM", "startListening blocked: STT engine not ready (language change in progress)")
            return
        }
        // Allow recording from Idle, Speaking, Error, and Clarification; block Emergency and busy states
        val currentState = _uiState.value
        if (currentState !is KioskState.Idle && currentState !is KioskState.Speaking && currentState !is KioskState.Error && currentState !is KioskState.Clarification ||
            currentState is KioskState.EmergencyActive ||
            currentState is KioskState.EmergencyAcknowledged ||
            currentState is KioskState.EmergencyConfirmation ||
            currentState is KioskState.EmergencyPending ||
            currentState is KioskState.EmergencyResponding ||
            currentState is KioskState.EmergencyResolved ||
            currentState is KioskState.EmergencyFailed ||
            currentState is KioskState.EmergencyCancelWindow ||
            currentState is KioskState.EmergencyCancelled) {
            // Stuck-state recovery: if stuck in Processing/Transcribing for too long, force reset
            Log.w("KioskVM", "startListening blocked by state: $currentState — ignoring")
            return
        }
        
        // Stop any previous TTS and clear pre-buffer so we don't record speaker output
        try { recorder.stopRecording() } catch (e: Exception) {}
        tts?.stop()
        clearLoadingOverlay()
        resetVoiceLevels()
        // New question about to start: hide any previous feedback button until we have a fresh answer


        _uiState.value = KioskState.PreparingToListen
        startListeningJob = viewModelScope.launch {
            // Hard gate recording until TTS pipeline is fully settled to avoid audio bleed.
            waitForTtsToSettle()
            if (!isActive) return@launch
            _uiState.value = KioskState.Listening
            startListeningJob = null
            _transcript.value = ""
            recordedSamples = Collections.synchronizedList(mutableListOf())
            hasReceivedRealAudio = false

            resetInactivityTimer()
            stt?.beginStream()
            var skipNextChunk = isBatchLanguage(_selectedLanguage.value)
            recorder.startRecording { chunk ->
                if (skipNextChunk) {
                    skipNextChunk = false
                    return@startRecording
                }
                // No live transcript/placeholder streaming in chat while recording.
                synchronized(recordedSamples) {
                    if (recordedSamples.size < 16000 * 300) {
                        recordedSamples.addAll(chunk.toList())
                    }
                }
                updateVoiceLevels(chunk)
                stt?.feedAndDecodeStream(chunk)
            }
        }
    }

    fun stopListening() {
        when (val s = _uiState.value) {
            is KioskState.PreparingToListen -> {
                startListeningJob?.cancel()
                startListeningJob = null
                _uiState.value = KioskState.Idle
                resetVoiceLevels()
            }
            is KioskState.Listening -> {
                recorder.stopRecording()
                resetVoiceLevels()
                beginLoadingOverlay()
                _uiState.value = KioskState.Transcribing
                resetInactivityTimer()
                // Continuous listener stays running in background for next tap
                processAudio()
            }
            else -> { /* no-op */ }
        }
    }

    fun selectClarification(category: String) {
        val qEn = lastQueryEnglish ?: return
        val qOrg = lastQueryOriginal ?: qEn
        resetInactivityTimer()
        performQuery(qEn, qOrg, isRetry = true, category = category)
    }

    fun submitTypedQuery(text: String) {
        val trimmed = text.trim()
        if (trimmed.isBlank() || _sessionId.value == null) return
        if (_uiState.value is KioskState.Transcribing || _uiState.value is KioskState.Processing) return
        tts?.stop()
        try { recorder.stopRecording() } catch (_: Exception) {}
        clearLoadingOverlay()
        resetVoiceLevels()

        val emergencyResult = EmergencyDetector.detect(trimmed, trimmed)
        if (emergencyResult.isEmergency) {
            tts?.stop()
            cancelInactivityTimer()
            if (emergencyResult.tier == 1) {
                startEmergencyCancelWindow(trimmed)
            } else {
                _uiState.value = KioskState.EmergencyConfirmation(trimmed, EMERGENCY_CONFIRM_SECONDS)
                startEmergencyConfirmationCountdown(trimmed)
                tts?.speak(EmergencyStrings.get("confirm_prompt", _selectedLanguage.value))
            }
            return
        }

        val queryType = inferTextQueryType(trimmed)
        val newList = _chatHistory.value.toMutableList()
        newList.add(ChatMessage(isUser = true, text = trimmed))
        _chatHistory.value = newList
        lastQueryEnglish = trimmed
        lastQueryOriginal = trimmed
        beginLoadingOverlay()
        _uiState.value = KioskState.Processing
        resetInactivityTimer()
        performQuery(
            queryEnglish = trimmed,
            queryOriginal = trimmed,
            isRetry = false,
            category = null,
            placeholderId = null,
            queryType = queryType,
            intonationConfidence = 0f,
        )
    }

    private fun inferTextQueryType(text: String): String {
        val trimmed = text.trim()
        if (trimmed.endsWith("?")) return "question"
        val lowered = trimmed.lowercase()
        val firstToken = lowered.split(Regex("\\s+")).firstOrNull().orEmpty()
        val questionStarts = setOf(
            "what", "where", "when", "why", "how", "who", "which",
            "can", "could", "is", "are", "do", "does", "did",
            "will", "would", "should", "may", "que", "donde", "cuando", "como",
            "wer", "wann", "wie", "warum", "quoi", "ou", "quand", "comment",
            "nan", "doko", "itsu", "naze", "dou"
        )
        return if (firstToken in questionStarts) "question" else "statement"
    }

    private fun isFollowUpAgreement(text: String, language: String): Boolean {
        val normalized = text
            .trim()
            .lowercase()
            .replace(Regex("[^\\p{L}\\p{N}\\s]"), " ")
            .replace(Regex("\\s+"), " ")
            .trim()
        if (normalized.isBlank()) return false

        val baseAgreement = setOf(
            "yes", "yes please", "yeah", "yep", "sure", "ok", "okay", "go ahead",
            "affirmative", "please do", "do it",
            "opo", "oo", "sige"
        )
        val localizedAgreement = when (language.lowercase()) {
            "es" -> setOf("si", "sí", "claro", "vale", "por favor")
            "de" -> setOf("ja", "klar", "bitte", "ok")
            "fr" -> setOf("oui", "daccord", "d accord", "ok", "bien sur")
            "ja" -> setOf("hai", "un", "onegai", "yoroshiku")
            else -> emptySet()
        }
        return normalized in baseAgreement || normalized in localizedAgreement
    }

    private fun followUpIntentToCategory(intent: String): String? {
        return when (intent.lowercase()) {
            "food" -> "Food & Water"
            "medical" -> "Medical"
            "registration" -> "Registration"
            "sleeping" -> "Sleeping"
            "facilities" -> "Facilities"
            "transportation" -> "Transportation"
            "safety", "emergency" -> "Safety"
            "lost_person" -> "Lost Person"
            "pets" -> "Pets"
            "children" -> "Children"
            "special_needs" -> "Special Needs"
            else -> null
        }
    }

    fun reset() {
        recorder.stopRecording()
        tts?.stop()
        try { stt?.finishStream() } catch (e: Exception) {}
        _transcript.value = ""
        _uiState.value = KioskState.Idle
        clearLoadingOverlay()
        resetVoiceLevels()
        performPendingRecorderRestartIfNeeded()
    }

    // --- Emergency (see Section 1.1 for inactivity/timer behavior) ---

    private fun startEmergencyConfirmationCountdown(transcript: String) {
        emergencyConfirmJob?.cancel()
        emergencyConfirmJob = viewModelScope.launch(Dispatchers.Main) {
            for (remaining in EMERGENCY_CONFIRM_SECONDS downTo 1) {
                if (_uiState.value !is KioskState.EmergencyConfirmation) return@launch
                _uiState.value = KioskState.EmergencyConfirmation(transcript, remaining)
                delay(1_000L)
            }
            confirmEmergency(transcript)
        }
    }

    private fun startEmergencyCancelWindow(transcript: String) {
        emergencyCancelJob?.cancel()
        emergencyCancelJob = viewModelScope.launch(Dispatchers.Main) {
            for (remaining in EMERGENCY_CANCEL_SECONDS downTo 1) {
                _uiState.value = KioskState.EmergencyCancelWindow(transcript, remaining)
                delay(1_000L)
            }
            activateEmergency(transcript, tier = 1)
        }
    }

    private fun startEmergencyCooldown() {
        emergencyCooldownJob?.cancel()
        emergencyCooldownUntil = System.currentTimeMillis() + EMERGENCY_COOLDOWN_MS
        _emergencyCooldownActive.value = true
        emergencyCooldownJob = viewModelScope.launch {
            delay(EMERGENCY_COOLDOWN_MS)
            _emergencyCooldownActive.value = false
            emergencyCooldownUntil = 0L
        }
    }

    private fun activateEmergency(transcript: String, tier: Int) {
        emergencyTranscript = transcript
        emergencyTier = tier
        cancelInactivityTimer()
        clearLoadingOverlay()
        resetVoiceLevels()
        emergencyConfirmJob?.cancel()
        emergencyCancelJob?.cancel()
        emergencyRetryJob?.cancel()
        emergencyPollJob?.cancel()
        tts?.stop()
        _uiState.value = KioskState.EmergencyPending
        postEmergency(retryCount = 0)
    }

    private fun postEmergency(retryCount: Int) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val hubUrl = prefs.getString("hub_url", "") ?: ""
                if (hubUrl.isBlank()) throw IllegalStateException("Hub not configured")

                val kioskId = prefs.getString("kiosk_id", null) ?: UUID.randomUUID().toString().also {
                    prefs.edit().putString("kiosk_id", it).apply()
                }
                val kioskLocation = prefs.getString("kiosk_location", "Unknown") ?: "Unknown"
                val localId = emergencyAlertLocalId ?: UUID.randomUUID().toString().also {
                    emergencyAlertLocalId = it
                    prefs.edit().putString("emergency_alert_local_id", it).apply()
                }

                val api = HubApiClient.getService(hubUrl)
                val transcriptToSend = emergencyTranscript ?: "[no transcript]"
                val resp = api.emergency(
                    mapOf(
                        "kiosk_id" to kioskId,
                        "kiosk_location" to kioskLocation,
                        "transcript" to transcriptToSend,
                        "language" to _selectedLanguage.value,
                        "timestamp" to System.currentTimeMillis(),
                        "tier" to emergencyTier,
                        "alert_id_local" to localId,
                        "retry_count" to retryCount
                    )
                )
                val alertId = resp.alertId
                if (alertId == null) throw IllegalStateException("Missing alert_id from hub")

                emergencyAlertId = alertId
                emergencyRetryJob?.cancel()
                emergencyRetryJob = null
                emergencyAlertLocalId = null
                prefs.edit().remove("emergency_alert_local_id").apply()

                withContext(Dispatchers.Main) {
                    _uiState.value = KioskState.EmergencyActive
                }
                startEmergencyPolling()
            } catch (e: Exception) {
                Log.e("Emergency", "Hub notify failed: ${e.message}")
                withContext(Dispatchers.Main) {
                    _uiState.value = KioskState.EmergencyFailed(retryCount + 1)
                }
                if (emergencyRetryJob == null || emergencyRetryJob?.isActive == false) {
                    startEmergencyRetryLoop(retryCount + 1)
                }
            }
        }
    }

    private fun startEmergencyRetryLoop(initialRetryCount: Int) {
        emergencyRetryJob?.cancel()
        emergencyRetryJob = viewModelScope.launch(Dispatchers.IO) {
            var count = initialRetryCount
            while (isActive) {
                delay(EMERGENCY_RETRY_INTERVAL_MS)
                postEmergency(retryCount = count)
                count += 1
            }
        }
    }

    private fun startEmergencyPolling() {
        emergencyPollJob?.cancel()
        emergencyPollJob = viewModelScope.launch(Dispatchers.IO) {
            while (isActive) {
                delay(EMERGENCY_POLL_INTERVAL_MS)
                val alertId = emergencyAlertId ?: continue
                try {
                    val hubUrl = prefs.getString("hub_url", "") ?: ""
                    if (hubUrl.isBlank()) continue
                    val api = HubApiClient.getService(hubUrl)
                    val statusResp = api.emergencyStatus(alertId)
                    val status = statusResp.status ?: "ACTIVE"
                    when (status) {
                        "ACTIVE" -> withContext(Dispatchers.Main) {
                            _uiState.value = KioskState.EmergencyActive
                        }
                        "ACKNOWLEDGED" -> withContext(Dispatchers.Main) {
                            _uiState.value = KioskState.EmergencyAcknowledged
                        }
                        "RESPONDING" -> withContext(Dispatchers.Main) {
                            _uiState.value = KioskState.EmergencyResponding
                        }
                        "RESOLVED" -> {
                            withContext(Dispatchers.Main) {
                                _uiState.value = KioskState.EmergencyResolved
                            }
                            emergencyPollJob?.cancel()
                            emergencyResolvedAutoEndJob?.cancel()
                            emergencyResolvedAutoEndJob = viewModelScope.launch(Dispatchers.Main) {
                                delay(30_000L)
                                if (_uiState.value is KioskState.EmergencyResolved && _sessionId.value != null) {
                                    endSession()
                                }
                            }
                        }
                        "DISMISSED" -> {
                            emergencyPollJob?.cancel()
                            withContext(Dispatchers.Main) {
                                finishEmergencyLocal()
                            }
                        }
                    }
                } catch (e: Exception) {
                    Log.e("Emergency", "Status poll failed: ${e.message}")
                }
            }
        }
    }

    private fun finishEmergencyLocal() {
        emergencyRetryJob?.cancel()
        emergencyPollJob?.cancel()
        emergencyConfirmJob?.cancel()
        emergencyCancelJob?.cancel()
        emergencyResolvedAutoEndJob?.cancel()
        clearLoadingOverlay()
        resetVoiceLevels()
        emergencyAlertId = null
        emergencyAlertLocalId = null
        prefs.edit().remove("emergency_alert_local_id").apply()
        emergencyTranscript = null
        emergencyTier = 1
        _uiState.value = KioskState.Idle
        performPendingRecorderRestartIfNeeded()
        resetInactivityTimer()
        startEmergencyCooldown()
    }

    fun confirmEmergency(transcript: String) {
        emergencyConfirmJob?.cancel()
        activateEmergency(transcript, tier = 2)
    }

    fun cancelEmergency() {
        emergencyConfirmJob?.cancel()
        clearLoadingOverlay()
        _uiState.value = KioskState.Idle
        performPendingRecorderRestartIfNeeded()
        resetInactivityTimer()
    }

    fun cancelFalseAlarm() {
        emergencyCancelJob?.cancel()
        clearLoadingOverlay()
        _uiState.value = KioskState.EmergencyCancelled
        viewModelScope.launch {
            delay(1200L)
            if (_uiState.value is KioskState.EmergencyCancelled) {
                _uiState.value = KioskState.Idle
                performPendingRecorderRestartIfNeeded()
                resetInactivityTimer()
            }
        }
    }

    fun dismissEmergency() {
        val alertId = emergencyAlertId
        if (alertId != null) {
            sendEmergencyDismissToHub(alertId)
        }
        finishEmergencyLocal()
    }

    private fun sendEmergencyDismissToHub(alertId: Int) {
        val hubUrl = prefs.getString("hub_url", "") ?: ""
        if (hubUrl.isBlank()) return
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val api = HubApiClient.getService(hubUrl)
                api.dismissEmergency(alertId)
            } catch (e: Exception) {
                Log.e("Emergency", "Dismiss failed: ${e.message}")
            }
        }
    }

    fun onSosButtonPressed() {
        if (_emergencyCooldownActive.value) return
        viewModelScope.launch(Dispatchers.Main) {
            tts?.stop()
            recorder.stopRecording()
            activateEmergency("[SOS button pressed]", tier = 1)
        }
    }

    fun sendFeedbackLike(messageId: String) {
        val message = _chatHistory.value.find { it.id == messageId } ?: return
        // sourceId must be present; queryLogId is required only for the network POST
        if (message.sourceId == null) return

        // Fire-and-forget UI update: dismiss buttons immediately
        _chatHistory.value = _chatHistory.value.map {
            if (it.id == messageId) it.copy(feedbackGiven = true) else it
        }

        val qLogId = message.queryLogId ?: return   // skip network POST if no log id
        val hubUrl = getHubUrl()
        if (hubUrl.isBlank()) return

        // Fire-and-forget network request
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val api = HubApiClient.getService(hubUrl)
                val kioskId = prefs.getString("kiosk_id", null) ?: "unknown"
                val payload = mutableMapOf<String, Any?>(
                    "query_log_id" to qLogId,
                    "label" to 1, // +1 for liked
                    "language" to _selectedLanguage.value,
                    "session_id" to _sessionId.value,
                    "kiosk_id" to kioskId,
                    "center_id" to "center_1",
                )
                message.sourceId?.let { src -> payload["source_id"] = src }
                api.feedback(payload)
            } catch (e: Exception) {
                Log.e("KioskVM", "Feedback POST failed (like)", e)
            }
        }
    }

    /**
     * User disliked the response. Mark it as disliked, then submit negative feedback
     * and retry the exact original query with the sourceId excluded.
     */
    fun sendFeedbackDislike(messageId: String) {
        val message = _chatHistory.value.find { it.id == messageId } ?: return
        // sourceId must be present; queryLogId only needed for network POST
        if (message.sourceId == null) return
        val qLogId = message.queryLogId
        val qEn = message.queryTextEnglish ?: return
        val qOrg = message.queryTextOriginal ?: qEn

        // Fire-and-forget UI update: dismiss buttons immediately
        _chatHistory.value = _chatHistory.value.map {
            if (it.id == messageId) it.copy(feedbackGiven = false) else it
        }

        val hubUrl = getHubUrl()
        if (hubUrl.isBlank()) return

        // Submit negative feedback (only if we have a query_log_id)
        if (qLogId != null) {
            viewModelScope.launch(Dispatchers.IO) {
                try {
                    val api = HubApiClient.getService(hubUrl)
                    val kioskId = prefs.getString("kiosk_id", null) ?: "unknown"
                    val payload = mutableMapOf<String, Any?>(
                        "query_log_id" to qLogId,
                        "label" to -1, // -1 for disliked
                        "language" to _selectedLanguage.value,
                        "session_id" to _sessionId.value,
                        "kiosk_id" to kioskId,
                        "center_id" to "center_1",
                    )
                    message.sourceId?.let { src -> payload["source_id"] = src }
                    api.feedback(payload)
                } catch (e: Exception) {
                    Log.e("KioskVM", "Feedback POST failed (dislike)", e)
                }
            }
        }

        // Accumulate excludes (what we previously excluded + what we are disliking now)
        val excludeIds = (message.excludeSourceIds ?: emptyList()).toMutableSet()
        message.sourceId?.let { excludeIds.add(it) }

        // Retry the query
        viewModelScope.launch(Dispatchers.Main) {
            val placeholderId = "hub_" + System.currentTimeMillis()
            val retryMsg = EmergencyStrings.getRandom("retrieving_new_response", 5, _selectedLanguage.value)
            val newList = _chatHistory.value.toMutableList()
            newList.add(ChatMessage(isUser = false, text = retryMsg, id = placeholderId))
            _chatHistory.value = newList
            tts?.stop()
            tts?.speak(retryMsg)
            performQuery(
                queryEnglish = qEn,
                queryOriginal = qOrg,
                isRetry = true,
                category = null,
                placeholderId = placeholderId,
                queryType = "statement",
                intonationConfidence = 0f,
                excludeSourceIds = excludeIds.toList(),
            )
        }
    }

    // --- Logic ---

    private fun processAudio() {
        viewModelScope.launch(Dispatchers.IO) {
            val lang = _selectedLanguage.value
            try {
                val samples: FloatArray
                synchronized(recordedSamples) {
                    samples = recordedSamples.toFloatArray()
                }
                Log.i("KioskVM", "Recorded ${samples.size} samples (${samples.size / 16000f}s)")

                // 0.3s minimum — short enough for "food?", "water?", "help!"
                if (samples.size < (16000 * 0.3f).toInt()) {
                    withContext(Dispatchers.Main) {
                        removeListeningPlaceholderIfAny()
                        clearLoadingOverlay()
                        handleError(EmergencyStrings.get("recording_too_short", lang))
                    }
                    stt?.finishStream()
                    return@launch
                }

                // Batch (Whisper): 2s minimum for reliable output
                if (isBatchLanguage(lang) && samples.size < 32000) {
                    withContext(Dispatchers.Main) {
                        removeListeningPlaceholderIfAny()
                        clearLoadingOverlay()
                        handleError(EmergencyStrings.get("recording_too_short", lang))
                    }
                    stt?.finishStream()
                    return@launch
                }

                lastSttMode = "local"
                val transcriptRaw = stt?.finishStream() ?: ""
                Log.i("KioskVM", "STT raw transcript: '$transcriptRaw'")

                if (transcriptRaw.isBlank()) {
                    withContext(Dispatchers.Main) {
                        removeListeningPlaceholderIfAny()
                        clearLoadingOverlay()
                        handleError(EmergencyStrings.get("didnt_hear", lang))
                    }
                    return@launch
                }

                // Post-process: corrections + optional punctuation
                // Punctuation only for Zipformer path (en, ja) — Whisper already produces punctuated text
                val useZipformerPunct = (lang == "en" || lang == "ja")
                val transcriptProcessed = com.reskiosk.stt.SttPostProcessor.process(
                    transcriptRaw,
                    punctuator = if (useZipformerPunct) _punctuator else null
                )
                Log.d("STT", "Raw:       $transcriptRaw")
                Log.d("STT", "Corrected: $transcriptProcessed")

                // Whisper silence markers only (no real words like sonido/sound/noise/ruido)
                if (isSilenceOnly(transcriptProcessed)) {
                    withContext(Dispatchers.Main) {
                        removeListeningPlaceholderIfAny()
                        clearLoadingOverlay()
                        handleError(EmergencyStrings.get("didnt_hear", lang))
                    }
                    return@launch
                }

                if (transcriptProcessed.isBlank()) {
                    withContext(Dispatchers.Main) {
                        removeListeningPlaceholderIfAny()
                        clearLoadingOverlay()
                        handleError(EmergencyStrings.get("didnt_catch", lang))
                    }
                    return@launch
                }

                // Emergency detection (both raw and processed) — before intonation and performQuery
                val emergencyResult = EmergencyDetector.detect(transcriptProcessed, transcriptRaw)
                if (emergencyResult.isEmergency) {
                    withContext(Dispatchers.Main) {
                        tts?.stop()
                        clearLoadingOverlay()
                        cancelInactivityTimer()
                        if (emergencyResult.tier == 1) {
                            startEmergencyCancelWindow(transcriptProcessed)
                        } else {
                            _uiState.value = KioskState.EmergencyConfirmation(transcriptProcessed, EMERGENCY_CONFIRM_SECONDS)
                            startEmergencyConfirmationCountdown(transcriptProcessed)
                            tts?.speak(EmergencyStrings.get("confirm_prompt", _selectedLanguage.value))
                        }
                    }
                    return@launch
                }

                // Intonation analysis — combine punctuation, acoustic, and lexical signals
                val intonation = analyzeIntonation(
                    rawText = transcriptRaw,
                    punctuatedText = transcriptProcessed,
                    audioSamples = samples
                )
                Log.i("KioskVM", "Intonation: isQuestion=${intonation.isQuestion}, confidence=${intonation.confidence}")

                // Show final transcript and UI on main thread
                withContext(Dispatchers.Main) {
                    _transcript.value = transcriptProcessed
                    _uiState.value = KioskState.Processing
                    val listeningId = currentListeningPlaceholderId
                    currentListeningPlaceholderId = null
                    val newList = _chatHistory.value.toMutableList()
                    if (listeningId != null) {
                        val idx = newList.indexOfFirst { it.id == listeningId }
                        if (idx >= 0) newList[idx] = ChatMessage(isUser = true, text = transcriptProcessed, id = listeningId)
                        else newList.add(ChatMessage(isUser = true, text = transcriptProcessed))
                    } else {
                        newList.add(ChatMessage(isUser = true, text = transcriptProcessed))
                    }
                    _chatHistory.value = newList
                    lastQueryEnglish = transcriptProcessed
                    lastQueryOriginal = transcriptProcessed
                    performQuery(
                        transcriptProcessed, transcriptProcessed,
                        isRetry = false, category = null,
                        placeholderId = null,
                        queryType = if (intonation.isQuestion) "question" else "statement",
                        intonationConfidence = intonation.confidence
                    )
                }

            } catch (e: Exception) {
                Log.e("KioskVM", "System Error", e)
                withContext(Dispatchers.Main) {
                    removeListeningPlaceholderIfAny()
                    clearLoadingOverlay()
                    handleError(EmergencyStrings.get("err_system", _selectedLanguage.value))
                }
            }
        }
    }

    private fun performQuery(
        queryEnglish: String,
        queryOriginal: String,
        isRetry: Boolean,
        category: String? = null,
        placeholderId: String? = null,
        queryType: String = "statement",
        intonationConfidence: Float = 0f,
        excludeSourceIds: List<Int>? = null,
    ) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                var effectiveIsRetry = isRetry
                var effectiveCategory = category
                var effectiveQueryEnglish = queryEnglish
                var effectiveQueryOriginal = queryOriginal
                val effectiveExcludeSourceIds = (excludeSourceIds ?: emptyList()).toMutableSet()
                val followUp = pendingFollowUp
                var followUpAccepted = false
                if (!isRetry && category == null && followUp != null) {
                    if (isFollowUpAgreement(queryOriginal, _selectedLanguage.value)) {
                        val mappedCategory = followUpIntentToCategory(followUp.intent)
                        if (mappedCategory != null) {
                            effectiveIsRetry = true
                            effectiveCategory = mappedCategory
                            effectiveQueryEnglish = followUp.baseQueryEnglish
                            effectiveQueryOriginal = followUp.baseQueryOriginal
                            followUp.primarySourceId?.let { effectiveExcludeSourceIds.add(it) }
                            followUpAccepted = true
                            Log.i("KioskVM", "Follow-up accepted. Auto-answering secondary intent=${followUp.intent}")
                        }
                    }
                    pendingFollowUp = null
                }

                val hubUrl = normalizeHubUrl(getHubUrl())
                if (hubUrl.isNullOrBlank()) {
                    withContext(Dispatchers.Main) {
                        clearLoadingOverlay()
                        handleError(EmergencyStrings.get("hub_not_configured", _selectedLanguage.value))
                    }
                    return@launch
                }

                val kioskId = prefs.getString("kiosk_id", null)
                    ?: UUID.randomUUID().toString().also { prefs.edit().putString("kiosk_id", it).apply() }
                val payload = mutableMapOf<String, Any?>(
                    "center_id" to "center_1",
                    "kiosk_id" to kioskId,
                    "transcript_original" to effectiveQueryOriginal,
                    "transcript_english" to effectiveQueryEnglish,
                    "language" to _selectedLanguage.value,
                    "kb_version" to 1,
                    "is_retry" to effectiveIsRetry,
                    "query_type" to queryType,
                    "intonation_confidence" to intonationConfidence,
                )
                if (effectiveCategory != null) payload["selected_category"] = effectiveCategory
                if (_sessionId.value != null) payload["session_id"] = _sessionId.value!!
                if (effectiveExcludeSourceIds.isNotEmpty()) {
                    payload["exclude_source_ids"] = effectiveExcludeSourceIds.toList()
                }
                payload["follow_up_token"] = null

                Log.i("KioskVM", "Sending query to hub: ${effectiveQueryEnglish.take(80)}")
                val queryStart = System.currentTimeMillis()
                val api = HubApiClient.getService(hubUrl)
                val response = api.query(payload)
                val queryMs = System.currentTimeMillis() - queryStart
                Log.i("KioskVM", "Hub responded in ${queryMs}ms: type=${response.answerType}")

                withContext(Dispatchers.Main) {
                    clearLoadingOverlay()
                    if (response.answerType == "NEEDS_CLARIFICATION") {
                        pendingFollowUp = null
                        if (placeholderId != null) {
                            _chatHistory.value = _chatHistory.value.filter { it.id != placeholderId }
                        }
                        val clarificationQuestion = EmergencyStrings.get("clarification_question", _selectedLanguage.value)
                        _uiState.value = KioskState.Clarification(
                            clarificationQuestion,
                            response.clarificationCategories ?: emptyList()
                        )
                        tts?.speak(clarificationQuestion)

                        resetInactivityTimer()
                    } else {
                        if (followUpAccepted) {
                            Log.i("KioskVM", "Follow-up answer returned successfully.")
                        }
                        val finalAnswer = if (_selectedLanguage.value == "ja") {
                            response.answerTextLocalized
                                ?: EmergencyStrings.get("no_answer_found", _selectedLanguage.value)
                        } else {
                            response.answerTextLocalized
                                ?: response.answerTextEn
                                ?: EmergencyStrings.get("no_answer_found", _selectedLanguage.value)
                        }
                        pendingFollowUp = response.followUpIntent?.let {
                            PendingFollowUp(
                                intent = it,
                                prompt = response.followUpPrompt,
                                baseQueryEnglish = effectiveQueryEnglish,
                                baseQueryOriginal = effectiveQueryOriginal,
                                primarySourceId = response.sourceId
                            )
                        }

                        if (placeholderId != null) {
                            _chatHistory.value = _chatHistory.value.map {
                                if (it.id == placeholderId) ChatMessage(
                                        isUser = false,
                                        text = finalAnswer,
                                        id = placeholderId, // keep same id
                                        queryLogId = response.queryLogId,
                                        sourceId = response.sourceId,
                                        queryTextEnglish = effectiveQueryEnglish,
                                        queryTextOriginal = effectiveQueryOriginal,
                                        excludeSourceIds = effectiveExcludeSourceIds.toList()
                                ) else it
                            }
                        } else {
                            val newList = _chatHistory.value.toMutableList()
                            newList.add(ChatMessage(
                                isUser = false,
                                text = finalAnswer,
                                id = UUID.randomUUID().toString(),
                                queryLogId = response.queryLogId,
                                sourceId = response.sourceId,
                                queryTextEnglish = effectiveQueryEnglish,
                                queryTextOriginal = effectiveQueryOriginal,
                                excludeSourceIds = effectiveExcludeSourceIds.toList()
                            ))
                            _chatHistory.value = newList
                        }
                        speakAndShow(finalAnswer)
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("KioskViewModel", "Query failed", e)
                withContext(Dispatchers.Main) {
                    clearLoadingOverlay()
                    if (placeholderId != null) {
                        _chatHistory.value = _chatHistory.value.filter { it.id != placeholderId }
                    }
                    val friendlyMsg = when {
                        e is java.net.ConnectException -> EmergencyStrings.get("err_hub_unreachable", _selectedLanguage.value)
                        e is java.net.SocketTimeoutException -> EmergencyStrings.get("err_hub_timeout", _selectedLanguage.value)
                        e.message?.contains("failed to connect", ignoreCase = true) == true -> EmergencyStrings.get("err_hub_unreachable", _selectedLanguage.value)
                        e.message?.contains("timeout", ignoreCase = true) == true -> EmergencyStrings.get("err_connection_timeout", _selectedLanguage.value)
                        else -> EmergencyStrings.get("err_generic", _selectedLanguage.value)
                    }
                    handleError(friendlyMsg)
                }
            }
        }
    }

    private fun handleError(msg: String) {
        clearLoadingOverlay()
        _uiState.value = KioskState.Error(msg)
        tts?.speak(msg)

        // Auto-reset to Idle after 3s so user can record again
        viewModelScope.launch {
            delay(3000L)
            if (_uiState.value is KioskState.Error) {
                _uiState.value = KioskState.Idle
                performPendingRecorderRestartIfNeeded()
            }
        }
    }

    private fun validateCurrentLanguageTts() {
        if (_selectedLanguage.value != "ja") return
        viewModelScope.launch {
            delay(900L)
            if (_selectedLanguage.value != "ja") return@launch
            if (tts?.hasRequiredVoice() == true) return@launch
            showNonBlockingWarning(EmergencyStrings.get("ja_tts_missing", _selectedLanguage.value))
        }
    }

    private fun showNonBlockingWarning(msg: String) {
        _uiState.value = KioskState.Error(msg)
        viewModelScope.launch {
            delay(3200L)
            if (_uiState.value is KioskState.Error) {
                _uiState.value = KioskState.Idle
                performPendingRecorderRestartIfNeeded()
            }
        }
    }

    private fun speakAndShow(text: String) {
        clearLoadingOverlay()
        _uiState.value = KioskState.Speaking(text)
        lastTtsMode = "local"
        tts?.speak(text)
        // Wait for TTS to actually finish playing, with a safety timeout
        viewModelScope.launch {
            delay(500L) // Brief initial delay for AudioTrack to start
            val startTime = System.currentTimeMillis()
            while (tts?.isPlaying() == true && System.currentTimeMillis() - startTime < 30_000L) {
                delay(300L)
            }
            delay(500L) // Brief pause after speech ends
            if (_uiState.value is KioskState.Speaking) {
                _uiState.value = KioskState.Idle
                performPendingRecorderRestartIfNeeded()
            }
            resetInactivityTimer()
        }
    }

    override fun onCleared() {
        super.onCleared()
        cancelInactivityTimer()
        emergencyModeOverlayJob?.cancel()
        emergencyModeReminderJob?.cancel()
        emergencyAlarmPlayer?.release()
        emergencyAlarmPlayer = null
        stt?.release()
        tts?.release()
        _punctuator?.release()
        recorder.release()
    }

    private suspend fun waitForTtsToSettle() {
        tts?.stop()
        val ttsStopDeadline = System.currentTimeMillis() + 1200L
        while (tts?.isPlaying() == true && System.currentTimeMillis() < ttsStopDeadline) {
            delay(40L)
        }
        // Clear recorder pre-buffer and add a short settle window so speaker tail isn't captured.
        recorder.clearPreBuffer()
        delay(220L)
    }

}
