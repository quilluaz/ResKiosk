package com.reskiosk.ui

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
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
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.foundation.Image
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.viewmodel.compose.viewModel
import com.reskiosk.ModelConstants
import com.reskiosk.R
import com.reskiosk.emergency.EmergencyStrings
import com.reskiosk.viewmodel.ChatMode
import com.reskiosk.viewmodel.KioskState
import com.reskiosk.viewmodel.KioskViewModel
import kotlinx.coroutines.delay
import java.io.File

private const val PAGE_LANGUAGE = 0
private const val PAGE_MAIN = 1
private const val PAGE_HUB = 2
private const val PAGE_SETTINGS = 3

@Composable
fun MainKioskScreen(viewModel: KioskViewModel = viewModel()) {
    val context = LocalContext.current
    val modelsDir = File(context.filesDir, ModelConstants.MODELS_BASE_DIR)
    val hasModels = remember {
        File(modelsDir, ModelConstants.STT_DIR_BILINGUAL).exists() &&
            File(modelsDir, ModelConstants.STT_DIR_WHISPER).exists() &&
            File(modelsDir, ModelConstants.TTS_DIR_EN).exists()
    }
    var showSetup by remember { mutableStateOf(!hasModels) }
    if (showSetup) {
        SetupScreen(onSetupComplete = { showSetup = false })
        return
    }

    var hasPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) ==
                PackageManager.PERMISSION_GRANTED
        )
    }
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        hasPermission = granted
    }

    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                hasPermission = ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.RECORD_AUDIO
                ) == PackageManager.PERMISSION_GRANTED
                if (!hasPermission) permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    if (!hasPermission) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.padding(32.dp)
            ) {
                Icon(
                    Icons.Default.Warning,
                    contentDescription = null,
                    modifier = Modifier.size(64.dp),
                    tint = MaterialTheme.colorScheme.error
                )
                Spacer(Modifier.height(16.dp))
                Text(
                    text = "Microphone Permission Needed",
                    style = MaterialTheme.typography.headlineMedium,
                    textAlign = TextAlign.Center
                )
                Spacer(Modifier.height(8.dp))
                Text(
                    text = "Please grant microphone access to use the kiosk.",
                    style = MaterialTheme.typography.bodyLarge,
                    textAlign = TextAlign.Center
                )
                Spacer(Modifier.height(24.dp))
                Button(onClick = { permissionLauncher.launch(Manifest.permission.RECORD_AUDIO) }) {
                    Text("Grant Permission")
                }
            }

        }
        return
    }

    MainScreenBody(viewModel = viewModel, onOpenSetup = { showSetup = true })
}

