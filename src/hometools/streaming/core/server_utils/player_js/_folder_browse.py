"""JS fragment: folder browse (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_folder_browse_js() -> str:
    """Return the folder browse section of the player JS."""
    return """  /* showFolderView (folder grid, root cards, card wiring) + playlist-card kebab:
     webui/src/folderView.ts. State via htState; DOM/config/actions via hooks. */
  function _folderViewHooks() {
    return {
      folderGrid: folderGrid, itemNoun: ITEM_NOUN, defaultLang: DEFAULT_LANG,
      playlistsEnabled: !!PLAYLISTS_ENABLED, offlineEnabled: !!OFFLINE_ENABLED, recentEnabled: !!RECENT_ENABLED,
      playlistsApiPath: PLAYLISTS_API_PATH,
      icons: {
        smartPlaylist: IC_SMART_PLAYLIST, playlist: IC_PLAYLIST, dl: IC_DL, refresh: IC_REFRESH,
        star: IC_STAR, folderPlay: IC_FOLDER_PLAY, dots: IC_DOTS, edit: IC_EDIT, trash: IC_TRASH
      },
      esc: escHtml, toast: showToast,
      cardOpts: function(showOrigNames) {
        return {
          escHtml: escHtml, viewMode: _view.viewMode, showOrigNames: showOrigNames, isVideo: ITEM_NOUN === 'video',
          itemNoun: ITEM_NOUN, defaultLang: DEFAULT_LANG, audiobookDirs: AUDIOBOOK_DIRS,
          langNames: _LANG_NAME_MAP, folderPlaceholder: FOLDER_PLACEHOLDER, filePlaceholder: FILE_PLACEHOLDER,
          icStar: IC_STAR, icFolderPlay: IC_FOLDER_PLAY,
          compositeFlagHtml: compositeFlagHtml, langBadgesHtml: langBadgesHtml
        };
      },
      toolActive: _anyToolActive,
      contentsAt: contentsAt,
      destroyPlaylistDragDrop: destroyPlaylistDragDrop,
      enterFolderGridView: _enterFolderGridView,
      showPlaylist: showPlaylist,
      loadRecentlyPlayed: loadRecentlyPlayed,
      openOfflineLibrary: openOfflineLibrary,
      updateOfflineFolderCount: updateOfflineFolderCount,
      showUserPlaylistView: showUserPlaylistView,
      playUserPlaylist: playUserPlaylist,
      openSmartPlaylistEditor: openSmartPlaylistEditor,
      refreshSmartPlaylist: refreshSmartPlaylist,
      renameUserPlaylist: renameUserPlaylist,
      deleteUserPlaylist: deleteUserPlaylist,
      navigateInto: navigateInto,
      playAllIn: playAllIn,
      showLangPicker: showLangPicker,
      triggerSilentRefresh: _triggerSilentRefresh
    };
  }
  function showFolderView() { window._showFolderView(_folderViewHooks()); }
  /* ── Language picker for multi-language folders ── */
  /* Picker (private cleanup state) ported to webui/src/folderBrowseUi.ts. */
  function closeLangPicker() { window._closeLangPicker(); }
  function showLangPicker(card, variants, playMode) {
    window._showLangPicker(card, variants, playMode, {
      esc: escHtml,
      itemNoun: ITEM_NOUN,
      langToFlag: LANG_TO_FLAG,
      langNames: _LANG_NAME_MAP,
      cleanFolderName: cleanFolderName,
      playAllIn: playAllIn,
      navigateInto: navigateInto
    });
  }
  /* navigateInto/playAllIn ported to webui/src/playAll.ts (currentPath via htState). */
  function _folderNavHooks() {
    return {
      showFolderView: showFolderView,
      triggerSilentRefresh: _triggerSilentRefresh,
      loadLastPlayedLocal: _loadLastPlayedLocal,
      showPlaylist: showPlaylist
    };
  }
  function navigateInto(name) { window._navigateInto(name, _folderNavHooks()); }
  function playAllIn(name) { window._playAllIn(name, _folderNavHooks()); }

  /* ── Shared track-list view entry point ───────────────────────────────
     Consolidates the header/toolbar DOM state that every "flat list of
     tracks" view must set up identically (folder-leaf playlist, user
     playlist, favorites, "Titel", smart playlist, duplicates) — see
     docs/IMPLEMENTATION_PLAN.md "UI-Template-Vereinheitlichung" Phase 2.
     Before this refactor each of the ~5 call sites (spread across
     _folder_browse.py/_smart_playlists.py/_library_tools.py) hand-rolled
     its own subset of these class toggles, which is exactly what caused
     the header/toolbar to drift out of sync between views (missing
     global-search-hide, stale fb-scroll-hidden, ...).
     Caller must set playlistItems/currentPath/_currentPlaylistId/
     inPlaylist BEFORE calling this — applyFilter() reads playlistItems. */
  /* ── Shared header state ──────────────────────────────────────────────
     THE single place that touches header controls. Every view routes
     through here via _enterTrackListView()/_enterFolderGridView(), so the
     header is structurally identical everywhere: the same controls exist,
     in the same order, in every view. Only their *content* (title,
     breadcrumb) and enabled/disabled state may differ — a control is never
     present in one view and absent in another.

     This replaced the earlier "global search is a folder-grid-only
     control" rule, which made the header visibly different between folder
     browsing and any track list (user playlist, favorites, duplicates,
     ...). Searching the whole library is a global action and must stay
     reachable from every view. */
  /* Shared view-entry points ported to webui/src/viewEntry.ts (DOM elements +
     legacy callbacks via hooks; currentPath/allItems/currentIndex via htState).
     Wrappers keep bare-name call sites. */
  function _entryHooks() {
    return {
      dom: {
        headerTitle: headerTitle, backBtn: backBtn, playAllBtn: playAllBtn,
        folderGrid: folderGrid, trackView: trackView, filterBar: filterBar,
        playerBar: playerBar, trackCount: trackCount, searchInput: searchInput,
        player: player
      },
      originalTitle: originalTitle,
      renderBreadcrumb: renderBreadcrumb,
      applyViewMode: applyViewMode,
      initGlobalSearch: initGlobalSearch,
      hideGlobalSearch: _hideGlobalSearch,
      initFilterBarScrollReveal: _initFilterBarScrollReveal,
      applyFilter: applyFilter,
      routerUpdate: function() { if (typeof _router !== 'undefined') _router.update(); }
    };
  }
  function _applyHeaderState(opts) { window._applyHeaderState(opts, _entryHooks()); }
  function _enterTrackListView(opts) { window._enterTrackListView(opts, _entryHooks()); }
  function _enterFolderGridView(opts) { window._enterFolderGridView(opts, _entryHooks()); }
  /* ── playlist view ── */
  /* showPlaylist ported to webui/src/playAll.ts (state via htState). */
  function showPlaylist(items, autoplay, startIdx) {
    window._showPlaylist(items, autoplay, startIdx, {
      destroyPlaylistDragDrop: destroyPlaylistDragDrop,
      sortByFolderOrder: _sortByFolderOrder,
      enterTrackListView: _enterTrackListView,
      refreshFolderRatings: refreshFolderRatings,
      playTrack: playTrack,
      restoreLastEpisode: _restoreLastEpisode,
      loadFolderOrderAsync: _loadFolderOrderAsync,
      loadFolderOrder: _loadFolderOrder,
      applyFilter: applyFilter,
      routerUpdate: function() { if (typeof _router !== 'undefined') _router.update(); }
    });
  }

  /* ── Auto-resume: restore last-watched episode when navigating into a folder ─
     Called from showPlaylist when the user opens a folder without an explicit
     startIdx (i.e. not via "Play All" or a file-card click).
     Priority: localStorage (instant, survives server restarts) → server recent API.
     Does NOT start playback — user must click explicitly. */
  function _restoreLastEpisode() {
    window._restoreLastEpisode({
      loadLastPlayedLocal: _loadLastPlayedLocal,
      recentEnabled: RECENT_ENABLED,
      recentApiPath: RECENT_API_PATH,
      selectResume: function(idx) {
        _pb.currentIndex = idx;
        markActive();
        var li = trackList.querySelector('[data-index="' + idx + '"]');
        if (li) li.scrollIntoView({ block: 'center', behavior: 'smooth' });
      },
      toast: showToast,
      fmtTime: fmtTime
    });
  }

  /* ── back ── */
  function goBack() {
    window._goBack({ exitGlobalSearch: exitGlobalSearch, showFolderView: showFolderView, contentsAt: contentsAt });
  }

  /* ── global search (root view) ── */
  /* Header search wiring (private debounce/init state) ported to
     webui/src/folderBrowseUi.ts; _globalSearchActive via htState. */
  function initGlobalSearch() {
    window._initGlobalSearch({ globalSearch: globalSearch, exitGlobalSearch: exitGlobalSearch });
  }
  function _hideGlobalSearch() { window._hideGlobalSearch(); }
  /* ── Filter bar scroll-reveal ── */
  function _initFilterBarScrollReveal() { window._initFilterBarScrollReveal(filterBar); }

"""
