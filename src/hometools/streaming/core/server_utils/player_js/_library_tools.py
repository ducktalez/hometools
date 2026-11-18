"""JS fragment: library tools (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_library_tools_js() -> str:
    """Return the library tools section of the player JS."""
    return """  /* Dupes, delete/move ops, folder list, move widget, ctx menus, rating, favorites, edit modal,
     folder/favorites custom order: webui/src/libraryWiring.ts. State via htState; legacy callbacks
     via the deps thunk (resolved per call). Wrappers keep bare names. */
  var _lw = window._createLibraryWiring({
    filePlaceholder: FILE_PLACEHOLDER, deleteApiPath: DELETE_API_PATH, moveApiPath: MOVE_API_PATH,
    revealApiPath: REVEAL_API_PATH, ratingApiPath: RATING_API_PATH, auditUndoPath: AUDIT_UNDO_PATH,
    folderOrderApiPath: FOLDER_ORDER_API_PATH, apiBase: API_PATH.substring(0, API_PATH.lastIndexOf('/')),
    ratingWriteEnabled: !!RATING_WRITE_ENABLED, metadataEditEnabled: !!METADATA_EDIT_ENABLED,
    metadataEditPath: METADATA_EDIT_PATH, icPlay: IC_PLAY, icDuplicate: IC_DUPLICATE, icTrash: IC_TRASH,
    icFolderOpen: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>',
    icStarFilled: IC_STAR_FILLED, icStarEmpty: IC_STAR_EMPTY
  }, function() {
    return {
      esc: escHtml, toast: showToast, applyFilter: applyFilter, markActive: markActive,
      showFolderView: showFolderView, showPlaylist: showPlaylist, playTrack: playTrack, itemsUnder: itemsUnder,
      destroyPlaylistDragDrop: destroyPlaylistDragDrop, enterTrackListView: _enterTrackListView,
      saveCatalogCache: _saveCatalogCache, isManualPlaylistView: _isManualPlaylistView,
      removeFromUserPlaylist: removeFromUserPlaylist,
      filterFavActive: function() { return !!_view.filterFav; }
    };
  });
  function _invalidateDupeMap() { _lw.invalidateDupeMap(); }
  function openDupePanel() { _lw.openDupePanel(); }
  function closeDupePanel() { _lw.closeDupePanel(); }
  function playDuplicates() { _lw.playDuplicates(); }
  function _deleteDuplicateFile(allIndex) { _lw.deleteDuplicateFile(allIndex); }
  function _removeGoneTrack(relativePath) { _lw.removeGoneTrack(relativePath); }
  function _deleteTrackFromList(filteredIdx) { _lw.deleteTrackFromList(filteredIdx); }
  function _getAllFolders() { return _lw.getAllFolders(); }
  function renderMoveWidget(t, idx) { return _lw.renderMoveWidget(t, idx); }
  function moveFileToFolder(idx, targetFolder) { _lw.moveFileToFolder(idx, targetFolder); }
  function _openCtxMenu(btn, items) { _lw.openCtxMenu(btn, items); }
  function _openTrackCtxMenu(btn, relativePath, title) { _lw.openTrackCtxMenu(btn, relativePath, title); }
  function _revealInExplorer(relativePath, title) { _lw.revealInExplorer(relativePath, title); }

  /* ── playback ── */
  /* Background playback for video — three layers of defence:
     ─────────────────────────────────────────────────────────
     PROBLEM: Mobile browsers (especially iOS Safari) pause <video>
     elements **before** the visibilitychange event fires.  So checking
     `!player.paused` inside that handler is already too late — the
     video is paused.  And `requestPictureInPicture()` requires a
     user-gesture, so calling it from visibilitychange is rejected.

     STRATEGY:
     1. **`wasPlaying` flag** — set on `playing` event, cleared only by
        intentional user-pause.  The browser's auto-pause does NOT
        clear it.  visibilitychange checks `wasPlaying` instead of
        `!player.paused`.
     2. **Hidden <audio> with `muted:true`** — plays the same source
        silently alongside the video.  Because it is already actively
        playing (started from user-gesture), iOS keeps it alive when
        backgrounded.  On visibilitychange we unmute it so audio
        continues seamlessly.
        NOTE: iOS ignores `volume` (always 1), so we MUST use `muted`
        to prevent double-audio in the foreground.
     3. **`autopictureinpicture` attribute** — Safari/WebKit honours
        this and enters PiP automatically when the page backgrounds.
        No user-gesture needed.  The manual PiP button works on all
        browsers that support the API. */
  var isVideoPlayer = player.tagName === 'VIDEO';
  var isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
              (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

  /* PiP ported to webui/src/pip.ts (state private; legacy reads _isPipActive). */
  window._initPip({
    player: player, button: document.getElementById('btn-pip'),
    isVideoPlayer: isVideoPlayer, isIOS: isIOS,
    wasPlaying: function() { return window._wasPlaying(); }
  });

  /* wasPlaying flag + visibilitychange handler ported to webui/src/bgPlayback.ts. */
  window._initBackgroundPlayback({ player: player, isVideoPlayer: isVideoPlayer, isIOS: isIOS });

  /* Bar fullscreen button ported to webui/src/playerBarUi.ts. */
  window._initBarFullscreen(player, isVideoPlayer);

  /* Playback glue (playItem/playTrack, metadata refresh, transport, bg mirror,
     media session, crossfade): webui/src/playbackWiring.ts (_pbw). */
  var _pbw = window._createPlaybackWiring({
    apiPath: API_PATH, itemNoun: ITEM_NOUN, isVideoMode: isVideoMode, isVideoPlayer: isVideoPlayer,
    icPause: IC_PAUSE, icPlay: IC_PLAY, filePlaceholder: FILE_PLACEHOLDER,
    autoResume: AUTO_RESUME_ENABLED, lyricsEnabled: !!LYRICS_ENABLED, crossfadeDuration: CROSSFADE_DURATION
  }, function() {
    return {
      revokeOfflineUrl: revokeOfflineUrl, generateWaveform: generateWaveform,
      playOfflineOrStream: playOfflineOrStream, openVideoOverlay: openVideoOverlay, syncMiniBar: _syncMiniBar,
      markActive: markActive, renderPlayerRating: renderPlayerRating,
      updatePlayerBarActions: updatePlayerBarActions,
      isLyricsOpen: function() { return window._lyrics.isOpen(); },
      openLyricsPanel: openLyricsPanel,
      saveProgressNow: saveProgressNow, clearProgressFor: clearProgressFor,
      saveLastPlayedLocal: _saveLastPlayedLocal, loadAndSeekProgress: loadAndSeekProgress,
      loadSpriteData: loadSpriteData,
      routerUpdate: function() { if (typeof _router !== 'undefined') _router.update(); },
      applyFilter: applyFilter, playFromQueue: playFromQueue
    };
  });
  _pbw.setPlayNext(function() { playNextItem(); });
  function bgAudioIsActive() { return window._bgAudioIsActive(); }
  function stopBgSync() { window._stopBgSync(); }
  function startBgMirror() { _pbw.startBgMirror(); }
  function activeMedia() { return _pbw.activeMedia(); }
  function updateMediaSession(t) { _pbw.updateMediaSession(t); }
  function playItem(t, index) { _pbw.playItem(t, index); }
  function playTrack(index) { _pbw.playTrack(index); }
  function refreshMetadata(t) { _pbw.refreshMetadata(t); }
  function togglePlay() { _pbw.togglePlay(); }
  function handlePreviousTrack() { _pbw.handlePreviousTrack(); }

  /* ── Shuffle logic ──
     fisherYates/buildWeightedQueue/buildNormalQueue/rebuildShuffleQueue/
     nextIndex/prevIndex: ported to webui/src/shuffle.ts via the htState
     bridge (window.htState in _core.py) — they read/write
     shuffleQueue/shufflePos live. Bare call sites unchanged. */  /* Shuffle/repeat buttons (cycle, persist, long-press): webui/src/modeButtons.ts */
  /* ── Rating stars (audio-only write, display-only for video) ── */
  /* Rating stars/patch/POST/undo: webui/src/rating.ts via libraryWiring.ts; _justRatedPath via htState. */
  function renderPlayerRating(stars) { _lw.renderPlayerRating(stars); }
  function _patchAllItemsRating(relativePath, rating) { _lw.patchAllItemsRating(relativePath, rating); }
  function _updateTrackRatingBar(idx, rating) { _lw.updateTrackRatingBar(idx, rating); }
  function setRating(stars) { _lw.setRating(stars); }
  /* Rating-star hover/click ported to webui/src/playerBarUi.ts. */
  window._initPlayerRatingEvents({
    writeEnabled: !!RATING_WRITE_ENABLED,
    currentRating: function() { return (_pb.filteredItems[_pb.currentIndex] && _pb.filteredItems[_pb.currentIndex].rating) || 0; },
    setRating: setRating
  });

  window._initModeButtons({
    btnShuffle: btnShuffle, btnRepeat: btnRepeat,
    shuffleEnabled: !!SHUFFLE_ENABLED, repeatEnabled: !!REPEAT_ENABLED,
    icRepeat: IC_REPEAT, icRepeatOne: IC_REPEAT_ONE, showToast: showToast
  });
  btnPlay.addEventListener('click', togglePlay);
  btnPrev.addEventListener('click', handlePreviousTrack);
  btnNext.addEventListener('click', playNextItem);
  /* Album cover click → jump to current track in list */
  if (playerThumb) playerThumb.addEventListener('click', jumpToCurrentTrack);

  function _startCrossfade() { _pbw.startCrossfade(); }
  function _finishCrossfade() { _pbw.finishCrossfade(); }
  /* ended/error/pause/play handlers ported to webui/src/playerEvents.ts. */
  window._initPlayerEvents({
    player: player, btnPlay: btnPlay, icPlay: IC_PLAY, icPause: IC_PAUSE, isVideoMode: isVideoMode,
    showVidControls: function() { _showVidControls(); },
    saveProgressNow: saveProgressNow,
    clearProgressFor: clearProgressFor,
    finishCrossfade: _finishCrossfade,
    playNextItem: playNextItem,
    currentStreamUrl: function() { return _pb.currentStreamUrl; },
    removeGoneTrack: _removeGoneTrack,
    showToast: showToast
  });
  /* timeupdate/loadedmetadata/seek/bg-sync/progress flush: webui/src/timeline.ts */
  window._initTimeline({
    player: player, progressBar: progressBar, timeCur: timeCur, timeDur: timeDur,
    track: progressTrack, isVideoPlayer: isVideoPlayer, crossfadeDuration: CROSSFADE_DURATION,
    fmtTime: fmtTime,
    getItemDuration: function() { return _pb.itemDuration; },
    setItemDuration: function(d) { _pb.itemDuration = d; },
    saveProgressNow: saveProgressNow, saveProgressDebounced: saveProgressDebounced,
    updateSkipIntroBtn: function() { window._updateSkipIntroBtn(); },
    startCrossfade: _startCrossfade
  });
  backBtn.addEventListener('click', goBack);
  playAllBtn.addEventListener('click', playAllCurrent);

  /* Logo-Icon click → always navigate back to root */
  /* Logo click + video show-on-load: webui/src/playerBarUi.ts */
  window._initHeaderHome(logoHomeBtn, {
    setRoot: function() { _pb.currentPath = ''; },
    showFolderView: showFolderView
  });
  window._showVideoOnLoad(player, isVideoPlayer);

  /* Favorites + edit modal: webui/src/libraryWiring.ts. */
  function loadFavorites() { _lw.loadFavorites(); }
  function updateFavoriteButtons() { _lw.updateFavoriteButtons(); }
  function toggleFavorite(item, btn) { _lw.toggleFavorite(item, btn); }
  _lw.initEditModalRatingEvents();
  function openEditModal(idx) { _lw.openEditModal(idx); }
  function closeEditModal() { _lw.closeEditModal(); }
  function submitEditModal() { _lw.submitEditModal(); }


  /* showToast() lives in _core.py — kept as the single canonical
     definition (was accidentally duplicated here during the module split). */

  /* View toggle, search debounce, sort, filter chips: webui/src/toolbarUi.ts. */
  window._initToolbar({
    viewToggle: viewToggle, searchInput: searchInput, sortField: sortField,
    filterCombinedBtn: filterCombinedBtn, filterHiddenBtn: filterHiddenBtn,
    isVideoMode: isVideoMode,
    isTrackViewVisible: _isTrackViewVisible, toggleTrackViewMode: _toggleTrackViewMode,
    anyToolActive: _anyToolActive,
    getViewMode: function() { return _view.viewMode; },
    setViewMode: function(m) { _view.viewMode = m; },
    getShowHidden: function() { return _view.showHidden; },
    setShowHidden: function(v) { _view.showHidden = v; },
    applyViewMode: applyViewMode, applyFilter: applyFilter, showFolderView: showFolderView,
    toggleFilterPopover: _toggleFilterPopover, updateFilterChips: updateFilterChips,
    routerUpdate: function() { if (typeof _router !== 'undefined') _router.update(); }
  });

  /* ── init ── */
  /* Edit-modal buttons/keys: webui/src/toolbarUi.ts */
  window._initEditModalEvents({ enabled: !!METADATA_EDIT_ENABLED, close: closeEditModal, submit: submitEditModal });

  if (!OFFLINE_ENABLED) {
    if (downloadedPill) {
      downloadedPill.textContent = 'Safe Mode';
      downloadedPill.classList.add('is-offline');
    }
  } else if (typeof indexedDB !== 'undefined') {
    initDownloadDB().catch(function(err) {
      console.warn('IndexedDB not available:', err);
    }).then(function() {
      updateAllDownloadButtons();
      refreshOfflineLibrary();
    });
  } else {
    refreshOfflineLibrary();
  }
  applyViewMode();

  /* URL routing / deep linking: webui/src/router.ts (state via htState, UI filter state via hooks). */
  var _router = window._createRouter({
    getUi: function() {
      return { rating: _view.filterRating, fav: _view.filterFav, genre: _view.filterGenre, showHidden: _view.showHidden, viewMode: _view.viewMode };
    },
    setUi: function(p) {
      if (p.rating !== undefined) _view.filterRating = p.rating;
      if (p.fav !== undefined) _view.filterFav = p.fav;
      if (p.genre !== undefined) _view.filterGenre = p.genre;
      if (p.showHidden !== undefined) _view.showHidden = p.showHidden;
      if (p.viewMode !== undefined) _view.viewMode = p.viewMode;
    },
    toolsOpen: function() { return window._isToolsPanelOpen(); },
    openToolsPanel: function() { openToolsPanel(); },
    contentsAt: contentsAt, itemsUnder: itemsUnder,
    showPlaylist: showPlaylist, showFolderView: showFolderView,
    showUserPlaylistView: showUserPlaylistView, openOfflineLibrary: openOfflineLibrary,
    globalSearch: globalSearch, markActive: markActive, updateFilterChips: updateFilterChips
  });

  /* ── User Playlists: state in _pb ── */

  /* Custom order (server sync + localStorage): webui/src/customOrder.ts via libraryWiring.ts. */
  function _loadFavoritesOrder() { return _lw.loadFavoritesOrder(); }
  function _saveFavoritesOrder(paths) { _lw.saveFavoritesOrder(paths); }
  function _loadFavoritesOrderAsync(cb) { _lw.loadFavoritesOrderAsync(cb); }
  function _sortFavoritesByOrder(favItems) { return _lw.sortFavoritesByOrder(favItems); }
  function _folderOrderKey(folderPath) { return _lw.folderOrderKey(folderPath); }
  function _loadFolderOrder(folderPath) { return _lw.loadFolderOrder(folderPath); }
  function _saveFolderOrder(folderPath, paths) { _lw.saveFolderOrder(folderPath, paths); }
  function _loadFolderOrderAsync(folderPath, cb) { _lw.loadFolderOrderAsync(folderPath, cb); }
  function _sortByFolderOrder(folderPath, items) { return _lw.sortByFolderOrder(folderPath, items); }
  var _PLAYLIST_SYNC_INTERVAL = CFG.playlistSyncIntervalMs || 30000; /* ms */

"""
