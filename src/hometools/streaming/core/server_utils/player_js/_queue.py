"""JS fragment: queue (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_queue_js(sprite_preview_js, waveform_setup_js) -> str:
    """Return the queue section of the player JS."""
    return (
        """  /* dequeueNext/playNextItem ported to webui/src/playNext.ts. */
  var _playNextHooks = {
    player: player,
    playFromQueue: function(i) { playFromQueue(i); },
    playTrack: function(i) { playTrack(i); },
    setWasPlaying: function(v) { window._setWasPlaying(v); },
    showStopped: function() { btnPlay.innerHTML = IC_PLAY; }
  };
  function dequeueNext() { return window._dequeueNext(_playNextHooks); }
  function playNextItem() { window._playNextItem(_playNextHooks); }

  /* Catalog fetch/refresh orchestration ported to webui/src/catalogFetch.ts
     (timer + in-flight flag private). Every successful fetch must call
     saveCache (-> _saveCatalogCache); refreshCatalog clears the cache first. */
  var _catalogFetchHooks = {
    apiPath: API_PATH,
    showIndexingToast: function(d, c) { showIndexingToast(d, c); },
    hideIndexingToast: function() { hideIndexingToast(); },
    applyLocalMutations: function(items) { return _applyLocalMutations(items); },
    invalidateCaches: function() { _invalidateDupeMap(); _invalidateFolderCache(); },
    saveCache: function(items) { _saveCatalogCache(items); },
    clearCache: function() { _clearCatalogCache(); },
    /* Clear in place (never reassign `= {}`) - window._locallyDeletedPaths
       must keep pointing at this same object. */
    clearLocalDeleted: function() {
      Object.keys(_locallyDeletedPaths).forEach(function(k) { delete _locallyDeletedPaths[k]; });
    },
    resetRatingRefresh: function() { window._resetRatingRefresh(); },
    showFolderView: function() { showFolderView(); },
    itemsUnder: function(p) { return itemsUnder(p); },
    applyFilter: function() { applyFilter(); },
    toast: function(m) { showToast(m); }
  };
  function scheduleBackgroundRefresh(delay) { window._scheduleBackgroundRefresh(_catalogFetchHooks, delay); }
  function forceBackgroundRefresh() { window._forceBackgroundRefresh(_catalogFetchHooks); }
  function _triggerSilentRefresh() { window._triggerSilentRefresh(_catalogFetchHooks); }
  function _refreshPoll() { window._refreshPoll(_catalogFetchHooks); }
  function refreshCatalog() { window._refreshCatalog(_catalogFetchHooks); }
  /* Extra library folders (video only): webui/src/extraFolders.ts */
  function _extraHooks() {
    return {
      apiBase: API_PATH.substring(0, API_PATH.lastIndexOf('/')),
      isVideo: ITEM_NOUN === 'video',
      toast: showToast, refreshCatalog: refreshCatalog, showFolderView: showFolderView
    };
  }
  function addExtraFolder() { window._addExtraFolder(_extraHooks()); }
  function removeExtraFolder() { window._removeExtraFolder(_extraHooks()); }
  window._loadExtraFolders(_extraHooks());

  /* Delegated click-handler for the dynamically rendered refresh-catalog-card in the tools-row */
  if (folderGrid) {
    folderGrid.addEventListener('click', function(e) {
      if (e.target.closest('.refresh-catalog-card')) refreshCatalog();
      if (e.target.closest('#add-folder-card')) addExtraFolder();
      if (e.target.closest('#remove-folder-card')) removeExtraFolder();
    });
  }

  /* ── Lazy per-folder rating refresh: webui/src/ratingRefresh.ts ── */
  function refreshFolderRatings(folderItems) {
    window._refreshFolderRatings(folderItems, {
      enabled: !!RATING_WRITE_ENABLED,
      apiBase: API_PATH.substring(0, API_PATH.lastIndexOf('/')),
      applyFilter: function() { applyFilter(); }
    });
  }

