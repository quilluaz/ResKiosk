package com.reskiosk.stt

/**
 * Lightweight acoustic intonation detector using zero-crossing rate (ZCR).
 *
 * Analyzes the final 1000ms of audio by comparing ZCR in two 500ms windows.
 * Rising ZCR in the final window correlates with rising fundamental frequency
 * (F0), which indicates a question in English and most languages.
 *
 * No external model or library required — pure signal processing.
 */
object IntonationDetector {

    /**
     * Analyzes the final 500ms of audio for rising pitch contour.
     * Returns true if the utterance ends with rising intonation (likely a question).
     *
     * Uses zero-crossing rate as a pitch proxy — rises in ZCR correlate with
     * rising fundamental frequency in voiced speech segments.
     */
    fun isRisingIntonation(samples: FloatArray, sampleRate: Int = 16000): Boolean {
        val windowMs = 500
        val windowSize = sampleRate * windowMs / 1000
        if (samples.size < windowSize * 2) return false

        val earlyWindow = samples.copyOfRange(
            samples.size - windowSize * 2,
            samples.size - windowSize
        )
        val lateWindow = samples.copyOfRange(
            samples.size - windowSize,
            samples.size
        )

        val earlyZcr = zeroCrossingRate(earlyWindow)
        val lateZcr = zeroCrossingRate(lateWindow)

        // Rising intonation = ZCR increases in the final window
        // 15% rise threshold — tuned to avoid false positives on trailing breath
        return lateZcr > earlyZcr * 1.15f
    }

    private fun zeroCrossingRate(window: FloatArray): Float {
        var crossings = 0
        for (i in 1 until window.size) {
            if ((window[i] >= 0) != (window[i - 1] >= 0)) crossings++
        }
        return crossings.toFloat() / window.size
    }
}
