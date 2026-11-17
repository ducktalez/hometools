"""JS fragment: search/filter wrappers (logic in webui/src/searchFilterWiring.ts)."""

from __future__ import annotations


def render_search_filter_js() -> str:
    """Return the search filter section of the player JS."""
    return """  /* Global search, filter pipeline/chips/popover, windowed render, row select,
     player-bar nav/actions, track-list delegation, inline edit:
     webui/src/searchFilterWiring.ts. State via htState; DOM via dom.ts; legacy
     callbacks via the deps thunk (resolved per call). Wrappers keep bare names. */
  var _sfw = window._createSearchFilterWiring({
    itemNoun: ITEM_NOUN, filePlaceholder: FILE_PLACEHOLDER,
    icons: {
      folderPlay: IC_FOLDER_PLAY, filter: IC_FILTER, eye: IC_EYE,
      starFilled: IC_STAR_FILLED, starEmpty: IC_STAR_EMPTY,
      trash: IC_TRASH, dl: IC_DL, pin: IC_PIN, edit: IC_EDIT,
      playlist: IC_PLAYLIST, queue: IC_QUEUE, dots: IC_DOTS
    },
    debugFilter: DEBUG_FILTER, batchSize: _RENDER_BATCH_SIZE, isVideoMode: isVideoMode,
    metadataEditEnabled: !!METADATA_EDIT_ENABLED, playlistsEnabled: !!PLAYLISTS_ENABLED,
    metadataEditPath: METADATA_EDIT_PATH, bpmMin: BPM_MIN, bpmMax: BPM_MAX
  }, function() {
    return {
      effectiveThreshold: function() { return _effectiveThreshold; },
      showHidden: function() { return _view.showHidden; },
      viewMode: function() { return _view.viewMode; },
      trackViewMode: function() { return _view.trackViewMode; },
      getFilter: function() { return { rating: _view.filterRating, fav: _view.filterFav, genre: _view.filterGenre }; },
      setFilter: function(p) {
        if (p.rating !== undefined) _view.filterRating = p.rating;
        if (p.fav !== undefined) _view.filterFav = p.fav;
        if (p.genre !== undefined) _view.filterGenre = p.genre;
      },
      locallyDeleted: function() { return _locallyDeletedPaths; },
      esc: escHtml, fmtTime: fmtTime, toast: showToast,
      anyToolActive: _anyToolActive, toolFlags: _toolFlags,
      currentDupeIndex: function() { return window._currentDupeIndex(); },
      renderBpmPill: window.renderBpmPill, renderInlineRating: renderInlineRating, renderMoveWidget: renderMoveWidget,
      showFolderView: showFolderView, showPlaylist: showPlaylist, enterTrackListView: _enterTrackListView,
      playItem: playItem, contentsAt: contentsAt, itemsUnder: itemsUnder, renderTracks: renderTracks,
      updateFavoriteButtons: updateFavoriteButtons, updateAllDownloadButtons: updateAllDownloadButtons,
      updateQueueButtons: updateQueueButtons, initPlaylistDragDrop: initPlaylistDragDrop,
      renderFilterPopoverBody: _renderFilterPopoverBody,
      routerUpdate: function() { if (typeof _router !== 'undefined') _router.update(); },
      getAllFolders: _getAllFolders, moveFileToFolder: moveFileToFolder,
      deleteTrackFromList: _deleteTrackFromList, openTrackCtxMenu: _openTrackCtxMenu,
      setInlineRating: setInlineRating, openBpmAdjustMenu: _openBpmAdjustMenu,
      deleteTrackDownload: deleteTrackDownload, cancelDownload: cancelDownload,
      downloadTrack: downloadTrack, toggleFavorite: toggleFavorite, openEditModal: openEditModal,
      loadUserPlaylists: loadUserPlaylists, openPlaylistModal: openPlaylistModal,
      removeFromQueue: removeFromQueue, addToQueue: addToQueue,
      revealInExplorer: _revealInExplorer, playTrack: playTrack
    };
  });
  function globalSearch(needle) { _sfw.globalSearch(needle); }
  function exitGlobalSearch() { _sfw.exitGlobalSearch(); }
  function playAllCurrent() { _sfw.playAllCurrent(); }
  function updateFilterChips() { _sfw.updateFilterChips(); }
  function applyFilter(force) { _sfw.applyFilter(force); }
  function _renderFilterPopoverBody() { _sfw.renderFilterPopoverBody(); }
  function _closeFilterPopover() { _sfw.closeFilterPopover(); }
  function _toggleFilterPopover(btn) { _sfw.toggleFilterPopover(btn); }
  function _stopRenderObserver() { _sfw.stopRenderObserver(); }
  function _appendTrackBatch() { _sfw.appendTrackBatch(); }
  function _ensureRenderedTo(idx) { _sfw.ensureRenderedTo(idx); }
  function markActive() { _sfw.markActive(); }
  function _startWindowedRender(realTracks) { _sfw.startWindowedRender(realTracks); }
  function _selectTrackRow(idx) { _sfw.selectTrackRow(idx); }
  function jumpToCurrentTrack() { _sfw.jumpToCurrentTrack(); }
  function updatePlayerBarActions() { _sfw.updatePlayerBarActions(); }
  /* Re-render player bar actions when tool mode changes */
  function _onToolModeChange() { updatePlayerBarActions(); }
  function _wireTrackListDelegation() { _sfw.wireTrackListDelegation(); }
  function _saveInlineTableEdit(editable) { _sfw.saveInlineTableEdit(editable); }

"""
