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
import logging
import mimetypes
import os
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import unquote

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Library directory validation
# ---------------------------------------------------------------------------

_check_cache: dict[str, tuple[tuple[bool, str], float]] = {}
_CHECK_CACHE_TTL = 10.0  # seconds


def check_library_accessible(library_dir: Path, timeout: float = 3.0) -> tuple[bool, str]:
    """Check whether a library directory is accessible.

    Uses a **timeout** so that unreachable network paths (UNC/SMB) don't
    block the server.  Results are cached for ``_CHECK_CACHE_TTL`` seconds
    to avoid repeated slow probes on every request.

    Returns ``(ok, message)``.
    """
    key = str(library_dir)
    now = time.monotonic()

    # Return cached result if fresh enough
    if key in _check_cache:
        cached_result, cached_at = _check_cache[key]
        if now - cached_at < _CHECK_CACHE_TTL:
            return cached_result

    path_str = key
    is_unc = path_str.startswith("\\\\") or path_str.startswith("//")

    result: list[tuple[bool, str]] = []

    def _probe() -> None:
        try:
            if not library_dir.exists():
                hint = ""
                if is_unc:
                    hint = (
                        " Tipp: LIBRARY_DIR sollte ein schneller lokaler Ordner sein. "
                        "Den NAS-Pfad stattdessen als NAS_DIR für 'sync' verwenden."
                    )
                result.append((False, f"Verzeichnis existiert nicht: {library_dir}{hint}"))
            elif not library_dir.is_dir():
                result.append((False, f"Pfad ist kein Verzeichnis: {library_dir}"))
            else:
                result.append((True, "ok"))
        except OSError as exc:
            reason = f"Pfad nicht erreichbar: {exc}"
            if is_unc:
                reason += (
                    " — UNC-Netzwerkpfade (\\\\Server\\Share) erfordern, "
                    "dass das NAS eingeschaltet und die Freigabe authentifiziert ist."
                )
            result.append((False, reason))

    thread = threading.Thread(target=_probe, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if not result:
        # Thread is still running → timeout
        msg = (
            f"Zeitüberschreitung ({timeout}s): Pfad nicht erreichbar: {library_dir}"
        )
        if is_unc:
            msg += (
                " — UNC-Netzwerkpfade können bei nicht erreichbarem NAS "
                "lange blockieren. Verwenden Sie einen lokalen Ordner als LIBRARY_DIR."
            )
        outcome = (False, msg)
    else:
        outcome = result[0]

    _check_cache[key] = (outcome, now)
    return outcome


def render_error_page(title: str, emoji: str, error_message: str, library_dir: Path) -> str:
    """Return a minimal dark-theme HTML page showing a library access error."""
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} — Fehler</title>
<style>
body {{ background:#121212; color:#fff; font-family:system-ui,sans-serif;
       display:flex; align-items:center; justify-content:center; min-height:100vh; margin:0; }}
