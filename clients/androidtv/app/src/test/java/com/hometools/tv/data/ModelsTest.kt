package com.hometools.tv.data

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * JVM unit tests for JSON deserialisation of the hometools API contract.
 *
 * Verifies that:
 * - The `items` key (not `tracks`/`videos`) is parsed correctly.
 * - Unknown fields are silently ignored (forward-compatible parsing).
 * - Optional fields fall back to their defaults when absent.
 * - Continue-Watching fields (`position_seconds`, `resume_duration`) parse correctly.
 */
class ModelsTest {

    // Use the same lenient config as [ApiClient]
    private val json = Json {
        ignoreUnknownKeys = true
        coerceInputValues = true
    }

    // ── ItemsResponse / `items` key ───────────────────────────────────────────

    @Test
    fun itemsResponse_parsesItemsKey() {
        val raw = """
            {
              "items": [
                { "relative_path": "Series/S01E01.mp4", "title": "Pilot" }
              ],
              "count": 1,
              "artists": []
            }
        """.trimIndent()
        val resp = json.decodeFromString<ItemsResponse>(raw)
        assertEquals(1, resp.items.size)
        assertEquals("Series/S01E01.mp4", resp.items[0].relativePath)
        assertEquals("Pilot", resp.items[0].title)
    }

    @Test
    fun itemsResponse_emptyItemsListWhenAbsent() {
        val raw = """{"count": 0}"""
        val resp = json.decodeFromString<ItemsResponse>(raw)
        assertTrue(resp.items.isEmpty())
    }

    // ── Unknown fields ignored ─────────────────────────────────────────────────

    @Test
    fun mediaItem_unknownFieldsAreIgnored() {
        val raw = """
            {
              "relative_path": "movie.mp4",
              "title": "The Movie",
              "rating": 4,
              "tags": ["action"],
              "new_backend_field_v99": true
            }
        """.trimIndent()
        val item = json.decodeFromString<MediaItem>(raw)
        assertEquals("movie.mp4", item.relativePath)
        assertEquals("The Movie", item.title)
    }

    // ── Default values for optional fields ────────────────────────────────────

    @Test
    fun mediaItem_defaultsAppliedForMissingOptionalFields() {
        val raw = """{ "relative_path": "x.mp4" }"""
        val item = json.decodeFromString<MediaItem>(raw)
        assertEquals("", item.title)
        assertEquals("", item.artist)
        assertEquals("video", item.mediaType)
        assertEquals(0, item.season)
        assertEquals(0, item.episode)
        assertEquals(0.0, item.duration, 0.0)
        assertEquals(0.0, item.introStart, 0.0)
        assertEquals(0.0, item.introEnd, 0.0)
        assertEquals(0.0, item.positionSeconds, 0.0)
        assertEquals(0.0, item.resumeDuration, 0.0)
    }

    // ── Continue-Watching fields ───────────────────────────────────────────────

    @Test
    fun mediaItem_continueWatchingFieldsParsed() {
        val raw = """
            {
              "relative_path": "show/S01E03.mkv",
              "title": "Episode 3",
              "position_seconds": 742.5,
              "resume_duration": 1800.0
            }
        """.trimIndent()
        val item = json.decodeFromString<MediaItem>(raw)
        assertEquals(742.5, item.positionSeconds, 0.001)
        assertEquals(1800.0, item.resumeDuration, 0.001)
    }

    // ── ProgressBody serialisation ─────────────────────────────────────────────

    @Test
    fun progressBody_serialisesCorrectly() {
        val body = ProgressBody(
            relativePath = "series/S01E01.mp4",
            positionSeconds = 123.4,
            duration = 2600.0,
        )
        val encoded = json.encodeToString(ProgressBody.serializer(), body)
        assertTrue(encoded.contains("\"relative_path\""))
        assertTrue(encoded.contains("\"position_seconds\""))
        assertTrue(encoded.contains("123.4"))
    }
}

