"""Shared server utilities — path validation and base CSS/JS for dark-theme media UIs.

INSTRUCTIONS (local):
- ``render_media_page()`` is the SINGLE HTML skeleton for all media types.
  Do NOT duplicate it in audio/video servers. Pass differences as parameters.
- CSS and JS are plain strings (no f-strings) to avoid Python escaping issues.
- ``render_player_js`` reads the ``items`` key from API responses. All API
  endpoints must return ``{ "items": [...] }`` — not ``tracks`` or ``videos``.
- ``resolve_media_path`` validates path traversal + suffix. Always use it
  instead of manual path joins in server endpoints.
"""

from __future__ import annotations

import html
import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import unquote


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def resolve_media_path(library_dir: Path, encoded_relative_path: str, allowed_suffixes: list[str]) -> Path:
    """Resolve and validate a requested media path inside a library root.

    Raises ValueError for path traversal or unsupported suffix, FileNotFoundError
    if the file does not exist on disk.
    """
    root = library_dir.resolve()
    relative_path = Path(unquote(encoded_relative_path))
    candidate = (root / relative_path).resolve()

    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Requested path escapes the configured library.") from exc

    if not candidate.is_file():
        raise FileNotFoundError(f"Media file not found: {relative_path}")
    if candidate.suffix.lower() not in allowed_suffixes:
        raise ValueError(f"Unsupported suffix for streaming: {candidate.suffix}")

    return candidate


# ---------------------------------------------------------------------------
# Shared dark-theme CSS
# ---------------------------------------------------------------------------


def render_base_css() -> str:
    """Return the shared dark-theme CSS used by both audio and video UIs."""
    return """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #121212; --surface: #1e1e1e; --surface2: #282828;
  --accent: #1db954; --text: #fff; --sub: #b3b3b3;
  --header-h: 56px; --filter-h: 52px; --player-h: 80px;
}
body {
  background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  height: 100dvh; display: flex; flex-direction: column; overflow: hidden;
}

/* ── Header ── */
header {
  height: var(--header-h); background: var(--surface);
  display: flex; align-items: center; padding: 0 1rem; gap: 0.75rem;
  flex-shrink: 0; border-bottom: 1px solid #333;
}
.logo { font-size: 1.1rem; font-weight: 700; color: var(--accent); }
.track-count { font-size: 0.8rem; color: var(--sub); margin-left: auto; }

/* ── Filter bar ── */
.filter-bar {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.5rem 1rem; background: var(--surface);
  border-bottom: 1px solid #333; flex-shrink: 0;
}
.filter-bar input, .filter-bar select {
  background: var(--surface2); color: var(--text);
  border: 1px solid #444; border-radius: 20px;
  padding: 0.4rem 0.8rem; font-size: 0.85rem; outline: none; min-width: 0;
}
.filter-bar input { flex: 1 1 0; }
.filter-bar input:focus, .filter-bar select:focus { border-color: var(--accent); }
.filter-bar select { color-scheme: dark; }

/* ── Item list ── */
.track-list-wrap { flex: 1 1 0; overflow-y: auto; }
.track-list { list-style: none; }
.track-item {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.65rem 1rem; cursor: pointer;
  border-bottom: 1px solid #222; transition: background 0.12s;
  -webkit-tap-highlight-color: transparent;
}
.track-item:hover  { background: var(--surface2); }
.track-item.active { background: #183320; }
.track-item.active .track-artist { color: var(--accent); }
.track-num {
  width: 26px; text-align: center; font-size: 0.78rem;
  color: var(--sub); flex-shrink: 0;
}
.track-item.active .num-text { display: none; }
.track-info { flex: 1 1 0; min-width: 0; }
.track-title {
  font-size: 0.92rem; font-weight: 500;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.track-artist {
  font-size: 0.8rem; color: var(--sub); margin-top: 2px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.empty-hint { text-align: center; color: var(--sub); padding: 3rem 1rem; font-size: 0.9rem; }

/* ── Bottom player bar ── */
.player-bar {
  height: var(--player-h); background: var(--surface);
  border-top: 1px solid #333; display: flex; align-items: center;
  padding: 0 0.75rem; gap: 0.65rem; flex-shrink: 0;
}
.player-info { flex: 0 0 150px; min-width: 0; }
.player-title {
  font-size: 0.85rem; font-weight: 600;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.player-artist {
  font-size: 0.75rem; color: var(--sub);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.player-controls { display: flex; align-items: center; gap: 0.4rem; flex-shrink: 0; }
.ctrl-btn {
  background: none; border: none; color: var(--text);
  cursor: pointer; font-size: 1.25rem; line-height: 1;
  padding: 0.35rem; border-radius: 50%; transition: color 0.12s;
  -webkit-tap-highlight-color: transparent;
}
.ctrl-btn:hover { color: var(--accent); }
.ctrl-btn.play-pause {
  background: var(--accent); color: #000; font-size: 1rem;
  width: 38px; height: 38px; display: flex; align-items: center; justify-content: center;
}
.ctrl-btn.play-pause:hover { background: #1ed760; }
.progress-wrap {
  flex: 1 1 0; min-width: 0; display: flex; align-items: center; gap: 0.4rem;
}
.time-label { font-size: 0.68rem; color: var(--sub); flex-shrink: 0; min-width: 2.2rem; }
.time-label.end { text-align: left; }
input[type=range] {
  -webkit-appearance: none; appearance: none;
  flex: 1 1 0; height: 4px; background: #555;
  border-radius: 2px; outline: none; cursor: pointer;
}
input[type=range]::-webkit-slider-thumb {
  -webkit-appearance: none; width: 12px; height: 12px;
  background: var(--text); border-radius: 50%;
}
input[type=range]:hover::-webkit-slider-thumb { background: var(--accent); }

@media (max-width: 480px) {
  .player-info { flex: 0 0 90px; }
  .filter-bar select:last-of-type { display: none; }
}
"""


