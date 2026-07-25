"""JS fragment: core (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_core_js(waveform_js) -> str:
    """Return the core section of the player JS."""
    return (
        """  var _LANG_NAME_MAP = {
    'de': 'Deutsch', 'en': 'English', 'fr': 'Fran\u00e7ais', 'es': 'Espa\u00f1ol',
    'it': 'Italiano', 'ja': '\u65e5\u672c\u8a9e', 'ko': '\ud55c\uad6d\uc5b4',
    'zh': '\u4e2d\u6587', 'pt': 'Portugu\u00eas', 'ru': '\u0420\u0443\u0441\u0441\u043a\u0438\u0439'
  };

  var allItems = Array.isArray(INITIAL) ? INITIAL : [];
  var currentPath = '';
  var playlistItems = [];
  /* _moveGhosts kept for compat but no longer populated — ghost display removed. */
  var _moveGhosts = {};
  /* Path currently being deleted by _deleteTrackFromList.  Prevents _removeGoneTrack
     (triggered by the 404 the stream returns for the deleted file) from double-advancing
     the player while the delete animation is still running. */
  var _deletePending = null;
  /* Paths deleted client-side this session (file sent to trash via POST /delete).
     Set IMMEDIATELY on user confirm (before the API call) to close the race window
     where a concurrent silent-refresh could re-add the item while the call is in-flight.
     Applied as a filter in every background catalog fetch so deleted items never
     reappear before the server has rebuilt its index. Cleared on full manual refresh. */
  var _locallyDeletedPaths = {};
  var filteredItems = [];
  var currentIndex = -1;
  var inPlaylist = false;
  var initialCatalogRetryTimer = null;
  var initialCatalogRetryCount = 0;
  /* ── Shuffle state ── */
  var shuffleMode = false;       /* false = off, 'normal' = random, 'weighted' = rating-weighted */
  var repeatMode  = false;       /* false = off, 'all' = repeat playlist, 'one' = repeat single track */
  var shuffleQueue = [];         /* pre-built queue of indices for current session */
  var shufflePos = -1;           /* current position within shuffleQueue */

  /* ── Queue (Warteschlange) state ── */
  var _userQueue = [];           /* Array of item objects {title, artist, stream_url, relative_path, thumbnail_url, ...} */
  var _queueOpen = false;
  var _queueDndCleanup = null;

  var player       = document.getElementById('player');
  var btnPlay      = document.getElementById('btn-play');
  var btnPrev      = document.getElementById('btn-prev');
  var btnNext      = document.getElementById('btn-next');
  var btnShuffle   = document.getElementById('btn-shuffle');
  var btnRepeat    = document.getElementById('btn-repeat');
  var trackList    = document.getElementById('track-list');
  var trackCount   = document.getElementById('track-count');
  var playerTitle  = document.getElementById('player-title');
  var playerArtist = document.getElementById('player-artist');
  var playerThumb  = document.getElementById('player-thumb');
  var playerBarActions = document.getElementById('player-bar-actions');
  var progressBar  = document.getElementById('progress-bar');
  var timeCur      = document.getElementById('time-cur');
  var timeDur      = document.getElementById('time-dur');
  var searchInput  = document.getElementById('search-input');
  var sortField    = document.getElementById('sort-field');
  var filterRatingBtn = document.getElementById('filter-rating');
  var filterFavBtn    = document.getElementById('filter-fav');
  var filterGenreBtn  = document.getElementById('filter-genre');
  var filterHiddenBtn = document.getElementById('filter-hidden');
  /* Persisted quick-filter state */
  var filterRating = parseInt(localStorage.getItem('ht-filter-rating') || '0', 10) || 0;
  var filterFav    = localStorage.getItem('ht-filter-fav') === '1';
  var filterGenre  = localStorage.getItem('ht-filter-genre') || '';
  var showHidden   = localStorage.getItem('ht-show-hidden') !== '0'; /* default true = ausgeblendet werden ausgegraut angezeigt */
  var folderGrid   = document.getElementById('folder-grid');
  var folderFilterBar = document.getElementById('folder-filter-bar');
  var trackView    = document.getElementById('track-view');
  var filterBar    = document.querySelector('.filter-bar');
  var backBtn      = document.getElementById('back-btn');
  /* Global search state */
  var _globalSearchActive = false;
  var logoHomeBtn  = document.getElementById('header-logo');
  var headerTitle  = document.getElementById('header-title');
  var playerBar    = document.querySelector('.player-bar');
  /* ── Video overlay (video-mode only) ── */
  var videoOverlay   = document.getElementById('video-overlay');
  var videoMiniBar   = document.getElementById('video-mini-bar');
  var miniTitle      = document.getElementById('mini-title');
  var miniArtist     = document.getElementById('mini-artist');
  var miniThumb      = document.getElementById('mini-thumb');
  var miniPlayBtn    = document.getElementById('mini-play-btn');
  var miniExpandBtn  = document.getElementById('mini-expand-btn');
  var videoCloseBtn  = document.getElementById('video-close-btn');
  var videoFsBtn     = document.getElementById('video-fs-btn');
  var videoCastBtn   = document.getElementById('video-cast-btn');
  var videoSkipIntroBtn = document.getElementById('video-skip-intro-btn');
  var videoOverlayTitleText = document.getElementById('video-overlay-title-text');
  var videoFloatContainer = document.getElementById('video-float-container');
  var videoFloatWrap   = document.getElementById('video-float-wrap');
  var floatExpandBtn   = document.getElementById('float-expand-btn');
  var floatCloseBtn    = document.getElementById('float-close-btn');
  var videoWrap        = document.querySelector('.video-wrap');
  /* In video-mode the overlay controls visibility; playerBar points to
     the .player-bar INSIDE the overlay, so existing classList calls work
     on the inner controls and the overlay is managed separately. */
  var playAllBtn   = document.getElementById('play-all-btn');
  var offlineLibrary = document.getElementById('offline-library');
  var offlineClose = document.getElementById('offline-close');
  var offlineSort  = document.getElementById('offline-sort');
  var offlinePersistBtn = document.getElementById('offline-persist-btn');
  var offlinePruneBtn = document.getElementById('offline-prune-btn');
  var offlineDownloadList = document.getElementById('offline-download-list');
  var offlineStorageSummary = document.getElementById('offline-storage-summary');
  var offlineStorageDetail = document.getElementById('offline-storage-detail');
  var downloadedPill = document.getElementById('downloaded-pill');
  var originalTitle = headerTitle.textContent;
  var breadcrumb  = document.getElementById('breadcrumb');
  var viewToggle  = document.getElementById('view-toggle');
  var _savedViewMode = localStorage.getItem('ht-view-mode');
  var viewMode    = (_savedViewMode === 'list' || _savedViewMode === 'grid') ? _savedViewMode : 'list';
  /* Track-list "detail/table" view — independent of the folder viewMode
     above. Audio-only feature (video keeps the classic row layout). */
  var _savedTrackViewMode = localStorage.getItem('ht-track-view-mode');
  var trackViewMode = (_savedTrackViewMode === 'table' && !isVideoMode) ? 'table' : 'rows';

  /* ── Windowed track rendering state ──────────────────────────────────────
     Instead of building one massive HTML string for all N items and setting
     innerHTML at once, we render _RENDER_BATCH_SIZE items at a time.  An
     IntersectionObserver on a sentinel <li> at the bottom of the list triggers
     each subsequent batch as the user scrolls down.  This keeps the initial
     render near-instant even for 6000-item playlists.

     _rgKey  — render-guard fingerprint.  If it matches the last render, the
               DOM rebuild is skipped entirely (e.g. navigating away and back
               to the same "Alle Titel" view).                                */
  var _RENDER_BATCH_SIZE  = 100;
  var _renderAllItems     = [];   /* full displayTracks array for current render */
  var _renderRealIdxMap   = [];   /* parallel: displayIdx → filteredItems index (-1 = placeholder) */
  var _renderBatchOffset  = 0;    /* how many items have been appended to DOM so far */
  var _renderSentinelEl   = null; /* sentinel <li> that triggers next batch */
  var _renderObserver     = null; /* IntersectionObserver watching the sentinel */
  var _rgKey              = '';   /* render-guard key from last completed renderTracks call */
  var _searchDebounceTimer = null; /* debounce timer for search-input */

  /* ── Catalog cache (localStorage, stale-while-revalidate) ──────────────────
     Persists the full catalog so that page reloads show content immediately
     without a loading spinner.  A silent background fetch always follows to
     pick up any changes since the cache was written.
     Key is unique per API endpoint so audio and video never clash.
     Rule: _saveCatalogCache after every successful items fetch;
           _clearCatalogCache before any user-triggered forced refresh.        */
  var _CATALOG_CACHE_KEY = 'ht-catalog-' + API_PATH.replace(/\\W+/g, '_');
  var _CATALOG_MAX_AGE_MS = 5 * 60 * 1000;  /* 5 min — discard if older */

  function _saveCatalogCache(items) {
    if (!items || !items.length) return;
    try {
      localStorage.setItem(_CATALOG_CACHE_KEY, JSON.stringify({
        items: items, savedAt: Date.now(), count: items.length
      }));
    } catch (e) { /* QuotaExceededError on large libraries or private-mode — ignore */ }
  }

  function _loadCatalogCache() {
    try {
      var raw = localStorage.getItem(_CATALOG_CACHE_KEY);
      if (!raw) return null;
      var data = JSON.parse(raw);
      if (!data || !Array.isArray(data.items) || !data.savedAt) return null;
      if (Date.now() - data.savedAt > _CATALOG_MAX_AGE_MS) {
        localStorage.removeItem(_CATALOG_CACHE_KEY);
        return null;  /* expired */
      }
      return data.items;
    } catch (e) { return null; }
  }

  function _clearCatalogCache() {
    try { localStorage.removeItem(_CATALOG_CACHE_KEY); } catch (e) {}
  }

  /* ── Last-played position (localStorage) ────────────────────────────────────
     Saved on every playItem() start and every saveProgressNow() tick.
     Survives server restarts and page reloads, unlike the in-memory currentIndex.
     Used as the primary (fast, offline) source for _restoreLastEpisode().
     Key is unique per server so audio and video don't clash.
     TTL: 30 days.                                                              */
  var _LAST_PLAYED_KEY = 'ht-last-' + API_PATH.replace(/\\W+/g, '_');

  function _saveLastPlayedLocal(rp, pos) {
    if (!rp) return;
    try {
      localStorage.setItem(_LAST_PLAYED_KEY, JSON.stringify({
        path: rp,
        position_seconds: pos,
        folder: rp.lastIndexOf('/') > 0 ? rp.substring(0, rp.lastIndexOf('/')) : '',
        timestamp: Date.now()
      }));
    } catch (e) {}
  }

  function _loadLastPlayedLocal() {
    try {
      var raw = localStorage.getItem(_LAST_PLAYED_KEY);
      if (!raw) return null;
      var data = JSON.parse(raw);
      if (!data || !data.path) return null;
      if (Date.now() - (data.timestamp || 0) > 30 * 24 * 60 * 60 * 1000) return null; /* 30 days */
      return data;
    } catch (e) { return null; }
  }

  /* Filter items returned by a background/silent fetch: remove paths that were
     deleted client-side this session so they don't reappear before the server
     has rescanned. Also prunes the set once the server confirms the deletion. */
  function _applyLocalMutations(items) {
    if (!items || !items.length) return items;
    var deletedKeys = Object.keys(_locallyDeletedPaths);
    if (!deletedKeys.length) return items;
    var freshSet = null;
    /* Prune confirmed deletions: if server no longer has the path, it's safe to
       remove from the local tracking set (no risk of re-adding). */
    deletedKeys.forEach(function(rp) {
      if (!freshSet) {
        freshSet = {};
        items.forEach(function(it) { freshSet[it.relative_path] = true; });
      }
      if (!freshSet[rp]) delete _locallyDeletedPaths[rp];
    });
    return items.filter(function(it) { return !_locallyDeletedPaths[it.relative_path]; });
  }

  var currentStreamUrl = '';
  var currentOfflineUrl = null;
