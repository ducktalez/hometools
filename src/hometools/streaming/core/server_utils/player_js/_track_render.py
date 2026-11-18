"""JS fragment: track render wrappers (logic in webui/src/trackRenderWiring.ts)."""

from __future__ import annotations


def render_track_render_js() -> str:
    """Return the track render section of the player JS."""
    return """  /* renderTracks, offline library (+ active downloads), download buttons, recently played,
     tools panel, BPM menu, inline rating markup: webui/src/trackRenderWiring.ts.
     Legacy callbacks via the deps thunk (resolved per call). Wrappers keep bare names. */
  var OFFLINE_SOFT_LIMIT = 500 * 1024 * 1024;
  var _trw = window._createTrackRenderWiring({
    itemNoun: ITEM_NOUN, debugFilter: DEBUG_FILTER, softLimit: OFFLINE_SOFT_LIMIT,
    recentApiPath: RECENT_API_PATH, filePlaceholder: FILE_PLACEHOLDER,
    ratingWriteEnabled: !!RATING_WRITE_ENABLED,
    icDl: IC_DL, icCheck: IC_CHECK, icStarFilled: IC_STAR_FILLED, icStarEmpty: IC_STAR_EMPTY,
    icChevronsDown: IC_CHEVRONS_DOWN, icRefresh: IC_REFRESH, icChevronsUp: IC_CHEVRONS_UP,
    bpmCalcApiPath: BPM_CALC_API_PATH, bpmAdjustApiPath: BPM_ADJUST_API_PATH, bpmSetApiPath: BPM_SET_API_PATH,
    bpmMin: BPM_MIN, bpmMax: BPM_MAX
  }, function() {
    return {
      esc: escHtml, toast: showToast, formatBytes: formatBytes,
      getFilter: function() { return { rating: _view.filterRating, fav: _view.filterFav, genre: _view.filterGenre }; },
      effectiveThreshold: function() { return _effectiveThreshold; },
      showHidden: function() { return _view.showHidden; },
      stopRenderObserver: _stopRenderObserver, startWindowedRender: _startWindowedRender,
      markActive: markActive, openTrackPicker: openTrackPicker,
      applyFilter: applyFilter, showFolderView: showFolderView, showPlaylist: showPlaylist,
      playItem: playItem, enterTrackListView: _enterTrackListView,
      destroyPlaylistDragDrop: destroyPlaylistDragDrop, applyViewMode: applyViewMode,
      updatePlayerBarActions: updatePlayerBarActions, invalidateDupeMap: _invalidateDupeMap,
      refreshCatalog: refreshCatalog, playDuplicates: playDuplicates, closeDupePanel: closeDupePanel,
      routerUpdate: function() { if (typeof _router !== 'undefined') _router.update(); }
    };
  });
  function renderTracks(tracks, force) { _trw.renderTracks(tracks, force); }
  function cancelDownload(streamUrl, btn) { _trw.cancelDownload(streamUrl, btn); }
  function refreshOfflineLibrary() { return _trw.refreshOfflineLibrary(); }
  function openOfflineLibrary() { _trw.openOfflineLibrary(); }
  function ensureStorageBudget(requiredBytes, protectedStreamUrl) {
    return _trw.ensureStorageBudget(requiredBytes, protectedStreamUrl);
  }
  function closeOfflineLibrary() { _trw.closeOfflineLibrary(); }
  function updateOfflineFolderCount() { _trw.updateOfflineFolderCount(); }
  function loadRecentlyPlayed() { _trw.loadRecentlyPlayed(); }
  function updateAllDownloadButtons() { _trw.updateAllDownloadButtons(); }
  function downloadTrack(streamUrl, title, btn, meta) { _trw.downloadTrack(streamUrl, title, btn, meta); }
  function deleteTrackDownload(streamUrl, btn) { _trw.deleteTrackDownload(streamUrl, btn); }
  function checkIfMediaCached(streamUrl) { return _trw.checkIfMediaCached(streamUrl); }
  function getOfflineUrl(blob) { return window.getOfflineUrl(blob); }
  function playOfflineOrStream(streamUrl) { return _trw.playOfflineOrStream(streamUrl); }
  function _anyToolActive() { return _trw.anyToolActive(); }
  function _toolFlags() { return _trw.toolFlags(); }
  function openToolsPanel() { _trw.openToolsPanel(); }
  function closeToolsPanel() { _trw.closeToolsPanel(); }
  function renderInlineRating(t, idx) { return _trw.renderInlineRating(t, idx); }
  /* Row rating (POST, relocate playing track, undo toast): webui/src/rating.ts::setInlineRating. */
  function setInlineRating(idx, stars) { _lw.setInlineRating(idx, stars); }
  function _openBpmAdjustMenu(idx, btnEl) { _trw.openBpmAdjustMenu(idx, btnEl); }

  var IC_DUPLICATE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>';

"""
