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
      _enterFolderGridView({
        playAllDisabled: true,
        trackCount: '',
        contentHtml: '<div class="empty-hint">No items found. Run a sync first.</div>'
      });
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

    var label = c.folders.length + ' folder' + (c.folders.length !== 1 ? 's' : '');
    if (c.files.length > 0) {
      label += ', ' + c.files.length + ' ' + (c.files.length !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN);
    }
    /* Header/toolbar state via the shared folder-grid entry point —
       content HTML is built below and assigned afterwards (identical
       result; _enterFolderGridView only touches container-level state). */
    _enterFolderGridView({ trackCount: label });

    var html = '';

    /* Compact tools row — only on root: Neue Playlist | Titel | Downloaded | reload.
       Video server omits playlist tools (Neue Playlist / Intelligente Playlist / Titel)
       since playlists are an audio-only feature there. */
    var _isVideo = (ITEM_NOUN === 'video');
    /* markup: webui/src/rootCards.ts::toolsRowHtml */
    html += window._toolsRowHtml({
      isRoot: isRoot, playlistsEnabled: !!PLAYLISTS_ENABLED, offlineEnabled: !!OFFLINE_ENABLED,
      isVideo: _isVideo, allItemsCount: allItems.length, icSmartPlaylist: IC_SMART_PLAYLIST,
      icPlaylist: IC_PLAYLIST, icDl: IC_DL, icRefresh: IC_REFRESH
    });

    /* Auto-Favorites playlist card — only on root when favorites exist */
    if (isRoot && PLAYLISTS_ENABLED) {
      var _favCount = allItems.filter(function(t) { return !!_savedFavorites[t.relative_path]; }).length;
      /* markup: webui/src/rootCards.ts::favoritesCardHtml */
      html += window._favoritesCardHtml(_favCount, IC_STAR, IC_FOLDER_PLAY);
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
        /* markup: webui/src/rootCards.ts::playlistCardHtml */
        html += window._playlistCardHtml(pl, cnt, {
          escHtml: escHtml, icPlaylist: IC_PLAYLIST, icSmartPlaylist: IC_SMART_PLAYLIST,
          icFolderPlay: IC_FOLDER_PLAY, icDots: IC_DOTS
        });
      });
      /* "+ Neue Playlist" and "Titel" are rendered in the compact tools row above. */
    }

    /* card HTML: webui/src/folderCards.ts (folderCardHtml / fileCardHtml) */
    var _cardOpts = {
      escHtml: escHtml, viewMode: viewMode, showOrigNames: showOrigNames, isVideo: _isVideo,
      itemNoun: ITEM_NOUN, defaultLang: DEFAULT_LANG, audiobookDirs: AUDIOBOOK_DIRS,
      langNames: _LANG_NAME_MAP, folderPlaceholder: FOLDER_PLACEHOLDER, filePlaceholder: FILE_PLACEHOLDER,
      icStar: IC_STAR, icFolderPlay: IC_FOLDER_PLAY,
      compositeFlagHtml: compositeFlagHtml, langBadgesHtml: langBadgesHtml
    };
    c.folders.forEach(function(f) { html += window._folderCardHtml(f, _cardOpts); });
    c.files.forEach(function(it, i) { html += window._fileCardHtml(it, i, _cardOpts); });
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
    /* breadcrumb/view-toggle/router already refreshed by
       _enterFolderGridView() above — no trailing calls needed. */
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
  /* ── Shared header state ──────────────────────────────────────────────
     THE single place that touches header controls. Every view routes
     through here via _enterTrackListView()/_enterFolderGridView(), so the
     header is structurally identical everywhere: the same controls exist,
     in the same order, in every view. Only their *content* (title,
     breadcrumb) and enabled/disabled state may differ — a control is never
     present in one view and absent in another.

     This replaced the earlier "global search is a folder-grid-only
     control" rule, which made the header visibly different between folder
     browsing and any track list (user playlist, favorites, duplicates,
     ...). Searching the whole library is a global action and must stay
     reachable from every view. */
  function _applyHeaderState(opts) {
    opts = opts || {};
    headerTitle.textContent = opts.title != null ? opts.title : (currentPath ? leafName(currentPath) : originalTitle);
    backBtn.classList.toggle('disabled', !!opts.backDisabled);
    playAllBtn.classList.toggle('disabled', !!opts.playAllDisabled);
    renderBreadcrumb();
    /* View-toggle icon depends on the *current* view (folder grid → grid/
       list mode, track list → list/table mode), so it must be refreshed on
       every view change or the button keeps the previous view's icon. */
    applyViewMode();
    /* Global search: present in every view once the catalog is loaded.
       disableSearch is only for states with no catalog at all (loading,
       load error), where a search box would be a dead control. */
    if (!opts.disableSearch && allItems.length > 0) initGlobalSearch(); else _hideGlobalSearch();
  }

  function _enterTrackListView(opts) {
    opts = opts || {};
    _applyHeaderState({
      title: opts.title,
      backDisabled: opts.backDisabled,
      /* Track-list views default to an enabled Play-All (the list itself
         is playable); callers opt out explicitly. */
      playAllDisabled: opts.playAllDisabled
    });
    folderGrid.classList.add('view-hidden');
    trackView.classList.remove('view-hidden');
    filterBar.classList.toggle('view-hidden', !!opts.hideFilterBar);
    filterBar.classList.toggle('fb-scroll-hidden', !!opts.collapseFilterBar);
    _initFilterBarScrollReveal();
    playerBar.classList.remove('view-hidden');
    /* Recently-played strip is a root/folder-grid-only section — every
       track-list view hides it (was previously only done by globalSearch()
       and showFolderView(), a drift bug: entering Favoriten from root left
       the strip visible above the track list). */
    var _rsEl = document.getElementById('recent-section');
    if (_rsEl) _rsEl.hidden = true;
    /* In-list filter box (#search-input, filter bar) — distinct from the
       header's global search. Reset so a previous list's filter doesn't
       silently hide items here. */
    searchInput.value = '';
    if (opts.resetIndex) currentIndex = -1;
    /* skipFilter: views that render their own list (global search's
       renderSearchResults) — applyFilter() would overwrite it. */
    if (!opts.skipFilter) applyFilter();
    if (opts.trackCount != null) trackCount.textContent = opts.trackCount;
    if (typeof _router !== 'undefined') _router.update();
  }

  /* ── Shared folder-grid view entry point ──────────────────────────────
     Counterpart to _enterTrackListView() for every "grid of folders" view
     (normal browse, empty library, loading state, catalog-load error) —
     same rationale: before this, showFolderView() (twice: empty + normal
     branch), showLoadingState() and showCatalogLoadError() each hand-rolled
     the identical header/toolbar toggles and drifted apart (e.g. the error
     view hid the back button via style.display='none' — which nothing ever
     reset — instead of the disabled class every other view uses). */
  function _enterFolderGridView(opts) {
    opts = opts || {};
    _applyHeaderState({
      title: opts.title,
      backDisabled: opts.backDisabled != null ? !!opts.backDisabled : !currentPath,
      playAllDisabled: opts.playAllDisabled,
      disableSearch: opts.disableSearch
    });
    folderGrid.classList.remove('view-hidden');
    trackView.classList.add('view-hidden');
    filterBar.classList.add('view-hidden');
    if (!player.currentSrc) playerBar.classList.add('view-hidden');
    if (opts.trackCount != null) trackCount.textContent = opts.trackCount;
    if (opts.contentHtml != null) folderGrid.innerHTML = opts.contentHtml;
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
    function _applyResume(hit, withPos) {
      currentIndex = hit.idx;
      markActive();
      var li = trackList.querySelector('[data-index="' + hit.idx + '"]');
      if (li) li.scrollIntoView({ block: 'center', behavior: 'smooth' });
      showToast('Weiter bei: ' + hit.label + (withPos ? ' (' + fmtTime(hit.pos) + ')' : ''), 5000);
    }
    var hitLocal = window._findResumeLocal(filteredItems, local, currentIndex);
    if (hitLocal) { _applyResume(hitLocal, hitLocal.pos > 2); return; }
    /* ── 2. Fallback: server recent API ────────────────────────────────────── */
    if (!RECENT_ENABLED) return;
    fetch(RECENT_API_PATH + '?limit=100')
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(d) {
        if (!d || !d.items) return;
        var hit = window._findResumeRecent(filteredItems, d.items, currentIndex);
        if (hit) _applyResume(hit, true);
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
