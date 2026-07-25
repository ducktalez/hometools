"""JS fragment: drag drop init (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_drag_drop_init_js() -> str:
    """Return the drag drop init section of the player JS."""
    return """  function initPlaylistDragDrop() {
    destroyPlaylistDragDrop();

    var trackList = document.getElementById('track-list');
    if (!trackList) return;
    var items = trackList.querySelectorAll('.track-item:not(.missing-episode)');
    if (items.length < 2) return;

    var _dragItem = null;
    var _dragPath = '';
    var _dragFromIdx = -1;
    var _ghost = null;
    var _dropTarget = null;
    var _dropAbove = true;
    var _longPressTimer = null;
    var _touchStartY = 0;
    var _touchStartX = 0;
    var _dragActive = false;
    var _pendingDrag = null;
    var LONG_PRESS_MS = 500;
    var MOVE_THRESHOLD = 10;

    function getTrackItem(el) {
      while (el && el !== trackList) {
        if (el.classList && el.classList.contains('track-item')) return el;
        el = el.parentElement;
      }
      return null;
    }

    function createGhost(item, x, y) {
      var g = document.createElement('div');
      g.className = 'playlist-drag-ghost';
      var img = item.querySelector('.track-thumb');
      var titleEl = item.querySelector('.track-title-text') || item.querySelector('.track-title');
      if (img && img.src) g.innerHTML = '<img src="' + img.src + '">';
      g.innerHTML += '<span>' + (titleEl ? titleEl.textContent : '') + '</span>';
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

    function clearDragClasses() {
      trackList.querySelectorAll('.drag-over-above,.drag-over-below,.dragging').forEach(function(el) {
        el.classList.remove('drag-over-above', 'drag-over-below', 'dragging');
      });
    }

    function clearDropIndicator() {
      if (_dropTarget) {
        _dropTarget.classList.remove('drag-over-above', 'drag-over-below');
        _dropTarget = null;
      }
    }

    function updateDropTarget(x, y) {
      if (_ghost) _ghost.style.display = 'none';
      var el = document.elementFromPoint(x, y);
      if (_ghost) _ghost.style.display = '';
      var target = el ? getTrackItem(el) : null;

      if (!target) {
        if (_dragItem) {
          var dragRect = _dragItem.getBoundingClientRect();
          if (dragRect.height > 0 &&
              x >= dragRect.left && x <= dragRect.right &&
              y >= dragRect.top && y <= dragRect.bottom) {
            clearDropIndicator();
            return;
          }
        }
        var tlRect = trackList.getBoundingClientRect();
        if (x >= tlRect.left && x <= tlRect.right &&
            y >= tlRect.top && y <= tlRect.bottom) {
          var visibleItems = trackList.querySelectorAll(
            '.track-item:not(.missing-episode):not(.dragging)');
          if (visibleItems.length > 0) {
            var lastItem = visibleItems[visibleItems.length - 1];
            if (_dropTarget !== lastItem) clearDropIndicator();
            _dropTarget = lastItem;
            _dropAbove = false;
            lastItem.classList.remove('drag-over-above');
            lastItem.classList.add('drag-over-below');
            return;
          }
        }
        clearDropIndicator();
        return;
      }

      if (target === _dragItem) { clearDropIndicator(); return; }

      var rect = target.getBoundingClientRect();
      var mid = rect.top + rect.height / 2;
      var above = y < mid;

      if (!above) {
        var nextSib = target.nextElementSibling;
        while (nextSib && (!nextSib.classList.contains('track-item') ||
               nextSib.classList.contains('missing-episode') ||
               nextSib === _dragItem)) {
          nextSib = nextSib.nextElementSibling;
        }
        if (nextSib && nextSib.classList.contains('track-item')) {
          target = nextSib;
          above = true;
        }
      }

      _dropAbove = above;

      var candidateIdx = Number(target.dataset.index);
      var candidateTo = above ? candidateIdx : candidateIdx + 1;
      if (_dragFromIdx < candidateTo) candidateTo--;
      if (candidateTo === _dragFromIdx) { clearDropIndicator(); return; }

      if (_dropTarget !== target) clearDropIndicator();
      _dropTarget = target;
      target.classList.toggle('drag-over-above', above);
      target.classList.toggle('drag-over-below', !above);
    }

    function startDrag(item, x, y) {
      _dragActive = true;
      _dragItem = item;
      _dragPath = '';
      var idx = Number(item.dataset.index);
      if (filteredItems[idx]) {
        _dragPath = filteredItems[idx].relative_path;
        _dragFromIdx = idx;
      }
      item.classList.add('dragging');
      document.body.classList.add('playlist-dragging');
      _ghost = createGhost(item, x, y);
    }

    function endDrag() {
      if (_longPressTimer) { clearTimeout(_longPressTimer); _longPressTimer = null; }
      if (!_dragActive) return;
      _dragActive = false;
      if (_ghost) { _ghost.remove(); _ghost = null; }
      document.body.classList.remove('playlist-dragging');

      if (_dropTarget && _dragPath) {
        var targetIdx = Number(_dropTarget.dataset.index);
        var toIndex = _dropAbove ? targetIdx : targetIdx + 1;
        if (_dragFromIdx < toIndex) toIndex--;
        if (toIndex !== _dragFromIdx && toIndex >= 0) {
          reorderPlaylistItem(_dragPath, toIndex);
        }
      }
      clearDragClasses();
      _dragItem = null;
      _dropTarget = null;
    }

    /* --- Named handlers for proper cleanup --- */
    function onMouseDown(e) {
      if (e.button !== 0) return;
      if (e.target.closest('.track-dl-btn,.track-pin-btn,.track-edit-btn,.track-playlist-btn,.track-queue-btn,.track-inline-rating-star,.track-title-text,.track-artist')) return;
      var item = getTrackItem(e.target);
      if (!item) return;
      _pendingDrag = { item: item, x: e.clientX, y: e.clientY };
    }
    function onMouseMove(e) {
      if (_pendingDrag && !_dragActive) {
        var pdx = Math.abs(e.clientX - _pendingDrag.x);
        var pdy = Math.abs(e.clientY - _pendingDrag.y);
        if (pdx > MOVE_THRESHOLD || pdy > MOVE_THRESHOLD) {
          startDrag(_pendingDrag.item, e.clientX, e.clientY);
          _pendingDrag = null;
        } else {
          return;
        }
      }
      if (!_dragActive) return;
      e.preventDefault();
      moveGhost(e.clientX, e.clientY);
      updateDropTarget(e.clientX, e.clientY);
      var rect = trackList.getBoundingClientRect();
      var scrollZone = 50;
      if (e.clientY < rect.top + scrollZone) trackList.scrollTop -= 8;
      if (e.clientY > rect.bottom - scrollZone) trackList.scrollTop += 8;
    }
    function onMouseUp() { _pendingDrag = null; endDrag(); }

    function onTouchStart(e) {
      if (e.touches.length !== 1) return;
      if (e.target.closest('.track-dl-btn,.track-pin-btn,.track-edit-btn,.track-playlist-btn,.track-queue-btn,.track-inline-rating-star,.track-title-text,.track-artist')) return;
      var item = getTrackItem(e.target);
      if (!item) return;
      _touchStartX = e.touches[0].clientX;
      _touchStartY = e.touches[0].clientY;
      _longPressTimer = setTimeout(function() {
        _longPressTimer = null;
        startDrag(item, _touchStartX, _touchStartY);
        if (navigator.vibrate) navigator.vibrate(30);
      }, LONG_PRESS_MS);
    }
    function onTouchMove(e) {
      if (_longPressTimer) {
        var dx = Math.abs(e.touches[0].clientX - _touchStartX);
        var dy = Math.abs(e.touches[0].clientY - _touchStartY);
        if (dx > MOVE_THRESHOLD || dy > MOVE_THRESHOLD) {
          clearTimeout(_longPressTimer);
          _longPressTimer = null;
        }
      }
      if (!_dragActive) return;
      e.preventDefault();
      var tx = e.touches[0].clientX;
      var ty = e.touches[0].clientY;
      moveGhost(tx, ty);
      updateDropTarget(tx, ty);
      var rect = trackList.getBoundingClientRect();
      var scrollZone = 50;
      if (ty < rect.top + scrollZone) trackList.scrollTop -= 6;
      if (ty > rect.bottom - scrollZone) trackList.scrollTop += 6;
    }
    function onTouchEnd() { endDrag(); }
    function onTouchCancel() {
      if (_longPressTimer) { clearTimeout(_longPressTimer); _longPressTimer = null; }
      endDrag();
    }

    /* --- Attach listeners --- */
    trackList.addEventListener('mousedown', onMouseDown);
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    trackList.addEventListener('touchstart', onTouchStart, { passive: true });
    trackList.addEventListener('touchmove', onTouchMove, { passive: false });
    trackList.addEventListener('touchend', onTouchEnd, { passive: true });
    trackList.addEventListener('touchcancel', onTouchCancel, { passive: true });

    /* --- Cleanup function --- */
    _dndCleanup = function() {
      trackList.removeEventListener('mousedown', onMouseDown);
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      trackList.removeEventListener('touchstart', onTouchStart);
      trackList.removeEventListener('touchmove', onTouchMove);
      trackList.removeEventListener('touchend', onTouchEnd);
      trackList.removeEventListener('touchcancel', onTouchCancel);
      if (_dragActive) {
        _dragActive = false;
        if (_ghost) { _ghost.remove(); _ghost = null; }
        document.body.classList.remove('playlist-dragging');
      }
      clearDragClasses();
    };
  }

  /* ── playlist event wiring ── */
  (function() {
    if (!PLAYLISTS_ENABLED) return;
    var modalClose = document.getElementById('playlist-modal-close-btn');
    if (modalClose) modalClose.addEventListener('click', closePlaylistModal);
    var modalBackdrop = document.getElementById('playlist-modal-backdrop');
    if (modalBackdrop) modalBackdrop.addEventListener('click', function(e) { if (e.target === modalBackdrop) closePlaylistModal(); });
    var newBtn = document.getElementById('playlist-modal-new-btn');
    var newInput = document.getElementById('playlist-modal-new-name');
    if (newBtn && newInput) {
      newBtn.addEventListener('click', function() {
        var n = newInput.value.trim();
        if (!n) return;
        createAndAddToPlaylist(n, _playlistAddPath);
        newInput.value = '';
      });
      newInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { newBtn.click(); }
      });
    }
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        var mb = document.getElementById('playlist-modal-backdrop');
        if (mb && !mb.hidden) closePlaylistModal();
      }
    });
  }());

  /* ── Touch swipe gestures (mobile navigation) ── */
  (function() {
    var _swipeStartX = 0;
    var _swipeStartY = 0;
    var _swipeStartT = 0;
    var _swipeActive = false;
    var SWIPE_MIN_DIST = 60;   /* px minimum horizontal distance */
    var SWIPE_MAX_VERT = 80;   /* px max vertical deviation */
    var SWIPE_MAX_TIME = 400;  /* ms max duration */

    function swipeTarget(el) {
      /* Don't intercept swipes on range inputs (progress bar, volume) */
      while (el) {
        if (el.tagName === 'INPUT' && el.type === 'range') return null;
        if (el.tagName === 'CANVAS') return null;
        if (el.classList && el.classList.contains('edit-modal-backdrop')) return null;
        if (el.classList && el.classList.contains('lyrics-panel')) return null;
        if (el.classList && el.classList.contains('queue-panel')) return null;
        if (el.classList && el.classList.contains('offline-library')) return null;
        if (el.classList && el.classList.contains('playlist-modal-backdrop')) return null;
        el = el.parentElement;
      }
      return true;
    }

    document.addEventListener('touchstart', function(e) {
      if (!swipeTarget(e.target)) return;
      if (e.touches.length !== 1) return;
      _swipeStartX = e.touches[0].clientX;
      _swipeStartY = e.touches[0].clientY;
      _swipeStartT = Date.now();
      _swipeActive = true;
    }, { passive: true });

    document.addEventListener('touchend', function(e) {
      if (!_swipeActive) return;
      _swipeActive = false;
      if (e.changedTouches.length !== 1) return;
      var dx = e.changedTouches[0].clientX - _swipeStartX;
      var dy = e.changedTouches[0].clientY - _swipeStartY;
      var dt = Date.now() - _swipeStartT;
      if (dt > SWIPE_MAX_TIME) return;
      if (Math.abs(dy) > SWIPE_MAX_VERT) return;
      if (Math.abs(dx) < SWIPE_MIN_DIST) return;

      /* Swipe right = go back (folder view or playlist view) */
      if (dx > 0) {
        if (inPlaylist) { goBack(); }
        else if (currentPath) { goBack(); }
      }
    }, { passive: true });
  }());

  loadInitialCatalog().then(function() {
    _router.init();
    loadFavorites();
    loadUserPlaylists().then(function() {
      /* Restore view from URL once both catalog and user playlists are ready */
      _router.restore();
      /* Default: render root folder view (router was a no-op for clean URLs) */
      if (!currentPath && !inPlaylist) showFolderView();
      _startPlaylistSync();
    });
  });
}());
"""
