package com.reskiosk.shared.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp

@Composable
fun HubSetupScreen(
    hubState: HubPreviewState,
    onHubUrlChange: (String) -> Unit,
    onScanQr: () -> Unit,
    onTestConnection: () -> Unit,
    onDisconnect: () -> Unit,
    onBack: () -> Unit,
) {
    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Back")
            }
            Spacer(Modifier.width(8.dp))
            Text("Hub Connection", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        }

        Column(
            modifier = Modifier.fillMaxWidth().padding(top = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            HubStatusCard(hubState)
            OutlinedTextField(
                value = hubState.hubUrl,
                onValueChange = onHubUrlChange,
                label = { Text("Hub URL") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(0.82f),
            )
            Row(modifier = Modifier.fillMaxWidth(0.82f), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedButton(onClick = onScanQr, modifier = Modifier.weight(1f).height(48.dp)) {
                    Icon(Icons.Default.Edit, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("Scan QR")
                }
                Button(
                    onClick = onTestConnection,
                    modifier = Modifier.weight(1f).height(48.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE8610A)),
                ) {
                    Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("Test")
                }
            }
            OutlinedButton(onClick = onDisconnect, modifier = Modifier.fillMaxWidth(0.82f).height(48.dp)) {
                Text("Disconnect")
            }
            DiagnosticsLog(hubState.diagnosticLog)
        }
    }
}

@Composable
private fun HubStatusCard(hubState: HubPreviewState) {
    Card(
        modifier = Modifier.fillMaxWidth(0.82f),
        colors = CardDefaults.cardColors(
            containerColor = if (hubState.connected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant
        ),
    ) {
        Column(modifier = Modifier.padding(18.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(
                if (hubState.connected) Icons.Default.CheckCircle else Icons.Default.Warning,
                contentDescription = null,
                tint = if (hubState.connected) Color(0xFF4CAF50) else Color(0xFFE8610A),
                modifier = Modifier.size(28.dp),
            )
            Spacer(Modifier.height(8.dp))
            Text(hubState.statusMessage, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(8.dp))
            Text(hubState.keyInfo, color = MaterialTheme.colorScheme.onSurfaceVariant, textAlign = TextAlign.Center)
        }
    }
}

@Composable
private fun DiagnosticsLog(logs: List<String>) {
    Card(modifier = Modifier.fillMaxWidth(0.82f), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Diagnostics", fontWeight = FontWeight.Bold)
            logs.takeLast(5).forEach {
                Text(it, maxLines = 1, overflow = TextOverflow.Ellipsis, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}