@Composable
private fun MainScreenBody(
    viewModel: KioskViewModel,
    onOpenSetup: () -> Unit
) {
    var showMenu by remember { mutableStateOf(false) }
    var currentScreen by remember { mutableStateOf(PAGE_MAIN) }
    var showEndSessionDialog by remember { mutableStateOf(false) }
    var showSosConfirmDialog by remember { mutableStateOf(false) }

    val uiState by viewModel.uiState.collectAsState()
    val selectedLang by viewModel.selectedLanguage.collectAsState()
    val sessionId by viewModel.sessionId.collectAsState()
    val chatMode by viewModel.chatMode.collectAsState()
    val emergencyCooldownActive by viewModel.emergencyCooldownActive.collectAsState()
    val emergencyModeActive by viewModel.emergencyModeActive.collectAsState()
    val emergencyModeOverlayVisible by viewModel.emergencyModeOverlayVisible.collectAsState()

    val isLoadingOverlay = uiState is KioskState.Transcribing || uiState is KioskState.Processing
    val isListeningBusy = uiState is KioskState.Listening || uiState is KioskState.PreparingToListen
    val isEmergencyState = uiState is KioskState.EmergencyActive ||
        uiState is KioskState.EmergencyAcknowledged ||
        uiState is KioskState.EmergencyPending ||
        uiState is KioskState.EmergencyResponding ||
        uiState is KioskState.EmergencyResolved ||
        uiState is KioskState.EmergencyFailed ||
        uiState is KioskState.EmergencyConfirmation ||
        uiState is KioskState.EmergencyCancelWindow ||
        uiState is KioskState.EmergencyCancelled
    val emergencyBannerInset = if (emergencyModeActive && !emergencyModeOverlayVisible) 44.dp else 0.dp

    Box(modifier = Modifier.fillMaxSize()) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(top = emergencyBannerInset, bottom = emergencyBannerInset)
        ) {
            when (currentScreen) {
                PAGE_MAIN -> MainPage(
                    viewModel = viewModel,
                    showEndSessionDialog = showEndSessionDialog,
                    onShowDialogChange = { showEndSessionDialog = it },
                    onNavigateToHub = { currentScreen = PAGE_HUB }
                )
                PAGE_LANGUAGE -> LanguageScreen(viewModel = viewModel, onBack = { currentScreen = PAGE_MAIN })
                PAGE_HUB -> HubScreen(viewModel = viewModel, onBack = { currentScreen = PAGE_MAIN })
                PAGE_SETTINGS -> SettingsScreen(
                    viewModel = viewModel,
                    onBack = { currentScreen = PAGE_MAIN },
                    onOpenSetup = onOpenSetup
                )
            }
        }

        if (currentScreen == PAGE_MAIN) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(
                        start = 14.dp,
                        end = 14.dp,
                        top = 10.dp + emergencyBannerInset,
                        bottom = 10.dp
                    ),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier.weight(1f),
                    contentAlignment = Alignment.CenterStart
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box {
                            IconButton(onClick = { showMenu = true }, enabled = !isLoadingOverlay) {
                                Icon(
                                    imageVector = Icons.Default.Menu,
                                    contentDescription = "Menu",
                                    modifier = Modifier.size(28.dp),
                                    tint = MaterialTheme.colorScheme.onSurface
                                )
                            }
                            DropdownMenu(
                                expanded = showMenu,
                                onDismissRequest = { showMenu = false }
                            ) {
                                DropdownMenuItem(
                                    text = { Text("Language") },
                                    onClick = {
                                        currentScreen = PAGE_LANGUAGE
                                        showMenu = false
                                    }
                                )
                                DropdownMenuItem(
                                    text = { Text("Hub Connection") },
                                    onClick = {
                                        currentScreen = PAGE_HUB
                                        showMenu = false
                                    }
                                )
                                DropdownMenuItem(
                                    text = { Text("Settings") },
                                    onClick = {
                                        currentScreen = PAGE_SETTINGS
                                        showMenu = false
                                    }
                                )
                            }
                        }
                        Spacer(Modifier.width(6.dp))
                        Surface(
                            shape = RoundedCornerShape(10.dp),
                            color = MaterialTheme.colorScheme.surfaceVariant
                        ) {
                            Text(
                                text = selectedLang.uppercase(),
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }

                Box(
                    modifier = Modifier.weight(1f),
                    contentAlignment = Alignment.Center
                ) {
                    if (sessionId != null && !isEmergencyState) {
                        ChatModeToggle(
                            mode = chatMode,
                            enabled = !isLoadingOverlay && !isListeningBusy,
                            onSelectMode = {
                                viewModel.setChatMode(it)
                                if (it == ChatMode.TEXT_ONLY && isListeningBusy) {
                                    viewModel.stopListening()
                                }
                            }
                        )
                    }
                }

                Box(
                    modifier = Modifier.weight(1f),
                    contentAlignment = Alignment.CenterEnd
                ) {
                    if (sessionId != null) {
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(4.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(width = 44.dp, height = 26.dp)
                                    .clip(RoundedCornerShape(13.dp))
                                    .background(if (emergencyCooldownActive) Color(0xFFBDBDBD) else Color(0xFFB71C1C))
                                    .clickable(
                                        enabled = !isLoadingOverlay && !isEmergencyState && !emergencyCooldownActive
                                    ) {
                                        showSosConfirmDialog = true
                                    },
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = "SOS",
                                    color = Color.White,
                                    fontSize = 10.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                            Box(
                                modifier = Modifier
                                    .size(26.dp)
                                    .clip(CircleShape)
                                    .background(
                                        if (isLoadingOverlay) {
                                            Color(0xFFE8610A).copy(alpha = 0.35f)
                                        } else {
                                            Color(0xFFE8610A).copy(alpha = 0.8f)
                                        }
                                    )
                                    .clickable(enabled = !isLoadingOverlay) { showEndSessionDialog = true },
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Close,
                                    contentDescription = "End Session",
                                    modifier = Modifier.size(14.dp),
                                    tint = Color(0xFFFFB56F)
                                )
                            }
                        }
                    }
                }
            }

        }

        if (emergencyModeActive && !emergencyModeOverlayVisible) {
            EmergencyModeBanners()
        }
        if (emergencyModeOverlayVisible) {
            EmergencyModeActivationOverlay()
        }
    }

    if (showSosConfirmDialog) {
        SosHoldToConfirmDialog(
            language = selectedLang,
            onDismiss = { showSosConfirmDialog = false },
            onConfirmed = {
                showSosConfirmDialog = false
                viewModel.onSosButtonPressed()
            }
        )
    }
}

@Composable
private fun ChatModeToggle(
    mode: ChatMode,
    enabled: Boolean,
    onSelectMode: (ChatMode) -> Unit
) {
    Surface(
        shape = RoundedCornerShape(14.dp),
        color = MaterialTheme.colorScheme.surfaceVariant
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.padding(2.dp)
        ) {
            val voiceSelected = mode == ChatMode.VOICE_ONLY
            val textSelected = mode == ChatMode.TEXT_ONLY
            Box(
                modifier = Modifier
                    .size(30.dp)
                    .clip(CircleShape)
                    .background(if (voiceSelected) Color(0xFFE8610A) else Color.Transparent)
                    .clickable(enabled = enabled) { onSelectMode(ChatMode.VOICE_ONLY) }
                    .padding(6.dp),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Mic,
                    contentDescription = "Voice mode",
                    tint = if (voiceSelected) Color.White else MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(16.dp)
                )
            }
            Box(
                modifier = Modifier
                    .size(30.dp)
                    .clip(CircleShape)
                    .background(if (textSelected) Color(0xFFE8610A) else Color.Transparent)
                    .clickable(enabled = enabled) { onSelectMode(ChatMode.TEXT_ONLY) }
                    .padding(6.dp),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Keyboard,
                    contentDescription = "Text mode",
                    tint = if (textSelected) Color.White else MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(16.dp)
                )
            }
        }
    }
}

@Composable
private fun ChatStreamLoadingOverlay(
    title: String,
    subtitle: String
) {
    val blocker = remember { androidx.compose.foundation.interaction.MutableInteractionSource() }
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.58f))
            .clickable(interactionSource = blocker, indication = null) {},
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            CircularProgressIndicator(
                modifier = Modifier.size(52.dp),
                color = Color(0xFFE8610A),
                strokeWidth = 4.dp
            )
            Spacer(Modifier.height(20.dp))
            Text(
                text = title,
                color = Color.White,
                style = MaterialTheme.typography.headlineSmall,
                textAlign = TextAlign.Center
            )
            Spacer(Modifier.height(8.dp))
            Text(
                text = subtitle,
                color = Color.White.copy(alpha = 0.86f),
                style = MaterialTheme.typography.bodyLarge,
                textAlign = TextAlign.Center
            )
        }
    }
}

