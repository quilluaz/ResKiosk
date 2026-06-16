package com.reskiosk.shared

import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.window.ComposeViewport
import com.reskiosk.shared.ui.ResKioskPreviewApp
import kotlinx.browser.document

@OptIn(ExperimentalComposeUiApi::class)
fun main() {
    val target = document.getElementById("compose-target")
        ?: error("Element with id 'compose-target' not found in the DOM")
    ComposeViewport(target) {
        ResKioskPreviewApp()
    }
}