"""
        + (waveform_setup_js)
        + (sprite_preview_js)
        + """

  /* itemsUnder: ported to webui/src/catalogQuery.ts (window._itemsUnder,
     pure, allItems explicit param — closure read not reachable from a
     Vite module). Thin wrapper keeps the bare name for all existing
     call sites unchanged. */
  function itemsUnder(path) {
    return window._itemsUnder(path, allItems);
  }

  /* IGNORED_FOLDERS moved to webui/src/folderContents.ts with contentsAt. */

  /* detectLangFromName/detectSubLangFromName: ported to
     webui/src/langDetect.ts, bridged onto window by main.ts. */

  /* cleanFolderName() now lives in webui/src/breadcrumb.ts, bridged onto
     window (see main.ts) — this bare identifier resolves through the
     normal JS scope chain to window.cleanFolderName. */

  /* langBadgesHtml/compositeFlagHtml: ported to webui/src/langDetect.ts
     (LANG_TO_FLAG explicit param). Wrappers keep bare names. */
  function langBadgesHtml(langs) {
    return window._langBadgesHtml(langs, LANG_TO_FLAG);
  }

  function compositeFlagHtml(mainLang, subLang) {
    return window._compositeFlagHtml(mainLang, subLang, LANG_TO_FLAG);
  }

  /* contentsAt: ported to webui/src/folderContents.ts (allItems +
     LANG_GROUPS explicit). Bare-name wrapper keeps all call sites. */
  function contentsAt(path) {
    return window._contentsAt(path, allItems, LANG_GROUPS);
  }

  /* leafName()/parentPath() now live in webui/src/pathUtils.ts, bridged
     onto window (see main.ts) — these bare identifiers resolve through
     the normal JS scope chain to window.leafName/window.parentPath. */

  function showLoadingState(message) {
    /* Header/toolbar via the shared folder-grid entry point
       (_folder_browse.py::_enterFolderGridView) — same structure as
       normal browse/empty/error views. disableSearch: catalog not
       loaded yet, search would query an empty list. */
    _enterFolderGridView({
      playAllDisabled: true,
      disableSearch: true,
      trackCount: 'Loading…',
      contentHtml: '<div class="empty-hint">' + escHtml(message || 'Loading library…') + '</div>'
    });
  }

  function showCatalogLoadError(detail) {
    /* Back button: disabled class like every other view — the old
       style.display='none' here was the only place hiding it outright
       (and nothing ever reset the inline style → header drift). */
    _enterFolderGridView({
      playAllDisabled: true,
      disableSearch: true,
      trackCount: 'Library unavailable',
      contentHtml: '<div class="empty-hint">' + escHtml(detail || 'Library could not be loaded.') + '</div>'
    });
  }

  /* loadInitialCatalog (stale-while-revalidate startup load + retry state)
     ported to webui/src/catalogFetch.ts. */
  function loadInitialCatalog() {
    return window._loadInitialCatalog(Object.assign({}, _catalogFetchHooks, {
      loadCache: function() { return _loadCatalogCache(); },
      showLoadingState: function(m) { showLoadingState(m); },
      showCatalogLoadError: function(m) { showCatalogLoadError(m); },
      autoRefreshOn: function() { return ((_toolState && _toolState.autoRefresh) || 'auto') !== 'off'; }
    }));
  }
  /* ── breadcrumb ──────────────────────────────────────────────────────
     Lives inline in the header (between the Home button and the flexible
     spacer, see docs/IMPLEMENTATION_PLAN.md "UI-Template-Vereinheitlichung").
     Only the path segments are rendered — no redundant "Home" entry, since
     the header-logo button already covers that. When visible, hides
     `.logo-title` so the current folder name isn't shown twice.
     Markup + DOM wiring ported to `webui/src/breadcrumb.ts::renderBreadcrumb()`
     (currentPath via htState). Extend breadcrumb.ts, don't re-inline. */
  function renderBreadcrumb() {
    window._renderBreadcrumb({
      breadcrumb: breadcrumb, headerTitle: headerTitle, escHtml: escHtml,
      showFolderView: function() { showFolderView(); }
    });
  }

  /* ── view toggle ── */
  var IC_GRID = '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>';
  var IC_LIST = '<svg viewBox="0 0 24 24"><circle cx="4" cy="6" r="1.6" fill="currentColor"/><circle cx="4" cy="12" r="1.6" fill="currentColor"/><circle cx="4" cy="18" r="1.6" fill="currentColor"/><line x1="9" y1="6" x2="21" y2="6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="9" y1="12" x2="21" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="9" y1="18" x2="21" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
  var IC_FILENAMES = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="14" y2="6"/><line x1="3" y1="12" x2="18" y2="12"/><line x1="3" y1="18" x2="11" y2="18"/><polyline points="17,15 20,18 17,21" stroke-linejoin="round"/></svg>';
  var IC_TABLE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="1"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="9" y1="10" x2="9" y2="20"/><line x1="15" y1="10" x2="15" y2="20"/></svg>';
  /* Track-list table/rows toggle ported to webui/src/trackViewMode.ts
     (trackViewMode itself stays here, read by rendering). */
  function _trackViewHooks() {
    return {
      trackList: trackList, trackView: trackView, viewToggle: viewToggle,
      isVideoMode: isVideoMode, tableHeaderHtml: window._trackTableHeaderHtml,
      icList: IC_LIST, icTable: IC_TABLE,
      getMode: function() { return trackViewMode; },
      setMode: function(m) { trackViewMode = m; },
      rerender: function() { renderTracks(playlistItems.length ? playlistItems : filteredItems, true); }
    };
  }
  function _toggleTrackViewMode() { window._toggleTrackViewMode(_trackViewHooks()); }
  function _applyTrackViewMode() { window._applyTrackViewMode(_trackViewHooks()); }
  function _isTrackViewVisible() { return window._isTrackViewVisible(trackView); }
  function applyViewMode() {
    if (_isTrackViewVisible()) {
      /* Track (playlist/folder) view is showing — the toggle button
         controls the detail/table view instead of the folder grid mode. */
      _applyTrackViewMode();
      return;
    }
    window._applyFolderViewMode({
      folderGrid: folderGrid, viewToggle: viewToggle, icList: IC_LIST, icGrid: IC_GRID,
      toolActive: _anyToolActive(), viewMode: viewMode
    });
  }

  /* ── folder view ── */

"""
    )
