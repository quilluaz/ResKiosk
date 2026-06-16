package com.reskiosk.shared.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Keyboard
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material.icons.outlined.ThumbDown
import androidx.compose.material.icons.outlined.ThumbUp
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun MainKioskScreen(
    state: KioskPreviewState,
    onNavigate: (PreviewScreen) -> Unit,
    onStartSession: () -> Unit,
    onEndSession: () -> Unit,
    onSetChatMode: (PreviewChatMode) -> Unit,
    onTypedInputChange: (String) -> Unit,
    onSubmitQuery: (String) -> Unit,
    onMicToggle: () -> Unit,
    onSos: () -> Unit,
    onFeedback: (Int, Boolean) -> Unit,
) {
    var showMenu by remember { mutableStateOf(false) }

    Box(modifier = Modifier.fillMaxSize()) {
        Column(modifier = Modifier.fillMaxSize().padding(18.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box {
                        IconButton(onClick = { showMenu = true }) {
                            Icon(Icons.Default.Menu, contentDescription = "Menu")
                        }
                        DropdownMenu(expanded = showMenu, onDismissRequest = { showMenu = false }) {
                            DropdownMenuItem(
                                text = { Text("Language") },
                                onClick = {
                                    showMenu = false
                                    onNavigate(PreviewScreen.Language)
                                }
                            )
                            DropdownMenuItem(
                                text = { Text("Hub Connection") },
                                onClick = {
                                    showMenu = false
                                    onNavigate(PreviewScreen.Hub)
                                }
                            )
                        }
                    }
                    LanguagePill(state.selectedLanguage)
                }

                ChatModeToggle(state.chatMode, state.sessionActive, onSetChatMode)

                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Button(
                        onClick = onSos,
                        enabled = state.sessionActive && !state.emergencyCooldownActive,
                        shape = RoundedCornerShape(16.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFB71C1C)),
                        contentPadding = PaddingValues(horizontal = 14.dp, vertical = 8.dp),
                    ) {
                        Text("SOS", fontWeight = FontWeight.Bold)
                    }
                    IconButton(onClick = onEndSession, enabled = state.sessionActive) {
                        Icon(Icons.Default.Close, contentDescription = "End Session", tint = Color(0xFFFFB56F))
                    }
                }
            }

            Spacer(Modifier.height(14.dp))

            if (state.emergencyModeActive || state.uiState == PreviewUiState.EmergencyPending || state.uiState == PreviewUiState.EmergencyAcknowledged) {
                EmergencyStatePanel(state.uiState)
                Spacer(Modifier.height(12.dp))
            }

            if (!state.sessionActive) {
                StartSessionHero(onStartSession)
            } else {
                ActiveSessionContent(
                    state = state,
                    onTypedInputChange = onTypedInputChange,
                    onSubmitQuery = onSubmitQuery,
                    onMicToggle = onMicToggle,
                    onFeedback = onFeedback,
                )
            }
        }
    }
}

