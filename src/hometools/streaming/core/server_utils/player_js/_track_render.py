"""JS fragment: track render (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_track_render_js() -> str:
    """Return the track render section of the player JS."""
    return """  /* renderTracks (render guard, count label, empty states): webui/src/trackRender.ts.
     Render-guard key private there; reset via window._resetRenderGuard(). */
  function _renderTracksHooks() {
    return {
      itemNoun: ITEM_NOUN, debugFilter: DEBUG_FILTER,
      trackList: trackList, trackCount: trackCount, searchInput: searchInput, sortField: sortField,
      getFilter: function() { return { rating: filterRating, fav: filterFav, genre: filterGenre }; },
      effectiveThreshold: function() { return _effectiveThreshold; },
      showHidden: function() { return showHidden; },
      stopRenderObserver: _stopRenderObserver,
      startWindowedRender: _startWindowedRender,
      markActive: markActive,
      openTrackPicker: openTrackPicker
    };
  }
  function renderTracks(tracks, force) { window._renderTracks(tracks, force, _renderTracksHooks()); }


  /* -- offline downloads -- */
  var OFFLINE_SOFT_LIMIT = 500 * 1024 * 1024;
  var activeDownloads = {};

  function cancelDownload(streamUrl, btn) {
    window._cancelDownload(streamUrl, btn, activeDownloads, { icDl: IC_DL, toast: showToast });
  }

  /* Offline library (refresh/open/budget/prune/persist, SW listener, pill/sort/close wiring):
     webui/src/offlineLibrary.ts. IndexedDB: offlineDb.ts (DB name/version = SW contract). */
  var _offlineLib = window._initOfflineLibrary({
    itemNoun: ITEM_NOUN, softLimit: OFFLINE_SOFT_LIMIT, formatBytes: formatBytes,
    currentStreamUrl: function() { return currentStreamUrl; },
    updateDownloadButtons: function() { updateAllDownloadButtons(); },
    applyFilter: function() { applyFilter(); },
    showFolderView: function() { showFolderView(); },
    enterTrackListView: function(o) { _enterTrackListView(o); },
    destroyPlaylistDragDrop: function() { destroyPlaylistDragDrop(); }
  });
  function refreshOfflineLibrary() { return _offlineLib.refresh(); }
  function openOfflineLibrary() { _offlineLib.open(); }
  function ensureStorageBudget(requiredBytes, protectedStreamUrl) {
    return _offlineLib.ensureStorageBudget(requiredBytes, protectedStreamUrl);
  }
  function closeOfflineLibrary() { window._closeOfflineLibrary({ showFolderView: showFolderView }); }
  function updateOfflineFolderCount() { window._updateOfflineFolderCount(downloadedPill); }

  /* -- Recently played section: webui/src/recentlyPlayed.ts -- */
  function loadRecentlyPlayed() {
    window._loadRecentlyPlayed({
      apiPath: RECENT_API_PATH, esc: escHtml, placeholder: FILE_PLACEHOLDER, player: player,
      showPlaylist: showPlaylist, playItem: playItem
    });
  }



  function updateAllDownloadButtons() {
    window._updateAllDownloadButtons({ icDl: IC_DL, icCheck: IC_CHECK });
  }

  /* downloadTrack/deleteTrackDownload/checkIfMediaCached/playOfflineOrStream:
     webui/src/downloadButtons.ts. activeDownloads + storage budget stay here. */
  function _dlHooks() {
    return {
      icDl: IC_DL, icCheck: IC_CHECK, itemNoun: ITEM_NOUN,
      softLimit: OFFLINE_SOFT_LIMIT, formatBytes: formatBytes,
      ensureStorageBudget: ensureStorageBudget, toast: showToast,
      refreshLibrary: refreshOfflineLibrary, updateButtons: updateAllDownloadButtons
    };
  }
  function downloadTrack(streamUrl, title, btn, meta) {
    window._downloadTrack(streamUrl, title, btn, meta, activeDownloads, _dlHooks());
  }

  function deleteTrackDownload(streamUrl, btn) {
    window._deleteTrackDownload(streamUrl, btn, _dlHooks());
  }

  function checkIfMediaCached(streamUrl) { return window._checkIfMediaCached(streamUrl); }

  function getOfflineUrl(blob) {
    return window.getOfflineUrl(blob);
  }

  function playOfflineOrStream(streamUrl) { return window._playOfflineOrStream(streamUrl); }

  /* ── Tools panel ──
     Tool state (ht-tools), body classes, toggles, split-pill, dupe link:
     webui/src/toolsPanel.ts. Legacy reads flags via _toolFlags()/_anyToolActive(). */
  function _anyToolActive() { return window._anyToolActive(); }
  function _toolFlags() { return window._toolFlags(); }
  function openToolsPanel() { window._openToolsPanel(); }
  function closeToolsPanel() { window._closeToolsPanel(); }
  window._initToolsPanel({
    folderGrid: folderGrid,
    showFolderView: function() { showFolderView(); },
    applyViewMode: function() { applyViewMode(); },
    applyFilter: function(force) { applyFilter(force); },
    updatePlayerBarActions: function() { updatePlayerBarActions(); },
    invalidateDupeMap: function() { _invalidateDupeMap(); },
    refreshCatalog: function() { refreshCatalog(); },
    playDuplicates: function() { playDuplicates(); },
    closeDupePanel: function() { closeDupePanel(); },
    routerUpdate: function() { if (typeof _router !== 'undefined') _router.update(); }
  });

  /* ── Inline track rating stars ── */
  /* markup: webui/src/inlineWidgets.ts::inlineRatingHtml */
  function renderInlineRating(t, idx) {
    return window._inlineRatingHtml(t.rating, idx, !!RATING_WRITE_ENABLED, IC_STAR_FILLED, IC_STAR_EMPTY);
  }

  /* Row rating (POST, relocate playing track, undo toast): webui/src/rating.ts::setInlineRating. */
  function setInlineRating(idx, stars) { window._setInlineRating(idx, stars, _ratingHooks()); }


  /* ── BPM adjust popup (Tools-panel "BPM berechnen") ──
     webui/src/bpmMenu.ts (cleanup handle private). Click handler for the BPM pill
     rendered by window.renderBpmPill() (webui/src/metricPill.ts). */
  function _openBpmAdjustMenu(idx, btnEl) {
    window._openBpmAdjustMenu(idx, btnEl, {
      calcPath: BPM_CALC_API_PATH, adjustPath: BPM_ADJUST_API_PATH, setPath: BPM_SET_API_PATH,
      bpmMin: BPM_MIN, bpmMax: BPM_MAX,
      icons: { chevronsDown: IC_CHEVRONS_DOWN, refresh: IC_REFRESH, chevronsUp: IC_CHEVRONS_UP },
      calcEnabled: function() { var f = _toolFlags(); return !!(f.active && f.bpmCalc); },
      toast: showToast
    });
  }

  /* ── Duplicate detection (client-side) ── */
  var IC_DUPLICATE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>';
  /* Dupe index state: webui/src/dupeState.ts. Helpers (_isDupeGroupSafe, formatters):
     webui/src/dupeUtils.ts, bridged onto window by main.ts. */

"""
