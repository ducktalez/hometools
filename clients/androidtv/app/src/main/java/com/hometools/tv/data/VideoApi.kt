package com.hometools.tv.data

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

/**
 * Thin typed client for the **playback subset** of the hometools video API.
 *
 * Deliberately omits all admin endpoints (rating writes, tag edits, move/delete,
 * playlist mutation) — those stay in the web UI. See `clients/README.md`.
 *
 * Contract source: `clients/shared/openapi/video-openapi.json`.
 */
interface VideoApi {

    /** Full catalog (folders/series + episodes). */
    @GET("api/video/items")
    suspend fun items(
        @Query("q") query: String? = null,
        @Query("artist") artist: String? = null,
        @Query("sort") sort: String = "title",
    ): ItemsResponse

    /** Unfinished, recently-played videos for the "Continue Watching" row. */
    @GET("api/video/continue")
    suspend fun continueWatching(@Query("limit") limit: Int = 20): ItemsResponse

    /** Stored resume position for a single file. */
    @GET("api/video/progress")
    suspend fun progress(@Query("path") path: String): ItemsResponse

    /** Persist playback position (called periodically while playing). */
    @POST("api/video/progress")
    suspend fun saveProgress(@Body body: ProgressBody): Map<String, Boolean>
}

