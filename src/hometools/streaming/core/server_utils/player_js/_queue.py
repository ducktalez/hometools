"""JS fragment: queue (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_queue_js(sprite_preview_js, waveform_setup_js) -> str:
    """Return the queue section of the player JS."""
    return (
        """  /* Play-next, catalog fetch/refresh, extra folders, lazy rating refresh:
     webui/src/catalogWiring.ts (_cw). Every successful fetch saves the cache
     (-> _saveCatalogCache); refreshCatalog clears it first. */
  var _cw = window._createCatalogWiring({
    apiPath: API_PATH, apiBase: API_PATH.substring(0, API_PATH.lastIndexOf('/')),
    isVideo: ITEM_NOUN === 'video', ratingWriteEnabled: !!RATING_WRITE_ENABLED, icPlay: IC_PLAY
  }, function() {
    return {
      playFromQueue: playFromQueue, playTrack: playTrack,
      showIndexingToast: showIndexingToast, hideIndexingToast: hideIndexingToast,
      applyLocalMutations: _applyLocalMutations,
      invalidateDupeMap: _invalidateDupeMap, invalidateFolderCache: _invalidateFolderCache,
      saveCatalogCache: _saveCatalogCache, clearCatalogCache: _clearCatalogCache,
      clearLocalDeleted: function() {
        Object.keys(_locallyDeletedPaths).forEach(function(k) { delete _locallyDeletedPaths[k]; });
      },
      showFolderView: showFolderView, itemsUnder: itemsUnder, applyFilter: applyFilter, toast: showToast
    };
  });
  function dequeueNext() { return _cw.dequeueNext(); }
  function playNextItem() { _cw.playNextItem(); }
  function scheduleBackgroundRefresh(delay) { _cw.scheduleBackgroundRefresh(delay); }
  function forceBackgroundRefresh() { _cw.forceBackgroundRefresh(); }
  function _triggerSilentRefresh() { _cw.triggerSilentRefresh(); }
  function _refreshPoll() { _cw.refreshPoll(); }
  function refreshCatalog() { _cw.refreshCatalog(); }
  function addExtraFolder() { _cw.addExtraFolder(); }
  function removeExtraFolder() { _cw.removeExtraFolder(); }
  _cw.loadExtraFolders();

  /* Delegated tools-row card clicks: webui/src/folderGridEvents.ts */
  window._initFolderGridEvents({
    folderGrid: folderGrid,
    refreshCatalog: refreshCatalog,
    addExtraFolder: addExtraFolder,
    removeExtraFolder: removeExtraFolder
  });
  function refreshFolderRatings(folderItems) { _cw.refreshFolderRatings(folderItems); }
"""
        + (waveform_setup_js)
        + (sprite_preview_js)
        + """

  /* itemsUnder: ported to webui/src/catalogQuery.ts (window._itemsUnder,
     pure, allItems explicit param — closure read not reachable from a
     Vite module). Thin wrapper keeps the bare name for all existing
     call sites unchanged. */
  function itemsUnder(path) {
    return window._itemsUnder(path, _pb.allItems);
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
    return window._contentsAt(path, _pb.allItems, LANG_GROUPS);
  }

  /* leafName()/parentPath() now live in webui/src/pathUtils.ts, bridged
     onto window (see main.ts) — these bare identifiers resolve through
     the normal JS scope chain to window.leafName/window.parentPath. */

  /* Loading/error view opts: webui/src/viewEntry.ts::catalogStateOpts. */
  function showLoadingState(message) {
    _enterFolderGridView(window._catalogStateOpts('loading', message, escHtml));
  }

  function showCatalogLoadError(detail) {
    _enterFolderGridView(window._catalogStateOpts('error', detail, escHtml));
  }

  /* loadInitialCatalog (stale-while-revalidate startup load + retry state)
     ported to webui/src/catalogFetch.ts. */
  function loadInitialCatalog() {
    return window._loadInitialCatalog(Object.assign({}, _cw.fetchHooks(), {
      loadCache: function() { return _loadCatalogCache(); },
      showLoadingState: function(m) { showLoadingState(m); },
      showCatalogLoadError: function(m) { showCatalogLoadError(m); },
      autoRefreshOn: function() { return ((_toolFlags() && _toolFlags().autoRefresh) || 'auto') !== 'off'; }
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
     (state in _view, see viewState.ts). */
  function _trackViewHooks() {
    return {
      trackList: trackList, trackView: trackView, viewToggle: viewToggle,
      isVideoMode: isVideoMode, tableHeaderHtml: window._trackTableHeaderHtml,
      icList: IC_LIST, icTable: IC_TABLE,
      getMode: function() { return _view.trackViewMode; },
      setMode: function(m) { _view.trackViewMode = m; },
      rerender: function() { renderTracks(_pb.playlistItems.length ? _pb.playlistItems : _pb.filteredItems, true); }
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
      toolActive: _anyToolActive(), viewMode: _view.viewMode
    });
  }

  /* ── folder view ── */

"""
    )
