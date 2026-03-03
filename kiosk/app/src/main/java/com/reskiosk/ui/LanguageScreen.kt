package com.reskiosk.ui

import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.material.icons.Icons
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.reskiosk.viewmodel.KioskViewModel

data class LanguageOption(val displayName: String, val code: String)

private val SUPPORTED_LANGUAGES = listOf(
    LanguageOption("English", "en"),
    LanguageOption("Español", "es"),
    LanguageOption("Deutsch", "de"),
    LanguageOption("Français", "fr"),
    LanguageOption("日本語", "ja"),
)

@Composable
fun LanguageScreen(viewModel: KioskViewModel, onBack: () -> Unit) {
    val selectedLang by viewModel.selectedLanguage.collectAsState()
    val isChangingLanguage by viewModel.isChangingLanguage.collectAsState()

    Box(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
        ) {
            // Top Bar with back + title
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = onBack, enabled = !isChangingLanguage) {
                    Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                }
                Spacer(Modifier.width(8.dp))
                Text(
                    "Language",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold
                )
            }

            // Content area — centered vertically
            Column(
                modifier = Modifier.fillMaxWidth().weight(1f),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Top
            ) {
                Spacer(Modifier.height(24.dp))
                Text(
                    "Select the language you will speak in.",
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center
                )

                Spacer(Modifier.height(24.dp))

                // ─── Vertical pill list ───
                Column(
                    modifier = Modifier.fillMaxWidth(0.75f),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    SUPPORTED_LANGUAGES.forEach { lang ->
                        val isSelected = lang.code == selectedLang
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(50))
                                .background(
                                    if (isSelected) Color(0xFFE8610A) else Color.Transparent
                                )
                                .border(
                                    width = if (isSelected) 2.dp else 1.dp,
                                    color = if (isSelected) Color(0xFFE8610A) else MaterialTheme.colorScheme.outline,
                                    shape = RoundedCornerShape(50)
                                )
                                .clickable(enabled = !isChangingLanguage) {
                                    viewModel.setLanguage(lang.code)
                                }
                                .padding(horizontal = 28.dp, vertical = 14.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                lang.displayName,
                                color = if (isSelected) Color.White else MaterialTheme.colorScheme.onSurface,
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
                            )
                        }
                    }
                }
            }
        }

        // Loading overlay while engines rebuild
        if (isChangingLanguage) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color.Black.copy(alpha = 0.5f)),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    CircularProgressIndicator(color = Color(0xFFE8610A))
                    Spacer(Modifier.height(16.dp))
                    Text(
                        "Changing language, please wait...",
                        color = Color.White,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Medium
                    )
                }
            }
        }
    }
}
