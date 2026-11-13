"""JS fragment: core (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_core_js(waveform_js) -> str:
    """Return the core section of the player JS."""
    return (
        """  /* Language names ported to webui/src/langNames.ts. */
  var _LANG_NAME_MAP = window._LANG_NAME_MAP;

  var allItems = Array.isArray(INITIAL) ? INITIAL : [];
  var currentPath = '';
  var playlistItems = [];
  /* _moveGhosts kept for compat but no longer populated — ghost display removed. */
  var _moveGhosts = {};
  /* _deletePending moved private into webui/src/libraryOps.ts. */
  /* Paths deleted client-side this session (file sent to trash via POST /delete).
     Set IMMEDIATELY on user confirm (before the API call) to close the race window
     where a concurrent silent-refresh could re-add the item while the call is in-flight.
     Applied as a filter in every background catalog fetch so deleted items never
     reappear before the server has rebuilt its index. Cleared on full manual refresh. */
  var _locallyDeletedPaths = {};
  /* Bridge onto window — read/mutated by _applyLocalMutations() (ported to
     webui/src/catalogCache.ts, bridged via main.ts). Object reference only:
     any in-place clear (delete/assign keys) elsewhere in this script stays
     visible through window._locallyDeletedPaths; never reassign this var
     with `= {}` (that would silently break the bridge — see refreshCatalog()
     in _queue.py which clears keys in place instead). */
  window._locallyDeletedPaths = _locallyDeletedPaths;
  var filteredItems = [];
  var currentIndex = -1;
  var inPlaylist = false;
  /* ── Shuffle state ── */
  var shuffleMode = false;       /* false = off, 'normal' = random, 'weighted' = rating-weighted */
  var repeatMode  = false;       /* false = off, 'all' = repeat playlist, 'one' = repeat single track */
  var shuffleQueue = [];         /* pre-built queue of indices for current session */
  var shufflePos = -1;           /* current position within shuffleQueue */

  /* ── Queue (Warteschlange) state ── */
  var _userQueue = [];           /* Array of item objects {title, artist, stream_url, relative_path, thumbnail_url, ...} */

  /* ── State bridge for ported TS modules (webui/src/stateBridge.ts) ──
     Getter/setter closures: TS reads see live values, TS writes reassign
     the IIFE-scoped vars. Legacy mutation sites stay untouched. Extend
     per property as ports need them — never mirror by copying values. */
  window.htState = {
    get allItems() { return allItems; },
    set allItems(v) { allItems = v; },
    get filteredItems() { return filteredItems; },
    set filteredItems(v) { filteredItems = v; },
    get playlistItems() { return playlistItems; },
    set playlistItems(v) { playlistItems = v; },
    get currentIndex() { return currentIndex; },
    set currentIndex(v) { currentIndex = v; },
    get currentPath() { return currentPath; },
    set currentPath(v) { currentPath = v; },
    get inPlaylist() { return inPlaylist; },
    set inPlaylist(v) { inPlaylist = v; },
    get shuffleMode() { return shuffleMode; },
    set shuffleMode(v) { shuffleMode = v; },
    get repeatMode() { return repeatMode; },
    set repeatMode(v) { repeatMode = v; },
    get shuffleQueue() { return shuffleQueue; },
    set shuffleQueue(v) { shuffleQueue = v; },
    get shufflePos() { return shufflePos; },
    set shufflePos(v) { shufflePos = v; },
    get userQueue() { return _userQueue; },
    set userQueue(v) { _userQueue = v; },
    get userPlaylists() { return _userPlaylists; },
    set userPlaylists(v) { _userPlaylists = v; },
    get playlistRevision() { return _playlistRevision; },
    set playlistRevision(v) { _playlistRevision = v; },
    get currentPlaylistId() { return _currentPlaylistId; },
    set currentPlaylistId(v) { _currentPlaylistId = v; },
    get playlistAddPath() { return _playlistAddPath; },
    set playlistAddPath(v) { _playlistAddPath = v; },
    get globalSearchActive() { return _globalSearchActive; },
    set globalSearchActive(v) { _globalSearchActive = v; },
    get savedFavorites() { return _savedFavorites; },
    set savedFavorites(v) { _savedFavorites = v; },
    get justRatedPath() { return _justRatedPath; },
    set justRatedPath(v) { _justRatedPath = v; }
  };

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
  var filterCombinedBtn = document.getElementById('filter-combined');
  var filterHiddenBtn = document.getElementById('filter-hidden');
  /* Persisted quick-filter state */
  var filterRating = parseInt(localStorage.getItem('ht-filter-rating') || '0', 10) || 0;
  var filterFav    = localStorage.getItem('ht-filter-fav') === '1';
  var filterGenre  = localStorage.getItem('ht-filter-genre') || '';
  var showHidden   = localStorage.getItem('ht-show-hidden') !== '0'; /* default true = ausgeblendet werden ausgegraut angezeigt */
  /* Path of the track whose rating was JUST changed (star click). Never
     fully hidden by any filter (auto-hide threshold OR quick "Bewertung"
     chip) while set — rendered grayed instead, so the just-applied change
     stays visible/undoable. Cleared (and the real filter re-applied) once
     the undo-toast window elapses. See applyFilter()/setRating()/
     setInlineRating() — bugfix for "rating crosses filter, song vanishes". */
  var _justRatedPath  = null;
  var _justRatedTimer = null;
  /* Combined "Filtern" popover (Bewertung + Favorit + Genre) — see
     docs/IMPLEMENTATION_PLAN.md "UI-Template-Vereinheitlichung" Phase 2. */
  var folderGrid   = document.getElementById('folder-grid');
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
  /* Bridge onto window — read by the ported leafName() (webui/src/pathUtils.ts,
     bridged via main.ts). A plain `var` here is scoped to this IIFE, not a
     real global, so the .ts module (a separate closure) can't see it
     otherwise; see legacy-globals.d.ts's header comment on this pattern. */
  window.originalTitle = originalTitle;
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
  var _rgKey              = '';   /* render-guard key from last completed renderTracks call */

  /* ── Catalog cache (localStorage, stale-while-revalidate) ──────────────────
     Ported to webui/src/catalogCache.ts (_saveCatalogCache/_loadCatalogCache/
     _clearCatalogCache), bridged onto window by main.ts. This IIFE keeps
     calling the bare identifiers (e.g. `_saveCatalogCache(allItems)`) — they
     resolve through the normal scope chain to window, unchanged call sites.
     Rule: _saveCatalogCache after every successful items fetch;
           _clearCatalogCache before any user-triggered forced refresh.        */

  /* ── Last-played position (localStorage) ────────────────────────────────────
     Ported to webui/src/catalogCache.ts (_saveLastPlayedLocal/
     _loadLastPlayedLocal) alongside the catalog cache above — same bridge
     pattern, same reasoning.
     Saved on every playItem() start and every saveProgressNow() tick.
     Survives server restarts and page reloads, unlike the in-memory currentIndex.
     Used as the primary (fast, offline) source for _restoreLastEpisode().     */

  /* _applyLocalMutations: ported to webui/src/catalogCache.ts, bridged onto
     window by main.ts (passes window._locallyDeletedPaths explicitly — see
     that file's header comment and the bridge assignment above). Filters
     items returned by a background/silent fetch: removes paths deleted
     client-side this session so they don't reappear before the server has
     rescanned. Also prunes the set once the server confirms the deletion. */

  var currentStreamUrl = '';
  /* currentOfflineUrl: ported to webui/src/offlineUrl.ts (module-private
     state, see that file's header comment) alongside revokeOfflineUrl/
     getOfflineUrl — bridged onto window.getOfflineUrl by main.ts. */
