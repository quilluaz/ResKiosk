package com.reskiosk.ui

import android.content.Context
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.reskiosk.utils.ModelDownloader
import kotlinx.coroutines.launch
import com.reskiosk.ModelConstants
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.foundation.shape.RoundedCornerShape
import android.util.Log
import java.io.File

@Composable
fun SetupScreen(onSetupComplete: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    
    // Paths (from ModelConstants — single source of truth)
    val modelsDir = File(context.filesDir, ModelConstants.MODELS_BASE_DIR)
    // Only the 5 supported languages (en, ja, es, de, fr) and their dependencies
    val requiredDirs = listOf(
        "English STT" to File(modelsDir, ModelConstants.STT_DIR_BILINGUAL),
        "Japanese STT" to File(modelsDir, ModelConstants.STT_DIR_JA),
        "Whisper STT" to File(modelsDir, ModelConstants.STT_DIR_WHISPER),
        "English Voice" to File(modelsDir, ModelConstants.TTS_DIR_EN),
        "Japanese Voice" to File(modelsDir, ModelConstants.TTS_DIR_JA),
        "Spanish Voice" to File(modelsDir, ModelConstants.TTS_DIR_ES),
        "German Voice" to File(modelsDir, ModelConstants.TTS_DIR_DE),
        "French Voice" to File(modelsDir, ModelConstants.TTS_DIR_FR),
        "Punctuation" to File(modelsDir, ModelConstants.PUNCTUATION_DIR)
    )
    
    var modelsExist by remember { mutableStateOf(requiredDirs.all { (_, dir) -> dir.exists() && (dir.list()?.isNotEmpty() ?: false) }) }
    var downloadProgress by remember { mutableStateOf(0f) }
    var isDownloading by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("Welcome to ResKiosk") }
    
    val downloads = listOf(
        "English STT" to ModelConstants.STT_URL_BILINGUAL,
        "Japanese STT" to ModelConstants.STT_URL_JA,
        "Whisper STT" to ModelConstants.STT_URL_WHISPER,
        "English Voice" to ModelConstants.TTS_URL_EN,
        "Japanese Voice" to ModelConstants.TTS_URL_JA,
        "Spanish Voice" to ModelConstants.TTS_URL_ES,
        "German Voice" to ModelConstants.TTS_URL_DE,
        "French Voice" to ModelConstants.TTS_URL_FR,
        "Punctuation" to ModelConstants.PUNCTUATION_URL
    )

    // Animate displayed progress toward actual progress so the bar moves smoothly
    val animatedProgress by animateFloatAsState(
        targetValue = downloadProgress,
        animationSpec = tween(durationMillis = 400, easing = LinearEasing),
        label = "progress"
    )
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
    ) {
        Text(
            "Setup",
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(start = 4.dp, top = 8.dp)
        )

        Spacer(modifier = Modifier.height(24.dp))

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Text(
                "ResKiosk Setup",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(modifier = Modifier.height(32.dp))

            if (isDownloading) {
                // Status block: step name + status line, constrained width for readable alignment
                Card(
                    modifier = Modifier
                        .fillMaxWidth(0.9f)
                        .padding(horizontal = 16.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
                    )
                ) {
                    Column(
                        modifier = Modifier.padding(20.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = message,
                            style = MaterialTheme.typography.bodyLarge,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }
                Spacer(modifier = Modifier.height(24.dp))

                // Animated progress bar
                Column(modifier = Modifier.fillMaxWidth(0.9f)) {
                    LinearProgressIndicator(
                        progress = animatedProgress,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(8.dp)
                            .clip(RoundedCornerShape(4.dp)),
                        color = MaterialTheme.colorScheme.primary,
                        trackColor = MaterialTheme.colorScheme.surfaceVariant
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(20.dp),
                            strokeWidth = 2.dp,
                            color = MaterialTheme.colorScheme.primary
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            "${(animatedProgress * 100).toInt()}%",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
            } else if (!modelsExist) {
                Text(
                    message,
                    style = MaterialTheme.typography.bodyLarge,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .fillMaxWidth(0.9f)
                        .padding(bottom = 24.dp)
                )
                Button(onClick = {
                    isDownloading = true
                    scope.launch {
                        var allSuccess = true
                        for ((index, item) in downloads.withIndex()) {
                            val (name, url) = item
                            val targetDir = requiredDirs.find { it.first == name }?.second
                            
                            // Incremental check: Skip if directory exists and is not empty
                            if (targetDir != null && targetDir.exists() && (targetDir.list()?.isNotEmpty() ?: false)) {
                                Log.i("SetupScreen", "Skipping $name, already installed.")
                                downloadProgress = (index + 1).toFloat() / downloads.size
                                continue
                            }

                            message = "Setting up $name (${index + 1}/${downloads.size})..."
                            val success = ModelDownloader.downloadAndExtract(
                                context = context,
                                urlString = url,
                                outputDir = modelsDir,
                                onProgress = { prog ->
                                    downloadProgress = (index.toFloat() / downloads.size) + (prog / downloads.size)
                                },
                                onStatus = { status ->
                                    message = "$name: $status"
                                }
                            )
                            if (!success) {
                                message = "$name Download Failed. Check Internet."
                                allSuccess = false
                                break
                            }
                        }
                        if (allSuccess) {
                            message = "Models Ready!"
                            modelsExist = true
                        }
                        isDownloading = false
                    }
                }) {
                    Text(if (requiredDirs.any { (_, dir) -> dir.exists() }) "Resume Setup" else "Download Offline Models")
                }
            } else {
                // Models exist
                Text(
                    "Models Found.",
                    style = MaterialTheme.typography.bodyLarge,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth(0.9f)
                )
                Spacer(modifier = Modifier.height(24.dp))
                Button(onClick = onSetupComplete) {
                    Text("Start Kiosk")
                }
                Spacer(modifier = Modifier.height(16.dp))
                OutlinedButton(onClick = {
                    requiredDirs.forEach { it.second.deleteRecursively() }
                    modelsExist = false
                    message = "Old models cleared. Tap Download to get fresh models."
                }) {
                    Text("Re-download Models")
                }
            }
        }
    }
}
