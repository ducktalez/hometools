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
      var resolvedSmart = _evaluateSmartPlaylist(pl);
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

  /* ── Smart playlist evaluator (mirror of Python smart_playlists.py) ── */
  var _smartRegexCache = Object.create(null);
  function _smartCompile(pat) {
    if (typeof pat !== 'string' || pat.length > 256) return null;
    if (pat in _smartRegexCache) return _smartRegexCache[pat];
    var rx = null;
    try { rx = new RegExp(pat, 'i'); } catch (e) { rx = null; }
    _smartRegexCache[pat] = rx;
    return rx;
  }
  function _smartGetField(it, field) {
    if (field === 'added_at') return Number(it.mtime || 0);
    if (field === 'is_favorite') {
      return !!(_savedFavorites && _savedFavorites[it.relative_path]);
    }
    if (field === 'in_folder') {
      var rp = String(it.relative_path || '');
      var i = rp.lastIndexOf('/');
      return i >= 0 ? rp.substring(0, i) : '';
    }
    return it[field];
  }
  function _smartEvalRule(rule, it, plIndex) {
    try {
      var field = String(rule.field || '');
      var op = String(rule.op || '');
      var value = rule.value;
      if (field === 'in_playlist') {
        var rp = String(it.relative_path || '');
        var ids = Array.isArray(value) ? value : [value];
        var hits = ids.map(function(pid) {
          var set = plIndex[String(pid)];
          return !!(set && set[rp]);
        });
        if (op === 'any_of') return hits.some(function(h) { return h; });
        if (op === 'all_of') return hits.length > 0 && hits.every(function(h) { return h; });
        if (op === 'none_of') return !hits.some(function(h) { return h; });
        return false;
      }
      var actual = _smartGetField(it, field);
      if (field === 'added_at') {
        var ts = Number(actual);
        var v = Number(value);
        if (!isFinite(ts) || !isFinite(v) || ts <= 0) return false;
        if (op === 'within_days') return (Date.now() / 1000 - ts) <= v * 86400;
        if (op === 'before')      return ts < v;
        if (op === 'after')       return ts > v;
        return false;
      }
      var na, nv;
      switch (op) {
        case 'eq':
          if (typeof actual === 'string' && typeof value === 'string') {
            return actual.toLowerCase() === value.toLowerCase();
          }
          return actual === value;
        case 'contains':
          if (actual == null || value == null) return false;
          return String(actual).toLowerCase().indexOf(String(value).toLowerCase()) >= 0;
        case 'starts_with':
          if (actual == null || value == null) return false;
          return String(actual).toLowerCase().indexOf(String(value).toLowerCase()) === 0;
        case 'matches':
          var rx = _smartCompile(String(value || ''));
          return !!(rx && rx.test(String(actual == null ? '' : actual)));
        case 'gte':
          na = Number(actual); nv = Number(value);
          return isFinite(na) && isFinite(nv) && na >= nv;
        case 'lte':
          na = Number(actual); nv = Number(value);
          return isFinite(na) && isFinite(nv) && na <= nv;
        case 'between':
          if (!Array.isArray(value) || value.length !== 2) return false;
          var lo = Number(value[0]), hi = Number(value[1]);
          if (lo > hi) { var t = lo; lo = hi; hi = t; }
          na = Number(actual);
          return isFinite(na) && lo <= na && na <= hi;
        case 'in':
          if (!Array.isArray(value)) return false;
          return value.some(function(v) {
            if (typeof actual === 'string' && typeof v === 'string') {
              return actual.toLowerCase() === v.toLowerCase();
            }
            return actual === v;
          });
        default:
          return false;
      }
    } catch (e) { return false; }
  }
  function _buildSmartPlIndex() {
    var idx = Object.create(null);
    _userPlaylists.forEach(function(pl) {
      if (pl.smart && pl.smart.rules) return; /* skip smart, no cascades */
      var pid = String(pl.id || '');
      if (!pid) return;
      var set = Object.create(null);
      (pl.items || []).forEach(function(rp) { set[String(rp)] = true; });
      idx[pid] = set;
    });
    return idx;
  }
  function _smartApplySort(items, sortKey) {
    if (!sortKey) return items;
    var arr = items.slice();
    if (sortKey === 'random') {
      for (var i = arr.length - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
      }
      return arr;
    }
    var desc = sortKey.indexOf('_desc') === sortKey.length - 5 && sortKey.length > 5;
    var base = desc ? sortKey.substring(0, sortKey.length - 5) : sortKey;
    var keyFn = null;
    if (base === 'title')    keyFn = function(x) { return String(x.title || '').toLowerCase(); };
    if (base === 'rating')   keyFn = function(x) { return Number(x.rating || 0); };
    if (base === 'added_at') keyFn = function(x) { return Number(x.mtime || 0); };
    if (base === 'duration') keyFn = function(x) { return Number(x.duration || 0); };
    if (!keyFn) return items;
    arr.sort(function(a, b) {
      var ka = keyFn(a), kb = keyFn(b);
      if (ka < kb) return desc ?  1 : -1;
      if (ka > kb) return desc ? -1 :  1;
      return 0;
    });
    return arr;
  }
  function _evaluateSmartPlaylist(pl) {
    try {
      var smart = pl && pl.smart;
      if (!smart || !Array.isArray(smart.rules) || smart.rules.length === 0) return [];
      var match = (smart.match === 'any') ? 'any' : 'all';
      var idx = _buildSmartPlIndex();
      var matched = [];
      allItems.forEach(function(it) {
        var results = smart.rules.map(function(r) {
          return _smartEvalRule(r, it, idx);
        });
        var keep = (match === 'all')
          ? results.every(function(v) { return v; })
          : results.some(function(v) { return v; });
        if (keep) matched.push(it);
      });
      if (smart.sort) matched = _smartApplySort(matched, String(smart.sort));
      if (typeof smart.limit === 'number' && smart.limit > 0) {
        matched = matched.slice(0, smart.limit);
      }
      return matched;
    } catch (e) { return []; }
  }

  /* Refresh smart playlist: re-evaluate locally and re-render. */
  function refreshSmartPlaylist(plId) {
    var pl = _userPlaylists.find(function(p) { return p.id === plId; });
    if (!pl || !pl.smart) return;
    /* If currently viewing this playlist, re-render in place. */
    if (typeof inPlaylist !== 'undefined' && inPlaylist && _currentPlaylistId === plId) {
      var resolved = _evaluateSmartPlaylist(pl);
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
  var SMART_FIELDS = [
    { value: 'rating',        label: 'Bewertung',     type: 'number' },
    { value: 'genre',         label: 'Genre',         type: 'text'   },
    { value: 'artist',        label: 'Artist',        type: 'text'   },
    { value: 'title',         label: 'Titel',         type: 'text'   },
    { value: 'relative_path', label: 'Dateipfad',     type: 'text'   },
    { value: 'language',      label: 'Sprache',       type: 'text'   },
    { value: 'added_at',      label: 'Hinzugefügt',   type: 'number' },
    { value: 'duration',      label: 'Dauer (Sek.)',  type: 'number' },
    { value: 'in_playlist',   label: 'In Playlist',   type: 'playlist' },
    { value: 'is_favorite',   label: 'Favorit',       type: 'bool'   }
  ];
  var SMART_OPS_BY_TYPE = {
    'number':   [['gte','≥'], ['lte','≤'], ['eq','='], ['between','zwischen']],
    'text':     [['contains','enthält'], ['eq','='], ['starts_with','beginnt mit'], ['matches','regex']],
    'bool':     [['eq','=']],
    'playlist': [['any_of','in einer von'], ['all_of','in allen von'], ['none_of','in keiner von']]
  };
  /* added_at gets its own op set (overrides number defaults) */
  var SMART_OPS_ADDED_AT = [['within_days','letzte N Tage']];

  function _smartFieldType(field) {
    var f = SMART_FIELDS.find(function(x) { return x.value === field; });
    return f ? f.type : 'text';
  }
  function _smartOpsFor(field) {
    if (field === 'added_at') return SMART_OPS_ADDED_AT;
    return SMART_OPS_BY_TYPE[_smartFieldType(field)] || SMART_OPS_BY_TYPE['text'];
  }

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
