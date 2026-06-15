package com.hometools.tv.ui

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.common.MediaItem as ExoMediaItem
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import com.hometools.tv.data.MediaItem
import com.hometools.tv.data.ProgressBody
import com.hometools.tv.data.VideoApi
import kotlinx.coroutines.delay

/**
 * Full-screen Media3/ExoPlayer surface.
 *
 * ExoPlayer plays MP4/MKV/AVI with HTTP Range directly from `/video/stream`,
 * which is why the native TV app handles formats the TV browser cannot.
 *
 * Resume: seeks to the stored position on start, then persists progress every
 * ~10 s and on exit via `POST /api/video/progress`.
 */
@Composable
fun PlayerScreen(
    api: VideoApi,
    streamUrl: String,
    item: MediaItem,
    onExit: () -> Unit,
) {
    val context = LocalContext.current
    val player = remember {
        ExoPlayer.Builder(context).build().apply {
            setMediaItem(ExoMediaItem.fromUri(streamUrl))
            prepare()
            playWhenReady = true
        }
    }

    // Seek to the stored resume position once metadata is ready.
    LaunchedEffect(item.relativePath) {
        val stored = runCatching { api.progress(item.relativePath).items.firstOrNull() }.getOrNull()
        val pos = stored?.positionSeconds ?: item.positionSeconds
        if (pos > 1.0) player.seekTo((pos * 1000).toLong())
    }

    // Persist progress periodically while playing.
    LaunchedEffect(item.relativePath) {
        while (true) {
            delay(10_000)
            val posSec = player.currentPosition / 1000.0
            val durSec = (player.duration.coerceAtLeast(0)) / 1000.0
            runCatching {
                api.saveProgress(ProgressBody(item.relativePath, posSec, durSec))
            }
        }
    }

    DisposableEffect(Unit) {
        onDispose {
            // Best-effort final progress save happens via the periodic loop;
            // release the player to free the codec.
            player.release()
        }
    }

    AndroidView(
        modifier = Modifier.fillMaxSize(),
        factory = { ctx ->
            PlayerView(ctx).apply {
                this.player = player
                useController = true
                setShowNextButton(false)
                setShowPreviousButton(false)
            }
        },
    )
}

