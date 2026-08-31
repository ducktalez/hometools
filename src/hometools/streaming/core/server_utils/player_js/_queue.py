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
    if (!_queuePanel) return;
    var bar = document.querySelector('.player-bar');
    var barH = bar ? bar.offsetHeight : 80;
    _queuePanel.style.bottom = barH + 'px';
    /* Compute available space: header top → player bar top */
    var hdr = document.querySelector('header');
    var hdrH = hdr ? hdr.offsetHeight : 56;
    var available = window.innerHeight - hdrH - barH - 8; /* 8px breathing room */
    if (available < _QUEUE_MIN_H) available = _QUEUE_MIN_H;
    /* Apply user-chosen height if set, otherwise use full available space */
    var h = _queueUserHeight ? Math.min(_queueUserHeight, available) : available;
    if (h < _QUEUE_MIN_H) h = _QUEUE_MIN_H;
    _queuePanel.style.maxHeight = h + 'px';
  }

  /* ── Queue drag-to-resize ── */
  (function _initQueueResize() {
    if (!_queueDragHandle || !_queuePanel) return;
    var _dragging = false;
    var _startY = 0;
    var _startH = 0;

    function _getAvailable() {
      var bar = document.querySelector('.player-bar');
      var barH = bar ? bar.offsetHeight : 80;
      var hdr = document.querySelector('header');
      var hdrH = hdr ? hdr.offsetHeight : 56;
      return window.innerHeight - hdrH - barH - 8;
    }

    function onPointerDown(e) {
      if (!_queueOpen) return;
      e.preventDefault();
      _dragging = true;
      _startY = e.touches ? e.touches[0].clientY : e.clientY;
      _startH = _queuePanel.offsetHeight;
      _queuePanel.classList.add('dragging');
      document.addEventListener('mousemove', onPointerMove, {passive: false});
      document.addEventListener('touchmove', onPointerMove, {passive: false});
      document.addEventListener('mouseup', onPointerUp);
      document.addEventListener('touchend', onPointerUp);
    }

    function onPointerMove(e) {
      if (!_dragging) return;
      e.preventDefault();
      var clientY = e.touches ? e.touches[0].clientY : e.clientY;
      var delta = _startY - clientY; /* positive = dragging up = taller */
      var available = _getAvailable();
      if (available < _QUEUE_MIN_H) available = _QUEUE_MIN_H;
      var newH = Math.max(_QUEUE_MIN_H, Math.min(_startH + delta, available));
      _queuePanel.style.maxHeight = newH + 'px';
    }

    function onPointerUp(e) {
      if (!_dragging) return;
      _dragging = false;
      _queuePanel.classList.remove('dragging');
      /* Persist the chosen height (enforce minimum) */
      var finalH = _queuePanel.offsetHeight;
      if (finalH >= _QUEUE_MIN_H) {
        _queueUserHeight = finalH;
        try { localStorage.setItem(_QUEUE_HEIGHT_KEY, String(finalH)); } catch(ex) {}
      }
      document.removeEventListener('mousemove', onPointerMove);
      document.removeEventListener('touchmove', onPointerMove);
      document.removeEventListener('mouseup', onPointerUp);
      document.removeEventListener('touchend', onPointerUp);
    }

    _queueDragHandle.addEventListener('mousedown', onPointerDown);
    _queueDragHandle.addEventListener('touchstart', onPointerDown, {passive: false});
  })();
  /* Recalc on window resize */
  window.addEventListener('resize', function() { if (_queueOpen) _syncQueueBottom(); });

  function openQueuePanel() {
    _ensureQueueDom();
    if (!_queuePanel) return;
    _queueOpen = true;
    /* Close lyrics panel if open */
    if (_lyricsOpen) closeLyricsPanel();
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

  /* Peek-handle above the player bar: click opens/closes the queue; a
     drag-up gesture (beyond a small threshold) also opens it. This is the
     sole entry point to the queue now — the old dedicated queue icon
     button was removed. Only visible while the queue has items. */
  (function _initQueuePeekHandle() {
    if (!_queuePeekHandle) return;
    var _peekDragging = false;
    var _peekStartY = 0;
    var _peekOpenedByDrag = false;
    var _PEEK_OPEN_THRESHOLD = 12; /* px dragged upward before we open */

    function onDown(e) {
      _peekDragging = true;
      _peekOpenedByDrag = false;
      _peekStartY = e.touches ? e.touches[0].clientY : e.clientY;
      document.addEventListener('mousemove', onMove, { passive: false });
      document.addEventListener('touchmove', onMove, { passive: false });
      document.addEventListener('mouseup', onUp);
      document.addEventListener('touchend', onUp);
    }
    function onMove(e) {
      if (!_peekDragging || _queueOpen) return;
      var clientY = e.touches ? e.touches[0].clientY : e.clientY;
      var delta = _peekStartY - clientY; /* positive = dragged up */
      if (delta > _PEEK_OPEN_THRESHOLD) {
        _peekOpenedByDrag = true;
        openQueuePanel();
      }
    }
    function onUp() {
      _peekDragging = false;
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('touchmove', onMove);
      document.removeEventListener('mouseup', onUp);
      document.removeEventListener('touchend', onUp);
    }
    _queuePeekHandle.addEventListener('mousedown', onDown);
    _queuePeekHandle.addEventListener('touchstart', onDown, { passive: false });
    _queuePeekHandle.addEventListener('click', function() {
      /* A drag-triggered open already happened — a plain click should not
         immediately re-toggle (close) it right after. */
      if (_peekOpenedByDrag) { _peekOpenedByDrag = false; return; }
      toggleQueuePanel();
    });
  })();

  if (_queueClose) {
    _queueClose.addEventListener('click', closeQueuePanel);
  }
  if (_queueClearBtn) {
    _queueClearBtn.addEventListener('click', function() {
      clearQueue();
      showToast('Warteschlange geleert');
    });
  }

  /* ── Queue drag-and-drop reorder ── */
  function destroyQueueDragDrop() {
    if (_queueDndCleanup) { _queueDndCleanup(); _queueDndCleanup = null; }
  }

  function initQueueDragDrop() {
    destroyQueueDragDrop();
    var qList = document.getElementById('queue-list');
    if (!qList) return;
    var items = qList.querySelectorAll('.queue-item');
    if (items.length < 2) return;

    var _dragItem = null;
    var _dragFromIdx = -1;
    var _ghost = null;
    var _dropTarget = null;
    var _dropAbove = true;
    var _longPressTimer = null;
    var _touchStartY = 0;
    var _touchStartX = 0;
    var _dragActive = false;
    var LONG_PRESS_MS = 400;
    var MOVE_THRESHOLD = 8;

    function getQueueItem(el) {
      while (el && el !== qList) {
        if (el.classList && el.classList.contains('queue-item')) return el;
        el = el.parentElement;
      }
      return null;
    }

    function createGhost(item, x, y) {
      var g = document.createElement('div');
      g.className = 'playlist-drag-ghost';
      var img = item.querySelector('.queue-item-thumb');
      var title = item.querySelector('.queue-item-title');
      if (img && img.src) g.innerHTML = '<img src="' + img.src + '">';
      g.innerHTML += '<span>' + (title ? title.textContent : '') + '</span>';
      g.style.left = (x - 20) + 'px';
      g.style.top = (y - 20) + 'px';
      document.body.appendChild(g);
      return g;
    }

    function moveGhost(x, y) {
      if (!_ghost) return;
      _ghost.style.left = (x - 20) + 'px';
      _ghost.style.top = (y - 20) + 'px';
    }

    function clearDropIndicator() {
      qList.querySelectorAll('.drag-over-above,.drag-over-below').forEach(function(el) {
        el.classList.remove('drag-over-above', 'drag-over-below');
      });
      _dropTarget = null;
    }

    function updateDropTarget(x, y) {
      if (_ghost) _ghost.style.display = 'none';
      var el = document.elementFromPoint(x, y);
      if (_ghost) _ghost.style.display = '';
      var target = el ? getQueueItem(el) : null;
      if (!target || target === _dragItem) { clearDropIndicator(); return; }
      var rect = target.getBoundingClientRect();
      var above = (y - rect.top) < rect.height / 2;
      clearDropIndicator();
      _dropTarget = target;
      _dropAbove = above;
      target.classList.add(above ? 'drag-over-above' : 'drag-over-below');
    }

    function finishDrag() {
      if (!_dragActive || !_dragItem || !_dropTarget) { cancelDrag(); return; }
      var fromIdx = Number(_dragItem.dataset.queueIndex);
      var toIdx = Number(_dropTarget.dataset.queueIndex);
      if (!_dropAbove) toIdx += 1;
      if (fromIdx < toIdx) toIdx -= 1;
      if (fromIdx !== toIdx && fromIdx >= 0 && toIdx >= 0 && fromIdx < _userQueue.length) {
        var moved = _userQueue.splice(fromIdx, 1)[0];
        _userQueue.splice(Math.min(toIdx, _userQueue.length), 0, moved);
      }
      cancelDrag();
      renderQueuePanel();
    }

    function cancelDrag() {
      _dragActive = false;
      if (_ghost) { _ghost.remove(); _ghost = null; }
      clearDropIndicator();
      if (_dragItem) _dragItem.style.opacity = '';
      _dragItem = null;
      _dragFromIdx = -1;
      document.body.classList.remove('playlist-dragging');
      if (_longPressTimer) { clearTimeout(_longPressTimer); _longPressTimer = null; }
    }

    function startDrag(item, x, y) {
      _dragActive = true;
      _dragItem = item;
      _dragFromIdx = Number(item.dataset.queueIndex);
      _ghost = createGhost(item, x, y);
      item.style.opacity = '0.3';
      document.body.classList.add('playlist-dragging');
    }

    /* Touch events */
    function onTouchStart(e) {
      var item = getQueueItem(e.target);
      if (!item || e.target.closest('.queue-item-remove')) return;
      _touchStartX = e.touches[0].clientX;
      _touchStartY = e.touches[0].clientY;
      _longPressTimer = setTimeout(function() {
        _longPressTimer = null;
        if (navigator.vibrate) navigator.vibrate(30);
        startDrag(item, _touchStartX, _touchStartY);
      }, LONG_PRESS_MS);
    }
    function onTouchMove(e) {
      if (_longPressTimer) {
        var dx = Math.abs(e.touches[0].clientX - _touchStartX);
        var dy = Math.abs(e.touches[0].clientY - _touchStartY);
        if (dx > MOVE_THRESHOLD || dy > MOVE_THRESHOLD) {
          clearTimeout(_longPressTimer); _longPressTimer = null;
        }
      }
      if (_dragActive) {
        e.preventDefault();
        var tx = e.touches[0].clientX, ty = e.touches[0].clientY;
        moveGhost(tx, ty);
        updateDropTarget(tx, ty);
      }
    }
    function onTouchEnd() {
      if (_longPressTimer) { clearTimeout(_longPressTimer); _longPressTimer = null; }
      if (_dragActive) finishDrag();
    }

    /* Mouse events */
    var _mouseItem = null;
    var _mouseStartX = 0, _mouseStartY = 0;
    function onMouseDown(e) {
      if (e.button !== 0) return;
      var item = getQueueItem(e.target);
      if (!item || e.target.closest('.queue-item-remove')) return;
      _mouseItem = item;
      _mouseStartX = e.clientX;
      _mouseStartY = e.clientY;
    }
    function onMouseMove(e) {
      if (_mouseItem && !_dragActive) {
        var dx = Math.abs(e.clientX - _mouseStartX);
        var dy = Math.abs(e.clientY - _mouseStartY);
        if (dx > MOVE_THRESHOLD || dy > MOVE_THRESHOLD) {
          startDrag(_mouseItem, e.clientX, e.clientY);
          _mouseItem = null;
        }
      }
      if (_dragActive) {
        e.preventDefault();
        moveGhost(e.clientX, e.clientY);
        updateDropTarget(e.clientX, e.clientY);
      }
    }
    function onMouseUp() {
      _mouseItem = null;
      if (_dragActive) finishDrag();
    }

    qList.addEventListener('touchstart', onTouchStart, { passive: true });
    qList.addEventListener('touchmove', onTouchMove, { passive: false });
    qList.addEventListener('touchend', onTouchEnd);
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    qList.addEventListener('mousedown', onMouseDown);

    _queueDndCleanup = function() {
      qList.removeEventListener('touchstart', onTouchStart);
      qList.removeEventListener('touchmove', onTouchMove);
      qList.removeEventListener('touchend', onTouchEnd);
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      qList.removeEventListener('mousedown', onMouseDown);
      cancelDrag();
    };
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
        /* Detect any change: count OR missing/added path */
        var changed = fresh.length !== allItems.length;
        if (!changed && fresh.length > 0) {
          var freshSet = {};
          fresh.forEach(function(it) { freshSet[it.relative_path] = true; });
          changed = allItems.some(function(it) { return !freshSet[it.relative_path]; });
        }
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
        var hhmm = String(dt.getHours()).padStart(2, '0') + ':' + String(dt.getMinutes()).padStart(2, '0');
        infoEl.textContent = allItems.length + ' Titel (' + hhmm + ')';
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
      var diff = allItems.length - oldCount;
      var msg = allItems.length + ' Titel geladen';
      if (diff > 0) msg += ' (+' + diff + ' neu)';
      else if (diff < 0) msg += ' (' + diff + ' entfernt)';
      showToast(msg);
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
      var anyChange = data.changed > 0;
      /* Patch allItems */
      for (var i = 0; i < allItems.length; i++) {
        var rp = allItems[i].relative_path;
        if (ratings.hasOwnProperty(rp) && allItems[i].rating !== ratings[rp]) {
          allItems[i] = Object.assign({}, allItems[i], { rating: ratings[rp] });
        }
      }
      /* Patch playlistItems */
      for (var j = 0; j < playlistItems.length; j++) {
        var rp2 = playlistItems[j].relative_path;
        if (ratings.hasOwnProperty(rp2) && playlistItems[j].rating !== ratings[rp2]) {
          playlistItems[j] = Object.assign({}, playlistItems[j], { rating: ratings[rp2] });
        }
      }
      /* Show refresh timestamp */
      var infoEl = document.getElementById('refresh-info');
      if (infoEl && data.last_refresh) {
        var dt = new Date(data.last_refresh);
        var hhmm = String(dt.getHours()).padStart(2, '0') + ':' + String(dt.getMinutes()).padStart(2, '0');
        var countInfo = Object.keys(ratings).length + ' Ratings gelesen';
        if (anyChange) countInfo += ', ' + data.changed + ' aktualisiert';
        infoEl.textContent = countInfo + ' (' + hhmm + ')';
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

  /* compute direct sub-folders and loose files at a path level */
  var IGNORED_FOLDERS = {'#recycle': true, '@eaDir': true};

  /* detectLangFromName/detectSubLangFromName: ported to
     webui/src/langDetect.ts, bridged onto window by main.ts. */

  /* cleanFolderName() now lives in webui/src/breadcrumb.ts, bridged onto
     window (see main.ts) — this bare identifier resolves through the
     normal JS scope chain to window.cleanFolderName. */

  function langBadgesHtml(langs) {
    if (!langs || !langs.length) return '';
    var html = '';
    langs.forEach(function(lc) {
      var svg = LANG_TO_FLAG[lc];
      if (svg) {
        html += '<span class="lang-badge" title="' + lc.toUpperCase() + '">' + svg + '</span>';
      }
    });
    return html;
  }


  /* Composite flag: main language flag with optional smaller subtitle flag overlay */
  function compositeFlagHtml(mainLang, subLang) {
    var mainSvg = mainLang && LANG_TO_FLAG[mainLang] ? LANG_TO_FLAG[mainLang] : '';
    if (!mainSvg) return '';
    var subSvg = subLang && LANG_TO_FLAG[subLang] ? LANG_TO_FLAG[subLang] : '';
    if (!subSvg) {
      return '<span class="composite-flag" title="' + (mainLang || '').toUpperCase() + '">' + mainSvg + '</span>';
    }
    return '<span class="composite-flag" title="' + (mainLang || '').toUpperCase() + ' + ' + (subLang || '').toUpperCase() + ' Sub">' +
      mainSvg +
      '<span class="composite-flag-sub">' + subSvg + '</span>' +
    '</span>';
  }

  function contentsAt(path) {
    var items = itemsUnder(path);
    var folderMap = {};
    var folderThumb = {};
    var folderThumbLg = {};
    var folderLangs = {};
    var folderSubLangs = {};
    var files = [];
    var off = path ? path.length + 1 : 0;
    items.forEach(function(it) {
      var rest = it.relative_path.substring(off);
      var slash = rest.indexOf('/');
      if (slash >= 0) {
        var name = rest.substring(0, slash);
        if (IGNORED_FOLDERS[name]) return;
        if (!folderMap[name]) folderMap[name] = 0;
        folderMap[name]++;
        if (!folderThumb[name] && it.thumbnail_url) folderThumb[name] = it.thumbnail_url;
        if (!folderThumbLg[name] && it.thumbnail_lg_url) folderThumbLg[name] = it.thumbnail_lg_url;
        /* Aggregate languages from items + folder-name detection */
        if (!folderLangs[name]) folderLangs[name] = {};
        if (it.language) folderLangs[name][it.language] = true;
        var folderLang = detectLangFromName(name);
        if (folderLang) folderLangs[name][folderLang] = true;
        /* Aggregate subtitle languages from items + folder-name detection */
        if (!folderSubLangs[name]) folderSubLangs[name] = '';
        if (!folderSubLangs[name] && it.subtitle_language) folderSubLangs[name] = it.subtitle_language;
        if (!folderSubLangs[name]) {
          var detSub = detectSubLangFromName(name);
          if (detSub) folderSubLangs[name] = detSub;
        }
      } else {
        files.push(it);
      }
    });
    var folders = Object.keys(folderMap)
      .sort(function(a, b) {
        /* Favorites (#-prefixed) first, then alphabetical */
        var aFav = a.charAt(0) === '#';
        var bFav = b.charAt(0) === '#';
        if (aFav !== bFav) return aFav ? -1 : 1;
        return a.localeCompare(b);
      })
      .map(function(n) {
        var isFav = n.charAt(0) === '#';
        var langs = folderLangs[n] ? Object.keys(folderLangs[n]).sort() : [];
        return {
          name: n,
          displayName: cleanFolderName(n),
          isFavorite: isFav,
          count: folderMap[n],
          thumbnail_url: folderThumb[n] || '',
          thumbnail_lg_url: folderThumbLg[n] || '',
          languages: langs,
          subLang: folderSubLangs[n] || '',
          variants: null
        };
      });

    /* ── Multi-language merge ── */
    /* Group folders by merge-key: LANG_GROUPS[name] or displayName */
    var _mergeMap = {};
    folders.forEach(function(f) {
      var key = LANG_GROUPS[f.name] || f.displayName;
      if (!_mergeMap[key]) _mergeMap[key] = [];
      _mergeMap[key].push(f);
    });
    var merged = [];
    Object.keys(_mergeMap).forEach(function(key) {
      var group = _mergeMap[key];
      if (group.length === 1) {
        merged.push(group[0]);
        return;
      }
      /* Pick primary: prefer variant without language tag, or favorite, or first */
      var primary = group[0];
      for (var gi = 0; gi < group.length; gi++) {
        if (group[gi].isFavorite) { primary = group[gi]; break; }
        if (!detectLangFromName(group[gi].name) && !LANG_GROUPS[group[gi].name]) primary = group[gi];
      }
      var allLangs = {};
      var totalCount = 0;
      var variants = [];
      group.forEach(function(g) {
        totalCount += g.count;
        g.languages.forEach(function(lc) { allLangs[lc] = true; });
        var lang = g.languages.length ? g.languages[0] : detectLangFromName(g.name) || '';
        var subLang = detectSubLangFromName(g.name) || g.subLang || '';
        variants.push({ name: g.name, lang: lang, subLang: subLang, count: g.count });
      });
      merged.push({
        name: primary.name,
        displayName: primary.displayName,
        isFavorite: group.some(function(g) { return g.isFavorite; }),
        count: totalCount,
        thumbnail_url: primary.thumbnail_url || group[1].thumbnail_url || '',
        thumbnail_lg_url: primary.thumbnail_lg_url || group[1].thumbnail_lg_url || '',
        languages: Object.keys(allLangs).sort(),
        variants: variants
      });
    });

    return { folders: merged, files: files };
  }

  /* leafName()/parentPath() now live in webui/src/pathUtils.ts, bridged
     onto window (see main.ts) — these bare identifiers resolve through
     the normal JS scope chain to window.leafName/window.parentPath. */

  function showLoadingState(message) {
    folderGrid.classList.remove('view-hidden');
    trackView.classList.add('view-hidden');
    filterBar.classList.add('view-hidden');
    playAllBtn.classList.add('disabled');
    backBtn.classList.toggle('disabled', !currentPath);
    headerTitle.textContent = currentPath ? leafName(currentPath) : originalTitle;
    trackCount.textContent = 'Loading…';
    if (!player.currentSrc) playerBar.classList.add('view-hidden');
    folderGrid.innerHTML = '<div class="empty-hint">' + escHtml(message || 'Loading library…') + '</div>';
    renderBreadcrumb();
    applyViewMode();
  }

  function showCatalogLoadError(detail) {
    folderGrid.classList.remove('view-hidden');
    trackView.classList.add('view-hidden');
    filterBar.classList.add('view-hidden');
    playAllBtn.classList.add('disabled');
    if (!player.currentSrc) playerBar.classList.add('view-hidden');
    trackCount.textContent = 'Library unavailable';
    headerTitle.textContent = currentPath ? leafName(currentPath) : originalTitle;
    backBtn.classList.toggle('disabled', !currentPath);
    backBtn.style.display = currentPath ? 'inline-block' : 'none';
    folderGrid.innerHTML = '<div class="empty-hint">' + escHtml(detail || 'Library could not be loaded.') + '</div>';
    renderBreadcrumb();
    applyViewMode();
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
          /* Detect deletions: check whether any currently cached path is absent
             from the fresh catalog (count-only check misses e.g. replaced files). */
          var freshPaths = null;
          var hasDeletion = false;
          if (fresh.length === allItems.length && allItems.length > 0) {
            freshPaths = {};
            fresh.forEach(function(i) { freshPaths[i.relative_path] = true; });
            hasDeletion = allItems.some(function(i) { return !freshPaths[i.relative_path]; });
          }
          var changed = fresh.length !== allItems.length || hasDeletion;
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
  var IC_LIST = '<svg viewBox="0 0 24 24"><line x1="3" y1="6" x2="21" y2="6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="3" y1="12" x2="21" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="3" y1="18" x2="21" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
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
        hdr.innerHTML =
          '<span></span><span></span>' +
          '<span>Titel</span><span>Interpret</span>' +
          '<span>Dauer</span><span>Genre</span><span>BPM</span><span>\u2605</span><span></span>';
        trackList.parentNode.insertBefore(hdr, trackList);
      }
    } else if (hdr) {
      hdr.remove();
    }
    if (viewToggle && _isTrackViewVisible()) {
      viewToggle.innerHTML = tableMode ? IC_LIST : IC_TABLE;
      viewToggle.title = tableMode
        ? 'Detailansicht \u2014 Klick f\u00fcr normale Listenansicht'
        : 'Listenansicht \u2014 Klick f\u00fcr Detailansicht (Tabelle)';
      viewToggle.classList.toggle('view-toggle-locked', isVideoMode);
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