"""
        + (waveform_js)
        + """

  /* ?? Video overlay / float player / mini bar ??
     Ported to webui/src/videoOverlay.ts (state private). Wrappers keep the
     bare names used by _library_tools.py hooks. */
  window._initVideoOverlay({
    player: player, isVideoMode: isVideoMode,
    overlay: videoOverlay, miniBar: videoMiniBar,
    miniTitle: miniTitle, miniArtist: miniArtist, miniThumb: miniThumb,
    miniPlayBtn: miniPlayBtn, miniExpandBtn: miniExpandBtn,
    overlayTitleText: videoOverlayTitleText, videoWrap: videoWrap,
    floatContainer: videoFloatContainer, floatWrap: videoFloatWrap,
    floatCloseBtn: floatCloseBtn, floatExpandBtn: floatExpandBtn,
    closeBtn: videoCloseBtn, icPlay: IC_PLAY, icPause: IC_PAUSE
  });
  function openVideoOverlay() { window._openVideoOverlay(); }
  function _showVidControls() { window._showVidControls(); }
  function _syncMiniBar(t) { window._syncMiniBar(t); }

  /* Background-tab resume (audio + video) ported to webui/src/tabResume.ts; flag private. */
  window._initTabResume({ player: player });

  /* Fullscreen + cast buttons ported to webui/src/videoButtons.ts. */
  window._initFullscreenButton({ button: videoFsBtn, overlay: videoOverlay, player: player });
  window._initCastButton({ button: videoCastBtn, player: player });
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
  /* Button DOM/click/long-press + _intro* state ported to webui/src/introUi.ts
     (legacy calls window._setCurrentIntro / window._updateSkipIntroBtn). */
  window._initIntroUi({
    player: player, button: videoSkipIntroBtn,
    enabled: SKIP_INTRO_ENABLED, isVideoMode: isVideoMode,
    apiPath: INTRO_API_PATH,
    getProgressPath: function() { return window._getProgressPath(); },
    fmtTime: fmtTime, toast: function(m) { showToast(m); }
  });

  /* ── helpers ──
     fmtTime/escHtml/formatBytes used to be defined here as plain function
     declarations. Vite/TS migration Phase 5 first slice (see
     streaming/core/webui/src/main.ts): they are now ported to TypeScript
     and served as window.fmtTime/window.escHtml/window.formatBytes by the
     static bundle _html.py loads BEFORE this inline script (see
     server_utils/_static.py + _html.py::render_media_page). Bare
     identifier references below (`fmtTime(...)`, `escHtml(...)`,
     `formatBytes(...)`) resolve to those globals via the normal JS scope
     chain — do NOT re-add local definitions here (that would silently
     shadow the ported TS version, defeating the whole point of the port —
     see the "single source of truth" rule in copilot-instructions.md). */
  /* showToast: ported to webui/src/toast.ts, bridged onto window by
     main.ts. Was duplicated in _library_tools.py/_track_render.py during
     the fragment split (later decl shadowed this one, custom durationMs
     silently ignored) — one module, one export now. Do NOT re-add a local
     definition here, it would shadow the ported version. */

  /* click-distance guard (_mdX/_mdY/CLICK_MOVE_THRESHOLD + listeners +
     wasDrag): ported to webui/src/clickGuard.ts, installed + bridged onto
     window by main.ts. Bare wasDrag(e) call sites unchanged. */

  /* ── playback progress persistence ── */
  /* Progress state (relPath + timer) + save/load chain: webui/src/progress.ts.
     Wrappers keep bare names; path via window._getProgressPath()/_setProgressPath(). */
  function _progHooks() {
    return {
      player: player, apiPath: API_PATH,
      saveLastPlayedLocal: _saveLastPlayedLocal, showToast: showToast, fmtTime: fmtTime
    };
  }
  function saveProgressNow() { window._saveProgressNow(_progHooks()); }
  function saveProgressDebounced() { window._saveProgressDebounced(_progHooks()); }
  function clearProgressFor(rp) { window._clearProgressFor(rp, _progHooks()); }
  function loadAndSeekProgress(rp) { window._loadAndSeekProgress(rp, _progHooks()); }
  /* Indexing toast (element + per-run dismissal) ported to webui/src/indexingToast.ts. */
  function showIndexingToast(msg, prog) { window._showIndexingToast(msg, prog, escHtml); }
  function hideIndexingToast() { window._hideIndexingToast(); }

  /* ── Lyrics panel ── */
  /* cache/open-state/DOM wiring: webui/src/lyricsPanel.ts. Wrappers keep the
     bare names used by _queue.py / _library_tools.py. */
  window._lyrics = window._initLyricsPanel({
    enabled: LYRICS_ENABLED, apiPath: LYRICS_API_PATH, escHtml: escHtml,
    getCurrentTrack: function() { return filteredItems[currentIndex] || playlistItems[currentIndex]; }
  });
  function openLyricsPanel(relativePath, trackTitle) { window._lyrics.open(relativePath, trackTitle); }
  function closeLyricsPanel() { window._lyrics.close(); }

  /* Queue (Warteschlange): panel DOM, open flag, height, wiring, data ops in
     webui/src/queueController.ts. Wrappers keep bare names for unported callers. */
  var _queueCtl = window._initQueueController({
    itemNoun: ITEM_NOUN, filePlaceholder: FILE_PLACEHOLDER, icRemove: IC_REMOVE,
    esc: escHtml, toast: showToast,
    playItem: function(item, i) { playItem(item, i); },
    lyricsOpen: function() { return window._lyrics.isOpen(); },
    closeLyrics: function() { closeLyricsPanel(); }
  });
  function addToQueue(item) { _queueCtl.add(item); }
  function removeFromQueue(index) { _queueCtl.remove(index); }
  function playFromQueue(index) { _queueCtl.playFrom(index); }
  function updateQueueButtons() { _queueCtl.updateButtons(); }

  /** Dequeue next item from queue — returns true if an item was played */
"""
    )
