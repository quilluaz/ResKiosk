package com.reskiosk.emergency

/**
 * Tier 1: full-phrase match — high confidence, trigger immediately.
 * Tier 2: single keyword — show confirmation before alerting.
 * Detection runs on both raw and processed transcript.
 */
object EmergencyDetector {

    data class Result(
        val isEmergency: Boolean,
        val tier: Int = 0,  // 1 = full phrase, 2 = keyword
        val triggerPhrase: String? = null
    )

    private val tier1Phrases = setOf(
        "i need immediate emergency help",
        "i cannot breathe", "i am having a heart attack",
        "someone is unconscious", "someone collapsed",
        "i am bleeding badly", "severe bleeding",
        "i need an ambulance", "call for help",
        "there is a fire",
        "necesito ayuda ahora", "no puedo respirar",
        "hay un incendio", "alguien está inconsciente",
        "tasukete kudasai", "kyuukyuu desu", "hi ga deta"
    )

    private val tier2Keywords = setOf(
        "fire", "fuego", "kaji",
        "dying", "muero",
        "unconscious", "inconsciente",
        "emergency", "emergencia", "kyuukyuu",
        "ambulance", "ambulancia"
    )

    private val questionSignals = setOf(
        "where", "what", "how", "where's", "where is",
        "donde", "dónde", "como", "cómo", "que", "qué",
        "wo", "doko", "nani", "desu ka", "?"
    )

    private val informationalMedicalTerms = setOf(
        "doctor", "clinic", "nurse", "medical station",
        "doktor", "clinica", "clínica", "enfermera",
        "isha", "byoin", "byōin", "nurse"
    )

    private val criticalEmergencyTerms = setOf(
        "cannot breathe", "heart attack", "unconscious", "collapsed", "bleeding badly",
        "fire", "ambulance", "dying",
        "no puedo respirar", "inconsciente", "fuego", "ambulancia", "muero",
        "kyuukyuu", "kaji", "tasukete"
    )

    private fun isInformationalMedicalQuestion(text: String): Boolean {
        val hasQuestionSignal = questionSignals.any { text.contains(it) }
        val hasMedicalLookupTerm = informationalMedicalTerms.any { text.contains(it) }
        val hasCriticalTerm = criticalEmergencyTerms.any { text.contains(it) }
        return hasQuestionSignal && hasMedicalLookupTerm && !hasCriticalTerm
    }

    fun detect(processedTranscript: String, rawTranscript: String): Result {
        val p = processedTranscript.lowercase().trim()
        val r = rawTranscript.lowercase().trim()
        val merged = "$p $r"

        // Guard: informational medical/location questions should stay in Q&A unless critical terms exist.
        if (isInformationalMedicalQuestion(merged)) {
            return Result(isEmergency = false)
        }

        for (phrase in tier1Phrases) {
            if (p.contains(phrase) || r.contains(phrase)) {
                return Result(isEmergency = true, tier = 1, triggerPhrase = phrase)
            }
        }
        for (keyword in tier2Keywords) {
            val pattern = Regex("\\b${Regex.escape(keyword)}\\b")
            if (pattern.containsMatchIn(p) || pattern.containsMatchIn(r)) {
                return Result(isEmergency = true, tier = 2, triggerPhrase = keyword)
            }
        }
        return Result(isEmergency = false)
    }
}
