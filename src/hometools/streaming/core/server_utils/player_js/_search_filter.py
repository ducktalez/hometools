"""JS fragment: search filter (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_search_filter_js() -> str:
    """Return the search filter section of the player JS."""
    return """  /* Global-search view (globalSearch/renderSearchResults/navigate/exit) ported
     to webui/src/searchView.ts; data in search.ts, rows in trackRows.ts. Shared
     state via htState, view effects via hooks. Wrappers keep bare names. */
  function _searchHooks() {
    return {
      effectiveThreshold: function() { return _effectiveThreshold; },
      showHidden: function() { return showHidden; },
      itemNoun: ITEM_NOUN,
      esc: escHtml,
      filePlaceholder: FILE_PLACEHOLDER,
      icFolderPlay: IC_FOLDER_PLAY,
      trackList: function() { return trackList; },
      enterTrackListView: _enterTrackListView,
      showFolderView: showFolderView,
      playItem: playItem,
      markActive: markActive
    };
  }
  function globalSearch(needle) { window._globalSearch(needle, _searchHooks()); }
  function exitGlobalSearch() { window._exitGlobalSearch(_searchHooks()); }

  /* play all items under current path */
  function playAllCurrent() {
    window._playAllCurrent({
      filesAt: function(p) { return contentsAt(p).files; },
      showPlaylist: showPlaylist
    });
  }

  /* ── filter / sort within playlist ── */
  /* ── Quick-filter chips ──
     Bewertung + Favorit + Genre live in ONE combined "Filtern" popover
     button (filter-combined) instead of three separate chips — see
     docs/IMPLEMENTATION_PLAN.md "UI-Template-Vereinheitlichung" Phase 2.
     "Ausgeblendet" (filterHiddenBtn) stays its own toggle-slot chip. */
  /* _collectPlaylistGenres: ported to webui/src/catalogQuery.ts as
     collectGenres(items) — playlistItems now explicit param. */
  /* Filter chips + filter/sort/render pipeline ported to webui/src/filterApply.ts
     (chain: filterChain.ts, sort: catalogQuery.ts, chip views: filterPopover.ts).
     Filter state/DOM/render come in via hooks. Wrappers keep bare names. */
  function _filterApplyHooks() {
    return {
      combinedBtn: function() { return filterCombinedBtn; },
      hiddenBtn: function() { return filterHiddenBtn; },
      getFilter: function() { return { rating: filterRating, fav: filterFav, genre: filterGenre }; },
      icFilter: IC_FILTER,
      icEye: IC_EYE,
      effectiveThreshold: function() { return _effectiveThreshold; },
      showHidden: function() { return showHidden; },
      refreshOpenPopover: function() {
        if (document.getElementById('ht-filter-popover')) _renderFilterPopoverBody();
      },
      searchValue: function() { return searchInput.value; },
      sortValue: function() { return sortField.value; },
      locallyDeleted: function() { return _locallyDeletedPaths; },
      debugFilter: DEBUG_FILTER,
      justRatedPath: function() { return _justRatedPath; },
      savedFavorites: function() { return _savedFavorites; },
      hasCustomPlaylist: function() { return !!_currentPlaylistId; },
      renderTracks: renderTracks
    };
  }
  function updateFilterChips() { window._updateFilterChips(_filterApplyHooks()); }
  function applyFilter(force) { window._applyFilter(force, _filterApplyHooks()); }

  /* Filter popover (wiring/lifecycle, cleanup handle private) ported to
     webui/src/filterPopoverUi.ts; markup in filterPopover.ts. Filter state is
     shared with this script -> read/written via hooks. */
  function _filterPopoverHooks() {
    return {
      genres: function() { return _collectGenres(playlistItems); },
      getFilter: function() { return { rating: filterRating, fav: filterFav, genre: filterGenre }; },
      setFilter: function(p) {
        if (p.rating !== undefined) filterRating = p.rating;
        if (p.fav !== undefined) filterFav = p.fav;
        if (p.genre !== undefined) filterGenre = p.genre;
      },
      icons: { starFilled: IC_STAR_FILLED, starEmpty: IC_STAR_EMPTY },
      esc: escHtml,
      onChange: function() {
        updateFilterChips();
        applyFilter();
        if (typeof _router !== 'undefined') _router.update();
      }
    };
  }
  function _renderFilterPopoverBody() { window._renderFilterPopoverBody(_filterPopoverHooks()); }
  function _closeFilterPopover() { window._closeFilterPopover(); }
  function _toggleFilterPopover(btn) { window._toggleFilterPopover(btn, _filterPopoverHooks()); }

  /* needsConversion()/filenameFromPath() ported to webui/src/pathUtils.ts
     (Vite/TS migration Phase 5 opportunistic-port slice — see
     docs/IMPLEMENTATION_PLAN.md) — bridged onto window by main.ts, bare
     calls below still resolve via the normal JS scope chain. */

  /* Windowed rendering (window state private; stop/append/ensure/markActive)
     ported to webui/src/trackRenderWindow.ts. Render guard (_rgKey), row-context
     building and button decoration stay here and come in via hooks. */
  function _renderWindowHooks() {
    return {
      trackList: function() { return trackList; },
      batchSize: _RENDER_BATCH_SIZE,
      rowCtx: function() {
        /* BPM "calculate" affordance (yellow-glow clickable "?") is gated by the
           Tools-panel "BPM berechnen" toggle - see _track_render.py::_applyToolState. */
        return {
          escHtml: escHtml, fmtTime: fmtTime, showOrig: _anyToolActive(), currentIndex: currentIndex,
          bpmCalcEnabled: !!(_toolState.active && _toolState.bpmCalc),
          trackViewMode: trackViewMode, isVideoMode: isVideoMode,
          metadataEditEnabled: !!METADATA_EDIT_ENABLED, playlistsEnabled: !!PLAYLISTS_ENABLED,
          itemNoun: ITEM_NOUN, bpmMin: BPM_MIN, bpmMax: BPM_MAX,
          dupePaths: _dupePaths, dupeSafety: _dupeSafety, filePlaceholder: FILE_PLACEHOLDER,
          ic: { folderPlay: IC_FOLDER_PLAY, trash: IC_TRASH, dl: IC_DL, pin: IC_PIN, edit: IC_EDIT,
                playlist: IC_PLAYLIST, queue: IC_QUEUE, dots: IC_DOTS },
          renderBpmPill: window.renderBpmPill,
          renderInlineRating: renderInlineRating, renderMoveWidget: renderMoveWidget
        };
      },
      decorateRows: function() {
        updateFavoriteButtons();
        updateAllDownloadButtons();
        updateQueueButtons();
      },
      maybeInitPlaylistDragDrop: function() {
        if (PLAYLISTS_ENABLED && inPlaylist && _currentPlaylistId && viewMode === 'list') {
          initPlaylistDragDrop();
        }
      },
      wireDelegation: _wireTrackListDelegation
    };
  }
  function _stopRenderObserver() { window._stopRenderObserver(_renderWindowHooks()); }
  function _appendTrackBatch() { window._appendTrackBatch(_renderWindowHooks()); }
  function _ensureRenderedTo(idx) { window._ensureRenderedTo(idx, _renderWindowHooks()); }
  function markActive() { window._markActive(_renderWindowHooks()); }
  function _startWindowedRender(realTracks) { window._startWindowedRender(realTracks, _renderWindowHooks()); }

  /* Desktop-only row click: select/highlight without starting playback.
     Actual playback on hover-capable devices is triggered via the
     dedicated .track-play-btn overlay on the thumbnail. */
  function _selectTrackRow(idx) {
    document.querySelectorAll('.track-item.row-selected').forEach(function(el) {
      el.classList.remove('row-selected');
    });
    var row = trackList.querySelector('.track-item[data-index="' + idx + '"]');
    if (row) row.classList.add('row-selected');
  }

  /* jumpToCurrentTrack + updatePlayerBarActions ported to webui/src/playerNav.ts
     (state via htState, actions via hooks). Wrappers keep bare names. */
  function jumpToCurrentTrack() {
    window._jumpToCurrentTrack({
      ensureRenderedTo: _ensureRenderedTo,
      markActive: markActive,
      itemsUnder: itemsUnder,
      showPlaylist: showPlaylist
    });
  }

  function updatePlayerBarActions() {
    window._updatePlayerBarActions({
      container: function() { return playerBarActions; },
      allFolders: _getAllFolders,
      esc: escHtml,
      icDots: IC_DOTS,
      icTrash: IC_TRASH,
      moveFileToFolder: moveFileToFolder,
      deleteTrackFromList: _deleteTrackFromList,
      openTrackCtxMenu: _openTrackCtxMenu
    });
  }

  /* Re-render player bar actions when tool mode changes */
  function _onToolModeChange() { updatePlayerBarActions(); }

  /* withMissingEpisodes: ported to webui/src/episodeGaps.ts, bridged
     onto window by main.ts. */

  /* ── Event delegation for track list ─────────────────────────────────────
     Wired once per renderTracks call, covers all items added by future
     _appendTrackBatch calls (windowed rendering).                           */
  /* Track-list click/change/focusout/keydown/dblclick delegation ported to
     webui/src/trackListDelegation.ts (handler refs private; dblclick no longer
     stacks on re-wire). Actions come in via hooks. Called once per renderTracks. */
  function _wireTrackListDelegation() {
    window._wireTrackListDelegation(trackList, {
      metadataEditEnabled: !!METADATA_EDIT_ENABLED,
      playlistsEnabled: !!PLAYLISTS_ENABLED,
      itemNoun: ITEM_NOUN,
      setInlineRating: setInlineRating,
      openBpmAdjustMenu: _openBpmAdjustMenu,
      deleteTrackDownload: deleteTrackDownload,
      cancelDownload: cancelDownload,
      downloadTrack: downloadTrack,
      toggleFavorite: toggleFavorite,
      openEditModal: openEditModal,
      openPlaylistModalFor: function(rp) { loadUserPlaylists().then(function() { openPlaylistModal(rp); }); },
      removeFromQueue: removeFromQueue,
      addToQueue: addToQueue,
      showToast: showToast,
      moveFileToFolder: moveFileToFolder,
      deleteTrackFromList: _deleteTrackFromList,
      openTrackCtxMenu: _openTrackCtxMenu,
      revealInExplorer: _revealInExplorer,
      playTrack: playTrack,
      selectTrackRow: _selectTrackRow,
      saveInlineTableEdit: _saveInlineTableEdit
    });
  }

  /* Inline title/artist edit save ported to webui/src/inlineEdit.ts. */
  function _saveInlineTableEdit(editable) {
    window._saveInlineTableEdit(editable, { editPath: METADATA_EDIT_PATH, toast: showToast });
  }


"""
