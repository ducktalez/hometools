"""Minimal local web server for the audio streaming prototype."""

from __future__ import annotations

import html
import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from hometools.config import get_audio_library_dir
from hometools.constants import AUDIO_SUFFIX
from hometools.streaming.audio.catalog import (
    AudioTrack,
    build_audio_index,
    list_artists,
    query_tracks,
)


HTML_PAGE_TITLE = "hometools"


def _render_css() -> str:
    """Return the player stylesheet (plain string, not an f-string)."""
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

/* ── Track list ── */
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
.track-item.active .track-num::before { content: '♪'; color: var(--accent); }
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


def _render_player_js() -> str:
    """Return the audio player JavaScript (plain string, not an f-string)."""
    return """
(function () {
  var INITIAL = JSON.parse(document.getElementById('initial-data').textContent);

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
    return Math.floor(s / 60) + ':' + String(Math.floor(s % 60)).padStart(2, '0');
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
    playerArtist.textContent = t.artist;
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
    trackCount.textContent = tracks.length + ' track' + (tracks.length !== 1 ? 's' : '');
    if (!tracks.length) {
      trackList.innerHTML = '<li class="empty-hint">No matching tracks found. Run a sync first.</li>';
      return;
    }
    trackList.innerHTML = tracks.map(function (t, i) {
      return (
        '<li class="track-item' + (i === currentIndex ? ' active' : '') +
        '" data-index="' + i + '">' +
          '<span class="track-num"><span class="num-text">' + (i + 1) + '</span></span>' +
          '<div class="track-info">' +
            '<div class="track-title">'  + escHtml(t.title)  + '</div>' +
            '<div class="track-artist">' + escHtml(t.artist) + '</div>' +
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
    var res = await fetch('/api/audio/tracks?' + params.toString());
    if (!res.ok) {
      trackList.innerHTML = '<li class="empty-hint">Could not load tracks.</li>'; return;
    }
    var payload = await res.json();
    currentIndex = -1;
    renderTracks(payload.tracks || []);
  }

  searchInput.addEventListener('input', fetchTracks);
  artistFilter.addEventListener('change', fetchTracks);
  sortField.addEventListener('change', fetchTracks);

  renderTracks(INITIAL);
}());
"""


def resolve_audio_path(library_dir: Path, encoded_relative_path: str) -> Path:
    """Resolve and validate a requested track path inside the library root."""
    root = library_dir.resolve()
    relative_path = Path(unquote(encoded_relative_path))
    candidate = (root / relative_path).resolve()

    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Requested path escapes the configured audio library.") from exc

    if not candidate.is_file():
        raise FileNotFoundError(f"Audio file not found: {relative_path}")
    if candidate.suffix.lower() not in AUDIO_SUFFIX:
        raise ValueError(f"Unsupported audio suffix for streaming: {candidate.suffix}")

    return candidate


def render_audio_index_html(tracks: list[AudioTrack], library_dir: Path) -> str:
    """Render the music player UI — dark theme, fixed bottom player, scrollable track list."""
    import json as _json

    artists = list_artists(tracks)
    artist_options = "\n".join(
        f'<option value="{html.escape(a, quote=True)}">{html.escape(a)}</option>'
        for a in artists
    )
    tracks_json = _json.dumps([t.to_dict() for t in tracks], ensure_ascii=False)

    skeleton = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{HTML_PAGE_TITLE}</title>
  <style>{_render_css()}</style>
</head>
<body>
  <header>
    <span class="logo">🎵 {HTML_PAGE_TITLE}</span>
    <span class="track-count" id="track-count"></span>
  </header>

  <div class="filter-bar">
    <input id="search-input" type="search" placeholder="Search…" autocomplete="off" />
    <select id="artist-filter">
      <option value="all">All artists</option>
      {artist_options}
    </select>
    <select id="sort-field">
      <option value="artist">Artist ↕</option>
      <option value="title">Title ↕</option>
      <option value="path">Path ↕</option>
    </select>
  </div>

  <div class="track-list-wrap">
    <ul class="track-list" id="track-list"></ul>
  </div>

  <audio id="player" preload="auto"></audio>

  <div class="player-bar">
    <div class="player-info">
      <div class="player-title"  id="player-title">No track selected</div>
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

  <script id="initial-data" type="application/json">{tracks_json}</script>"""

    return skeleton + "\n  <script>" + _render_player_js() + "  </script>\n</body>\n</html>\n"


def create_app(library_dir: Path | None = None) -> Any:
    """Create the FastAPI application for local audio streaming."""
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse, HTMLResponse

    resolved_library_dir = (library_dir or get_audio_library_dir()).expanduser()
    app = FastAPI(title="hometools audio streaming prototype")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "library_dir": str(resolved_library_dir),
        }

    @app.get("/", response_class=HTMLResponse)
    def audio_home() -> HTMLResponse:
        tracks = build_audio_index(resolved_library_dir)
        return HTMLResponse(render_audio_index_html(tracks, resolved_library_dir))

    @app.get("/api/audio/tracks")
    def audio_tracks(q: str | None = None, artist: str | None = None, sort: str = "artist") -> dict[str, object]:
        tracks = build_audio_index(resolved_library_dir)
        filtered_tracks = query_tracks(tracks, q=q, artist=artist, sort_by=sort)
        return {
            "library_dir": str(resolved_library_dir),
            "count": len(filtered_tracks),
            "tracks": [track.to_dict() for track in filtered_tracks],
            "artists": list_artists(tracks),
            "query": {
                "q": q or "",
                "artist": artist or "all",
                "sort": sort,
            },
        }

    @app.get("/audio/stream")
    def audio_stream(path: str) -> FileResponse:
        try:
            file_path = resolve_audio_path(resolved_library_dir, path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        return FileResponse(file_path, media_type=media_type, filename=file_path.name)

    return app



