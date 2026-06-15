package com.hometools.tv.data

import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory

/**
 * Builds the [VideoApi] for a given backend base URL (e.g. http://192.168.178.87:8011/).
 *
 * The base URL is provided by the user on the first-run server-setup screen and
 * persisted (see [ServerConfig]); there is no auto-discovery yet (planned).
 */
object ApiClient {

    private val json = Json {
        ignoreUnknownKeys = true   // tolerate new backend fields without a client update
        coerceInputValues = true
    }

    fun videoApi(baseUrl: String): VideoApi {
        val normalized = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
        return Retrofit.Builder()
            .baseUrl(normalized)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(VideoApi::class.java)
    }

    /** Absolute URL for the Range-capable video stream of [item]. */
    fun streamUrl(baseUrl: String, item: MediaItem): String =
        joinUrl(baseUrl, item.streamUrl)

    /** Absolute URL for a poster/thumbnail; prefers the large variant. */
    fun thumbUrl(baseUrl: String, item: MediaItem): String? {
        val rel = item.thumbnailLgUrl.ifBlank { item.thumbnailUrl }
        return if (rel.isBlank()) null else joinUrl(baseUrl, rel)
    }

    private fun joinUrl(baseUrl: String, path: String): String {
        val base = baseUrl.trimEnd('/')
        val rel = if (path.startsWith("/")) path else "/$path"
        return "$base$rel"
    }
}