.card {{ background:#1e1e1e; border-radius:12px; padding:2rem 2.5rem; max-width:600px; }}
h1 {{ margin:0 0 1rem; font-size:1.3rem; }}
.err {{ color:#ff6b6b; background:#2a1515; border-radius:8px; padding:1rem; font-size:0.9rem;
        word-break:break-all; margin:1rem 0; }}
.path {{ color:#b3b3b3; font-size:0.85rem; }}
.hint {{ color:#b3b3b3; font-size:0.85rem; margin-top:1rem; }}
code {{ background:#282828; padding:0.15rem 0.4rem; border-radius:4px; font-size:0.85rem; }}
</style></head><body>
<div class="card">
<h1>{emoji} {html.escape(title)}</h1>
<div class="err">⚠ {html.escape(error_message)}</div>
<div class="path">Konfigurierter Pfad: <code>{html.escape(str(library_dir))}</code></div>
<div class="hint">
  Prüfen Sie die Einstellung in <code>.env</code> und stellen Sie sicher,
  dass das Verzeichnis existiert und erreichbar ist.<br>
  Der Server läuft weiter — laden Sie die Seite neu, sobald das Problem behoben ist.
</div>
</div></body></html>"""


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def safe_resolve(p: Path) -> Path:
    """Normalise a path **without** filesystem I/O.

    ``Path.resolve()`` on Windows calls ``GetFinalPathNameByHandle`` which can
    hang indefinitely on unreachable UNC/SMB shares.  This function uses
    ``os.path.normpath`` + ``os.path.abspath`` instead — it resolves ``..``
    and ``.`` segments and makes the path absolute, but does **not** follow
    symlinks or touch the network.
    """
    return Path(os.path.normpath(os.path.abspath(str(p))))


def resolve_media_path(library_dir: Path, encoded_relative_path: str, allowed_suffixes: list[str]) -> Path:
    """Resolve and validate a requested media path inside a library root.

    Raises ValueError for path traversal or unsupported suffix, FileNotFoundError
    if the file does not exist on disk.
    """
    root = safe_resolve(library_dir)
    relative_path = Path(unquote(encoded_relative_path))
    candidate = safe_resolve(root / relative_path)

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
# Progressive Web App (PWA) support
# ---------------------------------------------------------------------------


def render_pwa_manifest(
    name: str,
    short_name: str,
    theme_color: str = "#1db954",
    background_color: str = "#121212",
) -> str:
    """Return a PWA manifest.json as string.

    ``display: standalone`` removes the browser chrome (URL bar, tabs)
    so the app feels native on iOS and Android.
    """
    import json
    manifest = {
        "name": name,
        "short_name": short_name,
        "start_url": "/",
        "display": "standalone",
        "background_color": background_color,
        "theme_color": theme_color,
        "icons": [
            {"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml"},
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }
    return json.dumps(manifest, indent=2, ensure_ascii=False)


def render_pwa_service_worker() -> str:
    """Return a minimal service worker JS for PWA installability and caching."""
    return """\
const CACHE_NAME = 'hometools-v1';

self.addEventListener('install', event => {
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(names =>
      Promise.all(names.filter(n => n !== CACHE_NAME).map(n => caches.delete(n)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  // Don't cache streaming endpoints or API calls
  if (url.pathname.includes('/stream') || url.pathname.startsWith('/api/')) return;
  // Cache-first for icons, network-first for everything else
  if (url.pathname.startsWith('/icon')) {
    event.respondWith(
      caches.match(event.request).then(r => r || fetch(event.request).then(resp => {
        const clone = resp.clone();
        caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
        return resp;
      }))
    );
  }
});
"""


def render_pwa_icon_svg(emoji: str, bg_color: str = "#1db954") -> str:
    """Return an SVG icon for the PWA using an emoji character."""
    return f"""\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" rx="20" fill="{bg_color}"/>
  <text x="50" y="50" text-anchor="middle" dominant-baseline="central"
        font-size="60">{emoji}</text>
</svg>"""


def render_pwa_icon_png(emoji: str, size: int, bg_color: str = "#1db954") -> bytes:
    """Return a PNG icon rendered from an SVG.

    Falls back to a simple colored square if cairosvg is not available.
    """
    svg = render_pwa_icon_svg(emoji, bg_color)
    try:
        import cairosvg  # type: ignore[import-untyped]
        return cairosvg.svg2png(bytestring=svg.encode(), output_width=size, output_height=size)
    except ImportError:
        pass
    # Fallback: create a minimal 1-color PNG (icon will just be the bg color)
    import struct, zlib
    # Simple RGBA PNG
    width = height = size
    def _raw_row():
        return b'\x00' + bytes(_parse_hex(bg_color)) * width
    raw = b''.join(_raw_row() for _ in range(height))
    def _chunk(ctype, data):
        c = ctype + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    return sig + _chunk(b'IHDR', ihdr) + _chunk(b'IDAT', zlib.compress(raw)) + _chunk(b'IEND', b'')


def _parse_hex(color: str) -> tuple[int, int, int]:
    """Parse a hex color string to (r, g, b)."""
    c = color.lstrip('#')
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def render_pwa_head_tags(theme_color: str = "#1db954") -> str:
    """Return HTML <head> tags required for PWA + iOS standalone mode."""
    return f"""\
  <link rel="manifest" href="/manifest.json">
  <meta name="theme-color" content="{theme_color}">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <link rel="apple-touch-icon" href="/icon-192.png">
  <link rel="icon" href="/icon.svg" type="image/svg+xml">"""


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
  --sat: env(safe-area-inset-top, 0px);
  --sab: env(safe-area-inset-bottom, 0px);
  --sal: env(safe-area-inset-left, 0px);
  --sar: env(safe-area-inset-right, 0px);
}
body {
  background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  height: 100dvh; display: flex; flex-direction: column; overflow: hidden;
}

/* ── Header ── */
header {
  height: calc(var(--header-h) + var(--sat));
  padding-top: var(--sat);
  background: var(--surface);
  display: flex; align-items: center; padding-left: max(1rem, var(--sal)); padding-right: max(1rem, var(--sar)); gap: 0.75rem;
  flex-shrink: 0; border-bottom: 1px solid #333;
}
.logo { font-size: 1.1rem; font-weight: 700; color: var(--accent); }
.track-count { font-size: 0.8rem; color: var(--sub); margin-left: auto; }

/* ── Filter bar ── */
.filter-bar {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.5rem max(1rem, var(--sal)) 0.5rem max(1rem, var(--sar));
  background: var(--surface);
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
  padding: 0.65rem max(1rem, var(--sar)) 0.65rem max(1rem, var(--sal));
  cursor: pointer;
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

/* ── Bottom player bar — shared ── */
.player-bar {
  padding-bottom: var(--sab);
  background: var(--surface);
  border-top: 1px solid #333; flex-shrink: 0;
}
.player-info { min-width: 0; }
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
.time-label { font-size: 0.68rem; color: var(--sub); flex-shrink: 0; min-width: 2.2rem; }
.time-label.end { text-align: left; }

/* ── Classic player bar — single row ── */
.player-bar.classic {
  display: flex; align-items: center;
  height: calc(var(--player-h) + var(--sab));
  padding-left: max(0.75rem, var(--sal)); padding-right: max(0.75rem, var(--sar)); gap: 0.65rem;
}
.player-bar.classic .player-info { flex: 0 0 150px; }
.player-bar.classic .progress-wrap {
  flex: 1 1 0; min-width: 0; display: flex; align-items: center; gap: 0.4rem;
}
.player-bar.classic input[type=range] {
  -webkit-appearance: none; appearance: none;
  flex: 1 1 0; height: 4px; background: #555;
  border-radius: 2px; outline: none; cursor: pointer;
}
.player-bar.classic input[type=range]::-webkit-slider-thumb {
  -webkit-appearance: none; width: 12px; height: 12px;
  background: var(--text); border-radius: 50%;
}
.player-bar.classic input[type=range]:hover::-webkit-slider-thumb { background: var(--accent); }

/* ── Waveform player bar — two rows ── */
.player-bar.waveform {
  display: flex; flex-direction: column;
}
.player-bar-top {
  display: flex; align-items: center;
  padding: 0.4rem max(0.75rem, var(--sal)) 0 max(0.75rem, var(--sar));
  gap: 0.65rem;
}
.player-bar-top .player-info { flex: 0 1 auto; max-width: 45%; }
.player-bar-top .player-controls { flex: 1 1 0; justify-content: center; }
.player-bar.waveform .progress-wrap {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.25rem max(0.75rem, var(--sal)) 0.5rem max(0.75rem, var(--sar));
}
.progress-track {
  flex: 1 1 0; position: relative; height: 48px; min-width: 0; cursor: pointer;
}
.progress-track.video-mode { height: 28px; }
.waveform-canvas {
  display: block; width: 100%; height: 100%; border-radius: 4px;
}
.progress-track input[type=range] {
  -webkit-appearance: none; appearance: none;
  position: absolute; top: 0; left: 0;
  width: 100%; height: 100%; opacity: 0;
  cursor: pointer; margin: 0; z-index: 2;
  background: transparent;
}
.progress-track input[type=range]::-webkit-slider-thumb {
  -webkit-appearance: none; width: 1px; height: 1px; background: transparent;
}

/* ── Video thumbnail preview ── */
.thumb-preview {
  display: none; position: absolute; bottom: calc(100% + 8px);
  transform: translateX(-50%);
  background: var(--surface2); border: 2px solid #444;
  border-radius: 6px; padding: 4px; z-index: 100;
  pointer-events: none;
}
.thumb-preview.visible { display: block; }
.thumb-preview canvas {
  display: block; width: 160px; height: 90px; border-radius: 3px;
}
.thumb-time {
  display: block; text-align: center; font-size: 0.72rem;
  color: var(--text); margin-top: 3px;
}

/* ── Folder grid ── */
.folder-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem; padding: 1rem max(1rem, var(--sar)) 1rem max(1rem, var(--sal));
  overflow-y: auto; flex: 1 1 0;
}
.folder-card {
  background: var(--surface2); border-radius: 8px;
  padding: 1rem; cursor: pointer; position: relative;
  transition: background 0.15s, transform 0.1s;
}
.folder-card:hover { background: #333; transform: translateY(-2px); }
.folder-icon { font-size: 2rem; margin-bottom: 0.3rem; }
.folder-name {
  font-size: 0.95rem; font-weight: 600;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.folder-count { font-size: 0.78rem; color: var(--sub); margin-top: 2px; }
.folder-play-btn {
  position: absolute; bottom: 0.75rem; right: 0.75rem;
  background: var(--accent); color: #000; border: none;
  border-radius: 50%; width: 36px; height: 36px;
  cursor: pointer; font-size: 1rem;
  display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: opacity 0.15s;
}
.folder-card:hover .folder-play-btn { opacity: 1; }
.folder-play-btn:hover { background: #1ed760; }
.back-btn {
  background: var(--surface2); border: 1px solid #444; color: var(--accent);
  cursor: pointer; font-size: 1rem; padding: 0.3rem 0.6rem;
  border-radius: 6px; display: none;
  transition: background 0.12s, color 0.12s;
}
.back-btn:hover { background: #333; color: #1ed760; }
.play-all-btn {
  background: var(--accent); color: #000; border: none;
  border-radius: 20px; padding: 0.3rem 0.8rem; cursor: pointer;
  font-size: 0.8rem; font-weight: 600; display: none;
  transition: background 0.12s; white-space: nowrap;
}
.play-all-btn:hover { background: #1ed760; }
.file-card .folder-icon { font-size: 1.6rem; }
.view-hidden { display: none !important; }

/* ── Breadcrumb navigation ── */
.breadcrumb {
  display: none; padding: 0.4rem max(1rem, var(--sal)) 0.4rem max(1rem, var(--sar));
  background: var(--surface);
  border-bottom: 1px solid #333; font-size: 0.82rem; flex-shrink: 0;
  overflow-x: auto; white-space: nowrap;
}
.breadcrumb.visible { display: block; }
.breadcrumb a {
  color: var(--accent); text-decoration: none; cursor: pointer;
}
.breadcrumb a:hover { text-decoration: underline; }
.breadcrumb .sep { color: var(--sub); margin: 0 0.4rem; }
.breadcrumb .current { color: var(--text); font-weight: 500; }

/* ── View toggle (list / grid) ── */
.view-toggle {
  background: none; border: 1px solid #444; color: var(--sub);
  border-radius: 4px; padding: 0.25rem 0.5rem; cursor: pointer;
  font-size: 0.85rem; transition: color 0.12s, border-color 0.12s;
  flex-shrink: 0;
}
.view-toggle:hover { color: var(--accent); border-color: var(--accent); }

/* ── Folder list mode ── */
.folder-grid.list-mode {
  display: flex; flex-direction: column; gap: 0; padding: 0;
}
.folder-grid.list-mode .folder-card {
  border-radius: 0; padding: 0.6rem 1rem;
  display: flex; align-items: center; gap: 0.75rem;
  border-bottom: 1px solid #282828;
}
.folder-grid.list-mode .folder-card:hover { transform: none; }
.folder-grid.list-mode .folder-icon { font-size: 1.3rem; margin-bottom: 0; flex-shrink: 0; }
.folder-grid.list-mode .folder-name { font-size: 0.9rem; flex: 1 1 0; }
.folder-grid.list-mode .folder-count { margin-top: 0; flex-shrink: 0; }
.folder-grid.list-mode .folder-play-btn {
  position: static; opacity: 0; width: 30px; height: 30px; font-size: 0.8rem;
  flex-shrink: 0;
}
.folder-grid.list-mode .folder-card:hover .folder-play-btn { opacity: 1; }

@media (max-width: 480px) {
  .player-info { flex: 0 0 90px; }
  .folder-grid { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); }
}
"""


# ---------------------------------------------------------------------------
# Shared player JavaScript
# ---------------------------------------------------------------------------


def render_player_js(api_path: str, item_noun: str = "track", file_emoji: str = "\U0001f3b5",
                     player_bar_style: str = "classic") -> str:
    """Return the media player JavaScript with hierarchical folder navigation.

    Default view is a folder list (configurable via toggle to grid).
    Clicking a folder navigates deeper into the hierarchy.  Leaf folders
    (no sub-folders) are displayed as playlists.  A breadcrumb trail and
    back button allow navigating up.  View preference is stored in
    localStorage.
    """
    # -- waveform/thumbnail JS (only for waveform mode) -----------------------
    if player_bar_style == "waveform":
        waveform_js = """
  /* ── waveform & thumbnail elements ── */
  var progressTrack  = document.getElementById('progress-track');
  var waveformCanvas = document.getElementById('waveform-canvas');
  var waveformCtx    = waveformCanvas ? waveformCanvas.getContext('2d') : null;
  var thumbPreview   = document.getElementById('thumb-preview');
  var thumbCanvas    = document.getElementById('thumb-canvas');
  var thumbCtx       = thumbCanvas ? thumbCanvas.getContext('2d') : null;
  var thumbTimeEl    = document.getElementById('thumb-time');
  var isAudioMode    = player.tagName === 'AUDIO';
  var isVideoMode    = player.tagName === 'VIDEO';
  var waveformData   = null;
  var waveformAbort  = null;
  var thumbVideo     = null;
"""
    else:
        waveform_js = ""

    if player_bar_style == "waveform":
        waveform_setup_js = """
  /* ── waveform (audio) & thumbnail (video) setup ── */
  if (isVideoMode && progressTrack) {
    progressTrack.classList.add('video-mode');
    thumbVideo = document.createElement('video');
    thumbVideo.preload = 'metadata';
    thumbVideo.muted = true;
    thumbVideo.crossOrigin = 'anonymous';
    thumbVideo.style.display = 'none';
    document.body.appendChild(thumbVideo);
    thumbVideo.addEventListener('seeked', function() {
      if (thumbCtx) thumbCtx.drawImage(thumbVideo, 0, 0, 160, 90);
    });
    progressTrack.addEventListener('mousemove', function(e) {
      if (!player.duration || !isFinite(player.duration)) return;
      var rect = progressTrack.getBoundingClientRect();
      var ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      var seekTime = ratio * player.duration;
      var pctLeft = Math.max(5, Math.min(95, ratio * 100));
      thumbPreview.style.left = pctLeft + '%';
      thumbPreview.classList.add('visible');
      thumbTimeEl.textContent = fmtTime(seekTime);
      if (thumbVideo.getAttribute('src') !== player.src) thumbVideo.src = player.src;
      thumbVideo.currentTime = seekTime;
    });
    progressTrack.addEventListener('mouseleave', function() {
      thumbPreview.classList.remove('visible');
    });
  }

  function generateWaveform(url) {
    if (!isAudioMode || !waveformCanvas) return;
    if (waveformAbort) waveformAbort.abort();
    waveformAbort = new AbortController();
    waveformData = null;
    drawWaveform(0);
    fetch(url, { signal: waveformAbort.signal })
      .then(function(r) { return r.arrayBuffer(); })
      .then(function(buf) {
        var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        return audioCtx.decodeAudioData(buf).then(function(decoded) {
          audioCtx.close();
          return decoded;
        });
      })
      .then(function(audioBuffer) {
        var rawData = audioBuffer.getChannelData(0);
        var samples = 120;
        var blockSize = Math.floor(rawData.length / samples);
        if (blockSize < 1) return;
        var data = [];
        for (var i = 0; i < samples; i++) {
          var sum = 0;
          for (var j = 0; j < blockSize; j++) sum += Math.abs(rawData[i * blockSize + j]);
          data.push(sum / blockSize);
        }
        var max = Math.max.apply(null, data);
        if (max > 0) data = data.map(function(d) { return d / max; });
        waveformData = data;
        var prog = player.duration > 0 ? player.currentTime / player.duration : 0;
        drawWaveform(prog);
      })
      .catch(function(e) {
        if (e.name !== 'AbortError') waveformData = null;
      });
  }

  function drawWaveform(progress) {
    if (!waveformCanvas || !waveformCtx) return;
    var W = 600, H = 48;
    waveformCanvas.width = W;
    waveformCanvas.height = H;
    waveformCtx.clearRect(0, 0, W, H);
    var accent = getComputedStyle(document.documentElement)
      .getPropertyValue('--accent').trim() || '#1db954';
    if (isAudioMode && waveformData && waveformData.length) {
      var BAR_COUNT = 120;
      var slotW = W / BAR_COUNT;
      var gapW = slotW * 0.15;
      var barW = slotW - gapW;
      var playedBars = Math.floor(progress * BAR_COUNT);
      for (var i = 0; i < BAR_COUNT; i++) {
        var di = Math.min(Math.floor(i * waveformData.length / BAR_COUNT), waveformData.length - 1);
        var bh = Math.max(2, waveformData[di] * H * 0.85);
        var x = i * slotW, y = (H - bh) / 2;
        waveformCtx.fillStyle = i < playedBars ? accent : '#555';
        waveformCtx.fillRect(x, y, barW, bh);
      }
    } else {
      var barH = 6, cy = H / 2, ty = cy - barH / 2;
      var playedW = W * progress;
      waveformCtx.fillStyle = '#555';
      waveformCtx.fillRect(0, ty, W, barH);
      if (playedW > 0) {
        waveformCtx.fillStyle = accent;
        waveformCtx.fillRect(0, ty, playedW, barH);
      }
      waveformCtx.fillStyle = '#fff';
      waveformCtx.beginPath();
      waveformCtx.arc(Math.max(7, Math.min(W - 7, playedW)), cy, 7, 0, Math.PI * 2);
      waveformCtx.fill();
    }
  }
"""
    else:
        waveform_setup_js = """
  function generateWaveform() {}
  function drawWaveform() {}
"""

    return """
(function () {
  var INITIAL = JSON.parse(document.getElementById('initial-data').textContent);
  var ITEM_NOUN = '""" + item_noun + """';
  var FILE_EMOJI = '""" + file_emoji + """';

  var allItems = INITIAL;
  var currentPath = '';
  var playlistItems = [];
  var filteredItems = [];
  var currentIndex = -1;
  var inPlaylist = false;

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
  var sortField    = document.getElementById('sort-field');
  var folderGrid   = document.getElementById('folder-grid');
  var trackView    = document.getElementById('track-view');
  var filterBar    = document.querySelector('.filter-bar');
  var backBtn      = document.getElementById('back-btn');
  var headerTitle  = document.querySelector('.logo');
  var playerBar    = document.querySelector('.player-bar');
  var playAllBtn   = document.getElementById('play-all-btn');
  var originalTitle = headerTitle.textContent;
  var breadcrumb  = document.getElementById('breadcrumb');
  var viewToggle  = document.getElementById('view-toggle');
  var viewMode    = localStorage.getItem('ht-view-mode') || 'list';
""" + waveform_js + """

  /* ── helpers ── */
  function fmtTime(s) {
    if (!isFinite(s)) return '0:00';
    var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
    var sec = String(Math.floor(s % 60)).padStart(2, '0');
    return h > 0 ? h + ':' + String(m).padStart(2, '0') + ':' + sec : m + ':' + sec;
  }
  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
""" + waveform_setup_js + """

  /* items under a path prefix (recursive) */
  function itemsUnder(path) {
    if (!path) return allItems;
    var prefix = path + '/';
    return allItems.filter(function(it) { return it.relative_path.startsWith(prefix); });
  }

  /* compute direct sub-folders and loose files at a path level */
  function contentsAt(path) {
    var items = itemsUnder(path);
    var folderMap = {};
    var files = [];
    var off = path ? path.length + 1 : 0;
    items.forEach(function(it) {
      var rest = it.relative_path.substring(off);
      var slash = rest.indexOf('/');
      if (slash >= 0) {
        var name = rest.substring(0, slash);
        if (!folderMap[name]) folderMap[name] = 0;
        folderMap[name]++;
      } else {
        files.push(it);
      }
    });
    var folders = Object.keys(folderMap)
      .sort(function(a, b) { return a.localeCompare(b); })
      .map(function(n) { return { name: n, count: folderMap[n] }; });
    return { folders: folders, files: files };
  }

  function leafName(path) {
    if (!path) return originalTitle;
    var i = path.lastIndexOf('/');
    return i >= 0 ? path.substring(i + 1) : path;
  }

  function parentPath(path) {
    if (!path) return '';
    var i = path.lastIndexOf('/');
    return i >= 0 ? path.substring(0, i) : '';
  }

  /* ── breadcrumb ── */
  function renderBreadcrumb() {
    if (!currentPath) { breadcrumb.classList.remove('visible'); return; }
    breadcrumb.classList.add('visible');
    var parts = currentPath.split('/');
    var h = '<a data-path="">\\u{1F3E0} Home</a>';
    for (var i = 0; i < parts.length; i++) {
      h += '<span class="sep">\\u203A</span>';
      var p = parts.slice(0, i + 1).join('/');
      if (i < parts.length - 1) {
        h += '<a data-path="' + escHtml(p) + '">' + escHtml(parts[i]) + '</a>';
      } else {
        h += '<span class="current">' + escHtml(parts[i]) + '</span>';
      }
    }
    breadcrumb.innerHTML = h;
    breadcrumb.querySelectorAll('a').forEach(function(a) {
      a.addEventListener('click', function() {
        currentPath = a.dataset.path;
        showFolderView();
      });
    });
  }

  /* ── view toggle ── */
  function applyViewMode() {
    if (viewMode === 'list') {
      folderGrid.classList.add('list-mode');
      viewToggle.textContent = '\\u25A6';
      viewToggle.title = 'Zur Kachelansicht wechseln';
    } else {
      folderGrid.classList.remove('list-mode');
      viewToggle.textContent = '\\u2630';
      viewToggle.title = 'Zur Listenansicht wechseln';
    }
  }

  /* ── folder view ── */
  function showFolderView() {
    inPlaylist = false;
    var c = contentsAt(currentPath);

    /* empty library */
    if (c.folders.length === 0 && c.files.length === 0) {
      folderGrid.classList.remove('view-hidden');
      trackView.classList.add('view-hidden');
      filterBar.classList.add('view-hidden');
      playAllBtn.style.display = 'none';
      headerTitle.textContent = currentPath ? leafName(currentPath) : originalTitle;
      backBtn.style.display = currentPath ? 'inline-block' : 'none';
      if (currentIndex < 0) playerBar.classList.add('view-hidden');
      folderGrid.innerHTML = '<div class="empty-hint">No items found. Run a sync first.</div>';
      trackCount.textContent = '';
      renderBreadcrumb();
      applyViewMode();
      return;
    }

    /* leaf folder (no sub-folders) → playlist */
    if (c.folders.length === 0) {
      showPlaylist(c.files, false);
      return;
    }

    folderGrid.classList.remove('view-hidden');
    trackView.classList.add('view-hidden');
    filterBar.classList.add('view-hidden');
    if (currentIndex < 0) playerBar.classList.add('view-hidden');

    headerTitle.textContent = currentPath ? leafName(currentPath) : originalTitle;
    backBtn.style.display = currentPath ? 'inline-block' : 'none';
    playAllBtn.style.display = '';

    var label = c.folders.length + ' folder' + (c.folders.length !== 1 ? 's' : '');
    if (c.files.length > 0) {
      label += ', ' + c.files.length + ' ' + (c.files.length !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN);
    }
    trackCount.textContent = label;

    var html = '';
    c.folders.forEach(function(f) {
      var noun = f.count !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN;
      html += '<div class="folder-card" data-folder="' + escHtml(f.name) + '">' +
        '<div class="folder-icon">\\u{1F4C1}</div>' +
        '<div class="folder-name">' + escHtml(f.name) + '</div>' +
        '<div class="folder-count">' + f.count + ' ' + noun + '</div>' +
        '<button class="folder-play-btn" title="Play all">\\u25B6</button>' +
      '</div>';
    });
    c.files.forEach(function(it, i) {
      html += '<div class="folder-card file-card" data-file-idx="' + i + '">' +
        '<div class="folder-icon">' + FILE_EMOJI + '</div>' +
        '<div class="folder-name">' + escHtml(it.title) + '</div>' +
        '<div class="folder-count">' + escHtml(it.artist || '') + '</div>' +
      '</div>';
    });
    folderGrid.innerHTML = html;

    folderGrid.querySelectorAll('.folder-card:not(.file-card)').forEach(function(card) {
      var pb = card.querySelector('.folder-play-btn');
      card.addEventListener('click', function(e) {
        if (e.target !== pb) navigateInto(card.dataset.folder);
      });
      pb.addEventListener('click', function(e) {
        e.stopPropagation();
        playAllIn(card.dataset.folder);
      });
    });

    var looseFiles = c.files;
    folderGrid.querySelectorAll('.file-card').forEach(function(card) {
      card.addEventListener('click', function() {
        showPlaylist(looseFiles, true, Number(card.dataset.fileIdx));
      });
    });

    renderBreadcrumb();
    applyViewMode();
  }

  function navigateInto(name) {
    currentPath = currentPath ? currentPath + '/' + name : name;
    showFolderView();
  }

  function playAllIn(name) {
    var full = currentPath ? currentPath + '/' + name : name;
    var items = itemsUnder(full);
    if (items.length) { currentPath = full; showPlaylist(items, true); }
  }

  /* ── playlist view ── */
  function showPlaylist(items, autoplay, startIdx) {
    inPlaylist = true;
    playlistItems = items;

    headerTitle.textContent = currentPath ? leafName(currentPath) : originalTitle;
    backBtn.style.display = currentPath ? 'inline-block' : 'none';
    playAllBtn.style.display = 'none';

    folderGrid.classList.add('view-hidden');
    trackView.classList.remove('view-hidden');
    filterBar.classList.remove('view-hidden');
    playerBar.classList.remove('view-hidden');

    searchInput.value = '';
    currentIndex = -1;
    renderBreadcrumb();
    applyFilter();
    if (autoplay && playlistItems.length) playTrack(startIdx || 0);
  }

  /* ── back ── */
  function goBack() {
    if (inPlaylist) {
      var c = contentsAt(currentPath);
      if (c.folders.length > 0) { showFolderView(); return; }
    }
    currentPath = parentPath(currentPath);
    showFolderView();
  }

  /* play all items under current path */
  function playAllCurrent() {
    var items = itemsUnder(currentPath);
    if (!items.length) items = contentsAt(currentPath).files;
    if (items.length) showPlaylist(items, true);
  }

  /* ── filter / sort within playlist ── */
  function applyFilter() {
    var needle = searchInput.value.trim().toLowerCase();
    var sortBy = sortField.value;
    var items = playlistItems;
    if (needle) {
      items = items.filter(function(t) {
        return t.title.toLowerCase().indexOf(needle) >= 0 ||
               t.artist.toLowerCase().indexOf(needle) >= 0 ||
               t.relative_path.toLowerCase().indexOf(needle) >= 0;
      });
    }
    items = items.slice().sort(function(a, b) {
      if (sortBy === 'title') return a.title.localeCompare(b.title) || a.relative_path.localeCompare(b.relative_path);
      if (sortBy === 'path') return a.relative_path.localeCompare(b.relative_path);
      return a.artist.localeCompare(b.artist) || a.title.localeCompare(b.title);
    });
    renderTracks(items);
  }

  /* ── track list rendering ── */
  function markActive() {
    document.querySelectorAll('.track-item').forEach(function(el, i) {
      el.classList.toggle('active', i === currentIndex);
      if (i === currentIndex) el.scrollIntoView({ block: 'nearest' });
    });
  }

  function renderTracks(tracks) {
    filteredItems = tracks;
    var noun = tracks.length !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN;
    trackCount.textContent = tracks.length + ' ' + noun;
    if (!tracks.length) {
      trackList.innerHTML = '<li class="empty-hint">No matching items.</li>';
      return;
    }
    trackList.innerHTML = tracks.map(function(t, i) {
      var subtitle = t.artist || t.relative_path;
      return '<li class="track-item' + (i === currentIndex ? ' active' : '') +
        '" data-index="' + i + '">' +
        '<span class="track-num"><span class="num-text">' + (i + 1) + '</span></span>' +
        '<div class="track-info">' +
          '<div class="track-title">' + escHtml(t.title) + '</div>' +
          '<div class="track-artist">' + escHtml(subtitle) + '</div>' +
        '</div></li>';
    }).join('');
    document.querySelectorAll('.track-item').forEach(function(el) {
      el.addEventListener('click', function() { playTrack(Number(el.dataset.index)); });
    });
  }

  /* ── playback ── */
  /* Background audio fallback for iOS PWA standalone mode:
     When the app goes to background, iOS pauses <video> elements.
     We mirror the source to a hidden <audio> element so playback continues. */
  var bgAudio = null;
  var isStandalone = window.matchMedia('(display-mode: standalone)').matches
                  || window.navigator.standalone === true;

  function ensureBgAudio() {
    if (bgAudio) return bgAudio;
    bgAudio = document.createElement('audio');
    bgAudio.style.display = 'none';
    bgAudio.preload = 'none';
    document.body.appendChild(bgAudio);
    /* When bg audio track ends, advance to next */
    bgAudio.addEventListener('ended', function() {
      playTrack(currentIndex < filteredItems.length - 1 ? currentIndex + 1 : 0);
    });
    return bgAudio;
  }

  /* Sync bg audio when app goes to background / foreground */
  if (isStandalone) {
    document.addEventListener('visibilitychange', function() {
      if (player.tagName === 'AUDIO') return; /* audio element handles bg natively */
      if (document.hidden && !player.paused) {
        /* App going to background with video playing → start bg audio */
        var bg = ensureBgAudio();
        bg.src = player.src;
        bg.currentTime = player.currentTime;
        bg.play();
        player.pause();
      } else if (!document.hidden && bgAudio && !bgAudio.paused) {
        /* App coming back → sync back to video */
        player.currentTime = bgAudio.currentTime;
        player.play();
        bgAudio.pause();
        bgAudio.removeAttribute('src');
      }
    });
  }

  /* Media Session API — lock screen controls & background playback signal */
  function updateMediaSession(t) {
    if (!('mediaSession' in navigator)) return;
    navigator.mediaSession.metadata = new MediaMetadata({
      title: t.title,
      artist: t.artist || '',
      album: ITEM_NOUN === 'video' ? 'hometools video' : 'hometools audio',
      artwork: [{ src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
                { src: '/icon-512.png', sizes: '512x512', type: 'image/png' }]
    });
    navigator.mediaSession.setActionHandler('play', function() { player.play(); });
    navigator.mediaSession.setActionHandler('pause', function() { player.pause(); });
    navigator.mediaSession.setActionHandler('previoustrack', function() {
      playTrack(currentIndex > 0 ? currentIndex - 1 : filteredItems.length - 1);
    });
    navigator.mediaSession.setActionHandler('nexttrack', function() {
      playTrack(currentIndex < filteredItems.length - 1 ? currentIndex + 1 : 0);
    });
    try {
      navigator.mediaSession.setActionHandler('seekto', function(details) {
        player.currentTime = details.seekTime;
      });
    } catch(e) {}
  }

  function playTrack(index) {
    if (index < 0 || index >= filteredItems.length) return;
    currentIndex = index;
    var t = filteredItems[index];
    /* Stop bg audio if active */
    if (bgAudio && !bgAudio.paused) { bgAudio.pause(); bgAudio.removeAttribute('src'); }
    player.src = t.stream_url;
    player.play();
    playerTitle.textContent = t.title;
    playerArtist.textContent = t.artist || t.relative_path;
    btnPlay.textContent = '\\u23F8';
    playerBar.classList.remove('view-hidden');
    markActive();
    updateMediaSession(t);
    generateWaveform(t.stream_url);
  }

  function togglePlay() {
    if (currentIndex < 0 && filteredItems.length) { playTrack(0); return; }
    if (player.paused) {
      /* If bg audio is playing (came back from background), sync first */
      if (bgAudio && !bgAudio.paused) {
        player.currentTime = bgAudio.currentTime;
        bgAudio.pause(); bgAudio.removeAttribute('src');
      }
      player.play(); btnPlay.textContent = '\\u23F8';
    } else {
      player.pause(); btnPlay.textContent = '\\u25B6';
    }
  }

  btnPlay.addEventListener('click', togglePlay);
  btnPrev.addEventListener('click', function() {
    playTrack(currentIndex > 0 ? currentIndex - 1 : filteredItems.length - 1);
  });
  btnNext.addEventListener('click', function() {
    playTrack(currentIndex < filteredItems.length - 1 ? currentIndex + 1 : 0);
  });
  player.addEventListener('ended', function() {
    playTrack(currentIndex < filteredItems.length - 1 ? currentIndex + 1 : 0);
  });
  player.addEventListener('pause', function() { if (!player.ended) btnPlay.textContent = '\\u25B6'; });
  player.addEventListener('play',  function() { btnPlay.textContent = '\\u23F8'; });
  player.addEventListener('timeupdate', function() {
    if (!isFinite(player.duration)) return;
    progressBar.max = player.duration; progressBar.value = player.currentTime;
    timeCur.textContent = fmtTime(player.currentTime);
    drawWaveform(player.currentTime / player.duration);
  });
  player.addEventListener('loadedmetadata', function() {
    timeDur.textContent = fmtTime(player.duration); progressBar.max = player.duration;
  });
  progressBar.addEventListener('input', function() { player.currentTime = progressBar.value; });

  /* bg audio events — keep UI in sync when playing in background */
  if (isStandalone) {
    setInterval(function() {
      if (bgAudio && !bgAudio.paused && document.hidden) {
        if (isFinite(bgAudio.duration)) {
          progressBar.max = bgAudio.duration;
          progressBar.value = bgAudio.currentTime;
          timeCur.textContent = fmtTime(bgAudio.currentTime);
          drawWaveform(bgAudio.currentTime / bgAudio.duration);
        }
      }
    }, 1000);
  }

  backBtn.addEventListener('click', goBack);
  playAllBtn.addEventListener('click', playAllCurrent);
  viewToggle.addEventListener('click', function() {
    viewMode = viewMode === 'list' ? 'grid' : 'list';
    localStorage.setItem('ht-view-mode', viewMode);
    applyViewMode();
  });
  searchInput.addEventListener('input', applyFilter);
  sortField.addEventListener('change', applyFilter);

  /* ── init ── */
  applyViewMode();
  showFolderView();
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
    media_element_tag: str,
    extra_css: str = "",
    api_path: str,
    item_noun: str = "track",
    theme_color: str = "#1db954",
    player_bar_style: str = "classic",
) -> str:
    """Build the complete HTML page for a media streaming UI.

    The page starts in folder-grid view.  Clicking a folder shows the
    track list with the player.  A back button returns to the grid.
    *media_element_tag* should be ``audio`` or ``video``.

    *player_bar_style* selects the bottom player layout:
    ``classic``  — single-row with inline range slider (default).
    ``waveform`` — two-row layout with audio waveform / video thumbnails.
    """
    css = render_base_css() + extra_css
    js = render_player_js(api_path=api_path, item_noun=item_noun, file_emoji=emoji,
                          player_bar_style=player_bar_style)
    pwa_tags = render_pwa_head_tags(theme_color=theme_color)
    sw_register = """
  <script>
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(function(){});
    }
  </script>"""

    if player_bar_style == "waveform":
        player_bar_html = f"""
  <div class="player-bar waveform view-hidden">
    <div class="player-bar-top">
      <div class="player-info">
        <div class="player-title"  id="player-title">No {item_noun} selected</div>
        <div class="player-artist" id="player-artist">&ndash;</div>
      </div>
      <div class="player-controls">
        <button class="ctrl-btn"            id="btn-prev" title="Previous">&#9198;</button>
        <button class="ctrl-btn play-pause" id="btn-play" title="Play / Pause">&#9654;</button>
        <button class="ctrl-btn"            id="btn-next" title="Next">&#9197;</button>
      </div>
    </div>
    <div class="progress-wrap">
      <span class="time-label"     id="time-cur">0:00</span>
      <div class="progress-track" id="progress-track">
        <canvas id="waveform-canvas"></canvas>
        <input type="range" id="progress-bar" min="0" step="0.1" value="0" />
        <div class="thumb-preview" id="thumb-preview">
          <canvas id="thumb-canvas" width="160" height="90"></canvas>
          <span class="thumb-time" id="thumb-time"></span>
        </div>
      </div>
      <span class="time-label end" id="time-dur">0:00</span>
    </div>
  </div>"""
    else:
        player_bar_html = f"""
  <div class="player-bar classic view-hidden">
    <div class="player-info">
      <div class="player-title"  id="player-title">No {item_noun} selected</div>
      <div class="player-artist" id="player-artist">&ndash;</div>
    </div>
    <div class="player-controls">
      <button class="ctrl-btn"            id="btn-prev" title="Previous">&#9198;</button>
      <button class="ctrl-btn play-pause" id="btn-play" title="Play / Pause">&#9654;</button>
      <button class="ctrl-btn"            id="btn-next" title="Next">&#9197;</button>
    </div>
    <div class="progress-wrap">
      <span class="time-label"     id="time-cur">0:00</span>
      <input type="range" id="progress-bar" min="0" step="0.1" value="0" />
      <span class="time-label end" id="time-dur">0:00</span>
    </div>
  </div>"""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{html.escape(title)}</title>
{pwa_tags}
  <style>{css}</style>
</head>
<body>
  <header>
    <button class="back-btn" id="back-btn" title="Back to folders">&larr;</button>
    <span class="logo">{emoji} {html.escape(title)}</span>
    <button class="play-all-btn" id="play-all-btn" title="Play all">&#9654; Play All</button>
    <button class="view-toggle" id="view-toggle" title="Ansicht wechseln">&#9776;</button>
    <span class="track-count" id="track-count"></span>
  </header>

  <!-- breadcrumb navigation -->
  <nav class="breadcrumb" id="breadcrumb"></nav>

  <!-- folder grid (default view) -->
  <div class="folder-grid" id="folder-grid"></div>

  <!-- filter bar (visible inside a folder) -->
  <div class="filter-bar view-hidden">
    <input id="search-input" type="search" placeholder="Search…" autocomplete="off" />
    <select id="sort-field">
      <option value="title">Title &UpDownArrow;</option>
      <option value="artist">Artist &UpDownArrow;</option>
      <option value="path">Path &UpDownArrow;</option>
    </select>
  </div>

  <!-- track list (visible inside a folder) -->
  <div class="track-list-wrap view-hidden" id="track-view">
    <ul class="track-list" id="track-list"></ul>
  </div>

  <{media_element_tag} id="player" preload="auto" playsinline></{media_element_tag}>
{player_bar_html}

  <script id="initial-data" type="application/json">{items_json}</script>
  <script>{js}</script>
{sw_register}
</body>
</html>
"""