@Composable
private fun EmergencyModeActivationOverlay() {
    val blocker = remember { androidx.compose.foundation.interaction.MutableInteractionSource() }
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.72f))
            .clickable(interactionSource = blocker, indication = null) {},
        contentAlignment = Alignment.Center
    ) {
        Surface(
            color = Color(0xFFB71C1C),
            shape = RoundedCornerShape(18.dp),
            modifier = Modifier
                .fillMaxWidth(0.86f)
                .padding(20.dp)
        ) {
            Column(
                modifier = Modifier.padding(horizontal = 22.dp, vertical = 26.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = "Emergency Mode Active",
                    style = MaterialTheme.typography.headlineSmall,
                    color = Color.White,
                    textAlign = TextAlign.Center,
                    fontWeight = FontWeight.Bold
                )
                Spacer(Modifier.height(10.dp))
                Text(
                    text = "Please follow staff instructions.",
                    style = MaterialTheme.typography.bodyLarge,
                    color = Color.White.copy(alpha = 0.95f),
                    textAlign = TextAlign.Center
                )
            }
        }
    }
}

@Composable
private fun EmergencyModeBanners() {
    Column(modifier = Modifier.fillMaxSize()) {
        EmergencyModeBannerStrip()
        Spacer(modifier = Modifier.weight(1f))
        EmergencyModeBannerStrip()
    }
}

@Composable
private fun EmergencyModeBannerStrip() {
    val pulse = rememberInfiniteTransition(label = "emergency_banner_pulse")
    val alpha by pulse.animateFloat(
        initialValue = 0.72f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(900, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "emergency_banner_alpha"
    )
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(44.dp)
            .background(Color(0xFFB71C1C).copy(alpha = alpha)),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = "Emergency Mode Active - Follow staff instructions.",
            color = Color.White,
            style = MaterialTheme.typography.titleSmall,
            fontWeight = FontWeight.SemiBold,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(horizontal = 12.dp)
        )
    }
}

@Composable
private fun SosHoldToConfirmDialog(
    language: String,
    onDismiss: () -> Unit,
    onConfirmed: () -> Unit
) {
    var holding by remember { mutableStateOf(false) }
    var holdProgress by remember { mutableFloatStateOf(0f) }

    LaunchedEffect(holding) {
        if (!holding) {
            if (holdProgress < 1f) holdProgress = 0f
            return@LaunchedEffect
        }
        val start = System.currentTimeMillis()
        while (holding) {
            val elapsed = System.currentTimeMillis() - start
            holdProgress = (elapsed / 3000f).coerceIn(0f, 1f)
            if (holdProgress >= 1f) {
                onConfirmed()
                break
            }
            delay(16L)
        }
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(EmergencyStrings.get("sos_confirm_title", language)) },
        text = {
            Column {
                Text(
                    text = EmergencyStrings.get("sos_confirm_body", language),
                    style = MaterialTheme.typography.bodyMedium
                )
                Spacer(Modifier.height(12.dp))
                Text(
                    text = EmergencyStrings.get("sos_hold_instruction", language),
                    style = MaterialTheme.typography.labelLarge,
                    color = Color(0xFFB71C1C),
                    fontWeight = FontWeight.SemiBold
                )
                Spacer(Modifier.height(12.dp))
                LinearProgressIndicator(
                    progress = holdProgress,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(8.dp),
                    color = Color(0xFFB71C1C),
                    trackColor = Color(0xFFE0E0E0)
                )
                Spacer(Modifier.height(12.dp))
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(54.dp)
                        .clip(RoundedCornerShape(27.dp))
                        .background(Color(0xFFB71C1C))
                        .pointerInput(Unit) {
                            detectTapGestures(
                                onPress = {
                                    holding = true
                                    tryAwaitRelease()
                                    holding = false
                                }
                            )
                        },
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = EmergencyStrings.get("sos_hold_button", language),
                        color = Color.White,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }
        },
        confirmButton = {},
        dismissButton = {
            OutlinedButton(onClick = onDismiss) {
                Text(EmergencyStrings.get("cancel_button", language))
            }
        }
    )
}

