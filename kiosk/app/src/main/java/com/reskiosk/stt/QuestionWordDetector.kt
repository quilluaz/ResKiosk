package com.reskiosk.stt

/**
 * Lexical question-word detector across multiple languages.
 *
 * Checks if the first word of a transcript is a known question starter.
 * This is one of three signals used in the hybrid intonation analysis
 * (along with ZCR acoustic analysis and punctuation model output).
 */
object QuestionWordDetector {

    private val questionStarters = setOf(
        // English
        "what", "where", "when", "who", "how", "why", "is", "are", "can",
        "do", "does", "did", "will", "would", "should", "could", "has", "have",
        // Spanish
        "dónde", "cuándo", "quién", "cómo", "qué", "hay",
        // Japanese (romanized starters that appear in raw transcript)
        "doko", "itsu", "dare", "naze", "dono",
    )

    fun isLikelyQuestion(text: String): Boolean {
        val first = text.lowercase().trim().split(" ").firstOrNull() ?: return false
        return first in questionStarters
    }
}

/**
 * Combined intonation analysis result.
 */
data class IntonationResult(
    val isQuestion: Boolean,
    val confidence: Float   // 0.0 to 1.0
)

/**
 * Combines three signals to determine whether the utterance is a question:
 *   1. Punctuation model output (highest weight: 0.6)
 *   2. Acoustic ZCR rising intonation (0.25)
 *   3. Lexical question-word detection (0.15)
 *
 * Threshold: score >= 0.5 → classified as question.
 */
fun analyzeIntonation(
    rawText: String,
    punctuatedText: String,
    audioSamples: FloatArray
): IntonationResult {
    var score = 0.0f

    // Signal 1 — punctuation model appended a question mark
    if (punctuatedText.trimEnd().endsWith("?")) score += 0.6f

    // Signal 2 — acoustic rising intonation in final 500ms
    if (IntonationDetector.isRisingIntonation(audioSamples)) score += 0.25f

    // Signal 3 — first word is a known question starter
    if (QuestionWordDetector.isLikelyQuestion(rawText)) score += 0.15f

    return IntonationResult(
        isQuestion = score >= 0.5f,
        confidence = score.coerceAtMost(1.0f)
    )
}
