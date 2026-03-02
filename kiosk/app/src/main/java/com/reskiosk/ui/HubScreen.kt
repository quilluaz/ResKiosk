package com.reskiosk.ui

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.ExitToApp
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions
import com.reskiosk.viewmodel.KioskViewModel
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private enum class HubConnectionMode { NONE, QR, MANUAL }

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HubScreen(viewModel: KioskViewModel, onBack: () -> Unit) {
    val context = LocalContext.current
    val focusManager = LocalFocusManager.current

    // Load saved URL from prefs on first composition
    var savedUrl by remember { mutableStateOf(viewModel.getHubUrl()) }
    val hubReachable by viewModel.hubReachable.collectAsState()
    val hubUrlValidationError by viewModel.hubUrlValidationError.collectAsState()
    val hasSavedUrl = savedUrl.isNotBlank()
    val isConnected = hasSavedUrl && hubReachable

    // Mode for the connection picker (when disconnected or changing)
    var connectionMode by remember { mutableStateOf(HubConnectionMode.NONE) }

    // Refresh timestamp
    var lastRefreshTime by remember { mutableStateOf(System.currentTimeMillis()) }
    var isRefreshing by remember { mutableStateOf(false) }

    // QR Scanner launcher
    val scanLauncher = rememberLauncherForActivityResult(ScanContract()) { result ->
        result.contents?.let { scannedUrl ->
            if (viewModel.saveHubUrl(scannedUrl)) {
                savedUrl = viewModel.getHubUrl()
                connectionMode = HubConnectionMode.NONE
                viewModel.refreshHubConnectionStatus()
            }
        }
    }

    // Camera permission launcher
    val cameraPermissionLauncher = rememberLauncherForActivityResult(
        androidx.activity.result.contract.ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            scanLauncher.launch(ScanOptions().apply {
                setDesiredBarcodeFormats(ScanOptions.QR_CODE)
                setPrompt("Point at the Hub QR code")
                setBeepEnabled(false)
                setBarcodeImageEnabled(false)
                setOrientationLocked(true)
                setCaptureActivity(PortraitCaptureActivity::class.java)
            })
        }
    }

    fun launchQrScan() {
        val hasCameraPermission = ContextCompat.checkSelfPermission(
            context, Manifest.permission.CAMERA
        ) == PackageManager.PERMISSION_GRANTED
        if (hasCameraPermission) {
            scanLauncher.launch(ScanOptions().apply {
                setDesiredBarcodeFormats(ScanOptions.QR_CODE)
                setPrompt("Point at the Hub QR code")
                setBeepEnabled(false)
                setBarcodeImageEnabled(false)
                setOrientationLocked(true)
                setCaptureActivity(PortraitCaptureActivity::class.java)
            })
        } else {
            cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        // Top Bar with back + title
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Back")
            }
            Spacer(Modifier.width(8.dp))
            Text(
                "Hub Connection",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold
            )
        }
        
        // Content centered
        Column(
            modifier = Modifier.fillMaxWidth().weight(1f),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Top
        ) {
        Spacer(Modifier.height(24.dp))

        if (isConnected && connectionMode == HubConnectionMode.NONE) {
            // ─── Connected state ───
            ConnectedCard()

            Spacer(Modifier.height(16.dp))

            // Connection details
            Column(
                modifier = Modifier.fillMaxWidth(0.9f),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                DetailRow("IP Address", savedUrl.replace("http://", "").replace("https://", ""))
                DetailRow("Status", if (isRefreshing) "Refreshing..." else "Connected")
                DetailRow("Last Seen", SimpleDateFormat("hh:mm a", Locale.getDefault()).format(Date(lastRefreshTime)))
            }

            Spacer(Modifier.height(24.dp))

            // Action buttons side by side
            Row(
                modifier = Modifier.fillMaxWidth(0.9f),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Refresh button — orange outlined
                OutlinedButton(
                    onClick = {
                        isRefreshing = true
                        viewModel.refreshHubConnectionStatus { _ ->
                            lastRefreshTime = System.currentTimeMillis()
                            savedUrl = viewModel.getHubUrl()
                            isRefreshing = false
                        }
                    },
                    modifier = Modifier.weight(1f).height(48.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFFE8610A)),
                    border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFE8610A))
                ) {
                    Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("Refresh", maxLines = 1)
                }

                // Disconnect button — filled orange
                Button(
                    onClick = {
                        viewModel.disconnectHub()
                        savedUrl = ""
                    },
                    modifier = Modifier.weight(1f).height(48.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE8610A))
                ) {
                    Icon(Icons.Default.ExitToApp, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("Disconnect", maxLines = 1)
                }
            }
        } else if (!isConnected && connectionMode == HubConnectionMode.NONE) {
            if (hasSavedUrl) {
                // ─── Saved URL but not reachable ───
                DisconnectedCard(
                    title = if (hubUrlValidationError != null) "Invalid URL" else "Not reachable"
                )

                Spacer(Modifier.height(16.dp))

                Column(
                    modifier = Modifier.fillMaxWidth(0.9f),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    DetailRow("IP Address", savedUrl.replace("http://", "").replace("https://", ""))
                    DetailRow(
                        "Status",
                        if (isRefreshing) "Refreshing..." else if (hubUrlValidationError != null) "Invalid URL" else "Not reachable"
                    )
                    DetailRow("Last Seen", SimpleDateFormat("hh:mm a", Locale.getDefault()).format(Date(lastRefreshTime)))
                }
                if (hubUrlValidationError != null) {
                    Spacer(Modifier.height(8.dp))
                    Text(
                        text = hubUrlValidationError ?: "",
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.fillMaxWidth(0.9f),
                        textAlign = TextAlign.Center
                    )
                }

                Spacer(Modifier.height(24.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(0.9f),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    OutlinedButton(
                        onClick = {
                            isRefreshing = true
                            viewModel.refreshHubConnectionStatus { _ ->
                                lastRefreshTime = System.currentTimeMillis()
                                savedUrl = viewModel.getHubUrl()
                                isRefreshing = false
                            }
                        },
                        modifier = Modifier.weight(1f).height(48.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFFE8610A)),
                        border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFE8610A))
                    ) {
                        Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(6.dp))
                        Text("Refresh", maxLines = 1)
                    }

                    Button(
                        onClick = {
                            viewModel.disconnectHub()
                            savedUrl = ""
                        },
                        modifier = Modifier.weight(1f).height(48.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE8610A))
                    ) {
                        Icon(Icons.Default.ExitToApp, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(6.dp))
                        Text("Disconnect", maxLines = 1)
                    }
                }
            } else {
                // ─── Disconnected: Show Picker ───
                ConnectionPicker(
                    onQr = { launchQrScan() },
                    onManual = { connectionMode = HubConnectionMode.MANUAL }
                )
            }
        }

        // ─── Manual URL entry (Main Screen) ───
        AnimatedVisibility(
            visible = connectionMode == HubConnectionMode.MANUAL,
            enter = slideInVertically() + fadeIn(),
            exit = slideOutVertically() + fadeOut()
        ) {
            ManualUrlEntry(
                initialUrl = savedUrl,
                validationError = hubUrlValidationError,
                onSave = { url ->
                    if (viewModel.saveHubUrl(url)) {
                        savedUrl = viewModel.getHubUrl()
                        connectionMode = HubConnectionMode.NONE
                        focusManager.clearFocus()
                        viewModel.refreshHubConnectionStatus()
                    }
                },
                onCancel = {
                    viewModel.clearHubUrlValidationError()
                    connectionMode = HubConnectionMode.NONE
                },
                onEdit = { viewModel.clearHubUrlValidationError() }
            )
        }
    }
    }
}