@Composable
private fun EmergencyStatePanel(
    backgroundColor: Color,
    panelColor: Color,
    accentColor: Color,
    titleColor: Color,
    bodyColor: Color,
    iconText: String,
    title: String,
    body: String,
    titleFontSize: androidx.compose.ui.unit.TextUnit = 48.sp,
    titleLineHeight: androidx.compose.ui.unit.TextUnit = 50.sp,
    showDismiss: Boolean = false,
    dismissText: String = "",
    onDismiss: (() -> Unit)? = null,
    lightTheme: Boolean = false
) {
    val pulse = rememberInfiniteTransition(label = "emergency_status_pulse")
    val pulseScale by pulse.animateFloat(
        initialValue = 0.95f,
        targetValue = 1.05f,
        animationSpec = infiniteRepeatable(
            animation = tween(1200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "emergency_status_scale"
    )

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(backgroundColor),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier
                .fillMaxWidth(0.86f)
                .background(panelColor, RoundedCornerShape(26.dp))
                .border(1.dp, accentColor.copy(alpha = if (lightTheme) 0.35f else 0.45f), RoundedCornerShape(26.dp))
                .padding(horizontal = 28.dp, vertical = 34.dp)
        ) {
            Box(
                modifier = Modifier
                    .size(76.dp)
                    .scale(pulseScale)
                    .background(accentColor, CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = iconText,
                    color = Color.White,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.ExtraBold
                )
            }
            Spacer(Modifier.height(22.dp))
            Text(
                text = title,
                color = titleColor,
                fontSize = titleFontSize,
                fontWeight = FontWeight.ExtraBold,
                lineHeight = titleLineHeight,
                textAlign = TextAlign.Center
            )
            Spacer(Modifier.height(16.dp))
            Text(
                text = body,
                color = bodyColor,
                fontSize = 24.sp,
                lineHeight = 32.sp,
                textAlign = TextAlign.Center
            )
            if (showDismiss && onDismiss != null) {
                Spacer(Modifier.height(30.dp))
                OutlinedButton(
                    onClick = onDismiss,
                    colors = ButtonDefaults.outlinedButtonColors(
                        containerColor = if (lightTheme) Color.White.copy(alpha = 0.9f) else Color.White.copy(alpha = 0.12f)
                    ),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(64.dp)
                ) {
                    Text(
                        text = dismissText,
                        color = if (lightTheme) Color(0xFF4E342E) else Color.White,
                        fontSize = 26.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }
        }
    }
}

@Composable
private fun MainPage(
    viewModel: KioskViewModel,
    showEndSessionDialog: Boolean,
    onShowDialogChange: (Boolean) -> Unit,
    onNavigateToHub: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()
    val transcript by viewModel.transcript.collectAsState()
    val chatHistory by viewModel.chatHistory.collectAsState()
    val sessionId by viewModel.sessionId.collectAsState()
    val selectedLang by viewModel.selectedLanguage.collectAsState()
    val chatMode by viewModel.chatMode.collectAsState()
    val voiceLevels by viewModel.voiceLevels.collectAsState()
    val hubReachable by viewModel.hubReachable.collectAsState()
    val loadingTitle by viewModel.loadingTitle.collectAsState()
    val loadingSubtitle by viewModel.loadingSubtitle.collectAsState()

    var showNoHubDialog by remember { mutableStateOf(false) }
    var selectedCategory by remember { mutableStateOf<String?>(null) }
    var typedInput by remember { mutableStateOf("") }

    if (sessionId == null) {
        StartSessionHero(
            selectedLang = selectedLang,
            onStart = {
                if (viewModel.getHubUrl().isBlank() || !hubReachable) {
                    showNoHubDialog = true
                } else {
                    viewModel.startSession()
                }
            }
        )
    } else {
        when (val s = uiState) {
            is KioskState.EmergencyConfirmation -> EmergencyConfirmationScreen(
                state = s,
                selectedLang = selectedLang,
                onConfirm = { viewModel.confirmEmergency(s.transcript) },
                onCancel = { viewModel.cancelEmergency() }
            )
            is KioskState.EmergencyCancelWindow -> EmergencyCancelWindowScreen(
                state = s,
                selectedLang = selectedLang,
                onCancel = { viewModel.cancelFalseAlarm() }
            )
            is KioskState.EmergencyPending -> EmergencyPendingScreen(selectedLang = selectedLang)
            is KioskState.EmergencyActive -> EmergencyStatePanel(
                backgroundColor = Color(0xFFB71C1C),
                panelColor = Color(0xFF8A1212),
                accentColor = Color(0xFFE65050),
                titleColor = Color.White,
                bodyColor = Color.White.copy(alpha = 0.92f),
                iconText = "SOS",
                title = EmergencyStrings.get("active_title", selectedLang),
                body = EmergencyStrings.get("active_body", selectedLang),
                showDismiss = true,
                dismissText = EmergencyStrings.get("dismiss", selectedLang),
                onDismiss = { viewModel.dismissEmergency() }
            )
            is KioskState.EmergencyAcknowledged -> EmergencyStatePanel(
                backgroundColor = Color(0xFFD84315),
                panelColor = Color(0xFFB53A12),
                accentColor = Color(0xFFFFB15C),
                titleColor = Color.White,
                bodyColor = Color.White.copy(alpha = 0.92f),
                iconText = "OTW",
                title = EmergencyStrings.get("acknowledged_title", selectedLang),
                body = EmergencyStrings.get("acknowledged_body", selectedLang),
                titleFontSize = 34.sp,
                titleLineHeight = 38.sp
            )
            is KioskState.EmergencyResponding -> EmergencyStatePanel(
                backgroundColor = Color(0xFFFFE8C4),
                panelColor = Color(0xFFF5E6D1),
                accentColor = Color(0xFFD97B2E),
                titleColor = Color(0xFF4E342E),
                bodyColor = Color(0xFF5D4037),
                iconText = "OTW",
                title = EmergencyStrings.get("help_on_the_way", selectedLang),
                body = EmergencyStrings.get("responding_body", selectedLang),
                showDismiss = true,
                dismissText = EmergencyStrings.get("dismiss", selectedLang),
                onDismiss = { viewModel.dismissEmergency() },
                lightTheme = true
            )
            is KioskState.EmergencyResolved -> EmergencyStatePanel(
                backgroundColor = Color(0xFF2E7D32),
                panelColor = Color(0xFF256A2A),
                accentColor = Color(0xFF5EC66B),
                titleColor = Color.White,
                bodyColor = Color.White.copy(alpha = 0.95f),
                iconText = "DONE",
                title = EmergencyStrings.get("resolved_title", selectedLang),
                body = EmergencyStrings.get("resolved_body", selectedLang)
            )
            is KioskState.EmergencyFailed -> EmergencyFailedScreen(state = s, selectedLang = selectedLang)
            is KioskState.EmergencyCancelled -> {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color(0xFFB71C1C)),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "Emergency cancelled",
                        color = Color.White,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
            is KioskState.TerminatingSession -> SessionTerminatingOverlay()
            else -> NormalActiveSessionContent(
                viewModel = viewModel,
                uiState = uiState,
                transcript = transcript,
                chatHistory = chatHistory,
                selectedLang = selectedLang,
                chatMode = chatMode,
                voiceLevels = voiceLevels,
                loadingTitle = if (loadingTitle.isBlank()) EmergencyStrings.get("asking_hub_title_1", selectedLang) else loadingTitle,
                loadingSubtitle = if (loadingSubtitle.isBlank()) EmergencyStrings.get("asking_hub_subtitle", selectedLang) else loadingSubtitle,
                selectedCategory = selectedCategory,
                onSelectedCategoryChange = { selectedCategory = it },
                typedInput = typedInput,
                onTypedInputChange = { typedInput = it }
            )
        }
    }

    if (showEndSessionDialog) {
        AlertDialog(
            onDismissRequest = { onShowDialogChange(false) },
            title = { Text("End Session") },
            text = { Text("This will end your current interaction with ResKiosk and clear the screen.") },
            confirmButton = {
                Button(
                    onClick = {
                        viewModel.endSession()
                        onShowDialogChange(false)
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFD32F2F))
                ) {
                    Text("Confirm")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { onShowDialogChange(false) }) {
                    Text("Back")
                }
            }
        )
    }

    if (showNoHubDialog) {
        AlertDialog(
            onDismissRequest = { showNoHubDialog = false },
            title = { Text("No Hub Connected") },
            text = { Text("Connect this kiosk to a ResKiosk hub to start a session.") },
            confirmButton = {
                Button(
                    onClick = {
                        showNoHubDialog = false
                        onNavigateToHub()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE8610A))
                ) {
                    Text("Connect to Hub")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { showNoHubDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }
}

@Composable
private fun StartSessionHero(
    selectedLang: String,
    onStart: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(start = 28.dp, end = 28.dp, bottom = 10.dp)
            .offset(y = (-10).dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Image(
            painter = painterResource(id = R.drawable.reskiosk_2d_logo),
            contentDescription = "ResKiosk",
            modifier = Modifier
                .fillMaxWidth(0.62f)
                .height(110.dp)
        )
        Spacer(Modifier.height(26.dp))
        Text(
            text = EmergencyStrings.get("start_title", selectedLang),
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center
        )
        Spacer(Modifier.height(10.dp))
        Text(
            text = EmergencyStrings.get("start_subtitle_line_1", selectedLang),
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
            maxLines = 1
        )
        Text(
            text = EmergencyStrings.get("start_subtitle_line_2", selectedLang),
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
            maxLines = 1
        )
        Spacer(Modifier.height(32.dp))
        Button(
            onClick = onStart,
            modifier = Modifier
                .fillMaxWidth(0.72f)
                .height(64.dp),
            shape = RoundedCornerShape(32.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE8610A))
        ) {
            Text(
                text = EmergencyStrings.get("start_button", selectedLang),
                style = MaterialTheme.typography.titleMedium
            )
        }
    }
}

@Composable
private fun EmergencyConfirmationScreen(
    state: KioskState.EmergencyConfirmation,
    selectedLang: String,
    onConfirm: () -> Unit,
    onCancel: () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFB71C1C)),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(48.dp)
        ) {
            Text(
                EmergencyStrings.get("confirm_title", selectedLang),
                color = Color.White,
                fontSize = 26.sp,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center
            )
            Spacer(Modifier.height(12.dp))
            Text(
                "Auto-sending in ${state.remainingSeconds}s",
                color = Color.White.copy(alpha = 0.9f),
                fontSize = 16.sp
            )
            Spacer(Modifier.height(28.dp))
            Button(
                onClick = onConfirm,
                colors = ButtonDefaults.buttonColors(containerColor = Color.White),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(64.dp)
            ) {
                Text(
                    EmergencyStrings.get("confirm_yes", selectedLang),
                    color = Color(0xFFB71C1C),
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold
                )
            }
            Spacer(Modifier.height(16.dp))
            OutlinedButton(
                onClick = onCancel,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp)
            ) {
                Text(EmergencyStrings.get("confirm_no", selectedLang), color = Color.White)
            }
        }
    }
}

