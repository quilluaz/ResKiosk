package com.reskiosk.shared.ui

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import kotlinx.coroutines.delay

private val ResKioskPreviewColors = darkColorScheme(
    primary = Color(0xFFE8610A),
    onPrimary = Color.White,
    primaryContainer = Color(0xFF3A1A08),
    onPrimaryContainer = Color(0xFFFFD7BF),
    secondary = Color(0xFFE8610A),
    onSecondary = Color.White,
    background = Color(0xFF121212),
    onBackground = Color(0xFFF2F2F2),
    surface = Color(0xFF1E1E1E),
    onSurface = Color(0xFFF2F2F2),
    surfaceVariant = Color(0xFF242424),
    onSurfaceVariant = Color(0xFFB0B0B0),
    outline = Color(0xFF4A4A4A),
)

@Composable
fun ResKioskPreviewApp() {
    var state by remember {
        mutableStateOf(
            KioskPreviewState(
                chatHistory = listOf(
                    PreviewChatMessage(false, "Welcome to ResKiosk. Start a session to ask for shelter, supplies, or emergency help.")
                )
            )
        )
    }

    MaterialTheme(colorScheme = ResKioskPreviewColors) {
        Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
            when (state.currentScreen) {
                PreviewScreen.Main -> MainKioskScreen(
                    state = state,
                    onNavigate = { state = state.copy(currentScreen = it) },
                    onStartSession = {
                        state = state.copy(
                            sessionActive = true,
                            chatHistory = listOf(
                                PreviewChatMessage(false, "Session started. The browser preview is using mock STT, TTS, hub, and emergency services.")
                            )
                        )
                    },
                    onEndSession = {
                        state = state.copy(
                            sessionActive = false,
                            uiState = PreviewUiState.Idle,
                            typedInput = "",
                            chatHistory = listOf(PreviewChatMessage(false, "Session ended. Ready for the next visitor."))
                        )
                    },
                    onSetChatMode = { state = state.copy(chatMode = it, uiState = PreviewUiState.Idle) },
                    onTypedInputChange = { state = state.copy(typedInput = it) },
                    onSubmitQuery = { query ->
                        state = state.copy(
                            typedInput = "",
                            uiState = PreviewUiState.Speaking,
                            chatHistory = state.chatHistory + PreviewChatMessage(true, query) + PreviewChatMessage(
                                false,
                                mockAnswerFor(query, state.selectedLanguage)
                            )
                        )
                    },
                    onMicToggle = {
                        state = state.copy(
                            sessionActive = true,
                            uiState = PreviewUiState.Listening,
                            chatHistory = state.chatHistory + PreviewChatMessage(true, "Where is the nearest water station?")
                        )
                    },
                    onSos = {
                        state = state.copy(
                            sessionActive = true,
                            uiState = PreviewUiState.EmergencyPending,
                            emergencyCooldownActive = true,
                            chatHistory = state.chatHistory + PreviewChatMessage(
                                false,
                                "Emergency phrase recognized. Mock alert sent to hub; responders have been notified."
                            )
                        )
                    },
                    onFeedback = { index, liked ->
                        state = state.copy(
                            chatHistory = state.chatHistory.mapIndexed { i, message ->
                                if (i == index) message.copy(feedbackGiven = liked) else message
                            }
                        )
                    },
                )
                PreviewScreen.Language -> LanguageScreen(
                    selectedLanguage = state.selectedLanguage,
                    isChangingLanguage = state.isChangingLanguage,
                    onLanguageSelected = { code ->
                        state = state.copy(selectedLanguage = code, isChangingLanguage = true)
                    },
                    onBack = { state = state.copy(currentScreen = PreviewScreen.Main) },
                )
                PreviewScreen.Hub -> HubSetupScreen(
                    hubState = state.hub,
                    onHubUrlChange = { state = state.copy(hub = state.hub.copy(hubUrl = it)) },
                    onScanQr = {
                        state = state.copy(
                            hub = state.hub.copy(
                                hubUrl = "http://192.168.1.42:8000",
                                connected = true,
                                statusMessage = "Mock QR accepted",
                                keyInfo = "Hub IP: 192.168.1.42\nVersion: preview-1.0\nKiosks Connected: 4",
                            )
                        )
                    },
                    onTestConnection = {
                        state = state.copy(
                            hub = state.hub.copy(
                                connected = true,
                                statusMessage = "Connected successfully!",
                                keyInfo = "Hub IP: ${state.hub.hubUrl.removePrefix("http://")}\nVersion: preview-1.0\nKiosks Connected: 3",
                                diagnosticLog = state.hub.diagnosticLog + "preview handshake ok",
                            )
                        )
                    },
                    onDisconnect = {
                        state = state.copy(
                            hub = HubPreviewState(connected = false, statusMessage = "Disconnected in preview")
                        )
                    },
                    onBack = { state = state.copy(currentScreen = PreviewScreen.Main) },
                )
            }
        }
    }

    LaunchedEffect(state.isChangingLanguage) {
        if (state.isChangingLanguage) {
            delay(450)
            state = state.copy(
                isChangingLanguage = false,
                chatHistory = state.chatHistory + PreviewChatMessage(
                    false,
                    "Language switched to ${languageLabel(state.selectedLanguage)}. Engines are simulated for web."
                )
            )
        }
    }

    LaunchedEffect(state.uiState) {
        if (state.uiState == PreviewUiState.Listening) {
            delay(650)
            state = state.copy(
                uiState = PreviewUiState.Speaking,
                chatHistory = state.chatHistory + PreviewChatMessage(
                    false,
                    mockAnswerFor("Where is the nearest water station?", state.selectedLanguage)
                )
            )
        }
        if (state.uiState == PreviewUiState.EmergencyPending) {
            delay(900)
            state = state.copy(uiState = PreviewUiState.EmergencyAcknowledged)
            delay(1800)
            state = state.copy(uiState = PreviewUiState.Idle, emergencyCooldownActive = false)
        }
    }
}

private fun mockAnswerFor(query: String, language: String): String {
    val base = when {
        query.contains("water", ignoreCase = true) -> "The nearest water station is at Gate B. Staff are refilling containers every 30 minutes."
        query.contains("medicine", ignoreCase = true) -> "Medical support is beside the registration table. Bring your wristband if available."
        query.contains("shelter", ignoreCase = true) -> "Shelter beds are available in Hall 2. Families with children are prioritized near the west wall."
        else -> "I found a matching local KB answer in the sandbox. Please proceed to the information desk for live confirmation."
    }
    return if (language == "en") base else "[$language preview] $base"
}
