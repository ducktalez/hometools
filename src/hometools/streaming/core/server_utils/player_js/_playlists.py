"""JS fragment: playlists (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_playlists_js() -> str:
    """Return the playlists section of the player JS."""
    return """  function loadUserPlaylists() {
    if (!PLAYLISTS_ENABLED) return Promise.resolve([]);
    return fetch(PLAYLISTS_API_PATH).then(function(r) { return r.json(); })
      .then(function(d) {
        _userPlaylists = d.items || [];
        if (typeof d.revision === 'number') _playlistRevision = d.revision;
        updatePlaylistPill();
        return _userPlaylists;
      })
      .catch(function() { return []; });
  }

  function _startPlaylistSync() {
    if (!PLAYLISTS_ENABLED) return;
    _stopPlaylistSync();
    _playlistSyncTimer = setInterval(_pollPlaylistVersion, _PLAYLIST_SYNC_INTERVAL);
    /* Pause when tab hidden, resume when visible */
    document.addEventListener('visibilitychange', _onPlaylistVisibility);
  }
  function _stopPlaylistSync() {
    if (_playlistSyncTimer) { clearInterval(_playlistSyncTimer); _playlistSyncTimer = null; }
  }
  function _onPlaylistVisibility() {
    if (document.hidden) {
      _stopPlaylistSync();
    } else {
      /* Resume polling and do an immediate check */
      _stopPlaylistSync();
      _pollPlaylistVersion();
      _playlistSyncTimer = setInterval(_pollPlaylistVersion, _PLAYLIST_SYNC_INTERVAL);
    }
  }
  function _pollPlaylistVersion() {
    fetch(PLAYLISTS_VERSION_PATH).then(function(r) { return r.json(); })
      .then(function(d) {
        if (typeof d.revision === 'number' && d.revision > _playlistRevision) {
          loadUserPlaylists().then(function() {
            /* If we're currently looking at the folder view, re-render to show updated playlist cards */
            if (!inPlaylist && currentPath === '') showFolderView();
          });
        }
      }).catch(function() { /* offline — ignore */ });
  }

  function updatePlaylistPill() { /* pill removed — no-op */ }

  /* ── optimistic UI helpers ── */
  function _snapshotPlaylists() {
    return JSON.parse(JSON.stringify(_userPlaylists));
  }
  function _restorePlaylists(snap) {
    _userPlaylists = snap;
    updatePlaylistPill();
  }

  /* ── playlist library panel (removed — playlists as pseudo-folders) ── */
  function openPlaylistLibrary() { /* removed */ }
  function closePlaylistLibrary() { /* removed */ }
  function renderPlaylistLibrary() { /* removed */ }

  function _resolvePlaylistItems(plId) {
    var pl = _userPlaylists.find(function(p) { return p.id === plId; });
    if (!pl) return null;
    /* Smart playlist: evaluate rules against allItems. */
    if (pl.smart && pl.smart.rules) {
      var resolvedSmart = _evaluateSmartPlaylist(pl, allItems, _userPlaylists, _savedFavorites);
      if (!resolvedSmart || resolvedSmart.length === 0) return null;
      return { pl: pl, resolved: resolvedSmart };
    }
    if (!pl.items || pl.items.length === 0) return null;
    var resolved = [];
    pl.items.forEach(function(rp) {
      var match = allItems.find(function(it) { return it.relative_path === rp; });
      if (match) resolved.push(match);
    });
    if (resolved.length === 0) return null;
    return { pl: pl, resolved: resolved };
  }

  /* Smart playlist evaluator: ported to webui/src/smartPlaylist.ts,
     bridged onto window (see main.ts) as window._evaluateSmartPlaylist —
     called here with the current allItems/_userPlaylists/_savedFavorites
     since the ported module takes them as explicit parameters instead of
     reading mutable globals (see that file's header comment). */

  /* Refresh smart playlist: re-evaluate locally and re-render. */
  function refreshSmartPlaylist(plId) {
    var pl = _userPlaylists.find(function(p) { return p.id === plId; });
    if (!pl || !pl.smart) return;
    /* If currently viewing this playlist, re-render in place. */
    if (typeof inPlaylist !== 'undefined' && inPlaylist && _currentPlaylistId === plId) {
      var resolved = _evaluateSmartPlaylist(pl, allItems, _userPlaylists, _savedFavorites);
      playlistItems = resolved;
      applyFilter();
      showToast('Aktualisiert: ' + resolved.length + ' Titel');
    } else {
      /* Just refresh the root view to update the count. */
      showFolderView();
      showToast('Intelligente Playlist aktualisiert');
    }
  }

  /* ── Smart Playlist Editor Modal ────────────────────────────────────── */
  /* SMART_FIELDS/SMART_OPS_BY_TYPE/SMART_OPS_ADDED_AT + _smartFieldType()/
     _smartOpsFor() ported to webui/src/smartPlaylist.ts, bridged onto
     window by main.ts — this fragment keeps calling the bare identifiers
     below (_smartRenderRuleRow), which resolve through the scope chain to
     window, unchanged. */

  function _smartRenderRuleRow(rule, idx) {
    var fieldOpts = SMART_FIELDS.map(function(f) {
      return '<option value="' + f.value + '"' + (rule.field === f.value ? ' selected' : '') + '>' + escHtml(f.label) + '</option>';
    }).join('');
    var ops = _smartOpsFor(rule.field || 'rating');
    var opOpts = ops.map(function(o) {
      return '<option value="' + o[0] + '"' + (rule.op === o[0] ? ' selected' : '') + '>' + escHtml(o[1]) + '</option>';
    }).join('');
    var valueInput;
    if (_smartFieldType(rule.field) === 'playlist') {
      var ownId = _smartEditorState ? _smartEditorState.id : null;
      var available = _userPlaylists.filter(function(p) { return !(p.smart && p.smart.rules) && p.id !== ownId; });
      if (available.length === 0) {
        valueInput = '<span class="smart-rule-empty">Keine regulären Playlists vorhanden</span>';
      } else {
        var plOpts = available.map(function(p) {
          var sel = Array.isArray(rule.value) && rule.value.indexOf(p.id) >= 0 ? ' checked' : '';
          return '<label class="smart-rule-pl-opt">' +
            '<input type="checkbox" class="smart-rule-value smart-rule-pl-cb" value="' + escHtml(p.id) + '"' + sel + '> ' +
            escHtml(p.name) +
            '</label>';
        }).join('');
        valueInput = '<div class="smart-rule-pl-list">' + plOpts + '</div>';
      }
    } else if (_smartFieldType(rule.field) === 'bool') {
      valueInput = '<select class="smart-rule-value">' +
        '<option value="true"' + (rule.value === true ? ' selected' : '') + '>ja</option>' +
        '<option value="false"' + (rule.value === false ? ' selected' : '') + '>nein</option>' +
        '</select>';
    } else if (rule.op === 'between') {
      var lo = Array.isArray(rule.value) ? rule.value[0] : '';
      var hi = Array.isArray(rule.value) ? rule.value[1] : '';
      valueInput = '<input type="number" class="smart-rule-value smart-rule-value-lo" value="' + escHtml(String(lo)) + '" placeholder="von">' +
                   '<input type="number" class="smart-rule-value smart-rule-value-hi" value="' + escHtml(String(hi)) + '" placeholder="bis">';
    } else {
      var t = _smartFieldType(rule.field) === 'number' ? 'number' : 'text';
      valueInput = '<input type="' + t + '" class="smart-rule-value" value="' + escHtml(String(rule.value == null ? '' : rule.value)) + '">';
    }
    return '<div class="smart-rule-row" data-idx="' + idx + '">' +
      '<select class="smart-rule-field">' + fieldOpts + '</select>' +
      '<select class="smart-rule-op">' + opOpts + '</select>' +
      valueInput +
      '<button type="button" class="smart-rule-del" title="Regel entfernen">×</button>' +
    '</div>';
  }

  var _smartEditorState = null;

"""
