"""JS fragment: playlists (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_playlists_js() -> str:
    """Return the playlists section of the player JS."""
    return """  /* Load/sync/snapshot ported to webui/src/playlistSync.ts (state via
     htState.userPlaylists/playlistRevision, sync timer private there).
     These thin wrappers keep the bare-name call sites unchanged. */
  function _playlistOpts() {
    return {
      enabled: PLAYLISTS_ENABLED,
      apiPath: PLAYLISTS_API_PATH,
      versionPath: PLAYLISTS_VERSION_PATH,
      intervalMs: _PLAYLIST_SYNC_INTERVAL,
      onRemoteUpdate: function() {
        /* If we're currently looking at the folder view, re-render to show updated playlist cards */
        if (!inPlaylist && currentPath === '') showFolderView();
      }
    };
  }
  function loadUserPlaylists() { return window._loadUserPlaylists(_playlistOpts()); }
  function _startPlaylistSync() { window._startPlaylistSync(_playlistOpts()); }
  function _stopPlaylistSync() { window._stopPlaylistSync(); }
  function _snapshotPlaylists() { return window._snapshotPlaylists(); }
  function _restorePlaylists(snap) { window._restorePlaylists(snap); }
  function updatePlaylistPill() { /* pill removed - no-op */ }

  function _resolvePlaylistItems(plId) {
    /* Logic ported to webui/src/smartPlaylist.ts::resolvePlaylistItems. */
    return window._resolvePlaylistItems(plId, _userPlaylists, allItems, _savedFavorites);
  }

  /* Smart playlist evaluator: ported to webui/src/smartPlaylist.ts,
     bridged onto window (see main.ts) as window._evaluateSmartPlaylist —
     called here with the current allItems/_userPlaylists/_savedFavorites
     since the ported module takes them as explicit parameters instead of
     reading mutable globals (see that file's header comment). */

  /* Refresh smart playlist: re-evaluate locally and re-render. */
  function refreshSmartPlaylist(plId) {
    var pl = _userPlaylists.find(function(p) { return p.id === plId; });
    if (!pl || !pl.smart) return;
    /* If currently viewing this playlist, re-render in place. */
    if (typeof inPlaylist !== 'undefined' && inPlaylist && _currentPlaylistId === plId) {
      var resolved = _evaluateSmartPlaylist(pl, allItems, _userPlaylists, _savedFavorites);
      playlistItems = resolved;
      applyFilter();
      showToast('Aktualisiert: ' + resolved.length + ' Titel');
    } else {
      /* Just refresh the root view to update the count. */
      showFolderView();
      showToast('Intelligente Playlist aktualisiert');
    }
  }

  /* ── Smart Playlist Editor Modal ────────────────────────────────────── */
  /* SMART_FIELDS/SMART_OPS_BY_TYPE/SMART_OPS_ADDED_AT + _smartFieldType()/
     _smartOpsFor()/_smartRenderRuleRow() ported to webui/src/smartPlaylist.ts,
     bridged onto window by main.ts. */


"""
