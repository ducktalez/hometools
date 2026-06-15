package com.hometools.tv.ui.theme

import androidx.compose.runtime.Composable
import androidx.tv.material3.MaterialTheme
import androidx.tv.material3.darkColorScheme

/**
 * Dark TV theme matching the hometools web UI accent (#bb86fc / purple).
 * Uses androidx.tv.material3 (Material Design for TV), not the phone Material3.
 */
@Composable
fun HometoolsTvTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(),
        content = content,
    )
}