@Composable
private fun EmergencyCancelWindowScreen(
    state: KioskState.EmergencyCancelWindow,
    selectedLang: String,
    onCancel: () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFB71C1C)),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(48.dp)
        ) {
            Text(
                text = "Emergency detected",
                color = Color.White,
                fontSize = 26.sp,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center
            )
            Spacer(Modifier.height(12.dp))
            Text(
                text = "Sending alert in ${state.remainingSeconds}s",
                color = Color.White.copy(alpha = 0.9f),
                fontSize = 16.sp
            )
            Spacer(Modifier.height(28.dp))
            Button(
                onClick = onCancel,
                colors = ButtonDefaults.buttonColors(containerColor = Color.White),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(64.dp)
            ) {
                Text(
                    EmergencyStrings.get("cancel_false_alarm", selectedLang),
                    color = Color(0xFFB71C1C),
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center
                )
            }
        }
    }
}

@Composable
private fun EmergencyPendingScreen(selectedLang: String) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFB71C1C)),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            CircularProgressIndicator(color = Color.White, strokeWidth = 4.dp)
            Spacer(Modifier.height(16.dp))
            Text(
                EmergencyStrings.get("sending_alert", selectedLang),
                color = Color.White,
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

@Composable
private fun EmergencyFailedScreen(
    state: KioskState.EmergencyFailed,
    selectedLang: String
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF7F1D1D)),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(48.dp)
        ) {
            Text(
                EmergencyStrings.get("could_not_reach_hub", selectedLang),
                color = Color.White,
                fontSize = 18.sp,
                textAlign = TextAlign.Center
            )
            Spacer(Modifier.height(12.dp))
            val retryText = EmergencyStrings.get("retrying_attempt", selectedLang)
                .replace("{n}", state.retryCount.toString())
                .replace("{max}", "inf")
            Text(retryText, color = Color.White.copy(alpha = 0.85f), fontSize = 14.sp)
        }
    }
}

