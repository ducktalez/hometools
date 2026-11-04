"""JS fragment: library tools (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_library_tools_js() -> str:
    """Return the library tools section of the player JS."""
    return """  /* Dupe index state + build/ensure/count/invalidate: webui/src/dupeState.ts. */
  function _invalidateDupeMap() {
    window._invalidateDupeIndex();
    _rgKey = '';  /* force re-render when allItems changes */
  }

  function _ensureDupeMap() {
    window._ensureDupeIndex(allItems);
  }

  function _getDupeCount() {
    return window._dupeCount(allItems);
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


  function playDuplicates() {
    var dupeMap = window._ensureDupeIndex(allItems).map;
    var keys = Object.keys(dupeMap);
    if (!keys.length) { showToast('Keine Duplikate gefunden'); return; }
    var dupeItems = window._collectDupeItems(dupeMap, allItems);
    if (!dupeItems.length) return;
    closeDupePanel();
    /* Show as virtual playlist. Header/toolbar state via _enterTrackListView()
       (_folder_browse.py) — same shared entry point as showPlaylist()/
       showUserPlaylistView(); collapseFilterBar keeps the sort/filter row
       initially hidden (dupe list has its own compact layout). */
    destroyPlaylistDragDrop();
    inPlaylist = true;
    _currentPlaylistId = '__duplicates__';
    currentPath = '';
    playlistItems = dupeItems;
    _enterTrackListView({
      title: 'Duplikate (' + keys.length + ' Gruppen)',
      playAllDisabled: true,
      collapseFilterBar: true,
      resetIndex: true
    });
    if (shuffleMode) rebuildShuffleQueue(0);

  }

  /* Delete/move/gone-track ported to webui/src/libraryOps.ts (_deletePending
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
    return html;
  }

  function moveFileToFolder(idx, targetFolder) { window._moveFileToFolder(idx, targetFolder, _libOpsHooks()); }

  /* Generic kebab dropdown + reveal-in-explorer ported to webui/src/ctxMenu.ts
     (cleanup handle private there). Wrappers keep bare-name call sites.
     items: [{ icon, label, onClick, danger }] */
  function _closeCtxMenu() { window._closeCtxMenu(); }
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

  /* Fullscreen button — uses native fullscreen or iOS webkitEnterFullscreen */
  var btnFs = document.getElementById('btn-fs');
  var fsSupported = isVideoPlayer && (
    document.fullscreenEnabled || document.webkitFullscreenEnabled ||
    typeof player.webkitEnterFullscreen === 'function'
  );
  if (fsSupported && btnFs) btnFs.hidden = false;
  if (btnFs) {
    btnFs.addEventListener('click', function() {
      if (player.requestFullscreen) {
        player.requestFullscreen().catch(function() {});
      } else if (player.webkitRequestFullscreen) {
        player.webkitRequestFullscreen();
      }
    });
  }

  /* Bg-audio mirror ported to webui/src/bgAudio.ts (element + sync timer
     private there). Wrappers keep bare names; _bgEl() = element or null. */
  function _bgEl() { return window._getBgAudio(); }
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
  function playItem(t, index) {
    currentIndex = typeof index === 'number' ? index : -1;
    currentStreamUrl = t.stream_url || '';
    _currentItemDuration = t.duration || 0;  /* catalog metadata duration — fallback before browser loads it */
    _setCurrentIntro(t);

    /* shuffle sync: webui/src/playbackStart.ts */
    window._syncShufflePosition();

    /* Reset bg audio for new track */
    stopBgSync();
    if (_bgEl()) { _bgEl().pause(); _bgEl().muted = true; _bgEl().removeAttribute('src'); }
    _xfadeCleanup();
    player.volume = 1;
    window._setWasPlaying(false);
    revokeOfflineUrl();

    /* start/retry/offline-fallback chain: webui/src/playbackStart.ts */
    function beginPlayback(playback) {
      window._beginPlayback(playback, t.relative_path, {
        player: player, btnPlay: btnPlay, icPause: IC_PAUSE, icPlay: IC_PLAY,
        revokeOfflineUrl: revokeOfflineUrl, onStarted: startBgMirror,
        generateWaveform: generateWaveform
      });
    }
    /* title/artist/thumb/icon/video overlay: webui/src/nowPlaying.ts */
    window._showNowPlaying(t, {
      title: playerTitle, artist: playerArtist, thumb: playerThumb, btnPlay: btnPlay,
      playerBar: playerBar, player: player, overlayTitle: videoOverlayTitleText
    }, {
      icPause: IC_PAUSE, filePlaceholder: FILE_PLACEHOLDER, isVideoMode: isVideoMode,
      openVideoOverlay: openVideoOverlay, syncMiniBar: _syncMiniBar
    });
    markActive();
    updateMediaSession(t);
    renderPlayerRating(t.rating || 0);
    updatePlayerBarActions();
    refreshMetadata(t);
    /* Auto-update lyrics panel if currently open */
    if (LYRICS_ENABLED && window._lyrics.isOpen()) openLyricsPanel(t.relative_path || '', t.title);

    /* playback progress: track current item and try to resume */
    saveProgressNow();   /* flush the outgoing track's position before switching */
    window._cancelProgressTimer();
    window._setProgressPath(t.relative_path || '');
    /* Also persist to localStorage so the episode can be restored after a
       server restart or page reload — even if < 5 s have elapsed (which
       saveProgressNow would otherwise skip). */
    _saveLastPlayedLocal(window._getProgressPath(), 0);
    if (AUTO_RESUME_ENABLED) loadAndSeekProgress(window._getProgressPath());

    /* load sprite sheet for video scrubber preview */
    loadSpriteData(t.relative_path || '');

    playOfflineOrStream(t.stream_url)
      .then(beginPlayback)
      .catch(function() {
        beginPlayback({ url: t.stream_url, offline: false, fallbackUrl: t.stream_url });
      });
    if (typeof _router !== 'undefined') _router.update();
  }

  function playTrack(index) {
    if (index < 0 || index >= filteredItems.length) return;
    playItem(filteredItems[index], index);
  }

  function refreshMetadata(t) {
    var base = API_PATH.substring(0, API_PATH.lastIndexOf('/'));
    var metaUrl = base + '/metadata?path=' + encodeURIComponent(t.relative_path);
    var _requestedFor = t.relative_path;
    fetch(metaUrl)
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(meta) {
        if (!meta) return;
        /* Guard against a stale/late response overwriting the title/artist
           of a track that has since been superseded by a newer playItem()
           call (e.g. rapid track switching or a fast list reload while
           Tools mode is active). Without this guard the UI can briefly show
           a swapped/mismatched title+artist pair. */
        if (window._getProgressPath() !== _requestedFor) return;
        var changed = false;
        if (meta.title && meta.title !== t.title) {
          t.title = meta.title;
          playerTitle.textContent = meta.title;
          changed = true;
        }
        if (meta.artist && meta.artist !== t.artist) {
          t.artist = meta.artist;
          playerArtist.textContent = meta.artist;
          changed = true;
        }
        if (typeof meta.rating === 'number') {
          t.rating = meta.rating;
          renderPlayerRating(meta.rating);
        }
        if (changed) {
          updateMediaSession(t);
          applyFilter();
          markActive();
        }
      })
      .catch(function() {});
  }

  /* togglePlay: webui/src/transport.ts */
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

  /* First playable index — kept for API compat, returns 0 */
  function _firstPlayableIndex() { return 0; }


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
  var playerRatingEl = document.getElementById('player-rating');


  if (playerRatingEl) {
    /* hover preview */
    playerRatingEl.addEventListener('mouseover', function(e) {
      var btn = e.target.closest('.player-rating-star');
      if (!btn || !RATING_WRITE_ENABLED) return;
      var n = parseInt(btn.dataset.star, 10);
      playerRatingEl.querySelectorAll('.player-rating-star').forEach(function(b, i) {
        b.classList.toggle('hover', i < n);
      });
    });
    playerRatingEl.addEventListener('mouseleave', function() {
      playerRatingEl.querySelectorAll('.player-rating-star').forEach(function(b) {
        b.classList.remove('hover');
      });
    });
    /* click to rate — clicking the currently-set star clears the rating (toggle to 0) */
    playerRatingEl.addEventListener('click', function(e) {
      var btn = e.target.closest('.player-rating-star');
      if (!btn || !RATING_WRITE_ENABLED) return;
      var clicked = parseInt(btn.dataset.star, 10);
      var current = Math.round((filteredItems[currentIndex] && filteredItems[currentIndex].rating) || 0);
      setRating(clicked === current ? 0 : clicked);
    });
  }


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
  function _xfadeCleanup() { window._crossfadeCleanup(); }
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
  player.addEventListener('timeupdate', function() {
    var dur = isFinite(player.duration) ? player.duration : _currentItemDuration;
    if (!dur) return;
    progressBar.max = dur; progressBar.value = player.currentTime;
    timeCur.textContent = fmtTime(player.currentTime);
    if (isFinite(player.duration)) {
      drawWaveform(player.currentTime / player.duration);
    } else if (_currentItemDuration) {
      drawWaveform(player.currentTime / _currentItemDuration);
    }
    saveProgressDebounced();
    _updateSkipIntroBtn();
    /* Crossfade trigger: start fading when remaining time <= CROSSFADE_DURATION
       Skip crossfade for repeat-one (track restarts itself) */
    if (CROSSFADE_DURATION > 0 && !window._isCrossfading() && !isVideoPlayer && repeatMode !== 'one') {
      var remaining = player.duration - player.currentTime;
      if (remaining > 0 && remaining <= CROSSFADE_DURATION && player.duration > CROSSFADE_DURATION + 5) {
        _startCrossfade();
      }
    }
  });
  player.addEventListener('loadedmetadata', function() {
    if (isFinite(player.duration)) _currentItemDuration = player.duration;
    timeDur.textContent = fmtTime(isFinite(player.duration) ? player.duration : _currentItemDuration);
    progressBar.max = isFinite(player.duration) ? player.duration : _currentItemDuration;
  });
  progressBar.addEventListener('input', function() { player.currentTime = progressBar.value; });

  /* ── Tap / drag-to-seek on the whole progress track ──
     The hidden range input has a 1px thumb, which on touch devices (iOS Safari)
     is impossible to grab — tapping the track does not jump there either.  This
     pointer handler makes the *entire* track tappable and draggable on mouse,
     touch and pen, so seeking works on mobile again. */
  (function initTrackSeek() {
    if (!progressTrack) return;
    var seeking = false;
    function effDuration() {
      if (_bgEl() && !_bgEl().muted && document.hidden && isFinite(_bgEl().duration)) return _bgEl().duration;
      if (isFinite(player.duration)) return player.duration;
      /* Fallback: use catalog metadata duration while the browser has not yet
         determined the real duration (common with long files / non-seekable streams) */
      return _currentItemDuration || 0;
    }
    function seekToClientX(clientX) {
      var d = effDuration();
      if (!d) return;
      var rect = progressTrack.getBoundingClientRect();
      if (!rect.width) return;
      var frac = (clientX - rect.left) / rect.width;
      frac = Math.max(0, Math.min(1, frac));
      var t = frac * d;
      try { player.currentTime = t; } catch (e) {}
      if (_bgEl()) { try { _bgEl().currentTime = t; } catch (e) {} }
      if (progressBar) { progressBar.max = d; progressBar.value = t; }
      if (timeCur) timeCur.textContent = fmtTime(t);
      drawWaveform(frac);
    }
    progressTrack.addEventListener('pointerdown', function(e) {
      if (e.button != null && e.button !== 0) return;
      seeking = true;
      try { progressTrack.setPointerCapture(e.pointerId); } catch (err) {}
      seekToClientX(e.clientX);
      e.preventDefault();
    });
    progressTrack.addEventListener('pointermove', function(e) {
      if (!seeking) return;
      seekToClientX(e.clientX);
      e.preventDefault();
    });
    function endSeek(e) {
      if (!seeking) return;
      seeking = false;
      try { progressTrack.releasePointerCapture(e.pointerId); } catch (err) {}
      saveProgressNow();
    }
    progressTrack.addEventListener('pointerup', endSeek);
    progressTrack.addEventListener('pointercancel', endSeek);
  })();

  /* Flush playback progress immediately when the page is hidden or unloaded.
     The 5s debounce would otherwise be lost when the app is backgrounded or
     closed on mobile, making the server-side "Continue watching" list lag
     behind by several episodes. */
  function _flushProgress() {
    window._cancelProgressTimer();
    saveProgressNow();
  }
  document.addEventListener('visibilitychange', function() {
    if (document.hidden) _flushProgress();
  });
  window.addEventListener('pagehide', _flushProgress);

  /* bg audio events — keep UI in sync when playing in background */
  if (isVideoPlayer) {
    setInterval(function() {
      if (_bgEl() && !_bgEl().muted && document.hidden) {
        if (isFinite(_bgEl().duration)) {
          progressBar.max = _bgEl().duration;
          progressBar.value = _bgEl().currentTime;
          timeCur.textContent = fmtTime(_bgEl().currentTime);
          drawWaveform(_bgEl().currentTime / _bgEl().duration);
        }
      }
    }, 1000);
  }

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

  viewToggle.addEventListener('click', function() {
    if (_isTrackViewVisible()) {
      if (isVideoMode) return; /* detail/table view is audio-only */
      _toggleTrackViewMode();
      return;
    }
    if (_anyToolActive()) return; /* locked while tools are active */
    if (viewMode === 'list') viewMode = 'grid';
    else viewMode = 'list';
    localStorage.setItem('ht-view-mode', viewMode);
    if (inPlaylist) {
      applyViewMode();
      applyFilter();
    } else {
      showFolderView();
    }
    if (typeof _router !== 'undefined') _router.update();
  });
  searchInput.addEventListener('input', function() {
    /* Debounce: wait 150 ms after last keystroke before re-rendering the
       (potentially large) track list.  Keeps typing snappy at 6000 items. */
    clearTimeout(_searchDebounceTimer);
    _searchDebounceTimer = setTimeout(function() {
      applyFilter();
      if (typeof _router !== 'undefined') _router.update();
    }, 150);
  });
  sortField.addEventListener('change', function() { applyFilter(); if (typeof _router !== 'undefined') _router.update(); });
  if (filterCombinedBtn) {
    filterCombinedBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      _toggleFilterPopover(filterCombinedBtn);
    });
  }
  if (filterHiddenBtn) {
    filterHiddenBtn.addEventListener('click', function() {
      showHidden = !showHidden;
      localStorage.setItem('ht-show-hidden', showHidden ? '1' : '0');
      updateFilterChips();
      applyFilter();
      if (typeof _router !== 'undefined') _router.update();
    });
  }
  updateFilterChips();

  /* ── init ── */
  if (METADATA_EDIT_ENABLED) {
    var _editCancelBtn = document.getElementById('edit-modal-cancel-btn');
    var _editSaveBtn   = document.getElementById('edit-modal-save-btn');
    var _editBackdrop  = document.getElementById('edit-modal-backdrop');
    if (_editCancelBtn) _editCancelBtn.addEventListener('click', closeEditModal);
    if (_editSaveBtn)   _editSaveBtn.addEventListener('click', submitEditModal);
    /* Close on backdrop click (outside the panel) */
    if (_editBackdrop) {
      _editBackdrop.addEventListener('click', function(e) {
        if (e.target === _editBackdrop) closeEditModal();
      });
    }
    /* Submit on Enter inside inputs, Escape to close */
    document.addEventListener('keydown', function(e) {
      var backdrop = document.getElementById('edit-modal-backdrop');
      if (!backdrop || backdrop.hasAttribute('hidden')) return;
      if (e.key === 'Escape') { e.preventDefault(); closeEditModal(); }
      if (e.key === 'Enter' && e.target.tagName === 'INPUT') { e.preventDefault(); submitEditModal(); }
    });
  }

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

  /* ── URL routing / deep linking ──
     The browser URL mirrors the current view so reload / bookmarks /
     share-links restore navigation state.

     Query schema (all parameters optional):
       ?view=folder       &path=<rel>                 → folder grid
       ?view=playlist     &path=<rel>     [&track=<rel>]   → folder-playlist
       ?view=userplaylist &id=<id>        [&track=<rel>]   → user playlist
       ?view=favorites                    [&track=<rel>]   → favorites
       ?view=offline                      [&track=<rel>]   → offline downloads
       ?view=search       &q=<needle>     [&track=<rel>]   → global search results

     Legacy ?id=<rel> (auto-play deep link) is still honoured. */
  var _router = (function() {
    var _suppress = true;      /* stays true until restore() runs — otherwise the initial
                                  showFolderView() from loadInitialCatalog would overwrite
                                  the deep-link URL the user reloaded with */
    var _lastKey = '';         /* "view|path|id" of last pushed entry; track-only change → replace */

    function _readUrl() {
      var p = new URLSearchParams(window.location.search);
      return {
        view: p.get('view') || '',
        path: p.get('path') || '',
        id: p.get('id') || '',
        track: p.get('track') || '',
        q: p.get('q') || '',
        sort: p.get('sort') || '',
        fr: p.get('fr') || '',
        ff: p.get('ff') || '',
        fg: p.get('fg') || '',
        fh: p.get('fh') || '',
        vm: p.get('vm') || '',
        panel: p.get('panel') || ''
      };
    }

    function _buildUrl(s) {
      var p = new URLSearchParams();
      if (s.view) p.set('view', s.view);
      if (s.path) p.set('path', s.path);
      if (s.id) p.set('id', s.id);
      if (s.track) p.set('track', s.track);
      if (s.q) p.set('q', s.q);
      if (s.sort) p.set('sort', s.sort);
      if (s.fr) p.set('fr', s.fr);
      if (s.ff) p.set('ff', s.ff);
      if (s.fg) p.set('fg', s.fg);
      if (s.fh) p.set('fh', s.fh);
      if (s.vm) p.set('vm', s.vm);
      if (s.panel) p.set('panel', s.panel);
      var qs = p.toString();
      return window.location.pathname + (qs ? '?' + qs : '');
    }

    function _collectUiState(s) {
      /* Sort/filter/view-mode are always meaningful — encode whenever they differ from defaults. */
      try {
        if (sortField && sortField.value && sortField.value !== 'custom') s.sort = sortField.value;
      } catch (e) { /* ignore */ }
      if (typeof filterRating === 'number' && filterRating > 0) s.fr = String(filterRating);
      if (filterFav) s.ff = '1';
      if (filterGenre) s.fg = filterGenre;
      /* showHidden default = true → only encode when explicitly disabled */
      if (typeof showHidden === 'boolean' && !showHidden) s.fh = '0';
      if (viewMode && viewMode !== 'list') s.vm = viewMode;
      /* Tools-panel open? (audit is its own page, not a modal) */
      try {
        if (toolsBackdrop && !toolsBackdrop.hasAttribute('hidden')) s.panel = 'tools';
      } catch (e) { /* ignore */ }
      return s;
    }

    function _currentState() {
      var s = { view: '', path: '', id: '', track: '', q: '',
                sort: '', fr: '', ff: '', fg: '', fh: '', vm: '', panel: '' };
      /* Active selection only meaningful inside a list view */
      if (inPlaylist && filteredItems && currentIndex >= 0 && currentIndex < filteredItems.length) {
        var t = filteredItems[currentIndex];
        if (t && t.relative_path) s.track = t.relative_path;
      }
      if (_globalSearchActive) {
        s.view = 'search';
        var inp = document.getElementById('global-search-input');
        if (inp && inp.value) s.q = inp.value.trim();
        return _collectUiState(s);
      }
      if (currentPath === '__offline__') { s.view = 'offline'; return _collectUiState(s); }
      if (_currentPlaylistId === '__favorites__') { s.view = 'favorites'; return _collectUiState(s); }
      if (_currentPlaylistId && _currentPlaylistId !== '__folder__') {
        s.view = 'userplaylist'; s.id = _currentPlaylistId; return _collectUiState(s);
      }
      if (inPlaylist) { s.view = 'playlist'; s.path = currentPath || ''; return _collectUiState(s); }
      /* Default = folder grid (incl. root) */
      s.view = 'folder'; s.path = currentPath || '';
      return _collectUiState(s);
    }

    /* Key drives pushState vs replaceState: filter/sort/vm/panel changes share the
       same key as the current view → no new history entry. */
    function _key(s) { return (s.view || '') + '|' + (s.path || '') + '|' + (s.id || '') + '|' + (s.q || ''); }

    function update() {
      if (_suppress) return;
      var s = _currentState();
      var url = _buildUrl(s);
      var cur = window.location.pathname + window.location.search;
      if (url === cur) { _lastKey = _key(s); return; }
      var k = _key(s);
      try {
        if (k === _lastKey) {
          /* Same list/view, only track changed → replace (no extra history entry) */
          history.replaceState(s, '', url);
        } else {
          history.pushState(s, '', url);
        }
      } catch (e) { /* ignore */ }
      _lastKey = k;
    }

    function _markTrack(trackRp) {
      if (!trackRp || !filteredItems || !filteredItems.length) return;
      var i = filteredItems.findIndex(function(it) { return it && it.relative_path === trackRp; });
      if (i >= 0) {
        currentIndex = i;
        if (typeof markActive === 'function') markActive();
      }
    }

    function _applyUiStateFromUrl(st) {
      /* URL wins over localStorage: explicit param overrides the saved value;
         absence of param leaves localStorage default untouched. */
      if (st.sort && sortField) {
        try { sortField.value = st.sort; } catch (e) { /* unknown option */ }
      }
      if (st.fr !== '') {
        var fr = parseInt(st.fr, 10);
        if (!isNaN(fr) && fr >= 0 && fr <= 5) {
          filterRating = fr;
          try { localStorage.setItem('ht-filter-rating', String(fr)); } catch (e) { /* ignore */ }
        }
      }
      if (st.ff !== '') {
        filterFav = (st.ff === '1');
        try { localStorage.setItem('ht-filter-fav', filterFav ? '1' : '0'); } catch (e) { /* ignore */ }
      }
      if (st.fg !== '') {
        filterGenre = st.fg;
        try { localStorage.setItem('ht-filter-genre', filterGenre); } catch (e) { /* ignore */ }
      }
      if (st.fh !== '') {
        showHidden = (st.fh !== '0');
        try { localStorage.setItem('ht-show-hidden', showHidden ? '1' : '0'); } catch (e) { /* ignore */ }
      }
      if (st.vm === 'grid' || st.vm === 'list') {
        viewMode = st.vm;
        try { localStorage.setItem('ht-view-mode', viewMode); } catch (e) { /* ignore */ }
      }
      try { if (typeof updateFilterChips === 'function') updateFilterChips(); } catch (e) { /* ignore */ }
    }

    function _applyPanelFromUrl(st) {
      /* Run after the view has been rendered so DOM is in place. */
      if (st.panel === 'tools' && typeof openToolsPanel === 'function') {
        try { openToolsPanel(); } catch (e) { /* ignore */ }
      }
    }

    function restore() {
      var st = _readUrl();

      /* Apply UI state (sort/filter/view-mode) BEFORE rendering — they affect what's shown. */
      _applyUiStateFromUrl(st);

      /* Legacy ?id= deep link → auto-play */
      if (!st.view && st.id && allItems.length) {
        var target = allItems.find(function(it) { return it.relative_path === st.id; });
        if (target) {
          var slash = st.id.lastIndexOf('/');
          var parent = slash > 0 ? st.id.substring(0, slash) : '';
          _suppress = true;
          try {
            currentPath = parent;
            var c = contentsAt(parent);
            var siblings = c.files.length ? c.files : itemsUnder(parent);
            var idx = siblings.findIndex(function(it) { return it.relative_path === st.id; });
            showPlaylist(siblings, true, idx >= 0 ? idx : 0);
          } finally { _suppress = false; }
          _applyPanelFromUrl(st);
          update();
          return;
        }
        _suppress = false;
        return;
      }

      if (!st.view) {
        _suppress = false;
        _applyPanelFromUrl(st);
        return;
      } /* root — nothing to do */

      _suppress = true;
      try {
        if (st.view === 'offline') {
          openOfflineLibrary();
          /* offline list is loaded async — defer track marker */
          if (st.track) setTimeout(function() { _markTrack(st.track); }, 200);
        } else if (st.view === 'favorites') {
          showUserPlaylistView('__favorites__');
          _markTrack(st.track);
        } else if (st.view === 'userplaylist' && st.id) {
          showUserPlaylistView(st.id);
          _markTrack(st.track);
        } else if (st.view === 'playlist') {
          currentPath = st.path || '';
          var pc = contentsAt(currentPath);
          var pItems = pc.files.length ? pc.files : itemsUnder(currentPath);
          if (pItems.length) {
            var pStart = 0;
            if (st.track) {
              var pi = pItems.findIndex(function(it) { return it.relative_path === st.track; });
              if (pi >= 0) pStart = pi;
            }
            showPlaylist(pItems, false, pStart);
            _markTrack(st.track);
          } else {
            showFolderView();
          }
        } else if (st.view === 'search' && st.q) {
          currentPath = '';
          showFolderView();
          var inp = document.getElementById('global-search-input');
          if (inp) inp.value = st.q;
          if (typeof globalSearch === 'function') globalSearch(st.q);
          _markTrack(st.track);
        } else {
          /* folder (default) */
          currentPath = st.path || '';
          showFolderView();
        }
      } finally {
        _suppress = false;
      }
      _applyPanelFromUrl(st);
      /* Reflect the actually-restored state back to the URL (e.g. fallback to folder view) */
      update();
    }

    function init() {
      window.addEventListener('popstate', function() {
        /* Browser back/forward → re-render. restore() handles its own suppression
           and the final update() is a no-op because the URL already matches. */
        restore();
      });
    }

    return { update: update, restore: restore, init: init };
  }());

  /* Backwards-compat shim so any leftover call sites keep working. */
  function handleDeepLink() { _router.restore(); }

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
    try { localStorage.setItem(_folderOrderKey(folderPath), JSON.stringify(paths)); }
    catch (e) { /* quota exceeded — ignore */ }
    /* persist to server (fire-and-forget) */
    fetch(FOLDER_ORDER_API_PATH, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder_path: folderPath || '__root__', items: paths })
    }).catch(function() {});
  }
  function _loadFolderOrderAsync(folderPath, cb) {
    var key = folderPath || '__root__';
    fetch(FOLDER_ORDER_API_PATH + '?path=' + encodeURIComponent(key))
      .then(function(r) { return r.json(); })
      .then(function(d) {
        var items = d.items || [];
        if (items.length) {
          try { localStorage.setItem(_folderOrderKey(folderPath), JSON.stringify(items)); }
          catch (e) {}
          cb(items);
        } else {
          cb(_loadFolderOrder(folderPath));
        }
      }).catch(function() { cb(_loadFolderOrder(folderPath)); });
  }
  function _sortByFolderOrder(folderPath, items) {
    return window._sortByOrder(items, _loadFolderOrder(folderPath));
  }  var _playlistRevision = 0;
  var _PLAYLIST_SYNC_INTERVAL = CFG.playlistSyncIntervalMs || 30000; /* ms */

"""
