package com.hometools.tv.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * JVM unit tests for [ApiClient] helper logic — no Android runtime needed.
 *
 * Covers:
 * - Base URL normalisation (trailing slash)
 * - [ApiClient.streamUrl] / [ApiClient.thumbUrl] URL joining
 * - [ApiClient.thumbUrl] preference of large variant over small
 */
class ApiClientTest {

    // ── streamUrl ─────────────────────────────────────────────────────────────

    @Test
    fun streamUrl_absoluteRelPath_combinedCorrectly() {
        val item = mediaItem(streamUrl = "/video/stream?path=foo/bar.mp4")
        assertEquals(
            "http://192.168.1.1:8011/video/stream?path=foo/bar.mp4",
            ApiClient.streamUrl("http://192.168.1.1:8011", item),
        )
    }

    @Test
    fun streamUrl_baseUrlWithTrailingSlash_noDuplicateSlash() {
        val item = mediaItem(streamUrl = "/video/stream?path=x.mp4")
        val result = ApiClient.streamUrl("http://192.168.1.1:8011/", item)
        assertEquals("http://192.168.1.1:8011/video/stream?path=x.mp4", result)
    }

    @Test
    fun streamUrl_relPathWithoutLeadingSlash_slashInserted() {
        val item = mediaItem(streamUrl = "video/stream?path=x.mp4")
        val result = ApiClient.streamUrl("http://host:8011", item)
        assertEquals("http://host:8011/video/stream?path=x.mp4", result)
    }

    // ── thumbUrl ──────────────────────────────────────────────────────────────

    @Test
    fun thumbUrl_prefersLargeVariant() {
        val item = mediaItem(thumbnailUrl = "/thumb?path=x.jpg", thumbnailLgUrl = "/thumb?path=x.jpg&size=lg")
        assertEquals(
            "http://host:8011/thumb?path=x.jpg&size=lg",
            ApiClient.thumbUrl("http://host:8011", item),
        )
    }

    @Test
    fun thumbUrl_fallsBackToSmallWhenLargeBlank() {
        val item = mediaItem(thumbnailUrl = "/thumb?path=x.jpg", thumbnailLgUrl = "")
        assertEquals(
            "http://host:8011/thumb?path=x.jpg",
            ApiClient.thumbUrl("http://host:8011", item),
        )
    }

    @Test
    fun thumbUrl_returnsNullWhenBothBlank() {
        val item = mediaItem(thumbnailUrl = "", thumbnailLgUrl = "")
        assertNull(ApiClient.thumbUrl("http://host:8011", item))
    }

    // ── helper ────────────────────────────────────────────────────────────────

    private fun mediaItem(
        relativePath: String = "folder/file.mp4",
        streamUrl: String = "",
        thumbnailUrl: String = "",
        thumbnailLgUrl: String = "",
    ) = MediaItem(
        relativePath = relativePath,
        streamUrl = streamUrl,
        thumbnailUrl = thumbnailUrl,
        thumbnailLgUrl = thumbnailLgUrl,
    )
}

