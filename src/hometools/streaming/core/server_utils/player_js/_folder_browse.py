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
    /* items: webui/src/folderBrowseUi.ts::playlistCtxMenuItems */
    _openCtxMenu(btn, window._playlistCtxMenuItems(pl, {
      refresh: refreshSmartPlaylist,
      editRules: openSmartPlaylistEditor,
      rename: renameUserPlaylist,
      remove: deleteUserPlaylist,
      icEdit: IC_EDIT,
      icTrash: IC_TRASH
    }));
  }
  /* ── Language picker for multi-language folders ── */
  /* Picker (private cleanup state) ported to webui/src/folderBrowseUi.ts. */
  function closeLangPicker() { window._closeLangPicker(); }
  function showLangPicker(card, variants, playMode) {
    window._showLangPicker(card, variants, playMode, {
      esc: escHtml,
      itemNoun: ITEM_NOUN,
      langToFlag: LANG_TO_FLAG,
      langNames: _LANG_NAME_MAP,
      cleanFolderName: cleanFolderName,
      playAllIn: playAllIn,
      navigateInto: navigateInto
    });
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
  /* Shared view-entry points ported to webui/src/viewEntry.ts (DOM elements +
     legacy callbacks via hooks; currentPath/allItems/currentIndex via htState).
     Wrappers keep bare-name call sites. */
  function _entryHooks() {
    return {
      dom: {
        headerTitle: headerTitle, backBtn: backBtn, playAllBtn: playAllBtn,
        folderGrid: folderGrid, trackView: trackView, filterBar: filterBar,
        playerBar: playerBar, trackCount: trackCount, searchInput: searchInput,
        player: player
      },
      originalTitle: originalTitle,
      renderBreadcrumb: renderBreadcrumb,
      applyViewMode: applyViewMode,
      initGlobalSearch: initGlobalSearch,
      hideGlobalSearch: _hideGlobalSearch,
      initFilterBarScrollReveal: _initFilterBarScrollReveal,
      applyFilter: applyFilter,
      routerUpdate: function() { if (typeof _router !== 'undefined') _router.update(); }
    };
  }
  function _applyHeaderState(opts) { window._applyHeaderState(opts, _entryHooks()); }
  function _enterTrackListView(opts) { window._enterTrackListView(opts, _entryHooks()); }
  function _enterFolderGridView(opts) { window._enterFolderGridView(opts, _entryHooks()); }
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
  /* Header search wiring (private debounce/init state) ported to
     webui/src/folderBrowseUi.ts; _globalSearchActive via htState. */
  function initGlobalSearch() {
    window._initGlobalSearch({ globalSearch: globalSearch, exitGlobalSearch: exitGlobalSearch });
  }
  function _hideGlobalSearch() { window._hideGlobalSearch(); }
  /* ── Filter bar scroll-reveal ── */
  function _initFilterBarScrollReveal() { window._initFilterBarScrollReveal(filterBar); }

"""
