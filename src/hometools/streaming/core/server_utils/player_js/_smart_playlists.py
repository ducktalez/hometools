"""JS fragment: smart playlists (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_smart_playlists_js() -> str:
    """Return the smart playlists section of the player JS."""
    return """  function openSmartPlaylistEditor(existingPl) {
    /* Build state copy (deep clone) */
    if (existingPl && existingPl.smart) {
      _smartEditorState = {
        id: existingPl.id,
        name: existingPl.name,
        match: existingPl.smart.match || 'all',
        rules: JSON.parse(JSON.stringify(existingPl.smart.rules || [])),
        limit: existingPl.smart.limit || ''
      };
    } else {
      _smartEditorState = {
        id: null,
        name: '',
        match: 'all',
        rules: [{ field: 'rating', op: 'gte', value: 4 }],
        limit: ''
      };
    }
    _smartRenderEditor();
  }

  function _smartRenderEditor() {
    var s = _smartEditorState;
    var rulesHtml = s.rules.map(function(r, i) { return _smartRenderRuleRow(r, i); }).join('');
    var html =
      '<div class="smart-editor-backdrop" id="smart-editor-backdrop">' +
        '<div class="smart-editor-modal" role="dialog" aria-modal="true">' +
          '<div class="smart-editor-header">' +
            '<span>' + IC_SMART_PLAYLIST + ' Intelligente Playlist</span>' +
            '<button type="button" class="smart-editor-close" id="smart-editor-close" title="Schließen">×</button>' +
          '</div>' +
          '<div class="smart-editor-body">' +
            '<label class="smart-editor-label">Name' +
              '<input type="text" id="smart-editor-name" value="' + escHtml(s.name) + '" placeholder="Best of Rock">' +
            '</label>' +
            '<div class="smart-editor-match">' +
              '<label><input type="radio" name="smart-match" value="all"' + (s.match === 'all' ? ' checked' : '') + '> Alle Regeln erfüllen (UND)</label>' +
              '<label><input type="radio" name="smart-match" value="any"' + (s.match === 'any' ? ' checked' : '') + '> Eine Regel erfüllen (ODER)</label>' +
            '</div>' +
            '<div class="smart-editor-rules" id="smart-editor-rules">' + rulesHtml + '</div>' +
            '<button type="button" class="smart-editor-add" id="smart-editor-add-rule">+ Regel hinzufügen</button>' +
            '<label class="smart-editor-label">Begrenzen auf (optional)' +
              '<input type="number" id="smart-editor-limit" value="' + escHtml(String(s.limit)) + '" placeholder="0 = unbegrenzt">' +
            '</label>' +
          '</div>' +
          '<div class="smart-editor-footer">' +
            '<button type="button" class="smart-editor-cancel" id="smart-editor-cancel">Abbrechen</button>' +
            '<button type="button" class="smart-editor-save" id="smart-editor-save">Speichern</button>' +
          '</div>' +
        '</div>' +
      '</div>';
    var existing = document.getElementById('smart-editor-backdrop');
    if (existing) existing.remove();
    document.body.insertAdjacentHTML('beforeend', html);
    _smartWireEditor();
  }

  function _smartWireEditor() {
    var bd = document.getElementById('smart-editor-backdrop');
    if (!bd) return;
    function close() { bd.remove(); _smartEditorState = null; }
    bd.addEventListener('click', function(e) { if (e.target === bd) close(); });
    document.getElementById('smart-editor-close').addEventListener('click', close);
    document.getElementById('smart-editor-cancel').addEventListener('click', close);
    document.getElementById('smart-editor-add-rule').addEventListener('click', function() {
      _smartCollectFromDom();
      _smartEditorState.rules.push({ field: 'rating', op: 'gte', value: 4 });
      _smartRenderEditor();
    });
    bd.querySelectorAll('input[name="smart-match"]').forEach(function(r) {
      r.addEventListener('change', function() {
        _smartCollectFromDom();
        _smartEditorState.match = r.value;
      });
    });
    bd.querySelectorAll('.smart-rule-row').forEach(function(row) {
      var idx = Number(row.dataset.idx);
      row.querySelector('.smart-rule-field').addEventListener('change', function(e) {
        _smartCollectFromDom();
        var rule = _smartEditorState.rules[idx];
        rule.field = e.target.value;
        var ops = _smartOpsFor(rule.field);
        rule.op = ops[0][0];
        rule.value = _smartFieldType(rule.field) === 'playlist' ? [] :
                     _smartFieldType(rule.field) === 'bool'     ? true :
                     _smartFieldType(rule.field) === 'number'   ? 0 : '';
        _smartRenderEditor();
      });
      row.querySelector('.smart-rule-op').addEventListener('change', function(e) {
        _smartCollectFromDom();
        _smartEditorState.rules[idx].op = e.target.value;
        _smartRenderEditor();
      });
      row.querySelector('.smart-rule-del').addEventListener('click', function() {
        _smartCollectFromDom();
        _smartEditorState.rules.splice(idx, 1);
        if (_smartEditorState.rules.length === 0) {
          _smartEditorState.rules.push({ field: 'rating', op: 'gte', value: 4 });
        }
        _smartRenderEditor();
      });
    });
    document.getElementById('smart-editor-save').addEventListener('click', function() {
      _smartCollectFromDom();
      _smartSubmit(close);
    });
  }

  function _smartCollectFromDom() {
    var s = _smartEditorState;
    var nameEl = document.getElementById('smart-editor-name');
    var limitEl = document.getElementById('smart-editor-limit');
    if (nameEl) s.name = nameEl.value.trim();
    if (limitEl) s.limit = limitEl.value ? Number(limitEl.value) : '';
    var matched = document.querySelector('input[name="smart-match"]:checked');
    if (matched) s.match = matched.value;
    var rows = document.querySelectorAll('.smart-rule-row');
    rows.forEach(function(row) {
      var idx = Number(row.dataset.idx);
      var rule = s.rules[idx]; if (!rule) return;
      rule.field = row.querySelector('.smart-rule-field').value;
      rule.op = row.querySelector('.smart-rule-op').value;
      var type = _smartFieldType(rule.field);
      if (type === 'playlist') {
        var cbs = row.querySelectorAll('.smart-rule-pl-cb');
        rule.value = Array.from(cbs).filter(function(cb) { return cb.checked; }).map(function(cb) { return cb.value; });
      } else if (type === 'bool') {
        rule.value = row.querySelector('.smart-rule-value').value === 'true';
      } else if (rule.op === 'between') {
        var lo = row.querySelector('.smart-rule-value-lo');
        var hi = row.querySelector('.smart-rule-value-hi');
        rule.value = [Number(lo.value || 0), Number(hi.value || 0)];
      } else {
        var v = row.querySelector('.smart-rule-value').value;
        rule.value = (type === 'number') ? Number(v || 0) : v;
      }
    });
  }

  function _smartSubmit(onSuccess) {
    var s = _smartEditorState;
    if (!s.name) { showToast('Bitte einen Namen eingeben'); return; }
    if (!s.rules.length) { showToast('Mindestens eine Regel erforderlich'); return; }
    /* Defensive: strip any self-reference from in_playlist rules (circular-reference guard) */
    if (s.id) {
      s.rules.forEach(function(r) {
        if (r.field === 'in_playlist' && Array.isArray(r.value)) {
          r.value = r.value.filter(function(v) { return v !== s.id; });
        }
      });
    }
    var smart = { match: s.match, rules: s.rules };
    if (s.limit && Number(s.limit) > 0) smart.limit = Number(s.limit);
    var payload, method;
    if (s.id) {
      payload = { playlist_id: s.id, smart: smart };
      method = 'PUT';
    } else {
      payload = { name: s.name, smart: smart };
      method = 'POST';
    }
    fetch(PLAYLISTS_SMART_PATH, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function(r) {
      if (!r.ok) return r.json().then(function(d) { throw new Error(d.detail || 'Fehler'); });
      return r.json();
    }).then(function(d) {
      if (d.playlist) {
        if (s.id) {
          var i = _userPlaylists.findIndex(function(p) { return p.id === s.id; });
          if (i >= 0) _userPlaylists[i] = d.playlist;
        } else {
          _userPlaylists.unshift(d.playlist);
        }
        if (typeof onSuccess === 'function') onSuccess();
        showFolderView();
        showToast('Intelligente Playlist gespeichert');
      }
    }).catch(function(err) {
      showToast(String(err.message || 'Fehler beim Speichern'));
    });
  }

  /* "Titel" pseudo-playlist: union of all user playlist tracks (deduplicated, order-preserving). */
  function _collectAllPlaylistRelPaths() {
    var seen = Object.create(null);
    var out = [];
    _userPlaylists.forEach(function(pl) {
      (pl.items || []).forEach(function(rp) {
        if (!seen[rp]) { seen[rp] = true; out.push(rp); }
      });
    });
    return out;
  }
  function _countAllPlaylistTitles() {
    return _collectAllPlaylistRelPaths().length;
  }
  function _resolveAllPlaylistItems() {
    var rels = _collectAllPlaylistRelPaths();
    var resolved = [];
    rels.forEach(function(rp) {
      var match = allItems.find(function(it) { return it.relative_path === rp; });
      if (match) resolved.push(match);
    });
    return resolved;
  }

  function showUserPlaylistView(plId) {
    /* Show playlist content without auto-playing (browse mode).
       Header/toolbar state is set via _enterTrackListView() (_folder_browse.py)
       — same shared entry point showPlaylist()/playDuplicates() use, so this
       view is indistinguishable from any other track list (see
       docs/IMPLEMENTATION_PLAN.md "UI-Template-Vereinheitlichung" Phase 2). */
    if (plId === '__alltitles__') {
      if (allItems.length === 0) { showToast('Keine Titel in der Bibliothek vorhanden'); return; }
      _currentPlaylistId = '__alltitles__';
      playlistItems = allItems.slice();
      inPlaylist = true;
      currentPath = '';
      _enterTrackListView({ title: 'Titel' });
      return;
    }
    if (plId === '__favorites__') {
      var favItems = allItems.filter(function(t) { return !!_savedFavorites[t.relative_path]; });
      if (favItems.length === 0) { showToast('Keine Favoriten vorhanden'); return; }
      _currentPlaylistId = '__favorites__';
      playlistItems = _sortFavoritesByOrder(favItems);
      inPlaylist = true;
      currentPath = '';
      _enterTrackListView({ title: 'Favoriten' });
      /* Pre-warm: fetch server-side favorites order and re-sort if different */
      _loadFavoritesOrderAsync(function(serverOrder) {
        if (!serverOrder.length) return;
        if (_currentPlaylistId !== '__favorites__') return;
        var localOrder = _loadFavoritesOrder();
        if (JSON.stringify(localOrder) === JSON.stringify(serverOrder)) return;
        playlistItems = _sortFavoritesByOrder(favItems);
        applyFilter();
      });
      return;
    }
    var data = _resolvePlaylistItems(plId);
    if (!data) { showToast('Keine Titel in dieser Playlist gefunden'); return; }
    _currentPlaylistId = plId;
    playlistItems = data.resolved;
    inPlaylist = true;
    currentPath = '';
    _enterTrackListView({ title: data.pl.name });
  }


  function playUserPlaylist(plId) {
    /* Delegate to showUserPlaylistView() so header/breadcrumb/toolbar state
       stays identical to the browse-mode entry point (same
       _enterTrackListView() path) — only difference is auto-play. Never
       duplicate header DOM manipulation here (see
       docs/IMPLEMENTATION_PLAN.md "UI-Template-Vereinheitlichung"). */
    var before = playlistItems;
    showUserPlaylistView(plId);
    if (playlistItems !== before && playlistItems.length > 0) playTrack(0);
  }

  function deleteUserPlaylist(plId) {
    /* TODO: Nach Entwicklungsphase → Nachfrage + Archivierung statt L\u00f6schung */
    var pl = _userPlaylists.find(function(p) { return p.id === plId; });
    var name = pl ? pl.name : 'Playlist';
    if (!confirm('Playlist "' + name + '" wirklich l\u00f6schen?')) return;
    /* Optimistic: remove locally first */
    var snap = _snapshotPlaylists();
    _userPlaylists = _userPlaylists.filter(function(p) { return p.id !== plId; });
    if (!currentPath && !inPlaylist) showFolderView();
    fetch(PLAYLISTS_API_PATH + '?id=' + encodeURIComponent(plId), { method: 'DELETE' })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        _userPlaylists = d.items || [];
        if (typeof d.revision === 'number') _playlistRevision = d.revision;
        showToast('Playlist gel\u00f6scht');
        if (!currentPath && !inPlaylist) showFolderView();
      })
      .catch(function() {
        _restorePlaylists(snap);
        showToast('Fehler beim L\u00f6schen \u2014 r\u00fcckg\u00e4ngig');
        if (!currentPath && !inPlaylist) showFolderView();
      });
  }

  function renameUserPlaylist(plId) {
    var pl = _userPlaylists.find(function(p) { return p.id === plId; });
    if (!pl) return;
    var newName = prompt('Neuer Name:', pl.name);
    if (!newName || !newName.trim() || newName.trim() === pl.name) return;
    var trimmed = newName.trim();
    var oldName = pl.name;
    pl.name = trimmed; /* optimistic */
    if (!currentPath && !inPlaylist) showFolderView();
    fetch(PLAYLISTS_API_PATH, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ playlist_id: plId, name: trimmed })
    }).then(function(r) {
      if (!r.ok) throw new Error();
      return r.json();
    }).then(function(d) {
      if (d.playlist) {
        var i = _userPlaylists.findIndex(function(p) { return p.id === plId; });
        if (i >= 0) _userPlaylists[i] = d.playlist;
      }
      showToast('Playlist umbenannt');
      if (!currentPath && !inPlaylist) showFolderView();
    }).catch(function() {
      pl.name = oldName;
      showToast('Fehler beim Umbenennen');
      if (!currentPath && !inPlaylist) showFolderView();
    });
  }

  /* ── add-to-playlist modal ── */
  function openPlaylistModal(relativePath) {
    _playlistAddPath = relativePath;
    var backdrop = document.getElementById('playlist-modal-backdrop');
    if (!backdrop) return;
    backdrop.hidden = false;
    document.body.classList.add('modal-open');
    renderPlaylistModalList();
  }

  function closePlaylistModal() {
    var backdrop = document.getElementById('playlist-modal-backdrop');
    if (backdrop) backdrop.hidden = true;
    document.body.classList.remove('modal-open');
    _playlistAddPath = '';
  }

  function renderPlaylistModalList() {
    var listEl = document.getElementById('playlist-modal-list');
    if (!listEl) return;
    if (_userPlaylists.length === 0) {
      listEl.innerHTML = '<li style="padding:0.5rem;color:var(--sub);font-size:0.85rem">Noch keine Playlists. Erstelle eine neue!</li>';
      return;
    }
    listEl.innerHTML = _userPlaylists.map(function(pl) {
      var cnt = (pl.items || []).length;
      return '<li class="playlist-modal-item" data-id="' + escHtml(pl.id) + '">' +
        '<span class="playlist-modal-item-name">' + escHtml(pl.name) + '</span>' +
        '<span class="playlist-modal-item-count">' + cnt + ' Titel</span></li>';
    }).join('');
    listEl.querySelectorAll('.playlist-modal-item').forEach(function(el) {
      el.addEventListener('click', function() {
        addToPlaylist(el.dataset.id, _playlistAddPath);
      });
    });
  }

  function addToPlaylist(plId, relativePath) {
    /* Optimistic: add item locally first */
    var snap = _snapshotPlaylists();
    var localPl = _userPlaylists.find(function(p) { return p.id === plId; });
    if (localPl && (localPl.items || []).indexOf(relativePath) < 0) {
      localPl.items = (localPl.items || []).slice();
      localPl.items.push(relativePath);
    }
    updatePlaylistPill();
    closePlaylistModal();
    showToast('Zur Playlist hinzugef\\u00fcgt');
    fetch(PLAYLISTS_API_PATH + '/items', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ playlist_id: plId, relative_path: relativePath })
    }).then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.playlist) {
          var idx = _userPlaylists.findIndex(function(p) { return p.id === plId; });
          if (idx >= 0) _userPlaylists[idx] = d.playlist;
        }
        updatePlaylistPill();
      }).catch(function() {
        _restorePlaylists(snap);
        showToast('Fehler beim Hinzuf\\u00fcgen \\u2014 r\\u00fcckg\\u00e4ngig');
      });
  }

  function createAndAddToPlaylist(name, relativePath) {
    fetch(PLAYLISTS_API_PATH, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name })
    }).then(function(r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function(d) {
        if (d.playlist) {
          _userPlaylists.unshift(d.playlist);
          updatePlaylistPill();
          addToPlaylist(d.playlist.id, relativePath);
        } else {
          showToast('Fehler beim Erstellen');
        }
      }).catch(function() { showToast('Fehler beim Erstellen'); });
  }

  function movePlaylistItem(relativePath, direction) {
    if (!_currentPlaylistId) return;
    if (_currentPlaylistId === '__alltitles__') return; /* read-only union */
    /* Optimistic: swap locally first */
    var snap = _snapshotPlaylists();
    var localPl = _userPlaylists.find(function(p) { return p.id === _currentPlaylistId; });
    if (localPl) {
      var litems = (localPl.items || []).slice();
      var li = litems.indexOf(relativePath);
      if (li >= 0) {
        var ni = direction === 'up' ? li - 1 : li + 1;
        if (ni >= 0 && ni < litems.length) {
          var tmp = litems[li]; litems[li] = litems[ni]; litems[ni] = tmp;
          localPl.items = litems;
          _applyPlaylistUpdate(localPl);
        }
      }
    }
    var savedPlId = _currentPlaylistId;
    fetch(PLAYLISTS_API_PATH + '/items', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ playlist_id: savedPlId, relative_path: relativePath, direction: direction })
    }).then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.playlist) {
          var idx = _userPlaylists.findIndex(function(p) { return p.id === savedPlId; });
          if (idx >= 0) _userPlaylists[idx] = d.playlist;
          if (_currentPlaylistId === savedPlId) _applyPlaylistUpdate(d.playlist);
        }
      }).catch(function() {
        _restorePlaylists(snap);
        if (_currentPlaylistId === savedPlId && localPl) _applyPlaylistUpdate(snap.find(function(p) { return p.id === savedPlId; }) || localPl);
        showToast('Fehler beim Verschieben \u2014 r\u00fcckg\u00e4ngig');
      });
  }

  function reorderPlaylistItem(relativePath, toIndex) {
    if (!_currentPlaylistId) return;
    /* "Titel" pseudo-playlist is a read-only union; reorder is not supported. */
    if (_currentPlaylistId === '__alltitles__') return;

    /* Favorites: client-side reorder via localStorage */
    if (_currentPlaylistId === '__favorites__') {
      var paths = playlistItems.map(function(it) { return it.relative_path; });
      var oldIdx = paths.indexOf(relativePath);
      if (oldIdx < 0) return;
      paths.splice(oldIdx, 1);
      var clamped = Math.max(0, Math.min(toIndex, paths.length));
      paths.splice(clamped, 0, relativePath);
      _saveFavoritesOrder(paths);
      /* rebuild playlistItems in new order */
      var itemMap = {};
      playlistItems.forEach(function(it) { itemMap[it.relative_path] = it; });
      var reordered = paths.map(function(rp) { return itemMap[rp]; }).filter(Boolean);
      var playingPath = currentIndex >= 0 && filteredItems[currentIndex]
        ? filteredItems[currentIndex].relative_path : null;
      playlistItems = reordered;
      filteredItems = reordered;
      if (playingPath) {
        var newIdx = reordered.findIndex(function(it) { return it.relative_path === playingPath; });
        if (newIdx >= 0) currentIndex = newIdx;
      }
      renderTracks(reordered, true);
      return;
    }

    /* Folder: client-side reorder via localStorage */
    if (_currentPlaylistId === '__folder__') {
      var fpaths = playlistItems.map(function(it) { return it.relative_path; });
      var fOldIdx = fpaths.indexOf(relativePath);
      if (fOldIdx < 0) return;
      fpaths.splice(fOldIdx, 1);
      var fClamped = Math.max(0, Math.min(toIndex, fpaths.length));
      fpaths.splice(fClamped, 0, relativePath);
      _saveFolderOrder(currentPath, fpaths);
      var fItemMap = {};
      playlistItems.forEach(function(it) { fItemMap[it.relative_path] = it; });
      var fReordered = fpaths.map(function(rp) { return fItemMap[rp]; }).filter(Boolean);
      var fPlayingPath = currentIndex >= 0 && filteredItems[currentIndex]
        ? filteredItems[currentIndex].relative_path : null;
      playlistItems = fReordered;
      filteredItems = fReordered;
      if (fPlayingPath) {
        var fNewIdx = fReordered.findIndex(function(it) { return it.relative_path === fPlayingPath; });
        if (fNewIdx >= 0) currentIndex = fNewIdx;
      }
      renderTracks(fReordered, true);
      return;
    }

    /* Server-backed playlist: optimistic local reorder first */
    var snap = _snapshotPlaylists();
    var localPl = _userPlaylists.find(function(p) { return p.id === _currentPlaylistId; });
    if (localPl) {
      var litems = (localPl.items || []).slice();
      var lOld = litems.indexOf(relativePath);
      if (lOld >= 0) {
        litems.splice(lOld, 1);
        var lClamped = Math.max(0, Math.min(toIndex, litems.length));
        litems.splice(lClamped, 0, relativePath);
        localPl.items = litems;
        _applyPlaylistUpdate(localPl);
      }
    }
    var savedPlId = _currentPlaylistId;
    fetch(PLAYLISTS_API_PATH + '/items', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ playlist_id: savedPlId, relative_path: relativePath, to_index: toIndex })
    }).then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.playlist) {
          var idx = _userPlaylists.findIndex(function(p) { return p.id === savedPlId; });
          if (idx >= 0) _userPlaylists[idx] = d.playlist;
          if (_currentPlaylistId === savedPlId) _applyPlaylistUpdate(d.playlist);
        }
      }).catch(function() {
        _restorePlaylists(snap);
        if (_currentPlaylistId === savedPlId && localPl) _applyPlaylistUpdate(snap.find(function(p) { return p.id === savedPlId; }) || localPl);
        showToast('Fehler beim Verschieben \u2014 r\u00fcckg\u00e4ngig');
      });
  }

  function _applyPlaylistUpdate(pl) {
    var resolved = [];
    pl.items.forEach(function(rp) {
      var match = allItems.find(function(it) { return it.relative_path === rp; });
      if (match) resolved.push(match);
    });
    var playingPath = currentIndex >= 0 && filteredItems[currentIndex] ? filteredItems[currentIndex].relative_path : null;
    playlistItems = resolved;
    filteredItems = resolved;
    if (playingPath) {
      var newIdx = resolved.findIndex(function(it) { return it.relative_path === playingPath; });
      if (newIdx >= 0) currentIndex = newIdx;
    }
    renderTracks(resolved, true);
    updatePlaylistPill();
  }

  /* ── Drag-and-drop reorder for playlist view ── */
  var _dndCleanup = null;

  function destroyPlaylistDragDrop() {
    if (_dndCleanup) { _dndCleanup(); _dndCleanup = null; }
  }

"""
