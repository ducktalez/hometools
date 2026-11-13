"""JS fragment: library tools (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_library_tools_js() -> str:
    """Return the library tools section of the player JS."""
    return """  /* Dupe index state + build/ensure/count/invalidate: webui/src/dupeState.ts. */
  function _invalidateDupeMap() {
    window._invalidateDupeIndex();
    _rgKey = '';  /* force re-render when allItems changes */
  }

  /* Panel open/close/wiring: webui/src/dupePanel.ts. Row click navigates to folder + plays. */
  function openDupePanel() {
    var di = window._ensureDupeIndex(allItems);
    window._openDupePanel(
      { allItems: allItems, dupeMap: di.map, dupeSafety: di.safety, dupePaths: di.paths },
      {
        escHtml: escHtml, filePlaceholder: FILE_PLACEHOLDER, icDuplicate: IC_DUPLICATE, icTrash: IC_TRASH,
        deleteDuplicate: _deleteDuplicateFile,
        playItem: function(t) {
          var sl = (t.relative_path || '').lastIndexOf('/');
          if (sl <= 0) return;
          var folder = t.relative_path.substring(0, sl);
          showPlaylist(itemsUnder(folder), folder);
          var localIdx = -1;
          for (var j = 0; j < filteredItems.length; j++) {
            if (filteredItems[j].relative_path === t.relative_path) { localIdx = j; break; }
          }
          if (localIdx >= 0) playTrack(localIdx);
        }
      }
    );
  }
  function closeDupePanel() { window._closeDupePanel(); }


  /* playDuplicates: webui/src/dupePanel.ts (state via htState). */
  function playDuplicates() {
    window._playDuplicates(window._ensureDupeIndex(allItems).map, {
      toast: showToast,
      closePanel: closeDupePanel,
      destroyPlaylistDragDrop: destroyPlaylistDragDrop,
      enterTrackListView: _enterTrackListView,
      rebuildShuffleQueue: rebuildShuffleQueue
    });
  }  /* Delete/move/gone-track ported to webui/src/libraryOps.ts (_deletePending
     private there; state via htState). Hooks bundle the legacy side effects. */
  function _libOpsHooks() {
    return {
      deleteApiPath: DELETE_API_PATH, moveApiPath: MOVE_API_PATH, toast: showToast,
      invalidateCaches: function() { _invalidateDupeMap(); _invalidateFolderCache(); },
      saveCatalogCache: _saveCatalogCache,
      applyFilter: applyFilter, showFolderView: showFolderView, playTrack: playTrack,
      itemsUnder: itemsUnder,
      progressRelPath: function() { return window._getProgressPath(); },
      showPausedIcon: function() { btnPlay.innerHTML = IC_PLAY; },
      reopenDupePanel: openDupePanel
    };
  }
  function _deleteDuplicateFile(allIndex) { window._deleteDuplicateFile(allIndex, _libOpsHooks()); }
  function _removeGoneTrack(relativePath) { window._removeGoneTrack(relativePath, _libOpsHooks()); }
  function _deleteTrackFromList(filteredIdx) { window._deleteTrackFromList(filteredIdx, _libOpsHooks()); }
  /* ── File mover (move to folder) ── */
  /* _getRecentMoveTargets()/_saveRecentMoveTarget() ported to
     webui/src/recentMoveTargets.ts, bridged onto window by main.ts. */

  /* _getAllFolders/_invalidateFolderCache + their cache var ported to
     webui/src/folderCache.ts. Wrapper keeps the bare name and feeds the
     current allItems; _invalidateFolderCache resolves straight to window. */
  function _getAllFolders() {
    return window._getAllFoldersFrom(allItems);
  }

  /* _currentFolderOf() ported to webui/src/pathUtils.ts (opportunistic
     port, see docs/IMPLEMENTATION_PLAN.md), bridged onto window by main.ts. */

  function renderMoveWidget(t, idx) {
    /* markup: webui/src/inlineWidgets.ts::moveWidgetHtml */
    return window._moveWidgetHtml(idx, _currentFolderOf(t), _getRecentMoveTargets(), _getAllFolders(), escHtml, IC_TRASH);
  }

  function moveFileToFolder(idx, targetFolder) { window._moveFileToFolder(idx, targetFolder, _libOpsHooks()); }

  /* Generic kebab dropdown + reveal-in-explorer ported to webui/src/ctxMenu.ts
     (cleanup handle private there). Wrappers keep bare-name call sites.
     items: [{ icon, label, onClick, danger }] */
  function _openCtxMenu(btn, items) { window._openCtxMenu(btn, items, escHtml); }
  /* -- Track context menu (three-dot / kebab) -- */
  function _openTrackCtxMenu(btn, relativePath, title) {
    var IC_FOLDER_OPEN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>';
    _openCtxMenu(btn, [
      { icon: IC_FOLDER_OPEN, label: 'Im Explorer anzeigen', onClick: function() { _revealInExplorer(relativePath, title); } }
    ]);
  }
  function _revealInExplorer(relativePath, title) {
    window._revealInExplorer(relativePath, { apiPath: REVEAL_API_PATH, toast: showToast });
  }

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

  /* Bg-audio mirror ported to webui/src/bgAudio.ts (element + sync timer
     private there). Wrappers keep bare names. */
  function bgAudioIsActive() { return window._bgAudioIsActive(); }
  function stopBgSync() { window._stopBgSync(); }
  function startBgMirror() {
    window._startBgMirror({ player: player, isVideoPlayer: isVideoPlayer, playNext: playNextItem });
  }
  /* activeMedia/updateMediaSession ported to webui/src/mediaSession.ts. */
  function activeMedia() { return window._activeMedia(player); }
  function updateMediaSession(t) {
    window._updateMediaSession(t, {
      player: player, itemNoun: ITEM_NOUN,
      previousTrack: handlePreviousTrack, nextTrack: playNextItem
    });
  }
  /* playItem sequencing: webui/src/playItem.ts. Legacy keeps state vars + UI side effects. */
  function playItem(t, index) {
    window._playItem(t, index, {
      player: player,
      setCurrentIndex: function(i) { currentIndex = i; },
      setCurrentStreamUrl: function(u) { currentStreamUrl = u; },
      setCurrentDuration: function(d) { _currentItemDuration = d; },
      setCurrentIntro: window._setCurrentIntro,
      beginPlayback: function(playback) {
        window._beginPlayback(playback, t.relative_path, {
          player: player, btnPlay: btnPlay, icPause: IC_PAUSE, icPlay: IC_PLAY,
          revokeOfflineUrl: revokeOfflineUrl, onStarted: startBgMirror,
          generateWaveform: generateWaveform
        });
      },
      playOfflineOrStream: playOfflineOrStream,
      showNowPlaying: function(tr) {
        window._showNowPlaying(tr, {
          title: playerTitle, artist: playerArtist, thumb: playerThumb, btnPlay: btnPlay,
          playerBar: playerBar, player: player, overlayTitle: videoOverlayTitleText
        }, {
          icPause: IC_PAUSE, filePlaceholder: FILE_PLACEHOLDER, isVideoMode: isVideoMode,
          openVideoOverlay: openVideoOverlay, syncMiniBar: _syncMiniBar
        });
      },
      markActive: markActive,
      updateMediaSession: updateMediaSession,
      renderPlayerRating: renderPlayerRating,
      updatePlayerBarActions: updatePlayerBarActions,
      refreshMetadata: refreshMetadata,
      refreshLyricsIfOpen: function(tr) {
        if (LYRICS_ENABLED && window._lyrics.isOpen()) openLyricsPanel(tr.relative_path || '', tr.title);
      },
      saveProgressNow: saveProgressNow,
      saveLastPlayedLocal: _saveLastPlayedLocal,
      autoResume: AUTO_RESUME_ENABLED,
      loadAndSeekProgress: loadAndSeekProgress,
      loadSpriteData: loadSpriteData,
      routerUpdate: function() { if (typeof _router !== 'undefined') _router.update(); }
    });
  }  function playTrack(index) {
    if (index < 0 || index >= filteredItems.length) return;
    playItem(filteredItems[index], index);
  }

  /* refreshMetadata: webui/src/metadataRefresh.ts */
  function refreshMetadata(t) {
    window._refreshMetadata(t, {
      apiPath: API_PATH,
      setTitle: function(s) { playerTitle.textContent = s; },
      setArtist: function(s) { playerArtist.textContent = s; },
      renderPlayerRating: renderPlayerRating,
      updateMediaSession: updateMediaSession,
      applyFilter: applyFilter,
      markActive: markActive
    });
  }  /* togglePlay: webui/src/transport.ts */
  function _transportHooks() {
    return {
      player: player, btnPlay: btnPlay, icPlay: IC_PLAY, icPause: IC_PAUSE,
      playTrack: playTrack, startBgMirror: startBgMirror, stopBgSync: stopBgSync,
      currentItemDuration: function() { return _currentItemDuration; }
    };
  }
  function togglePlay() { window._togglePlay(_transportHooks()); }
  /* ── Shuffle logic ──
     fisherYates/buildWeightedQueue/buildNormalQueue/rebuildShuffleQueue/
     nextIndex/prevIndex: ported to webui/src/shuffle.ts via the htState
     bridge (window.htState in _core.py) — they read/write
     shuffleQueue/shufflePos live. Bare call sites unchanged. */

  /* smart previous: webui/src/transport.ts */
  function handlePreviousTrack() { window._handlePreviousTrack(_transportHooks()); }

  /* Shuffle/repeat buttons (cycle, persist, long-press): webui/src/modeButtons.ts */
  /* ── Rating stars (audio-only write, display-only for video) ── */
  /* Rating stars/patch/POST/undo ported to webui/src/rating.ts; _justRatedPath
     stays here (read by applyFilter), reached via htState.justRatedPath. */
  function _ratingHooks() {
    return {
      writeEnabled: !!RATING_WRITE_ENABLED, ratingApiPath: RATING_API_PATH, auditUndoPath: AUDIT_UNDO_PATH,
      icStarFilled: IC_STAR_FILLED, icStarEmpty: IC_STAR_EMPTY,
      toast: showToast, applyFilter: applyFilter, markActive: markActive,
      rebuildShuffleQueue: rebuildShuffleQueue
    };
  }
  function renderPlayerRating(stars) { window._renderPlayerRating(stars, _ratingHooks()); }
  function _patchAllItemsRating(relativePath, rating) { window._patchAllItemsRating(relativePath, rating); }
  function _updateTrackRatingBar(idx, rating) { window._updateTrackRatingBar(idx, rating, _ratingHooks()); }
  function setRating(stars) { window._setRating(stars, _ratingHooks()); }
  /* Rating-star hover/click ported to webui/src/playerBarUi.ts. */
  window._initPlayerRatingEvents({
    writeEnabled: !!RATING_WRITE_ENABLED,
    currentRating: function() { return (filteredItems[currentIndex] && filteredItems[currentIndex].rating) || 0; },
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

  /* Crossfade ported to webui/src/crossfade.ts (_xfade* state private there). */
  function _xfadeHooks() {
    return {
      player: player, durationSec: CROSSFADE_DURATION,
      flushOutgoingProgress: function() { saveProgressNow(); clearProgressFor(window._getProgressPath()); },
      playTrack: playTrack, playFromQueue: playFromQueue
    };
  }
  function _startCrossfade() { window._startCrossfade(_xfadeHooks()); }
  function _finishCrossfade() { window._finishCrossfade(_xfadeHooks()); }


  /* ended/error/pause/play handlers ported to webui/src/playerEvents.ts. */
  window._initPlayerEvents({
    player: player, btnPlay: btnPlay, icPlay: IC_PLAY, icPause: IC_PAUSE, isVideoMode: isVideoMode,
    showVidControls: function() { _showVidControls(); },
    saveProgressNow: saveProgressNow,
    clearProgressFor: clearProgressFor,
    finishCrossfade: _finishCrossfade,
    playNextItem: playNextItem,
    currentStreamUrl: function() { return currentStreamUrl; },
    removeGoneTrack: _removeGoneTrack,
    showToast: showToast
  });
  /* timeupdate/loadedmetadata/seek/bg-sync/progress flush: webui/src/timeline.ts */
  window._initTimeline({
    player: player, progressBar: progressBar, timeCur: timeCur, timeDur: timeDur,
    track: progressTrack, isVideoPlayer: isVideoPlayer, crossfadeDuration: CROSSFADE_DURATION,
    fmtTime: fmtTime,
    getItemDuration: function() { return _currentItemDuration; },
    setItemDuration: function(d) { _currentItemDuration = d; },
    saveProgressNow: saveProgressNow, saveProgressDebounced: saveProgressDebounced,
    updateSkipIntroBtn: function() { window._updateSkipIntroBtn(); },
    startCrossfade: _startCrossfade
  });
  backBtn.addEventListener('click', goBack);
  playAllBtn.addEventListener('click', playAllCurrent);

  /* Logo-Icon click → always navigate back to root */
  logoHomeBtn.addEventListener('click', function() {
    currentPath = '';
    showFolderView();
  });

  /* Show video player element when something starts playing */
  if (isVideoPlayer) {
    player.addEventListener('loadeddata', function() {
      player.style.display = 'block';
    });
  }

  /* ── Favoriten — speichern & teilen ── */
  var _savedFavorites = {};

  /* loadFavorites/updateFavoriteButtons/toggleFavorite ported to
     webui/src/favorites.ts; _savedFavorites stays here (many legacy readers),
     reached from TS via htState.savedFavorites. */
  function _favHooks() {
    return {
      apiBase: API_PATH.substring(0, API_PATH.lastIndexOf('/')),
      toast: showToast, applyFilter: applyFilter,
      filterFavActive: function() { return !!filterFav; }
    };
  }
  function loadFavorites() { window._loadFavorites(_favHooks()); }
  function updateFavoriteButtons() { window._updateFavoriteButtons(); }
  function toggleFavorite(item, btn) { window._toggleFavorite(item, btn, _favHooks()); }
    /* ── metadata edit modal ── */
  /* Edit modal ported to webui/src/editModal.ts (_editModalRating private there). */
  function _editHooks() {
    return {
      metadataEditEnabled: !!METADATA_EDIT_ENABLED, ratingWriteEnabled: !!RATING_WRITE_ENABLED,
      metadataEditPath: METADATA_EDIT_PATH, ratingApiPath: RATING_API_PATH,
      icStarFilled: IC_STAR_FILLED, icStarEmpty: IC_STAR_EMPTY,
      toast: showToast, applyFilter: applyFilter,
      renderPlayerRating: renderPlayerRating, rebuildShuffleQueue: rebuildShuffleQueue,
      setPlayerText: function(title, artist) {
        if (playerTitle) playerTitle.textContent = title;
        if (playerArtist) playerArtist.textContent = artist;
      }
    };
  }
  window._initEditModalRatingEvents(_editHooks());
  function openEditModal(idx) { window._openEditModal(idx, _editHooks()); }
  function closeEditModal() { window._closeEditModal(); }
  function submitEditModal() { window._submitEditModal(_editHooks()); }


  /* showToast() lives in _core.py — kept as the single canonical
     definition (was accidentally duplicated here during the module split). */

  /* View toggle, search debounce, sort, filter chips: webui/src/toolbarUi.ts. */
  window._initToolbar({
    viewToggle: viewToggle, searchInput: searchInput, sortField: sortField,
    filterCombinedBtn: filterCombinedBtn, filterHiddenBtn: filterHiddenBtn,
    isVideoMode: isVideoMode,
    isTrackViewVisible: _isTrackViewVisible, toggleTrackViewMode: _toggleTrackViewMode,
    anyToolActive: _anyToolActive,
    getViewMode: function() { return viewMode; },
    setViewMode: function(m) { viewMode = m; },
    getShowHidden: function() { return showHidden; },
    setShowHidden: function(v) { showHidden = v; },
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
      return { rating: filterRating, fav: filterFav, genre: filterGenre, showHidden: showHidden, viewMode: viewMode };
    },
    setUi: function(p) {
      if (p.rating !== undefined) filterRating = p.rating;
      if (p.fav !== undefined) filterFav = p.fav;
      if (p.genre !== undefined) filterGenre = p.genre;
      if (p.showHidden !== undefined) showHidden = p.showHidden;
      if (p.viewMode !== undefined) viewMode = p.viewMode;
    },
    toolsOpen: function() { return !!toolsBackdrop && !toolsBackdrop.hasAttribute('hidden'); },
    openToolsPanel: function() { openToolsPanel(); },
    contentsAt: contentsAt, itemsUnder: itemsUnder,
    showPlaylist: showPlaylist, showFolderView: showFolderView,
    showUserPlaylistView: showUserPlaylistView, openOfflineLibrary: openOfflineLibrary,
    globalSearch: globalSearch, markActive: markActive, updateFilterChips: updateFilterChips
  });

  /* ── User Playlists ── */
  var _userPlaylists = [];
  var _playlistAddPath = '';
  var _currentPlaylistId = '';

  /* ── Favorites custom order (server-side + localStorage fallback) ── */
  /* order loading/sorting: webui/src/customOrder.ts (server sync stays here). */
  function _loadFavoritesOrder() {
    return window._loadOrder(window.FAVORITES_ORDER_KEY);
  }  function _saveFavoritesOrder(paths) {
    try { localStorage.setItem('ht-favorites-order', JSON.stringify(paths)); }
    catch (e) { /* quota exceeded — ignore */ }
    /* persist to server (fire-and-forget) */
    fetch(FOLDER_ORDER_API_PATH, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder_path: '__favorites__', items: paths })
    }).catch(function() {});
  }
  function _loadFavoritesOrderAsync(cb) {
    fetch(FOLDER_ORDER_API_PATH + '?path=__favorites__')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        var items = d.items || [];
        if (items.length) {
          try { localStorage.setItem('ht-favorites-order', JSON.stringify(items)); }
          catch (e) {}
          cb(items);
        } else {
          cb(_loadFavoritesOrder());
        }
      }).catch(function() { cb(_loadFavoritesOrder()); });
  }
  function _sortFavoritesByOrder(favItems) {
    return window._sortByOrder(favItems, _loadFavoritesOrder());
  }  /* ── Folder custom order (server-side + localStorage fallback) ── */
  function _folderOrderKey(folderPath) {
    return window._folderOrderKey(folderPath);
  }
  function _loadFolderOrder(folderPath) {
    return window._loadOrder(_folderOrderKey(folderPath));
  }  function _saveFolderOrder(folderPath, paths) {
    window._saveOrder(FOLDER_ORDER_API_PATH, _folderOrderKey(folderPath), folderPath || '__root__', paths);
  }
  function _loadFolderOrderAsync(folderPath, cb) {
    window._loadOrderAsync(FOLDER_ORDER_API_PATH, _folderOrderKey(folderPath), folderPath || '__root__', cb);
  }
  function _sortByFolderOrder(folderPath, items) {
    return window._sortByOrder(items, _loadFolderOrder(folderPath));
  }  var _playlistRevision = 0;
  var _PLAYLIST_SYNC_INTERVAL = CFG.playlistSyncIntervalMs || 30000; /* ms */

"""
