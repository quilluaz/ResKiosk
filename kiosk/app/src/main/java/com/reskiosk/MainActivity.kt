package com.reskiosk

import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.reskiosk.ui.MainKioskScreen
import com.reskiosk.ui.SetupScreen
import androidx.lifecycle.viewmodel.compose.viewModel
import com.reskiosk.viewmodel.KioskViewModel
import java.io.File

private val ResKioskLightColorScheme = lightColorScheme(
    primary = Color(0xFFE8610A),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFFFF3EC),
    onPrimaryContainer = Color(0xFF5C2400),
    secondary = Color(0xFFE8610A),
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFFFF3EC),
    onSecondaryContainer = Color(0xFF5C2400),
)

private val ResKioskDarkColorScheme = darkColorScheme(
    primary = Color(0xFFE8610A),
    onPrimary = Color.White,
    primaryContainer = Color(0xFF3A1A08),
    onPrimaryContainer = Color(0xFFFFD7BF),
    secondary = Color(0xFFE8610A),
    onSecondary = Color.White,
    background = Color(0xFF121212),
    onBackground = Color(0xFFF2F2F2),
    surface = Color(0xFF1E1E1E),
    onSurface = Color(0xFFF2F2F2),
    surfaceVariant = Color(0xFF242424),
    onSurfaceVariant = Color(0xFFB0B0B0),
    outline = Color(0xFF2A2A2A)
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // 1. Keep Screen On
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        
        // 2. Immersive Mode (Hide System Bars)
        hideSystemUI()

        setContent {
            val kioskViewModel: KioskViewModel = viewModel()
            val darkModeEnabled by kioskViewModel.darkModeEnabled.collectAsState()
            val colorScheme = if (darkModeEnabled) ResKioskDarkColorScheme else ResKioskLightColorScheme

            MaterialTheme(colorScheme = colorScheme) {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    val modelsDir = File(filesDir, "sherpa-models")
                    val sttDir = File(modelsDir, ModelConstants.STT_DIR_BILINGUAL)
                    val ttsDir = File(modelsDir, ModelConstants.TTS_DIR_EN)

                    var setupComplete by remember { mutableStateOf(sttDir.exists() && ttsDir.exists()) }

                    if (setupComplete) {
                        MainKioskScreen(viewModel = kioskViewModel)
                    } else {
                        SetupScreen(onSetupComplete = { setupComplete = true })
                    }
                }
            }
        }
    }
    
    private fun hideSystemUI() {
        WindowCompat.setDecorFitsSystemWindows(window, false)
        WindowInsetsControllerCompat(window, window.decorView).let { controller ->
            controller.hide(WindowInsetsCompat.Type.systemBars())
            controller.systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        }
    }

    override fun onResume() {
        super.onResume()
        hideSystemUI()
    }
}