@Composable
private fun DetailRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            label,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Text(
            value,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.Medium
        )
    }
}

@Composable
private fun ConnectedCard() {
    Card(
        modifier = Modifier.fillMaxWidth(0.9f),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(24.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center
        ) {
            Icon(
                Icons.Default.CheckCircle,
                contentDescription = null,
                tint = Color(0xFF4CAF50),
                modifier = Modifier.size(28.dp)
            )
            Spacer(Modifier.width(8.dp))
            Text(
                "Connected",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF4CAF50)
            )
        }
    }
}

@Composable
private fun DisconnectedCard(title: String) {
    Card(
        modifier = Modifier.fillMaxWidth(0.9f),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(24.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center
        ) {
            Icon(
                Icons.Default.Warning,
                contentDescription = null,
                tint = Color(0xFFE8610A),
                modifier = Modifier.size(28.dp)
            )
            Spacer(Modifier.width(8.dp))
            Text(
                title,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface
            )
        }
    }
}

@Composable
private fun ConnectionPicker(onQr: () -> Unit, onManual: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxWidth(0.75f),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // QR Scan button
        Button(
            onClick = onQr,
            modifier = Modifier.fillMaxWidth().height(60.dp),
            shape = RoundedCornerShape(12.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE8610A))
        ) {
            Icon(Icons.Default.Search, contentDescription = null, modifier = Modifier.size(24.dp))
            Spacer(Modifier.width(12.dp))
            Text("Scan QR Code", style = MaterialTheme.typography.titleMedium)
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Divider(modifier = Modifier.weight(1f))
            Text("  or  ", color = MaterialTheme.colorScheme.onSurfaceVariant)
            Divider(modifier = Modifier.weight(1f))
        }

        // Manual entry button
        OutlinedButton(
            onClick = onManual,
            modifier = Modifier.fillMaxWidth().height(60.dp),
            shape = RoundedCornerShape(12.dp)
        ) {
            Icon(Icons.Default.Edit, contentDescription = null, modifier = Modifier.size(20.dp))
            Spacer(Modifier.width(12.dp))
            Text("Enter URL Manually", style = MaterialTheme.typography.titleMedium)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ManualUrlEntry(
    initialUrl: String,
    validationError: String?,
    onSave: (String) -> Unit,
    onCancel: () -> Unit,
    onEdit: () -> Unit,
) {
    var urlText by remember { mutableStateOf(initialUrl) }

    Column(
        modifier = Modifier.fillMaxWidth(0.75f).padding(top = 8.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text("Hub URL", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
        OutlinedTextField(
            value = urlText,
            onValueChange = {
                urlText = it
                onEdit()
            },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("e.g. http://192.168.1.x:8000") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(
                keyboardType = KeyboardType.Uri,
                imeAction = ImeAction.Done
            ),
            keyboardActions = KeyboardActions(
                onDone = { if (urlText.isNotBlank()) onSave(urlText) }
            ),
            shape = RoundedCornerShape(12.dp)
        )
        if (!validationError.isNullOrBlank()) {
            Text(
                text = validationError,
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodySmall,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth()
            )
        }
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            OutlinedButton(onClick = onCancel, modifier = Modifier.weight(1f)) {
                Text("Cancel")
            }
            Button(
                onClick = { if (urlText.isNotBlank()) onSave(urlText) },
                modifier = Modifier.weight(1f),
                enabled = urlText.isNotBlank(),
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE8610A))
            ) {
                Text("Save")
            }
        }
    }
}
