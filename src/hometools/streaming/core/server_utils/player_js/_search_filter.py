"""JS fragment: search filter (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_search_filter_js() -> str:
    """Return the search filter section of the player JS."""
    return """  function globalSearch(needle) {
    needle = needle.toLowerCase();
    /* Folder-match + item-match computation: ported to webui/src/search.ts
       (buildFolderMatches/searchItems), bridged onto window by main.ts.
       allItems/hiddenActive/_effectiveThreshold passed explicitly. */
    var hiddenActive = (_effectiveThreshold > 0 && !showHidden);
    var folderMatches = window._buildFolderMatches(allItems, needle, hiddenActive, _effectiveThreshold);
    var results = window._searchItems(allItems, needle, hiddenActive, _effectiveThreshold);
    _globalSearchActive = true;
    /* Use search results as current playlist so next/prev works —
       must be set BEFORE _enterTrackListView (contract: caller sets
       playlistItems/inPlaylist first). */
    playlistItems = results;
    filteredItems = results;
    inPlaylist = true;
    var totalCount = folderMatches.length + results.length;
    var trackCountLabel = results.length + ' ' + (results.length !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN);
    if (folderMatches.length) {
      trackCountLabel = folderMatches.length + ' Ordner · ' + trackCountLabel;
    }
    /* Header/toolbar via the shared track-list entry point — search now
       updates breadcrumb/view-toggle/router like every other list view
       (was the only view skipping them). skipFilter: results are rendered
       by renderSearchResults below, applyFilter() would overwrite them.
       hideFilterBar: sort/filter chips don't apply to search results.
       The header search box stays visible on its own — _applyHeaderState()
       shows it in every view, so typing is never interrupted. */
    _enterTrackListView({
      title: totalCount + ' Ergebnis' + (totalCount !== 1 ? 'se' : ''),
      backDisabled: false,
      playAllDisabled: true,
      hideFilterBar: true,
      skipFilter: true,
      trackCount: trackCountLabel
    });
    if (shuffleMode) rebuildShuffleQueue(currentIndex >= 0 ? currentIndex : 0);
    /* Render search results */
    renderSearchResults(results, folderMatches);
  }

  function renderSearchResults(results, folderMatches) {
    trackList.innerHTML = '';
    folderMatches = folderMatches || [];
    if (results.length === 0 && folderMatches.length === 0) {
      trackList.innerHTML = '<li class="track-item" style="opacity:0.5;pointer-events:none"><div class="track-info"><div class="track-title">Keine Ergebnisse</div></div></li>';
      return;
    }
    /* Folder/series matches first */
    folderMatches.forEach(function(fm) {
      var li = document.createElement('li');
      li.className = 'track-item search-folder-item';
      /* row markup: webui/src/trackRows.ts::searchFolderRowHtml */
      li.innerHTML = window._searchFolderRowHtml(fm, escHtml, FILE_PLACEHOLDER, IC_FOLDER_PLAY);
      li.addEventListener('click', function() { navigateToSearchFolder(fm.path); });
      trackList.appendChild(li);
    });
    results.forEach(function(t, i) {
      var li = document.createElement('li');
      li.className = 'track-item';
      li.setAttribute('data-index', i);
      /* row markup: webui/src/trackRows.ts::searchResultRowHtml */
      li.innerHTML = window._searchResultRowHtml(t, i, escHtml, FILE_PLACEHOLDER);
      li.addEventListener('click', function() { navigateToSearchResult(t, i); });
      trackList.appendChild(li);
    });
  }

  function navigateToSearchFolder(folderPath) {
    /* Leave search and open the folder. */
    _globalSearchActive = false;
    var inp = document.getElementById('global-search-input');
    if (inp) inp.value = '';
    currentPath = folderPath || '';
    showFolderView();
  }

  function navigateToSearchResult(item, idx) {
    /* Play directly within search results — search stays open */
    playItem(item, idx);
    markActive();
  }

  function exitGlobalSearch() {
    _globalSearchActive = false;
    var inp = document.getElementById('global-search-input');
    if (inp) inp.value = '';
    showFolderView();
  }

  /* play all items under current path */
  function playAllCurrent() {
    var items = itemsUnder(currentPath);
    if (!items.length) items = contentsAt(currentPath).files;
    if (items.length) showPlaylist(items, true);
  }

  /* ── filter / sort within playlist ── */
  /* ── Quick-filter chips ──
     Bewertung + Favorit + Genre live in ONE combined "Filtern" popover
     button (filter-combined) instead of three separate chips — see
     docs/IMPLEMENTATION_PLAN.md "UI-Template-Vereinheitlichung" Phase 2.
     "Ausgeblendet" (filterHiddenBtn) stays its own toggle-slot chip. */
  /* _collectPlaylistGenres: ported to webui/src/catalogQuery.ts as
     collectGenres(items) — playlistItems now explicit param. */

  /* labels/counts: webui/src/filterPopover.ts (chip views); DOM writes here. */
  function updateFilterChips() {
    if (filterCombinedBtn) {
      var cv = window._filterCombinedChipView({ rating: filterRating, fav: filterFav, genre: filterGenre }, IC_FILTER);
      filterCombinedBtn.innerHTML = cv.html;
      filterCombinedBtn.classList.toggle('active', cv.active);
      filterCombinedBtn.title = cv.title;
    }
    /* Keep an already-open popover's contents (star state, genre <select>)
       in sync — e.g. after navigating into a folder whose genre list differs. */
    if (document.getElementById('ht-filter-popover')) _renderFilterPopoverBody();
    if (filterHiddenBtn) {
      var hv = window._filterHiddenChipView(playlistItems, _effectiveThreshold, showHidden, IC_EYE);
      if (hv) {
        filterHiddenBtn.style.display = '';
        filterHiddenBtn.innerHTML = hv.html;
        filterHiddenBtn.classList.toggle('active', hv.active);
        filterHiddenBtn.title = hv.title;
      } else {
        filterHiddenBtn.style.display = 'none';
      }
    }
  }  /* ── Combined "Filtern" popover (Bewertung + Favorit + Genre) ──────────
     Mirrors the generic _openCtxMenu() pattern (_library_tools.py) —
     fixed-position card anchored to the trigger button, closes on outside
     click / Escape — but hosts interactive controls (star buttons,
     checkbox, <select>) instead of a static action list, so it gets its
     own small open/close/wire trio here rather than reusing _openCtxMenu's
     items schema (label+onClick only). */
  /* markup: webui/src/filterPopover.ts::filterPopoverBodyHtml (state explicit). */
  function _filterPopoverBodyHtml() {
    return window._filterPopoverBodyHtml(
      _collectGenres(playlistItems),
      { rating: filterRating, fav: filterFav, genre: filterGenre },
      { starFilled: IC_STAR_FILLED, starEmpty: IC_STAR_EMPTY },
      escHtml
    );
  }  function _wireFilterPopoverBody(pop) {
    pop.querySelectorAll('.filter-popover-star').forEach(function(starBtn) {
      starBtn.addEventListener('click', function() {
        var val = Number(starBtn.dataset.star);
        filterRating = (filterRating === val) ? 0 : val;
        localStorage.setItem('ht-filter-rating', String(filterRating));
        updateFilterChips();
        applyFilter();
        if (typeof _router !== 'undefined') _router.update();
      });
    });
    var favCb = pop.querySelector('#filter-popover-fav');
    if (favCb) {
      favCb.addEventListener('change', function() {
        filterFav = favCb.checked;
        localStorage.setItem('ht-filter-fav', filterFav ? '1' : '0');
        updateFilterChips();
        applyFilter();
        if (typeof _router !== 'undefined') _router.update();
      });
    }
    var genreSel = pop.querySelector('#filter-popover-genre-select');
    if (genreSel) {
      genreSel.addEventListener('change', function() {
        filterGenre = genreSel.value;
        localStorage.setItem('ht-filter-genre', filterGenre);
        updateFilterChips();
        applyFilter();
        if (typeof _router !== 'undefined') _router.update();
      });
    }
    var resetBtn = pop.querySelector('#filter-popover-reset');
    if (resetBtn) {
      resetBtn.addEventListener('click', function() {
        filterRating = 0; filterFav = false; filterGenre = '';
        localStorage.setItem('ht-filter-rating', '0');
        localStorage.setItem('ht-filter-fav', '0');
        localStorage.setItem('ht-filter-genre', '');
        updateFilterChips();
        applyFilter();
        if (typeof _router !== 'undefined') _router.update();
      });
    }
  }

  function _renderFilterPopoverBody() {
    var pop = document.getElementById('ht-filter-popover');
    if (!pop) return;
    pop.innerHTML = _filterPopoverBodyHtml();
    _wireFilterPopoverBody(pop);
  }

  function _closeFilterPopover() {
    if (_filterPopoverCleanup) { _filterPopoverCleanup(); _filterPopoverCleanup = null; }
    var old = document.getElementById('ht-filter-popover');
    if (old) old.remove();
  }

  function _toggleFilterPopover(btn) {
    if (document.getElementById('ht-filter-popover')) { _closeFilterPopover(); return; }
    var pop = document.createElement('div');
    pop.id = 'ht-filter-popover';
    pop.className = 'filter-popover';
    pop.innerHTML = _filterPopoverBodyHtml();
    document.body.appendChild(pop);
    var rect = btn.getBoundingClientRect();
    pop.style.right = Math.max(4, window.innerWidth - rect.right) + 'px';
    var spaceBelow = window.innerHeight - rect.bottom;
    if (spaceBelow >= pop.offsetHeight + 8) {
      pop.style.top = (rect.bottom + 6) + 'px';
    } else {
      pop.style.top = Math.max(4, rect.top - pop.offsetHeight - 6) + 'px';
    }
    _wireFilterPopoverBody(pop);
    function _onOutside(e) { if (!pop.contains(e.target) && e.target !== btn && !btn.contains(e.target)) _closeFilterPopover(); }
    function _onEsc(e) { if (e.key === 'Escape') _closeFilterPopover(); }
    setTimeout(function() {
      document.addEventListener('click', _onOutside);
      document.addEventListener('keydown', _onEsc);
    }, 0);
    _filterPopoverCleanup = function() {
      document.removeEventListener('click', _onOutside);
      document.removeEventListener('keydown', _onEsc);
    };
  }

  function applyFilter(force) {
    var needle = searchInput.value.trim().toLowerCase();
    var sortBy = sortField.value;
    /* Safety net: always strip locally-deleted paths regardless of how
       playlistItems was last set (stale closure, folder-order callback, etc.) */
    var items = Object.keys(_locallyDeletedPaths).length
      ? playlistItems.filter(function(it) { return !_locallyDeletedPaths[it.relative_path]; })
      : playlistItems;

    /* Filter chain (rating/favorite/genre/search, normal + DEBUG_FILTER
       mode): ported to webui/src/filterChain.ts::applyFilterChain(items,
       opts), bridged onto window._applyFilterChain by main.ts. Globals
       bundled into one explicit options object instead of closure reads. */
    items = window._applyFilterChain(items, {
      needle: needle,
      debugFilter: DEBUG_FILTER,
      effectiveThreshold: _effectiveThreshold,
      showHidden: showHidden,
      justRatedPath: _justRatedPath,
      filterRating: filterRating,
      filterFav: filterFav,
      filterGenre: filterGenre,
      savedFavorites: _savedFavorites
    });

    /* sort: ported to webui/src/catalogQuery.ts::sortTracks(items, sortBy,
       hasCustomPlaylist), bridged onto window._sortTracks by main.ts. Explicit
       params instead of reading sortField.value/_currentPlaylistId globals. */
    items = window._sortTracks(items, sortBy, !!_currentPlaylistId);
    renderTracks(items, force);
  }
  /* needsConversion()/filenameFromPath() ported to webui/src/pathUtils.ts
     (Vite/TS migration Phase 5 opportunistic-port slice — see
     docs/IMPLEMENTATION_PLAN.md) — bridged onto window by main.ts, bare
     calls below still resolve via the normal JS scope chain. */

  /* ── Windowed rendering helpers ──────────────────────────────────────────
     _appendTrackBatch  — append the next _RENDER_BATCH_SIZE items to the DOM.
     _ensureRenderedTo  — synchronously render up to (and including) displayIdx.
     _stopRenderObserver — disconnect the IntersectionObserver.               */

  function _stopRenderObserver() {
    if (_renderObserver) { _renderObserver.disconnect(); _renderObserver = null; }
    if (_renderSentinelEl && _renderSentinelEl.parentNode === trackList) {
      trackList.removeChild(_renderSentinelEl);
    }
    _renderSentinelEl = null;
  }

  function _appendTrackBatch() {
    var end = window._batchEnd(_renderBatchOffset, _RENDER_BATCH_SIZE, _renderAllItems.length);
    if (end <= _renderBatchOffset) { _stopRenderObserver(); return; }
    var showOrig = _anyToolActive();
    /* BPM "calculate" affordance (yellow-glow clickable "?") is gated by the
       Tools-panel "BPM berechnen" toggle — see _track_render.py::_applyToolState. */
    var bpmCalcEnabled = !!(_toolState.active && _toolState.bpmCalc);
    /* row HTML: webui/src/trackRows.ts::trackRowsHtml (missing / debug / normal rows) */
    var html = window._trackRowsHtml(_renderAllItems, _renderRealIdxMap, _renderBatchOffset, end, {
      escHtml: escHtml, fmtTime: fmtTime, showOrig: showOrig, currentIndex: currentIndex,
      bpmCalcEnabled: bpmCalcEnabled, trackViewMode: trackViewMode, isVideoMode: isVideoMode,
      metadataEditEnabled: !!METADATA_EDIT_ENABLED, playlistsEnabled: !!PLAYLISTS_ENABLED,
      itemNoun: ITEM_NOUN, bpmMin: BPM_MIN, bpmMax: BPM_MAX,
      dupePaths: _dupePaths, dupeSafety: _dupeSafety, filePlaceholder: FILE_PLACEHOLDER,
      ic: { folderPlay: IC_FOLDER_PLAY, trash: IC_TRASH, dl: IC_DL, pin: IC_PIN, edit: IC_EDIT,
            playlist: IC_PLAYLIST, queue: IC_QUEUE, dots: IC_DOTS },
      renderBpmPill: window.renderBpmPill,
      renderInlineRating: renderInlineRating, renderMoveWidget: renderMoveWidget
    });
    var isFirstBatch = (_renderBatchOffset === 0);
    _renderBatchOffset = end;
    if (_renderSentinelEl && _renderSentinelEl.parentNode === trackList) {
      _renderSentinelEl.insertAdjacentHTML('beforebegin', html);
    } else {
      trackList.insertAdjacentHTML('beforeend', html);
    }
    /* Update status decorations for newly added buttons */
    updateFavoriteButtons();
    updateAllDownloadButtons();
    updateQueueButtons();
    if (_renderBatchOffset >= _renderAllItems.length) {
      _stopRenderObserver();
      /* Playlist drag-drop is wired on the container — set up once all items are present */
      if (PLAYLISTS_ENABLED && inPlaylist && _currentPlaylistId && viewMode === 'list') {
        initPlaylistDragDrop();
      }
    } else if (isFirstBatch) {
      /* First batch rendered: start DnD if appropriate (container-level, works for later items too) */
      if (PLAYLISTS_ENABLED && inPlaylist && _currentPlaylistId && viewMode === 'list') {
        initPlaylistDragDrop();
      }
    }
  }

  function _ensureRenderedTo(idx) {
    /* target: webui/src/renderWindow.ts::renderTargetFor */
    var displayIdx = window._renderTargetFor(_renderRealIdxMap, idx, _renderBatchOffset, _renderAllItems.length);
    if (displayIdx < 0) return;
    /* Render batches until displayIdx is covered */
    while (_renderBatchOffset <= displayIdx && _renderBatchOffset < _renderAllItems.length) {
      var prevOffset = _renderBatchOffset;
      _appendTrackBatch();
      if (_renderBatchOffset === prevOffset) break; /* safety: no progress */
    }
  }

  function markActive() {
    if (currentIndex >= 0) _ensureRenderedTo(currentIndex);
    document.querySelectorAll('.track-item:not(.missing-episode):not(.debug-filtered)').forEach(function(el) {
      var idx = Number(el.dataset.index);
      el.classList.toggle('active', idx === currentIndex);
      if (idx === currentIndex) el.scrollIntoView({ block: 'nearest' });
    });
  }

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

  /* ── Jump to current track in list ───────────────────────────────────────
     Called when the user clicks the album cover in the player bar.
     Navigates to the folder of the playing track (if needed), then scrolls
     to and highlights the active item.                                       */
  function jumpToCurrentTrack() {
    var t = (currentIndex >= 0)
      ? (filteredItems[currentIndex] || playlistItems[currentIndex])
      : null;
    if (!t) return;
    var rp = t.relative_path || '';
    /* target: webui/src/renderWindow.ts::jumpTarget */
    var jt = window._jumpTarget(t, inPlaylist, currentPath);
    var folder = jt.folder;
    if (jt.sameView) {
      /* Already in the right playlist view — just scroll to the track */
      _ensureRenderedTo(currentIndex);
      markActive();
      return;
    }
    /* Navigate to the folder that contains the playing track */
    var savedRp = rp;
    currentPath = folder;
    var items = itemsUnder(currentPath);
    if (!items.length) return;
    showPlaylist(items, false);
    /* Restore currentIndex to the playing track in the new filteredItems */
    var newIdx = filteredItems.findIndex(function(fi) {
      return fi.relative_path === savedRp;
    });
    if (newIdx >= 0) {
      currentIndex = newIdx;
      _ensureRenderedTo(currentIndex);
      markActive();
    }
  }

  /* ── Player bar right-side actions ────────────────────────────────────────
     Updated on every track change.  Always shows the 3-dots kebab.
     In tool-show-file-mover mode also shows move-folder-select + trash.      */
  function updatePlayerBarActions() {
    if (!playerBarActions) return;
    var t = (currentIndex >= 0)
      ? (filteredItems[currentIndex] || playlistItems[currentIndex])
      : null;
    if (!t) { playerBarActions.innerHTML = ''; return; }

    /* markup: webui/src/playerBarHtml.ts::playerBarActionsHtml */
    var inMoverMode = document.body.classList.contains('tool-show-file-mover');
    playerBarActions.innerHTML = window._playerBarActionsHtml(
      t, _getAllFolders(), _currentFolderOf(t), inMoverMode, escHtml, IC_DOTS, IC_TRASH);
    if (inMoverMode) {
      /* Wire move-select */
      var mvSel = playerBarActions.querySelector('#player-bar-move-select');
      if (mvSel) {
        mvSel.addEventListener('change', function() {
          var target = mvSel.value;
          if (!target || currentIndex < 0) return;
          var ci = currentIndex;
          moveFileToFolder(ci, target);
          mvSel.value = '';
        });
      }
      /* Wire trash */
      var trashBtn = playerBarActions.querySelector('#player-bar-trash');
      if (trashBtn) {
        trashBtn.addEventListener('click', function() {
          if (currentIndex < 0) return;
          var item = filteredItems[currentIndex] || playlistItems[currentIndex];
          if (!item) return;
          if (!confirm('Datei in den Papierkorb verschieben?\\n' + (item.title || item.relative_path))) return;
          _deleteItem(currentIndex);
        });
      }
    }
    /* Wire kebab */
    var kbBtn = playerBarActions.querySelector('#player-bar-kebab');
    if (kbBtn) {
      kbBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        _openTrackCtxMenu(kbBtn, kbBtn.dataset.relativePath, kbBtn.dataset.title);
      });
    }
  }

  /* Re-render player bar actions when tool mode changes */
  function _onToolModeChange() { updatePlayerBarActions(); }

  /* withMissingEpisodes: ported to webui/src/episodeGaps.ts, bridged
     onto window by main.ts. */

  /* ── Event delegation for track list ─────────────────────────────────────
     Wired once per renderTracks call, covers all items added by future
     _appendTrackBatch calls (windowed rendering).                           */
  var _trackListClickHandler  = null;
  var _trackListChangeHandler = null;
  var _trackListFocusoutHandler = null;
  var _trackListKeydownHandler  = null;

  function _wireTrackListDelegation() {
    if (_trackListClickHandler)  trackList.removeEventListener('click',  _trackListClickHandler);
    if (_trackListChangeHandler) trackList.removeEventListener('change', _trackListChangeHandler);
    _trackListClickHandler = function(e) {
      /* Rating stars */
      var ratingStar = e.target.closest('.track-inline-rating-star');
      if (ratingStar) {
        e.stopPropagation(); e.preventDefault();
        var _idx = Number(ratingStar.dataset.index);
        var _t = filteredItems[_idx];
        var _cur = Math.round((_t && _t.rating) || 0);
        var _clicked = Number(ratingStar.dataset.star);
        setInlineRating(_idx, _clicked === _cur ? 0 : _clicked);
        return;
      }
      /* BPM pill click — opens the adjust popup (langsamer/neu berechnen/
         schneller/manuell). Matches both the "unknown" (.meta-pill--calc)
         and "known, editable" (.meta-pill--editable) variants — both carry
         the same data-action attribute (see webui/src/metricPill.ts). Only
         rendered as a <button> at all when the Tools-panel "BPM berechnen"
         toggle is active. */
      var bpmPillBtn = e.target.closest('.meta-pill[data-action="calc-bpm"]');
      if (bpmPillBtn) {
        e.stopPropagation(); e.preventDefault();
        _openBpmAdjustMenu(Number(bpmPillBtn.dataset.index), bpmPillBtn);
        return;
      }
      /* Download button */
      var dlBtn = e.target.closest('.track-dl-btn');
      if (dlBtn) {
        e.stopPropagation(); e.preventDefault();
        var dlUrl = dlBtn.dataset.streamUrl;
        var dlMeta = { artist: dlBtn.dataset.artist || '', relativePath: dlBtn.dataset.relativePath || '',
          thumbnailUrl: dlBtn.dataset.thumbnailUrl || '', mediaType: dlBtn.dataset.mediaType || ITEM_NOUN };
        if (dlBtn.classList.contains('cached')) { deleteTrackDownload(dlUrl, dlBtn); }
        else if (dlBtn.classList.contains('downloading')) { cancelDownload(dlUrl, dlBtn); }
        else { downloadTrack(dlUrl, dlBtn.dataset.title, dlBtn, dlMeta); }
        return;
      }
      /* Favorite / pin button */
      var pinBtn = e.target.closest('.track-pin-btn');
      if (pinBtn) {
        e.stopPropagation(); e.preventDefault();
        var pinItem = filteredItems.find(function(it) { return it.relative_path === pinBtn.dataset.relativePath; });
        if (pinItem) toggleFavorite(pinItem, pinBtn);
        return;
      }
      /* Edit button */
      if (METADATA_EDIT_ENABLED) {
        var editBtn = e.target.closest('.track-edit-btn');
        if (editBtn) { e.stopPropagation(); e.preventDefault(); openEditModal(Number(editBtn.dataset.index)); return; }
      }
      /* Add-to-playlist button */
      if (PLAYLISTS_ENABLED) {
        var plBtn = e.target.closest('.track-playlist-btn');
        if (plBtn) {
          e.stopPropagation(); e.preventDefault();
          loadUserPlaylists().then(function() { openPlaylistModal(plBtn.dataset.relativePath); });
          return;
        }
      }
      /* Queue button */
      var queueBtn = e.target.closest('.track-queue-btn');
      if (queueBtn) {
        e.stopPropagation(); e.preventDefault();
        var qrp = queueBtn.dataset.relativePath;
        var qi = window._queueIndexOf(_userQueue, qrp);
        if (qi >= 0) {
          removeFromQueue(qi);
          showToast('Aus Warteschlange entfernt');
        } else {
          var qidx = Number(queueBtn.dataset.index);
          if (qidx >= 0 && qidx < filteredItems.length) addToQueue(filteredItems[qidx]);
        }
        return;
      }
      /* Move-quick-pick button */
      var movQuick = e.target.closest('.move-quick-btn');
      if (movQuick) {
        e.stopPropagation(); e.preventDefault();
        moveFileToFolder(Number(movQuick.dataset.index), movQuick.dataset.target);
        return;
      }
      /* Inline delete / trash buttons */
      var trashBtn = e.target.closest('.track-delete-btn, .move-delete-btn');
      if (trashBtn) {
        e.stopPropagation(); e.preventDefault();
        _deleteTrackFromList(Number(trashBtn.dataset.index));
        return;
      }
      /* Kebab / three-dot context menu */
      var kebabBtn = e.target.closest('.track-kebab-btn');
      if (kebabBtn) {
        e.stopPropagation(); e.preventDefault();
        _openTrackCtxMenu(kebabBtn, kebabBtn.dataset.relativePath, kebabBtn.dataset.title);
        return;
      }
      /* Reveal in Explorer button (inline, tool mode) */
      var revealBtn = e.target.closest('.track-reveal-btn');
      if (revealBtn) {
        e.stopPropagation(); e.preventDefault();
        _revealInExplorer(revealBtn.dataset.relativePath, revealBtn.dataset.title);
        return;
      }
      /* Hover-play button (thumbnail overlay) — always plays regardless of device */
      var playBtn = e.target.closest('.track-play-btn');
      if (playBtn) {
        e.stopPropagation(); e.preventDefault();
        playTrack(Number(playBtn.dataset.index));
        return;
      }
      /* Inline-editable title/artist cell (table/detail view, tools active):
         clicking to place the caret must not trigger row select/play. */
      if (e.target.closest('[contenteditable="true"]')) return;
      /* Track row click — on hover-capable (desktop/mouse) devices this only
         selects/highlights the row; actual playback is started via the
         dedicated hover-play button on the thumbnail. On touch devices
         (no hover) a row tap still plays directly, since there is no
         reliable hover affordance there. */
      var trackItem = e.target.closest('.track-item:not(.missing-episode):not(.debug-filtered)');
      if (trackItem && !wasDrag(e) && !window.getSelection().toString()) {
        var _idx2 = Number(trackItem.dataset.index);
        if (window.matchMedia && window.matchMedia('(hover: hover)').matches) {
          _selectTrackRow(_idx2);
        } else {
          playTrack(_idx2);
        }
      }
    };
    _trackListChangeHandler = function(e) {
      var movSel = e.target.closest('.move-folder-select');
      if (movSel) {
        e.stopPropagation();
        var mvTarget = movSel.value;
        if (!mvTarget) return;
        moveFileToFolder(Number(movSel.dataset.index), mvTarget);
        movSel.value = '';
      }
    };
    if (_trackListFocusoutHandler) trackList.removeEventListener('focusout', _trackListFocusoutHandler);
    if (_trackListKeydownHandler)  trackList.removeEventListener('keydown',  _trackListKeydownHandler);
    _trackListFocusoutHandler = function(e) {
      var editable = e.target.closest('.track-title-text[contenteditable="true"], .track-artist[contenteditable="true"]');
      if (!editable) return;
      _saveInlineTableEdit(editable);
    };
    _trackListKeydownHandler = function(e) {
      var editable = e.target.closest('.track-title-text[contenteditable="true"], .track-artist[contenteditable="true"]');
      if (!editable) return;
      if (e.key === 'Enter') { e.preventDefault(); editable.blur(); }
      else if (e.key === 'Escape') { e.preventDefault(); editable.dataset.cancelled = '1'; editable.blur(); }
    };
    trackList.addEventListener('click',  _trackListClickHandler);
    trackList.addEventListener('change', _trackListChangeHandler);
    trackList.addEventListener('focusout', _trackListFocusoutHandler);
    trackList.addEventListener('keydown',  _trackListKeydownHandler);
    /* Desktop convenience: double-click a row to play it directly */
    trackList.addEventListener('dblclick', function(e) {
      if (e.target.closest('[contenteditable="true"]')) return;
      var dblItem = e.target.closest('.track-item:not(.missing-episode):not(.debug-filtered)');
      if (dblItem) playTrack(Number(dblItem.dataset.index));
    });
  }

  /* Save an inline-edited title/artist cell (table/detail view).  Reuses the
     existing metadata-edit endpoint; reverts on error or Escape-cancel. */
  function _saveInlineTableEdit(editable) {
    var field = editable.dataset.field;
    var rp = editable.dataset.relativePath;
    if (!field || !rp) return;
    var cancelled = editable.dataset.cancelled === '1';
    delete editable.dataset.cancelled;
    var t = filteredItems.find(function(it) { return it.relative_path === rp; }) ||
      (allItems || []).find(function(it) { return it.relative_path === rp; });
    var oldVal = t ? (t[field] || '') : '';
    var newVal = editable.textContent.replace(/\\s+/g, ' ').trim();
    if (cancelled || newVal === oldVal) { editable.textContent = oldVal; return; }
    if (!newVal) { editable.textContent = oldVal; showToast('Feld darf nicht leer sein'); return; }
    var payload = { path: rp };
    payload[field] = newVal;
    fetch(METADATA_EDIT_PATH, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function(r) { return r.ok ? r.json() : null; })
      .then(function(d) {
        if (!d || !d.ok) { editable.textContent = oldVal; showToast('Fehler beim Speichern'); return; }
        if (t) t[field] = newVal;
        editable.textContent = newVal;
        showToast('Gespeichert');
      })
      .catch(function() { editable.textContent = oldVal; showToast('Fehler beim Speichern'); });
  }

"""