@Composable
private fun SessionTerminatingOverlay() {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.6f)),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier
                .fillMaxWidth(0.7f)
                .background(Color(0xFF2C2C2C), RoundedCornerShape(20.dp))
                .padding(horizontal = 24.dp, vertical = 28.dp)
        ) {
            CircularProgressIndicator(
                modifier = Modifier.size(36.dp),
                color = Color(0xFFE8610A),
                strokeWidth = 3.dp
            )
            Spacer(Modifier.height(16.dp))
            Text(
                text = "Session ending due to inactivity...",
                style = MaterialTheme.typography.titleMedium,
                color = Color.White,
                textAlign = TextAlign.Center
            )
        }
    }
}

@OptIn(ExperimentalComposeUiApi::class)
@Composable
private fun NormalActiveSessionContent(
    viewModel: KioskViewModel,
    uiState: KioskState,
    transcript: String,
    chatHistory: List<com.reskiosk.viewmodel.ChatMessage>,
    selectedLang: String,
    chatMode: ChatMode,
    voiceLevels: List<Float>,
    loadingTitle: String,
    loadingSubtitle: String,
    selectedCategory: String?,
    onSelectedCategoryChange: (String?) -> Unit,
    typedInput: String,
    onTypedInputChange: (String) -> Unit
) {
    val isVoiceMode = chatMode == ChatMode.VOICE_ONLY
    val isLoadingOverlay = uiState is KioskState.Transcribing || uiState is KioskState.Processing
    val isListening = uiState is KioskState.Listening || uiState is KioskState.PreparingToListen
    val isPreparing = uiState is KioskState.PreparingToListen
    val visibleMessages = if (isVoiceMode) chatHistory.filter { !it.isUser } else chatHistory
    val keyboardController = LocalSoftwareKeyboardController.current
    val focusRequester = remember { FocusRequester() }
    val density = LocalDensity.current
    val isKeyboardVisible = WindowInsets.ime.getBottom(density) > 0

    val listState = rememberLazyListState()
    LaunchedEffect(visibleMessages.size, transcript.length, isListening, uiState, chatMode) {
        val showLive = isVoiceMode && transcript.isNotBlank() && uiState is KioskState.Listening
        val totalItems = visibleMessages.size + if (showLive) 1 else 0
        if (totalItems > 0) listState.animateScrollToItem(totalItems - 1)
    }

    LaunchedEffect(uiState) {
        if (uiState !is KioskState.Clarification) onSelectedCategoryChange(null)
    }

    LaunchedEffect(chatMode, isListening) {
        if (chatMode == ChatMode.VOICE_ONLY) {
            onTypedInputChange("")
            keyboardController?.hide()
        } else if (isListening) {
            viewModel.stopListening()
        } else {
            delay(120L)
            focusRequester.requestFocus()
            keyboardController?.show()
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(top = 60.dp, bottom = 16.dp)
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth(0.9f)
                .fillMaxHeight(0.47f)
                .align(Alignment.TopCenter)
                .background(MaterialTheme.colorScheme.surface, RoundedCornerShape(16.dp))
                .border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(16.dp))
                .padding(12.dp)
        ) {
            if (visibleMessages.isEmpty() && transcript.isBlank()) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    when (val state = uiState) {
                        is KioskState.Error -> Text(
                            text = state.message,
                            color = Color(0xFFD32F2F),
                            style = MaterialTheme.typography.bodyLarge,
                            textAlign = TextAlign.Center
                        )
                        is KioskState.Clarification -> {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Text(state.question, style = MaterialTheme.typography.titleMedium, textAlign = TextAlign.Center)
                                Spacer(Modifier.height(8.dp))
                                state.options.forEach { option ->
                                    Button(
                                        onClick = {
                                            onSelectedCategoryChange(option)
                                            viewModel.selectClarification(option)
                                        },
                                        modifier = Modifier.fillMaxWidth(0.7f).padding(vertical = 4.dp),
                                        enabled = selectedCategory == null
                                    ) {
                                        Text(option)
                                    }
                                }
                            }
                        }
                        else -> {
                            val suggestions by viewModel.faqSuggestions.collectAsState()
                            Column(
                                horizontalAlignment = Alignment.CenterHorizontally,
                                modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp)
                            ) {
                                Text(
                                    text = if (isVoiceMode) {
                                        EmergencyStrings.get("voice_only_hint", selectedLang)
                                    } else {
                                        EmergencyStrings.get("text_only_hint", selectedLang)
                                    },
                                    style = MaterialTheme.typography.bodyLarge,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    textAlign = TextAlign.Center
                                )
                                if (suggestions.isNotEmpty()) {
                                    Spacer(Modifier.height(16.dp))
                                    Text(
                                        text = "Frequently Asked",
                                        style = MaterialTheme.typography.labelMedium,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f)
                                    )
                                    Spacer(Modifier.height(8.dp))
                                    suggestions.forEach { faq ->
                                        OutlinedButton(
                                            onClick = { viewModel.selectFaqSuggestion(faq.question) },
                                            modifier = Modifier
                                                .fillMaxWidth(0.85f)
                                                .padding(vertical = 3.dp),
                                            shape = RoundedCornerShape(20.dp),
                                            border = androidx.compose.foundation.BorderStroke(
                                                1.dp, Color(0xFFE8610A)
                                            )
                                        ) {
                                            Text(
                                                text = faq.question,
                                                color = Color(0xFFE8610A),
                                                maxLines = 2,
                                                overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis,
                                                textAlign = TextAlign.Center,
                                                style = MaterialTheme.typography.bodyMedium
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            } else {
                LazyColumn(
                    state = listState,
                    modifier = Modifier.fillMaxSize(),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    contentPadding = PaddingValues(vertical = 8.dp)
                ) {
                    items(visibleMessages) { msg ->
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = if (msg.isUser) Arrangement.End else Arrangement.Start
                        ) {
                            val userBubbleColor = MaterialTheme.colorScheme.surfaceVariant
                            val assistantBubbleColor = MaterialTheme.colorScheme.primaryContainer
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth(0.82f)
                                    .background(
                                        if (msg.isUser) userBubbleColor else assistantBubbleColor,
                                        RoundedCornerShape(12.dp)
                                    )
                                    .padding(14.dp)
                            ) {
                                Text(
                                    text = msg.text,
                                    style = MaterialTheme.typography.bodyLarge,
                                    color = if (msg.isUser)
                                        MaterialTheme.colorScheme.onSurface
                                    else
                                        MaterialTheme.colorScheme.onPrimaryContainer
                                )
                            }
                        }
                        if (!msg.isUser && msg.sourceId != null && msg.feedbackGiven == null) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(top = 4.dp, start = 4.dp),
                                horizontalArrangement = Arrangement.Start
                            ) {
                                Box(
                                    modifier = Modifier
                                        .border(1.dp, Color(0xFFE8610A), RoundedCornerShape(14.dp))
                                        .clickable { viewModel.sendFeedbackLike(msg.id) }
                                        .padding(horizontal = 14.dp, vertical = 6.dp)
                                ) {
                                    Icon(
                                        imageVector = Icons.Outlined.ThumbUp,
                                        contentDescription = "Helpful",
                                        tint = Color(0xFFE8610A),
                                        modifier = Modifier.size(16.dp)
                                    )
                                }
                                Spacer(Modifier.width(8.dp))
                                Box(
                                    modifier = Modifier
                                        .border(1.dp, Color(0xFFE8610A), RoundedCornerShape(14.dp))
                                        .clickable { viewModel.sendFeedbackDislike(msg.id) }
                                        .padding(horizontal = 14.dp, vertical = 6.dp)
                                ) {
                                    Icon(
                                        imageVector = Icons.Outlined.ThumbDown,
                                        contentDescription = "Not Helpful",
                                        tint = Color(0xFFE8610A),
                                        modifier = Modifier.size(16.dp)
                                    )
                                }
                            }
                        }
                    }

                    if (isVoiceMode && transcript.isNotBlank() && uiState is KioskState.Listening) {
                        item {
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth(0.82f)
                                        .background(Color(0xFFE8E8E8).copy(alpha = 0.65f), RoundedCornerShape(12.dp))
                                        .padding(14.dp)
                                ) {
                                    Text(text = transcript, style = MaterialTheme.typography.bodyLarge, color = Color.DarkGray)
                                }
                            }
                        }
                    }

                    if (uiState is KioskState.Clarification) {
                        val clarification = uiState as KioskState.Clarification
                        item {
                            Column(
                                modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                Text(
                                    clarification.question,
                                    style = MaterialTheme.typography.titleMedium,
                                    textAlign = TextAlign.Center,
                                    color = Color(0xFFE8610A)
                                )
                                Spacer(Modifier.height(8.dp))
                                clarification.options.forEach { option ->
                                    Button(
                                        onClick = {
                                            onSelectedCategoryChange(option)
                                            viewModel.selectClarification(option)
                                        },
                                        modifier = Modifier.fillMaxWidth(0.82f).padding(vertical = 4.dp),
                                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE8610A)),
                                        enabled = selectedCategory == null
                                    ) {
                                        Text(option, textAlign = TextAlign.Center)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            if (isLoadingOverlay) {
                ChatStreamLoadingOverlay(
                    title = loadingTitle,
                    subtitle = loadingSubtitle
                )
            }
        }

        if (isVoiceMode && isListening && !isPreparing) {
            Box(modifier = Modifier.fillMaxSize().background(Color.Black.copy(alpha = 0.34f)))
        }

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.BottomCenter)
                .imePadding()
                .padding(start = 20.dp, top = 0.dp, end = 20.dp, bottom = if (!isVoiceMode && isKeyboardVisible) 12.dp else 8.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            if (!isVoiceMode) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    OutlinedTextField(
                        value = typedInput,
                        onValueChange = onTypedInputChange,
                        modifier = Modifier
                            .weight(1f)
                            .height(58.dp)
                            .focusRequester(focusRequester)
                            .onFocusChanged { if (it.isFocused) keyboardController?.show() },
                        singleLine = true,
                        enabled = !isLoadingOverlay,
                        placeholder = { Text(EmergencyStrings.get("input_placeholder", selectedLang)) },
                        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                        keyboardActions = KeyboardActions(onSend = {
                            val query = typedInput.trim()
                            if (query.isNotBlank()) {
                                viewModel.submitTypedQuery(query)
                                onTypedInputChange("")
                            }
                        }),
                        shape = RoundedCornerShape(16.dp),
                        colors = androidx.compose.material3.OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = Color(0xFFE8610A),
                            unfocusedBorderColor = Color(0xFFE8610A).copy(alpha = 0.72f),
                            focusedContainerColor = Color(0xFF17171B),
                            unfocusedContainerColor = Color(0xFF17171B),
                            cursorColor = Color(0xFFE8610A),
                            focusedTextColor = Color.White,
                            unfocusedTextColor = Color.White,
                            focusedPlaceholderColor = Color(0xFF9A9AA0),
                            unfocusedPlaceholderColor = Color(0xFF9A9AA0)
                        ),
                        textStyle = MaterialTheme.typography.bodyLarge
                    )
                    Button(
                        onClick = {
                            val query = typedInput.trim()
                            if (query.isNotBlank()) {
                                viewModel.submitTypedQuery(query)
                                onTypedInputChange("")
                            }
                        },
                        enabled = !isLoadingOverlay,
                        modifier = Modifier
                            .height(58.dp)
                            .width(104.dp),
                        shape = RoundedCornerShape(28.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE8610A))
                    ) {
                        Text(EmergencyStrings.get("send", selectedLang))
                    }
                }
                Spacer(Modifier.height(if (isKeyboardVisible) 8.dp else 14.dp))
            }

            Box(contentAlignment = Alignment.Center) {
                androidx.compose.animation.AnimatedVisibility(visible = isVoiceMode && isListening && !isPreparing) {
                    VoiceWaveBars(levels = voiceLevels, modifier = Modifier.size(230.dp), color = Color(0xFFE8610A))
                }
                androidx.compose.animation.AnimatedVisibility(visible = isVoiceMode && isListening && !isPreparing) {
                    SonarWave(modifier = Modifier.size(220.dp))
                }
                if (isVoiceMode) {
                    Button(
                        onClick = {
                            if (isListening) viewModel.stopListening() else viewModel.startListening()
                        },
                        modifier = Modifier.size(132.dp),
                        shape = CircleShape,
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE8610A)),
                        contentPadding = PaddingValues(6.dp)
                    ) {
                        if (isPreparing) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(36.dp),
                                color = Color.White,
                                strokeWidth = 3.dp
                            )
                        } else {
                            Text(
                                text = if (uiState is KioskState.Listening) {
                                    EmergencyStrings.get("listening", selectedLang)
                                } else {
                                    "Tap to\nSpeak"
                                },
                                style = MaterialTheme.typography.labelMedium,
                                textAlign = TextAlign.Center,
                                color = Color.White
                            )
                        }
                    }
                }
            }
            Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable
private fun VoiceWaveBars(
    levels: List<Float>,
    modifier: Modifier = Modifier,
    color: Color = Color(0xFFE8610A)
) {
    val smoothedLevels = levels.mapIndexed { index, value ->
        val animated by animateFloatAsState(
            targetValue = value.coerceIn(0f, 1f),
            animationSpec = tween(durationMillis = 90, easing = FastOutSlowInEasing),
            label = "voice_bar_$index"
        )
        animated
    }
    Canvas(modifier = modifier) {
        if (smoothedLevels.isEmpty()) return@Canvas
        val gap = 6f
        val count = smoothedLevels.size
        val barWidth = ((size.width - gap * (count - 1)) / count).coerceAtLeast(3f)
        smoothedLevels.forEachIndexed { index, value ->
            val clamped = value.coerceIn(0f, 1f)
            val minHeight = size.height * 0.14f
            val barHeight = minHeight + ((size.height - minHeight) * clamped)
            val x = index * (barWidth + gap)
            val y = (size.height - barHeight) / 2f
            drawRoundRect(
                color = color.copy(alpha = 0.88f),
                topLeft = Offset(x, y),
                size = Size(barWidth, barHeight),
                cornerRadius = CornerRadius(barWidth / 2f, barWidth / 2f)
            )
        }
    }
}

