package com.reskiosk.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Divider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.reskiosk.ModelConstants
import com.reskiosk.viewmodel.KioskViewModel
import java.io.File

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    viewModel: KioskViewModel,
    onBack: () -> Unit,
    onOpenSetup: () -> Unit
) {
    val context = LocalContext.current
    val darkModeEnabled by viewModel.darkModeEnabled.collectAsState()
    val scrollState = rememberScrollState()
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

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 16.dp, vertical = 12.dp)
                .verticalScroll(scrollState),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Card(modifier = Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text("Appearance", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        Spacer(Modifier.height(6.dp))
                        Text("Dark mode", style = MaterialTheme.typography.titleSmall)
                        Text(
                            "Use a darker theme for low-light environments.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Spacer(Modifier.width(12.dp))
                    Switch(
                        checked = darkModeEnabled,
                        onCheckedChange = { viewModel.setDarkModeEnabled(it) }
                    )
                }
            }

            Card(modifier = Modifier.fillMaxWidth()) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text("Models & Dependencies", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    Text(
                        "Check required offline models for all supported languages.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )

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
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Check Models")
                    }

                    checkResult?.let { result ->
                        Divider()
                        val allGood = result.missing.isEmpty()

                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = if (allGood) Icons.Default.CheckCircle else Icons.Default.Warning,
                                contentDescription = null,
                                tint = if (allGood) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error
                            )
                            Spacer(Modifier.width(8.dp))
                            Text(
                                text = if (allGood) {
                                    "All required models are installed."
                                } else {
                                    "Missing models: ${result.missing.size}"
                                },
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.SemiBold
                            )
                        }

                        if (!allGood) {
                            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                result.missing.forEach { name ->
                                    Text("- $name", style = MaterialTheme.typography.bodySmall)
                                }
                            }
                            Button(
                                onClick = onOpenSetup,
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text("Download Missing Models")
                            }
                        }
                    }
                }
            }

            Card(modifier = Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    verticalAlignment = Alignment.Top
                ) {
                    Icon(
                        Icons.Default.Info,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary
                    )
                    Spacer(Modifier.width(12.dp))
                    Column {
                        Text("About", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        Spacer(Modifier.height(4.dp))
                        Text(
                            "Build number",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text("1.0.0", style = MaterialTheme.typography.titleSmall)
                    }
                }
            }

            Spacer(Modifier.height(8.dp))
        }
    }
}

private data class CheckResult(
    val missing: List<String>,
    val installed: List<String>
)
