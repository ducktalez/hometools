"""JS fragment: smart playlists (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_smart_playlists_js() -> str:
    """Return the smart playlists section of the player JS."""
    return """  /* Playlist hook wiring (views, CRUD, reorder, picker, smart editor, drag-drop):
     webui/src/playlistWiring.ts. Deps are a thunk, resolved per call. Wrappers
     below keep bare-name call sites. */
  var _plw = window._createPlaylistWiring({
    apiPath: PLAYLISTS_API_PATH,
    smartPath: PLAYLISTS_SMART_PATH,
    smartIcon: IC_SMART_PLAYLIST
  }, function() {
    return {
      toast: showToast,
      esc: escHtml,
      showFolderView: showFolderView,
      applyFilter: applyFilter,
      enterTrackListView: _enterTrackListView,
      playTrack: playTrack,
      sortFavoritesByOrder: _sortFavoritesByOrder,
      loadFavoritesOrder: _loadFavoritesOrder,
      loadFavoritesOrderAsync: _loadFavoritesOrderAsync,
      saveFavoritesOrder: _saveFavoritesOrder,
      saveFolderOrder: _saveFolderOrder,
      renderTracks: renderTracks
    };
  });
  function openSmartPlaylistEditor(existingPl) { _plw.openSmartPlaylistEditor(existingPl); }
  function refreshSmartPlaylist(plId) { _plw.refreshSmartPlaylist(plId); }
  function showUserPlaylistView(plId) { _plw.showUserPlaylistView(plId); }
  function playUserPlaylist(plId) { _plw.playUserPlaylist(plId); }
  function openPlaylistModal(relativePath) { _plw.openPlaylistModal(relativePath); }
  function closePlaylistModal() { _plw.closePlaylistModal(); }
  function openTrackPicker(plId) { _plw.openTrackPicker(plId); }
  function deleteUserPlaylist(plId) { _plw.deleteUserPlaylist(plId); }
  function renameUserPlaylist(plId) { _plw.renameUserPlaylist(plId); }
  function addToPlaylist(plId, relativePath) { _plw.addToPlaylist(plId, relativePath); }
  function createAndAddToPlaylist(name, relativePath) { _plw.createAndAddToPlaylist(name, relativePath); }
  function _isManualPlaylistView() { return _plw.isManualPlaylistView(); }
  function removeFromUserPlaylist(relativePath) { _plw.removeFromUserPlaylist(relativePath); }
  function reorderPlaylistItem(relativePath, toIndex) { _plw.reorderPlaylistItem(relativePath, toIndex); }
  function initPlaylistDragDrop() { _plw.initPlaylistDragDrop(); }
  function destroyPlaylistDragDrop() { _plw.destroyPlaylistDragDrop(); }

"""
