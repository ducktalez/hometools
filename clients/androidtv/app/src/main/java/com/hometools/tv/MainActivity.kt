package com.hometools.tv

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import com.hometools.tv.data.ApiClient
import com.hometools.tv.data.MediaItem
import com.hometools.tv.data.ServerConfig
import com.hometools.tv.ui.BrowseScreen
import com.hometools.tv.ui.PlayerScreen
import com.hometools.tv.ui.ServerSetupScreen
import com.hometools.tv.ui.theme.HometoolsTvTheme

/**
 * Single-activity Compose-for-TV app. Navigation is intentionally minimal
 * (a sealed screen state) — the app has only three screens: server setup,
 * browse, and player. All data comes from the backend REST API.
 */
class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val config = ServerConfig(this)

        setContent {
            HometoolsTvTheme {
                var baseUrl by remember { mutableStateOf(config.baseUrl) }
                var playing by remember { mutableStateOf<MediaItem?>(null) }

                val url = baseUrl
                when {
                    url.isNullOrBlank() -> ServerSetupScreen(
                        onConfirm = { entered ->
                            config.baseUrl = entered
                            baseUrl = entered
                        },
                    )

                    playing != null -> PlayerScreen(
                        api = ApiClient.videoApi(url),
                        streamUrl = ApiClient.streamUrl(url, playing!!),
                        item = playing!!,
                        onExit = { playing = null },
                    )

                    else -> BrowseScreen(
                        baseUrl = url,
                        api = ApiClient.videoApi(url),
                        onPlay = { playing = it },
                    )
                }
            }
        }
    }
}

