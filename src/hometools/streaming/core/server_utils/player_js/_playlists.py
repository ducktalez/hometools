"""JS fragment: playlists (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_playlists_js() -> str:
    """Return the playlists section of the player JS."""
    return """  function loadUserPlaylists() {
    if (!PLAYLISTS_ENABLED) return Promise.resolve([]);
    return fetch(PLAYLISTS_API_PATH).then(function(r) { return r.json(); })
      .then(function(d) {
        _userPlaylists = d.items || [];
        if (typeof d.revision === 'number') _playlistRevision = d.revision;
        updatePlaylistPill();
        return _userPlaylists;
      })
      .catch(function() { return []; });
  }

  function _startPlaylistSync() {
    if (!PLAYLISTS_ENABLED) return;
    _stopPlaylistSync();
    _playlistSyncTimer = setInterval(_pollPlaylistVersion, _PLAYLIST_SYNC_INTERVAL);
    /* Pause when tab hidden, resume when visible */
    document.addEventListener('visibilitychange', _onPlaylistVisibility);
  }
  function _stopPlaylistSync() {
    if (_playlistSyncTimer) { clearInterval(_playlistSyncTimer); _playlistSyncTimer = null; }
  }
  function _onPlaylistVisibility() {
    if (document.hidden) {
      _stopPlaylistSync();
    } else {
      /* Resume polling and do an immediate check */
      _stopPlaylistSync();
      _pollPlaylistVersion();
      _playlistSyncTimer = setInterval(_pollPlaylistVersion, _PLAYLIST_SYNC_INTERVAL);
    }
  }
  function _pollPlaylistVersion() {
    fetch(PLAYLISTS_VERSION_PATH).then(function(r) { return r.json(); })
      .then(function(d) {
        if (typeof d.revision === 'number' && d.revision > _playlistRevision) {
          loadUserPlaylists().then(function() {
            /* If we're currently looking at the folder view, re-render to show updated playlist cards */
            if (!inPlaylist && currentPath === '') showFolderView();
          });
        }
      }).catch(function() { /* offline — ignore */ });
  }

  function updatePlaylistPill() { /* pill removed — no-op */ }

  /* ── optimistic UI helpers ── */
  function _snapshotPlaylists() {
    return JSON.parse(JSON.stringify(_userPlaylists));
  }
  function _restorePlaylists(snap) {
    _userPlaylists = snap;
    updatePlaylistPill();
  }

  /* ── playlist library panel (removed — playlists as pseudo-folders) ── */
  function openPlaylistLibrary() { /* removed */ }
  function closePlaylistLibrary() { /* removed */ }
  function renderPlaylistLibrary() { /* removed */ }

  function _resolvePlaylistItems(plId) {
    var pl = _userPlaylists.find(function(p) { return p.id === plId; });
    if (!pl) return null;
    /* Smart playlist: evaluate rules against allItems. */
    if (pl.smart && pl.smart.rules) {
      var resolvedSmart = _evaluateSmartPlaylist(pl, allItems, _userPlaylists, _savedFavorites);
      if (!resolvedSmart || resolvedSmart.length === 0) return null;
      return { pl: pl, resolved: resolvedSmart };
    }
    if (!pl.items || pl.items.length === 0) return null;
    var resolved = [];
    pl.items.forEach(function(rp) {
      var match = allItems.find(function(it) { return it.relative_path === rp; });
      if (match) resolved.push(match);
    });
    if (resolved.length === 0) return null;
    return { pl: pl, resolved: resolved };
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

  var _smartEditorState = null;

"""
