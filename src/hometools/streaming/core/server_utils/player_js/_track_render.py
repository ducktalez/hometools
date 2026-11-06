"""JS fragment: track render (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_track_render_js() -> str:
    """Return the track render section of the player JS."""
    return """  function renderTracks(tracks, force) {
    /* Ensure dupe data is available when the dupe tool is active */
    if (_toolState.duplicates) _ensureDupeMap();
    /* Separate real items from debug-dimmed items for filteredItems / shuffle */
    var realTracks = DEBUG_FILTER
      ? tracks.filter(function(t) { return !t._debugReason; })
      : tracks;
    filteredItems = realTracks;
    /* Rebuild shuffle queue whenever the filtered set changes */
    if (shuffleMode) rebuildShuffleQueue(currentIndex >= 0 ? currentIndex : 0);
    var hiddenShownCount = realTracks.filter(function(t) { return !!t._hiddenShown; }).length;
    var visibleCount = realTracks.length - hiddenShownCount;
    var noun = visibleCount !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN;
    trackCount.textContent = visibleCount + ' ' + noun;

    /* ── Render guard ───────────────────────────────────────────────────────
       Key covers every input that can change the rendered output.
       _rgKey is reset by _invalidateDupeMap() whenever allItems changes,
       and by the force=true flag (e.g. after playlist reorder).             */
    var guardKey = (_currentPlaylistId || '') + '\\x00' + currentPath + '\\x00'
      + (searchInput ? searchInput.value.trim() : '') + '\\x00'
      + (sortField ? sortField.value : '') + '\\x00'
      + String(tracks.length) + '\\x00' + filterRating + '\\x00'
      + (filterFav ? '1' : '0') + '\\x00' + (filterGenre || '') + '\\x00'
      + _effectiveThreshold + '\\x00' + (showHidden ? '1' : '0') + '\\x00' + (_justRatedPath || '');
    if (!force && guardKey === _rgKey && trackList.children.length > 0) {
      /* Nothing visually changed — just refresh active highlight */
      markActive();
      return;
    }
    _rgKey = guardKey;

    /* ── Windowed rendering setup ─────────────────────────────────────────*/
    _stopRenderObserver();
    trackList.innerHTML = '';
    /* Mark series lists so .track-num gets a fixed width that fits "S01E12" */
    var _hasSeriesItems = tracks.some(function(t) { return (t.season || 0) > 0; });
    trackList.classList.toggle('track-list--series', _hasSeriesItems);

    if (!tracks.length) {
      trackList.innerHTML = '<li class="empty-hint">No matching items.</li>';
      return;
    }

    /* Episode-gap placeholders, sentinel, first batch, lazy-load observer:
       webui/src/trackRenderWindow.ts (window state private there). */
    _startWindowedRender(realTracks);
  }


  /* ── offline download management ── */
  var OFFLINE_SOFT_LIMIT = 500 * 1024 * 1024;
  var activeDownloads = {};

  function cancelDownload(streamUrl, btn) {
    window._cancelDownload(streamUrl, btn, activeDownloads, { icDl: IC_DL, toast: showToast });
  }

  /* revokeOfflineUrl/getOfflineUrl: ported to webui/src/offlineUrl.ts,
     bridged onto window.getOfflineUrl by main.ts (see that file's header
     comment for why currentOfflineUrl moved as private state). */

  /* IndexedDB layer (initDownloadDB/getDownloadByStreamUrl/getAllDownloads/
     deleteDownloadById/deleteDownloadByStreamUrl + downloadDB handle):
     ported to webui/src/offlineDb.ts, bridged onto window by main.ts under
     the same names — bare call sites below unchanged. DB name/version is a
     contract with the Service Worker (_pwa.py), see offlineDb.ts header. */

  /* formatBytes() lives in _core.py — kept as the single canonical
     definition (was accidentally duplicated here during the module split). */

  /* formatDate/sortDownloads/getAppDownloadUsage: ported to
     webui/src/offlineDownloads.ts, bridged onto window by main.ts. */

  /* findItemByStreamUrl: webui/src/catalogQuery.ts (explicit lists). */
  function findItemByStreamUrl(streamUrl) {
    return window._findItemByStreamUrl(streamUrl, filteredItems, allItems);
  }


  /* estimateOfflineStorage: ported to webui/src/offlineDownloads.ts,
     bridged onto window by main.ts. softLimit now explicit 2nd arg. */

  /* texts/flags: webui/src/offlineDownloads.ts::storageSummaryView. DOM here. */
  function renderStorageSummary(info) {
    if (!info) return;
    var v = window._storageSummaryView(info);
    if (offlineStorageSummary) {
      offlineStorageSummary.classList.toggle('warn', v.warn);
      offlineStorageSummary.textContent = v.summary;
    }
    if (offlineStorageDetail) offlineStorageDetail.textContent = v.detail;
    if (downloadedPill) {
      downloadedPill.textContent = v.pill;
      downloadedPill.classList.toggle('has-downloads', v.hasDownloads);
    }
    updateOfflineFolderCount();
  }  function renderOfflineDownloadList(downloads) {
    if (!offlineDownloadList) return;
    offlineDownloadList.innerHTML = window._offlineDownloadListHtml(downloads, escHtml, formatBytes, FILE_PLACEHOLDER);
    if (!downloads.length) return;
    offlineDownloadList.querySelectorAll('.offline-download-item').forEach(function(el) {
      el.addEventListener('click', function(e) {
        if (e.target && e.target.classList && e.target.classList.contains('offline-download-delete')) return;
        playStoredDownload(el.dataset.streamUrl);
      });
    });
    offlineDownloadList.querySelectorAll('.offline-download-delete').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        deleteTrackDownload(btn.dataset.streamUrl);
      });
    });
  }

  function refreshOfflineLibrary() {
    return getAllDownloads().then(function(downloads) {
      /* If currently viewing the offline playlist, refresh it */
      if (currentPath === '__offline__') {
        var ready = downloads.filter(function(d) { return d.status === 'ready'; });
        var sortBy = offlineSort ? offlineSort.value : 'newest';
        var sorted = sortDownloads(ready, sortBy);
        var items = sorted.map(function(d) {
          return {
            title: d.title || 'Offline-Download',
            artist: d.artist || '',
            relative_path: d.relativePath || d.title || d.streamUrl,
            stream_url: d.streamUrl,
            thumbnail_url: d.thumbnailUrl || '',
            media_type: d.mediaType || ITEM_NOUN,
            rating: 0
          };
        });
        playlistItems = items;
        applyFilter();
        estimateOfflineStorage(ready, OFFLINE_SOFT_LIMIT).then(function(info) {
          if (info && info.appUsage > 0) {
            trackCount.textContent = ready.length + ' download' + (ready.length !== 1 ? 's' : '') +
              ' · ' + formatBytes(info.appUsage);
          }
        });
      }
      updateOfflineFolderCount();
      return downloads;
    });
  }

  function openOfflineLibrary() {
    getAllDownloads().then(function(downloads) {
      var ready = downloads.filter(function(d) { return d.status === 'ready'; });
      var sortBy = offlineSort ? offlineSort.value : 'newest';
      var sorted = sortDownloads(ready, sortBy);
      var items = sorted.map(function(d) {
        return {
          title: d.title || 'Offline-Download',
          artist: d.artist || '',
          relative_path: d.relativePath || d.title || d.streamUrl,
          stream_url: d.streamUrl,
          thumbnail_url: d.thumbnailUrl || '',
          media_type: d.mediaType || ITEM_NOUN,
          rating: 0
        };
      });
      currentPath = '__offline__';
      /* Enter via _enterTrackListView() directly (same shared entry point as
         showPlaylist()/showUserPlaylistView()/playDuplicates() — see
         docs/IMPLEMENTATION_PLAN.md "UI-Template-Vereinheitlichung") instead
         of calling showPlaylist() and patching headerTitle.textContent
         afterward. The previous patch-after approach raced _enterTrackListView's
         own title logic (currentPath='__offline__' would otherwise render as
         the literal folder name via leafName()) and duplicated the router
         update showPlaylist() already performs. Also skips showPlaylist()'s
         folder-order fetch/sort, which is meaningless for a virtual list. */
      destroyPlaylistDragDrop();
      inPlaylist = true;
      _currentPlaylistId = '__offline__';
      playlistItems = items;
      _enterTrackListView({ title: 'Downloaded', backDisabled: false, resetIndex: true });
      estimateOfflineStorage(ready, OFFLINE_SOFT_LIMIT).then(function(info) {
        if (info && info.appUsage > 0) {
          trackCount.textContent = ready.length + ' download' + (ready.length !== 1 ? 's' : '') +
            ' · ' + formatBytes(info.appUsage);
        }
      });
    });
  }

  function closeOfflineLibrary() { window._closeOfflineLibrary({ showFolderView: showFolderView }); }

  function updateOfflineFolderCount() { window._updateOfflineFolderCount(downloadedPill); }

  /* ── Recently played section ── */
  function loadRecentlyPlayed() {
    var section = document.getElementById('recent-section');
    if (!section) return;
    fetch(RECENT_API_PATH + '?limit=10')
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(d) {
        if (!d || !d.items || d.items.length === 0) {
          section.hidden = true;
          return;
        }
        var scroll = section.querySelector('.recent-scroll');
        scroll.innerHTML = d.items.map(function(it) {
          var pct = Math.min(100, Math.max(0, it.progress_pct || 0));
          var thumb = it.thumbnail_url || FILE_PLACEHOLDER;
          var isPlaceholder = !it.thumbnail_url;
          var imgStyle = isPlaceholder ? ' style="object-fit:contain;padding:14px;opacity:.4"' : '';
          return '<div class="recent-card" data-path="' + escHtml(it.relative_path || '') + '"'
            + ' data-pos="' + (it.position_seconds || 0) + '" title="' + escHtml(it.title || '') + '">'
            + '<div class="recent-thumb-wrap">'
            + '<img class="recent-thumb" src="' + escHtml(thumb) + '" loading="lazy"' + imgStyle + '>'
            + (pct > 2 ? '<div class="recent-progress-bar" style="width:' + pct + '%"></div>' : '')
            + '</div>'
            + '<div class="recent-title">' + escHtml(it.title || it.relative_path || '') + '</div>'
            + '<div class="recent-sub">' + escHtml(it.artist || '') + '</div>'
            + '</div>';
        }).join('');
        section.hidden = false;
        /* attach click handlers */
        scroll.querySelectorAll('.recent-card').forEach(function(card) {
          card.addEventListener('click', function() {
            var path = card.dataset.path;
            var seekPos = parseFloat(card.dataset.pos) || 0;
            /* item + folder siblings: webui/src/recentlyPlayed.ts::recentPlayContext */
            var ctx = window._recentPlayContext(path, allItems);
            if (!ctx) return;
            var found = null;
            for (var i = 0; i < allItems.length; i++) {
              if (allItems[i].relative_path === path) { found = allItems[i]; break; }
            }
            currentPath = ctx.folder;
            inPlaylist = true;
            showPlaylist(ctx.folderItems, false);
            /* Find the correct index in filteredItems *after* showPlaylist has
               sorted them via applyFilter.  Computing idx from the unsorted
               folderItems before showPlaylist would give a stale position and
               cause the wrong next-episode to play when the current one ends. */
            var filteredIdx = 0;
            for (var k = 0; k < filteredItems.length; k++) {
              if (filteredItems[k].relative_path === path) { filteredIdx = k; break; }
            }
            playItem(found, filteredIdx);
            /* seek to saved position after canplay */
            if (seekPos > 2) {
              player.addEventListener('canplay', function onCp() {
                player.removeEventListener('canplay', onCp);
                player.currentTime = seekPos;
              }, { once: true });
            }
          });
        });
      })
      .catch(function() { if (section) section.hidden = true; });
  }



  function requestPersistentStorage() {
    if (!(navigator.storage && navigator.storage.persist)) return Promise.resolve(false);
    if (offlinePersistBtn) offlinePersistBtn.textContent = 'Prüfe persistenten Speicher…';
    return navigator.storage.persist().then(function(persistent) {
      if (offlinePersistBtn) {
        offlinePersistBtn.textContent = persistent ? 'Persistenter Speicher aktiv' : 'Persistenz nicht verfügbar';
      }
      return refreshOfflineLibrary().then(function() { return persistent; });
    }).catch(function() {
      if (offlinePersistBtn) offlinePersistBtn.textContent = 'Persistenz fehlgeschlagen';
      return false;
    });
  }

  function pruneOldDownloads(requiredBytes, protectedStreamUrl) {
    /* selection + deletion: webui/src/offlineDb.ts::evictForBudget
       (pickEvictionVictims in offlineDownloads.ts). UI refresh stays here. */
    return window._evictForBudget(requiredBytes, OFFLINE_SOFT_LIMIT, protectedStreamUrl).then(function(ok) {
      updateAllDownloadButtons();
      refreshOfflineLibrary();
      return ok;
    });
  }

  function ensureStorageBudget(requiredBytes, protectedStreamUrl) {
    return getAllDownloads().then(function(downloads) {
      var total = getAppDownloadUsage(downloads);
      if (total + requiredBytes <= OFFLINE_SOFT_LIMIT) return true;
      return pruneOldDownloads(requiredBytes, protectedStreamUrl);
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

  function playStoredDownload(streamUrl) {
    getDownloadByStreamUrl(streamUrl).then(function(download) {
      if (!download) return;
      /* If currently in offline playlist, find track in filtered items */
      if (currentPath === '__offline__') {
        var offIdx = filteredItems.findIndex(function(it) { return it.stream_url === streamUrl; });
        if (offIdx >= 0) { playTrack(offIdx); return; }
      }
      var match = findItemByStreamUrl(streamUrl);
      if (match) {
        playTrack(match.index >= 0 ? match.index : filteredItems.findIndex(function(it) { return it.stream_url === streamUrl; }));
        if (match.index < 0) {
          playItem(match.item, -1);
        }
        return;
      }
      playItem({
        title: download.title || 'Offline-Download',
        artist: download.artist || '',
        relative_path: download.relativePath || download.title || streamUrl,
        stream_url: download.streamUrl,
        thumbnail_url: download.thumbnailUrl || '',
        media_type: download.mediaType || ITEM_NOUN,
        rating: 0
      }, -1);
    });
  }

  /* Listen for Service Worker download notifications */
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.addEventListener('message', function(e) {
      if (e.data && (e.data.type === 'DOWNLOAD_CACHED' || e.data.type === 'DOWNLOAD_DELETED')) {
        updateAllDownloadButtons();
        refreshOfflineLibrary();
      }
    });
  }

  if (downloadedPill) downloadedPill.addEventListener('click', openOfflineLibrary);
  if (offlineClose) offlineClose.addEventListener('click', closeOfflineLibrary);
  if (offlineLibrary) {
    offlineLibrary.addEventListener('click', function(e) {
      if (e.target === offlineLibrary) closeOfflineLibrary();
    });
  }
  if (offlineSort) offlineSort.addEventListener('change', refreshOfflineLibrary);
  if (offlinePersistBtn) {
    if (!(navigator.storage && navigator.storage.persist)) {
      offlinePersistBtn.hidden = true;
    } else {
      offlinePersistBtn.addEventListener('click', requestPersistentStorage);
    }
  }
  if (offlinePruneBtn) {
    offlinePruneBtn.addEventListener('click', function() {
      pruneOldDownloads(0, currentStreamUrl);
    });
  }
  window.addEventListener('online', refreshOfflineLibrary);
  window.addEventListener('offline', refreshOfflineLibrary);

  /* ── Tools panel ── */
  var toolsPill = document.getElementById('tools-pill');
  var toolsBackdrop = document.getElementById('tools-panel-backdrop');
  var toolsClose = document.getElementById('tools-panel-close');
  var _toolInlineRatings = document.getElementById('tool-inline-ratings');
  var _toolDownloads = document.getElementById('tool-downloads');
  var _toolPlaylists = document.getElementById('tool-playlists');
  var _toolDuplicates = document.getElementById('tool-duplicates');
  var _dupeShowLink = document.getElementById('dupe-show-link');
  var _toolFileMover = document.getElementById('tool-file-mover');
  var _toolBpmCalc = document.getElementById('tool-bpm-calc');
  var _toolAutoRefreshGroup = null; /* removed — auto-refresh feature disabled */
  var _toolsGlobalRefreshBtn = document.getElementById('tools-global-refresh-btn');

  /* Load saved tool states from localStorage */
  var _toolState = JSON.parse(localStorage.getItem('ht-tools') || '{}');

  function _anyToolActive() {
    return !!_toolState.active && (!!_toolState.inlineRatings || !!_toolState.duplicates || !!_toolState.fileMover);
  }

  function _updateActivateBtn() {
    var isOn = !!_toolState.active;
    if (_toolsActivateAll) {
      _toolsActivateAll.textContent = isOn ? 'Tool-Modus deaktivieren' : 'Tool-Modus aktivieren';
      _toolsActivateAll.classList.toggle('tools-activate-all--active', isOn);
      _toolsActivateAll.title = isOn ? 'Tool-Modus ausschalten' : 'Tool-Modus mit den konfigurierten Einstellungen aktivieren';
    }
    /* Sync the header split-pill toggle button */
    var _pillToggle = document.getElementById('tools-pill-toggle');
    if (_pillToggle) {
      _pillToggle.classList.toggle('active', isOn);
      _pillToggle.title = isOn ? 'Tool-Modus deaktivieren' : 'Tool-Modus aktivieren';
    }
    /* Sync the wrap border highlight */
    var _pillWrap = document.getElementById('tools-pill-wrap');
    if (_pillWrap) _pillWrap.classList.toggle('has-active', _anyToolActive());
  }

  function _applyHeaderUiState() {
    /* Remove legacy body classes that may have been persisted in older localStorage saves */
    document.body.classList.remove('tool-refresh-off', 'tool-refresh-in-pill');
  }

  function _applyToolState() {
    _updateActivateBtn();
    _applyHeaderUiState();
    if (!_toolState.active) {
      /* Tool mode is off: hide all tool UI without changing saved preferences */
      document.body.classList.remove('tool-inline-ratings');
      document.body.classList.remove('tool-hide-downloads');
      document.body.classList.remove('tool-hide-playlists');
      document.body.classList.remove('tool-show-duplicates');
      document.body.classList.remove('tool-show-file-mover');
      document.body.classList.remove('tool-bpm-calc');
      if (toolsPill) toolsPill.classList.remove('has-active');
      /* Re-render to remove tool widgets from track list */
      if (folderGrid && !folderGrid.classList.contains('view-hidden')) {
        showFolderView();
      } else if (inPlaylist) {
        applyViewMode();
        applyFilter();
      }
      return;
    }
    if (_toolState.inlineRatings) {
      document.body.classList.add('tool-inline-ratings');
      if (_toolInlineRatings) _toolInlineRatings.checked = true;
    } else {
      document.body.classList.remove('tool-inline-ratings');
      if (_toolInlineRatings) _toolInlineRatings.checked = false;
    }
    if (_toolState.downloads === false) {
      document.body.classList.add('tool-hide-downloads');
      if (_toolDownloads) _toolDownloads.checked = false;
    } else {
      document.body.classList.remove('tool-hide-downloads');
      if (_toolDownloads) _toolDownloads.checked = true;
    }
    if (_toolState.playlists === false) {
      document.body.classList.add('tool-hide-playlists');
      if (_toolPlaylists) _toolPlaylists.checked = false;
    } else {
      document.body.classList.remove('tool-hide-playlists');
      if (_toolPlaylists) _toolPlaylists.checked = true;
    }
    if (_toolState.duplicates) {
      document.body.classList.add('tool-show-duplicates');
      if (_toolDuplicates) _toolDuplicates.checked = true;
    } else {
      document.body.classList.remove('tool-show-duplicates');
      if (_toolDuplicates) _toolDuplicates.checked = false;
    }
    if (_toolState.fileMover) {
      document.body.classList.add('tool-show-file-mover');
      if (_toolFileMover) _toolFileMover.checked = true;
    } else {
      document.body.classList.remove('tool-show-file-mover');
      if (_toolFileMover) _toolFileMover.checked = false;
    }
    if (_toolState.bpmCalc) {
      document.body.classList.add('tool-bpm-calc');
      if (_toolBpmCalc) _toolBpmCalc.checked = true;
    } else {
      document.body.classList.remove('tool-bpm-calc');
      if (_toolBpmCalc) _toolBpmCalc.checked = false;
    }
    /* Update pill highlight (now on the wrap container) */
    var anyActive = _anyToolActive();
    var _pillWrapEl = document.getElementById('tools-pill-wrap');
    if (_pillWrapEl) _pillWrapEl.classList.toggle('has-active', anyActive);
    if (toolsPill) toolsPill.classList.toggle('has-active', anyActive); /* legacy compat */
    /* Re-render current view so folder names / view mode reflect new tool state */
    if (folderGrid && !folderGrid.classList.contains('view-hidden')) {
      showFolderView();
    } else if (inPlaylist) {
      applyViewMode();
      applyFilter();
    }
    /* Refresh player bar actions so move/trash show/hide with tool mode changes */
    updatePlayerBarActions();
  }

  function _saveToolState() {
    localStorage.setItem('ht-tools', JSON.stringify(_toolState));
    _applyToolState();
  }

  function openToolsPanel() {
    if (toolsBackdrop) toolsBackdrop.removeAttribute('hidden');
    /* Always show dupe count when panel opens — show even if toggle is off */
    if (_dupeShowLink && allItems.length > 0) {
      _ensureDupeMap();
      var dc = _getDupeCount();
      _dupeShowLink.textContent = dc > 0
        ? dc + ' Duplikat-Gruppe' + (dc !== 1 ? 'n' : '') + ' \u2014 Liste anzeigen'
        : 'Keine Duplikate gefunden';
      _dupeShowLink.style.display = 'inline-block';
    }
    if (typeof _router !== 'undefined') _router.update();
  }
  function closeToolsPanel() {
    if (toolsBackdrop) toolsBackdrop.setAttribute('hidden', '');
    if (typeof _router !== 'undefined') _router.update();
  }

  if (toolsPill) toolsPill.addEventListener('click', openToolsPanel);
  /* Split-pill toggle: directly activates/deactivates tool mode without opening the panel */
  var _toolsPillToggle = document.getElementById('tools-pill-toggle');
  if (_toolsPillToggle) {
    _toolsPillToggle.addEventListener('click', function(e) {
      e.stopPropagation(); /* prevent bubbling to tools-pill-wrap / toolsPill */
      _toolState.active = !_toolState.active;
      if (_toolState.active && _toolState.duplicates) _ensureDupeMap();
      if (!_toolState.active) _invalidateDupeMap();
      _saveToolState();
      if (inPlaylist) applyFilter();
    });
  }
  if (toolsClose) toolsClose.addEventListener('click', closeToolsPanel);
  if (toolsBackdrop) {
    toolsBackdrop.addEventListener('click', function(e) {
      if (e.target === toolsBackdrop) closeToolsPanel();
    });
  }
  var _dupePanelBackdrop = document.getElementById('dupe-panel-backdrop');
  var _dupePanelClose = document.getElementById('dupe-panel-close');
  var _dupePanelPlayAll = document.getElementById('dupe-panel-play-all');
  if (_dupePanelClose) _dupePanelClose.addEventListener('click', closeDupePanel);
  if (_dupePanelPlayAll) _dupePanelPlayAll.addEventListener('click', playDuplicates);
  if (_dupePanelBackdrop) {
    _dupePanelBackdrop.addEventListener('click', function(e) {
      if (e.target === _dupePanelBackdrop) closeDupePanel();
    });
  }
  if (_toolInlineRatings) {
    _toolInlineRatings.addEventListener('change', function() {
      _toolState.inlineRatings = _toolInlineRatings.checked;
      _saveToolState();
      /* Re-render current track list to add/remove inline stars */
      if (inPlaylist) applyFilter();
    });
  }
  if (_toolDownloads) {
    _toolDownloads.addEventListener('change', function() {
      _toolState.downloads = _toolDownloads.checked;
      _saveToolState();
    });
  }
  if (_toolPlaylists) {
    _toolPlaylists.addEventListener('change', function() {
      _toolState.playlists = _toolPlaylists.checked;
      _saveToolState();
    });
  }
  if (_toolDuplicates) {
    _toolDuplicates.addEventListener('change', function() {
      _toolState.duplicates = _toolDuplicates.checked;
      if (_toolDuplicates.checked) _ensureDupeMap();
      else _invalidateDupeMap();
      _saveToolState();
      /* Re-render to show/hide badges */
      if (inPlaylist) applyFilter();
    });
  }
  if (_dupeShowLink) {
    _dupeShowLink.addEventListener('click', function(e) {
      e.preventDefault();
      closeToolsPanel();
      playDuplicates();
    });
  }
  if (_toolFileMover) {
    _toolFileMover.addEventListener('change', function() {
      _toolState.fileMover = _toolFileMover.checked;
      _saveToolState();
      /* Re-render to show/hide move widgets */
      if (inPlaylist) applyFilter();
    });
  }
  if (_toolBpmCalc) {
    _toolBpmCalc.addEventListener('change', function() {
      _toolState.bpmCalc = _toolBpmCalc.checked;
      _saveToolState();
      /* Re-render so the "?" pills switch between static and clickable-glow */
      if (inPlaylist) applyFilter();
    });
  }
  /* Global Tools: "Ordnerdaten aller Ordner erneuern" button */
  if (_toolsGlobalRefreshBtn) {
    _toolsGlobalRefreshBtn.addEventListener('click', function() {
      closeToolsPanel();
      refreshCatalog();
    });
  }
  var _toolsActivateAll = document.getElementById('tools-activate-all');
  if (_toolsActivateAll) {
    _toolsActivateAll.addEventListener('click', function() {
      _toolState.active = !_toolState.active;
      /* When activating: if duplicates tool is configured, ensure dupe map is ready */
      if (_toolState.active && _toolState.duplicates) _ensureDupeMap();
      /* When deactivating: invalidate dupe map to release memory */
      if (!_toolState.active) _invalidateDupeMap();
      _saveToolState();
      if (inPlaylist) applyFilter();
    });
  }
  _applyToolState();

  /* ── Inline track rating stars ── */
  /* markup: webui/src/inlineWidgets.ts::inlineRatingHtml */
  function renderInlineRating(t, idx) {
    return window._inlineRatingHtml(t.rating, idx, !!RATING_WRITE_ENABLED, IC_STAR_FILLED, IC_STAR_EMPTY);
  }

  function setInlineRating(idx, stars) {
    if (!RATING_WRITE_ENABLED) return;
    var t = filteredItems[idx];
    if (!t) return;
    var prevRating = t.rating || 0;
    /* Remember the currently-playing path (not necessarily this row) so it
       can be relocated after a re-sort/re-filter below. */
    var playingPath = (currentIndex >= 0 && filteredItems[currentIndex])
      ? filteredItems[currentIndex].relative_path : null;
    fetch(RATING_API_PATH, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: t.relative_path, rating: stars })
    })
    .then(function(r) { return r.ok ? r.json() : null; })
    .then(function(d) {
      if (!d || !d.ok) return;
      t.rating = d.rating;
      _patchAllItemsRating(t.relative_path, d.rating);
      /* Never let this rating change hide the row it was made on — gray it
         instead so the change stays visible/undoable. Cleared (and the real
         filter re-applied) once the undo-toast window elapses. */
      _justRatedPath = t.relative_path;
      clearTimeout(_justRatedTimer);
      _justRatedTimer = setTimeout(function() {
        _justRatedPath = null;
        if (inPlaylist) applyFilter(true);
      }, 5000);
      if (inPlaylist) {
        applyFilter(true);
        /* Sort/filter may have reordered items — relocate currentIndex to
           the track that is actually still playing. */
        if (playingPath) {
          var relocated = window._indexOfPath(filteredItems, playingPath);
          if (relocated >= 0) currentIndex = relocated;
        }
        markActive();
        if (playingPath === t.relative_path) renderPlayerRating(d.rating);
      } else {
        _updateTrackRatingBar(idx, d.rating);
        if (currentIndex === idx) renderPlayerRating(d.rating);
      }
      /* rebuild weighted shuffle queue so new rating is reflected */
      if (shuffleMode === 'weighted') rebuildShuffleQueue(currentIndex);
      var toastLabel2 = window._ratingToastLabel(stars);
      if (d.entry_id) {
        showRatingToastWithUndo(stars, prevRating, d.entry_id, t);
      } else {
        showToast(toastLabel2);
      }
    })
    .catch(function() {});
  }


  /* ── BPM adjust popup (Tools-panel "BPM berechnen") ───────────────────────
     Click handler for the BPM pill rendered by window.renderBpmPill()
     (webui/src/metricPill.ts) — both the "unknown" (.meta-pill--calc) and
     "known, editable" (.meta-pill--editable) variants, whenever the tool
     is active. Opens a small popup with four actions: langsamer (÷2),
     neu berechnen (reload), schneller (×2), and a manual numeric entry.
     Stays Python-generated (not ported to TS) because it needs
     filteredItems/allItems/showToast — identifiers private to this
     script's own closure, not reachable from the separate static bundle.
     See docs/IMPLEMENTATION_PLAN.md Design Discussions
     ("Player-JS-Modulkopplung") for why that boundary exists. */
  function _patchAllItemsBpm(relativePath, bpm) {
    /* copy-on-write: webui/src/catalogQuery.ts::replaceItemFields */
    window._replaceItemFields([allItems], relativePath, { bpm: bpm });
  }

  var _bpmMenuCleanup = null;

  function _closeBpmAdjustMenu() {
    if (_bpmMenuCleanup) { _bpmMenuCleanup(); _bpmMenuCleanup = null; }
    var old = document.getElementById('bpm-adjust-menu');
    if (old) old.remove();
  }

  /* langsamer/schneller: halves/doubles the value in one click AND biases
     every future "neu berechnen" via streaming/core/bpm_hints.py, so a
     known octave mis-detection (e.g. 85 erkannt, eigentlich 170) isn't
     reproduced by the next automatic analysis. */
  function _openBpmAdjustMenu(idx, btnEl) {
    _closeBpmAdjustMenu();
    var t = filteredItems[idx];
    if (!t || !t.relative_path) return;
    var curBpm = t.bpm || 0;

    var menu = document.createElement('div');
    menu.id = 'bpm-adjust-menu';
    menu.className = 'ht-ctx-menu bpm-adjust-menu';
    /* markup: webui/src/playerBarHtml.ts::bpmAdjustMenuHtml */
    menu.innerHTML = window._bpmAdjustMenuHtml(curBpm, { chevronsDown: IC_CHEVRONS_DOWN, refresh: IC_REFRESH, chevronsUp: IC_CHEVRONS_UP });
    document.body.appendChild(menu);

    var rect = btnEl.getBoundingClientRect();
    menu.style.right = Math.max(4, window.innerWidth - rect.right) + 'px';
    var spaceBelow = window.innerHeight - rect.bottom;
    if (spaceBelow >= menu.offsetHeight + 8) {
      menu.style.top = (rect.bottom + 4) + 'px';
    } else {
      menu.style.top = Math.max(4, rect.top - menu.offsetHeight - 4) + 'px';
    }

    function _busy(isBusy) {
      menu.querySelectorAll('button, input').forEach(function(el) { el.disabled = isBusy; });
    }

    function _applyResult(d, fallbackErr) {
      _busy(false);
      if (!d || !d.ok) {
        showToast((d && d.error) || fallbackErr);
        return;
      }
      t.bpm = d.bpm;
      _patchAllItemsBpm(t.relative_path, d.bpm);
      if (btnEl.parentNode && typeof window.renderBpmPill === 'function') {
        var wrap = document.createElement('span');
        wrap.innerHTML = window.renderBpmPill(d.bpm, BPM_MIN, BPM_MAX,
          { index: idx, relativePath: t.relative_path, calcEnabled: !!(_toolState.active && _toolState.bpmCalc) });
        var newPill = wrap.firstChild;
        if (newPill) btnEl.parentNode.replaceChild(newPill, btnEl);
      }
      showToast('BPM: ' + Math.round(d.bpm));
      _closeBpmAdjustMenu();
    }

    var reloadBtn = menu.querySelector('[data-action="reload"]');
    if (reloadBtn) {
      reloadBtn.addEventListener('click', function() {
        _busy(true);
        fetch(BPM_CALC_API_PATH, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: t.relative_path })
        })
          .then(function(r) { return r.ok ? r.json() : null; })
          .then(function(d) { _applyResult(d, 'BPM-Berechnung fehlgeschlagen'); })
          .catch(function() { _busy(false); showToast('BPM-Berechnung fehlgeschlagen (Netzwerkfehler)'); });
      });
    }

    ['slower', 'faster'].forEach(function(action) {
      var actionBtn = menu.querySelector('[data-action="' + action + '"]');
      if (!actionBtn) return;
      actionBtn.addEventListener('click', function() {
        if (actionBtn.disabled) return;
        _busy(true);
        fetch(BPM_ADJUST_API_PATH, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: t.relative_path, factor: action === 'slower' ? 0.5 : 2 })
        })
          .then(function(r) { return r.ok ? r.json() : null; })
          .then(function(d) { _applyResult(d, 'Anpassung fehlgeschlagen'); })
          .catch(function() { _busy(false); showToast('Anpassung fehlgeschlagen (Netzwerkfehler)'); });
      });
    });

    var manualInput = menu.querySelector('.bpm-adjust-input');
    var applyBtn = menu.querySelector('.bpm-adjust-apply');
    function _submitManual() {
      var val = parseFloat(manualInput.value);
      if (!val || val <= 0) { showToast('Bitte einen g\u00fcltigen BPM-Wert eingeben'); return; }
      _busy(true);
      fetch(BPM_SET_API_PATH, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: t.relative_path, bpm: val })
      })
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(d) { _applyResult(d, 'Speichern fehlgeschlagen'); })
        .catch(function() { _busy(false); showToast('Speichern fehlgeschlagen (Netzwerkfehler)'); });
    }
    if (applyBtn) applyBtn.addEventListener('click', _submitManual);
    if (manualInput) {
      manualInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { e.preventDefault(); _submitManual(); }
      });
      manualInput.addEventListener('click', function(e) { e.stopPropagation(); });
    }

    /* Close on outside click or Escape — same pattern as _openCtxMenu()
       in _library_tools.py (not reused directly: this popup needs a live
       <input>, not just a list of click-only rows). */
    function _onOutside(e) { if (!menu.contains(e.target) && e.target !== btnEl && !btnEl.contains(e.target)) _closeBpmAdjustMenu(); }
    function _onEsc(e) { if (e.key === 'Escape') _closeBpmAdjustMenu(); }
    setTimeout(function() {
      document.addEventListener('click', _onOutside);
      document.addEventListener('keydown', _onEsc);
    }, 0);
    _bpmMenuCleanup = function() {
      document.removeEventListener('click', _onOutside);
      document.removeEventListener('keydown', _onEsc);
    };
  }

  /* ── Duplicate detection (client-side) ── */
  var IC_DUPLICATE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>';
  /* Dupe index state: webui/src/dupeState.ts. */
  /* _isDupeGroupSafe() (incl. its 2% threshold) ported to
     webui/src/dupeUtils.ts (opportunistic port, see
     docs/IMPLEMENTATION_PLAN.md), bridged onto window by main.ts. */

  /* ── Dupe-panel metadata formatters ── */
  /* _fmtDuration/_fmtFileSize/_fmtDate/_normalizeStem/_dupeKey ported to
     webui/src/dupeUtils.ts (Vite/TS migration Phase 5 opportunistic-port
     slice — see docs/IMPLEMENTATION_PLAN.md) — bridged onto window by
     main.ts, bare calls elsewhere in this fragment still resolve via the
     normal JS scope chain. */

"""
