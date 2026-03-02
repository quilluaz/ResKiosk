package com.reskiosk.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.reskiosk.ModelConstants
import com.reskiosk.viewmodel.KioskViewModel
import java.io.File

@Composable
fun SettingsScreen(
    viewModel: KioskViewModel,
    onBack: () -> Unit,
    onOpenSetup: () -> Unit
) {
    val context = LocalContext.current
    val darkModeEnabled by viewModel.darkModeEnabled.collectAsState()
    val modelsDir = File(context.filesDir, ModelConstants.MODELS_BASE_DIR)
    val requiredDirs = remember {
        listOf(
            "English STT" to File(modelsDir, ModelConstants.STT_DIR_BILINGUAL),
            "Japanese STT" to File(modelsDir, ModelConstants.STT_DIR_JA),
            "Whisper STT" to File(modelsDir, ModelConstants.STT_DIR_WHISPER),
            "English Voice" to File(modelsDir, ModelConstants.TTS_DIR_EN),
            "Spanish Voice" to File(modelsDir, ModelConstants.TTS_DIR_ES),
            "German Voice" to File(modelsDir, ModelConstants.TTS_DIR_DE),
            "French Voice" to File(modelsDir, ModelConstants.TTS_DIR_FR),
            "Punctuation" to File(modelsDir, ModelConstants.PUNCTUATION_DIR)
        )
    }

    var checkResult by remember { mutableStateOf<CheckResult?>(null) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Back")
            }
            Spacer(Modifier.width(8.dp))
            Text(
                "Settings",
                style = MaterialTheme.typography.titleLarge,
                color = MaterialTheme.colorScheme.onSurface
            )
        }

        Spacer(Modifier.height(24.dp))

        Text(
            "Appearance",
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(start = 8.dp)
        )
        Spacer(Modifier.height(8.dp))
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 8.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column {
                    Text(
                        "Dark Mode",
                        style = MaterialTheme.typography.titleSmall,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Text(
                        "Use a darker theme for low-light environments.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Switch(
                    checked = darkModeEnabled,
                    onCheckedChange = { viewModel.setDarkModeEnabled(it) }
                )
            }
        }

        Spacer(Modifier.height(24.dp))

        Text(
            "Models & dependencies",
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(start = 8.dp)
        )
        Spacer(Modifier.height(8.dp))
        Text(
            "Check that all models needed to run the kiosk (all 5 languages) are installed. If any are missing, you can download them.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(start = 8.dp, end = 8.dp)
        )
        Spacer(Modifier.height(16.dp))

        Button(
            onClick = {
                val missing = requiredDirs.filter { (_, dir) ->
                    !dir.exists() || (dir.list()?.isEmpty() == true)
                }
                val installed = requiredDirs.filter { (_, dir) ->
                    dir.exists() && (dir.list()?.isNotEmpty() == true)
                }
                checkResult = CheckResult(
                    missing = missing.map { it.first },
                    installed = installed.map { it.first }
                )
            },
            modifier = Modifier.fillMaxWidth(0.9f)
        ) {
            Text("Check models")
        }

        checkResult?.let { result ->
            Spacer(Modifier.height(20.dp))
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 8.dp),
                colors = CardDefaults.cardColors(
                    containerColor = if (result.missing.isEmpty())
                        MaterialTheme.colorScheme.primaryContainer
                    else
                        MaterialTheme.colorScheme.errorContainer
                )
            ) {
                Column(
                    modifier = Modifier
                        .padding(16.dp)
                        .verticalScroll(rememberScrollState())
                ) {
                    if (result.missing.isEmpty()) {
                        Icon(
                            Icons.Default.CheckCircle,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(32.dp)
                        )
                        Spacer(Modifier.height(8.dp))
                        Text(
                            "All required models are installed.",
                            style = MaterialTheme.typography.titleSmall,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                        Spacer(Modifier.height(4.dp))
                        Text(
                            "You can run the kiosk with all 5 languages (English, Spanish, German, French, Japanese).",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                    } else {
                        Icon(
                            Icons.Default.Warning,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.error,
                            modifier = Modifier.size(32.dp)
                        )
                        Spacer(Modifier.height(8.dp))
                        Text(
                            "Missing models (${result.missing.size}):",
                            style = MaterialTheme.typography.titleSmall,
                            color = MaterialTheme.colorScheme.onErrorContainer
                        )
                        Spacer(Modifier.height(4.dp))
                        result.missing.forEach { name ->
                            Text(
                                "• $name",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onErrorContainer
                            )
                        }
                        Spacer(Modifier.height(16.dp))
                        Button(
                            onClick = onOpenSetup,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Download missing models")
                        }
                    }
                }
            }
        }
    }
}

private data class CheckResult(
    val missing: List<String>,
    val installed: List<String>
)