@Composable
fun SonarWave(modifier: Modifier = Modifier) {
    val primaryColor = Color(0xFFE8610A)
    val transition = rememberInfiniteTransition(label = "sonar")

    val progress1 by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(2000, easing = LinearEasing), RepeatMode.Restart),
        label = "ring1"
    )
    val progress2 by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(2000, delayMillis = 400, easing = LinearEasing), RepeatMode.Restart),
        label = "ring2"
    )
    val progress3 by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(2000, delayMillis = 800, easing = LinearEasing), RepeatMode.Restart),
        label = "ring3"
    )
    val progress4 by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(2000, delayMillis = 1200, easing = LinearEasing), RepeatMode.Restart),
        label = "ring4"
    )
    val progress5 by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(2000, delayMillis = 1600, easing = LinearEasing), RepeatMode.Restart),
        label = "ring5"
    )

    Canvas(modifier = modifier) {
        val center = Offset(size.width / 2f, size.height / 2f)
        val maxRadius = size.minDimension / 2f
        listOf(progress1, progress2, progress3, progress4, progress5).forEach { progress ->
            val radius = maxRadius * progress
            val alpha = (1f - progress) * 0.25f
            drawCircle(
                color = primaryColor,
                radius = radius,
                center = center,
                alpha = alpha
            )
        }
    }
}
