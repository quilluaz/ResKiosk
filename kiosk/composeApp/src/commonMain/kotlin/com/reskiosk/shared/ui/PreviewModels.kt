package com.reskiosk.shared.ui

enum class PreviewScreen {
    Main,
    Language,
    Hub,
}

enum class PreviewChatMode {
    Voice,
    Text,
}

enum class PreviewUiState {
    Idle,
    Preparing,
    Listening,
    Processing,
    Speaking,
    EmergencyPending,
    EmergencyAcknowledged,
}

data class PreviewChatMessage(
    val isUser: Boolean,
    val text: String,
    val feedbackGiven: Boolean? = null,
)

data class LanguageOption(
    val displayName: String,
    val code: String,
)

data class HubPreviewState(
    val hubUrl: String = "http://192.168.1.10:8000",
    val connected: Boolean = true,
    val statusMessage: String = "Sandbox hub ready",
    val keyInfo: String = "Hub IP: 192.168.1.10\nVersion: preview-1.0\nKiosks Connected: 3",
    val diagnosticLog: List<String> = listOf(
        "10:41 AM heartbeat ok",
        "10:42 AM kb_version=1",
        "10:43 AM emergency channel armed",
    ),
)

data class KioskPreviewState(
    val currentScreen: PreviewScreen = PreviewScreen.Main,
    val selectedLanguage: String = "en",
    val isChangingLanguage: Boolean = false,
    val uiState: PreviewUiState = PreviewUiState.Idle,
    val chatMode: PreviewChatMode = PreviewChatMode.Voice,
    val sessionActive: Boolean = false,
    val emergencyCooldownActive: Boolean = false,
    val emergencyModeActive: Boolean = false,
    val typedInput: String = "",
    val loadingTitle: String = "",
    val loadingSubtitle: String = "",
    val chatHistory: List<PreviewChatMessage> = emptyList(),
    val hub: HubPreviewState = HubPreviewState(),
)

val supportedLanguages = listOf(
    LanguageOption("English", "en"),
    LanguageOption("Espanol", "es"),
    LanguageOption("Deutsch", "de"),
    LanguageOption("Francais", "fr"),
    LanguageOption("Japanese", "ja"),
)

fun languageLabel(code: String): String =
    supportedLanguages.firstOrNull { it.code == code }?.displayName ?: code.uppercase()
