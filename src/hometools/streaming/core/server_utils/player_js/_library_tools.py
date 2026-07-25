"""JS fragment: library tools (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_library_tools_js(playlist_sync_interval_ms) -> str:
    """Return the library tools section of the player JS."""
    return (
        """  function _buildDuplicateMap() {
    var map = {};
    allItems.forEach(function(item, i) {
      var key = _dupeKey(item);
      if (!key) return;
      if (!map[key]) map[key] = [];
      map[key].push(i);
    });
    /* Keep only groups with 2+ items */
    _dupeMap = {};
    _dupePaths = new Set();
    _dupeSafety = {};
    var keys = Object.keys(map);
    for (var k = 0; k < keys.length; k++) {
      if (map[keys[k]].length > 1) {
        var groupIndices = map[keys[k]];
        _dupeMap[keys[k]] = groupIndices;
        /* Collect group items for safety check */
        var groupItems = groupIndices.map(function(gi) { return allItems[gi]; }).filter(Boolean);
        var isSafe = _isDupeGroupSafe(groupItems);
        groupIndices.forEach(function(gi) {
          var rp = allItems[gi] ? allItems[gi].relative_path : null;
          if (rp) {
            _dupePaths.add(rp);
            _dupeSafety[rp] = isSafe;
          }
        });
      }
    }
  }

  function _invalidateDupeMap() {
    _dupeMap = null;
    _dupePaths = null;
    _dupeSafety = null;
    _rgKey = '';  /* force re-render when allItems changes */
  }

  function _ensureDupeMap() {
    if (!_dupeMap) _buildDuplicateMap();
  }

  function _getDupeCount() {
    _ensureDupeMap();
    return Object.keys(_dupeMap).length;
  }

  function openDupePanel() {
    _ensureDupeMap();
    var backdrop = document.getElementById('dupe-panel-backdrop');
    if (!backdrop) return;
    var body = document.getElementById('dupe-panel-body');
    if (!body) return;
    var keys = Object.keys(_dupeMap);
    if (keys.length === 0) {
      body.innerHTML = '<div style="text-align:center;color:var(--sub);padding:2rem 0">Keine Duplikate gefunden.</div>';
    } else {
      var html = '';
      keys.forEach(function(key) {
        var indices = _dupeMap[key];
        var firstTitle = allItems[indices[0]] ? (allItems[indices[0]].title || key) : key;
        html += '<div class="dupe-group">';
        html += '<div class="dupe-group-header">' + IC_DUPLICATE +
          '<span>' + escHtml(firstTitle) + '</span>' +
          '<span class="dupe-group-count">(' + indices.length + 'x)</span></div>';
        indices.forEach(function(idx) {
          var t = allItems[idx];
          if (!t) return;
          var thumbSrc = t.thumbnail_url || FILE_PLACEHOLDER;
          var folder = '';
          var sl = (t.relative_path || '').lastIndexOf('/');
          if (sl > 0) folder = t.relative_path.substring(0, sl);
          /* Build metadata line: duration · kbps · size · date */
          var metaParts = [];
          if (t.duration) metaParts.push(_fmtDuration(t.duration));
          if (t.bitrate) metaParts.push(t.bitrate + '\u00a0kbps');
          if (t.file_size) metaParts.push(_fmtFileSize(t.file_size));
          if (t.mtime) metaParts.push(_fmtDate(t.mtime));
          var metaHtml = metaParts.length
            ? '<div class="dupe-group-item-meta">' + metaParts.join(' \u00b7 ') + '</div>'
            : '';
          var isSafe = _dupeSafety && _dupeSafety[t.relative_path];
          var trashCls = isSafe ? ' dupe-trash-btn--safe' : ' dupe-trash-btn--warn';
          var trashTitle = isSafe
            ? 'In den Papierkorb verschieben (Gr\u00f6\u00dfe + L\u00e4nge nahezu identisch)'
            : 'In den Papierkorb verschieben \u2014 Vorsicht: Gr\u00f6\u00dfe oder L\u00e4nge weicht ab!';
          html += '<div class="dupe-group-item" data-all-index="' + idx + '">' +
            '<img src="' + escHtml(thumbSrc) + '" alt="" loading="lazy">' +
            '<div class="dupe-group-item-info">' +
              '<div class="dupe-group-item-title">' + escHtml(t.title || t.relative_path) + '</div>' +
              '<div class="dupe-group-item-path">' + escHtml(folder || t.relative_path) + '</div>' +
              metaHtml +
            '</div>' +
            '<button class="dupe-trash-btn' + trashCls + '" data-all-index="' + idx +
            '" title="' + escHtml(trashTitle) + '">' + IC_TRASH + '</button>' +
            '</div>';
        });
        html += '</div>';
      });
      body.innerHTML = html;
      /* Wire up trash buttons */
      body.querySelectorAll('.dupe-trash-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
          e.stopPropagation();
          var ai = Number(btn.dataset.allIndex);
          _deleteDuplicateFile(ai);
        });
      });
      /* Wire up clicks to play */
      body.querySelectorAll('.dupe-group-item').forEach(function(el) {
        el.addEventListener('click', function() {
          var ai = Number(el.dataset.allIndex);
          var t = allItems[ai];
          if (!t) return;
          closeDupePanel();
          /* Navigate to folder and play */
          var sl = (t.relative_path || '').lastIndexOf('/');
          if (sl > 0) {
            var folder = t.relative_path.substring(0, sl);
            var items = itemsUnder(folder);
            showPlaylist(items, folder);
            var localIdx = -1;
            for (var j = 0; j < filteredItems.length; j++) {
              if (filteredItems[j].relative_path === t.relative_path) { localIdx = j; break; }
            }
            if (localIdx >= 0) playTrack(localIdx);
          }
        });
      });
    }
    /* Update subtitle */
    var sub = document.getElementById('dupe-panel-subtitle');
    if (sub) sub.textContent = keys.length + ' Duplikat-Gruppe' + (keys.length !== 1 ? 'n' : '') +
      ' (' + (_dupePaths ? _dupePaths.size : 0) + ' Dateien)';
    backdrop.removeAttribute('hidden');
  }

  function closeDupePanel() {
    var backdrop = document.getElementById('dupe-panel-backdrop');
    if (backdrop) backdrop.setAttribute('hidden', '');
  }

  function playDuplicates() {
    _ensureDupeMap();
    var keys = Object.keys(_dupeMap);
    if (!keys.length) { showToast('Keine Duplikate gefunden'); return; }
    /* Collect all items from dupe groups, grouped by key for natural listening order */
    var dupeItems = [];
    keys.forEach(function(key) {
      _dupeMap[key].forEach(function(idx) {
        var t = allItems[idx];
        if (t) dupeItems.push(t);
      });
    });
    if (!dupeItems.length) return;
    closeDupePanel();
    /* Show as virtual playlist */
    destroyPlaylistDragDrop();
    inPlaylist = true;
    _currentPlaylistId = '__duplicates__';
    currentPath = '';
    playlistItems = dupeItems;
    headerTitle.textContent = 'Duplikate (' + keys.length + ' Gruppen)';
    backBtn.style.display = 'inline-block';
    playAllBtn.style.display = 'none';
    folderGrid.classList.add('view-hidden');
    trackView.classList.remove('view-hidden');
    filterBar.classList.remove('view-hidden');
    filterBar.classList.add('fb-scroll-hidden');
    playerBar.classList.remove('view-hidden');
    _hideGlobalSearch();
    _initFilterBarScrollReveal();
    searchInput.value = '';
    currentIndex = -1;
    renderBreadcrumb();
    applyFilter();
    if (shuffleMode) rebuildShuffleQueue(0);
  }

  function _deleteDuplicateFile(allIndex) {
    var t = allItems[allIndex];
    if (!t) return;
    var name = t.title || t.relative_path;
    if (!confirm('Datei "' + name + '" in den Papierkorb verschieben?')) return;
    /* Check if this track is the currently playing one */
    var playingFilteredIdx = -1;
    if (currentIndex >= 0 && currentIndex < filteredItems.length &&
        filteredItems[currentIndex].relative_path === t.relative_path) {
      playingFilteredIdx = currentIndex;
    }
    var wasBefore = false;
    if (playingFilteredIdx < 0 && currentIndex >= 0) {
      for (var fi = 0; fi < currentIndex && fi < filteredItems.length; fi++) {
        if (filteredItems[fi].relative_path === t.relative_path) { wasBefore = true; break; }
      }
    }
    fetch(DELETE_API_PATH, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({path: t.relative_path})
    }).then(function(r) {
      if (!r.ok) return r.json().then(function(d) { throw new Error(d.detail || 'Fehler'); });
      return r.json();
    }).then(function() {
      /* Remove item from allItems */
      allItems.splice(allIndex, 1);
      /* Also remove from playlistItems (e.g. when in the "duplicates" virtual playlist view)
         so that filteredItems does not keep showing the deleted item on the next applyFilter() */
      var rp = t.relative_path;
      playlistItems = playlistItems.filter(function(it) { return it.relative_path !== rp; });
      _invalidateDupeMap();
      _invalidateFolderCache();
      /* Keep localStorage in sync so the deleted file is gone on the next page load too */
      _saveCatalogCache(allItems);
      /* Adjust currentIndex */
      if (wasBefore) {
        currentIndex = Math.max(0, currentIndex - 1);
      }
      showToast('Datei gel\\u00f6scht: ' + name);
      /* Re-render the track list first so filteredItems is up-to-date */
      if (inPlaylist) applyFilter();
      /* Re-render the dupe panel with updated data */
      openDupePanel();
      /* If the playing track was deleted, advance to next */
      if (playingFilteredIdx >= 0 && filteredItems.length > 0) {
        var ni = Math.min(currentIndex, filteredItems.length - 1);
        playTrack(ni);
      }
    }).catch(function(err) {
      showToast('L\\u00f6schen fehlgeschlagen: ' + (err.message || err));
    });
  }

  /* Remove a track that the player could not load (404 / gone on disk).
     Called from the player 'error' handler after a HEAD-request confirms 404.
     Mirrors the logic of _deleteTrackFromList but without the server DELETE call. */
  function _removeGoneTrack(relativePath) {
    /* If _deleteTrackFromList is already handling this path (animation still running),
       don't double-advance the player — _doRemoveRender will call playTrack after fade. */
    if (_deletePending === relativePath) return;
    showToast('Datei nicht gefunden \u2014 aus der Liste entfernt');
    /* Determine playback context before mutating filteredItems */
    var wasCurrentlyPlaying = (relativePath === _progressRelPath);
    var wasBefore = false;
    if (!wasCurrentlyPlaying && currentIndex >= 0) {
      for (var fi = 0; fi < currentIndex && fi < filteredItems.length; fi++) {
        if (filteredItems[fi].relative_path === relativePath) { wasBefore = true; break; }
      }
    }
    allItems = allItems.filter(function(it) { return it.relative_path !== relativePath; });
    _invalidateDupeMap();
    _invalidateFolderCache();
    _saveCatalogCache(allItems);
    playlistItems = playlistItems.filter(function(it) { return it.relative_path !== relativePath; });
    if (wasBefore) currentIndex = Math.max(0, currentIndex - 1);
    btnPlay.innerHTML = IC_PLAY;
    if (inPlaylist) {
      applyFilter();
      if (wasCurrentlyPlaying && filteredItems.length > 0) {
        playTrack(Math.min(currentIndex < 0 ? 0 : currentIndex, filteredItems.length - 1));
      } else if (filteredItems.length === 0) {
        showFolderView();
      }
    } else {
      showFolderView();
    }
  }

  function _deleteTrackFromList(filteredIdx) {
    var t = filteredItems[filteredIdx];
    if (!t) return;
    var name = t.title || t.relative_path;
    if (!confirm('Datei "' + name + '" in den Papierkorb verschieben?')) return;
    var wasCurrentlyPlaying = (filteredIdx === currentIndex);
    var wasBefore = (currentIndex >= 0 && filteredIdx < currentIndex);
    /* Mark IMMEDIATELY (before API call) so concurrent silent-refreshes and
       _removeGoneTrack don't re-add or double-handle the item. */
    _locallyDeletedPaths[t.relative_path] = true;
    _deletePending = t.relative_path;
    fetch(DELETE_API_PATH, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({path: t.relative_path})
    }).then(function(r) {
      if (!r.ok) return r.json().then(function(d) { throw new Error(d.detail || 'Fehler'); });
      return r.json();
    }).then(function() {
      allItems = allItems.filter(function(it) { return it.relative_path !== t.relative_path; });
      _invalidateDupeMap();
      _invalidateFolderCache();
      /* Keep localStorage in sync so the deleted file is gone on the next page load too */
      _saveCatalogCache(allItems);
      /* Adjust currentIndex so the player stays on the right track */
      if (wasBefore) {
        currentIndex = Math.max(0, currentIndex - 1);
      } else if (wasCurrentlyPlaying) {
        /* Will point to the next song (which shifted into our slot) */
        if (currentIndex >= filteredItems.length - 1) currentIndex = Math.max(0, currentIndex - 1);
      }
      showToast('Datei gel\\u00f6scht: ' + name);
      /* Re-render after the fade-out completes, or immediately if element not found */
      function _doRemoveRender() {
        _deletePending = null;
        if (inPlaylist) {
          var items = itemsUnder(currentPath);
          if (items.length) { playlistItems = items; applyFilter(); }
          else { showFolderView(); }
        } else { showFolderView(); }
        /* If the playing track was deleted, advance to the next one.
           Guard: _removeGoneTrack may have already advanced during the animation. */
        if (wasCurrentlyPlaying && filteredItems.length > 0) {
          playTrack(Math.min(currentIndex, filteredItems.length - 1));
        }
      }
      var li = trackList.querySelector('[data-index="' + filteredIdx + '"]');
      if (li) {
        li.classList.add('track-item--removing');
        li.addEventListener('animationend', _doRemoveRender, { once: true });
      } else {
        _doRemoveRender();
      }
    }).catch(function(err) {
      _locallyDeletedPaths[t.relative_path] && delete _locallyDeletedPaths[t.relative_path];
      _deletePending = null;
      showToast('L\\u00f6schen fehlgeschlagen: ' + (err.message || err));
    });
  }

  /* ── File mover (move to folder) ── */
  var _MOVE_RECENT_KEY = 'ht-move-recent';
  var _allFoldersCache = null;

  function _getRecentMoveTargets() {
    try { return JSON.parse(localStorage.getItem(_MOVE_RECENT_KEY) || '[]').slice(0, 4); }
    catch(e) { return []; }
  }

  function _saveRecentMoveTarget(folder) {
    var recent = _getRecentMoveTargets().filter(function(f) { return f !== folder; });
    recent.unshift(folder);
    if (recent.length > 4) recent = recent.slice(0, 4);
    try { localStorage.setItem(_MOVE_RECENT_KEY, JSON.stringify(recent)); } catch(e) {}
  }

  function _getAllFolders() {
    if (_allFoldersCache) return _allFoldersCache;
    var set = {};
    allItems.forEach(function(it) {
      var sl = it.relative_path.indexOf('/');
      if (sl > 0) set[it.relative_path.substring(0, sl)] = true;
    });
    _allFoldersCache = Object.keys(set).sort(function(a, b) { return a.localeCompare(b); });
    return _allFoldersCache;
  }

  function _invalidateFolderCache() { _allFoldersCache = null; }

  function _currentFolderOf(item) {
    var rp = item.relative_path || '';
    var sl = rp.indexOf('/');
    return sl > 0 ? rp.substring(0, sl) : '';
  }

  function renderMoveWidget(t, idx) {
    var curFolder = _currentFolderOf(t);
    var recent = _getRecentMoveTargets();
    var allF = _getAllFolders();
    /* Build 4 quick-pick folders: MRU first, fill with allFolders */
    var picks = recent.slice(0, 4);
    if (picks.length < 4) {
      var seen = {};
      picks.forEach(function(p) { seen[p] = true; });
      for (var fi = 0; fi < allF.length && picks.length < 4; fi++) {
        if (!seen[allF[fi]]) { picks.push(allF[fi]); seen[allF[fi]] = true; }
      }
    }
    /* The currently playing track may briefly remain at the source location while
       streaming; the server handles this gracefully (deferred delete).
       We keep the widget fully active — no disabled state. */
    var isActive = false; /* reserved, not used for blocking */
    var html = '<span class="track-move-widget" data-index="' + idx + '">';
    /* 2x2 quick-pick grid — always 4 buttons */
    html += '<span class="move-quick-grid">';
    for (var i = 0; i < Math.min(4, picks.length); i++) {
      var isCur = picks[i] === curFolder;
      html += '<button class="move-quick-btn' + (isCur ? ' is-current' : '') +
        '" data-target="' + escHtml(picks[i]) +
        '" data-index="' + idx + '" title="Verschieben nach: ' + escHtml(picks[i]) + '">' +
        escHtml(picks[i]) + '</button>';
    }
    html += '</span>';
    /* Dropdown with all folders */
    html += '<select class="move-folder-select" data-index="' + idx + '">';
    html += '<option value="" disabled' + (curFolder ? '' : ' selected') + '>Ordner w\u00e4hlen\u2026</option>';
    allF.forEach(function(f) {
      html += '<option value="' + escHtml(f) + '"' + (f === curFolder ? ' selected' : '') + '>' + escHtml(f) + '</option>';
    });
    html += '</select>';
    /* Delete button — last element, visually separated by left border */
    html += '<button class="move-delete-btn" data-index="' + idx + '" title="Datei in den Papierkorb verschieben">' +
      IC_TRASH + '</button>';
    html += '</span>';
    return html;
  }

  function moveFileToFolder(idx, targetFolder) {
    var t = filteredItems[idx];
    if (!t) return;
    var curFolder = _currentFolderOf(t);
    if (targetFolder === curFolder) { showToast('Datei ist bereits in diesem Ordner'); return; }
    /* Mark old path immediately so concurrent background fetches don't
       re-add the item at its old location before the server has rescanned. */
    _locallyDeletedPaths[t.relative_path] = true;
    fetch(MOVE_API_PATH, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: t.relative_path, target_folder: targetFolder })
    })
    .then(function(r) {
      if (!r.ok) return r.json().then(function(e) { throw new Error(e.detail || 'Move failed'); });
      return r.json();
    })
    .then(function(d) {
      if (!d || !d.ok) return;
      _saveRecentMoveTarget(targetFolder);
      /* Update allItems in-place */
      for (var i = 0; i < allItems.length; i++) {
        if (allItems[i].relative_path === t.relative_path) {
          allItems[i] = Object.assign({}, allItems[i], {
            relative_path: d.new_path,
            stream_url: allItems[i].stream_url.replace(encodeURIComponent(t.relative_path), encodeURIComponent(d.new_path)),
            artist: targetFolder
          });
          break;
        }
      }
      _invalidateDupeMap();
      _invalidateFolderCache();
      _saveCatalogCache(allItems);  /* keep localStorage in sync after rename */
      showToast('Verschoben nach ' + targetFolder);
      /* Fade item out, then re-render — no ghost needed since item is cleanly gone */
      var li = trackList.querySelector('[data-index="' + idx + '"]');
      if (li) {
        li.classList.add('track-item--removing');
        li.addEventListener('animationend', function() { applyFilter(); }, { once: true });
      } else {
        applyFilter();
      }
    })
    .catch(function(err) {
      delete _locallyDeletedPaths[t.relative_path];
      showToast('Fehler: ' + (err.message || 'Verschieben fehlgeschlagen'));
    });
  }

  /* ── Generic three-dot / kebab dropdown menu ─────────────────────────────
     Shared by every kebab menu in the UI (track rows, player bar, playlist
     cards, …) so they all look and behave identically — a single dropdown
     anchored to the triggering button, right-aligned to it.
     items: [{ icon, label, onClick, danger }] */
  var _ctxMenuCleanup = null;

  function _closeCtxMenu() {
    if (_ctxMenuCleanup) { _ctxMenuCleanup(); _ctxMenuCleanup = null; }
    var old = document.getElementById('ht-ctx-menu');
    if (old) old.remove();
  }

  function _openCtxMenu(btn, items) {
    _closeCtxMenu();
    var menu = document.createElement('div');
    menu.id = 'ht-ctx-menu';
    menu.className = 'ht-ctx-menu';
    menu.innerHTML = items.map(function(it, i) {
      return '<button class="ht-ctx-item' + (it.danger ? ' ht-ctx-item--danger' : '') + '" data-idx="' + i + '">' +
        (it.icon || '') + ' ' + escHtml(it.label) +
      '</button>';
    }).join('');
    document.body.appendChild(menu);
    /* Position: align right edge with button, just below (or above if no room) */
    var rect = btn.getBoundingClientRect();
    menu.style.right = Math.max(4, window.innerWidth - rect.right) + 'px';
    var spaceBelow = window.innerHeight - rect.bottom;
    if (spaceBelow >= menu.offsetHeight + 8) {
      menu.style.top = (rect.bottom + 4) + 'px';
    } else {
      menu.style.top = Math.max(4, rect.top - menu.offsetHeight - 4) + 'px';
    }
    menu.querySelectorAll('.ht-ctx-item').forEach(function(elBtn) {
      elBtn.addEventListener('click', function() {
        var idx = Number(elBtn.dataset.idx);
        _closeCtxMenu();
        if (items[idx] && typeof items[idx].onClick === 'function') items[idx].onClick();
      });
    });
    /* Close on outside click or Escape */
    function _onOutside(e) { if (!menu.contains(e.target) && e.target !== btn && !btn.contains(e.target)) _closeCtxMenu(); }
    function _onEsc(e) { if (e.key === 'Escape') _closeCtxMenu(); }
    setTimeout(function() {
      document.addEventListener('click', _onOutside);
      document.addEventListener('keydown', _onEsc);
    }, 0);
    _ctxMenuCleanup = function() {
      document.removeEventListener('click', _onOutside);
      document.removeEventListener('keydown', _onEsc);
    };
  }

  /* ── Track context menu (three-dot / kebab) ─────────────────────────────── */
  function _openTrackCtxMenu(btn, relativePath, title) {
    var IC_FOLDER_OPEN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>';
    _openCtxMenu(btn, [
      { icon: IC_FOLDER_OPEN, label: 'Im Explorer anzeigen', onClick: function() { _revealInExplorer(relativePath, title); } }
    ]);
  }

  function _revealInExplorer(relativePath, title) {
    fetch(REVEAL_API_PATH, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({path: relativePath})
    })
    .then(function(r) { return r.ok ? r.json() : null; })
    .then(function(d) {
      if (!d) { showToast('Pfad nicht gefunden'); return; }
      showToast(d.revealed ? 'Explorer ge\u00f6ffnet' : 'Pfad: ' + d.path);
    })
    .catch(function() { showToast('Fehler beim Anzeigen'); });
  }

  /* ── playback ── */
  /* Background playback for video — three layers of defence:
     ─────────────────────────────────────────────────────────
     PROBLEM: Mobile browsers (especially iOS Safari) pause <video>
     elements **before** the visibilitychange event fires.  So checking
     `!player.paused` inside that handler is already too late — the
     video is paused.  And `requestPictureInPicture()` requires a
     user-gesture, so calling it from visibilitychange is rejected.

     STRATEGY:
     1. **`wasPlaying` flag** — set on `playing` event, cleared only by
        intentional user-pause.  The browser's auto-pause does NOT
        clear it.  visibilitychange checks `wasPlaying` instead of
        `!player.paused`.
     2. **Hidden <audio> with `muted:true`** — plays the same source
        silently alongside the video.  Because it is already actively
        playing (started from user-gesture), iOS keeps it alive when
        backgrounded.  On visibilitychange we unmute it so audio
        continues seamlessly.
        NOTE: iOS ignores `volume` (always 1), so we MUST use `muted`
        to prevent double-audio in the foreground.
     3. **`autopictureinpicture` attribute** — Safari/WebKit honours
        this and enters PiP automatically when the page backgrounds.
        No user-gesture needed.  The manual PiP button works on all
        browsers that support the API. */
  var bgAudio = null;
  var bgSyncTimer = null;
  var isVideoPlayer = player.tagName === 'VIDEO';
  var isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
              (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var pipActive = false;
  var wasPlaying = false;
  var btnPip = document.getElementById('btn-pip');

  /* Track intentional playback state — survives browser auto-pause */
  player.addEventListener('playing', function() { wasPlaying = true; });

  /* Show PiP button only when the browser supports it for this player */
  var pipSupported = isVideoPlayer && (
    document.pictureInPictureEnabled ||
    (typeof player.webkitSupportsPresentationMode === 'function' &&
     player.webkitSupportsPresentationMode('picture-in-picture'))
  );
  /* On mobile / touch devices we do NOT show a dedicated PiP button — PiP works
     "like a classic browser" via the native video controls and the automatic
     `autopictureinpicture` transition when the page is backgrounded.  A custom
     button there is redundant and confusing. */
  var isTouchDevice = isIOS || (navigator.maxTouchPoints > 0 &&
    typeof window.matchMedia === 'function' && window.matchMedia('(pointer: coarse)').matches);
  if (pipSupported && btnPip && !isTouchDevice) btnPip.hidden = false;

  /* Enable Safari's automatic PiP on page background */
  if (isVideoPlayer) {
    player.setAttribute('autopictureinpicture', '');
  }

  function requestPiP() {
    if (!pipSupported || pipActive) return Promise.resolve();
    if (player.requestPictureInPicture) {
      return player.requestPictureInPicture().then(function() {
        pipActive = true;
        if (btnPip) btnPip.classList.add('active');
      }).catch(function() {});
    } else if (player.webkitSetPresentationMode) {
      player.webkitSetPresentationMode('picture-in-picture');
      pipActive = true;
      if (btnPip) btnPip.classList.add('active');
      return Promise.resolve();
    }
    return Promise.resolve();
  }

  function exitPiP() {
    if (!pipActive) return;
    if (document.exitPictureInPicture && document.pictureInPictureElement) {
      document.exitPictureInPicture().catch(function() {});
    } else if (player.webkitSetPresentationMode) {
      player.webkitSetPresentationMode('inline');
    }
    pipActive = false;
    if (btnPip) btnPip.classList.remove('active');
  }

  /* Track PiP state changes from native controls */
  if (isVideoPlayer) {
    player.addEventListener('enterpictureinpicture', function() {
      pipActive = true;
      if (btnPip) btnPip.classList.add('active');
    });
    player.addEventListener('leavepictureinpicture', function() {
      pipActive = false;
      if (btnPip) btnPip.classList.remove('active');
      /* If user closed PiP but wasPlaying, resume inline */
      if (wasPlaying && !document.hidden) {
        player.play().catch(function() {});
      }
    });
  }

  /* Manual PiP toggle button */
  if (btnPip) {
    btnPip.addEventListener('click', function() {
      if (pipActive) { exitPiP(); } else { requestPiP(); }
    });
  }

  /* Fullscreen button — uses native fullscreen or iOS webkitEnterFullscreen */
  var btnFs = document.getElementById('btn-fs');
  var fsSupported = isVideoPlayer && (
    document.fullscreenEnabled || document.webkitFullscreenEnabled ||
    typeof player.webkitEnterFullscreen === 'function'
  );
  if (fsSupported && btnFs) btnFs.hidden = false;
  if (btnFs) {
    btnFs.addEventListener('click', function() {
      if (player.requestFullscreen) {
        player.requestFullscreen().catch(function() {});
      } else if (player.webkitRequestFullscreen) {
        player.webkitRequestFullscreen();
      }
    });
  }

  function ensureBgAudio() {
    if (bgAudio) return bgAudio;
    bgAudio = document.createElement('audio');
    bgAudio.style.display = 'none';
    bgAudio.preload = 'auto';
    bgAudio.playsInline = true;
    bgAudio.muted = true;
    document.body.appendChild(bgAudio);
    /* When bg audio track ends, advance to next */
    bgAudio.addEventListener('ended', function() {
      playNextItem();
    });
    return bgAudio;
  }

  /* Is bg audio currently the active (unmuted) source? */
  function bgAudioIsActive() {
    return bgAudio && !bgAudio.muted && !bgAudio.paused;
  }

  /* Start the hidden <audio> muted, mirroring the video source.
     The play() call happens inside user-initiated playback so the
     browser allows it.  Because the element is already in a playing
     state, unmuting it later in visibilitychange works instantly. */
  function startBgMirror() {
    if (!isVideoPlayer) return;
    var bg = ensureBgAudio();
    if (bg.src !== player.src) {
      bg.src = player.src;
    }
    bg.currentTime = player.currentTime;
    bg.muted = true;
    bg.play().catch(function() {});
    /* keep bg audio roughly in sync while video plays */
    stopBgSync();
    bgSyncTimer = setInterval(function() {
      if (!bgAudio || !bgAudio.muted) return;
      if (!player.paused && Math.abs(bgAudio.currentTime - player.currentTime) > 0.5) {
        bgAudio.currentTime = player.currentTime;
      }
    }, 2000);
  }

  function stopBgSync() {
    if (bgSyncTimer) { clearInterval(bgSyncTimer); bgSyncTimer = null; }
  }

  /* ── Visibility change — the core background handler ──
     Uses `wasPlaying` instead of `!player.paused` because the browser
     has already paused the video by the time this fires on mobile. */
  document.addEventListener('visibilitychange', function() {
    if (!isVideoPlayer) return;
    if (document.hidden && wasPlaying) {
      /* Detect whether Safari has already pushed the video into system PiP
         via the `autopictureinpicture` attribute.  On iOS 17+ the transition
         starts BEFORE visibilitychange fires, so this check is reliable. */
      var inPiP = (document.pictureInPictureElement === player) ||
                  (player.webkitPresentationMode === 'picture-in-picture');
      /* Desktop browsers keep a *playing* <video> running when its tab is
         hidden (audio continues, only rendering is throttled).  So we do NOT
         pause it — the player simply keeps playing, as the user expects.
         iOS Safari suspends background <video>, so there we hand off to PiP
         or the muted bg-audio mirror instead.  Pausing only happened on
         desktop before and was the reason switching tabs "paused" playback. */
      if (isIOS && !inPiP && bgAudio && !bgAudio.paused) {
        bgAudio.currentTime = player.currentTime;
        bgAudio.muted = false;
      }
      /* Signal to OS that playback is ongoing */
      if ('mediaSession' in navigator) {
        navigator.mediaSession.playbackState = 'playing';
      }
    } else if (!document.hidden && wasPlaying) {
      /* App coming back to foreground */
      if (pipActive) exitPiP();
      if (bgAudio && !bgAudio.muted) {
        /* Sync video to where bg audio continued, resume video */
        player.currentTime = bgAudio.currentTime;
        player.play().catch(function() {});
        bgAudio.muted = true;
      } else if (player.paused) {
        /* No bg audio ran — just resume the video */
        player.play().catch(function() {});
      }
    }
  });

  /* Return whichever element is currently driving playback */
  function activeMedia() {
    if (bgAudioIsActive()) return bgAudio;
    return player;
  }

  /* Media Session API — lock screen controls & background playback signal */
  function updateMediaSession(t) {
    if (!('mediaSession' in navigator)) return;
    navigator.mediaSession.metadata = new MediaMetadata({
      title: t.title,
      artist: t.artist || '',
      album: ITEM_NOUN === 'video' ? 'hometools video' : 'hometools audio',
      artwork: [{ src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
                { src: '/icon-512.png', sizes: '512x512', type: 'image/png' }]
    });
    navigator.mediaSession.setActionHandler('play', function() {
      var m = activeMedia();
      m.play();
      wasPlaying = true;
    });
    navigator.mediaSession.setActionHandler('pause', function() {
      /* Lockscreen pause = intentional user pause */
      wasPlaying = false;
      var m = activeMedia();
      m.pause();
      if (bgAudio) { bgAudio.pause(); bgAudio.muted = true; }
    });
    navigator.mediaSession.setActionHandler('previoustrack', function() {
      playTrack(currentIndex > 0 ? currentIndex - 1 : filteredItems.length - 1);
    });
    navigator.mediaSession.setActionHandler('nexttrack', function() {
      playNextItem();
    });
    try {
      navigator.mediaSession.setActionHandler('seekto', function(details) {
        var m = activeMedia();
        m.currentTime = details.seekTime;
      });
    } catch(e) {}
  }

  function playItem(t, index) {
    currentIndex = typeof index === 'number' ? index : -1;
    currentStreamUrl = t.stream_url || '';
    _currentItemDuration = t.duration || 0;  /* catalog metadata duration — fallback before browser loads it */
    _setCurrentIntro(t);

    /* Sync shuffle queue position to the chosen index */
    if (shuffleMode && shuffleQueue.length && currentIndex >= 0) {
      var qpos = shuffleQueue.indexOf(currentIndex);
      if (qpos >= 0) shufflePos = qpos;
      else { shuffleQueue.unshift(currentIndex); shufflePos = 0; }
    }

    /* Reset bg audio for new track */
    stopBgSync();
    if (bgAudio) { bgAudio.pause(); bgAudio.muted = true; bgAudio.removeAttribute('src'); }
    _xfadeCleanup();
    player.volume = 1;
    wasPlaying = false;
    revokeOfflineUrl();

    function onPlaySuccess() {
      btnPlay.innerHTML = IC_PAUSE;
      startBgMirror();
    }

    function retryAfterCanPlay() {
      player.addEventListener('canplay', function() {
        player.play().then(onPlaySuccess).catch(function(e) {
          console.error('playTrack retry also failed:', e);
          btnPlay.innerHTML = IC_PLAY;
        });
      }, { once: true });
    }

    function beginPlayback(playback) {
      player.src = playback.url;
      player.load();
      player.play().then(onPlaySuccess).catch(function(err) {
        if (playback.offline) {
          console.warn('Offline playback failed, falling back to stream:', err);
          revokeOfflineUrl();
          player.src = playback.fallbackUrl;
          player.load();
          player.play().then(onPlaySuccess).catch(function(fallbackErr) {
            console.warn('Stream fallback play() failed, waiting for canplay:', fallbackErr);
            retryAfterCanPlay();
          });
          return;
        }
        console.warn('playTrack play() failed, waiting for canplay:', err);
        retryAfterCanPlay();
      });
      generateWaveform(playback.url, t.relative_path);
    }

    playerTitle.textContent = t.title;
    playerArtist.textContent = t.artist || t.relative_path;
    if (t.thumbnail_url) {
      playerThumb.src = t.thumbnail_lg_url || t.thumbnail_url;
      playerThumb.style.display = '';
    } else {
      playerThumb.src = FILE_PLACEHOLDER;
      playerThumb.style.display = '';
    }
    btnPlay.innerHTML = IC_PAUSE;
    playerBar.classList.remove('view-hidden');
    /* In video mode: open the overlay and sync the mini-bar title/thumb */
    if (isVideoMode) {
      openVideoOverlay();
      _syncMiniBar(t);
      if (videoOverlayTitleText) videoOverlayTitleText.textContent = t.title || '';
    }
    /* Show video player element before playback starts — the CSS sets
       #player { display:none }, so we must override with inline block */
    if (player.tagName === 'VIDEO') player.style.display = 'block';
    markActive();
    updateMediaSession(t);
    renderPlayerRating(t.rating || 0);
    updatePlayerBarActions();
    refreshMetadata(t);
    /* Auto-update lyrics panel if currently open */
    if (LYRICS_ENABLED && _lyricsOpen) openLyricsPanel(t.relative_path || '', t.title);

    /* playback progress: track current item and try to resume */
    saveProgressNow();   /* flush the outgoing track's position before switching */
    clearTimeout(_progressTimer);
    _progressRelPath = t.relative_path || '';
    /* Also persist to localStorage so the episode can be restored after a
       server restart or page reload — even if < 5 s have elapsed (which
       saveProgressNow would otherwise skip). */
    _saveLastPlayedLocal(_progressRelPath, 0);
    if (AUTO_RESUME_ENABLED) loadAndSeekProgress(_progressRelPath);

    /* load sprite sheet for video scrubber preview */
    loadSpriteData(t.relative_path || '');

    playOfflineOrStream(t.stream_url)
      .then(beginPlayback)
      .catch(function() {
        beginPlayback({ url: t.stream_url, offline: false, fallbackUrl: t.stream_url });
      });
    if (typeof _router !== 'undefined') _router.update();
  }

  function playTrack(index) {
    if (index < 0 || index >= filteredItems.length) return;
    playItem(filteredItems[index], index);
  }

  function refreshMetadata(t) {
    var base = API_PATH.substring(0, API_PATH.lastIndexOf('/'));
    var metaUrl = base + '/metadata?path=' + encodeURIComponent(t.relative_path);
    var _requestedFor = t.relative_path;
    fetch(metaUrl)
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(meta) {
        if (!meta) return;
        /* Guard against a stale/late response overwriting the title/artist
           of a track that has since been superseded by a newer playItem()
           call (e.g. rapid track switching or a fast list reload while
           Tools mode is active). Without this guard the UI can briefly show
           a swapped/mismatched title+artist pair. */
        if (_progressRelPath !== _requestedFor) return;
        var changed = false;
        if (meta.title && meta.title !== t.title) {
          t.title = meta.title;
          playerTitle.textContent = meta.title;
          changed = true;
        }
        if (meta.artist && meta.artist !== t.artist) {
          t.artist = meta.artist;
          playerArtist.textContent = meta.artist;
          changed = true;
        }
        if (typeof meta.rating === 'number') {
          t.rating = meta.rating;
          renderPlayerRating(meta.rating);
        }
        if (changed) {
          updateMediaSession(t);
          applyFilter();
          markActive();
        }
      })
      .catch(function() {});
  }

  function togglePlay() {
    if (currentIndex < 0 && filteredItems.length) { playTrack(0); return; }
    if (player.paused) {
      /* If bg audio was driving playback (came back from background), sync first */
      if (bgAudio && !bgAudio.muted) {
        player.currentTime = bgAudio.currentTime;
        bgAudio.muted = true;
      }
      player.play().then(function() { startBgMirror(); }).catch(function() {});
      btnPlay.innerHTML = IC_PAUSE;
    } else {
      /* Intentional user pause — clear wasPlaying */
      wasPlaying = false;
      player.pause();
      if (bgAudio) { bgAudio.pause(); bgAudio.muted = true; }
      stopBgSync();
      btnPlay.innerHTML = IC_PLAY;
    }
  }

  /* ── Shuffle logic ── */
  /* Fisher-Yates shuffle of an array in place */
  function fisherYates(arr) {
    for (var i = arr.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
    }
    return arr;
  }

  /* Build a weighted shuffle queue: items with higher rating appear more often.
     Rating 0 → weight 1, Rating 5 → weight 6. Items with no rating → weight 1. */
  function buildWeightedQueue(items) {
    var pool = [];
    items.forEach(function(t, idx) {
      var w = Math.max(1, Math.round((t.rating || 0) + 1));
      for (var i = 0; i < w; i++) pool.push(idx);
    });
    return fisherYates(pool);
  }

  /* Build a simple uniform shuffle queue */
  function buildNormalQueue(items) {
    var indices = items.map(function(_, i) { return i; });
    return fisherYates(indices);
  }

  /* Rebuild shuffle queue — called whenever filteredItems or shuffleMode changes */
  function rebuildShuffleQueue(startIndex) {
    if (!shuffleMode || !filteredItems.length) { shuffleQueue = []; shufflePos = -1; return; }
    var rawQueue = shuffleMode === 'weighted'
      ? buildWeightedQueue(filteredItems)
      : buildNormalQueue(filteredItems);
    shuffleQueue = rawQueue; /* already filteredItems indices */
    /* Put startIndex first so current track leads */
    if (typeof startIndex === 'number' && startIndex >= 0) {
      var pos = shuffleQueue.indexOf(startIndex);
      if (pos > 0) {
        shuffleQueue.splice(pos, 1);
        shuffleQueue.unshift(startIndex);
      }
    }
    shufflePos = 0;
  }

  /* Next index respecting shuffle state */
  function nextIndex() {
    if (shuffleMode && shuffleQueue.length) {
      shufflePos = (shufflePos + 1) % shuffleQueue.length;
      /* Replenish weighted queue when exhausted */
      if (shufflePos === 0 && shuffleMode === 'weighted') {
        shuffleQueue = buildWeightedQueue(filteredItems);
      }
      return shuffleQueue[shufflePos];
    }
    /* Sequential */
    var ni = currentIndex + 1;
    if (ni >= filteredItems.length) return repeatMode === 'all' ? 0 : -1;
    return ni;
  }

  /* First playable index — kept for API compat, returns 0 */
  function _firstPlayableIndex() { return 0; }

  /* Prev index respecting shuffle state */
  function prevIndex() {
    if (shuffleMode && shuffleQueue.length) {
      shufflePos = (shufflePos - 1 + shuffleQueue.length) % shuffleQueue.length;
      return shuffleQueue[shufflePos];
    }
    /* Sequential */
    var pi = currentIndex - 1;
    if (pi < 0) {
      if (repeatMode === 'all') return filteredItems.length - 1;
      return 0;
    }
    return pi;
  }

  /* Toggle shuffle mode: off → normal → weighted → off */
  function cycleShuffle() {
    if (!shuffleMode) {
      shuffleMode = 'normal';
    } else if (shuffleMode === 'normal') {
      shuffleMode = 'weighted';
    } else {
      shuffleMode = false;
    }
    localStorage.setItem('ht-shuffle-mode', shuffleMode || '');
    updateShuffleBtn();
    rebuildShuffleQueue(currentIndex >= 0 ? currentIndex : 0);
  }

  /* Activate weighted shuffle directly (long-press) */
  function activateWeightedShuffle() {
    shuffleMode = 'weighted';
    localStorage.setItem('ht-shuffle-mode', 'weighted');
    updateShuffleBtn();
    rebuildShuffleQueue(currentIndex >= 0 ? currentIndex : 0);
    showToast('Gewichteter Shuffle aktiv (nach Bewertung)');
  }

  function updateShuffleBtn() {
    if (!btnShuffle) return;
    btnShuffle.classList.toggle('shuffle-active', !!shuffleMode);
    btnShuffle.classList.toggle('shuffle-weighted', shuffleMode === 'weighted');
    btnShuffle.title = shuffleMode === 'weighted'
      ? 'Shuffle (gewichtet nach Bewertung) — Long Press für Aus'
      : shuffleMode === 'normal'
        ? 'Shuffle (zufällig) — Klick für gewichtet, Long Press für Aus'
        : 'Shuffle aktivieren';
  }

  /* ── Repeat mode: off → all → one → off ── */
  function cycleRepeat() {
    if (!repeatMode) {
      repeatMode = 'all';
    } else if (repeatMode === 'all') {
      repeatMode = 'one';
    } else {
      repeatMode = false;
    }
    localStorage.setItem('ht-repeat-mode', repeatMode || '');
    updateRepeatBtn();
  }

  function updateRepeatBtn() {
    if (!btnRepeat) return;
    btnRepeat.classList.toggle('repeat-active', !!repeatMode);
    btnRepeat.classList.toggle('repeat-one', repeatMode === 'one');
    btnRepeat.innerHTML = repeatMode === 'one' ? IC_REPEAT_ONE : IC_REPEAT;
    btnRepeat.title = repeatMode === 'one'
      ? 'Einzeltitel wiederholen — Klick für Aus'
      : repeatMode === 'all'
        ? 'Alle wiederholen — Klick für Einzeltitel'
        : 'Wiederholen aktivieren';
  }

  /* ── Rating stars (audio-only write, display-only for video) ── */
  var playerRatingEl = document.getElementById('player-rating');

  function renderPlayerRating(stars) {
    if (!playerRatingEl) return;
    var rounded = Math.round(stars || 0);
    playerRatingEl.innerHTML = '';
    for (var i = 1; i <= 5; i++) {
      var btn = document.createElement('button');
      btn.className = 'player-rating-star' + (i <= rounded ? ' active' : '');
      btn.innerHTML = i <= rounded ? IC_STAR_FILLED : IC_STAR_EMPTY;
      btn.dataset.star = i;
      /* Tooltip: clicking the currently-set star will clear the rating (toggle to 0) */
      btn.title = (i === rounded && rounded > 0)
        ? 'Bewertung entfernen (nochmals klicken)'
        : i + (i === 1 ? ' Stern' : ' Sterne');
      if (!RATING_WRITE_ENABLED) btn.style.pointerEvents = 'none';
      playerRatingEl.appendChild(btn);
    }
    playerRatingEl.removeAttribute('hidden');
  }

  /* Patch the matching entry in allItems by relative_path.
     Uses Object.assign to avoid mutating the frozen data pattern used elsewhere. */
  function _patchAllItemsRating(relativePath, rating) {
    for (var i = 0; i < allItems.length; i++) {
      if (allItems[i].relative_path === relativePath) {
        allItems[i] = Object.assign({}, allItems[i], { rating: rating });
        break;
      }
    }
  }

  /* Update the .rating-bar inside a track list item without a full re-render.
     Also refreshes inline rating stars for the same index when present. */
  function _updateTrackRatingBar(idx, rating) {
    var li = document.querySelector('.track-item[data-index="' + idx + '"]');
    if (!li) return;
    var wrap = li.querySelector('.track-thumb-wrap');
    if (wrap) {
      var bar = wrap.querySelector('.rating-bar');
      if (rating > 0) {
        if (!bar) {
          bar = document.createElement('div');
          bar.className = 'rating-bar';
          wrap.appendChild(bar);
        }
        bar.style.width = (rating / 5 * 100) + '%';
      } else if (bar) {
        bar.remove();
      }
    }
    /* Inline rating stars (if visible) */
    var container = li.querySelector('.track-inline-rating');
    if (container) {
      var rounded = Math.round(rating || 0);
      container.querySelectorAll('.track-inline-rating-star').forEach(function(b) {
        var s = Number(b.dataset.star);
        b.className = 'track-inline-rating-star' + (s <= rounded ? ' active' : '');
        b.innerHTML = s <= rounded ? IC_STAR_FILLED : IC_STAR_EMPTY;
      });
    }
  }

  function setRating(stars) {
    if (!RATING_WRITE_ENABLED) return;
    var t = filteredItems[currentIndex];
    if (!t) return;
    var prevRating = t.rating || 0;
    fetch(RATING_API_PATH, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: t.relative_path, rating: stars })
    })
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(d) {
        if (!d || !d.ok) return;
        /* Check visibility change before patching (was grayed out, now above threshold or vice versa) */
        var wasHidden = !!t._hiddenShown;
        t.rating = d.rating;
        /* Keep allItems in sync so any re-render shows the correct rating bar */
        _patchAllItemsRating(t.relative_path, d.rating);
        var nowHidden = _effectiveThreshold > 0 && d.rating > 0 && d.rating < _effectiveThreshold;
        if (wasHidden !== nowHidden && inPlaylist) {
          /* Visibility changed — full re-render to remove or apply gray state */
          applyFilter();
        } else {
          renderPlayerRating(d.rating);
          /* Sync the track list item (rating-bar + inline stars) without re-render */
          _updateTrackRatingBar(currentIndex, d.rating);
        }
        /* rebuild weighted shuffle queue so new rating is reflected immediately */
        if (shuffleMode === 'weighted') rebuildShuffleQueue(currentIndex);
        /* show toast with undo option if entry_id was returned */
        var toastLabel = stars === 0
          ? 'Bewertung entfernt'
          : stars + (stars === 1 ? ' Stern' : ' Sterne') + ' vergeben';
        if (d.entry_id) {
          showRatingToastWithUndo(stars, prevRating, d.entry_id, t);
        } else {
          showToast(toastLabel);
        }
      })
      .catch(function() {});
  }

  function showRatingToastWithUndo(stars, prevStars, entryId, t) {
    var toast = document.getElementById('toast');
    var label = stars === 0
      ? 'Bewertung entfernt'
      : stars + (stars === 1 ? ' Stern' : ' Sterne') + ' vergeben';
    if (!toast) { showToast(label); return; }
    /* build toast via DOM — avoids quote-escaping in onclick attribute */
    toast.innerHTML = '';
    var span = document.createElement('span');
    span.textContent = label;
    toast.appendChild(span);
    var undoBtn = document.createElement('button');
    undoBtn.textContent = 'Rueckgaengig';
    undoBtn.style.cssText = 'margin-left:0.5rem;background:none;border:1px solid #888;'
      + 'color:inherit;border-radius:4px;padding:1px 8px;cursor:pointer;font-size:0.8rem;';
    undoBtn.addEventListener('click', function() { undoRating(undoBtn, entryId, prevStars); });
    toast.appendChild(undoBtn);
    toast.classList.add('show');
    clearTimeout(toast._hideTimer);
    toast._hideTimer = setTimeout(function() { toast.classList.remove('show'); }, 5000);
  }

  function undoRating(btn, entryId, prevStars) {
    btn.disabled = true; btn.textContent = '…';
    fetch(AUDIT_UNDO_PATH, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entry_id: entryId })
    })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        var t2 = filteredItems[currentIndex];
        if (d.ok && t2) {
          t2.rating = prevStars;
          _patchAllItemsRating(t2.relative_path, prevStars);
          renderPlayerRating(prevStars);
          _updateTrackRatingBar(currentIndex, prevStars);
          if (shuffleMode === 'weighted') rebuildShuffleQueue(currentIndex);
        }
        var toast = document.getElementById('toast');
        if (toast) {
          toast.innerHTML = d.ok ? 'Rückgängig gemacht ✓' : ('Fehler: ' + (d.detail || '?'));
          clearTimeout(toast._hideTimer);
          toast._hideTimer = setTimeout(function() { toast.classList.remove('show'); }, 2500);
        }
      })
      .catch(function() { showToast('Netzwerkfehler beim Rückgängig'); });
  }

  if (playerRatingEl) {
    /* hover preview */
    playerRatingEl.addEventListener('mouseover', function(e) {
      var btn = e.target.closest('.player-rating-star');
      if (!btn || !RATING_WRITE_ENABLED) return;
      var n = parseInt(btn.dataset.star, 10);
      playerRatingEl.querySelectorAll('.player-rating-star').forEach(function(b, i) {
        b.classList.toggle('hover', i < n);
      });
    });
    playerRatingEl.addEventListener('mouseleave', function() {
      playerRatingEl.querySelectorAll('.player-rating-star').forEach(function(b) {
        b.classList.remove('hover');
      });
    });
    /* click to rate — clicking the currently-set star clears the rating (toggle to 0) */
    playerRatingEl.addEventListener('click', function(e) {
      var btn = e.target.closest('.player-rating-star');
      if (!btn || !RATING_WRITE_ENABLED) return;
      var clicked = parseInt(btn.dataset.star, 10);
      var current = Math.round((filteredItems[currentIndex] && filteredItems[currentIndex].rating) || 0);
      setRating(clicked === current ? 0 : clicked);
    });
  }


  if (SHUFFLE_ENABLED) {
    var _savedShuffle = localStorage.getItem('ht-shuffle-mode');
    if (_savedShuffle === 'normal' || _savedShuffle === 'weighted') {
      shuffleMode = _savedShuffle;
    }
    updateShuffleBtn();
  }

  btnPlay.addEventListener('click', togglePlay);
  btnPrev.addEventListener('click', function() { playTrack(prevIndex()); });
  btnNext.addEventListener('click', playNextItem);
  /* Album cover click → jump to current track in list */
  if (playerThumb) playerThumb.addEventListener('click', jumpToCurrentTrack);

  /* ── Shuffle button: click = cycle modes, long-press (600 ms) = weighted ── */
  if (SHUFFLE_ENABLED && btnShuffle) {
    var _shuffleLongPressed = false;
    var _shuffleLongPressTimer = null;
    function _startShuffleLongPress() {
      _shuffleLongPressed = false;
      _shuffleLongPressTimer = setTimeout(function() {
        _shuffleLongPressed = true;
        activateWeightedShuffle();
      }, 600);
    }
    function _cancelShuffleLongPress() { clearTimeout(_shuffleLongPressTimer); }
    btnShuffle.addEventListener('mousedown', _startShuffleLongPress);
    btnShuffle.addEventListener('mouseup', _cancelShuffleLongPress);
    btnShuffle.addEventListener('mouseleave', _cancelShuffleLongPress);
    btnShuffle.addEventListener('touchstart', function(e) {
      e.preventDefault();
      _startShuffleLongPress();
    }, { passive: false });
    btnShuffle.addEventListener('touchend', _cancelShuffleLongPress);
    btnShuffle.addEventListener('touchcancel', _cancelShuffleLongPress);
    btnShuffle.addEventListener('click', function() {
      if (!_shuffleLongPressed) cycleShuffle();
      _shuffleLongPressed = false;
    });
  }

  /* ── Repeat button: click = cycle modes (off → all → one → off) ── */
  if (REPEAT_ENABLED) {
    var _savedRepeat = localStorage.getItem('ht-repeat-mode');
    if (_savedRepeat === 'all' || _savedRepeat === 'one') {
      repeatMode = _savedRepeat;
    }
    updateRepeatBtn();
  }
  if (REPEAT_ENABLED && btnRepeat) {
    btnRepeat.addEventListener('click', cycleRepeat);
  }

  /* ── Crossfade (audio only) ── */
  var _xfadeAudio = null;   /* second <audio> element for crossfade target */
  var _xfading = false;     /* true while a crossfade is in progress */
  var _xfadeTimer = null;   /* setInterval for volume ramp */
  var _xfadeNextItem = null;/* the item being crossfaded into */
  var _xfadeNextIndex = -1; /* filteredItems index of the crossfade target */

  function _xfadeCleanup() {
    if (_xfadeTimer) { clearInterval(_xfadeTimer); _xfadeTimer = null; }
    if (_xfadeAudio) { _xfadeAudio.pause(); _xfadeAudio.removeAttribute('src'); }
    _xfading = false;
    _xfadeNextItem = null;
    _xfadeNextIndex = -1;
  }

  function _resolveNextForCrossfade() {
    /* Determine the next item WITHOUT consuming queue or advancing state */
    if (_userQueue.length > 0) {
      return { item: _userQueue[0], index: -1, fromQueue: true };
    }
    if (!filteredItems.length) return null;
    var ni = nextIndex();
    if (ni < 0 || ni >= filteredItems.length) return null;
    return { item: filteredItems[ni], index: ni, fromQueue: false };
  }

  function _startCrossfade() {
    if (_xfading) return;
    var next = _resolveNextForCrossfade();
    if (!next || !next.item || !next.item.stream_url) return;
    _xfading = true;
    _xfadeNextItem = next.item;
    _xfadeNextIndex = next.index;

    /* Create or reuse the xfade audio element */
    if (!_xfadeAudio) {
      _xfadeAudio = document.createElement('audio');
      _xfadeAudio.style.display = 'none';
      _xfadeAudio.preload = 'auto';
      document.body.appendChild(_xfadeAudio);
    }
    _xfadeAudio.volume = 0;
    _xfadeAudio.src = next.item.stream_url;
    _xfadeAudio.load();
    _xfadeAudio.play().catch(function() { _xfadeCleanup(); });

    /* Ramp volumes: fade out current, fade in next */
    var steps = 20; /* 50ms intervals over CROSSFADE_DURATION */
    var interval = (CROSSFADE_DURATION * 1000) / steps;
    var step = 0;
    _xfadeTimer = setInterval(function() {
      step++;
      var progress = Math.min(step / steps, 1);
      /* Ease curve: sine ease-in-out */
      var ease = 0.5 - 0.5 * Math.cos(Math.PI * progress);
      player.volume = Math.max(0, 1 - ease);
      _xfadeAudio.volume = Math.min(1, ease);
      if (step >= steps) {
        clearInterval(_xfadeTimer);
        _xfadeTimer = null;
        _finishCrossfade();
      }
    }, interval);
  }

  function _finishCrossfade() {
    if (!_xfadeNextItem) { _xfadeCleanup(); return; }
    /* Save progress for the outgoing track */
    saveProgressNow();
    clearProgressFor(_progressRelPath);

    /* Advance the actual playback state */
    var nextItem = _xfadeNextItem;
    var fromQueue = _xfadeNextIndex === -1 && _userQueue.length > 0;

    /* Stop the xfade audio — main player takes over */
    var xfSrc = _xfadeAudio.src;
    var xfTime = _xfadeAudio.currentTime;
    _xfadeAudio.pause();

    _xfading = false;
    _xfadeNextItem = null;

    if (fromQueue) {
      /* Consume from queue */
      playFromQueue(0);
    } else {
      playTrack(_xfadeNextIndex >= 0 ? _xfadeNextIndex : nextIndex());
    }
    _xfadeNextIndex = -1;

    /* Restore volume to 1 for the main player */
    player.volume = 1;
  }

  player.addEventListener('ended', function() {
    /* Guard against spurious 'ended' events: some browsers (and stream/network
       errors after a connection loss) fire 'ended' even though playback did NOT
       reach the end.  Auto-advancing then would jump to the next item — with
       repeat-all this wraps to the first episode (S01E01).  Only treat it as a
       real completion when we are actually near the end of the media. */
    var dur = player.duration;
    var pos = player.currentTime;
    var reachedEnd = !isFinite(dur) || dur <= 0 || pos >= dur - 1.5;
    if (!reachedEnd) {
      /* Likely a stall/stream error, not a real end — keep position, don't advance. */
      saveProgressNow();
      btnPlay.innerHTML = IC_PLAY;
      return;
    }
    clearProgressFor(_progressRelPath);
    if (_xfading) {
      /* Crossfade already handled transition — just finish it */
      _finishCrossfade();
      return;
    }
    playNextItem();
  });
  /* ── Player error: detect missing/gone files (404) ──────────────────────
     MEDIA_ERR_NETWORK (2) fires when the browser gets a 4xx/5xx on the
     stream URL.  We do a quick HEAD to confirm it is a 404 before removing
     the item from the list — this avoids wrongly deleting items on a
     transient Wi-Fi drop. */
  player.addEventListener('error', function() {
    var err = player.error;
    if (!err) { btnPlay.innerHTML = IC_PLAY; return; }
    /* MEDIA_ERR_ABORTED (1) = user-initiated stop, ignore */
    if (err.code === 1) return;
    var checkUrl = currentStreamUrl || player.currentSrc || '';
    var rp = _progressRelPath;
    if (err.code === 2 && checkUrl && rp) {
      /* Network error — confirm with HEAD before removing */
      fetch(checkUrl, { method: 'HEAD', cache: 'no-store' })
        .then(function(r) {
          if (r.status === 404) {
            _removeGoneTrack(rp);
          } else {
            showToast('Wiedergabe fehlgeschlagen');
            btnPlay.innerHTML = IC_PLAY;
          }
        })
        .catch(function() {
          /* Offline or CORS blocked — don't remove, might be transient */
          showToast('Verbindungsfehler');
          btnPlay.innerHTML = IC_PLAY;
        });
    } else {
      /* MEDIA_ERR_DECODE (3) or MEDIA_ERR_SRC_NOT_SUPPORTED (4) */
      showToast('Wiedergabe fehlgeschlagen');
      btnPlay.innerHTML = IC_PLAY;
    }
  });
  player.addEventListener('pause', function() {
    /* Don't change state when the browser auto-paused for background,
       or when bg audio has taken over playback */
    if (document.hidden) return;
    if (bgAudioIsActive()) return;
    /* User-initiated pause (custom button OR native controls) */
    wasPlaying = false;
    if (_xfading) { _xfadeCleanup(); player.volume = 1; }
    if (bgAudio) { bgAudio.pause(); bgAudio.muted = true; }
    stopBgSync();
    if (!player.ended) btnPlay.innerHTML = IC_PLAY;
    saveProgressNow();
    /* Show controls on pause so user can interact */
    if (isVideoMode) _showVidControls();
  });
  player.addEventListener('play',  function() {
    btnPlay.innerHTML = IC_PAUSE;
    /* Schedule auto-hide when playback resumes */
    if (isVideoMode) _showVidControls();
  });
  player.addEventListener('timeupdate', function() {
    var dur = isFinite(player.duration) ? player.duration : _currentItemDuration;
    if (!dur) return;
    progressBar.max = dur; progressBar.value = player.currentTime;
    timeCur.textContent = fmtTime(player.currentTime);
    if (isFinite(player.duration)) {
      drawWaveform(player.currentTime / player.duration);
    } else if (_currentItemDuration) {
      drawWaveform(player.currentTime / _currentItemDuration);
    }
    saveProgressDebounced();
    _updateSkipIntroBtn();
    /* Crossfade trigger: start fading when remaining time <= CROSSFADE_DURATION
       Skip crossfade for repeat-one (track restarts itself) */
    if (CROSSFADE_DURATION > 0 && !_xfading && !isVideoPlayer && repeatMode !== 'one') {
      var remaining = player.duration - player.currentTime;
      if (remaining > 0 && remaining <= CROSSFADE_DURATION && player.duration > CROSSFADE_DURATION + 5) {
        _startCrossfade();
      }
    }
  });
  player.addEventListener('loadedmetadata', function() {
    if (isFinite(player.duration)) _currentItemDuration = player.duration;
    timeDur.textContent = fmtTime(isFinite(player.duration) ? player.duration : _currentItemDuration);
    progressBar.max = isFinite(player.duration) ? player.duration : _currentItemDuration;
  });
  progressBar.addEventListener('input', function() { player.currentTime = progressBar.value; });

  /* ── Tap / drag-to-seek on the whole progress track ──
     The hidden range input has a 1px thumb, which on touch devices (iOS Safari)
     is impossible to grab — tapping the track does not jump there either.  This
     pointer handler makes the *entire* track tappable and draggable on mouse,
     touch and pen, so seeking works on mobile again. */
  (function initTrackSeek() {
    if (!progressTrack) return;
    var seeking = false;
    function effDuration() {
      if (bgAudio && !bgAudio.muted && document.hidden && isFinite(bgAudio.duration)) return bgAudio.duration;
      if (isFinite(player.duration)) return player.duration;
      /* Fallback: use catalog metadata duration while the browser has not yet
         determined the real duration (common with long files / non-seekable streams) */
      return _currentItemDuration || 0;
    }
    function seekToClientX(clientX) {
      var d = effDuration();
      if (!d) return;
      var rect = progressTrack.getBoundingClientRect();
      if (!rect.width) return;
      var frac = (clientX - rect.left) / rect.width;
      frac = Math.max(0, Math.min(1, frac));
      var t = frac * d;
      try { player.currentTime = t; } catch (e) {}
      if (bgAudio) { try { bgAudio.currentTime = t; } catch (e) {} }
      if (progressBar) { progressBar.max = d; progressBar.value = t; }
      if (timeCur) timeCur.textContent = fmtTime(t);
      drawWaveform(frac);
    }
    progressTrack.addEventListener('pointerdown', function(e) {
      if (e.button != null && e.button !== 0) return;
      seeking = true;
      try { progressTrack.setPointerCapture(e.pointerId); } catch (err) {}
      seekToClientX(e.clientX);
      e.preventDefault();
    });
    progressTrack.addEventListener('pointermove', function(e) {
      if (!seeking) return;
      seekToClientX(e.clientX);
      e.preventDefault();
    });
    function endSeek(e) {
      if (!seeking) return;
      seeking = false;
      try { progressTrack.releasePointerCapture(e.pointerId); } catch (err) {}
      saveProgressNow();
    }
    progressTrack.addEventListener('pointerup', endSeek);
    progressTrack.addEventListener('pointercancel', endSeek);
  })();

  /* Flush playback progress immediately when the page is hidden or unloaded.
     The 5s debounce would otherwise be lost when the app is backgrounded or
     closed on mobile, making the server-side "Continue watching" list lag
     behind by several episodes. */
  function _flushProgress() {
    clearTimeout(_progressTimer);
    saveProgressNow();
  }
  document.addEventListener('visibilitychange', function() {
    if (document.hidden) _flushProgress();
  });
  window.addEventListener('pagehide', _flushProgress);

  /* bg audio events — keep UI in sync when playing in background */
  if (isVideoPlayer) {
    setInterval(function() {
      if (bgAudio && !bgAudio.muted && document.hidden) {
        if (isFinite(bgAudio.duration)) {
          progressBar.max = bgAudio.duration;
          progressBar.value = bgAudio.currentTime;
          timeCur.textContent = fmtTime(bgAudio.currentTime);
          drawWaveform(bgAudio.currentTime / bgAudio.duration);
        }
      }
    }, 1000);
  }

  backBtn.addEventListener('click', goBack);
  playAllBtn.addEventListener('click', playAllCurrent);

  /* Logo-Icon click → always navigate back to root */
  logoHomeBtn.addEventListener('click', function() {
    currentPath = '';
    showFolderView();
  });

  /* Show video player element when something starts playing */
  if (isVideoPlayer) {
    player.addEventListener('loadeddata', function() {
      player.style.display = 'block';
    });
  }

  /* ── Favoriten — speichern & teilen ── */
  var _savedFavorites = {};

  function loadFavorites() {
    var base = API_PATH.substring(0, API_PATH.lastIndexOf('/'));
    fetch(base + '/shortcuts')
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(data) {
        _savedFavorites = {};
        if (data && Array.isArray(data.items)) {
          data.items.forEach(function(s) { _savedFavorites[s.id] = true; });
        }
        updateFavoriteButtons();
        /* If favorites filter is active, re-apply so newly loaded state is reflected */
        if (filterFav && inPlaylist) applyFilter();
      })
      .catch(function() {});
  }

  function updateFavoriteButtons() {
    document.querySelectorAll('.track-pin-btn').forEach(function(btn) {
      var rp = btn.dataset.relativePath;
      if (_savedFavorites[rp]) {
        btn.classList.add('pinned');
        btn.title = 'Favorit entfernen';
      } else {
        btn.classList.remove('pinned');
        btn.title = 'Favorit';
      }
    });
  }

  /* ── metadata edit modal ── */
  var _editModalRating = 0; /* selected rating inside the edit modal */

  function renderEditModalRating(stars) {
    var container = document.getElementById('edit-modal-rating');
    if (!container) return;
    var rounded = Math.round(stars || 0);
    _editModalRating = rounded;
    container.innerHTML = '';
    for (var i = 1; i <= 5; i++) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'edit-modal-rating-star' + (i <= rounded ? ' active' : '');
      btn.innerHTML = i <= rounded ? IC_STAR_FILLED : IC_STAR_EMPTY;
      btn.dataset.star = String(i);
      btn.title = i + (i === 1 ? ' Stern' : ' Sterne');
      container.appendChild(btn);
    }
  }

  (function _initEditModalRatingEvents() {
    var container = document.getElementById('edit-modal-rating');
    if (!container) return;
    container.addEventListener('mouseover', function(e) {
      var btn = e.target.closest('.edit-modal-rating-star');
      if (!btn) return;
      var n = parseInt(btn.dataset.star, 10);
      container.querySelectorAll('.edit-modal-rating-star').forEach(function(b, i) {
        b.classList.toggle('hover', i < n);
      });
    });
    container.addEventListener('mouseleave', function() {
      container.querySelectorAll('.edit-modal-rating-star').forEach(function(b) {
        b.classList.remove('hover');
      });
    });
    container.addEventListener('click', function(e) {
      var btn = e.target.closest('.edit-modal-rating-star');
      if (!btn) return;
      var n = parseInt(btn.dataset.star, 10);
      /* Toggle off if clicking the same star */
      renderEditModalRating(n === _editModalRating ? 0 : n);
    });
  })();

  function openEditModal(idx) {
    if (!METADATA_EDIT_ENABLED) return;
    var t = filteredItems[idx];
    if (!t) return;
    var backdrop = document.getElementById('edit-modal-backdrop');
    if (!backdrop) return;
    document.getElementById('edit-modal-title-input').value = t.title || '';
    document.getElementById('edit-modal-artist-input').value = t.artist || '';
    document.getElementById('edit-modal-album-input').value = '';
    document.getElementById('edit-modal-path').value = t.relative_path || '';
    document.getElementById('edit-modal-idx').value = String(idx);
    /* Rating stars — only if rating write is enabled */
    var ratingField = document.getElementById('edit-modal-rating-field');
    if (RATING_WRITE_ENABLED) {
      if (ratingField) ratingField.style.display = '';
      renderEditModalRating(t.rating || 0);
    } else {
      if (ratingField) ratingField.style.display = 'none';
    }
    backdrop.removeAttribute('hidden');
    document.body.classList.add('modal-open');
    document.getElementById('edit-modal-title-input').focus();
  }

  function closeEditModal() {
    var backdrop = document.getElementById('edit-modal-backdrop');
    if (backdrop) backdrop.setAttribute('hidden', '');
    document.body.classList.remove('modal-open');
  }

  function submitEditModal() {
    var path = document.getElementById('edit-modal-path').value;
    var idx = parseInt(document.getElementById('edit-modal-idx').value, 10);
    var title = document.getElementById('edit-modal-title-input').value.trim();
    var artist = document.getElementById('edit-modal-artist-input').value.trim();
    var album = document.getElementById('edit-modal-album-input').value.trim();
    var saveBtn = document.getElementById('edit-modal-save-btn');
    if (!path) return;
    if (saveBtn) saveBtn.disabled = true;

    /* Determine if rating changed */
    var t = filteredItems[idx];
    var oldRating = t ? Math.round(t.rating || 0) : 0;
    var newRating = _editModalRating;
    var ratingChanged = RATING_WRITE_ENABLED && (newRating !== oldRating);

    /* Save metadata (title/artist/album) */
    var metaPromise = fetch(METADATA_EDIT_PATH, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: path, title: title, artist: artist, album: album || null })
    }).then(function(r) { return r.json(); });

    /* Save rating if changed */
    var ratingPromise = ratingChanged
      ? fetch(RATING_API_PATH, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: path, rating: newRating })
        }).then(function(r) { return r.ok ? r.json() : null; })
      : Promise.resolve(null);

    Promise.all([metaPromise, ratingPromise])
      .then(function(results) {
        var d = results[0];
        var rd = results[1];
        if (saveBtn) saveBtn.disabled = false;
        if (d.ok) {
          /* Update in-memory items so the list reflects changes immediately */
          var updates = { title: title, artist: artist };
          if (rd && rd.ok) updates.rating = rd.rating;
          if (filteredItems[idx]) {
            filteredItems[idx] = Object.assign({}, filteredItems[idx], updates);
          }
          for (var i = 0; i < allItems.length; i++) {
            if (allItems[i].relative_path === path) {
              allItems[i] = Object.assign({}, allItems[i], updates);
              break;
            }
          }
          closeEditModal();
          applyFilter();
          /* Update player display if this is the currently playing track */
          if (idx === currentIndex) {
            if (playerTitle) playerTitle.textContent = title;
            if (playerArtist) playerArtist.textContent = artist;
            if (rd && rd.ok) renderPlayerRating(rd.rating);
          }
          /* Rebuild weighted shuffle queue if rating changed */
          if (rd && rd.ok && shuffleMode === 'weighted') rebuildShuffleQueue(currentIndex);
          showToast('Gespeichert \u2713');
        } else {
          showToast('Fehler beim Speichern');
        }
      })
      .catch(function() {
        if (saveBtn) saveBtn.disabled = false;
        showToast('Netzwerkfehler beim Speichern');
      });
  }

  function toggleFavorite(item, btn) {
    if (!item || !item.relative_path) return;
    var base = API_PATH.substring(0, API_PATH.lastIndexOf('/'));
    var isPinned = _savedFavorites[item.relative_path];

    if (isPinned) {
      /* Remove favorite */
      fetch(base + '/shortcuts?id=' + encodeURIComponent(item.relative_path), { method: 'DELETE' })
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function() {
          delete _savedFavorites[item.relative_path];
          if (btn) { btn.classList.remove('pinned'); btn.title = 'Favorit'; }
          showToast('Favorit entfernt');
        })
        .catch(function() {});
    } else {
      /* Add favorite */
      fetch(base + '/shortcuts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: item.relative_path,
          title: item.title || item.relative_path,
          icon: '/thumb?path=' + encodeURIComponent(item.relative_path)
        })
      })
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function() {
        _savedFavorites[item.relative_path] = true;
        if (btn) { btn.classList.add('pinned'); btn.title = 'Favorit entfernen'; }
        showToast('Als Favorit gespeichert');
        /* On mobile: additionally offer share sheet for home screen shortcut */
        if (navigator.share && ('ontouchstart' in window || navigator.maxTouchPoints > 0)) {
          var deepUrl = window.location.origin + '/?id=' + encodeURIComponent(item.relative_path);
          setTimeout(function() {
            navigator.share({
              title: item.title || 'Favorit',
              text: item.title || '',
              url: deepUrl
            }).catch(function() {});
          }, 600);
        }
      })
      .catch(function() { showToast('Favorit konnte nicht gespeichert werden'); });
    }
  }

  /* showToast() lives in _core.py — kept as the single canonical
     definition (was accidentally duplicated here during the module split). */

  viewToggle.addEventListener('click', function() {
    if (_isTrackViewVisible()) {
      if (isVideoMode) return; /* detail/table view is audio-only */
      _toggleTrackViewMode();
      return;
    }
    if (_anyToolActive()) return; /* locked while tools are active */
    if (viewMode === 'list') viewMode = 'grid';
    else viewMode = 'list';
    localStorage.setItem('ht-view-mode', viewMode);
    if (inPlaylist) {
      applyViewMode();
      applyFilter();
    } else {
      showFolderView();
    }
    if (typeof _router !== 'undefined') _router.update();
  });
  searchInput.addEventListener('input', function() {
    /* Debounce: wait 150 ms after last keystroke before re-rendering the
       (potentially large) track list.  Keeps typing snappy at 6000 items. */
    clearTimeout(_searchDebounceTimer);
    _searchDebounceTimer = setTimeout(function() {
      applyFilter();
      if (typeof _router !== 'undefined') _router.update();
    }, 150);
  });
  sortField.addEventListener('change', function() { applyFilter(); if (typeof _router !== 'undefined') _router.update(); });
  if (filterRatingBtn) {
    filterRatingBtn.addEventListener('click', function() {
      /* cycle 0 → 1 → 2 → 3 → 4 → 5 → 0 */
      filterRating = (filterRating + 1) % 6;
      localStorage.setItem('ht-filter-rating', String(filterRating));
      updateFilterChips();
      applyFilter();
      if (typeof _router !== 'undefined') _router.update();
    });
  }
  if (filterFavBtn) {
    filterFavBtn.addEventListener('click', function() {
      filterFav = !filterFav;
      localStorage.setItem('ht-filter-fav', filterFav ? '1' : '0');
      updateFilterChips();
      applyFilter();
      if (typeof _router !== 'undefined') _router.update();
    });
  }
  if (filterGenreBtn) {
    filterGenreBtn.addEventListener('click', function() {
      /* Collect genres from current playlist, cycle through them */
      var genres = {};
      (playlistItems || []).forEach(function(t) {
        if (t.genre) genres[t.genre] = true;
      });
      var genreList = Object.keys(genres).sort();
      if (!genreList.length) return;
      var idx = filterGenre ? genreList.indexOf(filterGenre) : -1;
      filterGenre = (idx + 1 < genreList.length) ? genreList[idx + 1] : '';
      localStorage.setItem('ht-filter-genre', filterGenre);
      updateFilterChips();
      applyFilter();
      if (typeof _router !== 'undefined') _router.update();
    });
  }
  if (filterHiddenBtn) {
    filterHiddenBtn.addEventListener('click', function() {
      showHidden = !showHidden;
      localStorage.setItem('ht-show-hidden', showHidden ? '1' : '0');
      updateFilterChips();
      applyFilter();
      if (typeof _router !== 'undefined') _router.update();
    });
  }
  updateFilterChips();

  /* ── init ── */
  if (METADATA_EDIT_ENABLED) {
    var _editCancelBtn = document.getElementById('edit-modal-cancel-btn');
    var _editSaveBtn   = document.getElementById('edit-modal-save-btn');
    var _editBackdrop  = document.getElementById('edit-modal-backdrop');
    if (_editCancelBtn) _editCancelBtn.addEventListener('click', closeEditModal);
    if (_editSaveBtn)   _editSaveBtn.addEventListener('click', submitEditModal);
    /* Close on backdrop click (outside the panel) */
    if (_editBackdrop) {
      _editBackdrop.addEventListener('click', function(e) {
        if (e.target === _editBackdrop) closeEditModal();
      });
    }
    /* Submit on Enter inside inputs, Escape to close */
    document.addEventListener('keydown', function(e) {
      var backdrop = document.getElementById('edit-modal-backdrop');
      if (!backdrop || backdrop.hasAttribute('hidden')) return;
      if (e.key === 'Escape') { e.preventDefault(); closeEditModal(); }
      if (e.key === 'Enter' && e.target.tagName === 'INPUT') { e.preventDefault(); submitEditModal(); }
    });
  }

  if (!OFFLINE_ENABLED) {
    if (downloadedPill) {
      downloadedPill.textContent = 'Safe Mode';
      downloadedPill.classList.add('is-offline');
    }
  } else if (typeof indexedDB !== 'undefined') {
    initDownloadDB().catch(function(err) {
      console.warn('IndexedDB not available:', err);
    }).then(function() {
      updateAllDownloadButtons();
      refreshOfflineLibrary();
    });
  } else {
    refreshOfflineLibrary();
  }
  applyViewMode();

  /* ── URL routing / deep linking ──
     The browser URL mirrors the current view so reload / bookmarks /
     share-links restore navigation state.

     Query schema (all parameters optional):
       ?view=folder       &path=<rel>                 → folder grid
       ?view=playlist     &path=<rel>     [&track=<rel>]   → folder-playlist
       ?view=userplaylist &id=<id>        [&track=<rel>]   → user playlist
       ?view=favorites                    [&track=<rel>]   → favorites
       ?view=offline                      [&track=<rel>]   → offline downloads
       ?view=search       &q=<needle>     [&track=<rel>]   → global search results

     Legacy ?id=<rel> (auto-play deep link) is still honoured. */
  var _router = (function() {
    var _suppress = true;      /* stays true until restore() runs — otherwise the initial
                                  showFolderView() from loadInitialCatalog would overwrite
                                  the deep-link URL the user reloaded with */
    var _lastKey = '';         /* "view|path|id" of last pushed entry; track-only change → replace */

    function _readUrl() {
      var p = new URLSearchParams(window.location.search);
      return {
        view: p.get('view') || '',
        path: p.get('path') || '',
        id: p.get('id') || '',
        track: p.get('track') || '',
        q: p.get('q') || '',
        sort: p.get('sort') || '',
        fr: p.get('fr') || '',
        ff: p.get('ff') || '',
        fg: p.get('fg') || '',
        fh: p.get('fh') || '',
        vm: p.get('vm') || '',
        panel: p.get('panel') || ''
      };
    }

    function _buildUrl(s) {
      var p = new URLSearchParams();
      if (s.view) p.set('view', s.view);
      if (s.path) p.set('path', s.path);
      if (s.id) p.set('id', s.id);
      if (s.track) p.set('track', s.track);
      if (s.q) p.set('q', s.q);
      if (s.sort) p.set('sort', s.sort);
      if (s.fr) p.set('fr', s.fr);
      if (s.ff) p.set('ff', s.ff);
      if (s.fg) p.set('fg', s.fg);
      if (s.fh) p.set('fh', s.fh);
      if (s.vm) p.set('vm', s.vm);
      if (s.panel) p.set('panel', s.panel);
      var qs = p.toString();
      return window.location.pathname + (qs ? '?' + qs : '');
    }

    function _collectUiState(s) {
      /* Sort/filter/view-mode are always meaningful — encode whenever they differ from defaults. */
      try {
        if (sortField && sortField.value && sortField.value !== 'custom') s.sort = sortField.value;
      } catch (e) { /* ignore */ }
      if (typeof filterRating === 'number' && filterRating > 0) s.fr = String(filterRating);
      if (filterFav) s.ff = '1';
      if (filterGenre) s.fg = filterGenre;
      /* showHidden default = true → only encode when explicitly disabled */
      if (typeof showHidden === 'boolean' && !showHidden) s.fh = '0';
      if (viewMode && viewMode !== 'list') s.vm = viewMode;
      /* Tools-panel open? (audit is its own page, not a modal) */
      try {
        if (toolsBackdrop && !toolsBackdrop.hasAttribute('hidden')) s.panel = 'tools';
      } catch (e) { /* ignore */ }
      return s;
    }

    function _currentState() {
      var s = { view: '', path: '', id: '', track: '', q: '',
                sort: '', fr: '', ff: '', fg: '', fh: '', vm: '', panel: '' };
      /* Active selection only meaningful inside a list view */
      if (inPlaylist && filteredItems && currentIndex >= 0 && currentIndex < filteredItems.length) {
        var t = filteredItems[currentIndex];
        if (t && t.relative_path) s.track = t.relative_path;
      }
      if (_globalSearchActive) {
        s.view = 'search';
        var inp = document.getElementById('global-search-input');
        if (inp && inp.value) s.q = inp.value.trim();
        return _collectUiState(s);
      }
      if (currentPath === '__offline__') { s.view = 'offline'; return _collectUiState(s); }
      if (_currentPlaylistId === '__favorites__') { s.view = 'favorites'; return _collectUiState(s); }
      if (_currentPlaylistId && _currentPlaylistId !== '__folder__') {
        s.view = 'userplaylist'; s.id = _currentPlaylistId; return _collectUiState(s);
      }
      if (inPlaylist) { s.view = 'playlist'; s.path = currentPath || ''; return _collectUiState(s); }
      /* Default = folder grid (incl. root) */
      s.view = 'folder'; s.path = currentPath || '';
      return _collectUiState(s);
    }

    /* Key drives pushState vs replaceState: filter/sort/vm/panel changes share the
       same key as the current view → no new history entry. */
    function _key(s) { return (s.view || '') + '|' + (s.path || '') + '|' + (s.id || '') + '|' + (s.q || ''); }

    function update() {
      if (_suppress) return;
      var s = _currentState();
      var url = _buildUrl(s);
      var cur = window.location.pathname + window.location.search;
      if (url === cur) { _lastKey = _key(s); return; }
      var k = _key(s);
      try {
        if (k === _lastKey) {
          /* Same list/view, only track changed → replace (no extra history entry) */
          history.replaceState(s, '', url);
        } else {
          history.pushState(s, '', url);
        }
      } catch (e) { /* ignore */ }
      _lastKey = k;
    }

    function _markTrack(trackRp) {
      if (!trackRp || !filteredItems || !filteredItems.length) return;
      var i = filteredItems.findIndex(function(it) { return it && it.relative_path === trackRp; });
      if (i >= 0) {
        currentIndex = i;
        if (typeof markActive === 'function') markActive();
      }
    }

    function _applyUiStateFromUrl(st) {
      /* URL wins over localStorage: explicit param overrides the saved value;
         absence of param leaves localStorage default untouched. */
      if (st.sort && sortField) {
        try { sortField.value = st.sort; } catch (e) { /* unknown option */ }
      }
      if (st.fr !== '') {
        var fr = parseInt(st.fr, 10);
        if (!isNaN(fr) && fr >= 0 && fr <= 5) {
          filterRating = fr;
          try { localStorage.setItem('ht-filter-rating', String(fr)); } catch (e) { /* ignore */ }
        }
      }
      if (st.ff !== '') {
        filterFav = (st.ff === '1');
        try { localStorage.setItem('ht-filter-fav', filterFav ? '1' : '0'); } catch (e) { /* ignore */ }
      }
      if (st.fg !== '') {
        filterGenre = st.fg;
        try { localStorage.setItem('ht-filter-genre', filterGenre); } catch (e) { /* ignore */ }
      }
      if (st.fh !== '') {
        showHidden = (st.fh !== '0');
        try { localStorage.setItem('ht-show-hidden', showHidden ? '1' : '0'); } catch (e) { /* ignore */ }
      }
      if (st.vm === 'grid' || st.vm === 'list') {
        viewMode = st.vm;
        try { localStorage.setItem('ht-view-mode', viewMode); } catch (e) { /* ignore */ }
      }
      try { if (typeof updateFilterChips === 'function') updateFilterChips(); } catch (e) { /* ignore */ }
    }

    function _applyPanelFromUrl(st) {
      /* Run after the view has been rendered so DOM is in place. */
      if (st.panel === 'tools' && typeof openToolsPanel === 'function') {
        try { openToolsPanel(); } catch (e) { /* ignore */ }
      }
    }

    function restore() {
      var st = _readUrl();

      /* Apply UI state (sort/filter/view-mode) BEFORE rendering — they affect what's shown. */
      _applyUiStateFromUrl(st);

      /* Legacy ?id= deep link → auto-play */
      if (!st.view && st.id && allItems.length) {
        var target = allItems.find(function(it) { return it.relative_path === st.id; });
        if (target) {
          var slash = st.id.lastIndexOf('/');
          var parent = slash > 0 ? st.id.substring(0, slash) : '';
          _suppress = true;
          try {
            currentPath = parent;
            var c = contentsAt(parent);
            var siblings = c.files.length ? c.files : itemsUnder(parent);
            var idx = siblings.findIndex(function(it) { return it.relative_path === st.id; });
            showPlaylist(siblings, true, idx >= 0 ? idx : 0);
          } finally { _suppress = false; }
          _applyPanelFromUrl(st);
          update();
          return;
        }
        _suppress = false;
        return;
      }

      if (!st.view) {
        _suppress = false;
        _applyPanelFromUrl(st);
        return;
      } /* root — nothing to do */

      _suppress = true;
      try {
        if (st.view === 'offline') {
          openOfflineLibrary();
          /* offline list is loaded async — defer track marker */
          if (st.track) setTimeout(function() { _markTrack(st.track); }, 200);
        } else if (st.view === 'favorites') {
          showUserPlaylistView('__favorites__');
          _markTrack(st.track);
        } else if (st.view === 'userplaylist' && st.id) {
          showUserPlaylistView(st.id);
          _markTrack(st.track);
        } else if (st.view === 'playlist') {
          currentPath = st.path || '';
          var pc = contentsAt(currentPath);
          var pItems = pc.files.length ? pc.files : itemsUnder(currentPath);
          if (pItems.length) {
            var pStart = 0;
            if (st.track) {
              var pi = pItems.findIndex(function(it) { return it.relative_path === st.track; });
              if (pi >= 0) pStart = pi;
            }
            showPlaylist(pItems, false, pStart);
            _markTrack(st.track);
          } else {
            showFolderView();
          }
        } else if (st.view === 'search' && st.q) {
          currentPath = '';
          showFolderView();
          var inp = document.getElementById('global-search-input');
          if (inp) inp.value = st.q;
          if (typeof globalSearch === 'function') globalSearch(st.q);
          _markTrack(st.track);
        } else {
          /* folder (default) */
          currentPath = st.path || '';
          showFolderView();
        }
      } finally {
        _suppress = false;
      }
      _applyPanelFromUrl(st);
      /* Reflect the actually-restored state back to the URL (e.g. fallback to folder view) */
      update();
    }

    function init() {
      window.addEventListener('popstate', function() {
        /* Browser back/forward → re-render. restore() handles its own suppression
           and the final update() is a no-op because the URL already matches. */
        restore();
      });
    }

    return { update: update, restore: restore, init: init };
  }());

  /* Backwards-compat shim so any leftover call sites keep working. */
  function handleDeepLink() { _router.restore(); }

  /* ── User Playlists ── */
  var _userPlaylists = [];
  var _playlistAddPath = '';
  var _currentPlaylistId = '';

  /* ── Favorites custom order (server-side + localStorage fallback) ── */
  function _loadFavoritesOrder() {
    try {
      var raw = localStorage.getItem('ht-favorites-order');
      return raw ? JSON.parse(raw) : [];
    } catch (e) { return []; }
  }
  function _saveFavoritesOrder(paths) {
    try { localStorage.setItem('ht-favorites-order', JSON.stringify(paths)); }
    catch (e) { /* quota exceeded — ignore */ }
    /* persist to server (fire-and-forget) */
    fetch(FOLDER_ORDER_API_PATH, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder_path: '__favorites__', items: paths })
    }).catch(function() {});
  }
  function _loadFavoritesOrderAsync(cb) {
    fetch(FOLDER_ORDER_API_PATH + '?path=__favorites__')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        var items = d.items || [];
        if (items.length) {
          try { localStorage.setItem('ht-favorites-order', JSON.stringify(items)); }
          catch (e) {}
          cb(items);
        } else {
          cb(_loadFavoritesOrder());
        }
      }).catch(function() { cb(_loadFavoritesOrder()); });
  }
  function _sortFavoritesByOrder(favItems) {
    var order = _loadFavoritesOrder();
    if (!order.length) return favItems;
    var orderMap = {};
    order.forEach(function(rp, i) { orderMap[rp] = i; });
    return favItems.slice().sort(function(a, b) {
      var ia = orderMap[a.relative_path], ib = orderMap[b.relative_path];
      if (ia === undefined && ib === undefined) return 0;
      if (ia === undefined) return 1;
      if (ib === undefined) return -1;
      return ia - ib;
    });
  }

  /* ── Folder custom order (server-side + localStorage fallback) ── */
  function _folderOrderKey(folderPath) {
    return 'ht-folder-order-' + (folderPath || '__root__');
  }
  function _loadFolderOrder(folderPath) {
    try {
      var raw = localStorage.getItem(_folderOrderKey(folderPath));
      return raw ? JSON.parse(raw) : [];
    } catch (e) { return []; }
  }
  function _saveFolderOrder(folderPath, paths) {
    try { localStorage.setItem(_folderOrderKey(folderPath), JSON.stringify(paths)); }
    catch (e) { /* quota exceeded — ignore */ }
    /* persist to server (fire-and-forget) */
    fetch(FOLDER_ORDER_API_PATH, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder_path: folderPath || '__root__', items: paths })
    }).catch(function() {});
  }
  function _loadFolderOrderAsync(folderPath, cb) {
    var key = folderPath || '__root__';
    fetch(FOLDER_ORDER_API_PATH + '?path=' + encodeURIComponent(key))
      .then(function(r) { return r.json(); })
      .then(function(d) {
        var items = d.items || [];
        if (items.length) {
          try { localStorage.setItem(_folderOrderKey(folderPath), JSON.stringify(items)); }
          catch (e) {}
          cb(items);
        } else {
          cb(_loadFolderOrder(folderPath));
        }
      }).catch(function() { cb(_loadFolderOrder(folderPath)); });
  }
  function _sortByFolderOrder(folderPath, items) {
    var order = _loadFolderOrder(folderPath);
    if (!order.length) return items;
    var orderMap = {};
    order.forEach(function(rp, i) { orderMap[rp] = i; });
    return items.slice().sort(function(a, b) {
      var ia = orderMap[a.relative_path], ib = orderMap[b.relative_path];
      if (ia === undefined && ib === undefined) return 0;
      if (ia === undefined) return 1;
      if (ib === undefined) return -1;
      return ia - ib;
    });
  }

  var _playlistRevision = 0;
  var _playlistSyncTimer = null;
  var _PLAYLIST_SYNC_INTERVAL = """
        + (str(playlist_sync_interval_ms))
        + """; /* ms */

"""
    )