@Composable
private fun LanguagePill(code: String) {
    Surface(shape = RoundedCornerShape(10.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
        Text(
            text = code.uppercase(),
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun ChatModeToggle(
    mode: PreviewChatMode,
    enabled: Boolean,
    onSelectMode: (PreviewChatMode) -> Unit,
) {
    Surface(shape = RoundedCornerShape(14.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
        Row(modifier = Modifier.padding(2.dp), verticalAlignment = Alignment.CenterVertically) {
            ToggleIcon(
                selected = mode == PreviewChatMode.Voice,
                enabled = enabled,
                onClick = { onSelectMode(PreviewChatMode.Voice) },
            ) {
                Icon(Icons.Default.Mic, contentDescription = "Voice", modifier = Modifier.size(17.dp))
            }
            ToggleIcon(
                selected = mode == PreviewChatMode.Text,
                enabled = enabled,
                onClick = { onSelectMode(PreviewChatMode.Text) },
            ) {
                Icon(Icons.Default.Keyboard, contentDescription = "Text", modifier = Modifier.size(17.dp))
            }
        }
    }
}

@Composable
private fun ToggleIcon(selected: Boolean, enabled: Boolean, onClick: () -> Unit, content: @Composable () -> Unit) {
    Box(
        modifier = Modifier
            .size(30.dp)
            .clip(CircleShape)
            .background(if (selected) Color(0xFFE8610A) else Color.Transparent)
            .clickable(enabled = enabled, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        content()
    }
}

@Composable
internal fun StartSessionHero(onStartSession: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().padding(horizontal = 24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Box(
            modifier = Modifier.size(118.dp).clip(CircleShape).background(Color(0xFFE8610A)),
            contentAlignment = Alignment.Center,
        ) {
            Text("R", color = Color.White, fontSize = 58.sp, fontWeight = FontWeight.Black)
        }
        Spacer(Modifier.height(24.dp))
        Text("ResKiosk", style = MaterialTheme.typography.displaySmall, fontWeight = FontWeight.Bold)
        Text(
            "Static browser showcase with simulated voice, language, emergency, and hub flows.",
            modifier = Modifier.fillMaxWidth(0.72f).padding(top = 8.dp),
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(28.dp))
        Button(
            onClick = onStartSession,
            shape = RoundedCornerShape(28.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE8610A)),
            modifier = Modifier.height(56.dp).width(220.dp),
        ) {
            Text("Start Session", fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
internal fun ActiveSessionContent(
    state: KioskPreviewState,
    onTypedInputChange: (String) -> Unit,
    onSubmitQuery: (String) -> Unit,
    onMicToggle: () -> Unit,
    onFeedback: (Int, Boolean) -> Unit,
) {
    Column(modifier = Modifier.fillMaxSize()) {
        LazyColumn(
            modifier = Modifier.weight(1f).fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(10.dp),
            contentPadding = PaddingValues(vertical = 8.dp),
        ) {
            items(state.chatHistory.size) { index ->
                val msg = state.chatHistory[index]
                ChatBubble(index, msg, onFeedback)
            }
        }

        if (state.chatMode == PreviewChatMode.Text) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                OutlinedTextField(
                    value = state.typedInput,
                    onValueChange = onTypedInputChange,
                    modifier = Modifier.weight(1f).height(58.dp),
                    singleLine = true,
                    placeholder = { Text("Ask about shelter, water, medicine...") },
                    shape = RoundedCornerShape(16.dp),
                )
                Button(
                    onClick = { if (state.typedInput.isNotBlank()) onSubmitQuery(state.typedInput.trim()) },
                    modifier = Modifier.height(58.dp).width(104.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE8610A)),
                    shape = RoundedCornerShape(28.dp),
                ) {
                    Text("Send")
                }
            }
        } else {
            Box(modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp), contentAlignment = Alignment.Center) {
                Button(
                    onClick = onMicToggle,
                    modifier = Modifier.size(132.dp),
                    shape = CircleShape,
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE8610A)),
                    contentPadding = PaddingValues(0.dp),
                ) {
                    if (state.uiState == PreviewUiState.Listening) {
                        CircularProgressIndicator(modifier = Modifier.size(32.dp), color = Color.White, strokeWidth = 3.dp)
                    } else {
                        Icon(Icons.Default.Mic, contentDescription = "Speak", tint = Color.White, modifier = Modifier.size(42.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun ChatBubble(index: Int, msg: PreviewChatMessage, onFeedback: (Int, Boolean) -> Unit) {
    Column(horizontalAlignment = if (msg.isUser) Alignment.End else Alignment.Start, modifier = Modifier.fillMaxWidth()) {
        Box(
            modifier = Modifier
                .fillMaxWidth(0.82f)
                .background(
                    if (msg.isUser) MaterialTheme.colorScheme.surfaceVariant else MaterialTheme.colorScheme.primaryContainer,
                    RoundedCornerShape(12.dp)
                )
                .padding(14.dp),
        ) {
            Text(
                msg.text,
                color = if (msg.isUser) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onPrimaryContainer,
            )
        }
        if (!msg.isUser) {
            Row(modifier = Modifier.padding(top = 4.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { onFeedback(index, true) }, enabled = msg.feedbackGiven == null) {
                    Icon(Icons.Outlined.ThumbUp, contentDescription = "Helpful", modifier = Modifier.size(16.dp))
                }
                OutlinedButton(onClick = { onFeedback(index, false) }, enabled = msg.feedbackGiven == null) {
                    Icon(Icons.Outlined.ThumbDown, contentDescription = "Not helpful", modifier = Modifier.size(16.dp))
                }
            }
        }
    }
}

@Composable
internal fun EmergencyStatePanel(uiState: PreviewUiState) {
    val text = when (uiState) {
        PreviewUiState.EmergencyPending -> "Emergency alert pending..."
        PreviewUiState.EmergencyAcknowledged -> "Emergency acknowledged. Help is on the way."
        else -> "Emergency mode active"
    }
    Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF4A0808)), modifier = Modifier.fillMaxWidth()) {
        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.Warning, contentDescription = null, tint = Color(0xFFFFB56F))
            Spacer(Modifier.width(10.dp))
            Text(text, color = Color.White, fontWeight = FontWeight.Bold)
        }
    }
}