# ---------------------------------------------------------------------------
# Shared player JavaScript
# ---------------------------------------------------------------------------


def render_player_js(api_path: str, item_noun: str = "track") -> str:
    """Return the media player JavaScript.

    *api_path* is the fetch URL (e.g. ``/api/audio/tracks``).
    *item_noun* is used for the counter label (``6 tracks`` / ``3 videos``).
    """
    return """
(function () {
  var INITIAL = JSON.parse(document.getElementById('initial-data').textContent);
  var API_PATH = '""" + api_path + """';
  var ITEM_NOUN = '""" + item_noun + """';

  var allTracks = [], currentIndex = -1;

  var player       = document.getElementById('player');
  var btnPlay      = document.getElementById('btn-play');
  var btnPrev      = document.getElementById('btn-prev');
  var btnNext      = document.getElementById('btn-next');
  var trackList    = document.getElementById('track-list');
  var trackCount   = document.getElementById('track-count');
  var playerTitle  = document.getElementById('player-title');
  var playerArtist = document.getElementById('player-artist');
  var progressBar  = document.getElementById('progress-bar');
  var timeCur      = document.getElementById('time-cur');
  var timeDur      = document.getElementById('time-dur');
  var searchInput  = document.getElementById('search-input');
  var artistFilter = document.getElementById('artist-filter');
  var sortField    = document.getElementById('sort-field');

  function fmtTime(s) {
    if (!isFinite(s)) return '0:00';
    var h = Math.floor(s / 3600);
    var m = Math.floor((s % 3600) / 60);
    var sec = String(Math.floor(s % 60)).padStart(2, '0');
    return h > 0 ? h + ':' + String(m).padStart(2, '0') + ':' + sec : m + ':' + sec;
  }

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function markActive() {
    document.querySelectorAll('.track-item').forEach(function (el, i) {
      el.classList.toggle('active', i === currentIndex);
      if (i === currentIndex) el.scrollIntoView({ block: 'nearest' });
    });
  }

  function playTrack(index) {
    if (index < 0 || index >= allTracks.length) return;
    currentIndex = index;
    var t = allTracks[index];
    player.src = t.stream_url;
    player.play();
    playerTitle.textContent  = t.title;
    playerArtist.textContent = t.artist || t.relative_path;
    btnPlay.textContent = '⏸';
    markActive();
  }

  function togglePlay() {
    if (currentIndex < 0 && allTracks.length) { playTrack(0); return; }
    if (player.paused) { player.play(); btnPlay.textContent = '⏸'; }
    else               { player.pause(); btnPlay.textContent = '▶'; }
  }

  btnPlay.addEventListener('click', togglePlay);
  btnPrev.addEventListener('click', function () {
    playTrack(currentIndex > 0 ? currentIndex - 1 : allTracks.length - 1);
  });
  btnNext.addEventListener('click', function () {
    playTrack(currentIndex < allTracks.length - 1 ? currentIndex + 1 : 0);
  });
  player.addEventListener('ended', function () {
    playTrack(currentIndex < allTracks.length - 1 ? currentIndex + 1 : 0);
  });
  player.addEventListener('pause', function () {
    if (!player.ended) btnPlay.textContent = '▶';
  });
  player.addEventListener('play', function () { btnPlay.textContent = '⏸'; });

  player.addEventListener('timeupdate', function () {
    if (!isFinite(player.duration)) return;
    progressBar.max   = player.duration;
    progressBar.value = player.currentTime;
    timeCur.textContent = fmtTime(player.currentTime);
  });
  player.addEventListener('loadedmetadata', function () {
    timeDur.textContent = fmtTime(player.duration);
    progressBar.max     = player.duration;
  });
  progressBar.addEventListener('input', function () {
    player.currentTime = progressBar.value;
  });

  function renderTracks(tracks) {
    allTracks = tracks;
    var noun = tracks.length !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN;
    trackCount.textContent = tracks.length + ' ' + noun;
    if (!tracks.length) {
      trackList.innerHTML = '<li class="empty-hint">No matching items found. Run a sync first.</li>';
      return;
    }
    trackList.innerHTML = tracks.map(function (t, i) {
      var subtitle = t.artist || t.relative_path;
      return (
        '<li class="track-item' + (i === currentIndex ? ' active' : '') +
        '" data-index="' + i + '">' +
          '<span class="track-num"><span class="num-text">' + (i + 1) + '</span></span>' +
          '<div class="track-info">' +
            '<div class="track-title">'  + escHtml(t.title)  + '</div>' +
            '<div class="track-artist">' + escHtml(subtitle) + '</div>' +
          '</div>' +
        '</li>'
      );
    }).join('');
    document.querySelectorAll('.track-item').forEach(function (el) {
      el.addEventListener('click', function () { playTrack(Number(el.dataset.index)); });
    });
  }

  async function fetchTracks() {
    var params = new URLSearchParams({
      q: searchInput.value, artist: artistFilter.value, sort: sortField.value
    });
    var res = await fetch(API_PATH + '?' + params.toString());
    if (!res.ok) {
      trackList.innerHTML = '<li class="empty-hint">Could not load items.</li>'; return;
    }
    var payload = await res.json();
    currentIndex = -1;
    renderTracks(payload.items || []);
  }

  searchInput.addEventListener('input', fetchTracks);
  artistFilter.addEventListener('change', fetchTracks);
  sortField.addEventListener('change', fetchTracks);

  renderTracks(INITIAL);
}());
"""


