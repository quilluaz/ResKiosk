package com.reskiosk.audio

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.media.audiofx.NoiseSuppressor
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class AudioRecorder {
    private val sampleRate = 16000
    private val channelConfig = AudioFormat.CHANNEL_IN_MONO
    private val audioFormat = AudioFormat.ENCODING_PCM_16BIT
    private val minBufferSize = AudioRecord.getMinBufferSize(sampleRate, channelConfig, audioFormat) * 4

    private var recorder: AudioRecord? = null
    
    // Continuous background listening job
    private var listeningJob: Job? = null
    
    // Noise suppression: disabled for batch/Whisper languages (es, de, fr) to avoid OEM suppression of non-English speech
    @Volatile private var useNoiseSuppression = true

    // State flag
    @Volatile private var isActivelyRecordingForStt = false
    
    // Callback to push data to STT
    @Volatile private var activeCallback: ((FloatArray) -> Unit)? = null

    // Rolling ring buffer to hold the last ~1500ms of audio (24000 floats at 16kHz)
    // Extra 0.5s over the previous 1.0s ensures no leading audio is lost
    // even on slower devices where tap→record latency can be 100-200ms
    private val ringBufferSize = 24000
    private val ringBuffer = FloatArray(ringBufferSize)
    private var ringBufferIndex = 0

    /** Add samples to the rolling buffer */
    private fun appendToRingBuffer(samples: FloatArray) {
        for (sample in samples) {
            ringBuffer[ringBufferIndex] = sample
            ringBufferIndex = (ringBufferIndex + 1) % ringBufferSize
        }
    }

    /** 
     * Get the contents of the ring buffer linearly, oldest to newest.
     * This represents the audio captured *just before* the user tapped the button.
     */
    private fun dumpRingBuffer(): FloatArray {
        val result = FloatArray(ringBufferSize)
        var i = ringBufferIndex
        var j = 0
        while (j < ringBufferSize) {
            result[j] = ringBuffer[i]
            i = (i + 1) % ringBufferSize
            j++
        }
        return result
    }
    
    /** Clear the ring buffer to silence */
    private fun clearRingBuffer() {
        for (i in ringBuffer.indices) {
            ringBuffer[i] = 0f
        }
        ringBufferIndex = 0
    }

    /**
     * Clear the pre-buffer (ring buffer) so that the next startRecording() does not
     * include previously captured audio (e.g. TTS bleed). Call this after stopping TTS
     * and before startRecording() to avoid recording speaker output.
     */
    fun clearPreBuffer() {
        clearRingBuffer()
    }

    /**
     * Enable or disable hardware noise suppression. When false, NoiseSuppressor is not
     * attached to the AudioRecord session. Call before startContinuousListening() or
     * restart the continuous session (stop then start) for the change to take effect.
     */
    fun setNoiseSuppressionEnabled(enabled: Boolean) {
        useNoiseSuppression = enabled
    }

    /**
     * Starts continuous background listening. This keeps the AudioRecord HAL open and actively
     * reading data into our rolling ring buffer. This completely eliminates hardware startup latency
     * and captures the speech *before* the user's tap registers.
     */
    @SuppressLint("MissingPermission")
    fun startContinuousListening(coroutineScope: CoroutineScope) {
        if (listeningJob?.isActive == true) return // Already running

        listeningJob = coroutineScope.launch(Dispatchers.IO) {
            try {
                if (recorder == null || recorder?.state != AudioRecord.STATE_INITIALIZED) {
                    recorder?.release()
                    recorder = AudioRecord(
                        MediaRecorder.AudioSource.VOICE_RECOGNITION,
                        sampleRate,
                        channelConfig,
                        audioFormat,
                        minBufferSize
                    )
                }

                val rec = recorder
                if (rec == null || rec.state != AudioRecord.STATE_INITIALIZED) {
                    Log.e("AudioRecorder", "Failed to initialize AudioRecord for continuous listening")
                    recorder = null
                    return@launch
                }

                if (useNoiseSuppression) {
                    try {
                        val ns = NoiseSuppressor.create(rec.audioSessionId)
                        if (ns != null) {
                            ns.enabled = true
                            Log.i("AudioRecorder", "Hardware NoiseSuppressor enabled on sessionId ${rec.audioSessionId}")
                        } else {
                            Log.w("AudioRecorder", "NoiseSuppressor not available on this device")
                        }
                    } catch (e: Exception) {
                        Log.e("AudioRecorder", "Failed to initialize NoiseSuppressor", e)
                    }
                } else {
                    Log.i("AudioRecorder", "NoiseSuppressor disabled (batch/Whisper language)")
                }

                Log.i("AudioRecorder", "Started continuous background listening (ring buffer active)")
                rec.startRecording()
                clearRingBuffer()

                val buffer = ShortArray(2048)
                
                while (isActive) {
                    if (rec.recordingState != AudioRecord.RECORDSTATE_RECORDING) {
                        break
                    }
                    
                    val read = rec.read(buffer, 0, buffer.size)
                    if (read > 0) {
                        // Convert Short to Float [-1.0, 1.0]
                        val floats = FloatArray(read)
                        for (i in 0 until read) {
                            floats[i] = buffer[i] / 32768.0f
                        }
                        
                        if (isActivelyRecordingForStt) {
                            activeCallback?.invoke(floats)
                        } else {
                            // Keep updating the ring buffer
                            appendToRingBuffer(floats)
                        }
                    }
                }
            } catch (e: Exception) {
                Log.e("AudioRecorder", "Continuous listening loop crashed", e)
            } finally {
                try {
                    recorder?.stop()
                } catch (e: Exception) {}
            }
        }
    }

    /**
     * Stop the continuous listening loop and release the AudioRecord session.
     * Call before startContinuousListening() again to apply a new NS setting (e.g. after language change).
     */
    fun stopContinuousListening() {
        isActivelyRecordingForStt = false
        activeCallback = null
        listeningJob?.cancel()
        listeningJob = null
        try {
            if (recorder?.recordingState == AudioRecord.RECORDSTATE_RECORDING) {
                recorder?.stop()
            }
            recorder?.release()
        } catch (e: Exception) { /* ignore */ }
        recorder = null
    }

    /**
     * Instantly switch the continuous listener to "active STT mode".
     * It will immediately flush the ring buffer (look-back) to the callback and stream live data.
     */
    fun startRecording(onData: (FloatArray) -> Unit) {
        // We capture the callback. The background loop will notice isActivelyRecordingForStt = true,
        // dump the ring buffer to it ONCE, and then pipe all subsequent live data to it.
        // To ensure the ring buffer is only dumped ONCE per session, we use a wrapper callback.
        
        var ringBufferDumped = false
        
        activeCallback = { chunk ->
            if (!ringBufferDumped) {
                val preBuffer = dumpRingBuffer()
                clearRingBuffer()
                Log.i("AudioRecorder", "Dumped ${preBuffer.size} samples from pre-buffer")
                onData(preBuffer)
                ringBufferDumped = true
            }
            onData(chunk)
        }
        
        isActivelyRecordingForStt = true
    }

    /**
     * Stop active STT piping, but KEEP the background loop running to fill the ring buffer.
     */
    fun stopRecording() {
        isActivelyRecordingForStt = false
        activeCallback = null
    }

    /** 
     * Completely shut down audio hardware and background loop (call on ViewModel clear).
     */
    fun release() {
        isActivelyRecordingForStt = false
        activeCallback = null
        listeningJob?.cancel()
        listeningJob = null
        
        try {
            if (recorder?.recordingState == AudioRecord.RECORDSTATE_RECORDING) {
                recorder?.stop()
            }
            recorder?.release()
        } catch (e: Exception) {}
        recorder = null
    }
}
