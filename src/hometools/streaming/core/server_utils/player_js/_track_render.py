"""JS fragment: track render (split from the former monolithic _player_js.py)."""

from __future__ import annotations


def render_track_render_js() -> str:
    """Return the track render section of the player JS."""
    return """  function renderTracks(tracks, force) {
    /* Ensure dupe data is available when the dupe tool is active */
    if (_toolState.duplicates) _ensureDupeMap();
    /* Separate real items from debug-dimmed items for filteredItems / shuffle */
    var realTracks = DEBUG_FILTER
      ? tracks.filter(function(t) { return !t._debugReason; })
      : tracks;
    filteredItems = realTracks;
    /* Rebuild shuffle queue whenever the filtered set changes */
    if (shuffleMode) rebuildShuffleQueue(currentIndex >= 0 ? currentIndex : 0);
    var hiddenShownCount = realTracks.filter(function(t) { return !!t._hiddenShown; }).length;
    var visibleCount = realTracks.length - hiddenShownCount;
    var noun = visibleCount !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN;
    trackCount.textContent = visibleCount + ' ' + noun;

    /* ── Render guard ───────────────────────────────────────────────────────
       Key covers every input that can change the rendered output.
       _rgKey is reset by _invalidateDupeMap() whenever allItems changes,
       and by the force=true flag (e.g. after playlist reorder).             */
    var guardKey = (_currentPlaylistId || '') + '\\x00' + currentPath + '\\x00'
      + (searchInput ? searchInput.value.trim() : '') + '\\x00'
      + (sortField ? sortField.value : '') + '\\x00'
      + String(tracks.length) + '\\x00' + filterRating + '\\x00'
      + (filterFav ? '1' : '0') + '\\x00' + (filterGenre || '') + '\\x00'
      + _effectiveThreshold + '\\x00' + (showHidden ? '1' : '0');
    if (!force && guardKey === _rgKey && trackList.children.length > 0) {
      /* Nothing visually changed — just refresh active highlight */
      markActive();
      return;
    }
    _rgKey = guardKey;

    /* ── Windowed rendering setup ─────────────────────────────────────────*/
    _stopRenderObserver();
    trackList.innerHTML = '';
    /* Mark series lists so .track-num gets a fixed width that fits "S01E12" */
    var _hasSeriesItems = tracks.some(function(t) { return (t.season || 0) > 0; });
    trackList.classList.toggle('track-list--series', _hasSeriesItems);

    if (!tracks.length) {
      trackList.innerHTML = '<li class="empty-hint">No matching items.</li>';
      return;
    }

    /* Pre-compute displayTracks (with episode-gap placeholders) and a map
       from display index → filteredItems index (-1 for placeholder rows). */
    var displayTracks = withMissingEpisodes(realTracks);
    _renderAllItems   = displayTracks;
    _renderRealIdxMap = [];
    var rc = 0;
    for (var mi = 0; mi < displayTracks.length; mi++) {
      var mt = displayTracks[mi];
      _renderRealIdxMap.push((mt._missing || mt._debugReason) ? -1 : rc++);
    }
    _renderBatchOffset = 0;

    /* Sentinel <li> at bottom — IntersectionObserver fires _appendTrackBatch */
    _renderSentinelEl = document.createElement('li');
    _renderSentinelEl.className = 'track-list-sentinel';
    _renderSentinelEl.setAttribute('aria-hidden', 'true');
    _renderSentinelEl.style.cssText = 'height:1px;pointer-events:none;visibility:hidden;';
    trackList.appendChild(_renderSentinelEl);

    /* Wire event delegation once — covers all current + future batch items */
    _wireTrackListDelegation();

    /* Render first batch so the user sees content immediately */
    _appendTrackBatch();

    /* Set up observer for lazy-loading of remaining batches */
    if (_renderBatchOffset < _renderAllItems.length) {
      if (typeof IntersectionObserver !== 'undefined') {
        _renderObserver = new IntersectionObserver(function(entries) {
          if (entries[0].isIntersecting) _appendTrackBatch();
        }, { rootMargin: '400px' });
        _renderObserver.observe(_renderSentinelEl);
      } else {
        /* Fallback for old browsers: render everything synchronously */
        while (_renderBatchOffset < _renderAllItems.length) _appendTrackBatch();
      }
    }
  }

  /* ── offline download management ── */
  var downloadDB = null;
  var OFFLINE_SOFT_LIMIT = 500 * 1024 * 1024;
  var activeDownloads = {};

  function cancelDownload(streamUrl, btn) {
    var controller = activeDownloads[streamUrl];
    if (controller) {
      controller.abort();
      delete activeDownloads[streamUrl];
    }
    if (btn) {
      btn.classList.remove('downloading');
      btn.classList.remove('cached');
      btn.innerHTML = IC_DL;
      btn.title = 'Download';
    }
    showToast('Download abgebrochen');
  }

  function revokeOfflineUrl() {
    if (currentOfflineUrl) {
      URL.revokeObjectURL(currentOfflineUrl);
      currentOfflineUrl = null;
    }
  }

  function initDownloadDB() {
    return new Promise(function(resolve, reject) {
      var req = indexedDB.open('hometools-downloads', 2);
      req.onerror = function() { reject(req.error); };
      req.onsuccess = function() { downloadDB = req.result; resolve(req.result); };
      req.onupgradeneeded = function(e) {
        var db = e.target.result;
        var store;
        if (!db.objectStoreNames.contains('downloads')) {
          store = db.createObjectStore('downloads', { keyPath: 'id', autoIncrement: true });
        } else {
          store = e.target.transaction.objectStore('downloads');
        }
        if (!store.indexNames.contains('streamUrl')) {
          store.createIndex('streamUrl', 'streamUrl', { unique: true });
        }
        if (!store.indexNames.contains('status')) {
          store.createIndex('status', 'status', { unique: false });
        }
        if (!store.indexNames.contains('timestamp')) {
          store.createIndex('timestamp', 'timestamp', { unique: false });
        }
        if (!store.indexNames.contains('title')) {
          store.createIndex('title', 'title', { unique: false });
        }
      };
    });
  }

  function getDownloadByStreamUrl(streamUrl) {
    return new Promise(function(resolve) {
      if (!downloadDB) { resolve(null); return; }
      try {
        var tx = downloadDB.transaction('downloads', 'readonly');
        var store = tx.objectStore('downloads');
        var index = store.index('streamUrl');
        var req = index.get(streamUrl);
        req.onerror = function() { resolve(null); };
        req.onsuccess = function() { resolve(req.result || null); };
      } catch (e) {
        resolve(null);
      }
    });
  }

  function getAllDownloads() {
    return new Promise(function(resolve) {
      if (!downloadDB) { resolve([]); return; }
      try {
        var tx = downloadDB.transaction('downloads', 'readonly');
        var store = tx.objectStore('downloads');
        var req = store.getAll();
        req.onerror = function() { resolve([]); };
        req.onsuccess = function() { resolve(req.result || []); };
      } catch (e) {
        resolve([]);
      }
    });
  }

  function deleteDownloadById(id) {
    return new Promise(function(resolve) {
      if (!downloadDB) { resolve(false); return; }
      try {
        var tx = downloadDB.transaction('downloads', 'readwrite');
        tx.objectStore('downloads').delete(id);
        tx.oncomplete = function() { resolve(true); };
        tx.onerror = function() { resolve(false); };
      } catch (e) {
        resolve(false);
      }
    });
  }

  function deleteDownloadByStreamUrl(streamUrl) {
    return getDownloadByStreamUrl(streamUrl).then(function(download) {
      if (!download) return false;
      return deleteDownloadById(download.id).then(function(ok) {
        if (ok && navigator.serviceWorker && navigator.serviceWorker.controller) {
          navigator.serviceWorker.controller.postMessage({ type: 'DELETE_DOWNLOAD', url: streamUrl });
        }
        return ok;
      });
    });
  }

  /* formatBytes() lives in _core.py — kept as the single canonical
     definition (was accidentally duplicated here during the module split). */

  function formatDate(ts) {
    if (!ts) return 'Unbekannt';
    try {
      return new Date(ts).toLocaleString();
    } catch (e) {
      return 'Unbekannt';
    }
  }

  function findItemByStreamUrl(streamUrl) {
    var idx = filteredItems.findIndex(function(it) { return it.stream_url === streamUrl; });
    if (idx >= 0) return { item: filteredItems[idx], index: idx };
    for (var i = 0; i < allItems.length; i++) {
      if (allItems[i].stream_url === streamUrl) return { item: allItems[i], index: -1 };
    }
    return null;
  }

  function sortDownloads(downloads, sortBy) {
    return downloads.slice().sort(function(a, b) {
      if (sortBy === 'oldest') return (a.timestamp || 0) - (b.timestamp || 0);
      if (sortBy === 'title') return String(a.title || '').localeCompare(String(b.title || ''));
      if (sortBy === 'size') return (b.size || 0) - (a.size || 0);
      return (b.timestamp || 0) - (a.timestamp || 0);
    });
  }

  function getAppDownloadUsage(downloads) {
    return (downloads || []).reduce(function(sum, d) {
      return sum + (d.status === 'ready' ? Number(d.size || 0) : 0);
    }, 0);
  }

  function estimateOfflineStorage(downloads) {
    var list = downloads || [];
    var info = {
      downloads: list,
      appUsage: getAppDownloadUsage(list),
      softLimit: OFFLINE_SOFT_LIMIT,
      browserUsage: null,
      browserQuota: null,
      persistent: null
    };
    var tasks = [];
    if (navigator.storage && navigator.storage.estimate) {
      tasks.push(
        navigator.storage.estimate().then(function(estimate) {
          info.browserUsage = estimate && estimate.usage ? estimate.usage : 0;
          info.browserQuota = estimate && estimate.quota ? estimate.quota : 0;
        }).catch(function() {})
      );
    }
    if (navigator.storage && navigator.storage.persisted) {
      tasks.push(
        navigator.storage.persisted().then(function(persistent) {
          info.persistent = !!persistent;
        }).catch(function() {})
      );
    }
    return Promise.all(tasks).then(function() { return info; });
  }

  function renderStorageSummary(info) {
    if (!info) return;
    var warn = info.appUsage >= info.softLimit * 0.8 ||
      (info.browserQuota && info.browserUsage >= info.browserQuota * 0.8);
    if (offlineStorageSummary) {
      offlineStorageSummary.classList.toggle('warn', !!warn);
      offlineStorageSummary.textContent = info.downloads.length
        ? info.downloads.length + ' Offline-Download' + (info.downloads.length !== 1 ? 's' : '') +
          ' · ' + formatBytes(info.appUsage) + ' lokal gespeichert'
        : 'Noch keine Offline-Downloads.';
    }
    if (offlineStorageDetail) {
      var parts = [
        'App-Budget ' + formatBytes(info.appUsage) + ' / ' + formatBytes(info.softLimit)
      ];
      if (info.browserQuota) {
        parts.push('Browser ' + formatBytes(info.browserUsage) + ' / ' + formatBytes(info.browserQuota));
      }
      if (info.persistent !== null) {
        parts.push(info.persistent ? 'Persistent aktiv' : 'Nicht persistent');
      }
      offlineStorageDetail.textContent = parts.join(' · ');
    }
    if (downloadedPill) {
      downloadedPill.textContent = 'Downloaded (' + info.downloads.length + ')';
      downloadedPill.classList.toggle('has-downloads', info.downloads.length > 0);
    }
    updateOfflineFolderCount();
  }

  function renderOfflineDownloadList(downloads) {
    if (!offlineDownloadList) return;
    if (!downloads.length) {
      offlineDownloadList.innerHTML = '<li class="empty-downloads">Noch keine Offline-Downloads gespeichert.</li>';
      return;
    }
    offlineDownloadList.innerHTML = downloads.map(function(download) {
      var thumbSrc = download.thumbnailUrl || FILE_PLACEHOLDER;
      var subtitle = download.artist || download.relativePath || '';
      var statusText = download.status === 'ready' ? 'Offline bereit' : (download.status || 'unbekannt');
      return '<li class="offline-download-item" data-stream-url="' + escHtml(download.streamUrl) + '">' +
        '<img class="offline-download-thumb" src="' + escHtml(thumbSrc) + '" alt="" loading="lazy">' +
        '<div class="offline-download-meta">' +
          '<div class="offline-download-title">' + escHtml(download.title || 'Unbenannter Download') + '</div>' +
          '<div class="offline-download-sub">' + escHtml(subtitle) + '</div>' +
          '<div class="offline-download-size">' + escHtml(statusText) + ' · ' +
            escHtml(formatBytes(download.size || 0)) + ' · ' + escHtml(formatDate(download.timestamp)) + '</div>' +
        '</div>' +
        '<button class="offline-download-delete" data-stream-url="' + escHtml(download.streamUrl) + '" title="Entfernen">Entfernen</button>' +
      '</li>';
    }).join('');
    offlineDownloadList.querySelectorAll('.offline-download-item').forEach(function(el) {
      el.addEventListener('click', function(e) {
        if (e.target && e.target.classList && e.target.classList.contains('offline-download-delete')) return;
        playStoredDownload(el.dataset.streamUrl);
      });
    });
    offlineDownloadList.querySelectorAll('.offline-download-delete').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        deleteTrackDownload(btn.dataset.streamUrl);
      });
    });
  }

  function refreshOfflineLibrary() {
    return getAllDownloads().then(function(downloads) {
      /* If currently viewing the offline playlist, refresh it */
      if (currentPath === '__offline__') {
        var ready = downloads.filter(function(d) { return d.status === 'ready'; });
        var sortBy = offlineSort ? offlineSort.value : 'newest';
        var sorted = sortDownloads(ready, sortBy);
        var items = sorted.map(function(d) {
          return {
            title: d.title || 'Offline-Download',
            artist: d.artist || '',
            relative_path: d.relativePath || d.title || d.streamUrl,
            stream_url: d.streamUrl,
            thumbnail_url: d.thumbnailUrl || '',
            media_type: d.mediaType || ITEM_NOUN,
            rating: 0
          };
        });
        playlistItems = items;
        applyFilter();
        estimateOfflineStorage(ready).then(function(info) {
          if (info && info.appUsage > 0) {
            trackCount.textContent = ready.length + ' download' + (ready.length !== 1 ? 's' : '') +
              ' · ' + formatBytes(info.appUsage);
          }
        });
      }
      updateOfflineFolderCount();
      return downloads;
    });
  }

  function openOfflineLibrary() {
    getAllDownloads().then(function(downloads) {
      var ready = downloads.filter(function(d) { return d.status === 'ready'; });
      var sortBy = offlineSort ? offlineSort.value : 'newest';
      var sorted = sortDownloads(ready, sortBy);
      var items = sorted.map(function(d) {
        return {
          title: d.title || 'Offline-Download',
          artist: d.artist || '',
          relative_path: d.relativePath || d.title || d.streamUrl,
          stream_url: d.streamUrl,
          thumbnail_url: d.thumbnailUrl || '',
          media_type: d.mediaType || ITEM_NOUN,
          rating: 0
        };
      });
      currentPath = '__offline__';
      showPlaylist(items, false);
      headerTitle.textContent = 'Downloaded';
      backBtn.style.display = 'inline-block';
      if (typeof _router !== 'undefined') _router.update();
      estimateOfflineStorage(ready).then(function(info) {
        if (info && info.appUsage > 0) {
          trackCount.textContent = ready.length + ' download' + (ready.length !== 1 ? 's' : '') +
            ' · ' + formatBytes(info.appUsage);
        }
      });
    });
  }

  function closeOfflineLibrary() {
    if (currentPath === '__offline__') {
      currentPath = '';
      showFolderView();
    }
  }

  function updateOfflineFolderCount() {
    getAllDownloads().then(function(downloads) {
      var ready = downloads.filter(function(d) { return d.status === 'ready'; });
      var el = document.getElementById('offline-folder-count');
      if (el) {
        el.textContent = String(ready.length);
      }
      if (downloadedPill) {
        downloadedPill.textContent = 'Downloaded (' + ready.length + ')';
        downloadedPill.classList.toggle('has-downloads', ready.length > 0);
      }
    });
  }

  /* ── Recently played section ── */
  function loadRecentlyPlayed() {
    var section = document.getElementById('recent-section');
    if (!section) return;
    fetch(RECENT_API_PATH + '?limit=10')
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(d) {
        if (!d || !d.items || d.items.length === 0) {
          section.hidden = true;
          return;
        }
        var scroll = section.querySelector('.recent-scroll');
        scroll.innerHTML = d.items.map(function(it) {
          var pct = Math.min(100, Math.max(0, it.progress_pct || 0));
          var thumb = it.thumbnail_url || FILE_PLACEHOLDER;
          var isPlaceholder = !it.thumbnail_url;
          var imgStyle = isPlaceholder ? ' style="object-fit:contain;padding:14px;opacity:.4"' : '';
          return '<div class="recent-card" data-path="' + escHtml(it.relative_path || '') + '"'
            + ' data-pos="' + (it.position_seconds || 0) + '" title="' + escHtml(it.title || '') + '">'
            + '<div class="recent-thumb-wrap">'
            + '<img class="recent-thumb" src="' + escHtml(thumb) + '" loading="lazy"' + imgStyle + '>'
            + (pct > 2 ? '<div class="recent-progress-bar" style="width:' + pct + '%"></div>' : '')
            + '</div>'
            + '<div class="recent-title">' + escHtml(it.title || it.relative_path || '') + '</div>'
            + '<div class="recent-sub">' + escHtml(it.artist || '') + '</div>'
            + '</div>';
        }).join('');
        section.hidden = false;
        /* attach click handlers */
        scroll.querySelectorAll('.recent-card').forEach(function(card) {
          card.addEventListener('click', function() {
            var path = card.dataset.path;
            var seekPos = parseFloat(card.dataset.pos) || 0;
            /* find item in the full allItems list */
            var found = null;
            for (var i = 0; i < allItems.length; i++) {
              if (allItems[i].relative_path === path) { found = allItems[i]; break; }
            }
            if (!found) return;
            /* navigate to the item's folder and play it */
            var folder = path.lastIndexOf('/') >= 0
              ? path.substring(0, path.lastIndexOf('/')) : '';
            currentPath = folder;
            inPlaylist = true;
            var folderItems = folder
              ? allItems.filter(function(it) {
                  return it.relative_path.startsWith(folder + '/') &&
                    it.relative_path.indexOf('/', folder.length + 1) < 0;
                })
              : allItems.filter(function(it) { return it.relative_path.indexOf('/') < 0; });
            if (!folderItems.length) folderItems = [found];
            showPlaylist(folderItems, false);
            /* Find the correct index in filteredItems *after* showPlaylist has
               sorted them via applyFilter.  Computing idx from the unsorted
               folderItems before showPlaylist would give a stale position and
               cause the wrong next-episode to play when the current one ends. */
            var filteredIdx = 0;
            for (var k = 0; k < filteredItems.length; k++) {
              if (filteredItems[k].relative_path === path) { filteredIdx = k; break; }
            }
            playItem(found, filteredIdx);
            /* seek to saved position after canplay */
            if (seekPos > 2) {
              player.addEventListener('canplay', function onCp() {
                player.removeEventListener('canplay', onCp);
                player.currentTime = seekPos;
              }, { once: true });
            }
          });
        });
      })
      .catch(function() { if (section) section.hidden = true; });
  }



  function requestPersistentStorage() {
    if (!(navigator.storage && navigator.storage.persist)) return Promise.resolve(false);
    if (offlinePersistBtn) offlinePersistBtn.textContent = 'Prüfe persistenten Speicher…';
    return navigator.storage.persist().then(function(persistent) {
      if (offlinePersistBtn) {
        offlinePersistBtn.textContent = persistent ? 'Persistenter Speicher aktiv' : 'Persistenz nicht verfügbar';
      }
      return refreshOfflineLibrary().then(function() { return persistent; });
    }).catch(function() {
      if (offlinePersistBtn) offlinePersistBtn.textContent = 'Persistenz fehlgeschlagen';
      return false;
    });
  }

  function pruneOldDownloads(requiredBytes, protectedStreamUrl) {
    return getAllDownloads().then(function(downloads) {
      var total = getAppDownloadUsage(downloads);
      var candidates = downloads.filter(function(download) {
        return download.status === 'ready' && download.streamUrl !== protectedStreamUrl;
      }).sort(function(a, b) {
        return (a.timestamp || 0) - (b.timestamp || 0);
      });
      var victims = [];
      while (total + requiredBytes > OFFLINE_SOFT_LIMIT && candidates.length) {
        var victim = candidates.shift();
        victims.push(victim);
        total -= Number(victim.size || 0);
      }
      if (total + requiredBytes > OFFLINE_SOFT_LIMIT) return false;
      var chain = Promise.resolve();
      victims.forEach(function(victim) {
        chain = chain.then(function() { return deleteDownloadById(victim.id); });
      });
      return chain.then(function() { return true; });
    }).then(function(ok) {
      updateAllDownloadButtons();
      refreshOfflineLibrary();
      return ok;
    });
  }

  function ensureStorageBudget(requiredBytes, protectedStreamUrl) {
    return getAllDownloads().then(function(downloads) {
      var total = getAppDownloadUsage(downloads);
      if (total + requiredBytes <= OFFLINE_SOFT_LIMIT) return true;
      return pruneOldDownloads(requiredBytes, protectedStreamUrl);
    });
  }

  function updateAllDownloadButtons() {
    if (!downloadDB) return;
    getAllDownloads().then(function(downloads) {
      var cached = {};
      downloads.forEach(function(d) {
        if (d.streamUrl && d.status === 'ready') cached[d.streamUrl] = true;
      });
      document.querySelectorAll('.track-dl-btn').forEach(function(btn) {
        var url = btn.dataset.streamUrl;
        btn.classList.remove('cached');
        if (!btn.classList.contains('downloading')) {
          btn.innerHTML = IC_DL;
          btn.title = 'Download';
        }
        if (cached[url]) {
          btn.classList.add('cached');
          btn.classList.remove('downloading');
          btn.innerHTML = IC_CHECK;
          btn.title = 'Offline gespeichert — klicken zum Entfernen';
        }
      });
    });
  }

  function downloadTrack(streamUrl, title, btn, meta) {
    if (!downloadDB) return;
    btn.classList.add('downloading');
    btn.classList.remove('cached');
    btn.textContent = '0%';
    btn.title = 'Download l\\u00e4uft \\u2014 klicken zum Abbrechen';

    var controller = new AbortController();
    activeDownloads[streamUrl] = controller;

    fetch(streamUrl, { signal: controller.signal }).then(function(response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      var total = parseInt(response.headers.get('content-length'), 10) || 0;
      if (total > OFFLINE_SOFT_LIMIT) {
        throw new Error('Datei zu gro\\u00df f\\u00fcr Offline-Speicher (' + formatBytes(total) + ', max ' + formatBytes(OFFLINE_SOFT_LIMIT) + ')');
      }
      return Promise.resolve(total > 0 ? ensureStorageBudget(total, streamUrl) : true).then(function(ok) {
        if (!ok) throw new Error('Offline-Speicher voll \\u2014 l\\u00f6sche alte Downloads oder erh\\u00f6he den Speicher');
        var received = 0;
        var reader = response.body.getReader();
        var chunks = [];

        function pump() {
          return reader.read().then(function(result) {
            if (result.done) return;
            chunks.push(result.value);
            received += result.value.length;
            if (total > 0) {
              btn.textContent = Math.round(received / total * 100) + '%';
            }
            return pump();
          });
        }

        return pump().then(function() {
          var blob = new Blob(chunks, { type: response.headers.get('content-type') || 'application/octet-stream' });
          return ensureStorageBudget(blob.size, streamUrl).then(function(stillOk) {
            if (!stillOk) throw new Error('Offline-Speicher voll');
            return deleteDownloadByStreamUrl(streamUrl).then(function() {
              return new Promise(function(resolve, reject) {
                var tx = downloadDB.transaction('downloads', 'readwrite');
                var store = tx.objectStore('downloads');
                store.add({
                  streamUrl: streamUrl,
                  title: title,
                  artist: meta && meta.artist ? meta.artist : '',
                  relativePath: meta && meta.relativePath ? meta.relativePath : '',
                  thumbnailUrl: meta && meta.thumbnailUrl ? meta.thumbnailUrl : '',
                  mediaType: meta && meta.mediaType ? meta.mediaType : ITEM_NOUN,
                  blob: blob,
                  size: blob.size,
                  timestamp: Date.now(),
                  status: 'ready'
                });
                tx.oncomplete = resolve;
                tx.onerror = function() { reject(tx.error || new Error('IndexedDB write failed')); };
              });
            });
          });
        });
      });
    }).then(function() {
      delete activeDownloads[streamUrl];
      btn.classList.remove('downloading');
      btn.classList.add('cached');
      btn.innerHTML = IC_CHECK;
      btn.title = 'Offline gespeichert — klicken zum Entfernen';
      updateAllDownloadButtons();
      refreshOfflineLibrary();
    }).catch(function(err) {
      delete activeDownloads[streamUrl];
      if (err && err.name === 'AbortError') return;
      console.error('Download failed:', err);
      btn.classList.remove('downloading');
      btn.classList.remove('cached');
      btn.innerHTML = IC_DL;
      btn.title = 'Download fehlgeschlagen';
      showToast(err && err.message ? err.message : 'Download fehlgeschlagen');
      refreshOfflineLibrary();
    });
  }

  function deleteTrackDownload(streamUrl, btn) {
    deleteDownloadByStreamUrl(streamUrl).then(function(deleted) {
      if (!deleted) return;
      if (btn) {
        btn.classList.remove('cached');
        btn.classList.remove('downloading');
        btn.innerHTML = IC_DL;
        btn.title = 'Download';
      }
      refreshOfflineLibrary();
      updateAllDownloadButtons();
    });
  }

  function checkIfMediaCached(streamUrl) {
    return getDownloadByStreamUrl(streamUrl).then(function(download) {
      return download && download.status === 'ready' && download.blob ? download : null;
    });
  }

  function getOfflineUrl(blob) {
    revokeOfflineUrl();
    currentOfflineUrl = URL.createObjectURL(blob);
    return currentOfflineUrl;
  }

  function playOfflineOrStream(streamUrl) {
    return checkIfMediaCached(streamUrl).then(function(download) {
      if (download && download.blob) {
        return {
          url: getOfflineUrl(download.blob),
          offline: true,
          fallbackUrl: streamUrl
        };
      }
      return {
        url: streamUrl,
        offline: false,
        fallbackUrl: streamUrl
      };
    });
  }

  function playStoredDownload(streamUrl) {
    getDownloadByStreamUrl(streamUrl).then(function(download) {
      if (!download) return;
      /* If currently in offline playlist, find track in filtered items */
      if (currentPath === '__offline__') {
        var offIdx = filteredItems.findIndex(function(it) { return it.stream_url === streamUrl; });
        if (offIdx >= 0) { playTrack(offIdx); return; }
      }
      var match = findItemByStreamUrl(streamUrl);
      if (match) {
        playTrack(match.index >= 0 ? match.index : filteredItems.findIndex(function(it) { return it.stream_url === streamUrl; }));
        if (match.index < 0) {
          playItem(match.item, -1);
        }
        return;
      }
      playItem({
        title: download.title || 'Offline-Download',
        artist: download.artist || '',
        relative_path: download.relativePath || download.title || streamUrl,
        stream_url: download.streamUrl,
        thumbnail_url: download.thumbnailUrl || '',
        media_type: download.mediaType || ITEM_NOUN,
        rating: 0
      }, -1);
    });
  }

  /* Listen for Service Worker download notifications */
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.addEventListener('message', function(e) {
      if (e.data && (e.data.type === 'DOWNLOAD_CACHED' || e.data.type === 'DOWNLOAD_DELETED')) {
        updateAllDownloadButtons();
        refreshOfflineLibrary();
      }
    });
  }

  if (downloadedPill) downloadedPill.addEventListener('click', openOfflineLibrary);
  if (offlineClose) offlineClose.addEventListener('click', closeOfflineLibrary);
  if (offlineLibrary) {
    offlineLibrary.addEventListener('click', function(e) {
      if (e.target === offlineLibrary) closeOfflineLibrary();
    });
  }
  if (offlineSort) offlineSort.addEventListener('change', refreshOfflineLibrary);
  if (offlinePersistBtn) {
    if (!(navigator.storage && navigator.storage.persist)) {
      offlinePersistBtn.hidden = true;
    } else {
      offlinePersistBtn.addEventListener('click', requestPersistentStorage);
    }
  }
  if (offlinePruneBtn) {
    offlinePruneBtn.addEventListener('click', function() {
      pruneOldDownloads(0, currentStreamUrl);
    });
  }
  window.addEventListener('online', refreshOfflineLibrary);
  window.addEventListener('offline', refreshOfflineLibrary);

  /* ── Tools panel ── */
  var toolsPill = document.getElementById('tools-pill');
  var toolsBackdrop = document.getElementById('tools-panel-backdrop');
  var toolsClose = document.getElementById('tools-panel-close');
  var _toolInlineRatings = document.getElementById('tool-inline-ratings');
  var _toolDownloads = document.getElementById('tool-downloads');
  var _toolPlaylists = document.getElementById('tool-playlists');
  var _toolDuplicates = document.getElementById('tool-duplicates');
  var _dupeShowLink = document.getElementById('dupe-show-link');
  var _toolFileMover = document.getElementById('tool-file-mover');
  var _toolBpmCalc = document.getElementById('tool-bpm-calc');
  var _toolAutoRefreshGroup = null; /* removed — auto-refresh feature disabled */
  var _toolsGlobalRefreshBtn = document.getElementById('tools-global-refresh-btn');

  /* Load saved tool states from localStorage */
  var _toolState = JSON.parse(localStorage.getItem('ht-tools') || '{}');

  function _anyToolActive() {
    return !!_toolState.active && (!!_toolState.inlineRatings || !!_toolState.duplicates || !!_toolState.fileMover);
  }

  function _updateActivateBtn() {
    var isOn = !!_toolState.active;
    if (_toolsActivateAll) {
      _toolsActivateAll.textContent = isOn ? 'Tool-Modus deaktivieren' : 'Tool-Modus aktivieren';
      _toolsActivateAll.classList.toggle('tools-activate-all--active', isOn);
      _toolsActivateAll.title = isOn ? 'Tool-Modus ausschalten' : 'Tool-Modus mit den konfigurierten Einstellungen aktivieren';
    }
    /* Sync the header split-pill toggle button */
    var _pillToggle = document.getElementById('tools-pill-toggle');
    if (_pillToggle) {
      _pillToggle.classList.toggle('active', isOn);
      _pillToggle.title = isOn ? 'Tool-Modus deaktivieren' : 'Tool-Modus aktivieren';
    }
    /* Sync the wrap border highlight */
    var _pillWrap = document.getElementById('tools-pill-wrap');
    if (_pillWrap) _pillWrap.classList.toggle('has-active', _anyToolActive());
  }

  function _applyHeaderUiState() {
    /* Remove legacy body classes that may have been persisted in older localStorage saves */
    document.body.classList.remove('tool-refresh-off', 'tool-refresh-in-pill');
  }

  function _applyToolState() {
    _updateActivateBtn();
    _applyHeaderUiState();
    if (!_toolState.active) {
      /* Tool mode is off: hide all tool UI without changing saved preferences */
      document.body.classList.remove('tool-inline-ratings');
      document.body.classList.remove('tool-hide-downloads');
      document.body.classList.remove('tool-hide-playlists');
      document.body.classList.remove('tool-show-duplicates');
      document.body.classList.remove('tool-show-file-mover');
      document.body.classList.remove('tool-bpm-calc');
      if (toolsPill) toolsPill.classList.remove('has-active');
      /* Re-render to remove tool widgets from track list */
      if (folderGrid && !folderGrid.classList.contains('view-hidden')) {
        showFolderView();
      } else if (inPlaylist) {
        applyViewMode();
        applyFilter();
      }
      return;
    }
    if (_toolState.inlineRatings) {
      document.body.classList.add('tool-inline-ratings');
      if (_toolInlineRatings) _toolInlineRatings.checked = true;
    } else {
      document.body.classList.remove('tool-inline-ratings');
      if (_toolInlineRatings) _toolInlineRatings.checked = false;
    }
    if (_toolState.downloads === false) {
      document.body.classList.add('tool-hide-downloads');
      if (_toolDownloads) _toolDownloads.checked = false;
    } else {
      document.body.classList.remove('tool-hide-downloads');
      if (_toolDownloads) _toolDownloads.checked = true;
    }
    if (_toolState.playlists === false) {
      document.body.classList.add('tool-hide-playlists');
      if (_toolPlaylists) _toolPlaylists.checked = false;
    } else {
      document.body.classList.remove('tool-hide-playlists');
      if (_toolPlaylists) _toolPlaylists.checked = true;
    }
    if (_toolState.duplicates) {
      document.body.classList.add('tool-show-duplicates');
      if (_toolDuplicates) _toolDuplicates.checked = true;
    } else {
      document.body.classList.remove('tool-show-duplicates');
      if (_toolDuplicates) _toolDuplicates.checked = false;
    }
    if (_toolState.fileMover) {
      document.body.classList.add('tool-show-file-mover');
      if (_toolFileMover) _toolFileMover.checked = true;
    } else {
      document.body.classList.remove('tool-show-file-mover');
      if (_toolFileMover) _toolFileMover.checked = false;
    }
    if (_toolState.bpmCalc) {
      document.body.classList.add('tool-bpm-calc');
      if (_toolBpmCalc) _toolBpmCalc.checked = true;
    } else {
      document.body.classList.remove('tool-bpm-calc');
      if (_toolBpmCalc) _toolBpmCalc.checked = false;
    }
    /* Update pill highlight (now on the wrap container) */
    var anyActive = _anyToolActive();
    var _pillWrapEl = document.getElementById('tools-pill-wrap');
    if (_pillWrapEl) _pillWrapEl.classList.toggle('has-active', anyActive);
    if (toolsPill) toolsPill.classList.toggle('has-active', anyActive); /* legacy compat */
    /* Re-render current view so folder names / view mode reflect new tool state */
    if (folderGrid && !folderGrid.classList.contains('view-hidden')) {
      showFolderView();
    } else if (inPlaylist) {
      applyViewMode();
      applyFilter();
    }
    /* Refresh player bar actions so move/trash show/hide with tool mode changes */
    updatePlayerBarActions();
  }

  function _saveToolState() {
    localStorage.setItem('ht-tools', JSON.stringify(_toolState));
    _applyToolState();
  }

  function openToolsPanel() {
    if (toolsBackdrop) toolsBackdrop.removeAttribute('hidden');
    /* Always show dupe count when panel opens — show even if toggle is off */
    if (_dupeShowLink && allItems.length > 0) {
      _ensureDupeMap();
      var dc = _getDupeCount();
      _dupeShowLink.textContent = dc > 0
        ? dc + ' Duplikat-Gruppe' + (dc !== 1 ? 'n' : '') + ' \u2014 Liste anzeigen'
        : 'Keine Duplikate gefunden';
      _dupeShowLink.style.display = 'inline-block';
    }
    if (typeof _router !== 'undefined') _router.update();
  }
  function closeToolsPanel() {
    if (toolsBackdrop) toolsBackdrop.setAttribute('hidden', '');
    if (typeof _router !== 'undefined') _router.update();
  }

  if (toolsPill) toolsPill.addEventListener('click', openToolsPanel);
  /* Split-pill toggle: directly activates/deactivates tool mode without opening the panel */
  var _toolsPillToggle = document.getElementById('tools-pill-toggle');
  if (_toolsPillToggle) {
    _toolsPillToggle.addEventListener('click', function(e) {
      e.stopPropagation(); /* prevent bubbling to tools-pill-wrap / toolsPill */
      _toolState.active = !_toolState.active;
      if (_toolState.active && _toolState.duplicates) _ensureDupeMap();
      if (!_toolState.active) _invalidateDupeMap();
      _saveToolState();
      if (inPlaylist) applyFilter();
    });
  }
  if (toolsClose) toolsClose.addEventListener('click', closeToolsPanel);
  if (toolsBackdrop) {
    toolsBackdrop.addEventListener('click', function(e) {
      if (e.target === toolsBackdrop) closeToolsPanel();
    });
  }
  var _dupePanelBackdrop = document.getElementById('dupe-panel-backdrop');
  var _dupePanelClose = document.getElementById('dupe-panel-close');
  var _dupePanelPlayAll = document.getElementById('dupe-panel-play-all');
  if (_dupePanelClose) _dupePanelClose.addEventListener('click', closeDupePanel);
  if (_dupePanelPlayAll) _dupePanelPlayAll.addEventListener('click', playDuplicates);
  if (_dupePanelBackdrop) {
    _dupePanelBackdrop.addEventListener('click', function(e) {
      if (e.target === _dupePanelBackdrop) closeDupePanel();
    });
  }
  if (_toolInlineRatings) {
    _toolInlineRatings.addEventListener('change', function() {
      _toolState.inlineRatings = _toolInlineRatings.checked;
      _saveToolState();
      /* Re-render current track list to add/remove inline stars */
      if (inPlaylist) applyFilter();
    });
  }
  if (_toolDownloads) {
    _toolDownloads.addEventListener('change', function() {
      _toolState.downloads = _toolDownloads.checked;
      _saveToolState();
    });
  }
  if (_toolPlaylists) {
    _toolPlaylists.addEventListener('change', function() {
      _toolState.playlists = _toolPlaylists.checked;
      _saveToolState();
    });
  }
  if (_toolDuplicates) {
    _toolDuplicates.addEventListener('change', function() {
      _toolState.duplicates = _toolDuplicates.checked;
      if (_toolDuplicates.checked) _ensureDupeMap();
      else _invalidateDupeMap();
      _saveToolState();
      /* Re-render to show/hide badges */
      if (inPlaylist) applyFilter();
    });
  }
  if (_dupeShowLink) {
    _dupeShowLink.addEventListener('click', function(e) {
      e.preventDefault();
      closeToolsPanel();
      playDuplicates();
    });
  }
  if (_toolFileMover) {
    _toolFileMover.addEventListener('change', function() {
      _toolState.fileMover = _toolFileMover.checked;
      _saveToolState();
      /* Re-render to show/hide move widgets */
      if (inPlaylist) applyFilter();
    });
  }
  if (_toolBpmCalc) {
    _toolBpmCalc.addEventListener('change', function() {
      _toolState.bpmCalc = _toolBpmCalc.checked;
      _saveToolState();
      /* Re-render so the "?" pills switch between static and clickable-glow */
      if (inPlaylist) applyFilter();
    });
  }
  /* Global Tools: "Ordnerdaten aller Ordner erneuern" button */
  if (_toolsGlobalRefreshBtn) {
    _toolsGlobalRefreshBtn.addEventListener('click', function() {
      closeToolsPanel();
      refreshCatalog();
    });
  }
  var _toolsActivateAll = document.getElementById('tools-activate-all');
  if (_toolsActivateAll) {
    _toolsActivateAll.addEventListener('click', function() {
      _toolState.active = !_toolState.active;
      /* When activating: if duplicates tool is configured, ensure dupe map is ready */
      if (_toolState.active && _toolState.duplicates) _ensureDupeMap();
      /* When deactivating: invalidate dupe map to release memory */
      if (!_toolState.active) _invalidateDupeMap();
      _saveToolState();
      if (inPlaylist) applyFilter();
    });
  }
  _applyToolState();

  /* ── Inline track rating stars ── */
  function renderInlineRating(t, idx) {
    if (!RATING_WRITE_ENABLED) return '';
    var rounded = Math.round(t.rating || 0);
    var html = '<span class="track-inline-rating" data-index="' + idx + '">';
    for (var i = 1; i <= 5; i++) {
      html += '<button class="track-inline-rating-star' + (i <= rounded ? ' active' : '') +
        '" data-star="' + i + '" data-index="' + idx + '" title="' + i + (i === 1 ? ' Stern' : ' Sterne') + '">' +
        (i <= rounded ? IC_STAR_FILLED : IC_STAR_EMPTY) + '</button>';
    }
    html += '</span>';
    return html;
  }

  function setInlineRating(idx, stars) {
    if (!RATING_WRITE_ENABLED) return;
    var t = filteredItems[idx];
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
      /* Check if visibility changed before patching (was grayed, now above threshold, or vice versa) */
      var wasHidden = !!t._hiddenShown;
      t.rating = d.rating;
      _patchAllItemsRating(t.relative_path, d.rating);
      var nowHidden = _effectiveThreshold > 0 && d.rating > 0 && d.rating < _effectiveThreshold;
      if (wasHidden !== nowHidden) {
        /* Visibility changed — full re-render so gray state is removed/added */
        if (inPlaylist) applyFilter();
      } else {
        /* Sync track list item (rating-bar + inline stars) and player bar */
        _updateTrackRatingBar(idx, d.rating);
        if (currentIndex === idx) renderPlayerRating(d.rating);
      }
      /* rebuild weighted shuffle queue so new rating is reflected */
      if (shuffleMode === 'weighted') rebuildShuffleQueue(currentIndex);
      var toastLabel2 = stars === 0
        ? 'Bewertung entfernt'
        : stars + (stars === 1 ? ' Stern' : ' Sterne') + ' vergeben';
      if (d.entry_id) {
        showRatingToastWithUndo(stars, prevRating, d.entry_id, t);
      } else {
        showToast(toastLabel2);
      }
    })
    .catch(function() {});
  }

  /* ── BPM calculate (Tools-panel "BPM berechnen") ──────────────────────────
     Click handler for the .meta-pill--calc button rendered by
     window.renderBpmPill() (webui/src/metricPill.ts) when a track's BPM is
     unknown and the tool is active. Stays Python-generated (not ported to
     TS) because it needs filteredItems/allItems/showToast — identifiers
     private to this script's own closure, not reachable from the separate
     static bundle. See docs/IMPLEMENTATION_PLAN.md Design Discussions
     ("Player-JS-Modulkopplung") for why that boundary exists. */
  function _patchAllItemsBpm(relativePath, bpm) {
    for (var i = 0; i < allItems.length; i++) {
      if (allItems[i].relative_path === relativePath) {
        allItems[i] = Object.assign({}, allItems[i], { bpm: bpm });
        break;
      }
    }
  }

  function _calculateBpmForTrack(idx, btnEl) {
    var t = filteredItems[idx];
    if (!t || !t.relative_path) return;
    if (btnEl) {
      btnEl.classList.add('meta-pill--calculating');
      btnEl.disabled = true;
      btnEl.textContent = '\u2026';
    }
    fetch(BPM_CALC_API_PATH, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: t.relative_path })
    })
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(d) {
        if (!d || !d.ok) {
          showToast((d && d.error) || 'BPM-Berechnung fehlgeschlagen');
          if (btnEl) {
            btnEl.classList.remove('meta-pill--calculating');
            btnEl.disabled = false;
            btnEl.textContent = '?';
          }
          return;
        }
        t.bpm = d.bpm;
        _patchAllItemsBpm(t.relative_path, d.bpm);
        if (btnEl && btnEl.parentNode && typeof window.renderBpmPill === 'function') {
          var wrap = document.createElement('span');
          wrap.innerHTML = window.renderBpmPill(d.bpm, BPM_MIN, BPM_MAX,
            { index: idx, relativePath: t.relative_path, calcEnabled: false });
          var newPill = wrap.firstChild;
          if (newPill) btnEl.parentNode.replaceChild(newPill, btnEl);
        }
        showToast('BPM berechnet: ' + Math.round(d.bpm));
      })
      .catch(function() {
        showToast('BPM-Berechnung fehlgeschlagen (Netzwerkfehler)');
        if (btnEl) {
          btnEl.classList.remove('meta-pill--calculating');
          btnEl.disabled = false;
          btnEl.textContent = '?';
        }
      });
  }

  /* ── Duplicate detection (client-side) ── */
  var IC_DUPLICATE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>';
  var _dupeMap = null;   /* Map<key, [itemIndex, ...]> — only groups with 2+ items */
  var _dupePaths = null;  /* Set<relative_path> — all paths that belong to a dupe group */
  var _dupeSafety = null; /* {relative_path: bool} — true=safe(≤2% deviation), false=warn(>2%) */
  var _DUPE_SAFE_THRESHOLD = 0.02; /* 2 % — max allowed relative deviation in size & duration */

  /* Return true when ALL pairs in the group have file_size AND duration within threshold.
     Returns false if any metric is missing (0) for any item, or if any pair exceeds the
     threshold in either metric. */
  function _isDupeGroupSafe(groupItems) {
    if (groupItems.length < 2) return true;
    for (var a = 0; a < groupItems.length; a++) {
      for (var b = a + 1; b < groupItems.length; b++) {
        var sA = groupItems[a].file_size || 0;
        var sB = groupItems[b].file_size || 0;
        var dA = groupItems[a].duration  || 0;
        var dB = groupItems[b].duration  || 0;
        /* Both values must be present and within threshold */
        if (!sA || !sB || Math.abs(sA - sB) / Math.max(sA, sB) > _DUPE_SAFE_THRESHOLD) return false;
        if (!dA || !dB || Math.abs(dA - dB) / Math.max(dA, dB) > _DUPE_SAFE_THRESHOLD) return false;
      }
    }
    return true;
  }

  /* ── Dupe-panel metadata formatters ── */
  function _fmtDuration(secs) {
    if (!secs) return '';
    var s = Math.round(secs);
    var h = Math.floor(s / 3600);
    var m = Math.floor((s % 3600) / 60);
    var sec = s % 60;
    if (h > 0) return h + ':' + (m < 10 ? '0' : '') + m + ':' + (sec < 10 ? '0' : '') + sec;
    return m + ':' + (sec < 10 ? '0' : '') + sec;
  }
  function _fmtFileSize(bytes) {
    if (!bytes) return '';
    if (bytes >= 1073741824) return (bytes / 1073741824).toFixed(1) + '\u00a0GB';
    if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + '\u00a0MB';
    if (bytes >= 1024) return Math.round(bytes / 1024) + '\u00a0KB';
    return bytes + '\u00a0B';
  }
  function _fmtDate(ts) {
    if (!ts) return '';
    var d = new Date(ts * 1000);
    return d.toLocaleDateString('de-DE', {day: '2-digit', month: '2-digit', year: 'numeric'});
  }

  function _normalizeStem(s) {
    if (!s) return '';
    s = s.replace(/&amp;/g, '&');
    s = s.replace(/\\(\\d{1,3}kbit_[A-Za-z]+\\)/gi, '');
    /* Strip ALL parenthesised Official-... blocks, not just "Official * Video" */
    s = s.replace(/\\(Official[^)]*\\)/gi, '');
    /* Strip common platform/promo tags that don't identify the song version */
    s = s.replace(/\\((?:Audio|Video|Music\\s+Video|Lyric\\s+Video|Lyrics|Lyric|Visualizer|Topic|HD|HQ)\\)/gi, '');
    s = s.replace(/\\(\\w*\\.[a-zA-Z]{2,5}\\)/gi, '');
    s = s.replace(/\\w*\\.(?:com|net|org|co\\.uk|de|vu|ru|pl)/gi, '');
    s = s.replace(/(?<=\\W)(?:featuring|feat\\.|feat)\\W/gi, 'feat. ');
    s = s.replace(/(?<=\\W)(?:produced by|produced|prod\\. by|prod by|prod\\.|prod)\\W/gi, 'prod. ');
    s = s.replace(/(?<=(?:\\W|\\(|\\[))(?:vs\\.|vs|versus)/gi, 'vs. ');
    s = s.replace(/\\(\\s*\\)|\\[\\s*\\]/g, '');
    s = s.replace(/ {2,}/g, ' ');
    return s.trim().toLowerCase();
  }

  function _dupeKey(item) {
    /* Build a stable key from artist + title.
       Version/mix descriptors (Remix, Extended, Live, Acoustic, etc.) are kept in the key
       so that different versions are NOT flagged as duplicates.
       Only strip markers that are purely promotional and don't identify a song version.
       Artist is included so that "Blümchen - Nur Geträumt" and "Nena - Nur Geträumt"
       are NOT considered duplicates. */
    var raw = item.title || '';
    if (!raw) {
      var rp = item.relative_path || '';
      var sl = rp.lastIndexOf('/');
      raw = sl >= 0 ? rp.substring(sl + 1) : rp;
      var dot = raw.lastIndexOf('.');
      if (dot > 0) raw = raw.substring(0, dot);
    }
    var cleaned = _normalizeStem(raw);
    /* Strip common download-duplicate suffixes: _2, (2), -2, _copy, - Copy, (copy) etc. */
    cleaned = cleaned.replace(/[\\s_-]*\\(?(?:copy|kopie)\\)?\\s*$/i, '');
    cleaned = cleaned.replace(/[\\s_-]+\\d{1,2}\\s*$/, '');
    cleaned = cleaned.replace(/\\s*\\(\\d{1,2}\\)\\s*$/, '');
    cleaned = cleaned.replace(/\\s*\\[\\d{1,2}\\]\\s*$/, '');
    /* Split on common separators */
    var parts = cleaned.split(/feat\\.|prod\\.|vs\\.|\\(|\\[| - |, | & |\\)|\\]/i);
    /* Strip ONLY purely promotional/label markers that don't differentiate song versions.
       Version keywords (remix, mix, extended, live, acoustic, instrumental, remaster, etc.)
       are intentionally kept so that e.g. "Song" and "Song - Remix" get different keys. */
    parts = parts.map(function(p) {
      return p.replace(/\\bofficial\\b|\\bexplicit\\b|\\bclean\\b/gi, '');
    });
    /* Strip non-word characters and filter short parts */
    parts = parts.map(function(p) { return p.replace(/[^a-z0-9]/gi, ''); });
    parts = parts.filter(function(p) { return p.length > 2; });
    /* Deduplicate and sort for stable key */
    var seen = {};
    var unique = [];
    parts.forEach(function(p) { if (!seen[p]) { seen[p] = true; unique.push(p); } });
    unique.sort();
    var titleKey = unique.join('|');
    /* Include the artist to prevent false positives across different artists */
    var artistRaw = (item.artist || '').toLowerCase().replace(/[^a-z0-9]/gi, '');
    if (artistRaw.length > 2) titleKey = artistRaw + '::' + titleKey;
    return titleKey;
  }

"""
