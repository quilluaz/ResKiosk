package com.reskiosk.emergency

/** Pre-translated UI/emergency strings. Falls back to English if key/lang is missing. */
object EmergencyStrings {
    fun get(key: String, lang: String): String =
        strings[lang]?.get(key) ?: strings["en"]!![key] ?: key

    fun getRandom(keyBase: String, count: Int, lang: String): String {
        if (count <= 1) return get(keyBase, lang)
        val idx = (1..count).random()
        return get("${keyBase}_$idx", lang)
    }

    private val en = mapOf(
        "confirm_prompt" to "I heard something urgent. Do you need emergency help right now?",
        "confirm_title" to "Do you need emergency help?",
        "confirm_yes" to "YES - CALL FOR HELP",
        "confirm_no" to "No - cancel",
        "activated" to "Help is on the way. A response team has been notified of your location. Stay where you are. You are not alone.",
        "active_title" to "HELP IS ON THE WAY",
        "active_body" to "A response team has been notified of your location. Stay where you are. You are not alone.",
        "acknowledged_title" to "HELP REQUEST ACKNOWLEDGED",
        "acknowledged_body" to "A staff member has acknowledged your request. Please stay where you are.",
        "resolved_title" to "HELP REQUEST RESOLVED",
        "resolved_body" to "The emergency request was marked resolved. This screen will close shortly.",
        "dismiss" to "Dismiss",
        "sending_alert" to "Sending alert...",
        "help_on_the_way" to "Help is on the way.",
        "responding_body" to "Stay here. Responders are coming.",
        "could_not_reach_hub" to "Could not reach emergency system -- retrying.",
        "retrying_attempt" to "Retrying... attempt {n} of {max}.",
        "cancel_false_alarm" to "Cancel -- not an emergency",
        "listening" to "Listening...",
        "preparing" to "Preparing...",
        "recording_too_short" to "Recording was too short. Please hold the button longer.",
        "didnt_hear" to "I didn't hear anything. Please try again.",
        "didnt_catch" to "I didn't catch that. Please try again.",
        "feedback_inaccurate" to "Response is inaccurate",
        "retrieving_new_response_1" to "Retrieving new response...",
        "retrieving_new_response_2" to "Generating a new response...",
        "retrieving_new_response_3" to "Looking for a better answer...",
        "retrieving_new_response_4" to "Let me try another response...",
        "retrieving_new_response_5" to "Finding a clearer answer...",
        "start_title" to "Welcome to ResKiosk",
        "start_subtitle" to "Ask by voice or type a message. Reze is ready to help.",
        "start_subtitle_line_1" to "Ask by voice or type a message.",
        "start_subtitle_line_2" to "Reze is ready to help.",
        "start_button" to "Start Session",
        "session_start_welcome" to "Hi, I'm Reze. How can I help you today? Tap the button to get started.",
        "mode_voice_only" to "Voice",
        "mode_text_voice" to "Text",
        "keyboard_open" to "Keyboard",
        "input_placeholder" to "Type your question",
        "send" to "Send",
        "voice_only_hint" to "Tap the button below and speak your question.",
        "text_only_hint" to "Use the keyboard below to ask a question.",
        "text_voice_hint" to "Tap speak or open the keyboard to ask a question.",
        "asking_hub_title_1" to "Asking the hub...",
        "asking_hub_title_2" to "Finding the best answer...",
        "asking_hub_title_3" to "Checking shelter information...",
        "asking_hub_title_4" to "Preparing your response...",
        "asking_hub_title_5" to "Almost there...",
        "asking_hub_subtitle" to "Reze will respond soon.",
        "sos_confirm_title" to "Confirm emergency alert",
        "sos_confirm_body" to "Use this only when immediate help is needed.",
        "sos_hold_instruction" to "Press and hold for 3 seconds to send SOS.",
        "sos_hold_button" to "Hold to Send SOS",
        "cancel_button" to "Cancel",
        "session_ending" to "Session ending, thank you for using ResKiosk."
    )

