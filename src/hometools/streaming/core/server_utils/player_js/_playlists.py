"""JS fragment: playlists (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_playlists_js() -> str:
    """Return the playlists section of the player JS."""
    return """      /* Playlist sync wiring: webui/src/playlistSync.ts::bindPlaylistSync (state in _pb). */
    var _plSync = window._bindPlaylistSync({
      enabled: PLAYLISTS_ENABLED,
      apiPath: PLAYLISTS_API_PATH,
      versionPath: PLAYLISTS_VERSION_PATH,
      intervalMs: _PLAYLIST_SYNC_INTERVAL
    }, function() { showFolderView(); });
    function loadUserPlaylists() { return _plSync.load(); }
    function _startPlaylistSync() { _plSync.start(); }

  /* ── Smart Playlist Editor Modal ────────────────────────────────────── */
  /* SMART_FIELDS/SMART_OPS_BY_TYPE/SMART_OPS_ADDED_AT + _smartFieldType()/
     _smartOpsFor()/_smartRenderRuleRow() ported to webui/src/smartPlaylist.ts,
     bridged onto window by main.ts. */


"""
