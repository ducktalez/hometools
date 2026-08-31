"""JS fragment: search filter (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_search_filter_js() -> str:
    """Return the search filter section of the player JS."""
    return """  function globalSearch(needle) {
    needle = needle.toLowerCase();
    /* ── Phase 1: Folder / series matches ──
       Walk every relative_path, split into segments, collect each unique
       folder prefix whose *leaf* segment contains the needle.  For video
       libraries the top-level folder is the series title, so a search for
       "avatar" surfaces the series folder before the individual episodes. */
    var folderSeen = {};
    var folderMatches = [];
    var hiddenActive = (_effectiveThreshold > 0 && !showHidden);
    allItems.forEach(function(t) {
      if (hiddenActive) {
        var r = t.rating || 0;
        if (r > 0 && r < _effectiveThreshold) return;
      }
      var rp = t.relative_path || '';
      if (!rp) return;
      var parts = rp.split('/');
      /* Drop the file segment — only directory segments are folders. */
      parts.pop();
      var prefix = '';
      for (var i = 0; i < parts.length; i++) {
        var seg = parts[i];
        prefix = prefix ? (prefix + '/' + seg) : seg;
        if (folderSeen[prefix]) continue;
        var cleaned = (typeof cleanFolderName === 'function') ? cleanFolderName(seg) : seg;
        if (seg.toLowerCase().indexOf(needle) < 0 &&
            (cleaned || '').toLowerCase().indexOf(needle) < 0) continue;
        folderSeen[prefix] = true;
        folderMatches.push({
          path: prefix,
          name: seg,
          displayName: cleaned,
          depth: i,
          thumbnail_url: t.thumbnail_url || '',
          thumbnail_lg_url: t.thumbnail_lg_url || ''
        });
      }
    });
    /* Count items beneath each matched folder + favour top-level matches. */
    folderMatches.forEach(function(fm) {
      var p = fm.path + '/';
      var c = 0;
      for (var j = 0; j < allItems.length; j++) {
        var rp2 = allItems[j].relative_path || '';
        if (rp2.indexOf(p) === 0) c++;
      }
      fm.count = c;
    });
    folderMatches.sort(function(a, b) {
      if (a.depth !== b.depth) return a.depth - b.depth;   /* shallow first */
      if (b.count !== a.count) return b.count - a.count;   /* bigger first */
      return a.displayName.localeCompare(b.displayName);
    });

    /* ── Phase 2: Individual item matches ── */
    var results = allItems.filter(function(t) {
      var r = t.rating || 0;
      if (hiddenActive && r > 0 && r < _effectiveThreshold) return false;
      return (t.title || '').toLowerCase().indexOf(needle) >= 0 ||
             (t.artist || '').toLowerCase().indexOf(needle) >= 0 ||
             (t.relative_path || '').toLowerCase().indexOf(needle) >= 0;
    });
    _globalSearchActive = true;
    /* Hide folder grid, show track view with results */
    folderGrid.classList.add('view-hidden');
    trackView.classList.remove('view-hidden');
    filterBar.classList.add('view-hidden');
    playerBar.classList.remove('view-hidden');
    var totalCount = folderMatches.length + results.length;
    headerTitle.textContent = totalCount + ' Ergebnis' + (totalCount !== 1 ? 'se' : '');
    backBtn.classList.remove('disabled');
    playAllBtn.classList.add('disabled');
    var trackCountLabel = results.length + ' ' + (results.length !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN);
    if (folderMatches.length) {
      trackCountLabel = folderMatches.length + ' Ordner · ' + trackCountLabel;
    }
    trackCount.textContent = trackCountLabel;
    /* Hide recently played */
    var rs = document.getElementById('recent-section');
    if (rs) rs.hidden = true;
    /* Use search results as current playlist so next/prev works */
    playlistItems = results;
    filteredItems = results;
    inPlaylist = true;
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
      var thumbSrc = fm.thumbnail_url || FILE_PLACEHOLDER;
      var parentDir = fm.path.lastIndexOf('/') > 0 ? fm.path.substring(0, fm.path.lastIndexOf('/')) : '';
      li.innerHTML = '<div class="track-number">' + IC_FOLDER_PLAY + '</div>' +
        '<div class="track-thumb-wrap"><img class="track-thumb" src="' + escHtml(thumbSrc) + '" loading="lazy"></div>' +
        '<div class="track-info">' +
          '<div class="track-title">' + escHtml(fm.displayName || fm.name) +
            ' <span class="search-folder-count">(' + fm.count + ')</span></div>' +
          '<div class="track-artist">Ordner</div>' +
          (parentDir ? '<div class="search-result-folder">' + escHtml(parentDir) + '</div>' : '') +
        '</div>';
      li.addEventListener('click', function() { navigateToSearchFolder(fm.path); });
      trackList.appendChild(li);
    });
    results.forEach(function(t, i) {
      var li = document.createElement('li');
      li.className = 'track-item';
      li.setAttribute('data-index', i);
      var thumbSrc = t.thumbnail_url || FILE_PLACEHOLDER;
      var ratingBar = t.rating > 0 ? '<div class="rating-bar" style="width:' + (t.rating / 5 * 100) + '%"></div>' : '';
      /* Extract folder path for context */
      var folderPath = '';
      var lastSlash = (t.relative_path || '').lastIndexOf('/');
      if (lastSlash > 0) folderPath = t.relative_path.substring(0, lastSlash);
      li.innerHTML = '<div class="track-number">' + (i + 1) + '</div>' +
        '<div class="track-thumb-wrap"><img class="track-thumb" src="' + escHtml(thumbSrc) + '" loading="lazy">' + ratingBar + '</div>' +
        '<div class="track-info">' +
          '<div class="track-title">' + escHtml(t.title || t.relative_path) + '</div>' +
          '<div class="track-artist">' + escHtml(t.artist || '') + '</div>' +
          (folderPath ? '<div class="search-result-folder">' + escHtml(folderPath) + '</div>' : '') +
        '</div>';
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
  function _collectPlaylistGenres() {
    var genres = {};
    (playlistItems || []).forEach(function(t) { if (t.genre) genres[t.genre] = true; });
    return Object.keys(genres).sort();
  }

  function updateFilterChips() {
    if (filterCombinedBtn) {
      var activeCount = (filterRating > 0 ? 1 : 0) + (filterFav ? 1 : 0) + (filterGenre ? 1 : 0);
      filterCombinedBtn.innerHTML = IC_FILTER + ' Filtern' + (activeCount ? ' (' + activeCount + ')' : '');
      filterCombinedBtn.classList.toggle('active', activeCount > 0);
      filterCombinedBtn.title = activeCount
        ? activeCount + ' Filter aktiv \u2014 klicken zum Anpassen'
        : 'Filtern (Bewertung, Favoriten, Genre)';
    }
    /* Keep an already-open popover's contents (star state, genre <select>)
       in sync — e.g. after navigating into a folder whose genre list differs. */
    if (document.getElementById('ht-filter-popover')) _renderFilterPopoverBody();
    if (filterHiddenBtn) {
      if (_effectiveThreshold > 0) {
        var _hiddenCount = playlistItems.filter(function(t) {
          var r = t.rating || 0; return r > 0 && r < _effectiveThreshold;
        }).length;
        var _totalCount = playlistItems.length;
        filterHiddenBtn.style.display = '';
        /* Always render "(N/M)" so the button width stays stable — prevents layout shift on click */
        filterHiddenBtn.innerHTML = IC_EYE + ' Ausgeblendet (' + _hiddenCount + '/' + _totalCount + ')';
        filterHiddenBtn.classList.toggle('active', !showHidden);
        filterHiddenBtn.title = showHidden
          ? 'Ausgeblendete Songs sichtbar \u2014 klicken zum Verstecken'
          : 'Ausgeblendete Songs einblenden';
      } else {
        filterHiddenBtn.style.display = 'none';
      }
    }
  }

  /* ── Combined "Filtern" popover (Bewertung + Favorit + Genre) ──────────
     Mirrors the generic _openCtxMenu() pattern (_library_tools.py) —
     fixed-position card anchored to the trigger button, closes on outside
     click / Escape — but hosts interactive controls (star buttons,
     checkbox, <select>) instead of a static action list, so it gets its
     own small open/close/wire trio here rather than reusing _openCtxMenu's
     items schema (label+onClick only). */
  function _filterPopoverBodyHtml() {
    var genreList = _collectPlaylistGenres();
    var starsHtml = '';
    for (var i = 1; i <= 5; i++) {
      starsHtml += '<button type="button" class="filter-popover-star' + (i <= filterRating ? ' active' : '') +
        '" data-star="' + i + '" title="' + i + (i === 1 ? '+ Stern' : '+ Sterne') + '">' +
        (i <= filterRating ? IC_STAR_FILLED : IC_STAR_EMPTY) + '</button>';
    }
    var genreSectionHtml = genreList.length
      ? '<div class="filter-popover-section">' +
          '<div class="filter-popover-label">Genre</div>' +
          '<select class="filter-popover-genre-select" id="filter-popover-genre-select">' +
            '<option value="">Alle Genres</option>' +
            genreList.map(function(g) {
              return '<option value="' + escHtml(g) + '"' + (g === filterGenre ? ' selected' : '') + '>' + escHtml(g) + '</option>';
            }).join('') +
          '</select>' +
        '</div>'
      : '';
    return (
      '<div class="filter-popover-section">' +
        '<div class="filter-popover-label">Bewertung</div>' +
        '<div class="filter-popover-stars">' + starsHtml + '</div>' +
      '</div>' +
      '<div class="filter-popover-section">' +
        '<label class="filter-popover-toggle">' +
          '<input type="checkbox" id="filter-popover-fav"' + (filterFav ? ' checked' : '') + '> Nur Favoriten' +
        '</label>' +
      '</div>' +
      genreSectionHtml +
      '<button type="button" class="filter-popover-reset" id="filter-popover-reset">Zur\u00fccksetzen</button>'
    );
  }

  function _wireFilterPopoverBody(pop) {
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

  function applyFilter() {
    var needle = searchInput.value.trim().toLowerCase();
    var sortBy = sortField.value;
    /* Safety net: always strip locally-deleted paths regardless of how
       playlistItems was last set (stale closure, folder-order callback, etc.) */
    var items = Object.keys(_locallyDeletedPaths).length
      ? playlistItems.filter(function(it) { return !_locallyDeletedPaths[it.relative_path]; })
      : playlistItems;

    if (DEBUG_FILTER) {
      /* ── Debug mode: annotate items with reasons instead of removing ──
         showHidden=true  → rating-below-threshold items get _hiddenShown (grayed, same UX as normal mode)
         showHidden=false → rating-below-threshold items get _debugReason (visible with filter-reason overlay) */
      items = items.map(function(t) {
        var r = t.rating || 0;
        /* Rating threshold: when showHidden=true, gray items in-place (don't annotate as debug-filtered) */
        if (_effectiveThreshold > 0 && r > 0 && r < _effectiveThreshold) {
          var hClone = {}; for (var k in t) { if (t.hasOwnProperty(k)) hClone[k] = t[k]; }
          if (showHidden) {
            hClone._hiddenShown = true;
            return hClone;
          } else {
            hClone._debugReason = 'Rating ' + r + '\\u2605 < Schwelle ' + _effectiveThreshold;
            return hClone;
          }
        }
        var reasons = [];
        if (filterRating > 0 && (r < filterRating)) {
          reasons.push('Quick-Filter: Rating < ' + filterRating + '\\u2605');
        }
        if (filterFav && !_savedFavorites[t.relative_path]) {
          reasons.push('Kein Favorit');
        }
        if (filterGenre && t.genre !== filterGenre) {
          reasons.push('Genre \\u2260 ' + filterGenre);
        }
        if (reasons.length > 0) {
          /* Clone the item so we don't mutate the original in playlistItems */
          var clone = {};
          for (var k in t) { if (t.hasOwnProperty(k)) clone[k] = t[k]; }
          clone._debugReason = reasons.join(' | ');
          return clone;
        }
        return t;
      });
      /* Text search always filters even in debug mode */
      if (needle) {
        items = items.filter(function(t) {
          return t.title.toLowerCase().indexOf(needle) >= 0 ||
                 t.artist.toLowerCase().indexOf(needle) >= 0 ||
                 t.relative_path.toLowerCase().indexOf(needle) >= 0;
        });
      }
    } else {
      /* ── Normal mode ── */
      /* Effective threshold: tracks with rating < threshold are "ausgeblendet".
         Unrated tracks (rating 0) are always shown regardless of threshold.
         showHidden=false  → hidden songs filtered out entirely.
         showHidden=true   → hidden songs kept at their natural position, grayed
                             out so the full list is visible. */
      if (_effectiveThreshold > 0) {
        if (!showHidden) {
          items = items.filter(function(t) {
            var r = t.rating || 0; return r === 0 || r >= _effectiveThreshold;
          });
        } else {
          /* Mark hidden items in-place — they stay at their sorted position */
          items = items.map(function(t) {
            var r = t.rating || 0;
            if (r > 0 && r < _effectiveThreshold) {
              var clone = {}; for (var k in t) { if (t.hasOwnProperty(k)) clone[k] = t[k]; }
              clone._hiddenShown = true;
              return clone;
            }
            return t;
          });
        }
      }
      if (needle) {
        items = items.filter(function(t) {
          return t.title.toLowerCase().indexOf(needle) >= 0 ||
                 t.artist.toLowerCase().indexOf(needle) >= 0 ||
                 t.relative_path.toLowerCase().indexOf(needle) >= 0;
        });
      }
      /* Quick-filters (never affect hidden-shown items — they are already grayed) */
      if (filterRating > 0) {
        items = items.filter(function(t) { return t._hiddenShown || (t.rating || 0) >= filterRating; });
      }
      if (filterFav) {
        items = items.filter(function(t) { return t._hiddenShown || !!_savedFavorites[t.relative_path]; });
      }
      if (filterGenre) {
        items = items.filter(function(t) { return t._hiddenShown || t.genre === filterGenre; });
      }
    }
    items = items.slice().sort(function(a, b) {
      var sa = a.season || 0, sb = b.season || 0;
      var ea = a.episode || 0, eb = b.episode || 0;
      if (sortBy === 'custom') {
        /* In playlist context: preserve playlist order (no sort).
           In filesystem context: sort by rating desc, title asc as tiebreaker. */
        if (_currentPlaylistId) return 0;
        var ra = a.rating || 0, rb = b.rating || 0;
        if (ra !== rb) return rb - ra;
        return a.title.localeCompare(b.title);
      }
      if (sortBy === 'recent') {
        /* newest first by mtime, title as tiebreaker */
        var ma = a.mtime || 0, mb = b.mtime || 0;
        if (ma !== mb) return mb - ma;
        return a.title.localeCompare(b.title);
      }
      if (sortBy === 'title') {
        /* Series-aware title sort: prefer season/episode when present */
        if (sa > 0 || sb > 0) {
          if (sa !== sb) return sa - sb;
          if (ea !== eb) return ea - eb;
        }
        return a.title.localeCompare(b.title) || a.relative_path.localeCompare(b.relative_path);
      }
      if (sortBy === 'path') return a.relative_path.localeCompare(b.relative_path);
      /* artist sort: group by folder, then season/episode within */
      var ad = a.artist.localeCompare(b.artist);
      if (ad !== 0) return ad;
      if (sa !== sb) return sa - sb;
      if (ea !== eb) return ea - eb;
      return a.title.localeCompare(b.title);
    });
    renderTracks(items);
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
    var end = Math.min(_renderBatchOffset + _RENDER_BATCH_SIZE, _renderAllItems.length);
    if (end <= _renderBatchOffset) { _stopRenderObserver(); return; }
    var showOrig = _anyToolActive();
    /* BPM "calculate" affordance (yellow-glow clickable "?") is gated by the
       Tools-panel "BPM berechnen" toggle — see _track_render.py::_applyToolState. */
    var bpmCalcEnabled = !!(_toolState.active && _toolState.bpmCalc);
    var html = '';
    for (var i = _renderBatchOffset; i < end; i++) {
      var t = _renderAllItems[i];
      var idx = _renderRealIdxMap[i];
      /* missing episode placeholder */
      if (t._missing) {
        var seLabel = 'S' + String(t.season).padStart(2, '0') + 'E' + String(t.episode).padStart(2, '0');
        html += '<li class="track-item missing-episode" aria-disabled="true">' +
          '<span class="track-num"><span class="num-text">' + seLabel + '</span></span>' +
          '<div class="track-info"><div class="track-title">Folge fehlt</div>' +
          '<div class="track-artist">' + seLabel + ' \\u2014 nicht in der Bibliothek</div></div></li>';
        continue;
      }
      /* debug-filtered placeholder */
      if (t._debugReason) {
        var dbgTitle = showOrig ? filenameFromPath(t.relative_path) : t.title;
        var dbgSub = t.artist || t.relative_path;
        var dbgThumb = t.thumbnail_url || FILE_PLACEHOLDER;
        var dbgRating = t.rating > 0 ? '<div class="rating-bar" style="width:' + (t.rating / 5 * 100) + '%"></div>' : '';
        html += '<li class="track-item debug-filtered">' +
          '<span class="track-num"><span class="num-text">\\u00b7</span></span>' +
          '<div class="thumb-wrap track-thumb-wrap">' +
          '<img class="track-thumb" src="' + escHtml(dbgThumb) + '" alt="" loading="lazy">' +
          dbgRating + '</div>' +
          '<div class="track-info">' +
            '<div class="track-title">' + escHtml(dbgTitle) + '</div>' +
            '<div class="track-artist">' + escHtml(dbgSub) + '</div>' +
            '<div class="debug-reason">' + escHtml(t._debugReason) + '</div>' +
          '</div></li>';
        continue;
      }
      /* normal track row */
      var isSeries = (t.season || 0) > 0;
      var numLabel = isSeries
        ? 'S' + String(t.season).padStart(2, '0') + 'E' + String(t.episode).padStart(2, '0')
        : String(idx + 1);
      var displayTitle = showOrig ? filenameFromPath(t.relative_path) : t.title;
      var subtitle = t.artist || t.relative_path;
      var extraCls = (idx === currentIndex ? ' active' : '') + (t._hiddenShown ? ' track-item--hidden-shown' : '');
      var thumbSrc = t.thumbnail_url || FILE_PLACEHOLDER;
      var ratingBar = t.rating > 0 ? '<div class="rating-bar" style="width:' + (t.rating / 5 * 100) + '%"></div>' : '';
      var convertBadge = needsConversion(t.relative_path) ? '<span class="convert-badge" title="Wird on-the-fly konvertiert">\\u26A1</span>' : '';
      var isDupe = _dupePaths && _dupePaths.has(t.relative_path);
      var dupeSafe = isDupe && _dupeSafety && _dupeSafety[t.relative_path];
      var dupeDeleteCls = isDupe ? (dupeSafe ? ' track-delete-btn--safe' : ' track-delete-btn--warn') : '';
      var dupeDeleteTitle = isDupe
        ? (dupeSafe ? 'Duplikat l\\u00f6schen (Gr\\u00f6\\u00dfe + L\\u00e4nge nahezu identisch)'
                    : 'Duplikat l\\u00f6schen \\u2014 Vorsicht: Gr\\u00f6\\u00dfe oder L\\u00e4nge weicht ab!')
        : '';
      var dupeBadge = isDupe ? '<span class="dupe-badge" title="Duplikat erkannt">Duplikat' +
        '<button class="track-delete-btn' + dupeDeleteCls + '" data-index="' + idx +
        '" title="' + escHtml(dupeDeleteTitle) + '">' + IC_TRASH + '</button></span>' : '';
      /* Table/detail view (audio only): title + artist become directly
         editable while a tool is active, and duration/genre get their own
         columns (hidden by CSS outside table-mode). */
      var tableEditable = (trackViewMode === 'table' && !isVideoMode && METADATA_EDIT_ENABLED && showOrig);
      var editAttrs = tableEditable
        ? ' contenteditable="true" spellcheck="false" data-relative-path="' + escHtml(t.relative_path || '') + '"'
        : '';
      /* BPM pill (audio only) — same markup serves both the always-visible
         list-view pill and the table-view column (CSS alone repositions it
         via .track-bpm-cell); see webui/src/metricPill.ts + docs/architecture.md
         "Metric Pill Architecture" for the generalized design (future fields:
         genre/mood/key can follow the same pattern). */
      var bpmPillHtml = (isVideoMode || typeof window.renderBpmPill !== 'function')
        ? ''
        : '<span class="track-bpm-cell">' + window.renderBpmPill(t.bpm, BPM_MIN, BPM_MAX,
            { index: idx, relativePath: t.relative_path, calcEnabled: bpmCalcEnabled }) + '</span>';
      html += '<li class="track-item' + extraCls +
        '" data-index="' + idx + '">' +
        '<span class="track-num"><span class="num-text">' + numLabel + '</span></span>' +
        '<div class="thumb-wrap track-thumb-wrap">' +
        '<img class="track-thumb" src="' + escHtml(thumbSrc) + '" alt="" loading="lazy">' +
        '<button class="track-play-btn" data-index="' + idx + '" title="Abspielen">' + IC_FOLDER_PLAY + '</button>' +
        ratingBar + '</div>' +
        '<div class="track-info">' +
          '<div class="track-title"><span class="track-title-text"' + (tableEditable ? editAttrs + ' data-field="title"' : '') + '>' + escHtml(displayTitle) + '</span>' + convertBadge + dupeBadge + '</div>' +
          '<div class="track-artist"' + (tableEditable ? editAttrs + ' data-field="artist"' : '') + '>' + escHtml(subtitle) + '</div>' +
        '</div>' +
        bpmPillHtml +
        '<span class="track-duration-cell">' + (t.duration ? fmtTime(t.duration) : '') + '</span>' +
        '<span class="track-genre-cell">' + escHtml(t.genre || '') + '</span>' +
        '<button class="track-dl-btn" data-stream-url="' + escHtml(t.stream_url) +
          '" data-title="' + escHtml(t.title) +
          '" data-artist="' + escHtml(t.artist || '') +
          '" data-relative-path="' + escHtml(t.relative_path || '') +
          '" data-thumbnail-url="' + escHtml(t.thumbnail_url || '') +
          '" data-media-type="' + escHtml(t.media_type || ITEM_NOUN) + '" title="Download">' + IC_DL + '</button>' +
        '<button class="track-pin-btn" data-relative-path="' + escHtml(t.relative_path || '') +
          '" data-title="' + escHtml(t.title) +
          '" title="Favorit">' + IC_PIN + '</button>' +
        (METADATA_EDIT_ENABLED ? '<button class="track-edit-btn" data-index="' + idx + '" title="Bearbeiten">' + IC_EDIT + '</button>' : '') +
        (PLAYLISTS_ENABLED ? '<button class="track-playlist-btn" data-relative-path="' + escHtml(t.relative_path || '') + '" title="Zur Playlist hinzuf\\u00fcgen">' + IC_PLAYLIST + '</button>' : '') +
        '<button class="track-queue-btn" data-relative-path="' + escHtml(t.relative_path || '') + '" data-index="' + idx + '" title="Zur Warteschlange hinzuf\\u00fcgen">' + IC_QUEUE + '</button>' +
        '<button class="track-kebab-btn" data-relative-path="' + escHtml(t.relative_path || '') +
          '" data-title="' + escHtml(t.title) + '" title="Mehr Optionen">' + IC_DOTS + '</button>' +
        '<button class="track-reveal-btn" data-relative-path="' + escHtml(t.relative_path || '') +
          '" data-title="' + escHtml(t.title) + '" title="Im Explorer anzeigen">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>' +
        '</button>' +
        renderInlineRating(t, idx) +
        renderMoveWidget(t, idx) +
        '</li>';
    }
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
    /* Synchronously render batches until the item at filteredItems index idx
       is present in the DOM.  Needed before markActive / scrollIntoView. */
    if (!_renderAllItems.length || idx < 0) return;
    /* Find the display index for filteredItems index idx */
    var displayIdx = -1;
    for (var k = 0; k < _renderRealIdxMap.length; k++) {
      if (_renderRealIdxMap[k] === idx) { displayIdx = k; break; }
    }
    if (displayIdx < 0 || displayIdx < _renderBatchOffset) return;
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
    var lastSlash = rp.lastIndexOf('/');
    var folder = lastSlash >= 0 ? rp.substring(0, lastSlash) : '';
    if (inPlaylist && currentPath === folder) {
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

    var allF = _getAllFolders();
    var curFolder = _currentFolderOf(t);
    var kebabHtml =
      '<button class="player-bar-kebab-btn" id="player-bar-kebab" ' +
        'data-relative-path="' + escHtml(t.relative_path || '') + '" ' +
        'data-title="' + escHtml(t.title || '') + '" ' +
        'title="Mehr Optionen">' + IC_DOTS + '</button>';

    var moveHtml = '';
    if (allF.length) {
      moveHtml = '<select class="player-bar-move-select" id="player-bar-move-select">' +
        '<option value="" disabled selected>Verschieben\u2026</option>';
      allF.forEach(function(f) {
        moveHtml += '<option value="' + escHtml(f) + '"' +
          (f === curFolder ? ' disabled' : '') + '>' + escHtml(f) + '</option>';
      });
      moveHtml += '</select>';
    }
    var trashHtml =
      '<button class="player-bar-trash-btn" id="player-bar-trash" title="Datei l\\u00f6schen">' +
        IC_TRASH + '</button>';

    /* Check current tool state */
    var inMoverMode = document.body.classList.contains('tool-show-file-mover');
    if (inMoverMode) {
      playerBarActions.innerHTML =
        (moveHtml ? '<div class="player-bar-actions-row">' + moveHtml + '</div>' : '') +
        '<div class="player-bar-actions-row">' + trashHtml + kebabHtml + '</div>';
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
    } else {
      playerBarActions.innerHTML = kebabHtml;
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
        var inQ = _userQueue.some(function(q) { return q.relative_path === qrp; });
        if (inQ) {
          var qi = _userQueue.findIndex(function(q) { return q.relative_path === qrp; });
          if (qi >= 0) removeFromQueue(qi);
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