    private val es = en + mapOf(
        "confirm_prompt" to "Escuche algo urgente. Necesitas ayuda de emergencia ahora mismo?",
        "confirm_title" to "Necesitas ayuda de emergencia?",
        "confirm_yes" to "SI - PEDIR AYUDA",
        "confirm_no" to "No - cancelar",
        "active_title" to "LA AYUDA ESTA EN CAMINO",
        "active_body" to "El equipo de respuesta fue notificado. Quedate donde estas. No estas solo.",
        "dismiss" to "Cerrar",
        "help_on_the_way" to "La ayuda esta en camino.",
        "listening" to "Escuchando...",
        "start_title" to "Bienvenido a ResKiosk",
        "start_subtitle" to "Pregunta por voz o escribe un mensaje. Reze esta lista para ayudar.",
        "start_subtitle_line_1" to "Pregunta por voz o escribe un mensaje.",
        "start_subtitle_line_2" to "Reze esta lista para ayudar.",
        "start_button" to "Iniciar sesion",
        "session_start_welcome" to "Hola, soy Reze. Como puedo ayudarte hoy? Toca el boton para comenzar.",
        "mode_voice_only" to "Voz",
        "mode_text_voice" to "Texto",
        "keyboard_open" to "Teclado",
        "input_placeholder" to "Escribe tu pregunta",
        "send" to "Enviar",
        "voice_only_hint" to "Toca el boton y di tu pregunta.",
        "text_only_hint" to "Usa el teclado para hacer una pregunta.",
        "text_voice_hint" to "Toca hablar o abre el teclado para preguntar.",
        "asking_hub_title_1" to "Consultando al hub...",
        "asking_hub_title_2" to "Buscando la mejor respuesta...",
        "asking_hub_title_3" to "Revisando informacion del refugio...",
        "asking_hub_title_4" to "Preparando tu respuesta...",
        "asking_hub_title_5" to "Casi listo...",
        "asking_hub_subtitle" to "Reze respondera pronto...",
        "sos_confirm_title" to "Confirmar alerta de emergencia",
        "sos_confirm_body" to "Usa esto solo cuando necesites ayuda inmediata.",
        "sos_hold_instruction" to "Manten pulsado 3 segundos para enviar SOS.",
        "sos_hold_button" to "Mantener para enviar SOS",
        "cancel_button" to "Cancelar"
    )

    private val de = en + mapOf(
        "start_subtitle_line_1" to "Frage per Sprache oder tippe eine Nachricht.",
        "start_subtitle_line_2" to "Reze ist bereit zu helfen.",
        "session_start_welcome" to "Hallo, ich bin Reze. Wie kann ich dir heute helfen? Tippe auf die Schaltflache, um zu starten.",
        "mode_voice_only" to "Sprache",
        "mode_text_voice" to "Text",
        "text_only_hint" to "Nutze die Tastatur unten fur deine Frage.",
        "keyboard_open" to "Tastatur",
        "send" to "Senden",
        "asking_hub_subtitle" to "Reze antwortet gleich..."
    )

    private val fr = en + mapOf(
        "start_subtitle_line_1" to "Posez votre question a la voix ou par texte.",
        "start_subtitle_line_2" to "Reze est prete a aider.",
        "session_start_welcome" to "Bonjour, je suis Reze. Comment puis-je vous aider aujourd'hui ? Touchez le bouton pour commencer.",
        "mode_voice_only" to "Voix",
        "mode_text_voice" to "Texte",
        "text_only_hint" to "Utilisez le clavier ci-dessous pour poser une question.",
        "keyboard_open" to "Clavier",
        "send" to "Envoyer",
        "asking_hub_subtitle" to "Reze repondra bientot..."
    )

    private val ja = en + mapOf(
        "start_subtitle_line_1" to "Ask by voice or type a message.",
        "start_subtitle_line_2" to "Reze is ready to help.",
        "session_start_welcome" to "こんにちは、Rezeです。今日はどのようにお手伝いできますか？開始するにはボタンを押してください。",
        "mode_voice_only" to "Voice",
        "mode_text_voice" to "Text",
        "text_only_hint" to "Use the keyboard below to ask a question.",
        "asking_hub_subtitle" to "Reze will respond soon."
    )

    private val strings = mapOf(
        "en" to en,
        "es" to es,
        "de" to de,
        "fr" to fr,
        "ja" to ja,
    )
}