# ---------------------------------------------------------------------------
# HTML skeleton builder
# ---------------------------------------------------------------------------


def render_media_page(
    *,
    title: str,
    emoji: str,
    items_json: str,
    artist_options_html: str,
    media_element_tag: str,
    extra_css: str = "",
    api_path: str,
    item_noun: str = "track",
    filter2_label: str = "Artist",
) -> str:
    """Build the complete HTML page for a media streaming UI.

    *media_element_tag* should be ``audio`` or ``video``.
    """
    css = render_base_css() + extra_css
    js = render_player_js(api_path=api_path, item_noun=item_noun)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{css}</style>
</head>
<body>
  <header>
    <span class="logo">{emoji} {html.escape(title)}</span>
    <span class="track-count" id="track-count"></span>
  </header>

  <div class="filter-bar">
    <input id="search-input" type="search" placeholder="Search…" autocomplete="off" />
    <select id="artist-filter">
      <option value="all">All {html.escape(filter2_label.lower())}s</option>
      {artist_options_html}
    </select>
    <select id="sort-field">
      <option value="artist">{html.escape(filter2_label)} ↕</option>
      <option value="title">Title ↕</option>
      <option value="path">Path ↕</option>
    </select>
  </div>

  <div class="track-list-wrap">
    <ul class="track-list" id="track-list"></ul>
  </div>

  <{media_element_tag} id="player" preload="auto"></{media_element_tag}>

  <div class="player-bar">
    <div class="player-info">
      <div class="player-title"  id="player-title">No {item_noun} selected</div>
      <div class="player-artist" id="player-artist">–</div>
    </div>
    <div class="player-controls">
      <button class="ctrl-btn"            id="btn-prev" title="Previous">⏮</button>
      <button class="ctrl-btn play-pause" id="btn-play" title="Play / Pause">▶</button>
      <button class="ctrl-btn"            id="btn-next" title="Next">⏭</button>
    </div>
    <div class="progress-wrap">
      <span class="time-label"     id="time-cur">0:00</span>
      <input type="range" id="progress-bar" min="0" step="0.1" value="0" />
      <span class="time-label end" id="time-dur">0:00</span>
    </div>
  </div>

  <script id="initial-data" type="application/json">{items_json}</script>
  <script>{js}</script>
</body>
</html>
"""