"""
        + (waveform_js)
        + """

  /* ── Video overlay helpers (no-op in audio mode) ── */
  var _isFloating = false;

  function _fixOverlaySize() {
    /* iOS Safari clips position:fixed inside body{overflow:hidden} to the flex
       container height. Setting an explicit pixel height via JS is the only
       reliable cross-browser fix. */
    if (!videoOverlay) return;
    var h = window.innerHeight;
    videoOverlay.style.height = h + 'px';
    videoOverlay.style.width  = window.innerWidth + 'px';
  }
  if (isVideoMode) {
    window.addEventListener('resize', _fixOverlaySize);
    _fixOverlaySize();
  }

  function openVideoOverlay() {
    if (!videoOverlay) return;
    _isFloating = false;
    _fixOverlaySize(); /* ensure pixel-perfect height before showing */
    videoOverlay.classList.remove('view-hidden');
    if (videoMiniBar) videoMiniBar.hidden = true;
    if (videoFloatContainer) videoFloatContainer.classList.remove('active');
    /* Move <video> back to overlay if it was in float container */
    if (videoWrap && player.parentNode !== videoWrap) videoWrap.appendChild(player);
    player.style.display = 'block';
    _showVidControls(); /* always show controls when overlay opens */
  }

  /* ── Video overlay: auto-hide controls ──────────────────────────────────
     Controls (header + player bar) overlay the video. They fade out after
     3 s of uninterrupted playback. Tap the video area to toggle them.     */
  var _vidCtrlTimer = null;
  var _VID_CTRL_HIDE_MS = 3000;

  function _showVidControls() {
    if (!videoOverlay) return;
    videoOverlay.classList.remove('controls-hidden');
    clearTimeout(_vidCtrlTimer);
    /* Schedule auto-hide only while playing */
    if (!player.paused) {
      _vidCtrlTimer = setTimeout(_hideVidControls, _VID_CTRL_HIDE_MS);
    }
  }
  function _hideVidControls() {
    if (!videoOverlay) return;
    videoOverlay.classList.add('controls-hidden');
    clearTimeout(_vidCtrlTimer);
    _vidCtrlTimer = null;
  }
  function _toggleVidControls() {
    if (!videoOverlay) return;
    if (videoOverlay.classList.contains('controls-hidden')) {
      _showVidControls();
    } else {
      _hideVidControls();
    }
  }
  function closeVideoOverlay() {
    if (!videoOverlay) return;
    videoOverlay.classList.add('view-hidden');
    /* Show mini-bar only when a video source is loaded */
    if (videoMiniBar) videoMiniBar.hidden = !player.currentSrc;
  }
  function enterFloatPlayer() {
    /* Move <video> to float container and show it without closing the overlay completely */
    if (!videoFloatContainer || !videoFloatWrap || !isVideoMode) return;
    if (_isFloating) return; /* already floating */
    _isFloating = true;
    videoOverlay.classList.add('view-hidden');
    if (videoMiniBar) videoMiniBar.hidden = true;
    /* Move <video> into float wrap */
    videoFloatWrap.appendChild(player);
    player.style.display = 'block';
    videoFloatContainer.classList.add('active');
    /* Reset position to default bottom-right */
    videoFloatContainer.style.bottom = '80px';
    videoFloatContainer.style.right = '16px';
    videoFloatContainer.style.left = '';
    videoFloatContainer.style.top = '';
  }
  function exitFloatPlayer() {
    if (!_isFloating) return;
    _isFloating = false;
    videoFloatContainer.classList.remove('active');
    /* Move <video> back to overlay */
    if (videoWrap) videoWrap.appendChild(player);
    player.style.display = 'block';
    openVideoOverlay();
  }
  function _syncMiniBar(t) {
    if (!videoMiniBar) return;
    if (miniTitle)  miniTitle.textContent  = t.title  || '';
    if (miniArtist) miniArtist.textContent = t.artist || '';
    if (miniThumb) {
      var src = t.thumbnail_lg_url || t.thumbnail_url || '';
      miniThumb.src = src;
      miniThumb.style.display = src ? '' : 'none';
    }
    if (videoOverlayTitleText) videoOverlayTitleText.textContent = t.title || '';
  }
  function _syncMiniPlayBtn() {
    if (!miniPlayBtn) return;
    miniPlayBtn.innerHTML = player.paused ? IC_PLAY : IC_PAUSE;
  }

  /* ── Background-tab resume ──────────────────────────────────────────────
     Chrome (and other browsers) can pause media when a tab becomes hidden.
     We track whether the player was running before hide and resume it when
     the tab becomes visible again. Works for both audio and video mode.     */
  var _wasPlayingBeforeHide = false;
  document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
      _wasPlayingBeforeHide = !player.paused;
    } else {
      if (_wasPlayingBeforeHide && player.paused) {
        player.play().catch(function() {});
      }
    }
  });

  if (videoCloseBtn) {
    videoCloseBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      closeVideoOverlay();
    });
  }
  if (miniExpandBtn) {
    miniExpandBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      openVideoOverlay();
    });
  }
  if (videoMiniBar) {
    videoMiniBar.addEventListener('click', function(e) {
      /* Clicking the bar (not its buttons) reopens the overlay */
      if (e.target === miniPlayBtn || miniPlayBtn && miniPlayBtn.contains(e.target)) return;
      if (e.target === miniExpandBtn || miniExpandBtn && miniExpandBtn.contains(e.target)) return;
      openVideoOverlay();
    });
  }
  if (miniPlayBtn) {
    miniPlayBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      if (player.paused) { player.play(); } else { player.pause(); }
    });
  }
  /* ── Tap on video area → toggle overlay controls ── */
  if (isVideoMode && videoWrap) {
    videoWrap.addEventListener('click', function(e) {
      /* Ignore clicks on the skip-intro button or other interactive children */
      if (e.target.closest && e.target.closest('button')) return;
      _toggleVidControls();
    });
  }

  /* ── Fullscreen button — uses requestFullscreen on the OVERLAY div ── */
  if (videoFsBtn) {
    videoFsBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      var target = videoOverlay || player;
      if (document.fullscreenEnabled && target.requestFullscreen) {
        target.requestFullscreen().catch(function() {
          /* fallback: iOS webkitEnterFullscreen on video element */
          if (player.webkitEnterFullscreen) player.webkitEnterFullscreen();
        });
      } else if (target.webkitRequestFullscreen) {
        target.webkitRequestFullscreen();
      } else if (player.webkitEnterFullscreen) {
        player.webkitEnterFullscreen(); /* iOS Safari */
      }
    });
  }

  /* ── Cast button (HTML5 Remote Playback API) ─────────────────────────
     Streams the playing <video> element to any reachable Chromecast /
     AirPlay target.  Implementation uses only standard browser APIs —
     no Cast SDK, no app-id setup.  Visibility is driven by availability
     callbacks, so the button stays hidden on browsers without support
     (Firefox desktop, embedded WebViews without media-router). */
  if (videoCastBtn && player && player.tagName === 'VIDEO') {
    var _castInitialised = false;

    /* Chromium / Android Chrome / Desktop Chrome — Remote Playback API */
    if (player.remote && typeof player.remote.watchAvailability === 'function') {
      _castInitialised = true;
      try {
        player.remote.watchAvailability(function(available) {
          videoCastBtn.hidden = !available;
        }).catch(function() { /* unsupported / disabled in iframe */ });
      } catch (_e) { /* ignore */ }

      videoCastBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        if (player.remote && typeof player.remote.prompt === 'function') {
          player.remote.prompt().catch(function(err) {
            console.warn('Cast prompt cancelled or failed:', err);
          });
        }
      });

      try {
        player.remote.addEventListener('connect', function() {
          videoCastBtn.classList.add('active');
        });
        player.remote.addEventListener('disconnect', function() {
          videoCastBtn.classList.remove('active');
        });
      } catch (_e) { /* ignore */ }
    }

    /* iOS Safari fallback — AirPlay picker */
    if (!_castInitialised && window.WebKitPlaybackTargetAvailabilityEvent) {
      player.addEventListener('webkitplaybacktargetavailabilitychanged', function(ev) {
        videoCastBtn.hidden = (ev.availability !== 'available');
      });
      videoCastBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        if (typeof player.webkitShowPlaybackTargetPicker === 'function') {
          player.webkitShowPlaybackTargetPicker();
        }
      });
    }
    /* If neither API is available the button stays hidden — no regression. */
  }

  /* ── Skip-Intro (Netflix-style) ───────────────────────────────────────
     Markers come from the item's intro_start/intro_end fields (manual UI
     markers, YAML overrides or chapter auto-detection — merged server-side).
     The button has two modes:
       • "skip"  — a marker exists and playback is inside [start, end]:
                   tapping seeks to intro_end. Long-press recalibrates the
                   end to the current position.
       • "set"   — no marker yet on a *series* episode, early in playback:
                   tapping stores intro_end = current position so the next
                   episodes (and this one on replay) get a real skip button. */
  var _introStart = 0;
  var _introEnd = 0;
  var _curIsSeries = false;
  var _introBtnMode = '';       /* '', 'skip' or 'set' */
  var _introLongPressTimer = null;
  var _introLongPressed = false;

  function _setCurrentIntro(t) {
    _introStart = Math.max(0, parseFloat(t && t.intro_start) || 0);
    _introEnd = Math.max(0, parseFloat(t && t.intro_end) || 0);
    _curIsSeries = !!(t && ((parseInt(t.season, 10) || 0) > 0 || (parseInt(t.episode, 10) || 0) > 0));
    if (videoSkipIntroBtn) { videoSkipIntroBtn.hidden = true; _introBtnMode = ''; }
  }

  function _updateSkipIntroBtn() {
    if (!SKIP_INTRO_ENABLED || !videoSkipIntroBtn || !isVideoMode) return;
    var cur = player.currentTime || 0;
    var dur = isFinite(player.duration) ? player.duration : 0;
    var label = videoSkipIntroBtn.querySelector('span');
    /* skip mode: a marker is set and we're inside the intro window */
    if (_introEnd > 0 && cur >= _introStart && cur < _introEnd - 0.3) {
      if (_introBtnMode !== 'skip') {
        _introBtnMode = 'skip';
        videoSkipIntroBtn.classList.remove('set-mode');
        if (label) label.textContent = 'Intro \\u00fcberspringen';
        videoSkipIntroBtn.hidden = false;
      }
      return;
    }
    /* set mode: series episode, no marker yet, early in playback */
    if (_introEnd <= 0 && _curIsSeries && dur > 0) {
      var maxSet = Math.min(dur * 0.25, 180);
      if (cur >= 5 && cur <= maxSet) {
        if (_introBtnMode !== 'set') {
          _introBtnMode = 'set';
          videoSkipIntroBtn.classList.add('set-mode');
          if (label) label.textContent = 'Intro-Ende setzen';
          videoSkipIntroBtn.hidden = false;
        }
        return;
      }
    }
    if (!videoSkipIntroBtn.hidden) { videoSkipIntroBtn.hidden = true; _introBtnMode = ''; }
  }

  function _patchIntroLocal(relPath, start, end) {
    if (!relPath) return;
    function patch(arr) {
      if (!arr) return;
      for (var i = 0; i < arr.length; i++) {
        if (arr[i] && arr[i].relative_path === relPath) {
          arr[i].intro_start = start; arr[i].intro_end = end;
        }
      }
    }
    patch(typeof allItems !== 'undefined' ? allItems : null);
    patch(typeof filteredItems !== 'undefined' ? filteredItems : null);
  }

  function _saveIntroMarker(start, end) {
    var relPath = _progressRelPath || '';
    if (!relPath) return;
    _introStart = Math.max(0, start || 0);
    _introEnd = Math.max(0, end || 0);
    _patchIntroLocal(relPath, _introStart, _introEnd);
    try {
      fetch(INTRO_API_PATH, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: relPath, start: _introStart, end: _introEnd })
      }).catch(function() {});
    } catch (e) { /* ignore */ }
  }

  if (SKIP_INTRO_ENABLED && videoSkipIntroBtn) {
    videoSkipIntroBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      if (_introLongPressed) { _introLongPressed = false; return; }
      if (_introBtnMode === 'skip') {
        try { player.currentTime = _introEnd; } catch (err) {}
        if (typeof showToast === 'function') showToast('Intro \\u00fcbersprungen');
      } else if (_introBtnMode === 'set') {
        var pos = Math.round((player.currentTime || 0) * 10) / 10;
        _saveIntroMarker(0, pos);
        videoSkipIntroBtn.hidden = true; _introBtnMode = '';
        if (typeof showToast === 'function') showToast('Intro-Ende gesetzt bei ' + fmtTime(pos));
      }
    });
    /* Long-press in skip mode → recalibrate the intro end to the current pos */
    videoSkipIntroBtn.addEventListener('pointerdown', function() {
      if (_introBtnMode !== 'skip') return;
      _introLongPressed = false;
      _introLongPressTimer = setTimeout(function() {
        _introLongPressed = true;
        var pos = Math.round((player.currentTime || 0) * 10) / 10;
        _saveIntroMarker(_introStart, pos);
        if (typeof showToast === 'function') showToast('Intro-Ende neu gesetzt bei ' + fmtTime(pos));
      }, 650);
    });
    function _cancelIntroLongPress() { if (_introLongPressTimer) { clearTimeout(_introLongPressTimer); _introLongPressTimer = null; } }
    videoSkipIntroBtn.addEventListener('pointerup', _cancelIntroLongPress);
    videoSkipIntroBtn.addEventListener('pointercancel', _cancelIntroLongPress);
    videoSkipIntroBtn.addEventListener('pointerleave', _cancelIntroLongPress);
  }

  /* ── Fullscreen exit → float player ── */
  function _handleFullscreenChange() {
    var fsEl = document.fullscreenElement || document.webkitFullscreenElement;
    if (!fsEl && !videoOverlay.classList.contains('view-hidden') && player.currentSrc) {
      /* Exited native fullscreen (Escape / browser UI) while overlay was visible */
      enterFloatPlayer();
    }
  }
  document.addEventListener('fullscreenchange', _handleFullscreenChange);
  document.addEventListener('webkitfullscreenchange', _handleFullscreenChange);

  /* ── Escape key in overlay → float player ── */
  document.addEventListener('keydown', function(e) {
    if (!isVideoMode) return;
    if (e.key !== 'Escape') return;
    /* Escape while overlay is open (and not in native fullscreen) → float */
    if (!videoOverlay.classList.contains('view-hidden') && !document.fullscreenElement) {
      enterFloatPlayer();
    }
  });

  /* ── Float player: close and expand buttons ── */
  if (floatCloseBtn) {
    floatCloseBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      player.pause();
      videoFloatContainer.classList.remove('active');
      _isFloating = false;
      /* Move <video> back to overlay (hidden) */
      if (videoWrap) videoWrap.appendChild(player);
    });
  }
  if (floatExpandBtn) {
    floatExpandBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      exitFloatPlayer();
    });
  }

  /* ── Float player: drag to reposition ── */
  if (videoFloatContainer && isVideoMode) {
    (function _initFloatDrag() {
      var _dragging = false;
      var _startX = 0, _startY = 0;
      var _origLeft = 0, _origTop = 0;

      function _getControlled(e) {
        /* Don't start drag if clicking a button */
        var t = e.target;
        while (t && t !== videoFloatContainer) {
          if (t.tagName === 'BUTTON') return false;
          t = t.parentNode;
        }
        return true;
      }
      function _onDown(e) {
        if (!videoFloatContainer.classList.contains('active')) return;
        if (!_getControlled(e)) return;
        _dragging = true;
        var rect = videoFloatContainer.getBoundingClientRect();
        var cx = e.touches ? e.touches[0].clientX : e.clientX;
        var cy = e.touches ? e.touches[0].clientY : e.clientY;
        _startX = cx - rect.left;
        _startY = cy - rect.top;
        videoFloatContainer.classList.add('dragging');
        /* Switch to left/top positioning */
        videoFloatContainer.style.right = '';
        videoFloatContainer.style.bottom = '';
        videoFloatContainer.style.left = rect.left + 'px';
        videoFloatContainer.style.top  = rect.top  + 'px';
        e.preventDefault();
      }
      function _onMove(e) {
        if (!_dragging) return;
        var cx = e.touches ? e.touches[0].clientX : e.clientX;
        var cy = e.touches ? e.touches[0].clientY : e.clientY;
        var newLeft = cx - _startX;
        var newTop  = cy - _startY;
        var maxL = window.innerWidth  - videoFloatContainer.offsetWidth;
        var maxT = window.innerHeight - videoFloatContainer.offsetHeight;
        newLeft = Math.max(0, Math.min(newLeft, maxL));
        newTop  = Math.max(0, Math.min(newTop, maxT));
        videoFloatContainer.style.left = newLeft + 'px';
        videoFloatContainer.style.top  = newTop  + 'px';
        e.preventDefault();
      }
      function _onUp() {
        if (!_dragging) return;
        _dragging = false;
        videoFloatContainer.classList.remove('dragging');
      }
      videoFloatContainer.addEventListener('mousedown',  _onDown, {passive: false});
      videoFloatContainer.addEventListener('touchstart', _onDown, {passive: false});
      document.addEventListener('mousemove',  _onMove, {passive: false});
      document.addEventListener('touchmove',  _onMove, {passive: false});
      document.addEventListener('mouseup',  _onUp);
      document.addEventListener('touchend', _onUp);
    })();
  }

  /* Toggle play/pause by clicking the video area */
  if (isVideoMode) {
    var _videoWrap = document.querySelector('.video-wrap');
    if (_videoWrap) {
      _videoWrap.addEventListener('click', function() {
        if (player.paused) { player.play(); } else { player.pause(); }
      });
    }
  }
  /* Keep mini-bar play button icon in sync */
  player.addEventListener('play',  _syncMiniPlayBtn);
  player.addEventListener('pause', _syncMiniPlayBtn);

  /* ── helpers ── */
  function fmtTime(s) {
    if (!isFinite(s)) return '0:00';
    var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
    var sec = String(Math.floor(s % 60)).padStart(2, '0');
    return h > 0 ? h + ':' + String(m).padStart(2, '0') + ':' + sec : m + ':' + sec;
  }
  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function formatBytes(bytes) {
    var value = Number(bytes || 0);
    if (value <= 0) return '0 B';
    var units = ['B', 'KB', 'MB', 'GB'];
    var idx = 0;
    while (value >= 1024 && idx < units.length - 1) {
      value /= 1024;
      idx++;
    }
    return (idx === 0 ? String(value) : value.toFixed(1)) + ' ' + units[idx];
  }
  /* Single canonical toast implementation. Was accidentally duplicated in
     _library_tools.py / _track_render.py during the module split — a second
     top-level `function showToast(...)`/`function formatBytes(...)` later in
     the concatenated script silently shadowed this one (last declaration
     wins), which meant callers passing a custom `durationMs` (e.g. the
     "Weiter bei ..." resume toast) had it silently ignored. Keep this the
     only definition — see test_js_syntax.py::test_no_duplicate_top_level_functions. */
  function showToast(msg, durationMs) {
    var t = document.getElementById('ht-toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'ht-toast';
      t.style.cssText = 'position:fixed;bottom:100px;left:50%;transform:translateX(-50%);background:#333;color:#fff;padding:10px 20px;border-radius:8px;z-index:9999;font-size:14px;max-width:90%;text-align:center;transition:opacity .3s';
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.style.opacity = '1';
    t.style.display = 'block';
    clearTimeout(t._timer);
    t._timer = setTimeout(function() { t.style.opacity = '0'; setTimeout(function() { t.style.display = 'none'; }, 300); }, durationMs || 3500);
  }

  /* ── click-distance guard: suppress clicks when the mouse moved ── */
  var _mdX = 0, _mdY = 0;
  var CLICK_MOVE_THRESHOLD = 6; /* pixels */
  document.addEventListener('mousedown', function(e) { _mdX = e.clientX; _mdY = e.clientY; }, true);
  document.addEventListener('touchstart', function(e) {
    if (e.touches.length === 1) { _mdX = e.touches[0].clientX; _mdY = e.touches[0].clientY; }
  }, { passive: true, capture: true });
  function wasDrag(e) {
    var dx = Math.abs(e.clientX - _mdX);
    var dy = Math.abs(e.clientY - _mdY);
    return dx > CLICK_MOVE_THRESHOLD || dy > CLICK_MOVE_THRESHOLD;
  }

  /* ── playback progress persistence ── */
  var _progressTimer = 0;
  var _progressRelPath = '';
  function _progressApiBase() {
    return API_PATH.substring(0, API_PATH.lastIndexOf('/')) + '/progress';
  }
  function saveProgressNow() {
    var rp = _progressRelPath;
    if (!rp) return;
    var pos = player.currentTime;
    var dur = player.duration;
    if (!isFinite(pos) || !isFinite(dur)) return;
    /* Always update localStorage so the episode is restored after server restarts,
       even in the first/last 5 s where the server save is intentionally skipped. */
    _saveLastPlayedLocal(rp, pos);
    if (pos < 5 || pos > dur - 5) return;
    var payload = JSON.stringify({relative_path: rp, position_seconds: pos, duration: dur});
    /* Prefer sendBeacon — it survives page unload / app backgrounding on mobile,
       where a regular fetch() would be cancelled. */
    if (navigator.sendBeacon) {
      try {
        var blob = new Blob([payload], {type: 'application/json'});
        if (navigator.sendBeacon(_progressApiBase(), blob)) return;
      } catch (e) {}
    }
    fetch(_progressApiBase(), {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: payload,
      keepalive: true
    }).catch(function() {});
  }
  function saveProgressDebounced() {
    clearTimeout(_progressTimer);
    _progressTimer = setTimeout(saveProgressNow, 5000);
  }
  function clearProgressFor(rp) {
    if (!rp) return;
    fetch(_progressApiBase(), {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({relative_path: rp, position_seconds: 0, duration: 0})
    }).catch(function() {});
  }
  function loadAndSeekProgress(rp) {
    if (!rp) return;
    fetch(_progressApiBase() + '?path=' + encodeURIComponent(rp))
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(data) {
        if (!data || !data.items || !data.items.length) return;
        var entry = data.items[0];
        var pos = entry.position_seconds || 0;
        if (pos < 5) return;
        function doSeek() {
          if (isFinite(player.duration) && pos < player.duration - 5) {
            player.currentTime = pos;
            showToast('Fortfahren bei ' + fmtTime(pos), 3000);
          }
        }
        if (isFinite(player.duration) && player.duration > 0) {
          doSeek();
        } else {
          player.addEventListener('loadedmetadata', doSeek, { once: true });
        }
      })
      .catch(function() {});
  }

  var _indexToastEl = null;
  var _indexRefreshTimer = null;
  /* Per-run dismissal: once the user taps the toast away it stays hidden for
     the current indexing run.  The dismissal is persisted in localStorage
     (keyed by the run's start time) so it survives a page reload — but a
     genuinely *new* indexing run (different start time) shows the toast
     again.  hideIndexingToast() clears it when the run finishes. */
  var _indexToastDismissed = false;
  var _indexCurrentRunId = '';
  var _INDEX_DISMISS_KEY = 'ht-index-toast-dismissed';
  function _indexDismissedRunId() {
    try { return localStorage.getItem(_INDEX_DISMISS_KEY) || ''; } catch (e) { return ''; }
  }
  function showIndexingToast(msg, prog) {
    /* Identify the current indexing run so a dismissal can be scoped to it. */
    var runId = (prog && prog.last_build_started_at != null) ? String(prog.last_build_started_at) : '';
    _indexCurrentRunId = runId;
    if (_indexToastDismissed) return;
    /* Persisted dismissal for *this* run survives reloads. */
    if (runId && _indexDismissedRunId() === runId) { _indexToastDismissed = true; return; }
    if (!_indexToastEl) {
      _indexToastEl = document.createElement('div');
      _indexToastEl.className = 'ht-indexing-toast';
      _indexToastEl.title = 'Antippen zum Ausblenden';
      _indexToastEl.addEventListener('click', function() {
        _indexToastDismissed = true;
        if (_indexCurrentRunId) {
          try { localStorage.setItem(_INDEX_DISMISS_KEY, _indexCurrentRunId); } catch (e) {}
        }
        if (_indexToastEl) _indexToastEl.classList.remove('visible');
      });
      document.body.appendChild(_indexToastEl);
    }
    /* Optional progress bar — prog may be the cache status object (build_percent)
       or a plain {percent} object. */
    var pct = null;
    if (prog) {
      if (typeof prog.build_percent === 'number') pct = prog.build_percent;
      else if (typeof prog.percent === 'number') pct = prog.percent;
    }
    var barHtml = '';
    if (pct !== null && pct >= 0) {
      var w = Math.max(2, Math.min(100, pct));
      barHtml = '<div class="ht-index-progress"><div class="ht-index-progress-fill" style="width:' + w + '%"></div></div>';
    }
    _indexToastEl.innerHTML = '<div class="ht-index-row"><span class="spinner"></span>' +
      escHtml(msg || 'Indexing…') + '</div>' + barHtml;
    _indexToastEl.classList.add('visible');
  }
  function hideIndexingToast() {
    if (_indexToastEl) _indexToastEl.classList.remove('visible');
    if (_indexRefreshTimer) { clearTimeout(_indexRefreshTimer); _indexRefreshTimer = null; }
    _indexToastDismissed = false;
    /* The run is over — drop the persisted dismissal so a future run can
       show its toast again. */
    try { localStorage.removeItem(_INDEX_DISMISS_KEY); } catch (e) {}
  }

  /* ── Lyrics panel ── */
  var _lyricsBtn   = document.getElementById('btn-lyrics');
  var _lyricsPanel = document.getElementById('lyrics-panel');
  var _lyricsBody  = document.getElementById('lyrics-body');
  var _lyricsClose = document.getElementById('lyrics-close-btn');
  var _lyricsCache = {};   /* relative_path → lyrics text or '' */
  var _lyricsOpen  = false;

  function openLyricsPanel(relativePath, trackTitle) {
    if (!LYRICS_ENABLED || !_lyricsPanel) return;
    _lyricsOpen = true;
    _lyricsPanel.classList.add('visible');
    if (_lyricsBtn) _lyricsBtn.title = 'Songtext schlie\u00dfen';

    /* Serve from cache if available */
    if (relativePath in _lyricsCache) {
      _renderLyrics(_lyricsCache[relativePath], trackTitle);
      return;
    }
    if (_lyricsBody) _lyricsBody.innerHTML = '<div class="lyrics-loading">Lade Songtext\u2026</div>';
    fetch(LYRICS_API_PATH + '?path=' + encodeURIComponent(relativePath), { cache: 'no-store' })
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(d) {
        var text = (d && d.lyrics) ? d.lyrics : '';
        _lyricsCache[relativePath] = text;
        if (_lyricsOpen) _renderLyrics(text, trackTitle);
      })
      .catch(function() {
        if (_lyricsBody) _lyricsBody.innerHTML = '<div class="lyrics-empty">Songtext konnte nicht geladen werden.</div>';
      });
  }

  function _renderLyrics(text, trackTitle) {
    if (!_lyricsBody) return;
    if (text) {
      _lyricsBody.innerHTML = '<div class="lyrics-text">' + escHtml(text) + '</div>';
      if (_lyricsBtn) _lyricsBtn.classList.add('has-lyrics');
    } else {
      _lyricsBody.innerHTML = '<div class="lyrics-empty">Kein Songtext f\u00fcr \u201e' + escHtml(trackTitle || 'diesen Titel') + '\u201c hinterlegt.</div>';
      if (_lyricsBtn) _lyricsBtn.classList.remove('has-lyrics');
    }
  }

  function closeLyricsPanel() {
    _lyricsOpen = false;
    if (_lyricsPanel) _lyricsPanel.classList.remove('visible');
    if (_lyricsBtn) _lyricsBtn.title = 'Songtext anzeigen';
  }

  if (_lyricsBtn) {
    _lyricsBtn.addEventListener('click', function() {
      if (_lyricsOpen) {
        closeLyricsPanel();
      } else {
        /* Find the currently playing track */
        var t = filteredItems[currentIndex] || playlistItems[currentIndex];
        if (t) openLyricsPanel(t.relative_path, t.title);
      }
    });
  }
  if (_lyricsClose) {
    _lyricsClose.addEventListener('click', closeLyricsPanel);
  }

  if (_lyricsClose) {
    _lyricsClose.addEventListener('click', closeLyricsPanel);
  }

  /* ── Queue (Warteschlange) panel ── */
  var _queuePeekHandle = document.getElementById('queue-peek-handle');
  var _queuePanel = document.getElementById('queue-panel');
  var _queueBody  = document.getElementById('queue-body');
  var _queueClose = document.getElementById('queue-close-btn');
  var _queueBadge = document.getElementById('queue-peek-badge');
  var _queueClearBtn = document.getElementById('queue-clear-btn');
  var _queueDragHandle = document.getElementById('queue-drag-handle');
  var _queueUserHeight = null; /* user-chosen height in px, null = auto */
  var _QUEUE_HEIGHT_KEY = 'hometools_queue_height';
  var _QUEUE_MIN_H = 220; /* head ~57px + at least 3 items à 53px */
  /* Restore saved height preference (enforce minimum) */
  try {
    var _sh = localStorage.getItem(_QUEUE_HEIGHT_KEY);
    if (_sh) { var _sv = parseInt(_sh, 10); _queueUserHeight = (_sv >= _QUEUE_MIN_H) ? _sv : null; }
  } catch(e) {}

  /** Re-query queue DOM refs — called before every render to guard against
   *  stale references (e.g. if the player-bar was not yet visible at init). */
  function _domNodeMissingOrDetached(el) {
    return !el || !el.isConnected;
  }

  function _ensureQueueDom() {
    if (_domNodeMissingOrDetached(_queuePanel)) _queuePanel = document.getElementById('queue-panel');
    if (_domNodeMissingOrDetached(_queueBody)) _queueBody = document.getElementById('queue-body');
    if (_domNodeMissingOrDetached(_queueBadge)) _queueBadge = document.getElementById('queue-peek-badge');
    if (_domNodeMissingOrDetached(_queueClearBtn)) _queueClearBtn = document.getElementById('queue-clear-btn');
    if (_domNodeMissingOrDetached(_queuePeekHandle)) _queuePeekHandle = document.getElementById('queue-peek-handle');
    if (_domNodeMissingOrDetached(_queueClose)) _queueClose = document.getElementById('queue-close-btn');
    if (_domNodeMissingOrDetached(_queueDragHandle)) _queueDragHandle = document.getElementById('queue-drag-handle');
  }

  function addToQueue(item) {
    _ensureQueueDom();
    if (!item || !item.relative_path) return;
    /* Prevent duplicates */
    var exists = _userQueue.some(function(q) { return q.relative_path === item.relative_path; });
    if (exists) {
      showToast('Bereits in der Warteschlange');
      return;
    }
    _userQueue.push({
      title: item.title || '',
      artist: item.artist || '',
      stream_url: item.stream_url || '',
      relative_path: item.relative_path || '',
      thumbnail_url: item.thumbnail_url || '',
      thumbnail_lg_url: item.thumbnail_lg_url || '',
      rating: item.rating || 0,
      media_type: item.media_type || ITEM_NOUN
    });
    updateQueueBadge();
    updateQueueButtons();
    if (_queueOpen) renderQueuePanel();
    showToast('\u201e' + escHtml(item.title || 'Titel') + '\u201c zur Warteschlange hinzugef\u00fcgt');
  }

  function removeFromQueue(index) {
    if (index < 0 || index >= _userQueue.length) return;
    _userQueue.splice(index, 1);
    updateQueueBadge();
    updateQueueButtons();
    if (_queueOpen) renderQueuePanel();
  }

  function clearQueue() {
    _userQueue = [];
    updateQueueBadge();
    updateQueueButtons();
    if (_queueOpen) renderQueuePanel();
  }

  function updateQueueBadge() {
    _ensureQueueDom();
    if (_queueBadge) _queueBadge.textContent = _userQueue.length > 0 ? String(_userQueue.length) : '';
    if (_queuePeekHandle) _queuePeekHandle.classList.toggle('has-items', _userQueue.length > 0);
  }

  function updateQueueButtons() {
    /* Update .track-queue-btn states in track list */
    document.querySelectorAll('.track-queue-btn').forEach(function(btn) {
      var rp = btn.dataset.relativePath;
      var inQ = _userQueue.some(function(q) { return q.relative_path === rp; });
      btn.classList.toggle('in-queue', inQ);
      btn.title = inQ ? 'Aus Warteschlange entfernen' : 'Zur Warteschlange hinzuf\u00fcgen';
    });
  }

  function renderQueuePanel() {
    if (!_queueBody) return;
    if (_userQueue.length === 0) {
      _queueBody.innerHTML = '<div class="queue-empty">Die Warteschlange ist leer.</div>';
      if (_queueClearBtn) _queueClearBtn.style.display = 'none';
      return;
    }
    if (_queueClearBtn) _queueClearBtn.style.display = '';
    var html = '<ul class="queue-list" id="queue-list">';
    _userQueue.forEach(function(item, idx) {
      var thumbSrc = item.thumbnail_url || FILE_PLACEHOLDER;
      html += '<li class="queue-item" data-queue-index="' + idx + '">' +
        '<img class="queue-item-thumb" src="' + escHtml(thumbSrc) + '" alt="" loading="lazy">' +
        '<div class="queue-item-info">' +
          '<div class="queue-item-title">' + escHtml(item.title) + '</div>' +
          '<div class="queue-item-artist">' + escHtml(item.artist || item.relative_path) + '</div>' +
        '</div>' +
        '<button class="queue-item-remove" data-queue-index="' + idx + '" title="Entfernen">' + IC_REMOVE + '</button>' +
        '</li>';
    });
    html += '</ul>';
    _queueBody.innerHTML = html;
    /* Wire up click handlers */
    _queueBody.querySelectorAll('.queue-item').forEach(function(el) {
      el.addEventListener('click', function(e) {
        if (e.target.closest('.queue-item-remove')) return;
        var qi = Number(el.dataset.queueIndex);
        playFromQueue(qi);
      });
    });
    _queueBody.querySelectorAll('.queue-item-remove').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        removeFromQueue(Number(btn.dataset.queueIndex));
      });
    });
    initQueueDragDrop();
  }

  function playFromQueue(index) {
    if (index < 0 || index >= _userQueue.length) return;
    var item = _userQueue[index];
    /* Remove played item from queue */
    _userQueue.splice(index, 1);
    updateQueueBadge();
    updateQueueButtons();
    if (_queueOpen) renderQueuePanel();
    /* Play via playItem — find in filteredItems for correct index, or play directly */
    var fiIdx = filteredItems.findIndex(function(fi) { return fi.relative_path === item.relative_path; });
    if (fiIdx >= 0) {
      playItem(filteredItems[fiIdx], fiIdx);
    } else {
      playItem(item, -1);
    }
  }

  /** Dequeue next item from queue — returns true if an item was played */
"""
    )
