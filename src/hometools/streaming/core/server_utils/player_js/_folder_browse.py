"""JS fragment: folder browse (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_folder_browse_js() -> str:
    """Return the folder browse section of the player JS."""
    return """  function showFolderView() {
    destroyPlaylistDragDrop();
    closeLangPicker();
    inPlaylist = false;
    _currentPlaylistId = '';
    _globalSearchActive = false;
    _moveGhosts = {};  /* clear move ghosts when leaving playlist */
    /* Clear refresh-info when leaving playlist view */
    var rInfo = document.getElementById('refresh-info');
    if (rInfo) rInfo.textContent = '';
    var c = contentsAt(currentPath);
    var isRoot = !currentPath;
    var showOrigNames = _anyToolActive();

    /* empty library — still the folder-grid view, so the global search bar
       follows the same "folder-grid visible" rule as the normal branch below. */
    if (c.folders.length === 0 && c.files.length === 0) {
      folderGrid.classList.remove('view-hidden');
      trackView.classList.add('view-hidden');
      filterBar.classList.add('view-hidden');
      playAllBtn.classList.add('disabled');
      headerTitle.textContent = currentPath ? leafName(currentPath) : originalTitle;
      backBtn.classList.toggle('disabled', !currentPath);
      if (!player.currentSrc) playerBar.classList.add('view-hidden');
      folderGrid.innerHTML = '<div class="empty-hint">No items found. Run a sync first.</div>';
      trackCount.textContent = '';
      if (allItems.length > 0) initGlobalSearch(); else _hideGlobalSearch();
      renderBreadcrumb();
      applyViewMode();
      if (typeof _router !== 'undefined') _router.update();
      return;
    }

    /* leaf folder (no sub-folders) → playlist. Global search bar is a
       folder-grid-only control (see docs/IMPLEMENTATION_PLAN.md
       "UI-Template-Vereinheitlichung" Phase 2) — showPlaylist() hides it,
       same as showUserPlaylistView() does for user/smart playlists, so
       every track-list view behaves identically regardless of entry point. */
    if (c.folders.length === 0) {
      showPlaylist(c.files, false);
      return;
    }

    folderGrid.classList.remove('view-hidden');
    trackView.classList.add('view-hidden');
    filterBar.classList.add('view-hidden');
    if (!player.currentSrc) playerBar.classList.add('view-hidden');
    /* Global search bar — folder-grid view only, visible whenever the
       catalog is loaded (see comment above the leaf-folder branch). */
    if (allItems.length > 0) initGlobalSearch(); else _hideGlobalSearch();

     headerTitle.textContent = currentPath ? leafName(currentPath) : originalTitle;
    backBtn.classList.toggle('disabled', !currentPath);
    playAllBtn.classList.remove('disabled');

    var label = c.folders.length + ' folder' + (c.folders.length !== 1 ? 's' : '');
    if (c.files.length > 0) {
      label += ', ' + c.files.length + ' ' + (c.files.length !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN);
    }
    trackCount.textContent = label;

    var html = '';

    /* Compact tools row — only on root: Neue Playlist | Titel | Downloaded | reload.
       Video server omits playlist tools (Neue Playlist / Intelligente Playlist / Titel)
       since playlists are an audio-only feature there. */
    var _toolsRowParts = [];
    var _isVideo = (ITEM_NOUN === 'video');
    if (isRoot && PLAYLISTS_ENABLED && !_isVideo) {
      _toolsRowParts.push(
        '<button type="button" class="tools-row-item playlist-new-card" id="playlist-new-card">' +
          '<span class="tools-row-icon">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" style="width:18px;height:18px"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>' +
          '</span>' +
          '<span class="tools-row-label">Neue Playlist\u2026</span>' +
          '<span class="tools-row-count"></span>' +
        '</button>'
      );
      _toolsRowParts.push(
        '<button type="button" class="tools-row-item playlist-new-card smart-new-card" id="smart-playlist-new-card"' +
          ' title="Intelligente Playlist erstellen">' +
          '<span class="tools-row-icon">' + IC_SMART_PLAYLIST + '</span>' +
          '<span class="tools-row-label">Intelligente Playlist\u2026</span>' +
          '<span class="tools-row-count"></span>' +
        '</button>'
      );
      /* "Titel" — flat list of all library tracks (allItems). */
      _toolsRowParts.push(
        '<button type="button" class="tools-row-item playlist-folder-card" id="all-titles-card"' +
          ' data-playlist-id="__alltitles__" title="Zeigt alle Titel der Ordner als Liste an">' +
          '<span class="tools-row-icon">' + IC_PLAYLIST + '</span>' +
          '<span class="tools-row-label">Titel</span>' +
          (allItems.length > 0 ? '<span class="tools-row-count">' + allItems.length + '</span>' : '') +
        '</button>'
      );
    }
    if (isRoot && OFFLINE_ENABLED) {
      _toolsRowParts.push(
        '<button type="button" class="tools-row-item offline-folder-card" id="offline-folder-card">' +
          '<span class="tools-row-icon">' + IC_DL + '</span>' +
          '<span class="tools-row-label">Downloaded</span>' +
          '<span class="tools-row-count" id="offline-folder-count">0</span>' +
        '</button>'
      );
    }
    /* "Neu laden" icon-only square button — always visible on root, right-most */
    if (isRoot) {
      _toolsRowParts.push(
        '<button type="button" class="tools-row-item refresh-catalog-card" id="refresh-catalog-card" title="Neu laden">' +
          '<span class="tools-row-icon">' + IC_REFRESH + '</span>' +
        '</button>'
      );
    }
    if (_toolsRowParts.length > 0) {
      html += '<div class="playlist-tools-row">' + _toolsRowParts.join('') + '</div>';
    }

    /* Auto-Favorites playlist card — only on root when favorites exist */
    if (isRoot && PLAYLISTS_ENABLED) {
      var _favCount = allItems.filter(function(t) { return !!_savedFavorites[t.relative_path]; }).length;
      if (_favCount > 0) {
        html += '<div class="folder-card playlist-folder-card" data-playlist-id="__favorites__">' +
          '<div class="thumb-wrap playlist-thumb-wrap">' +
            '<div class="folder-thumb playlist-folder-icon">' + IC_STAR + '</div>' +
            '<button class="playlist-cover-play-btn" title="Abspielen">' + IC_FOLDER_PLAY + '</button>' +
          '</div>' +
          '<div class="folder-name">Favoriten</div>' +
          '<div class="folder-count">' + _favCount + ' Titel</div>' +
        '</div>';
      }
    }

    /* Playlist pseudo-folder cards — only on root, only when playlists enabled.
       All modification actions (Umbenennen, Regeln bearbeiten, Aktualisieren,
       Löschen) live behind a single top-right kebab menu — consistent with
       every other three-dot menu in the UI. The cover itself doubles as the
       play button (centered overlay, revealed on hover). */
    var _playlistCardsRendered = false;
    if (isRoot && PLAYLISTS_ENABLED) {
      _playlistCardsRendered = true;
      _userPlaylists.forEach(function(pl) {
        var isSmart = !!(pl.smart && pl.smart.rules);
        var cnt = isSmart ? _evaluateSmartPlaylist(pl, allItems, _userPlaylists, _savedFavorites).length : (pl.items || []).length;
        var iconHtml = IC_PLAYLIST +
          (isSmart ? '<span class="smart-pl-badge" title="Intelligente Playlist">' + IC_SMART_PLAYLIST + '</span>' : '');
        html += '<div class="folder-card playlist-folder-card' + (isSmart ? ' smart-playlist-card' : '') + '" data-playlist-id="' + escHtml(pl.id) + '">' +
          '<div class="thumb-wrap playlist-thumb-wrap">' +
            '<div class="folder-thumb playlist-folder-icon">' + iconHtml + '</div>' +
            '<button class="playlist-cover-play-btn" title="Abspielen">' + IC_FOLDER_PLAY + '</button>' +
          '</div>' +
          '<div class="folder-name">' + escHtml(pl.name) + '</div>' +
          '<div class="folder-count">' + cnt + ' Titel</div>' +
          '<button class="playlist-folder-kebab" title="Mehr Optionen">' + IC_DOTS + '</button>' +
        '</div>';
      });
      /* "+ Neue Playlist" and "Titel" are rendered in the compact tools row above. */
    }

    c.folders.forEach(function(f) {
      var noun = f.count !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN;
      var thumbSrc = viewMode !== 'list'
        ? (f.thumbnail_lg_url || f.thumbnail_url || FOLDER_PLACEHOLDER)
        : (f.thumbnail_url || FOLDER_PLACEHOLDER);
      var displayLabel = showOrigNames ? f.name : f.displayName;
      var favBadge = f.isFavorite && !showOrigNames ? '<span class="fav-badge" title="Favorit">' + IC_STAR + '</span>' : '';
      var langBadges = !showOrigNames ? langBadgesHtml(f.languages) : '';
      var isAudiobook = AUDIOBOOK_DIRS.some(function(d) { return f.name.toLowerCase().startsWith(d.toLowerCase()); });
      var hasVariants = f.variants && f.variants.length > 1;
      var extraClass = (f.isFavorite ? ' fav-folder' : '') + (isAudiobook ? ' audiobook-folder' : '') + (hasVariants ? ' multi-lang-folder' : '');
      var variantsAttr = hasVariants ? ' data-variants="' + escHtml(JSON.stringify(f.variants)) + '"' : '';

      /* Video server: always show a single primary-language flag in a fixed
         top-right corner — falls back to DEFAULT_LANG when nothing detected.
         Multi-variant folders skip this corner flag because they already render
         per-variant flag buttons inside the folder-count area.  Audio keeps the
         pre-existing inline langBadges next to folder-name. */
      var cornerFlagHtml = '';
      if (_isVideo && !showOrigNames && !hasVariants) {
        var primaryLang = (f.languages && f.languages[0]) || DEFAULT_LANG;
        var pf = compositeFlagHtml(primaryLang, f.subLang || '');
        if (pf) cornerFlagHtml = '<span class="folder-lang-corner">' + pf + '</span>';
        /* On video we suppress the inline name-side badge to avoid duplication */
        langBadges = '';
      }

      /* Build folder-count content: inline flag buttons for multi-lang, plain count otherwise */
      var countContent;
      if (hasVariants && !showOrigNames) {
        /* Sort: DEFAULT_LANG first, then alphabetical */
        var sortedV = f.variants.slice().sort(function(a, b) {
          if (a.lang === DEFAULT_LANG && b.lang !== DEFAULT_LANG) return -1;
          if (b.lang === DEFAULT_LANG && a.lang !== DEFAULT_LANG) return 1;
          return (a.lang || '').localeCompare(b.lang || '');
        });
        countContent = '';
        sortedV.forEach(function(v) {
          var flag = compositeFlagHtml(v.lang, v.subLang);
          if (flag) {
            countContent += '<button class="lang-select-btn" data-variant-name="' + escHtml(v.name) + '" title="' +
              escHtml((_LANG_NAME_MAP[v.lang] || v.lang || '') + (v.subLang ? ' + ' + (_LANG_NAME_MAP[v.subLang] || v.subLang) + ' Sub' : '') + ' (' + v.count + ')') + '">' +
              flag + '<span class="lang-select-count">' + v.count + '</span></button>';
          }
        });
        if (!countContent) countContent = f.count + ' ' + noun;
      } else {
        countContent = f.count + ' ' + noun;
      }

      html += '<div class="folder-card' + extraClass + '" data-folder="' + escHtml(f.name) + '"' + variantsAttr + '>' +
        favBadge +
        cornerFlagHtml +
        '<img class="folder-thumb" src="' + escHtml(thumbSrc) + '" alt="" loading="lazy">' +
        '<div class="folder-name">' + escHtml(displayLabel) + (langBadges && !hasVariants ? ' ' + langBadges : '') + '</div>' +
        '<div class="folder-count">' + countContent + '</div>' +
        '<button class="folder-play-btn" title="Play all">' + IC_FOLDER_PLAY + '</button>' +
      '</div>';
    });
    c.files.forEach(function(it, i) {
      var thumbSrc = viewMode !== 'list'
        ? (it.thumbnail_lg_url || it.thumbnail_url || FILE_PLACEHOLDER)
        : (it.thumbnail_url || FILE_PLACEHOLDER);
      var ratingBar = it.rating > 0 ? '<div class="rating-bar" style="width:' + (it.rating / 5 * 100) + '%"></div>' : '';
      html += '<div class="folder-card file-card" data-file-idx="' + i + '">' +
        '<div class="thumb-wrap folder-thumb-wrap">' +
        '<img class="folder-thumb" src="' + escHtml(thumbSrc) + '" alt="" loading="lazy">' +
        ratingBar + '</div>' +
        '<div class="folder-name">' + escHtml(it.title) + '</div>' +
        '<div class="folder-count">' + escHtml(it.artist || '') + '</div>' +
      '</div>';
    });
    folderGrid.innerHTML = html;

    /* Offline folder card click → open offline library */
    var offFolderCard = document.getElementById('offline-folder-card');
    if (offFolderCard) {
      offFolderCard.addEventListener('click', function() { openOfflineLibrary(); });
      updateOfflineFolderCount();
    }

    /* Playlist pseudo-folder card click handlers */
    if (_playlistCardsRendered) {
      folderGrid.querySelectorAll('.playlist-folder-card').forEach(function(card) {
        var playBtn = card.querySelector('.playlist-cover-play-btn');
        var kebabBtn = card.querySelector('.playlist-folder-kebab');
        card.addEventListener('click', function(e) {
          if (wasDrag(e)) return;
          if (e.target.closest('.playlist-cover-play-btn') ||
              e.target.closest('.playlist-folder-kebab')) return;
          showUserPlaylistView(card.dataset.playlistId);
        });
        if (playBtn) playBtn.addEventListener('click', function(e) {
          e.stopPropagation();
          if (wasDrag(e)) return;
          playUserPlaylist(card.dataset.playlistId);
        });
        if (kebabBtn) kebabBtn.addEventListener('click', function(e) {
          e.stopPropagation();
          if (wasDrag(e)) return;
          _openPlaylistCtxMenu(kebabBtn, card.dataset.playlistId);
        });
      });
      var newCard = document.getElementById('playlist-new-card');
      if (newCard) newCard.addEventListener('click', function() {
        var name = prompt('Playlist-Name:');
        if (!name || !name.trim()) return;
        fetch(PLAYLISTS_API_PATH, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: name.trim() })
        }).then(function(r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
          })
          .then(function(d) {
            if (d.playlist) {
              _userPlaylists.unshift(d.playlist);
              showFolderView();
              showToast('Playlist "' + d.playlist.name + '" erstellt');
            } else {
              showToast('Fehler beim Erstellen');
            }
          }).catch(function() { showToast('Fehler beim Erstellen'); });
      });
      var smartNewCard = document.getElementById('smart-playlist-new-card');
      if (smartNewCard) smartNewCard.addEventListener('click', function() {
        openSmartPlaylistEditor(null);
      });
    }

    /* Recently played — only on root, only when catalog is loaded, only when enabled */
    if (RECENT_ENABLED && isRoot && allItems.length > 0) {
      loadRecentlyPlayed();
    } else {
      var rs = document.getElementById('recent-section');
      if (rs) rs.hidden = true;
    }

    folderGrid.querySelectorAll('.folder-card:not(.file-card):not(.offline-folder-card):not(.playlist-folder-card):not(.playlist-new-card)').forEach(function(card) {
      var pb = card.querySelector('.folder-play-btn');
      var variants = card.dataset.variants ? JSON.parse(card.dataset.variants) : null;

      /* Lang-select buttons: direct navigation into that variant */
      card.querySelectorAll('.lang-select-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
          e.stopPropagation();
          if (wasDrag(e)) return;
          var vName = btn.dataset.variantName;
          if (vName) navigateInto(vName);
        });
      });

      card.addEventListener('click', function(e) {
        if (wasDrag(e)) return;
        if (e.target.closest('.folder-play-btn')) return;
        if (e.target.closest('.lang-select-btn')) return;
        if (variants && variants.length > 1) {
          /* Navigate into the DEFAULT_LANG variant, or first variant */
          var defaultV = variants.find(function(v) { return v.lang === DEFAULT_LANG; });
          navigateInto(defaultV ? defaultV.name : card.dataset.folder);
        } else {
          navigateInto(card.dataset.folder);
        }
      });
      pb.addEventListener('click', function(e) {
        e.stopPropagation();
        if (wasDrag(e)) return;
        if (variants && variants.length > 1) {
          showLangPicker(card, variants, true);
        } else {
          playAllIn(card.dataset.folder);
        }
      });
    });

    var looseFiles = c.files;
    folderGrid.querySelectorAll('.file-card').forEach(function(card) {
      card.addEventListener('click', function(e) {
        if (wasDrag(e)) return;
        _triggerSilentRefresh(); /* get freshest data on playlist entry */
        showPlaylist(looseFiles, true, Number(card.dataset.fileIdx));
      });
    });

    renderBreadcrumb();
    applyViewMode();
    if (typeof _router !== 'undefined') _router.update();
  }

  /* ── Playlist card kebab menu ──────────────────────────────────────────
     All playlist modification actions (Umbenennen, Regeln bearbeiten,
     Aktualisieren, Löschen) live behind the top-right three-dot menu —
     reuses the generic _openCtxMenu() dropdown shared with other
     kebab menus in the UI, so every three-dot menu looks/behaves alike. */
  function _openPlaylistCtxMenu(btn, plId) {
    var pl = _userPlaylists.find(function(p) { return p.id === plId; });
    if (!pl) return;
    var isSmart = !!(pl.smart && pl.smart.rules);
    var items = [];
    if (isSmart) {
      items.push({
        icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:15px;height:15px"><polyline points="23,4 23,10 17,10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>',
        label: 'Aktualisieren',
        onClick: function() { refreshSmartPlaylist(plId); }
      });
      items.push({
        icon: IC_EDIT,
        label: 'Regeln bearbeiten',
        onClick: function() { openSmartPlaylistEditor(pl); }
      });
    }
    items.push({
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:15px;height:15px"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>',
      label: 'Umbenennen',
      onClick: function() { renameUserPlaylist(plId); }
    });
    items.push({
      icon: IC_TRASH,
      label: 'Löschen',
      danger: true,
      onClick: function() { deleteUserPlaylist(plId); }
    });
    _openCtxMenu(btn, items);
  }

  /* ── Language picker for multi-language folders ── */
  var _langPickerCleanup = null;
  function closeLangPicker() {
    if (_langPickerCleanup) { _langPickerCleanup(); _langPickerCleanup = null; }
    var old = document.querySelector('.lang-picker-overlay');
    if (old) old.remove();
  }
  function showLangPicker(card, variants, playMode) {
    closeLangPicker();
    var overlay = document.createElement('div');
    overlay.className = 'lang-picker-overlay';
    var heading = playMode ? 'Sprache zum Abspielen w\u00e4hlen' : 'Sprachversion w\u00e4hlen';
    var inner = '<div class="lang-picker-title">' + escHtml(heading) + '</div>';
    variants.forEach(function(v) {
      var flagSvg = v.lang && LANG_TO_FLAG[v.lang] ? LANG_TO_FLAG[v.lang] : '';
      var langLabel = v.lang && _LANG_NAME_MAP[v.lang] ? _LANG_NAME_MAP[v.lang] : cleanFolderName(v.name);
      var countLabel = v.count + ' ' + (v.count !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN);
      inner += '<button class="lang-picker-item" data-variant-name="' + escHtml(v.name) + '">' +
        (flagSvg ? '<span class="lang-picker-flag">' + flagSvg + '</span>' : '') +
        '<span class="lang-picker-label">' + escHtml(langLabel) + '</span>' +
        '<span class="lang-picker-count">' + countLabel + '</span>' +
      '</button>';
    });
    overlay.innerHTML = inner;

    /* Position near the card */
    var rect = card.getBoundingClientRect();
    overlay.style.position = 'fixed';
    overlay.style.left = Math.max(4, Math.min(rect.left, window.innerWidth - 260)) + 'px';
    var spaceBelow = window.innerHeight - rect.bottom;
    if (spaceBelow > 200) {
      overlay.style.top = rect.bottom + 4 + 'px';
    } else {
      overlay.style.bottom = (window.innerHeight - rect.top + 4) + 'px';
    }
    document.body.appendChild(overlay);

    overlay.querySelectorAll('.lang-picker-item').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        var vName = btn.dataset.variantName;
        closeLangPicker();
        if (playMode) { playAllIn(vName); } else { navigateInto(vName); }
      });
    });

    /* Close on click outside or Escape */
    function onDocClick(e) { if (!overlay.contains(e.target) && !card.contains(e.target)) closeLangPicker(); }
    function onKeyDown(e) { if (e.key === 'Escape') closeLangPicker(); }
    document.addEventListener('click', onDocClick, true);
    document.addEventListener('keydown', onKeyDown);
    _langPickerCleanup = function() {
      document.removeEventListener('click', onDocClick, true);
      document.removeEventListener('keydown', onKeyDown);
    };
  }

  function navigateInto(name) {
    currentPath = currentPath ? currentPath + '/' + name : name;
    _triggerSilentRefresh(); /* always fetch fresh catalog on folder navigation */
    showFolderView();
  }

  function playAllIn(name) {
    var full = currentPath ? currentPath + '/' + name : name;
    var items = itemsUnder(full);
    if (!items.length) return;
    currentPath = full;
    /* Series folders: resume at the last-watched episode instead of
       always restarting at episode 1 (hover-play button on the cover). */
    var isSeries = items.some(function(it) { return (it.season || 0) > 0; });
    if (isSeries) {
      var local = _loadLastPlayedLocal();
      if (local && local.path) {
        var idx = items.findIndex(function(it) { return it.relative_path === local.path; });
        if (idx >= 0) { showPlaylist(items, true, idx); return; }
      }
    }
    showPlaylist(items, true);
  }

  /* ── Shared track-list view entry point ───────────────────────────────
     Consolidates the header/toolbar DOM state that every "flat list of
     tracks" view must set up identically (folder-leaf playlist, user
     playlist, favorites, "Titel", smart playlist, duplicates) — see
     docs/IMPLEMENTATION_PLAN.md "UI-Template-Vereinheitlichung" Phase 2.
     Before this refactor each of the ~5 call sites (spread across
     _folder_browse.py/_smart_playlists.py/_library_tools.py) hand-rolled
     its own subset of these class toggles, which is exactly what caused
     the header/toolbar to drift out of sync between views (missing
     global-search-hide, stale fb-scroll-hidden, ...).
     Caller must set playlistItems/currentPath/_currentPlaylistId/
     inPlaylist BEFORE calling this — applyFilter() reads playlistItems. */
  function _enterTrackListView(opts) {
    opts = opts || {};
    headerTitle.textContent = opts.title != null ? opts.title : (currentPath ? leafName(currentPath) : originalTitle);
    backBtn.classList.toggle('disabled', !!opts.backDisabled);
    if (opts.playAllDisabled != null) playAllBtn.classList.toggle('disabled', !!opts.playAllDisabled);
    folderGrid.classList.add('view-hidden');
    trackView.classList.remove('view-hidden');
    filterBar.classList.remove('view-hidden');
    filterBar.classList.toggle('fb-scroll-hidden', !!opts.collapseFilterBar);
    _initFilterBarScrollReveal();
    playerBar.classList.remove('view-hidden');
    /* Global search bar is folder-grid-only (see showFolderView) — every
       track-list view hides it the same way, regardless of entry point. */
    _hideGlobalSearch();
    searchInput.value = '';
    if (opts.resetIndex) currentIndex = -1;
    renderBreadcrumb();
    /* View-toggle button (table/list icon) — showFolderView() always
       refreshes it (see its trailing renderBreadcrumb()/applyViewMode()
       pair); track-list entry points must do the same or the button is
       left showing whatever the previous (folder-grid) view set, which
       is exactly the kind of header drift this function exists to fix. */
    applyViewMode();
    applyFilter();
    if (typeof _router !== 'undefined') _router.update();
  }

  /* ── playlist view ── */
  function showPlaylist(items, autoplay, startIdx) {
    destroyPlaylistDragDrop();
    inPlaylist = true;
    _currentPlaylistId = '__folder__';
    _moveGhosts = {};  /* clear move ghosts when entering a new playlist */
    playlistItems = _sortByFolderOrder(currentPath, items);

    _enterTrackListView({ backDisabled: !currentPath, resetIndex: true });

    /* Lazy refresh: re-read ratings from filesystem for visible items */
    refreshFolderRatings(items);
    /* Rebuild shuffle queue for the new playlist */
    if (shuffleMode) rebuildShuffleQueue(startIdx || 0);
    if (autoplay && playlistItems.length) {
      /* When shuffle is on, start from shuffleQueue[0] instead of startIdx */
      var firstIdx = shuffleMode && shuffleQueue.length ? shuffleQueue[0] : (startIdx || 0);
      playTrack(firstIdx);
    } else if (typeof startIdx === 'undefined') {
      /* Passive folder navigation — highlight the last-watched episode (if any)
         so the user can resume with a single click without starting playback. */
      _restoreLastEpisode();
    }
    /* Pre-warm: fetch server-side order and re-sort if different */
    var _showPlaylistPath = currentPath;
    _loadFolderOrderAsync(currentPath, function(serverOrder) {
      if (!serverOrder.length) return;
      if (_currentPlaylistId !== '__folder__') return;
      var localOrder = _loadFolderOrder(_showPlaylistPath);
      if (JSON.stringify(localOrder) === JSON.stringify(serverOrder)) return;
      /* Use itemsUnder() — reads from current allItems — NOT the stale 'items'
         closure which still contains songs deleted during this session. */
      playlistItems = _sortByFolderOrder(_showPlaylistPath, itemsUnder(_showPlaylistPath));
      applyFilter();
    });
    if (typeof _router !== 'undefined') _router.update();
  }

  /* ── Auto-resume: restore last-watched episode when navigating into a folder ─
     Called from showPlaylist when the user opens a folder without an explicit
     startIdx (i.e. not via "Play All" or a file-card click).
     Priority: localStorage (instant, survives server restarts) → server recent API.
     Does NOT start playback — user must click explicitly. */
  function _restoreLastEpisode() {
    /* ── 1. Try localStorage first (fast, works through server restarts) ─── */
    var local = _loadLastPlayedLocal();
    if (local && local.path) {
      var pathToIdx = {};
      filteredItems.forEach(function(it, i) { pathToIdx[it.relative_path] = i; });
      if (local.path in pathToIdx && currentIndex < 0) {
        var idx = pathToIdx[local.path];
        currentIndex = idx;
        markActive();
        var li = trackList.querySelector('[data-index="' + idx + '"]');
        if (li) li.scrollIntoView({ block: 'center', behavior: 'smooth' });
        var pos = Number(local.position_seconds || 0);
        var label = (filteredItems[idx] && filteredItems[idx].title) || local.path;
        showToast('Weiter bei: ' + label + (pos > 2 ? ' (' + fmtTime(pos) + ')' : ''), 5000);
        return;
      }
    }
    /* ── 2. Fallback: server recent API ────────────────────────────────────── */
    if (!RECENT_ENABLED) return;
    fetch(RECENT_API_PATH + '?limit=100')
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(d) {
        if (!d || !d.items || !d.items.length) return;
        if (currentIndex >= 0) return;
        var pathToIdx2 = {};
        filteredItems.forEach(function(it, i) { pathToIdx2[it.relative_path] = i; });
        for (var j = 0; j < d.items.length; j++) {
          var entry = d.items[j];
          var rp = entry.relative_path || '';
          if (!(rp in pathToIdx2)) continue;
          var pos2 = Number(entry.position_seconds || 0);
          if (pos2 < 5) continue;
          if (currentIndex >= 0) return;
          var idx2 = pathToIdx2[rp];
          currentIndex = idx2;
          markActive();
          var li2 = trackList.querySelector('[data-index="' + idx2 + '"]');
          if (li2) li2.scrollIntoView({ block: 'center', behavior: 'smooth' });
          var label2 = (filteredItems[idx2] && filteredItems[idx2].title) || rp;
          showToast('Weiter bei: ' + label2 + ' (' + fmtTime(pos2) + ')', 5000);
          return;
        }
      })
      .catch(function() {});
  }

  /* ── back ── */
  function goBack() {
    if (_globalSearchActive) { exitGlobalSearch(); return; }
    if (currentPath === '__offline__') {
      currentPath = '';
      showFolderView();
      return;
    }
    if (inPlaylist) {
      var c = contentsAt(currentPath);
      if (c.folders.length > 0) { showFolderView(); return; }
    }
    currentPath = parentPath(currentPath);
    showFolderView();
  }

  /* ── global search (root view) ── */
  var _globalSearchDebounce = null;
  var _globalSearchListenersInit = false;
  function initGlobalSearch() {
    var inp = document.getElementById('global-search-input');
    if (!inp) return;
    /* Show in header */
    inp.classList.remove('view-hidden');
    /* Wire events only once */
    if (_globalSearchListenersInit) return;
    _globalSearchListenersInit = true;
    inp.addEventListener('input', function() {
      clearTimeout(_globalSearchDebounce);
      var val = inp.value.trim();
      if (!val) {
        if (_globalSearchActive) exitGlobalSearch();
        return;
      }
      _globalSearchDebounce = setTimeout(function() { globalSearch(val); }, 200);
    });
    inp.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        inp.value = '';
        if (_globalSearchActive) exitGlobalSearch();
        inp.blur();
      }
    });
  }

  function _hideGlobalSearch() {
    var inp = document.getElementById('global-search-input');
    if (inp) { inp.classList.add('view-hidden'); inp.value = ''; }
    if (folderFilterBar) folderFilterBar.hidden = true;
  }

  /* ── Filter bar scroll-reveal ── */
  var _fbScrollInitDone = false;
  var _fbLastScrollY = 0;
  function _initFilterBarScrollReveal() {
    if (_fbScrollInitDone) return;
    _fbScrollInitDone = true;
    var wrap = document.getElementById('track-view');
    if (!wrap) return;
    wrap.addEventListener('scroll', function() {
      var y = wrap.scrollTop;
      /* Reveal when near top (y < 10) or scrolling upward */
      if (y < 10 || y < _fbLastScrollY - 2) {
        filterBar.classList.remove('fb-scroll-hidden');
      } else if (y > _fbLastScrollY + 8) {
        filterBar.classList.add('fb-scroll-hidden');
      }
      _fbLastScrollY = y;
    });
  }

"""
