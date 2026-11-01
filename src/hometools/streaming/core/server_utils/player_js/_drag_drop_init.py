"""JS fragment: drag drop init (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_drag_drop_init_js() -> str:
    """Return the drag drop init section of the player JS."""
    return """  /* Playlist drag-drop reorder ported to webui/src/playlistDragDrop.ts
     (drag state private there; filteredItems via htState). Wrappers keep
     bare-name call sites; destroyPlaylistDragDrop lives in _smart_playlists.py. */
  function initPlaylistDragDrop() {
    window._initPlaylistDragDrop({ reorder: reorderPlaylistItem });
  }

  /* Playlist modal DOM events ported to webui/src/playlistModalEvents.ts. */
  window._initPlaylistModalEvents({
    enabled: !!PLAYLISTS_ENABLED,
    closeModal: closePlaylistModal,
    createAndAdd: createAndAddToPlaylist
  });

  /* Swipe-right = back ported to webui/src/swipe.ts (state private, installed once). */
  window._initSwipeGestures({ goBack: goBack });

  /* Bootstrap sequence ported to webui/src/bootstrap.ts. */
  window._bootstrapApp({
    loadInitialCatalog: loadInitialCatalog,
    routerInit: function() { _router.init(); },
    loadFavorites: loadFavorites,
    loadUserPlaylists: loadUserPlaylists,
    routerRestore: function() { _router.restore(); },
    showFolderView: showFolderView,
    startPlaylistSync: _startPlaylistSync
  });
}());
"""
