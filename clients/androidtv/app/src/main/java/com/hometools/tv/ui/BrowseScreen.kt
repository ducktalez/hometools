package com.hometools.tv.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.tv.foundation.lazy.list.TvLazyColumn
import androidx.tv.foundation.lazy.list.TvLazyRow
import androidx.tv.foundation.lazy.list.items
import androidx.tv.material3.Card
import androidx.tv.material3.Text
import coil.compose.AsyncImage
import com.hometools.tv.data.ApiClient
import com.hometools.tv.data.MediaItem
import com.hometools.tv.data.VideoApi

/**
 * 10-foot browse screen (Netflix/Jellyfin style): a "Continue Watching" row
 * followed by the catalog. D-pad focus + scrolling are handled by the
 * androidx.tv lazy lists. Read-only — no admin actions.
 */
@Composable
fun BrowseScreen(
    baseUrl: String,
    api: VideoApi,
    onPlay: (MediaItem) -> Unit,
) {
    var continueItems by remember { mutableStateOf<List<MediaItem>>(emptyList()) }
    var catalog by remember { mutableStateOf<List<MediaItem>>(emptyList()) }
    var error by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(baseUrl) {
        runCatching { continueItems = api.continueWatching().items }
            .onFailure { error = it.message }
        runCatching { catalog = api.items().items }
            .onFailure { error = it.message }
    }

    TvLazyColumn(
        modifier = Modifier.fillMaxSize().padding(32.dp),
        verticalArrangement = Arrangement.spacedBy(24.dp),
    ) {
        error?.let { msg ->
            item { Text("Verbindungsfehler: $msg") }
        }
        if (continueItems.isNotEmpty()) {
            item { MediaRow("Weiterschauen", continueItems, baseUrl, onPlay) }
        }
        item { MediaRow("Bibliothek", catalog, baseUrl, onPlay) }
    }
}

@Composable
private fun MediaRow(
    title: String,
    items: List<MediaItem>,
    baseUrl: String,
    onPlay: (MediaItem) -> Unit,
) {
    Column(modifier = Modifier.fillMaxWidth()) {
        Text(text = title, modifier = Modifier.padding(bottom = 12.dp))
        TvLazyRow(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            items(items, key = { it.relativePath }) { item ->
                PosterCard(item, baseUrl, onPlay)
            }
        }
    }
}

@Composable
private fun PosterCard(
    item: MediaItem,
    baseUrl: String,
    onPlay: (MediaItem) -> Unit,
) {
    Card(onClick = { onPlay(item) }, modifier = Modifier.width(220.dp)) {
        Box(contentAlignment = Alignment.BottomStart) {
            val thumb = ApiClient.thumbUrl(baseUrl, item)
            if (thumb != null) {
                AsyncImage(model = thumb, contentDescription = item.title)
            }
            Text(
                text = item.title.ifBlank { item.relativePath },
                modifier = Modifier.padding(8.dp),
            )
        }
    }
}

