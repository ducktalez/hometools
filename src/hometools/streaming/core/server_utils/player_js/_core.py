"""JS fragment: core (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_core_js(waveform_js) -> str:
    """Return the core section of the player JS."""
    return (
        """  /* Language names ported to webui/src/langNames.ts. */
  var _LANG_NAME_MAP = window._LANG_NAME_MAP;

  /* Core state (allItems, currentPath, playlistItems, filteredItems, currentIndex,
     inPlaylist, shuffle*, repeatMode): _pb, see playbackState.ts. */
  /* Paths deleted client-side this session. Set on confirm (before POST /delete)
     so a concurrent silent refresh can't re-add them; filtered in every
     background catalog fetch; cleared on manual refresh. */
  var _locallyDeletedPaths = {};
  /* Bridge onto window — read/mutated by _applyLocalMutations() (ported to
     webui/src/catalogCache.ts, bridged via main.ts). Object reference only:
     any in-place clear (delete/assign keys) elsewhere in this script stays
     visible through window._locallyDeletedPaths; never reassign this var
     with `= {}` (that would silently break the bridge — see refreshCatalog()
     in _queue.py which clears keys in place instead). */
  window._locallyDeletedPaths = _locallyDeletedPaths;

  /* Queue / user-playlist state lives in _pb (webui/src/playbackState.ts). */

  /* State bridge for ported TS modules (webui/src/stateBridge.ts): htState IS
     the TS-owned object _pb (webui/src/playbackState.ts). */
  var _pb = window._createPlaybackState(Array.isArray(INITIAL) ? INITIAL : []);
  window.htState = _pb;

  /* DOM refs: webui/src/dom.ts (single id/selector table). */
  var _dom = window._getDom();
  var player       = _dom.player;
  var btnPlay      = _dom.btnPlay;
  var btnPrev      = _dom.btnPrev;
  var btnNext      = _dom.btnNext;
  var btnShuffle   = _dom.btnShuffle;
  var btnRepeat    = _dom.btnRepeat;
  var trackList    = _dom.trackList;
  var trackCount   = _dom.trackCount;
  var playerTitle  = _dom.playerTitle;
  var playerArtist = _dom.playerArtist;
  var playerThumb  = _dom.playerThumb;
  var playerBarActions = _dom.playerBarActions;
  var progressBar  = _dom.progressBar;
  var timeCur      = _dom.timeCur;
  var timeDur      = _dom.timeDur;
  var searchInput  = _dom.searchInput;
  var sortField    = _dom.sortField;
  var filterCombinedBtn = _dom.filterCombinedBtn;
  var filterHiddenBtn = _dom.filterHiddenBtn;
  /* Persisted filter/view state: webui/src/viewState.ts. Fields: filterRating,
     filterFav, filterGenre, showHidden (hidden items greyed), viewMode (folder
     grid/list), trackViewMode (rows/table; audio only). */
  var _view = window._initViewState(player.tagName === 'VIDEO');
  /* _pb.justRatedPath: just-rated track never fully hidden by filters (see playbackState.ts). */
  /* Combined "Filtern" popover (Bewertung + Favorit + Genre) — see
     docs/IMPLEMENTATION_PLAN.md "UI-Template-Vereinheitlichung" Phase 2. */
  var folderGrid   = _dom.folderGrid;
  var trackView    = _dom.trackView;
  var filterBar    = _dom.filterBar;
  var backBtn      = _dom.backBtn;
  var logoHomeBtn  = _dom.logoHomeBtn;
  var headerTitle  = _dom.headerTitle;
  var playerBar    = _dom.playerBar;
  /* ── Video overlay (video-mode only) ── */
  var videoOverlay   = _dom.videoOverlay;
  var videoMiniBar   = _dom.videoMiniBar;
  var miniTitle      = _dom.miniTitle;
  var miniArtist     = _dom.miniArtist;
  var miniThumb      = _dom.miniThumb;
  var miniPlayBtn    = _dom.miniPlayBtn;
  var miniExpandBtn  = _dom.miniExpandBtn;
  var videoCloseBtn  = _dom.videoCloseBtn;
  var videoFsBtn     = _dom.videoFsBtn;
  var videoCastBtn   = _dom.videoCastBtn;
  var videoSkipIntroBtn = _dom.videoSkipIntroBtn;
  var videoOverlayTitleText = _dom.videoOverlayTitleText;
  var videoFloatContainer = _dom.videoFloatContainer;
  var videoFloatWrap   = _dom.videoFloatWrap;
  var floatExpandBtn   = _dom.floatExpandBtn;
  var floatCloseBtn    = _dom.floatCloseBtn;
  var videoWrap        = _dom.videoWrap;
  /* In video-mode the overlay controls visibility; playerBar points to
     the .player-bar INSIDE the overlay, so existing classList calls work
     on the inner controls and the overlay is managed separately. */
  var playAllBtn   = _dom.playAllBtn;
  var downloadedPill = _dom.downloadedPill;
  var originalTitle = headerTitle.textContent;
  /* Bridge onto window — read by the ported leafName() (webui/src/pathUtils.ts,
     bridged via main.ts). A plain `var` here is scoped to this IIFE, not a
     real global, so the .ts module (a separate closure) can't see it
     otherwise; see legacy-globals.d.ts's header comment on this pattern. */
  window.originalTitle = originalTitle;
  var breadcrumb  = _dom.breadcrumb;
  var viewToggle  = _dom.viewToggle;

  /* ── Windowed track rendering state ──────────────────────────────────────
     Instead of building one massive HTML string for all N items and setting
     innerHTML at once, we render _RENDER_BATCH_SIZE items at a time.  An
     IntersectionObserver on a sentinel <li> at the bottom of the list triggers
     each subsequent batch as the user scrolls down.  This keeps the initial
     render near-instant even for 6000-item playlists.

     _rgKey  — render-guard fingerprint, now private to webui/src/trackRender.ts
               (reset via window._resetRenderGuard()).                          */
  var _RENDER_BATCH_SIZE  = 100;

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

  /* Playback scratch state: webui/src/playbackState.ts (_pb, created above). */
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
    getCurrentTrack: function() { return _pb.filteredItems[_pb.currentIndex] || _pb.playlistItems[_pb.currentIndex]; }
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
