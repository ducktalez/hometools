"""JS fragment: folder browse wrappers (logic in webui/src/folderWiring.ts)."""

from __future__ import annotations


def render_folder_browse_js() -> str:
    """Return the folder browse section of the player JS."""
    return """  /* Folder view, lang picker, folder nav, view-entry/header state, folder playlist,
     resume, back, global search: webui/src/folderWiring.ts. State via htState;
     DOM via dom.ts; remaining legacy callbacks via the deps thunk (resolved per call).
     Wrappers keep bare-name call sites. */
  var _fw = window._createFolderWiring({
    itemNoun: ITEM_NOUN, defaultLang: DEFAULT_LANG,
    playlistsEnabled: !!PLAYLISTS_ENABLED, offlineEnabled: !!OFFLINE_ENABLED, recentEnabled: !!RECENT_ENABLED,
    playlistsApiPath: PLAYLISTS_API_PATH, recentApiPath: RECENT_API_PATH,
    icons: {
      smartPlaylist: IC_SMART_PLAYLIST, playlist: IC_PLAYLIST, dl: IC_DL, refresh: IC_REFRESH,
      star: IC_STAR, folderPlay: IC_FOLDER_PLAY, dots: IC_DOTS, edit: IC_EDIT, trash: IC_TRASH
    },
    audiobookDirs: AUDIOBOOK_DIRS, langNames: _LANG_NAME_MAP, langToFlag: LANG_TO_FLAG,
    folderPlaceholder: FOLDER_PLACEHOLDER, filePlaceholder: FILE_PLACEHOLDER,
    originalTitle: originalTitle
  }, function() {
    return {
      esc: escHtml, toast: showToast, toolActive: _anyToolActive, contentsAt: contentsAt,
      loadRecentlyPlayed: loadRecentlyPlayed, openOfflineLibrary: openOfflineLibrary,
      updateOfflineFolderCount: updateOfflineFolderCount, triggerSilentRefresh: _triggerSilentRefresh,
      destroyPlaylistDragDrop: destroyPlaylistDragDrop,
      showUserPlaylistView: showUserPlaylistView, playUserPlaylist: playUserPlaylist,
      openSmartPlaylistEditor: openSmartPlaylistEditor, refreshSmartPlaylist: refreshSmartPlaylist,
      renameUserPlaylist: renameUserPlaylist, deleteUserPlaylist: deleteUserPlaylist,
      loadLastPlayedLocal: _loadLastPlayedLocal,
      sortByFolderOrder: _sortByFolderOrder, refreshFolderRatings: refreshFolderRatings,
      playTrack: playTrack, loadFolderOrderAsync: _loadFolderOrderAsync, loadFolderOrder: _loadFolderOrder,
      applyFilter: applyFilter, applyViewMode: applyViewMode, renderBreadcrumb: renderBreadcrumb,
      routerUpdate: function() { if (typeof _router !== 'undefined') _router.update(); },
      exitGlobalSearch: exitGlobalSearch, globalSearch: globalSearch,
      cleanFolderName: cleanFolderName, markActive: markActive, fmtTime: fmtTime,
      viewMode: function() { return _view.viewMode; },
      compositeFlagHtml: compositeFlagHtml, langBadgesHtml: langBadgesHtml
    };
  });
  function showFolderView() { _fw.showFolderView(); }
  function closeLangPicker() { _fw.closeLangPicker(); }
  function showLangPicker(card, variants, playMode) { _fw.showLangPicker(card, variants, playMode); }
  function navigateInto(name) { _fw.navigateInto(name); }
  function playAllIn(name) { _fw.playAllIn(name); }
  function _applyHeaderState(opts) { _fw.applyHeaderState(opts); }
  function _enterTrackListView(opts) { _fw.enterTrackListView(opts); }
  function _enterFolderGridView(opts) { _fw.enterFolderGridView(opts); }
  function showPlaylist(items, autoplay, startIdx) { _fw.showPlaylist(items, autoplay, startIdx); }
  function _restoreLastEpisode() { _fw.restoreLastEpisode(); }
  function goBack() { _fw.goBack(); }
  function initGlobalSearch() { _fw.initGlobalSearch(); }
  function _hideGlobalSearch() { _fw.hideGlobalSearch(); }
  function _initFilterBarScrollReveal() { _fw.initFilterBarScrollReveal(); }

"""
