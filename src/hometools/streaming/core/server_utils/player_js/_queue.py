"""JS fragment: queue (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_queue_js(sprite_preview_js, waveform_setup_js) -> str:
    """Return the queue section of the player JS."""
    return (
        """  function dequeueNext() {
    if (_userQueue.length === 0) return false;
    playFromQueue(0);
    return true;
  }

  function playNextItem() {
    if (repeatMode === 'one') {
      /* Repeat single: restart the current track */
      player.currentTime = 0;
      player.play().catch(function() {});
      return;
    }
    if (dequeueNext()) return;
    if (!filteredItems.length) return;
    var ni = nextIndex();
    if (ni < 0) {
      /* End of list, no repeat — stop playback */
      wasPlaying = false;
      btnPlay.innerHTML = IC_PLAY;
      return;
    }
    playTrack(ni);
  }

  function _syncQueueBottom() {
    window._syncQueueBottom(_queuePanel, _queueUserHeight, _QUEUE_MIN_H);
  }

  /* Queue drag-to-resize ported to webui/src/queuePanelUi.ts. */
  window._initQueueResize({
    handle: _queueDragHandle,
    panel: _queuePanel,
    minH: _QUEUE_MIN_H,
    heightKey: _QUEUE_HEIGHT_KEY,
    isOpen: function() { return _queueOpen; },
    setUserHeight: function(h) { _queueUserHeight = h; }
  });
  /* Recalc on window resize */
  window.addEventListener('resize', function() { if (_queueOpen) _syncQueueBottom(); });

  function openQueuePanel() {
    _ensureQueueDom();
    if (!_queuePanel) return;
    _queueOpen = true;
    /* Close lyrics panel if open */
    if (window._lyrics.isOpen()) closeLyricsPanel();
    _syncQueueBottom();
    renderQueuePanel();
    _queuePanel.classList.add('visible');
    if (_queuePeekHandle) _queuePeekHandle.classList.add('queue-active');
  }

  function closeQueuePanel() {
    _ensureQueueDom();
    _queueOpen = false;
    destroyQueueDragDrop();
    if (_queuePanel) _queuePanel.classList.remove('visible');
    if (_queuePeekHandle) _queuePeekHandle.classList.remove('queue-active');
  }

  function toggleQueuePanel() {
    _ensureQueueDom();
    if (_queueOpen) closeQueuePanel();
    else openQueuePanel();
  }

  /* Peek handle (click/drag-up opens queue) ported to webui/src/queuePanelUi.ts. */
  window._initQueuePeekHandle({
    handle: _queuePeekHandle,
    isOpen: function() { return _queueOpen; },
    open: openQueuePanel,
    toggle: toggleQueuePanel
  });

  if (_queueClose) {
    _queueClose.addEventListener('click', closeQueuePanel);
  }
  if (_queueClearBtn) {
    _queueClearBtn.addEventListener('click', function() {
      clearQueue();
      showToast('Warteschlange geleert');
    });
  }

  /* Queue drag-drop reorder ported to webui/src/queueDragDrop.ts (state +
     cleanup handle private there). Wrappers keep bare-name call sites. */
  function destroyQueueDragDrop() { window._destroyQueueDragDrop(); }
  function initQueueDragDrop() {
    window._initQueueDragDrop({
      move: function(f, t) { window._queueMove(f, t); },
      render: renderQueuePanel
    });
  }

  function scheduleBackgroundRefresh(delay) {
    if (_indexRefreshTimer) return;
    _indexRefreshTimer = setTimeout(function() {
      _indexRefreshTimer = null;
      fetch(API_PATH, { cache: 'no-store' })
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(data) {
          if (!data || data.error) return;
          if (data.refreshing) {
            var detail = data.detail || 'Building index…';
            showIndexingToast(detail, data.cache);
            scheduleBackgroundRefresh();
            /* Update items if more are now available */
            var newItems = data && Array.isArray(data.items) ? data.items : [];
            if (newItems.length > allItems.length) {
              allItems = newItems;
              _invalidateDupeMap();
              _invalidateFolderCache();
              showFolderView();
            }
            return;
          }
          /* Full index ready */
          hideIndexingToast();
          allItems = _applyLocalMutations(data && Array.isArray(data.items) ? data.items : []);
          _invalidateDupeMap();
          _invalidateFolderCache();
          _saveCatalogCache(allItems);
          console.info('Background refresh complete:', allItems.length, 'items');
          showFolderView();
        })
        .catch(function() { scheduleBackgroundRefresh(); });
    }, delay !== undefined ? delay : 800);
  }

  /* Cancel the pending poll timer and re-fetch immediately.
     Only acts when an index build is actually in progress. */
  function forceBackgroundRefresh() {
    if (!_indexRefreshTimer) return; /* nothing scheduled → no build in progress */
    clearTimeout(_indexRefreshTimer);
    _indexRefreshTimer = null;
    scheduleBackgroundRefresh(0);
  }

  /* Trigger a silent catalog fetch immediately — called on every folder/playlist
     navigation so the user always gets fresh data with the highest priority.
     Shows cached data first (instant), then updates the view if something changed.
     A flag prevents concurrent fetches; already-in-flight requests are reused. */
  var _silentRefreshInFlight = false;
  function _triggerSilentRefresh() {
    if (_silentRefreshInFlight) return;
    _silentRefreshInFlight = true;
    fetch(API_PATH, { cache: 'no-store' })
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(data) {
        _silentRefreshInFlight = false;
        if (!data || data.error || data.loading) return;
        var fresh = _applyLocalMutations(Array.isArray(data.items) ? data.items : []);
        /* Detect any change: count OR missing/added path (webui/src/catalogRefresh.ts) */
        var changed = window._catalogChanged(allItems, fresh);
        allItems = fresh;
        _invalidateDupeMap();
        _invalidateFolderCache();
        _saveCatalogCache(allItems);
        if (changed) {
          if (inPlaylist) {
            var newItems = itemsUnder(currentPath);
            if (newItems.length) { playlistItems = newItems; applyFilter(); }
            else { showFolderView(); }
          } else {
            showFolderView();
          }
        }
        if (data.refreshing) scheduleBackgroundRefresh();
      })
      .catch(function() { _silentRefreshInFlight = false; });
  }

  /* ── Manual catalog refresh (user-triggered) ── */
  /* The refresh button is rendered dynamically in the tools-row (root view only). */
  function _getRefreshBtn() { return document.getElementById('refresh-catalog-card'); }

  function _refreshPoll() {
    fetch(API_PATH, { cache: 'no-store' })
    .then(function(r) { return r.ok ? r.json() : null; })
    .then(function(data) {
      var _rb = _getRefreshBtn();
      if (!data) {
        if (_rb) _rb.classList.remove('spinning');
        showToast('Refresh fehlgeschlagen');
        return;
      }
      if (data.refreshing) {
        setTimeout(_refreshPoll, 800);
        return;
      }
      var oldCount = allItems.length;
      allItems = Array.isArray(data.items) ? data.items : [];
      _invalidateDupeMap();
      _invalidateFolderCache();
      _saveCatalogCache(allItems);
      if (_rb) _rb.classList.remove('spinning');

      /* Show refresh timestamp */
      var infoEl = document.getElementById('refresh-info');
      if (infoEl) {
        var dt = new Date();
        infoEl.textContent = window._catalogRefreshInfo(allItems.length, dt);
        infoEl.title = 'Letzter Katalog-Refresh: ' + dt.toLocaleString();
      }

      /* Re-render current view */
      if (inPlaylist) {
        var newItems = itemsUnder(currentPath);
        if (newItems.length) playlistItems = newItems;
        applyFilter();
      } else {
        showFolderView();
      }
      showToast(window._refreshToastMessage(allItems.length, oldCount));
    })
    .catch(function() { setTimeout(_refreshPoll, 2000); });
  }

  function refreshCatalog() {
    var _rb = _getRefreshBtn(); if (_rb) _rb.classList.add('spinning');
    _clearCatalogCache();  /* force fresh data — user explicitly requested a reload */
    /* Clear in place (never reassign `= {}`) — window._locallyDeletedPaths
       (bridged in _core.py for webui/src/catalogCache.ts) must keep pointing
       at this same object, or _applyLocalMutations() silently stops seeing
       future deletions. */
    Object.keys(_locallyDeletedPaths).forEach(function(k) { delete _locallyDeletedPaths[k]; });
    _ratingRefreshPath = null;

    var base = API_PATH.substring(0, API_PATH.lastIndexOf('/'));
    /* Invalidate server-side index cache and trigger full rebuild */
    fetch(base + '/refresh', { method: 'POST' })
    .then(function(r) { return r.ok ? r.json() : null; })
    .then(function() { _refreshPoll(); })
    .catch(function() {
      var _rb2 = _getRefreshBtn(); if (_rb2) _rb2.classList.remove('spinning');
      showToast('Refresh fehlgeschlagen');
    });
  }
  /* Delegated click-handler for the dynamically rendered refresh-catalog-card in the tools-row */
  if (folderGrid) {
    folderGrid.addEventListener('click', function(e) {
      if (e.target.closest('.refresh-catalog-card')) refreshCatalog();
    });
  }

  /* ── Lazy per-folder rating refresh ── */
  var _ratingRefreshPath = null;
  function refreshFolderRatings(folderItems) {
    if (!RATING_WRITE_ENABLED || !folderItems.length) return;
    var refreshPath = currentPath;
    /* Skip if we just refreshed this exact folder */
    if (_ratingRefreshPath === refreshPath) return;
    _ratingRefreshPath = refreshPath;
    var paths = folderItems.map(function(t) { return t.relative_path; });
    var base = API_PATH.substring(0, API_PATH.lastIndexOf('/'));
    fetch(base + '/refresh-ratings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paths: paths })
    })
    .then(function(r) { return r.ok ? r.json() : null; })
    .then(function(data) {
      if (!data || !data.ratings) return;
      var ratings = data.ratings;
      /* Patch allItems + playlistItems in place (webui/src/catalogRefresh.ts) */
      window._patchRatingsInPlace(allItems, ratings);
      window._patchRatingsInPlace(playlistItems, ratings);
      /* Show refresh timestamp */
      var infoEl = document.getElementById('refresh-info');
      if (infoEl && data.last_refresh) {
        var dt = new Date(data.last_refresh);
        infoEl.textContent = window._ratingRefreshInfo(Object.keys(ratings).length, data.changed, dt);
        infoEl.title = 'Letzte Rating-Aktualisierung: ' + dt.toLocaleString();
      }
      /* Re-render if still viewing the same folder */
      if (inPlaylist && currentPath === refreshPath) {
        applyFilter();
      }
    })
    .catch(function() { /* silent background refresh */ });
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

  function scheduleInitialCatalogRetry(reason) {
    if (initialCatalogRetryTimer) return;
    console.info('Initial catalog retry scheduled:', reason || 'loading');
    initialCatalogRetryTimer = window.setTimeout(function() {
      initialCatalogRetryTimer = null;
      loadInitialCatalog();
    }, 800);
  }

  function loadInitialCatalog() {
    if (allItems.length) {
      console.info('Initial catalog already present in page payload:', allItems.length, 'items');
      return Promise.resolve(allItems);
    }
    /* ── Stale-while-revalidate: show cached catalog immediately ───────────────
       If localStorage holds a fresh snapshot (< _CATALOG_MAX_AGE_MS), display
       it instantly with no loading spinner.  A silent background fetch follows
       to pick up any changes; the UI only re-renders when the item count differs.
       _loadCatalogCache() returns null when the entry is absent or expired.    */
    var _cachedItems = _loadCatalogCache();
    if (_cachedItems && _cachedItems.length) {
      console.info('Initial catalog: serving', _cachedItems.length, 'items from localStorage cache (background refresh follows)');
      allItems = _cachedItems;
      _invalidateDupeMap();
      _invalidateFolderCache();
      showFolderView();
      /* Verify against server silently — no loading state, no spinner */
      fetch(API_PATH, { cache: 'no-store' })
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(data) {
          if (!data || data.error || data.loading) return;
          var fresh = _applyLocalMutations(Array.isArray(data.items) ? data.items : []);
          /* Detect deletions/replacements, not just count (catalogRefresh.ts). */
          var changed = window._catalogChanged(allItems, fresh);
          allItems = fresh;
          _invalidateDupeMap();
          _invalidateFolderCache();
          _saveCatalogCache(allItems);
          if (changed) { showFolderView(); }
          if (data.refreshing) scheduleBackgroundRefresh();
        })
        .catch(function() { /* server offline — cached data stays visible */ });
      return Promise.resolve(allItems);
    }
    initialCatalogRetryCount += 1;
    if (initialCatalogRetryCount <= 1) {
      showLoadingState('Loading library…');
    }
    var t0 = Date.now();
    console.info('Initial catalog fetch started:', API_PATH);
    return fetch(API_PATH, { cache: 'no-store' })
      .then(function(r) {
        console.info('Initial catalog response received after', Date.now() - t0, 'ms with status', r.status);
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function(data) {
        if (data && data.error) {
          throw new Error(data.error);
        }
        /* Handle loading state (truly empty, no quick scan available) */
        if (data && data.loading && (!data.items || data.items.length === 0)) {
          var detail = data.detail || 'Library cache is warming in the background.';
          console.info('Initial catalog still building (empty):', detail);
          showIndexingToast(detail, data.cache);
          scheduleInitialCatalogRetry(detail);
          return [];
        }
        if (initialCatalogRetryTimer) {
          window.clearTimeout(initialCatalogRetryTimer);
          initialCatalogRetryTimer = null;
        }
        initialCatalogRetryCount = 0;
        allItems = data && Array.isArray(data.items) ? data.items : [];
        _invalidateDupeMap();
        _invalidateFolderCache();
        _saveCatalogCache(allItems);
        console.info('Initial catalog parsed after', Date.now() - t0, 'ms:', allItems.length, 'items');
        showFolderView();
        /* If still building, show indexing toast and poll for updates */
        if (data && data.refreshing) {
          var refreshDetail = data.detail || 'Building index in background…';
          console.info('Catalog served from quick scan, index still building:', refreshDetail);
          showIndexingToast(refreshDetail, data.cache);
          if ((_toolState && _toolState.autoRefresh || 'auto') !== 'off') scheduleBackgroundRefresh();
        } else {
          hideIndexingToast();
        }
        return allItems;
      })
      .catch(function(err) {
        console.error('Initial catalog load failed:', err);
        showCatalogLoadError(err && err.message ? err.message : 'Library could not be loaded.');
        return [];
      });
  }

  /* ── breadcrumb ──────────────────────────────────────────────────────
     Lives inline in the header (between the Home button and the flexible
     spacer, see docs/IMPLEMENTATION_PLAN.md "UI-Template-Vereinheitlichung").
     Only the path segments are rendered — no redundant "Home" entry, since
     the header-logo button already covers that. When visible, hides
     `.logo-title` so the current folder name isn't shown twice.
     Markup building (segments, offline special-case, escaping) is ported
     to `webui/src/breadcrumb.ts::renderBreadcrumbHtml()`, bridged onto
     `window` (see main.ts) — this bare identifier resolves through the
     normal JS scope chain to window.renderBreadcrumbHtml. Do not re-inline
     that logic here; extend breadcrumb.ts instead. */
  function renderBreadcrumb() {
    if (!currentPath) {
      breadcrumb.classList.remove('visible');
      headerTitle.style.display = '';
      return;
    }
    breadcrumb.classList.add('visible');
    headerTitle.style.display = 'none';
    breadcrumb.innerHTML = renderBreadcrumbHtml(currentPath, escHtml);
    breadcrumb.querySelectorAll('a').forEach(function(a) {
      a.addEventListener('click', function() {
        currentPath = a.dataset.path;
        showFolderView();
      });
    });
  }

  /* ── view toggle ── */
  var IC_GRID = '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>';
  var IC_LIST = '<svg viewBox="0 0 24 24"><circle cx="4" cy="6" r="1.6" fill="currentColor"/><circle cx="4" cy="12" r="1.6" fill="currentColor"/><circle cx="4" cy="18" r="1.6" fill="currentColor"/><line x1="9" y1="6" x2="21" y2="6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="9" y1="12" x2="21" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="9" y1="18" x2="21" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
  var IC_FILENAMES = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="14" y2="6"/><line x1="3" y1="12" x2="18" y2="12"/><line x1="3" y1="18" x2="11" y2="18"/><polyline points="17,15 20,18 17,21" stroke-linejoin="round"/></svg>';
  var IC_TABLE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="1"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="9" y1="10" x2="9" y2="20"/><line x1="15" y1="10" x2="15" y2="20"/></svg>';
  /* Toggle the track-list detail/table view (audio only). Rebuilds the
     list (force=true) so column layout + inline-edit affordances update. */
  function _toggleTrackViewMode() {
    trackViewMode = (trackViewMode === 'table') ? 'rows' : 'table';
    localStorage.setItem('ht-track-view-mode', trackViewMode);
    _applyTrackViewMode();
    renderTracks(playlistItems.length ? playlistItems : filteredItems, true);
  }
  function _applyTrackViewMode() {
    var tableMode = trackViewMode === 'table' && !isVideoMode;
    trackList.classList.toggle('table-mode', tableMode);
    var hdr = document.getElementById('track-table-header');
    if (tableMode) {
      if (!hdr) {
        hdr = document.createElement('div');
        hdr.id = 'track-table-header';
        hdr.className = 'track-table-header';
        hdr.innerHTML = window._trackTableHeaderHtml; /* webui/src/chromeHtml.ts */
        trackList.parentNode.insertBefore(hdr, trackList);
      }
    } else if (hdr) {
      hdr.remove();
    }
    if (viewToggle && _isTrackViewVisible()) {
      var _vt = window._viewToggleView(tableMode, isVideoMode); /* webui/src/chromeHtml.ts */
      viewToggle.innerHTML = _vt.useListIcon ? IC_LIST : IC_TABLE;
      viewToggle.title = _vt.title;
      viewToggle.classList.toggle('view-toggle-locked', _vt.locked);
    }
  }
  function _isTrackViewVisible() {
    return trackView && !trackView.classList.contains('view-hidden');
  }
  function applyViewMode() {
    if (_isTrackViewVisible()) {
      /* Track (playlist/folder) view is showing — the toggle button
         controls the detail/table view instead of the folder grid mode. */
      _applyTrackViewMode();
      return;
    }
    if (_anyToolActive()) {
      /* Tools mode: force list view with raw filenames, toggle locked */
      folderGrid.classList.add('list-mode');
      folderGrid.classList.add('filenames-mode');
      viewToggle.innerHTML = IC_LIST;
      viewToggle.title = 'Tools aktiv \u2014 Listenansicht mit Dateinamen';
      viewToggle.classList.add('view-toggle-locked');
    } else if (viewMode === 'list') {
      folderGrid.classList.add('list-mode');
      folderGrid.classList.remove('filenames-mode');
      viewToggle.innerHTML = IC_GRID;
      viewToggle.title = 'Listenansicht \u2014 Klick f\u00fcr Kachelansicht';
      viewToggle.classList.remove('view-toggle-locked');
    } else {
      /* 'grid' */
      folderGrid.classList.remove('list-mode');
      folderGrid.classList.remove('filenames-mode');
      viewToggle.innerHTML = IC_LIST;
      viewToggle.title = 'Kachelansicht \u2014 Klick f\u00fcr Listenansicht';
      viewToggle.classList.remove('view-toggle-locked');
    }
  }

  /* ── folder view ── */

"""
    )
