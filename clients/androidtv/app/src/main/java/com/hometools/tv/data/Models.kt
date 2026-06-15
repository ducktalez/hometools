package com.hometools.tv.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Mirrors the `MediaItem` shape returned by the backend
 * (`/api/video/items`, `/api/video/continue`). Field names match
 * `src/hometools/streaming/core/models.py:MediaItem.to_dict()`.
 *
 * Keep in sync with `clients/shared/openapi/video-openapi.json`. Only the
 * fields the TV app actually uses are declared; unknown fields are ignored
 * by the lenient JSON config in [ApiClient].
 */
@Serializable
data class MediaItem(
    @SerialName("relative_path") val relativePath: String,
    val title: String = "",
    val artist: String = "",
    @SerialName("stream_url") val streamUrl: String = "",
    @SerialName("media_type") val mediaType: String = "video",
    @SerialName("thumbnail_url") val thumbnailUrl: String = "",
    @SerialName("thumbnail_lg_url") val thumbnailLgUrl: String = "",
    val season: Int = 0,
    val episode: Int = 0,
    val duration: Double = 0.0,
    @SerialName("intro_start") val introStart: Double = 0.0,
    @SerialName("intro_end") val introEnd: Double = 0.0,
    // Only present on /api/video/continue:
    @SerialName("position_seconds") val positionSeconds: Double = 0.0,
    @SerialName("resume_duration") val resumeDuration: Double = 0.0,
)

@Serializable
data class ItemsResponse(
    val items: List<MediaItem> = emptyList(),
    val count: Int = 0,
    val artists: List<String> = emptyList(),
)

@Serializable
data class ProgressBody(
    @SerialName("relative_path") val relativePath: String,
    @SerialName("position_seconds") val positionSeconds: Double,
    val duration: Double = 0.0,
)

