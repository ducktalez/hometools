package com.hometools.tv.data

import android.content.Context

/**
 * Persists the backend base URL the user enters on first run
 * (e.g. http://192.168.178.87:8011). No discovery/auth yet — see the
 * "Further Considerations" in docs/IMPLEMENTATION_PLAN.md.
 */
class ServerConfig(context: Context) {
    private val prefs = context.getSharedPreferences("hometools", Context.MODE_PRIVATE)

    var baseUrl: String?
        get() = prefs.getString(KEY_BASE_URL, null)
        set(value) = prefs.edit().putString(KEY_BASE_URL, value).apply()

    fun isConfigured(): Boolean = !baseUrl.isNullOrBlank()

    companion object {
        private const val KEY_BASE_URL = "base_url"
    }
}

