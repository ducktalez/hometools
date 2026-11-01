"""JS fragment: smart playlists (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_smart_playlists_js() -> str:
    """Return the smart playlists section of the player JS."""
    return """  /* Smart-playlist editor (state, DOM wiring, save) ported to
     webui/src/smartEditor.ts. Wrapper keeps bare-name call sites. */
  function openSmartPlaylistEditor(existingPl) {
    window._openSmartPlaylistEditor(existingPl, {
      apiPath: PLAYLISTS_SMART_PATH,
      esc: escHtml,
      icon: IC_SMART_PLAYLIST,
      toast: showToast,
      showFolderView: showFolderView
    });
  }

  /* Playlist views (browse/play) + add-to-playlist modal ported to
     webui/src/playlistViews.ts (state via htState incl. playlistAddPath).
     Wrappers keep bare-name call sites. */
  function _viewHooks() {
    return {
      toast: showToast,
      esc: escHtml,
      enterTrackListView: _enterTrackListView,
      applyFilter: applyFilter,
      playTrack: playTrack,
      savedFavorites: function() { return _savedFavorites; },
      sortFavoritesByOrder: _sortFavoritesByOrder,
      loadFavoritesOrder: _loadFavoritesOrder,
      loadFavoritesOrderAsync: _loadFavoritesOrderAsync,
      resolvePlaylist: _resolvePlaylistItems,
      addToPlaylist: addToPlaylist
    };
  }
  function showUserPlaylistView(plId) { window._showUserPlaylistView(plId, _viewHooks()); }
  function playUserPlaylist(plId) { window._playUserPlaylist(plId, _viewHooks()); }
  function openPlaylistModal(relativePath) { window._openPlaylistModal(relativePath, _viewHooks()); }
  function closePlaylistModal() { window._closePlaylistModal(); }

  /* Playlist CRUD + optimistic UI ported to webui/src/playlistActions.ts
     (state via htState.userPlaylists). Wrappers keep bare-name call sites. */
  function _playlistHooks() {
    return {
      apiPath: PLAYLISTS_API_PATH,
      toast: showToast,
      refreshRoot: function() { if (!currentPath && !inPlaylist) showFolderView(); },
      closeModal: closePlaylistModal
    };
  }
  function deleteUserPlaylist(plId) { window._deleteUserPlaylist(plId, _playlistHooks()); }
  function renameUserPlaylist(plId) { window._renameUserPlaylist(plId, _playlistHooks()); }
  function addToPlaylist(plId, relativePath) { window._addToPlaylist(plId, relativePath, _playlistHooks()); }
  function createAndAddToPlaylist(name, relativePath) { window._createAndAddToPlaylist(name, relativePath, _playlistHooks()); }
  /* Reorder (drag & drop target) ported to webui/src/playlistReorder.ts
     (state via htState incl. currentPlaylistId). movePlaylistItem had no callers. */
  function reorderPlaylistItem(relativePath, toIndex) {
    window._reorderPlaylistItem(relativePath, toIndex, {
      apiPath: PLAYLISTS_API_PATH,
      toast: showToast,
      renderTracks: renderTracks,
      saveFavoritesOrder: _saveFavoritesOrder,
      saveFolderOrder: _saveFolderOrder
    });
  }
  /* Drag-drop cleanup handle is private to webui/src/playlistDragDrop.ts. */
  function destroyPlaylistDragDrop() { window._destroyPlaylistDragDrop(); }

"""
