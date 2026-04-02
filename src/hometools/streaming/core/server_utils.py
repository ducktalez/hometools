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
import os
import threading
import time
from pathlib import Path
from urllib.parse import unquote

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SVG Icons — inline SVGs render consistently on all platforms (no iOS emoji)
# ---------------------------------------------------------------------------

SVG_PLAY = '<svg viewBox="0 0 24 24"><polygon points="6,3 20,12 6,21"/></svg>'
SVG_PAUSE = '<svg viewBox="0 0 24 24"><rect x="5" y="3" width="4" height="18"/><rect x="15" y="3" width="4" height="18"/></svg>'
SVG_PREV = '<svg viewBox="0 0 24 24"><polygon points="18,3 8,12 18,21"/><rect x="5" y="3" width="3" height="18"/></svg>'
SVG_NEXT = '<svg viewBox="0 0 24 24"><polygon points="6,3 16,12 6,21"/><rect x="16" y="3" width="3" height="18"/></svg>'
SVG_PIP = '<svg viewBox="0 0 24 24"><rect x="2" y="4" width="20" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><rect x="11" y="11" width="10" height="8" rx="1"/></svg>'
SVG_BACK = '<svg viewBox="0 0 24 24"><polyline points="15,18 9,12 15,6" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
SVG_MENU = '<svg viewBox="0 0 24 24"><line x1="3" y1="6" x2="21" y2="6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="3" y1="12" x2="21" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="3" y1="18" x2="21" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>'
SVG_DOWNLOAD = '<svg viewBox="0 0 24 24"><path d="M12 3v12m0 0l-4-4m4 4l4-4M5 19h14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
SVG_CHECK = '<svg viewBox="0 0 24 24"><polyline points="4,12 10,18 20,6" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
SVG_FOLDER_PLAY = '<svg viewBox="0 0 24 24"><polygon points="6,3 20,12 6,21"/></svg>'
SVG_PIN = '<svg viewBox="0 0 24 24"><path d="M16 4l4 4-2.5 2.5 1.5 5.5-6-6-5 5v-2l3.5-3.5L6 4h2l5 1.5z" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
SVG_STAR = '<svg viewBox="0 0 24 24"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="currentColor"/></svg>'
SVG_STAR_EMPTY = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"/></svg>'
SVG_SHUFFLE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16,3 21,3 21,8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21,16 21,21 16,21"/><line x1="4" y1="4" x2="9" y2="9"/></svg>'
SVG_REPEAT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="17,1 21,5 17,9"/><path d="M3,11V9a4,4,0,0,1,4-4h14"/><polyline points="7,23 3,19 7,15"/><path d="M21,13v2a4,4,0,0,1-4,4H3"/></svg>'
SVG_HISTORY = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><polyline points="12,7 12,12 15,15"/><polyline points="3.05,10 3,12 5,11.5"/></svg>'
SVG_EDIT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>'
SVG_LYRICS = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14,2 14,8 20,8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>'
SVG_PLAYLIST = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>'


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
                    " — UNC-Netzwerkpfade (\\\\Server\\Share) erfordern, dass das NAS eingeschaltet und die Freigabe authentifiziert ist."
                )
            result.append((False, reason))

    thread = threading.Thread(target=_probe, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if not result:
        # Thread is still running → timeout
        msg = f"Zeitüberschreitung ({timeout}s): Pfad nicht erreichbar: {library_dir}"
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


def build_index_status_payload(
    *,
    library_dir: Path,
    item_label: str,
    library_ok: bool,
    library_message: str,
    cache_status: dict[str, object],
    issues_summary: dict[str, object] | None = None,
    todo_summary: dict[str, object] | None = None,
) -> dict[str, object]:
    """Return a normalized API payload describing index-build state.

    Used by both audio and video servers so the frontend can diagnose slow
    background scans consistently.
    """
    path_str = str(library_dir)
    is_unc = path_str.startswith("\\\\") or path_str.startswith("//")
    detail = library_message
    if library_ok and bool(cache_status.get("building")):
        runtime = cache_status.get("build_running_for_seconds")
        if runtime is not None:
            detail = f"Building {item_label} index in background for {float(runtime):.1f}s"
        else:
            detail = f"Building {item_label} index in background"
        if is_unc:
            detail += ". UNC/NAS libraries can be very slow on the first scan; a local LIBRARY_DIR plus NAS sync is recommended."

    payload = {
        "library_dir": path_str,
        "library_accessible": library_ok,
        "detail": detail,
        "cache": cache_status,
    }
    if issues_summary is not None:
        payload["issues"] = issues_summary
    if todo_summary is not None:
        payload["todos"] = todo_summary
    return payload


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
    display_mode: str = "standalone",
    shortcuts: list[dict[str, object]] | None = None,
) -> str:
    """Return a PWA manifest.json as string.

    *display_mode* controls the browser chrome:
    ``standalone`` — no browser UI (feels native, best for audio).
    ``minimal-ui`` — minimal back-button; allows PiP & fullscreen on iOS
                     (required for video background playback).

    *shortcuts* — optional list of PWA shortcut dicts with keys
    ``name``, ``short_name``, ``url``, and optionally ``icons``.
    """
    import json

    manifest = {
        "name": name,
        "short_name": short_name,
        "start_url": "/",
        "display": display_mode,
        "background_color": background_color,
        "theme_color": theme_color,
        "icons": [
            {"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml"},
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }
    if shortcuts:
        manifest["shortcuts"] = shortcuts
    return json.dumps(manifest, indent=2, ensure_ascii=False)


def render_pwa_service_worker() -> str:
    """Return a service worker JS for PWA caching, offline UI, and download support."""
    return """\
const CACHE_NAME = 'hometools-v7';
const DOWNLOAD_CACHE = 'hometools-downloads-v1';

self.addEventListener('install', event => {
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(names =>
      Promise.all(names.filter(n => n !== CACHE_NAME && n !== DOWNLOAD_CACHE).map(n => caches.delete(n)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  
  // Streaming endpoints — try network first, then serve from IndexedDB cache
  if (url.pathname.includes('/stream') || url.pathname.includes('/audio/') || url.pathname.includes('/video/')) {
    event.respondWith(
      fetch(event.request)
        .then(resp => resp)
        .catch(() => {
          // Offline — serve from IndexedDB downloads cache
          return serveFromIndexedDB(event.request);
        })
    );
    return;
  }
  
  // API calls — network first
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request).catch(() => new Response('{}', { status: 503 }))
    );
    return;
  }
  
  // Icons — cache first
  if (url.pathname.startsWith('/icon') || url.pathname.startsWith('/manifest')) {
    event.respondWith(
      caches.match(event.request).then(r => r || fetch(event.request).then(resp => {
        const clone = resp.clone();
        caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
        return resp;
      }))
    );
    return;
  }
  
  // HTML / navigation — network first, cache fallback
  if (event.request.mode === 'navigate' || event.request.destination === 'document') {
    event.respondWith(
      fetch(event.request).then(resp => {
        const clone = resp.clone();
        caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
        return resp;
      }).catch(() =>
        caches.match(event.request).then(r => r || new Response('Offline — page not cached', { status: 503 }))
      )
    );
    return;
  }

  // Static assets (JS/CSS) — cache first, fallback to network
  if (
      event.request.destination === 'script' || 
      event.request.destination === 'style') {
    event.respondWith(
      caches.match(event.request).then(r => {
        if (r) return r;
        return fetch(event.request).then(resp => {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
          return resp;
        }).catch(() => new Response('Offline — page not cached', { status: 503 }));
      })
    );
    return;
  }
});

// Download progress tracking — client sends updates
self.addEventListener('message', event => {
  if (event.data.type === 'CACHE_DOWNLOAD') {
    // Client (JS) sends download blob after fetch completes
    const { url, blob, title } = event.data;
    caches.open(DOWNLOAD_CACHE).then(cache => {
      cache.put(url, new Response(blob, { status: 200 }));
      // Notify all clients that download is cached
      self.clients.matchAll().then(clients => {
        clients.forEach(client => {
          client.postMessage({
            type: 'DOWNLOAD_CACHED',
            url: url,
            title: title
          });
        });
      });
    });
  } else if (event.data.type === 'DELETE_DOWNLOAD') {
    caches.open(DOWNLOAD_CACHE).then(cache => cache.delete(event.data.url)).then(() => {
      self.clients.matchAll().then(clients => {
        clients.forEach(client => {
          client.postMessage({
            type: 'DOWNLOAD_DELETED',
            url: event.data.url
          });
        });
      });
    });
  }
});

function openDownloadDB() {
  return new Promise((resolve, reject) => {
    const dbReq = indexedDB.open('hometools-downloads', 2);
    dbReq.onerror = () => reject(new Error('IndexedDB open failed'));
    dbReq.onupgradeneeded = (e) => {
      const db = e.target.result;
      let store;
      if (!db.objectStoreNames.contains('downloads')) {
        store = db.createObjectStore('downloads', { keyPath: 'id', autoIncrement: true });
      } else {
        store = e.target.transaction.objectStore('downloads');
      }
      if (!store.indexNames.contains('streamUrl')) store.createIndex('streamUrl', 'streamUrl', { unique: true });
      if (!store.indexNames.contains('status')) store.createIndex('status', 'status', { unique: false });
      if (!store.indexNames.contains('timestamp')) store.createIndex('timestamp', 'timestamp', { unique: false });
      if (!store.indexNames.contains('title')) store.createIndex('title', 'title', { unique: false });
    };
    dbReq.onsuccess = () => resolve(dbReq.result);
  });
}

function findDownloadByUrl(streamUrl) {
  return openDownloadDB().then(db => new Promise((resolve, reject) => {
    const tx = db.transaction('downloads', 'readonly');
    const store = tx.objectStore('downloads');
    const index = store.index('streamUrl');
    const query = index.get(streamUrl);
    query.onerror = () => reject(new Error('Download lookup failed'));
    query.onsuccess = () => resolve(query.result || null);
  }));
}

function responseFromBlob(blob, request) {
  const type = blob.type || 'application/octet-stream';
  const range = request.headers.get('range');
  if (range) {
    const match = /bytes=([0-9]+)-([0-9]*)/.exec(range);
    if (match) {
      const start = parseInt(match[1], 10);
      const end = match[2] ? Math.min(parseInt(match[2], 10), blob.size - 1) : blob.size - 1;
      if (start >= blob.size) {
        return new Response(null, {
          status: 416,
          headers: new Headers({
            'Content-Range': 'bytes */' + blob.size,
            'Accept-Ranges': 'bytes'
          })
        });
      }
      const chunk = blob.slice(start, end + 1, type);
      return new Response(chunk, {
        status: 206,
        statusText: 'Partial Content (from offline cache)',
        headers: new Headers({
          'Content-Type': type,
          'Content-Length': String(end - start + 1),
          'Content-Range': 'bytes ' + start + '-' + end + '/' + blob.size,
          'Accept-Ranges': 'bytes',
          'Cache-Control': 'public, max-age=31536000'
        })
      });
    }
  }
  return new Response(blob, {
    status: 200,
    statusText: 'OK (from offline cache)',
    headers: new Headers({
      'Content-Type': type,
      'Content-Length': String(blob.size),
      'Accept-Ranges': 'bytes',
      'Cache-Control': 'public, max-age=31536000'
    })
  });
}

/* Serve cached downloads from IndexedDB */
function serveFromIndexedDB(request) {
  const streamUrl = typeof request === 'string' ? request : request.url;
  const req = typeof request === 'string' ? new Request(streamUrl) : request;
  return findDownloadByUrl(streamUrl).then(result => {
    if (result && result.blob) {
      return responseFromBlob(result.blob, req);
    }
    throw new Error('Download not found in cache');
  }).catch(err => {
    // Fallback: return error response
    return new Response(
      'Offline — ' + (err.message || 'stream not cached'),
      { status: 503, statusText: 'Service Unavailable' }
    );
  });
}
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
    import struct
    import zlib

    # Simple RGBA PNG
    width = height = size

    def _raw_row():
        return b"\x00" + bytes(_parse_hex(bg_color)) * width

    raw = b"".join(_raw_row() for _ in range(height))

    def _chunk(ctype, data):
        c = ctype + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(raw)) + _chunk(b"IEND", b"")


def _parse_hex(color: str) -> tuple[int, int, int]:
    """Parse a hex color string to (r, g, b)."""
    c = color.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def render_pwa_head_tags(theme_color: str = "#1db954", standalone: bool = True) -> str:
    """Return HTML <head> tags required for PWA + iOS.

    When *standalone* is ``True`` (default, best for audio), the
    ``apple-mobile-web-app-capable`` meta tag is included so iOS opens
    the app without browser chrome.  Set to ``False`` for video — the
    standalone WebView on iOS aggressively suspends media on background
    and disables PiP / fullscreen.
    """
    apple_capable = (
        '\n  <meta name="apple-mobile-web-app-capable" content="yes">'
        '\n  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
        if standalone
        else ""
    )
    return f"""\
  <link rel="manifest" href="/manifest.json">
  <meta name="theme-color" content="{theme_color}">{apple_capable}
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
.logo { font-size: 1.1rem; font-weight: 700; color: var(--accent); user-select: none; }
.logo-home-btn {
  background: none; border: none; font-size: 1.4rem; line-height: 1;
  cursor: pointer; padding: 0 2px; color: inherit; flex-shrink: 0;
  -webkit-tap-highlight-color: transparent;
}
.logo-home-btn:hover { opacity: 0.75; }
.logo-title {
  font-size: 1.1rem; font-weight: 700; color: var(--accent);
  user-select: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.track-count { font-size: 0.8rem; color: var(--sub); margin-left: auto; }
.offline-close, .offline-action-btn {
  background: var(--surface2); color: var(--text); border: 1px solid #444;
  border-radius: 999px; cursor: pointer; padding: 0.4rem 0.8rem;
  font-size: 0.8rem; -webkit-tap-highlight-color: transparent;
}
.offline-close:hover, .offline-action-btn:hover {
  color: var(--accent); border-color: var(--accent);
}
.downloaded-pill {
  font-size: 0.72rem; color: var(--sub); border: 1px solid #3a3a3a;
  border-radius: 999px; padding: 0.28rem 0.55rem; margin-left: 0.45rem;
  cursor: pointer; -webkit-tap-highlight-color: transparent;
  transition: color 0.15s, border-color 0.15s;
}
.downloaded-pill:hover, .downloaded-pill.has-downloads { color: var(--accent); border-color: var(--accent); }
.downloaded-pill.is-offline { color: #ffcc00; border-color: #ffcc00; }
.folder-filter-bar {
  padding: 0 16px 4px; display: flex; align-items: center; gap: 8px;
}
.offline-folder-card { cursor: pointer; }
.offline-folder-icon {
  display: flex; align-items: center; justify-content: center;
  background: var(--surface2); border-radius: 6px; width: 100%; aspect-ratio: 1;
}
.offline-folder-icon svg { width: 36px; height: 36px; fill: var(--accent); }
.fav-badge {
  position: absolute; top: 0.5rem; right: 0.5rem;
  color: var(--accent); font-size: 1rem; line-height: 1;
  pointer-events: none; z-index: 2;
}
.fav-folder { border: 1px solid var(--accent); border-radius: 8px; }
/* Audiobook folder styling */
.audiobook-folder .folder-icon { color: #a0c4ff; }
.audiobook-folder .folder-name { color: #a0c4ff; }
/* Recently played section */
.recent-section { padding: 0.5rem 0.75rem 0; }
.recent-section-title {
  font-size: 0.68rem; text-transform: uppercase; letter-spacing: .08em;
  color: var(--sub); margin-bottom: 0.4rem; padding-left: 0.1rem;
}
.recent-scroll {
  display: flex; gap: 0.65rem; overflow-x: auto; padding-bottom: 0.4rem;
  scrollbar-width: thin; scrollbar-color: #444 transparent;
  -webkit-overflow-scrolling: touch;
}
.recent-scroll::-webkit-scrollbar { height: 3px; }
.recent-scroll::-webkit-scrollbar-thumb { background: #444; border-radius: 2px; }
.recent-card {
  flex-shrink: 0; width: 100px; cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.recent-thumb-wrap {
  position: relative; width: 100px; height: 100px;
  border-radius: 6px; overflow: hidden; background: #2a2a2a;
}
.recent-thumb { width: 100%; height: 100%; object-fit: cover; display: block; }
.recent-progress-bar {
  position: absolute; bottom: 0; left: 0; height: 3px; background: var(--accent);
  border-radius: 0 2px 2px 0;
}
.recent-title {
  font-size: 0.72rem; margin-top: 0.25rem; line-height: 1.2;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.recent-sub {
  font-size: 0.62rem; color: var(--sub); margin-top: 0.1rem;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.recent-card:hover .recent-title { color: var(--accent); }
body.modal-open { overflow: hidden; }
.offline-library {
  position: fixed; inset: 0; z-index: 40; background: rgba(0,0,0,0.62);
  display: flex; align-items: flex-end; justify-content: center; padding: 1rem;
}
.offline-library[hidden] { display: none; }
.offline-panel {
  width: min(760px, 100%); max-height: min(82vh, 900px);
  display: flex; flex-direction: column; overflow: hidden;
  background: var(--surface); border: 1px solid #333; border-radius: 16px;
  box-shadow: 0 20px 48px rgba(0,0,0,0.45);
}
.offline-head {
  display: flex; align-items: flex-start; gap: 0.75rem;
  padding: 1rem 1rem 0.75rem; border-bottom: 1px solid #262626;
}
.offline-title-wrap { flex: 1 1 0; min-width: 0; }
.offline-title { font-size: 1rem; font-weight: 700; }
.offline-subtitle, .offline-summary-detail {
  font-size: 0.78rem; color: var(--sub); margin-top: 0.2rem;
}
.offline-summary {
  padding: 0.75rem 1rem 0.25rem; font-size: 0.85rem; color: var(--text);
}
.offline-summary.warn { color: #ffcc00; }
.offline-toolbar {
  display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;
  padding: 0.5rem 1rem 0.9rem;
}
.offline-toolbar select {
  background: var(--surface2); color: var(--text); border: 1px solid #444;
  border-radius: 999px; padding: 0.4rem 0.8rem; font-size: 0.8rem;
}
.offline-download-list {
  list-style: none; margin: 0; padding: 0; overflow: auto; border-top: 1px solid #202020;
}
.offline-download-item {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.8rem 1rem; border-bottom: 1px solid #202020; cursor: pointer;
}
.offline-download-item:hover { background: var(--surface2); }
.offline-download-thumb {
  width: 48px; height: 48px; border-radius: 6px; object-fit: cover; background: var(--surface2);
  flex-shrink: 0;
}
.offline-download-meta { flex: 1 1 0; min-width: 0; }
.offline-download-title {
  font-size: 0.9rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.offline-download-sub, .offline-download-size {
  font-size: 0.77rem; color: var(--sub); margin-top: 0.12rem;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.offline-download-delete {
  background: none; border: 1px solid #555; color: var(--sub); border-radius: 999px;
  padding: 0.35rem 0.65rem; cursor: pointer; flex-shrink: 0;
}
.offline-download-delete:hover { color: #ff6b6b; border-color: #ff6b6b; }
.empty-downloads {
  text-align: center; color: var(--sub); padding: 2rem 1rem; font-size: 0.85rem;
}

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
/* Filter-Chips (Schnellfilter in der Track-Liste) */
.filter-chip {
  background: var(--surface2); color: var(--sub);
  border: 1px solid #444; border-radius: 20px;
  padding: 0.35rem 0.65rem; font-size: 0.78rem; font-weight: 500;
  cursor: pointer; white-space: nowrap; flex-shrink: 0;
  display: inline-flex; align-items: center; gap: 0.25rem;
  transition: color 0.12s, border-color 0.12s;
  -webkit-tap-highlight-color: transparent; line-height: 1;
}
.filter-chip:hover { border-color: var(--accent); color: var(--text); }
.filter-chip.active { border-color: var(--accent); color: var(--accent); }
.filter-chip svg { width: 11px; height: 11px; fill: currentColor; flex-shrink: 0; }

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
  min-width: 26px; text-align: center; font-size: 0.78rem;
  color: var(--sub); flex-shrink: 0; white-space: nowrap; padding-right: 4px;
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
/* missing episode placeholder */
.track-item.missing-episode {
  opacity: 0.35; pointer-events: none; min-height: 32px;
  border-bottom: 1px solid #1a1a1a;
}
.track-item.missing-episode .track-title { font-style: italic; }
/* conversion badge for non-native formats */
.convert-badge {
  display: inline-block; font-size: 0.65rem; color: #f5a623;
  margin-left: 5px; vertical-align: middle; opacity: 0.8;
  title: attr(data-tip);
}
.track-dl-btn {
  background: none; border: 1px solid #555; color: var(--sub);
  border-radius: 50%; width: 30px; height: 30px;
  cursor: pointer; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
  -webkit-tap-highlight-color: transparent;
  padding: 0; line-height: 1; font-size: 0.7rem;
}
.track-dl-btn svg { width: 16px; height: 16px; fill: currentColor; pointer-events: none; }
.track-dl-btn:hover { color: var(--accent); border-color: var(--accent); }
.track-dl-btn.cached {
  color: var(--accent); border-color: var(--accent);
  background: rgba(29, 185, 84, 0.12);
}
.track-dl-btn.downloading {
  color: #ffcc00; border-color: #ffcc00; font-size: 0.65rem;
  cursor: pointer;
}
@keyframes dl-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
.track-dl-btn.downloading { animation: dl-pulse 1.2s ease-in-out infinite; }
.track-pin-btn {
  background: none; border: 1px solid #555; color: var(--sub);
  border-radius: 50%; width: 28px; height: 28px;
  cursor: pointer; flex-shrink: 0; margin-left: 4px;
  display: flex; align-items: center; justify-content: center;
  transition: color 0.15s, border-color 0.15s;
  -webkit-tap-highlight-color: transparent;
  padding: 0; line-height: 1;
}
.track-pin-btn svg { width: 14px; height: 14px; fill: currentColor; pointer-events: none; }
.track-pin-btn:hover { color: var(--accent); border-color: var(--accent); }
.track-pin-btn.pinned {
  color: var(--accent); border-color: var(--accent);
  background: rgba(29, 185, 84, 0.12);
}
.track-edit-btn {
  background: none; border: 1px solid #555; color: var(--sub);
  border-radius: 50%; width: 28px; height: 28px;
  cursor: pointer; flex-shrink: 0; margin-left: 4px;
  display: flex; align-items: center; justify-content: center;
  transition: color 0.15s, border-color 0.15s;
  -webkit-tap-highlight-color: transparent;
  padding: 0; line-height: 1;
}
.track-edit-btn svg { width: 14px; height: 14px; fill: currentColor; pointer-events: none; }
.track-edit-btn:hover { color: var(--accent); border-color: var(--accent); }
/* ── Edit metadata modal ── */
.edit-modal-backdrop {
  position: fixed; inset: 0; z-index: 60; background: rgba(0,0,0,0.72);
  display: flex; align-items: center; justify-content: center; padding: 1rem;
}
.edit-modal-backdrop[hidden] { display: none; }
.edit-modal {
  width: min(480px, 100%); background: var(--surface);
  border: 1px solid #444; border-radius: 14px;
  padding: 1.25rem 1.25rem 1rem;
  box-shadow: 0 20px 48px rgba(0,0,0,0.55);
}
.edit-modal-heading { font-size: 1rem; font-weight: 700; margin-bottom: 1rem; }
.edit-field { margin-bottom: 0.75rem; }
.edit-field label { display: block; font-size: 0.78rem; color: var(--sub); margin-bottom: 0.25rem; }
.edit-field input {
  width: 100%; box-sizing: border-box;
  background: var(--surface2); border: 1px solid #444; border-radius: 6px;
  color: var(--text); font-size: 0.9rem; padding: 0.45rem 0.6rem;
  outline: none; transition: border-color 0.15s;
}
.edit-field input:focus { border-color: var(--accent); }
.edit-modal-actions { display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1rem; }
.edit-modal-cancel {
  background: none; border: 1px solid #555; color: var(--sub);
  border-radius: 6px; padding: 0.4rem 0.9rem;
  cursor: pointer; font-size: 0.85rem; transition: border-color 0.12s, color 0.12s;
}
.edit-modal-cancel:hover { border-color: var(--text); color: var(--text); }
.edit-modal-save {
  background: var(--accent); color: #000; border: none; border-radius: 6px;
  padding: 0.4rem 0.9rem; cursor: pointer; font-size: 0.85rem; font-weight: 600;
  transition: background 0.12s;
}
.edit-modal-save:hover { background: #1ed760; }
.edit-modal-save:disabled { opacity: 0.6; cursor: not-allowed; }
/* ── Playlist add button (per track) ── */
.track-playlist-btn {
  background: none; border: 1px solid #555; color: var(--sub);
  border-radius: 50%; width: 28px; height: 28px;
  cursor: pointer; flex-shrink: 0; margin-left: 4px;
  display: flex; align-items: center; justify-content: center;
  transition: color 0.15s, border-color 0.15s;
  -webkit-tap-highlight-color: transparent;
  padding: 0; line-height: 1;
}
.track-playlist-btn svg { width: 14px; height: 14px; fill: none; stroke: currentColor; pointer-events: none; }
.track-playlist-btn:hover { color: var(--accent); border-color: var(--accent); }
/* ── Playlist drag-and-drop reorder ── */
.track-item.dragging { opacity: 0.25; pointer-events: none; }
.track-item.drag-over-above { box-shadow: 0 3px 0 0 var(--accent) inset; }
.track-item.drag-over-below { box-shadow: 0 -3px 0 0 var(--accent) inset; }
.playlist-drag-ghost {
  position: fixed; z-index: 200; pointer-events: none;
  background: var(--surface2); border: 1px solid var(--accent);
  border-radius: 8px; padding: 0.5rem 1rem; opacity: 0.92;
  font-size: 0.88rem; color: var(--fg); white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; max-width: 280px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5);
  display: flex; align-items: center; gap: 0.5rem;
}
.playlist-drag-ghost img { width: 32px; height: 32px; border-radius: 4px; object-fit: cover; }
body.playlist-dragging { user-select: none; -webkit-user-select: none; }
body.playlist-dragging .track-list { overflow: visible; }
/* ── Playlist modal (add-to / create) ── */
.playlist-modal-backdrop {
  position: fixed; inset: 0; z-index: 60; background: rgba(0,0,0,0.72);
  display: flex; align-items: center; justify-content: center; padding: 1rem;
}
.playlist-modal-backdrop[hidden] { display: none; }
.playlist-modal {
  width: min(420px, 100%); background: var(--surface);
  border: 1px solid #444; border-radius: 14px;
  padding: 1.25rem 1.25rem 1rem;
  box-shadow: 0 20px 48px rgba(0,0,0,0.55);
  max-height: 70vh; display: flex; flex-direction: column;
}
.playlist-modal-heading { font-size: 1rem; font-weight: 700; margin-bottom: 0.75rem; }
.playlist-modal-list {
  list-style: none; margin: 0; padding: 0; overflow: auto;
  flex: 1 1 auto; min-height: 0;
}
.playlist-modal-item {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.55rem 0.5rem; border-radius: 8px; cursor: pointer;
  transition: background 0.12s;
}
.playlist-modal-item:hover { background: var(--surface2); }
.playlist-modal-item-name { flex: 1; font-size: 0.9rem; }
.playlist-modal-item-count { font-size: 0.75rem; color: var(--sub); }
.playlist-modal-new {
  display: flex; gap: 0.4rem; margin-top: 0.75rem; padding-top: 0.75rem;
  border-top: 1px solid #333;
}
.playlist-modal-new input {
  flex: 1; background: var(--surface2); border: 1px solid #444; border-radius: 6px;
  color: var(--text); font-size: 0.85rem; padding: 0.4rem 0.6rem; outline: none;
}
.playlist-modal-new input:focus { border-color: var(--accent); }
.playlist-modal-new button {
  background: var(--accent); color: #000; border: none; border-radius: 6px;
  padding: 0.4rem 0.75rem; cursor: pointer; font-size: 0.85rem; font-weight: 600;
}
.playlist-modal-close {
  display: flex; justify-content: flex-end; margin-top: 0.75rem;
}
.playlist-modal-close button {
  background: none; border: 1px solid #555; color: var(--sub);
  border-radius: 6px; padding: 0.35rem 0.75rem; cursor: pointer; font-size: 0.8rem;
}
.playlist-modal-close button:hover { border-color: var(--text); color: var(--text); }
/* ── Playlist library panel (removed — playlists as pseudo-folders) ── */
/* ── Playlist pseudo-folder cards ── */
.playlist-folder-card { position: relative; }
.playlist-folder-icon {
  width: 100%; aspect-ratio: 1; display: flex; align-items: center; justify-content: center;
  background: var(--surface2); border-radius: 8px; color: var(--sub);
}
.playlist-folder-icon svg { width: 36px; height: 36px; }
.playlist-new-card { opacity: 0.65; border: 2px dashed #444; }
.playlist-new-card:hover { opacity: 1; border-color: var(--accent); }
.playlist-folder-del {
  position: absolute; top: 6px; right: 6px; z-index: 2;
  background: rgba(0,0,0,0.55); border: 1px solid #555; color: var(--sub);
  border-radius: 50%; width: 24px; height: 24px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  opacity: 0.6; transition: opacity 0.15s, color 0.12s, border-color 0.12s;
}
.playlist-folder-card:hover .playlist-folder-del { opacity: 1; }
.playlist-folder-del:hover { color: #ff5555; border-color: #ff5555; opacity: 1; }
.track-thumb {
  width: 40px; height: 40px; border-radius: 4px; object-fit: cover;
  flex-shrink: 0; background: var(--surface2);
}
/* ── Rating bar overlay on thumbnails ── */
.thumb-wrap {
  position: relative; flex-shrink: 0; overflow: hidden;
}
.thumb-wrap.track-thumb-wrap {
  width: 40px; height: 40px; border-radius: 4px;
}
.thumb-wrap.track-thumb-wrap .track-thumb {
  width: 100%; height: 100%; border-radius: 0;
}
.thumb-wrap.folder-thumb-wrap {
  width: 100%; border-radius: 6px; margin-bottom: 0.4rem;
}
.thumb-wrap.folder-thumb-wrap .folder-thumb {
  margin-bottom: 0; border-radius: 0;
}
.rating-bar {
  position: absolute; bottom: 0; left: 0; height: 3px;
  background: linear-gradient(90deg, #ff8800, #ffcc00);
  opacity: 0.85; pointer-events: none;
  border-radius: 0 1px 0 0;
}
.folder-grid.list-mode .thumb-wrap.folder-thumb-wrap {
  width: 40px; height: 40px; border-radius: 4px;
  margin-bottom: 0; flex-shrink: 0;
}
.folder-grid.list-mode .thumb-wrap.folder-thumb-wrap .folder-thumb {
  width: 100%; height: 100%; aspect-ratio: auto; border-radius: 0;
}
.folder-thumb {
  width: 100%; aspect-ratio: 1; border-radius: 6px; object-fit: cover;
  margin-bottom: 0.4rem; background: var(--surface2);
}
.folder-grid.list-mode .folder-thumb {
  width: 40px; height: 40px; aspect-ratio: auto; border-radius: 4px;
  margin-bottom: 0; flex-shrink: 0;
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
  cursor: pointer; line-height: 1;
  padding: 0.35rem; border-radius: 50%; transition: color 0.12s;
  -webkit-tap-highlight-color: transparent;
  display: flex; align-items: center; justify-content: center;
}
.ctrl-btn svg { width: 18px; height: 18px; fill: currentColor; pointer-events: none; }
.ctrl-btn:hover { color: var(--accent); }
.ctrl-btn.play-pause {
  background: var(--accent); color: #000;
  width: 38px; height: 38px; display: flex; align-items: center; justify-content: center;
}
.ctrl-btn.play-pause svg { width: 16px; height: 16px; }
.ctrl-btn.play-pause:hover { background: #1ed760; }
.ctrl-btn.pip-btn { position: relative; }
.ctrl-btn.pip-btn svg { width: 16px; height: 16px; }
.ctrl-btn.pip-btn.active { color: var(--accent); }
.ctrl-btn.pip-btn[hidden] { display: none; }
/* Shuffle button active states */
.ctrl-btn.shuffle-btn.shuffle-active { color: var(--accent); }
.ctrl-btn.shuffle-btn.shuffle-weighted { color: var(--accent); background: rgba(29, 185, 84, 0.15); border-radius: 50%; }
/* Rating stars in player */
.player-rating { display: flex; gap: 1px; margin-top: 2px; }
.player-rating[hidden] { display: none; }
.player-rating-star { background: none; border: none; padding: 1px; cursor: pointer; color: #555; width: 15px; height: 15px; flex-shrink: 0; transition: color 0.1s; -webkit-tap-highlight-color: transparent; display: flex; align-items: center; justify-content: center; }
.player-rating-star svg { width: 12px; height: 12px; }
.player-rating-star.active { color: #ffd700; }
.player-rating-star.hover { color: #ffd700; }
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
.player-bar.classic .progress-track {
  flex: 1 1 0; position: relative; min-width: 0; height: auto;
}
.player-bar.classic input[type=range] {
  -webkit-appearance: none; appearance: none;
  width: 100%; height: 4px; background: #555;
  border-radius: 2px; outline: none; cursor: pointer;
  position: static; opacity: 1;
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
.player-bar.waveform .progress-track {
  flex: 1 1 0; position: relative; height: 48px; min-width: 0; cursor: pointer;
}
.player-bar.waveform .progress-track.video-mode { height: 28px; }
.waveform-canvas {
  display: block; width: 100%; height: 100%; border-radius: 4px;
}
.player-bar.waveform .progress-track input[type=range] {
  -webkit-appearance: none; appearance: none;
  position: absolute; top: 0; left: 0;
  width: 100%; height: 100%; opacity: 0;
  cursor: pointer; margin: 0; z-index: 2;
  background: transparent;
}
.player-bar.waveform .progress-track input[type=range]::-webkit-slider-thumb {
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
  display: block; max-width: 200px; border-radius: 3px;
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
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: opacity 0.15s;
}
.folder-play-btn svg { width: 16px; height: 16px; fill: currentColor; pointer-events: none; }
/* Touch devices: always show play button at low opacity */
@media (hover: none) {
  .folder-play-btn { opacity: 0.55; }
}
/* Mouse/trackpad: reveal on hover */
@media (hover: hover) {
  .folder-card:hover .folder-play-btn { opacity: 1; }
}
.folder-play-btn:hover { background: #1ed760; }
.back-btn {
  background: var(--surface2); border: 1px solid #444; color: var(--accent);
  cursor: pointer; padding: 0.3rem 0.5rem;
  border-radius: 6px; display: none;
  transition: background 0.12s, color 0.12s;
  line-height: 0;
}
.back-btn svg { width: 18px; height: 18px; fill: currentColor; }
.back-btn:hover { background: #333; color: #1ed760; }
.play-all-btn {
  background: var(--accent); color: #000; border: none;
  border-radius: 20px; padding: 0.3rem 0.8rem; cursor: pointer;
  font-size: 0.8rem; font-weight: 600; display: none;
  transition: background 0.12s; white-space: nowrap;
  align-items: center; gap: 4px;
}
.play-all-btn svg { width: 14px; height: 14px; fill: currentColor; display: inline-block; vertical-align: middle; }
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
  border-radius: 4px; padding: 0.25rem 0.4rem; cursor: pointer;
  transition: color 0.12s, border-color 0.12s;
  flex-shrink: 0; line-height: 0;
}
.view-toggle svg { width: 16px; height: 16px; fill: currentColor; }
.view-toggle:hover { color: var(--accent); border-color: var(--accent); }
.audit-btn {
  background: none; border: 1px solid #333; color: var(--sub);
  border-radius: 4px; padding: 0.25rem 0.4rem; cursor: pointer;
  transition: color 0.12s, border-color 0.12s;
  flex-shrink: 0; line-height: 0; text-decoration: none; display: inline-flex; align-items: center;
}
.audit-btn svg { width: 16px; height: 16px; }
.audit-btn:hover { color: var(--accent); border-color: var(--accent); }

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
@media (hover: none) {
  .folder-grid.list-mode .folder-play-btn { opacity: 0.55; }
}
@media (hover: hover) {
  .folder-grid.list-mode .folder-card:hover .folder-play-btn { opacity: 1; }
}

@media (max-width: 480px) {
  .player-info { flex: 0 0 90px; }
  .folder-grid { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); }
}
/* toast notification */
.ht-toast {
  position: fixed; bottom: 5rem; left: 50%; transform: translateX(-50%);
  background: #e53935; color: #fff; padding: 0.6rem 1.2rem;
  border-radius: 8px; font-size: 0.85rem; z-index: 9999;
  box-shadow: 0 4px 12px rgba(0,0,0,0.5); opacity: 0;
  transition: opacity 0.3s; pointer-events: none;
  max-width: 90vw; text-align: center; word-break: break-word;
}
.ht-toast.visible { opacity: 1; }
/* indexing toast (top-right info notification) */
.ht-indexing-toast {
  position: fixed; top: 0.75rem; right: 0.75rem;
  background: rgba(50,50,50,0.92); color: #ccc; padding: 0.45rem 0.9rem;
  border-radius: 6px; font-size: 0.78rem; z-index: 9998;
  box-shadow: 0 2px 8px rgba(0,0,0,0.35); opacity: 0;
  transition: opacity 0.3s; pointer-events: none;
  max-width: 320px; text-align: left; word-break: break-word;
  backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px);
  border: 1px solid rgba(255,255,255,0.06);
}
.ht-indexing-toast.visible { opacity: 1; }
.ht-indexing-toast .spinner {
  display: inline-block; width: 10px; height: 10px;
  border: 2px solid #666; border-top-color: #ccc;
  border-radius: 50%; animation: ht-spin 0.8s linear infinite;
  margin-right: 6px; vertical-align: middle;
}
@keyframes ht-spin { to { transform: rotate(360deg); } }

/* ── Lyrics panel ── */
.lyrics-panel {
  position: fixed; left: 0; right: 0; bottom: 0;
  background: var(--surface); border-top: 1px solid #333;
  z-index: 500; display: flex; flex-direction: column;
  max-height: 55vh; transform: translateY(100%);
  transition: transform 0.28s cubic-bezier(.4,0,.2,1);
}
.lyrics-panel.visible { transform: translateY(0); }
.lyrics-panel-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.6rem 1rem 0.4rem; border-bottom: 1px solid #2a2a2a; flex-shrink: 0;
}
.lyrics-panel-title { font-size: 0.82rem; font-weight: 600; color: var(--sub); text-transform: uppercase; letter-spacing: .06em; }
.lyrics-close-btn {
  background: none; border: none; color: var(--sub); cursor: pointer;
  font-size: 1.2rem; line-height: 1; padding: 0.2rem 0.4rem;
  border-radius: 4px; transition: color 0.12s;
}
.lyrics-close-btn:hover { color: var(--accent); }
.lyrics-body {
  overflow-y: auto; padding: 0.75rem 1rem 1.5rem;
  flex: 1 1 0; -webkit-overflow-scrolling: touch;
}
.lyrics-text {
  white-space: pre-wrap; font-size: 0.9rem; line-height: 1.75;
  color: var(--text); font-family: inherit;
}
.lyrics-empty { color: var(--sub); font-size: 0.85rem; font-style: italic; }
.lyrics-loading { color: var(--sub); font-size: 0.85rem; }
.ctrl-btn.lyrics-btn.has-lyrics { color: var(--accent); }
"""


# ---------------------------------------------------------------------------
# Shared player JavaScript
# ---------------------------------------------------------------------------


def render_player_js(
    api_path: str,
    item_noun: str = "track",
    file_emoji: str = "\U0001f3b5",
    player_bar_style: str = "classic",
    enable_offline: bool = True,
    enable_shuffle: bool = False,
    enable_rating_write: bool = False,
    enable_metadata_edit: bool = False,
    enable_recent: bool = True,
    enable_lyrics: bool = False,
    enable_playlists: bool = False,
    playlist_sync_interval_ms: int = 30000,
) -> str:
    """Return the media player JavaScript with hierarchical folder navigation.

    Default view is a folder list (configurable via toggle to grid).
    Clicking a folder navigates deeper into the hierarchy.  Leaf folders
    (no sub-folders) are displayed as playlists.  A breadcrumb trail and
    back button allow navigating up.  View preference is stored in
    localStorage.

    *enable_shuffle* activates the shuffle button in the player bar.
    Long-pressing the shuffle button activates weighted shuffle (items with
    higher ratings are more likely to play).  Works with offline downloads too.
    """
    # -- waveform/thumbnail JS (only for waveform mode) -----------------------
    if player_bar_style == "waveform":
        waveform_js = """
  /* ── waveform & thumbnail elements ── */
  var progressTrack  = document.getElementById('progress-track');
  var waveformCanvas = document.getElementById('waveform-canvas');
  var waveformCtx    = waveformCanvas ? waveformCanvas.getContext('2d') : null;
  var isAudioMode    = player.tagName === 'AUDIO';
  var isVideoMode    = player.tagName === 'VIDEO';
  var waveformData   = null;
  var waveformAbort  = null;
"""
    else:
        waveform_js = """
  var progressTrack  = document.getElementById('progress-track');
  var isAudioMode    = player.tagName === 'AUDIO';
  var isVideoMode    = player.tagName === 'VIDEO';
"""

    # -- sprite sheet preview (always available for video, both modes) ----------
    sprite_preview_js = """
  /* ── sprite sheet preview (video scrubber thumbnails) ── */
  var thumbPreview   = document.getElementById('thumb-preview');
  var thumbCanvas    = document.getElementById('thumb-canvas');
  var thumbCtx       = thumbCanvas ? thumbCanvas.getContext('2d') : null;
  var thumbTimeEl    = document.getElementById('thumb-time');
  var spriteData     = null;
  var spriteImg      = null;

  function loadSpriteData(relativePath) {
    spriteData = null;
    spriteImg = null;
    if (!isVideoMode || !relativePath) return;
    fetch('/api/video/sprites?path=' + encodeURIComponent(relativePath))
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(meta) {
        if (!meta || !meta.cols) return;
        spriteData = meta;
        var img = new Image();
        img.onload = function() { spriteImg = img; };
        img.src = '/thumb?path=' + encodeURIComponent(relativePath) + '&size=sprite';
      })
      .catch(function() {});
  }

  if (isVideoMode && progressTrack) {
    progressTrack.addEventListener('mousemove', function(e) {
      if (!spriteData || !spriteImg || !player.duration || !isFinite(player.duration)) return;
      var rect = progressTrack.getBoundingClientRect();
      var ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      var seekTime = ratio * player.duration;
      var pctLeft = Math.max(5, Math.min(95, ratio * 100));
      thumbPreview.style.left = pctLeft + '%';
      thumbPreview.classList.add('visible');
      thumbTimeEl.textContent = fmtTime(seekTime);
      var idx = Math.min(Math.floor(seekTime / spriteData.interval), spriteData.count - 1);
      var col = idx % spriteData.cols;
      var row = Math.floor(idx / spriteData.cols);
      if (thumbCtx) {
        thumbCanvas.width = spriteData.frame_w;
        thumbCanvas.height = spriteData.frame_h;
        thumbCtx.drawImage(spriteImg,
          col * spriteData.frame_w, row * spriteData.frame_h,
          spriteData.frame_w, spriteData.frame_h,
          0, 0, spriteData.frame_w, spriteData.frame_h);
      }
    });
    progressTrack.addEventListener('mouseleave', function() {
      thumbPreview.classList.remove('visible');
    });
  }
"""

    if player_bar_style == "waveform":
        waveform_setup_js = """
  /* ── waveform (audio) & video mode setup ── */
  if (isVideoMode && progressTrack) {
    progressTrack.classList.add('video-mode');
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

    return (
        """
(function () {
  var INITIAL = JSON.parse(document.getElementById('initial-data').textContent);
  var ITEM_NOUN = '"""
        + item_noun
        + """';
  var FILE_EMOJI = '"""
        + file_emoji
        + """';
  var API_PATH = '"""
        + api_path
        + """';
  var OFFLINE_ENABLED = """
        + ("true" if enable_offline else "false")
        + """;

  /* Placeholder SVG thumbnails — same dimensions as real thumbs so layout never shifts.
     Simple dark-grey squares with a subtle icon silhouette. */
  var FOLDER_PLACEHOLDER = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 120'%3E%3Crect width='120' height='120' rx='6' fill='%232a2a2a'/%3E%3Cpath d='M30 45h25l7-10h28l0 0H90v40H30z' fill='%23444'/%3E%3C/svg%3E";
  var FILE_PLACEHOLDER  = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 120'%3E%3Crect width='120' height='120' rx='6' fill='%232a2a2a'/%3E%3Ccircle cx='54' cy='72' r='12' fill='none' stroke='%23444' stroke-width='3'/%3E%3Crect x='63' y='38' width='3' height='34' fill='%23444'/%3E%3Crect x='57' y='38' width='12' height='4' rx='1' fill='%23444'/%3E%3C/svg%3E";

  /* SVG icons for play/pause — cross-platform, no emoji rendering */
  var IC_PLAY  = '<svg viewBox="0 0 24 24"><polygon points="6,3 20,12 6,21"/></svg>';
  var IC_PAUSE = '<svg viewBox="0 0 24 24"><rect x="5" y="3" width="4" height="18"/><rect x="15" y="3" width="4" height="18"/></svg>';
  var IC_DL    = '<svg viewBox="0 0 24 24"><path d="M12 3v12m0 0l-4-4m4 4l4-4M5 19h14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var IC_CHECK = '<svg viewBox="0 0 24 24"><polyline points="4,12 10,18 20,6" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var IC_FOLDER_PLAY = '<svg viewBox="0 0 24 24"><polygon points="6,3 20,12 6,21"/></svg>';
  var IC_PIN = '<svg viewBox="0 0 24 24"><path d="M16 4l4 4-2.5 2.5 1.5 5.5-6-6-5 5v-2l3.5-3.5L6 4h2l5 1.5z" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var IC_STAR = '<svg viewBox="0 0 24 24"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="currentColor"/></svg>';
  var IC_SHUFFLE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16,3 21,3 21,8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21,16 21,21 16,21"/><line x1="4" y1="4" x2="9" y2="9"/></svg>';
  var IC_STAR_FILLED = '<svg viewBox="0 0 24 24"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="currentColor"/></svg>';
  var IC_STAR_EMPTY  = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"/></svg>';
  var SHUFFLE_ENABLED = """
        + ("true" if enable_shuffle else "false")
        + """;
  var RATING_WRITE_ENABLED = """
        + ("true" if enable_rating_write else "false")
        + """;
  var RATING_API_PATH = '"""
        + api_path.rsplit("/", 1)[0]
        + """/rating';
  var AUDIT_UNDO_PATH = '"""
        + api_path.rsplit("/", 1)[0].replace("/api/", "/api/")
        + """/audit/undo';
  var RECENT_ENABLED = """
        + ("true" if enable_recent else "false")
        + """;
  var RECENT_API_PATH = '"""
        + api_path.rsplit("/", 1)[0]
        + """/recent';
  var METADATA_EDIT_ENABLED = """
        + ("true" if enable_metadata_edit else "false")
        + """;
  var METADATA_EDIT_PATH = '"""
        + api_path.rsplit("/", 1)[0]
        + """/metadata/edit';
  var IC_EDIT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>';
  var IC_LYRICS = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14,2 14,8 20,8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>';
  var LYRICS_ENABLED = """
        + ("true" if enable_lyrics else "false")
        + """;
  var LYRICS_API_PATH = '"""
        + api_path.rsplit("/", 1)[0]
        + """/lyrics';
  var PLAYLISTS_ENABLED = """
        + ("true" if enable_playlists else "false")
        + """;
  var PLAYLISTS_API_PATH = '"""
        + api_path.rsplit("/", 1)[0]
        + """/playlists';
  var PLAYLISTS_VERSION_PATH = '"""
        + api_path.rsplit("/", 1)[0]
        + """/playlists/version';
  var FOLDER_ORDER_API_PATH = '"""
        + api_path.rsplit("/", 1)[0]
        + """/folder-order';
  var IC_PLAYLIST = '"""
        + SVG_PLAYLIST.replace("'", "\\'")
        + """';
  var AUDIOBOOK_DIRS = """
        + __import__("json").dumps(__import__("hometools.config", fromlist=["get_audiobook_dirs"]).get_audiobook_dirs())
        + """;

  var allItems = Array.isArray(INITIAL) ? INITIAL : [];
  var currentPath = '';
  var playlistItems = [];
  var filteredItems = [];
  var currentIndex = -1;
  var inPlaylist = false;
  var initialCatalogRetryTimer = null;
  var initialCatalogRetryCount = 0;
  /* ── Shuffle state ── */
  var shuffleMode = false;       /* false = off, 'normal' = random, 'weighted' = rating-weighted */
  var shuffleQueue = [];         /* pre-built queue of indices for current session */
  var shufflePos = -1;           /* current position within shuffleQueue */

  var player       = document.getElementById('player');
  var btnPlay      = document.getElementById('btn-play');
  var btnPrev      = document.getElementById('btn-prev');
  var btnNext      = document.getElementById('btn-next');
  var btnShuffle   = document.getElementById('btn-shuffle');
  var trackList    = document.getElementById('track-list');
  var trackCount   = document.getElementById('track-count');
  var playerTitle  = document.getElementById('player-title');
  var playerArtist = document.getElementById('player-artist');
  var playerThumb  = document.getElementById('player-thumb');
  var progressBar  = document.getElementById('progress-bar');
  var timeCur      = document.getElementById('time-cur');
  var timeDur      = document.getElementById('time-dur');
  var searchInput  = document.getElementById('search-input');
  var sortField    = document.getElementById('sort-field');
  var filterRatingBtn = document.getElementById('filter-rating');
  var filterFavBtn    = document.getElementById('filter-fav');
  var filterGenreBtn  = document.getElementById('filter-genre');
  /* Persisted quick-filter state */
  var filterRating = parseInt(localStorage.getItem('ht-filter-rating') || '0', 10) || 0;
  var filterFav    = localStorage.getItem('ht-filter-fav') === '1';
  var filterGenre  = localStorage.getItem('ht-filter-genre') || '';
  var folderGrid   = document.getElementById('folder-grid');
  var trackView    = document.getElementById('track-view');
  var filterBar    = document.querySelector('.filter-bar');
  var backBtn      = document.getElementById('back-btn');
  var logoHomeBtn  = document.getElementById('header-logo');
  var headerTitle  = document.getElementById('header-title');
  var playerBar    = document.querySelector('.player-bar');
  var playAllBtn   = document.getElementById('play-all-btn');
  var offlineLibrary = document.getElementById('offline-library');
  var offlineClose = document.getElementById('offline-close');
  var offlineSort  = document.getElementById('offline-sort');
  var offlinePersistBtn = document.getElementById('offline-persist-btn');
  var offlinePruneBtn = document.getElementById('offline-prune-btn');
  var offlineDownloadList = document.getElementById('offline-download-list');
  var offlineStorageSummary = document.getElementById('offline-storage-summary');
  var offlineStorageDetail = document.getElementById('offline-storage-detail');
  var downloadedPill = document.getElementById('downloaded-pill');
  var originalTitle = headerTitle.textContent;
  var breadcrumb  = document.getElementById('breadcrumb');
  var viewToggle  = document.getElementById('view-toggle');
  var _savedViewMode = localStorage.getItem('ht-view-mode');
  var viewMode    = (_savedViewMode === 'list' || _savedViewMode === 'grid' || _savedViewMode === 'filenames') ? _savedViewMode : 'list';
  var currentStreamUrl = '';
  var currentOfflineUrl = null;
"""
        + waveform_js
        + """

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
  function formatBytes(b) {
    if (b < 1024) return b + ' B';
    if (b < 1048576) return (b / 1024).toFixed(1) + ' KB';
    if (b < 1073741824) return (b / 1048576).toFixed(1) + ' MB';
    return (b / 1073741824).toFixed(2) + ' GB';
  }
  var _toastEl = null;
  var _toastTimer = 0;
  function showToast(msg, durationMs) {
    if (!_toastEl) {
      _toastEl = document.createElement('div');
      _toastEl.className = 'ht-toast';
      document.body.appendChild(_toastEl);
    }
    _toastEl.textContent = msg;
    _toastEl.classList.add('visible');
    clearTimeout(_toastTimer);
    _toastTimer = setTimeout(function() { _toastEl.classList.remove('visible'); }, durationMs || 4000);
  }

  /* ── click-distance guard: suppress clicks when the mouse moved ── */
  var _mdX = 0, _mdY = 0;
  var CLICK_MOVE_THRESHOLD = 6; /* pixels */
  document.addEventListener('mousedown', function(e) { _mdX = e.clientX; _mdY = e.clientY; }, true);
  document.addEventListener('touchstart', function(e) {
    if (e.touches.length === 1) { _mdX = e.touches[0].clientX; _mdY = e.touches[0].clientY; }
  }, { passive: true, capture: true });
  function wasDrag(e) {
    var dx = Math.abs(e.clientX - _mdX);
    var dy = Math.abs(e.clientY - _mdY);
    return dx > CLICK_MOVE_THRESHOLD || dy > CLICK_MOVE_THRESHOLD;
  }

  /* ── playback progress persistence ── */
  var _progressTimer = 0;
  var _progressRelPath = '';
  function _progressApiBase() {
    return API_PATH.substring(0, API_PATH.lastIndexOf('/')) + '/progress';
  }
  function saveProgressNow() {
    var rp = _progressRelPath;
    if (!rp) return;
    var pos = player.currentTime;
    var dur = player.duration;
    if (!isFinite(pos) || !isFinite(dur)) return;
    if (pos < 5 || pos > dur - 5) return;
    fetch(_progressApiBase(), {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({relative_path: rp, position_seconds: pos, duration: dur})
    }).catch(function() {});
  }
  function saveProgressDebounced() {
    clearTimeout(_progressTimer);
    _progressTimer = setTimeout(saveProgressNow, 5000);
  }
  function clearProgressFor(rp) {
    if (!rp) return;
    fetch(_progressApiBase(), {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({relative_path: rp, position_seconds: 0, duration: 0})
    }).catch(function() {});
  }
  function loadAndSeekProgress(rp) {
    if (!rp) return;
    fetch(_progressApiBase() + '?path=' + encodeURIComponent(rp))
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(data) {
        if (!data || !data.items || !data.items.length) return;
        var entry = data.items[0];
        var pos = entry.position_seconds || 0;
        if (pos < 5) return;
        function doSeek() {
          if (isFinite(player.duration) && pos < player.duration - 5) {
            player.currentTime = pos;
            showToast('Fortfahren bei ' + fmtTime(pos), 3000);
          }
        }
        if (isFinite(player.duration) && player.duration > 0) {
          doSeek();
        } else {
          player.addEventListener('loadedmetadata', doSeek, { once: true });
        }
      })
      .catch(function() {});
  }

  var _indexToastEl = null;
  var _indexRefreshTimer = null;
  function showIndexingToast(msg) {
    if (!_indexToastEl) {
      _indexToastEl = document.createElement('div');
      _indexToastEl.className = 'ht-indexing-toast';
      document.body.appendChild(_indexToastEl);
    }
    _indexToastEl.innerHTML = '<span class="spinner"></span>' + escHtml(msg || 'Indexing…');
    _indexToastEl.classList.add('visible');
  }
  function hideIndexingToast() {
    if (_indexToastEl) _indexToastEl.classList.remove('visible');
    if (_indexRefreshTimer) { clearTimeout(_indexRefreshTimer); _indexRefreshTimer = null; }
  }

  /* ── Lyrics panel ── */
  var _lyricsBtn   = document.getElementById('btn-lyrics');
  var _lyricsPanel = document.getElementById('lyrics-panel');
  var _lyricsBody  = document.getElementById('lyrics-body');
  var _lyricsClose = document.getElementById('lyrics-close-btn');
  var _lyricsCache = {};   /* relative_path → lyrics text or '' */
  var _lyricsOpen  = false;

  function openLyricsPanel(relativePath, trackTitle) {
    if (!LYRICS_ENABLED || !_lyricsPanel) return;
    _lyricsOpen = true;
    _lyricsPanel.classList.add('visible');
    if (_lyricsBtn) _lyricsBtn.title = 'Songtext schlie\u00dfen';

    /* Serve from cache if available */
    if (relativePath in _lyricsCache) {
      _renderLyrics(_lyricsCache[relativePath], trackTitle);
      return;
    }
    if (_lyricsBody) _lyricsBody.innerHTML = '<div class="lyrics-loading">Lade Songtext\u2026</div>';
    fetch(LYRICS_API_PATH + '?path=' + encodeURIComponent(relativePath), { cache: 'no-store' })
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(d) {
        var text = (d && d.lyrics) ? d.lyrics : '';
        _lyricsCache[relativePath] = text;
        if (_lyricsOpen) _renderLyrics(text, trackTitle);
      })
      .catch(function() {
        if (_lyricsBody) _lyricsBody.innerHTML = '<div class="lyrics-empty">Songtext konnte nicht geladen werden.</div>';
      });
  }

  function _renderLyrics(text, trackTitle) {
    if (!_lyricsBody) return;
    if (text) {
      _lyricsBody.innerHTML = '<div class="lyrics-text">' + escHtml(text) + '</div>';
      if (_lyricsBtn) _lyricsBtn.classList.add('has-lyrics');
    } else {
      _lyricsBody.innerHTML = '<div class="lyrics-empty">Kein Songtext f\u00fcr \u201e' + escHtml(trackTitle || 'diesen Titel') + '\u201c hinterlegt.</div>';
      if (_lyricsBtn) _lyricsBtn.classList.remove('has-lyrics');
    }
  }

  function closeLyricsPanel() {
    _lyricsOpen = false;
    if (_lyricsPanel) _lyricsPanel.classList.remove('visible');
    if (_lyricsBtn) _lyricsBtn.title = 'Songtext anzeigen';
  }

  if (_lyricsBtn) {
    _lyricsBtn.addEventListener('click', function() {
      if (_lyricsOpen) {
        closeLyricsPanel();
      } else {
        /* Find the currently playing track */
        var t = filteredItems[currentIndex] || playlistItems[currentIndex];
        if (t) openLyricsPanel(t.relative_path, t.title);
      }
    });
  }
  if (_lyricsClose) {
    _lyricsClose.addEventListener('click', closeLyricsPanel);
  }

  function scheduleBackgroundRefresh(delay) {
    if (_indexRefreshTimer) return;
    _indexRefreshTimer = setTimeout(function() {
      _indexRefreshTimer = null;
      fetch(API_PATH, { cache: 'no-store' })
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(data) {
          if (!data || data.error) return;
          if (data.refreshing) {
            var detail = data.detail || 'Building index…';
            showIndexingToast(detail);
            scheduleBackgroundRefresh();
            /* Update items if more are now available */
            var newItems = data && Array.isArray(data.items) ? data.items : [];
            if (newItems.length > allItems.length) {
              allItems = newItems;
              showFolderView();
            }
            return;
          }
          /* Full index ready */
          hideIndexingToast();
          allItems = data && Array.isArray(data.items) ? data.items : [];
          console.info('Background refresh complete:', allItems.length, 'items');
          showFolderView();
        })
        .catch(function() { scheduleBackgroundRefresh(); });
    }, delay !== undefined ? delay : 800);
  }

  /* Cancel the pending poll timer and re-fetch immediately.
     Only acts when an index build is actually in progress. */
  function forceBackgroundRefresh() {
    if (!_indexRefreshTimer) return; /* nothing scheduled → no build in progress */
    clearTimeout(_indexRefreshTimer);
    _indexRefreshTimer = null;
    scheduleBackgroundRefresh(0);
  }

"""
        + waveform_setup_js
        + sprite_preview_js
        + """

  /* items under a path prefix (recursive) */
  function itemsUnder(path) {
    if (!path) return allItems;
    var prefix = path + '/';
    return allItems.filter(function(it) { return it.relative_path.startsWith(prefix); });
  }

  /* compute direct sub-folders and loose files at a path level */
  var IGNORED_FOLDERS = {'#recycle': true, '@eaDir': true};

  function contentsAt(path) {
    var items = itemsUnder(path);
    var folderMap = {};
    var folderThumb = {};
    var folderThumbLg = {};
    var files = [];
    var off = path ? path.length + 1 : 0;
    items.forEach(function(it) {
      var rest = it.relative_path.substring(off);
      var slash = rest.indexOf('/');
      if (slash >= 0) {
        var name = rest.substring(0, slash);
        if (IGNORED_FOLDERS[name]) return;
        if (!folderMap[name]) folderMap[name] = 0;
        folderMap[name]++;
        if (!folderThumb[name] && it.thumbnail_url) folderThumb[name] = it.thumbnail_url;
        if (!folderThumbLg[name] && it.thumbnail_lg_url) folderThumbLg[name] = it.thumbnail_lg_url;
      } else {
        files.push(it);
      }
    });
    var folders = Object.keys(folderMap)
      .sort(function(a, b) {
        /* Favorites (#-prefixed) first, then alphabetical */
        var aFav = a.charAt(0) === '#';
        var bFav = b.charAt(0) === '#';
        if (aFav !== bFav) return aFav ? -1 : 1;
        return a.localeCompare(b);
      })
      .map(function(n) {
        var isFav = n.charAt(0) === '#';
        return {
          name: n,
          displayName: isFav ? n.substring(1) : n,
          isFavorite: isFav,
          count: folderMap[n],
          thumbnail_url: folderThumb[n] || '',
          thumbnail_lg_url: folderThumbLg[n] || ''
        };
      });
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

  function showLoadingState(message) {
    folderGrid.classList.remove('view-hidden');
    trackView.classList.add('view-hidden');
    filterBar.classList.add('view-hidden');
    playAllBtn.style.display = 'none';
    backBtn.style.display = currentPath ? 'inline-block' : 'none';
    headerTitle.textContent = currentPath ? leafName(currentPath) : originalTitle;
    trackCount.textContent = 'Loading…';
    if (!player.currentSrc) playerBar.classList.add('view-hidden');
    folderGrid.innerHTML = '<div class="empty-hint">' + escHtml(message || 'Loading library…') + '</div>';
    renderBreadcrumb();
    applyViewMode();
  }

  function showCatalogLoadError(detail) {
    folderGrid.classList.remove('view-hidden');
    trackView.classList.add('view-hidden');
    filterBar.classList.add('view-hidden');
    playAllBtn.style.display = 'none';
    if (!player.currentSrc) playerBar.classList.add('view-hidden');
    trackCount.textContent = 'Library unavailable';
    headerTitle.textContent = currentPath ? leafName(currentPath) : originalTitle;
    backBtn.style.display = currentPath ? 'inline-block' : 'none';
    folderGrid.innerHTML = '<div class="empty-hint">' + escHtml(detail || 'Library could not be loaded.') + '</div>';
    renderBreadcrumb();
    applyViewMode();
  }

  function scheduleInitialCatalogRetry(reason) {
    if (initialCatalogRetryTimer) return;
    console.info('Initial catalog retry scheduled:', reason || 'loading');
    initialCatalogRetryTimer = window.setTimeout(function() {
      initialCatalogRetryTimer = null;
      loadInitialCatalog();
    }, 800);
  }

  function loadInitialCatalog() {
    if (allItems.length) {
      console.info('Initial catalog already present in page payload:', allItems.length, 'items');
      return Promise.resolve(allItems);
    }
    initialCatalogRetryCount += 1;
    if (initialCatalogRetryCount <= 1) {
      showLoadingState('Loading library…');
    }
    var t0 = Date.now();
    console.info('Initial catalog fetch started:', API_PATH);
    return fetch(API_PATH, { cache: 'no-store' })
      .then(function(r) {
        console.info('Initial catalog response received after', Date.now() - t0, 'ms with status', r.status);
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function(data) {
        if (data && data.error) {
          throw new Error(data.error);
        }
        /* Handle loading state (truly empty, no quick scan available) */
        if (data && data.loading && (!data.items || data.items.length === 0)) {
          var detail = data.detail || 'Library cache is warming in the background.';
          console.info('Initial catalog still building (empty):', detail);
          showIndexingToast(detail);
          scheduleInitialCatalogRetry(detail);
          return [];
        }
        if (initialCatalogRetryTimer) {
          window.clearTimeout(initialCatalogRetryTimer);
          initialCatalogRetryTimer = null;
        }
        initialCatalogRetryCount = 0;
        allItems = data && Array.isArray(data.items) ? data.items : [];
        console.info('Initial catalog parsed after', Date.now() - t0, 'ms:', allItems.length, 'items');
        showFolderView();
        /* If still building, show indexing toast and poll for updates */
        if (data && data.refreshing) {
          var refreshDetail = data.detail || 'Building index in background…';
          console.info('Catalog served from quick scan, index still building:', refreshDetail);
          showIndexingToast(refreshDetail);
          scheduleBackgroundRefresh();
        } else {
          hideIndexingToast();
        }
        return allItems;
      })
      .catch(function(err) {
        console.error('Initial catalog load failed:', err);
        showCatalogLoadError(err && err.message ? err.message : 'Library could not be loaded.');
        return [];
      });
  }

  /* ── breadcrumb ── */
  function renderBreadcrumb() {
    if (!currentPath) { breadcrumb.classList.remove('visible'); return; }
    breadcrumb.classList.add('visible');
    /* Special offline playlist breadcrumb */
    if (currentPath === '__offline__') {
      breadcrumb.innerHTML = '<a data-path="">\\u{1F3E0} Home</a>' +
        '<span class="sep">\\u203A</span>' +
        '<span class="current">Downloaded</span>';
      breadcrumb.querySelectorAll('a').forEach(function(a) {
        a.addEventListener('click', function() {
          currentPath = a.dataset.path;
          showFolderView();
        });
      });
      return;
    }
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
  var IC_GRID = '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>';
  var IC_LIST = '<svg viewBox="0 0 24 24"><line x1="3" y1="6" x2="21" y2="6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="3" y1="12" x2="21" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="3" y1="18" x2="21" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
  var IC_FILENAMES = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="14" y2="6"/><line x1="3" y1="12" x2="18" y2="12"/><line x1="3" y1="18" x2="11" y2="18"/><polyline points="17,15 20,18 17,21" stroke-linejoin="round"/></svg>';
  function applyViewMode() {
    if (viewMode === 'list') {
      folderGrid.classList.add('list-mode');
      folderGrid.classList.remove('filenames-mode');
      viewToggle.innerHTML = IC_GRID;
      viewToggle.title = 'Listenansicht \u2014 Klick f\u00fcr Kachelansicht';
    } else if (viewMode === 'grid') {
      folderGrid.classList.remove('list-mode');
      folderGrid.classList.remove('filenames-mode');
      viewToggle.innerHTML = IC_FILENAMES;
      viewToggle.title = 'Kachelansicht \u2014 Klick f\u00fcr Dateinamen';
    } else {
      /* 'filenames' */
      folderGrid.classList.add('list-mode');
      folderGrid.classList.add('filenames-mode');
      viewToggle.innerHTML = IC_LIST;
      viewToggle.title = 'Dateinamen \u2014 Klick f\u00fcr Listenansicht';
    }
  }

  /* ── folder view ── */

  function showFolderView() {
    destroyPlaylistDragDrop();
    inPlaylist = false;
    _currentPlaylistId = '';
    var c = contentsAt(currentPath);
    var isRoot = !currentPath;
    var showOrigNames = (viewMode === 'filenames');

    /* empty library */
    if (c.folders.length === 0 && c.files.length === 0) {
      folderGrid.classList.remove('view-hidden');
      trackView.classList.add('view-hidden');
      filterBar.classList.add('view-hidden');
      playAllBtn.style.display = 'none';
      headerTitle.textContent = currentPath ? leafName(currentPath) : originalTitle;
      backBtn.style.display = currentPath ? 'inline-block' : 'none';
      if (!player.currentSrc) playerBar.classList.add('view-hidden');
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
    if (!player.currentSrc) playerBar.classList.add('view-hidden');

    headerTitle.textContent = currentPath ? leafName(currentPath) : originalTitle;
    backBtn.style.display = currentPath ? 'inline-block' : 'none';
    playAllBtn.style.display = '';

    var label = c.folders.length + ' folder' + (c.folders.length !== 1 ? 's' : '');
    if (c.files.length > 0) {
      label += ', ' + c.files.length + ' ' + (c.files.length !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN);
    }
    trackCount.textContent = label;

    var html = '';

    /* Offline Downloads folder card — only on root */
    if (isRoot && OFFLINE_ENABLED) {
      html += '<div class="folder-card offline-folder-card" id="offline-folder-card">' +
        '<div class="folder-thumb offline-folder-icon">' + IC_DL + '</div>' +
        '<div class="folder-name">Downloaded</div>' +
        '<div class="folder-count" id="offline-folder-count">0 downloads</div>' +
      '</div>';
    }

    /* Auto-Favorites playlist card — only on root when favorites exist */
    if (isRoot && PLAYLISTS_ENABLED) {
      var _favCount = allItems.filter(function(t) { return !!_savedFavorites[t.relative_path]; }).length;
      if (_favCount > 0) {
        html += '<div class="folder-card playlist-folder-card" data-playlist-id="__favorites__">' +
          '<div class="folder-thumb playlist-folder-icon">' + IC_STAR + '</div>' +
          '<div class="folder-name">Favoriten</div>' +
          '<div class="folder-count">' + _favCount + ' Titel</div>' +
          '<button class="folder-play-btn playlist-folder-play" title="Abspielen">' + IC_FOLDER_PLAY + '</button>' +
        '</div>';
      }
    }

    /* Playlist pseudo-folder cards — only on root, only when playlists enabled */
    var _playlistCardsRendered = false;
    if (isRoot && PLAYLISTS_ENABLED) {
      _playlistCardsRendered = true;
      _userPlaylists.forEach(function(pl) {
        var cnt = (pl.items || []).length;
        html += '<div class="folder-card playlist-folder-card" data-playlist-id="' + escHtml(pl.id) + '">' +
          '<div class="folder-thumb playlist-folder-icon">' + IC_PLAYLIST + '</div>' +
          '<div class="folder-name">' + escHtml(pl.name) + '</div>' +
          '<div class="folder-count">' + cnt + ' Titel</div>' +
          '<button class="folder-play-btn playlist-folder-play" title="Abspielen">' + IC_FOLDER_PLAY + '</button>' +
          '<button class="playlist-folder-del" title="L\u00f6schen">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
          '</button>' +
        '</div>';
      });
      /* "+ Neue Playlist" card */
      html += '<div class="folder-card playlist-new-card" id="playlist-new-card">' +
        '<div class="folder-thumb playlist-folder-icon">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>' +
        '</div>' +
        '<div class="folder-name">Neue Playlist\u2026</div>' +
        '<div class="folder-count"></div>' +
      '</div>';
    }

    c.folders.forEach(function(f) {
      var noun = f.count !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN;
      var thumbSrc = viewMode !== 'list'
        ? (f.thumbnail_lg_url || f.thumbnail_url || FOLDER_PLACEHOLDER)
        : (f.thumbnail_url || FOLDER_PLACEHOLDER);
      var displayLabel = showOrigNames ? f.name : f.displayName;
      var favBadge = f.isFavorite && !showOrigNames ? '<span class="fav-badge" title="Favorit">' + IC_STAR + '</span>' : '';
      var isAudiobook = AUDIOBOOK_DIRS.some(function(d) { return f.name.toLowerCase().startsWith(d.toLowerCase()); });
      var extraClass = (f.isFavorite ? ' fav-folder' : '') + (isAudiobook ? ' audiobook-folder' : '');
      html += '<div class="folder-card' + extraClass + '" data-folder="' + escHtml(f.name) + '">' +
        favBadge +
        '<img class="folder-thumb" src="' + escHtml(thumbSrc) + '" alt="" loading="lazy">' +
        '<div class="folder-name">' + escHtml(displayLabel) + '</div>' +
        '<div class="folder-count">' + f.count + ' ' + noun + '</div>' +
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
        var playBtn = card.querySelector('.playlist-folder-play');
        var delBtn = card.querySelector('.playlist-folder-del');
        card.addEventListener('click', function(e) {
          if (wasDrag(e)) return;
          if (e.target.closest('.playlist-folder-play') || e.target.closest('.playlist-folder-del')) return;
          showUserPlaylistView(card.dataset.playlistId);
        });
        if (playBtn) playBtn.addEventListener('click', function(e) {
          e.stopPropagation();
          if (wasDrag(e)) return;
          playUserPlaylist(card.dataset.playlistId);
        });
        if (delBtn) delBtn.addEventListener('click', function(e) {
          e.stopPropagation();
          if (wasDrag(e)) return;
          deleteUserPlaylist(card.dataset.playlistId);
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
        }).then(function(r) { return r.json(); })
          .then(function(d) {
            if (d.playlist) {
              _userPlaylists.unshift(d.playlist);
              showFolderView();
              showToast('Playlist "' + d.playlist.name + '" erstellt');
            }
          }).catch(function() { showToast('Fehler beim Erstellen'); });
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
      card.addEventListener('click', function(e) {
        if (wasDrag(e)) return;
        if (e.target !== pb) navigateInto(card.dataset.folder);
      });
      pb.addEventListener('click', function(e) {
        e.stopPropagation();
        if (wasDrag(e)) return;
        playAllIn(card.dataset.folder);
      });
    });

    var looseFiles = c.files;
    folderGrid.querySelectorAll('.file-card').forEach(function(card) {
      card.addEventListener('click', function(e) {
        if (wasDrag(e)) return;
        forceBackgroundRefresh(); /* get freshest data while index builds */
        showPlaylist(looseFiles, true, Number(card.dataset.fileIdx));
      });
    });

    renderBreadcrumb();
    applyViewMode();
  }

  function navigateInto(name) {
    currentPath = currentPath ? currentPath + '/' + name : name;
    forceBackgroundRefresh(); /* get freshest data while index builds */
    showFolderView();
  }

  function playAllIn(name) {
    var full = currentPath ? currentPath + '/' + name : name;
    var items = itemsUnder(full);
    if (items.length) { currentPath = full; showPlaylist(items, true); }
  }

  /* ── playlist view ── */
  function showPlaylist(items, autoplay, startIdx) {
    destroyPlaylistDragDrop();
    inPlaylist = true;
    _currentPlaylistId = '__folder__';
    playlistItems = _sortByFolderOrder(currentPath, items);

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
    /* Rebuild shuffle queue for the new playlist */
    if (shuffleMode) rebuildShuffleQueue(startIdx || 0);
    if (autoplay && playlistItems.length) {
      /* When shuffle is on, start from shuffleQueue[0] instead of startIdx */
      var firstIdx = shuffleMode && shuffleQueue.length ? shuffleQueue[0] : (startIdx || 0);
      playTrack(firstIdx);
    }
    /* Pre-warm: fetch server-side order and re-sort if different */
    var _showPlaylistPath = currentPath;
    _loadFolderOrderAsync(currentPath, function(serverOrder) {
      if (!serverOrder.length) return;
      if (_currentPlaylistId !== '__folder__') return;
      var localOrder = _loadFolderOrder(_showPlaylistPath);
      if (JSON.stringify(localOrder) === JSON.stringify(serverOrder)) return;
      playlistItems = _sortByFolderOrder(_showPlaylistPath, items);
      applyFilter();
    });
  }

  /* ── back ── */
  function goBack() {
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

  /* play all items under current path */
  function playAllCurrent() {
    var items = itemsUnder(currentPath);
    if (!items.length) items = contentsAt(currentPath).files;
    if (items.length) showPlaylist(items, true);
  }

  /* ── filter / sort within playlist ── */
  /* ── Quick-filter chips ── */
  function updateFilterChips() {
    if (filterRatingBtn) {
      if (filterRating > 0) {
        filterRatingBtn.innerHTML = IC_STAR_FILLED + ' ' + filterRating + '+';
        filterRatingBtn.classList.add('active');
        filterRatingBtn.title = filterRating + '+ Sterne — klicken zum Weiterschalten';
      } else {
        filterRatingBtn.innerHTML = IC_STAR_EMPTY + ' Bewertung';
        filterRatingBtn.classList.remove('active');
        filterRatingBtn.title = 'Nach Bewertung filtern';
      }
    }
    if (filterFavBtn) {
      filterFavBtn.innerHTML = IC_PIN + ' Favoriten';
      filterFavBtn.classList.toggle('active', filterFav);
      filterFavBtn.title = filterFav
        ? 'Favoriten-Filter aktiv — klicken zum Aufheben'
        : 'Nur Favoriten anzeigen';
    }
    if (filterGenreBtn) {
      /* Collect genres from current playlist items */
      var genres = {};
      (playlistItems || []).forEach(function(t) {
        if (t.genre) genres[t.genre] = true;
      });
      var genreList = Object.keys(genres).sort();
      if (genreList.length === 0) {
        filterGenreBtn.style.display = 'none';
      } else {
        filterGenreBtn.style.display = '';
        if (filterGenre) {
          filterGenreBtn.textContent = filterGenre;
          filterGenreBtn.classList.add('active');
          filterGenreBtn.title = 'Genre: ' + filterGenre + ' — klicken zum Weiterschalten';
        } else {
          filterGenreBtn.textContent = 'Genre';
          filterGenreBtn.classList.remove('active');
          filterGenreBtn.title = 'Nach Genre filtern';
        }
      }
    }
  }

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
    /* Quick-filters */
    if (filterRating > 0) {
      items = items.filter(function(t) { return (t.rating || 0) >= filterRating; });
    }
    if (filterFav) {
      items = items.filter(function(t) { return !!_savedFavorites[t.relative_path]; });
    }
    if (filterGenre) {
      items = items.filter(function(t) { return t.genre === filterGenre; });
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

  /* ── track list rendering ── */
  var NATIVE_EXT = ['.mp4','.m4v','.webm','.ogg','.ogv','.mp3','.m4a','.aac','.opus','.flac','.wav'];
  function needsConversion(rp) {
    if (!rp) return false;
    var dot = rp.lastIndexOf('.');
    if (dot < 0) return false;
    return NATIVE_EXT.indexOf(rp.substring(dot).toLowerCase()) < 0;
  }
  function filenameFromPath(rp) {
    if (!rp) return '';
    var slash = rp.lastIndexOf('/');
    var name = slash >= 0 ? rp.substring(slash + 1) : rp;
    var dot = name.lastIndexOf('.');
    return dot > 0 ? name.substring(0, dot) : name;
  }

  function markActive() {
    document.querySelectorAll('.track-item:not(.missing-episode)').forEach(function(el) {
      var idx = Number(el.dataset.index);
      el.classList.toggle('active', idx === currentIndex);
      if (idx === currentIndex) el.scrollIntoView({ block: 'nearest' });
    });
  }

  /* insert placeholder rows for missing episodes within the same season */
  function withMissingEpisodes(tracks) {
    /* only insert gaps if all tracks are series episodes */
    var allSeries = tracks.length > 0 && tracks.every(function(t) { return (t.season || 0) > 0; });
    if (!allSeries) return tracks;

    var result = [];
    for (var i = 0; i < tracks.length; i++) {
      var t = tracks[i];
      /* insert gap placeholders within the same season */
      if (i > 0) {
        var prev = tracks[i - 1];
        if ((prev.season || 0) === (t.season || 0)) {
          var gap = (t.episode || 0) - (prev.episode || 0);
          for (var g = 1; g < gap && g < 20; g++) {
            result.push({ _missing: true, season: prev.season, episode: (prev.episode || 0) + g });
          }
        }
      }
      result.push(t);
    }
    return result;
  }

  function renderTracks(tracks) {
    filteredItems = tracks;
    /* Rebuild shuffle queue whenever the filtered set changes */
    if (shuffleMode) rebuildShuffleQueue(currentIndex >= 0 ? currentIndex : 0);
    var noun = tracks.length !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN;
    trackCount.textContent = tracks.length + ' ' + noun;
    if (!tracks.length) {
      trackList.innerHTML = '<li class="empty-hint">No matching items.</li>';
      return;
    }
    var showOrig = (viewMode === 'filenames');
    var displayTracks = withMissingEpisodes(tracks);
    var realIdx = 0;
    trackList.innerHTML = displayTracks.map(function(t) {
      /* missing episode placeholder */
      if (t._missing) {
        var seLabel = 'S' + String(t.season).padStart(2, '0') + 'E' + String(t.episode).padStart(2, '0');
        return '<li class="track-item missing-episode">' +
          '<span class="track-num"><span class="num-text">' + seLabel + '</span></span>' +
          '<div class="track-info"><div class="track-title">—</div></div></li>';
      }
      var idx = realIdx++;
      var isSeries = (t.season || 0) > 0;
      var numLabel = isSeries
        ? 'S' + String(t.season).padStart(2, '0') + 'E' + String(t.episode).padStart(2, '0')
        : String(idx + 1);
      var displayTitle = showOrig ? filenameFromPath(t.relative_path) : t.title;
      var subtitle = t.artist || t.relative_path;
      var thumbSrc = t.thumbnail_url || FILE_PLACEHOLDER;
      var extraCls = idx === currentIndex ? ' active' : '';
      var ratingBar = t.rating > 0 ? '<div class="rating-bar" style="width:' + (t.rating / 5 * 100) + '%"></div>' : '';
      var convertBadge = needsConversion(t.relative_path) ? '<span class="convert-badge" title="Wird on-the-fly konvertiert">\\u26A1</span>' : '';
      return '<li class="track-item' + extraCls +
        '" data-index="' + idx + '">' +
        '<span class="track-num"><span class="num-text">' + numLabel + '</span></span>' +
        '<div class="thumb-wrap track-thumb-wrap">' +
        '<img class="track-thumb" src="' + escHtml(thumbSrc) + '" alt="" loading="lazy">' +
        ratingBar + '</div>' +
        '<div class="track-info">' +
          '<div class="track-title">' + escHtml(displayTitle) + convertBadge + '</div>' +
          '<div class="track-artist">' + escHtml(subtitle) + '</div>' +
        '</div>' +
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
        '</li>';
    }).join('');
    document.querySelectorAll('.track-item:not(.missing-episode)').forEach(function(el) {
      el.addEventListener('click', function(e) { if (!wasDrag(e)) playTrack(Number(el.dataset.index)); });
    });
    document.querySelectorAll('.track-dl-btn').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        e.preventDefault();
        var url = btn.dataset.streamUrl;
        var title = btn.dataset.title;
        var meta = {
          artist: btn.dataset.artist || '',
          relativePath: btn.dataset.relativePath || '',
          thumbnailUrl: btn.dataset.thumbnailUrl || '',
          mediaType: btn.dataset.mediaType || ITEM_NOUN
        };
        if (btn.classList.contains('cached')) {
          deleteTrackDownload(url, btn);
        } else if (btn.classList.contains('downloading')) {
          cancelDownload(url, btn);
        } else {
          downloadTrack(url, title, btn, meta);
        }
      });
    });
    document.querySelectorAll('.track-pin-btn').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        e.preventDefault();
        var item = filteredItems.find(function(it) { return it.relative_path === btn.dataset.relativePath; });
        if (item) toggleFavorite(item, btn);
      });
    });
    if (METADATA_EDIT_ENABLED) {
      document.querySelectorAll('.track-edit-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
          e.stopPropagation();
          e.preventDefault();
          openEditModal(Number(btn.dataset.index));
        });
      });
    }
    if (PLAYLISTS_ENABLED) {
      document.querySelectorAll('.track-playlist-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
          e.stopPropagation();
          e.preventDefault();
          loadUserPlaylists().then(function() { openPlaylistModal(btn.dataset.relativePath); });
        });
      });
      if (inPlaylist && _currentPlaylistId && (viewMode === 'filenames' || viewMode === 'list')) initPlaylistDragDrop();
    }
    updateFavoriteButtons();
    updateAllDownloadButtons();
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

  function formatBytes(bytes) {
    var value = Number(bytes || 0);
    if (value <= 0) return '0 MB';
    var units = ['B', 'KB', 'MB', 'GB'];
    var idx = 0;
    while (value >= 1024 && idx < units.length - 1) {
      value /= 1024;
      idx++;
    }
    return value.toFixed(idx === 0 ? 0 : 1) + ' ' + units[idx];
  }

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
        var n = ready.length;
        el.textContent = n + ' download' + (n !== 1 ? 's' : '');
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
            var idx = 0;
            for (var j = 0; j < folderItems.length; j++) {
              if (folderItems[j].relative_path === path) { idx = j; break; }
            }
            showPlaylist(folderItems, false);
            playItem(found, idx);
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

  /* ── playback ── */
  /* Background playback for video — three layers of defence:
     ─────────────────────────────────────────────────────────
     PROBLEM: Mobile browsers (especially iOS Safari) pause <video>
     elements **before** the visibilitychange event fires.  So checking
     `!player.paused` inside that handler is already too late — the
     video is paused.  And `requestPictureInPicture()` requires a
     user-gesture, so calling it from visibilitychange is rejected.

     STRATEGY:
     1. **`wasPlaying` flag** — set on `playing` event, cleared only by
        intentional user-pause.  The browser's auto-pause does NOT
        clear it.  visibilitychange checks `wasPlaying` instead of
        `!player.paused`.
     2. **Hidden <audio> with `muted:true`** — plays the same source
        silently alongside the video.  Because it is already actively
        playing (started from user-gesture), iOS keeps it alive when
        backgrounded.  On visibilitychange we unmute it so audio
        continues seamlessly.
        NOTE: iOS ignores `volume` (always 1), so we MUST use `muted`
        to prevent double-audio in the foreground.
     3. **`autopictureinpicture` attribute** — Safari/WebKit honours
        this and enters PiP automatically when the page backgrounds.
        No user-gesture needed.  The manual PiP button works on all
        browsers that support the API. */
  var bgAudio = null;
  var bgSyncTimer = null;
  var isVideoPlayer = player.tagName === 'VIDEO';
  var isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
              (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var pipActive = false;
  var wasPlaying = false;
  var btnPip = document.getElementById('btn-pip');

  /* Track intentional playback state — survives browser auto-pause */
  player.addEventListener('playing', function() { wasPlaying = true; });

  /* Show PiP button only when the browser supports it for this player */
  var pipSupported = isVideoPlayer && (
    document.pictureInPictureEnabled ||
    (typeof player.webkitSupportsPresentationMode === 'function' &&
     player.webkitSupportsPresentationMode('picture-in-picture'))
  );
  if (pipSupported && btnPip) btnPip.hidden = false;

  /* Enable Safari's automatic PiP on page background */
  if (isVideoPlayer) {
    player.setAttribute('autopictureinpicture', '');
  }

  function requestPiP() {
    if (!pipSupported || pipActive) return Promise.resolve();
    if (player.requestPictureInPicture) {
      return player.requestPictureInPicture().then(function() {
        pipActive = true;
        if (btnPip) btnPip.classList.add('active');
      }).catch(function() {});
    } else if (player.webkitSetPresentationMode) {
      player.webkitSetPresentationMode('picture-in-picture');
      pipActive = true;
      if (btnPip) btnPip.classList.add('active');
      return Promise.resolve();
    }
    return Promise.resolve();
  }

  function exitPiP() {
    if (!pipActive) return;
    if (document.exitPictureInPicture && document.pictureInPictureElement) {
      document.exitPictureInPicture().catch(function() {});
    } else if (player.webkitSetPresentationMode) {
      player.webkitSetPresentationMode('inline');
    }
    pipActive = false;
    if (btnPip) btnPip.classList.remove('active');
  }

  /* Track PiP state changes from native controls */
  if (isVideoPlayer) {
    player.addEventListener('enterpictureinpicture', function() {
      pipActive = true;
      if (btnPip) btnPip.classList.add('active');
    });
    player.addEventListener('leavepictureinpicture', function() {
      pipActive = false;
      if (btnPip) btnPip.classList.remove('active');
      /* If user closed PiP but wasPlaying, resume inline */
      if (wasPlaying && !document.hidden) {
        player.play().catch(function() {});
      }
    });
  }

  /* Manual PiP toggle button */
  if (btnPip) {
    btnPip.addEventListener('click', function() {
      if (pipActive) { exitPiP(); } else { requestPiP(); }
    });
  }

  /* Fullscreen button — uses native fullscreen or iOS webkitEnterFullscreen */
  var btnFs = document.getElementById('btn-fs');
  var fsSupported = isVideoPlayer && (
    document.fullscreenEnabled || document.webkitFullscreenEnabled ||
    typeof player.webkitEnterFullscreen === 'function'
  );
  if (fsSupported && btnFs) btnFs.hidden = false;
  if (btnFs) {
    btnFs.addEventListener('click', function() {
      if (player.requestFullscreen) {
        player.requestFullscreen().catch(function() {});
      } else if (player.webkitRequestFullscreen) {
        player.webkitRequestFullscreen();
      }
    });
  }

  function ensureBgAudio() {
    if (bgAudio) return bgAudio;
    bgAudio = document.createElement('audio');
    bgAudio.style.display = 'none';
    bgAudio.preload = 'auto';
    bgAudio.playsInline = true;
    bgAudio.muted = true;
    document.body.appendChild(bgAudio);
    /* When bg audio track ends, advance to next */
    bgAudio.addEventListener('ended', function() {
      playTrack(currentIndex < filteredItems.length - 1 ? currentIndex + 1 : 0);
    });
    return bgAudio;
  }

  /* Is bg audio currently the active (unmuted) source? */
  function bgAudioIsActive() {
    return bgAudio && !bgAudio.muted && !bgAudio.paused;
  }

  /* Start the hidden <audio> muted, mirroring the video source.
     The play() call happens inside user-initiated playback so the
     browser allows it.  Because the element is already in a playing
     state, unmuting it later in visibilitychange works instantly. */
  function startBgMirror() {
    if (!isVideoPlayer) return;
    var bg = ensureBgAudio();
    if (bg.src !== player.src) {
      bg.src = player.src;
    }
    bg.currentTime = player.currentTime;
    bg.muted = true;
    bg.play().catch(function() {});
    /* keep bg audio roughly in sync while video plays */
    stopBgSync();
    bgSyncTimer = setInterval(function() {
      if (!bgAudio || !bgAudio.muted) return;
      if (!player.paused && Math.abs(bgAudio.currentTime - player.currentTime) > 0.5) {
        bgAudio.currentTime = player.currentTime;
      }
    }, 2000);
  }

  function stopBgSync() {
    if (bgSyncTimer) { clearInterval(bgSyncTimer); bgSyncTimer = null; }
  }

  /* ── Visibility change — the core background handler ──
     Uses `wasPlaying` instead of `!player.paused` because the browser
     has already paused the video by the time this fires on mobile. */
  document.addEventListener('visibilitychange', function() {
    if (!isVideoPlayer) return;
    if (document.hidden && wasPlaying) {
      /* App going to background — explicitly pause the video to prevent
         double audio on desktop (desktop browsers do NOT auto-pause video).
         On mobile, the browser already paused it so this is a no-op. */
      player.pause();
      if (bgAudio && !bgAudio.paused) {
        bgAudio.currentTime = player.currentTime;
        bgAudio.muted = false;
      }
      /* Signal to OS that playback is ongoing */
      if ('mediaSession' in navigator) {
        navigator.mediaSession.playbackState = 'playing';
      }
    } else if (!document.hidden && wasPlaying) {
      /* App coming back to foreground */
      if (pipActive) exitPiP();
      if (bgAudio && !bgAudio.muted) {
        /* Sync video to where bg audio continued, resume video */
        player.currentTime = bgAudio.currentTime;
        player.play().catch(function() {});
        bgAudio.muted = true;
      } else if (player.paused) {
        /* No bg audio ran — just resume the video */
        player.play().catch(function() {});
      }
    }
  });

  /* Return whichever element is currently driving playback */
  function activeMedia() {
    if (bgAudioIsActive()) return bgAudio;
    return player;
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
    navigator.mediaSession.setActionHandler('play', function() {
      var m = activeMedia();
      m.play();
      wasPlaying = true;
    });
    navigator.mediaSession.setActionHandler('pause', function() {
      /* Lockscreen pause = intentional user pause */
      wasPlaying = false;
      var m = activeMedia();
      m.pause();
      if (bgAudio) { bgAudio.pause(); bgAudio.muted = true; }
    });
    navigator.mediaSession.setActionHandler('previoustrack', function() {
      playTrack(currentIndex > 0 ? currentIndex - 1 : filteredItems.length - 1);
    });
    navigator.mediaSession.setActionHandler('nexttrack', function() {
      playTrack(currentIndex < filteredItems.length - 1 ? currentIndex + 1 : 0);
    });
    try {
      navigator.mediaSession.setActionHandler('seekto', function(details) {
        var m = activeMedia();
        m.currentTime = details.seekTime;
      });
    } catch(e) {}
  }

  function playItem(t, index) {
    currentIndex = typeof index === 'number' ? index : -1;
    currentStreamUrl = t.stream_url || '';

    /* Sync shuffle queue position to the chosen index */
    if (shuffleMode && shuffleQueue.length && currentIndex >= 0) {
      var qpos = shuffleQueue.indexOf(currentIndex);
      if (qpos >= 0) shufflePos = qpos;
      else { shuffleQueue.unshift(currentIndex); shufflePos = 0; }
    }

    /* Reset bg audio for new track */
    stopBgSync();
    if (bgAudio) { bgAudio.pause(); bgAudio.muted = true; bgAudio.removeAttribute('src'); }
    wasPlaying = false;
    revokeOfflineUrl();

    function onPlaySuccess() {
      btnPlay.innerHTML = IC_PAUSE;
      startBgMirror();
    }

    function retryAfterCanPlay() {
      player.addEventListener('canplay', function() {
        player.play().then(onPlaySuccess).catch(function(e) {
          console.error('playTrack retry also failed:', e);
          btnPlay.innerHTML = IC_PLAY;
        });
      }, { once: true });
    }

    function beginPlayback(playback) {
      player.src = playback.url;
      player.load();
      player.play().then(onPlaySuccess).catch(function(err) {
        if (playback.offline) {
          console.warn('Offline playback failed, falling back to stream:', err);
          revokeOfflineUrl();
          player.src = playback.fallbackUrl;
          player.load();
          player.play().then(onPlaySuccess).catch(function(fallbackErr) {
            console.warn('Stream fallback play() failed, waiting for canplay:', fallbackErr);
            retryAfterCanPlay();
          });
          return;
        }
        console.warn('playTrack play() failed, waiting for canplay:', err);
        retryAfterCanPlay();
      });
      generateWaveform(playback.url);
    }

    playerTitle.textContent = t.title;
    playerArtist.textContent = t.artist || t.relative_path;
    if (t.thumbnail_url) {
      playerThumb.src = t.thumbnail_lg_url || t.thumbnail_url;
      playerThumb.style.display = '';
    } else {
      playerThumb.src = FILE_PLACEHOLDER;
      playerThumb.style.display = '';
    }
    btnPlay.innerHTML = IC_PAUSE;
    playerBar.classList.remove('view-hidden');
    /* Show video player element before playback starts — the CSS sets
       #player { display:none }, so we must override with inline block */
    if (player.tagName === 'VIDEO') player.style.display = 'block';
    markActive();
    updateMediaSession(t);
    renderPlayerRating(t.rating || 0);
    refreshMetadata(t);
    /* Auto-update lyrics panel if currently open */
    if (LYRICS_ENABLED && _lyricsOpen) openLyricsPanel(t.relative_path || '', t.title);

    /* playback progress: track current item and try to resume */
    clearTimeout(_progressTimer);
    _progressRelPath = t.relative_path || '';
    loadAndSeekProgress(_progressRelPath);

    /* load sprite sheet for video scrubber preview */
    loadSpriteData(t.relative_path || '');

    playOfflineOrStream(t.stream_url)
      .then(beginPlayback)
      .catch(function() {
        beginPlayback({ url: t.stream_url, offline: false, fallbackUrl: t.stream_url });
      });
  }

  function playTrack(index) {
    if (index < 0 || index >= filteredItems.length) return;
    playItem(filteredItems[index], index);
  }

  function refreshMetadata(t) {
    var base = API_PATH.substring(0, API_PATH.lastIndexOf('/'));
    var metaUrl = base + '/metadata?path=' + encodeURIComponent(t.relative_path);
    fetch(metaUrl)
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(meta) {
        if (!meta) return;
        var changed = false;
        if (meta.title && meta.title !== t.title) {
          t.title = meta.title;
          playerTitle.textContent = meta.title;
          changed = true;
        }
        if (meta.artist && meta.artist !== t.artist) {
          t.artist = meta.artist;
          playerArtist.textContent = meta.artist;
          changed = true;
        }
        if (typeof meta.rating === 'number') {
          t.rating = meta.rating;
          renderPlayerRating(meta.rating);
        }
        if (changed) {
          updateMediaSession(t);
          renderTracks(filteredItems);
          markActive();
        }
      })
      .catch(function() {});
  }

  function togglePlay() {
    if (currentIndex < 0 && filteredItems.length) { playTrack(0); return; }
    if (player.paused) {
      /* If bg audio was driving playback (came back from background), sync first */
      if (bgAudio && !bgAudio.muted) {
        player.currentTime = bgAudio.currentTime;
        bgAudio.muted = true;
      }
      player.play().then(function() { startBgMirror(); }).catch(function() {});
      btnPlay.innerHTML = IC_PAUSE;
    } else {
      /* Intentional user pause — clear wasPlaying */
      wasPlaying = false;
      player.pause();
      if (bgAudio) { bgAudio.pause(); bgAudio.muted = true; }
      stopBgSync();
      btnPlay.innerHTML = IC_PLAY;
    }
  }

  /* ── Shuffle logic ── */
  /* Fisher-Yates shuffle of an array in place */
  function fisherYates(arr) {
    for (var i = arr.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
    }
    return arr;
  }

  /* Build a weighted shuffle queue: items with higher rating appear more often.
     Rating 0 → weight 1, Rating 5 → weight 6. Items with no rating → weight 1. */
  function buildWeightedQueue(items) {
    var pool = [];
    items.forEach(function(t, idx) {
      var w = Math.max(1, Math.round((t.rating || 0) + 1));
      for (var i = 0; i < w; i++) pool.push(idx);
    });
    return fisherYates(pool);
  }

  /* Build a simple uniform shuffle queue */
  function buildNormalQueue(items) {
    var indices = items.map(function(_, i) { return i; });
    return fisherYates(indices);
  }

  /* Rebuild shuffle queue — called whenever filteredItems or shuffleMode changes */
  function rebuildShuffleQueue(startIndex) {
    if (!shuffleMode || !filteredItems.length) { shuffleQueue = []; shufflePos = -1; return; }
    shuffleQueue = shuffleMode === 'weighted'
      ? buildWeightedQueue(filteredItems)
      : buildNormalQueue(filteredItems);
    /* Put startIndex first so current track leads */
    if (typeof startIndex === 'number' && startIndex >= 0) {
      var pos = shuffleQueue.indexOf(startIndex);
      if (pos > 0) {
        shuffleQueue.splice(pos, 1);
        shuffleQueue.unshift(startIndex);
      }
    }
    shufflePos = 0;
  }

  /* Next index respecting shuffle state */
  function nextIndex() {
    if (shuffleMode && shuffleQueue.length) {
      shufflePos = (shufflePos + 1) % shuffleQueue.length;
      /* Replenish weighted queue when exhausted */
      if (shufflePos === 0 && shuffleMode === 'weighted') {
        shuffleQueue = buildWeightedQueue(filteredItems);
      }
      return shuffleQueue[shufflePos];
    }
    return currentIndex < filteredItems.length - 1 ? currentIndex + 1 : 0;
  }

  /* Prev index respecting shuffle state */
  function prevIndex() {
    if (shuffleMode && shuffleQueue.length) {
      shufflePos = (shufflePos - 1 + shuffleQueue.length) % shuffleQueue.length;
      return shuffleQueue[shufflePos];
    }
    return currentIndex > 0 ? currentIndex - 1 : filteredItems.length - 1;
  }

  /* Toggle shuffle mode: off → normal → weighted → off */
  function cycleShuffle() {
    if (!shuffleMode) {
      shuffleMode = 'normal';
    } else if (shuffleMode === 'normal') {
      shuffleMode = 'weighted';
    } else {
      shuffleMode = false;
    }
    localStorage.setItem('ht-shuffle-mode', shuffleMode || '');
    updateShuffleBtn();
    rebuildShuffleQueue(currentIndex >= 0 ? currentIndex : 0);
  }

  /* Activate weighted shuffle directly (long-press) */
  function activateWeightedShuffle() {
    shuffleMode = 'weighted';
    localStorage.setItem('ht-shuffle-mode', 'weighted');
    updateShuffleBtn();
    rebuildShuffleQueue(currentIndex >= 0 ? currentIndex : 0);
    showToast('Gewichteter Shuffle aktiv (nach Bewertung)');
  }

  function updateShuffleBtn() {
    if (!btnShuffle) return;
    btnShuffle.classList.toggle('shuffle-active', !!shuffleMode);
    btnShuffle.classList.toggle('shuffle-weighted', shuffleMode === 'weighted');
    btnShuffle.title = shuffleMode === 'weighted'
      ? 'Shuffle (gewichtet nach Bewertung) — Long Press für Aus'
      : shuffleMode === 'normal'
        ? 'Shuffle (zufällig) — Klick für gewichtet, Long Press für Aus'
        : 'Shuffle aktivieren';
  }

  /* ── Rating stars (audio-only write, display-only for video) ── */
  var playerRatingEl = document.getElementById('player-rating');

  function renderPlayerRating(stars) {
    if (!playerRatingEl) return;
    var rounded = Math.round(stars || 0);
    playerRatingEl.innerHTML = '';
    for (var i = 1; i <= 5; i++) {
      var btn = document.createElement('button');
      btn.className = 'player-rating-star' + (i <= rounded ? ' active' : '');
      btn.innerHTML = i <= rounded ? IC_STAR_FILLED : IC_STAR_EMPTY;
      btn.dataset.star = i;
      btn.title = i + (i === 1 ? ' Stern' : ' Sterne');
      if (!RATING_WRITE_ENABLED) btn.style.pointerEvents = 'none';
      playerRatingEl.appendChild(btn);
    }
    playerRatingEl.removeAttribute('hidden');
  }

  function setRating(stars) {
    if (!RATING_WRITE_ENABLED) return;
    var t = filteredItems[currentIndex];
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
        t.rating = d.rating;
        renderPlayerRating(d.rating);
        /* rebuild weighted shuffle queue so new rating is reflected immediately */
        if (shuffleMode === 'weighted') rebuildShuffleQueue(currentIndex);
        /* show toast with undo option if entry_id was returned */
        if (d.entry_id) {
          showRatingToastWithUndo(stars, prevRating, d.entry_id, t);
        } else {
          showToast(stars + (stars === 1 ? ' Stern' : ' Sterne') + ' vergeben');
        }
      })
      .catch(function() {});
  }

  function showRatingToastWithUndo(stars, prevStars, entryId, t) {
    var toast = document.getElementById('toast');
    if (!toast) { showToast(stars + (stars === 1 ? ' Stern' : ' Sterne') + ' vergeben'); return; }
    var label = stars + (stars === 1 ? ' Stern' : ' Sterne') + ' vergeben';
    /* build toast via DOM — avoids quote-escaping in onclick attribute */
    toast.innerHTML = '';
    var span = document.createElement('span');
    span.textContent = label;
    toast.appendChild(span);
    var undoBtn = document.createElement('button');
    undoBtn.textContent = 'Rueckgaengig';
    undoBtn.style.cssText = 'margin-left:0.5rem;background:none;border:1px solid #888;'
      + 'color:inherit;border-radius:4px;padding:1px 8px;cursor:pointer;font-size:0.8rem;';
    undoBtn.addEventListener('click', function() { undoRating(undoBtn, entryId, prevStars); });
    toast.appendChild(undoBtn);
    toast.classList.add('show');
    clearTimeout(toast._hideTimer);
    toast._hideTimer = setTimeout(function() { toast.classList.remove('show'); }, 5000);
  }

  function undoRating(btn, entryId, prevStars) {
    btn.disabled = true; btn.textContent = '…';
    fetch(AUDIT_UNDO_PATH, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entry_id: entryId })
    })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        var t2 = filteredItems[currentIndex];
        if (d.ok && t2) {
          t2.rating = prevStars;
          renderPlayerRating(prevStars);
          if (shuffleMode === 'weighted') rebuildShuffleQueue(currentIndex);
        }
        var toast = document.getElementById('toast');
        if (toast) {
          toast.innerHTML = d.ok ? 'Rückgängig gemacht ✓' : ('Fehler: ' + (d.detail || '?'));
          clearTimeout(toast._hideTimer);
          toast._hideTimer = setTimeout(function() { toast.classList.remove('show'); }, 2500);
        }
      })
      .catch(function() { showToast('Netzwerkfehler beim Rückgängig'); });
  }

  if (playerRatingEl) {
    /* hover preview */
    playerRatingEl.addEventListener('mouseover', function(e) {
      var btn = e.target.closest('.player-rating-star');
      if (!btn || !RATING_WRITE_ENABLED) return;
      var n = parseInt(btn.dataset.star, 10);
      playerRatingEl.querySelectorAll('.player-rating-star').forEach(function(b, i) {
        b.classList.toggle('hover', i < n);
      });
    });
    playerRatingEl.addEventListener('mouseleave', function() {
      playerRatingEl.querySelectorAll('.player-rating-star').forEach(function(b) {
        b.classList.remove('hover');
      });
    });
    /* click to rate */
    playerRatingEl.addEventListener('click', function(e) {
      var btn = e.target.closest('.player-rating-star');
      if (!btn || !RATING_WRITE_ENABLED) return;
      setRating(parseInt(btn.dataset.star, 10));
    });
  }


  if (SHUFFLE_ENABLED) {
    var _savedShuffle = localStorage.getItem('ht-shuffle-mode');
    if (_savedShuffle === 'normal' || _savedShuffle === 'weighted') {
      shuffleMode = _savedShuffle;
    }
    updateShuffleBtn();
  }

  btnPlay.addEventListener('click', togglePlay);
  btnPrev.addEventListener('click', function() { playTrack(prevIndex()); });
  btnNext.addEventListener('click', function() { playTrack(nextIndex()); });

  /* ── Shuffle button: click = cycle modes, long-press (600 ms) = weighted ── */
  if (SHUFFLE_ENABLED && btnShuffle) {
    var _shuffleLongPressed = false;
    var _shuffleLongPressTimer = null;
    function _startShuffleLongPress() {
      _shuffleLongPressed = false;
      _shuffleLongPressTimer = setTimeout(function() {
        _shuffleLongPressed = true;
        activateWeightedShuffle();
      }, 600);
    }
    function _cancelShuffleLongPress() { clearTimeout(_shuffleLongPressTimer); }
    btnShuffle.addEventListener('mousedown', _startShuffleLongPress);
    btnShuffle.addEventListener('mouseup', _cancelShuffleLongPress);
    btnShuffle.addEventListener('mouseleave', _cancelShuffleLongPress);
    btnShuffle.addEventListener('touchstart', function(e) {
      e.preventDefault();
      _startShuffleLongPress();
    }, { passive: false });
    btnShuffle.addEventListener('touchend', _cancelShuffleLongPress);
    btnShuffle.addEventListener('touchcancel', _cancelShuffleLongPress);
    btnShuffle.addEventListener('click', function() {
      if (!_shuffleLongPressed) cycleShuffle();
      _shuffleLongPressed = false;
    });
  }

  player.addEventListener('ended', function() {
    clearProgressFor(_progressRelPath);
    playTrack(nextIndex());
  });
  player.addEventListener('pause', function() {
    /* Don't change state when the browser auto-paused for background,
       or when bg audio has taken over playback */
    if (document.hidden) return;
    if (bgAudioIsActive()) return;
    /* User-initiated pause (custom button OR native controls) */
    wasPlaying = false;
    if (bgAudio) { bgAudio.pause(); bgAudio.muted = true; }
    stopBgSync();
    if (!player.ended) btnPlay.innerHTML = IC_PLAY;
    saveProgressNow();
  });
  player.addEventListener('play',  function() { btnPlay.innerHTML = IC_PAUSE; });
  player.addEventListener('timeupdate', function() {
    if (!isFinite(player.duration)) return;
    progressBar.max = player.duration; progressBar.value = player.currentTime;
    timeCur.textContent = fmtTime(player.currentTime);
    drawWaveform(player.currentTime / player.duration);
    saveProgressDebounced();
  });
  player.addEventListener('loadedmetadata', function() {
    timeDur.textContent = fmtTime(player.duration); progressBar.max = player.duration;
  });
  progressBar.addEventListener('input', function() { player.currentTime = progressBar.value; });

  /* bg audio events — keep UI in sync when playing in background */
  if (isVideoPlayer) {
    setInterval(function() {
      if (bgAudio && !bgAudio.muted && document.hidden) {
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

  /* Logo-Icon click → always navigate back to root */
  logoHomeBtn.addEventListener('click', function() {
    currentPath = '';
    showFolderView();
  });

  /* Show video player element when something starts playing */
  if (isVideoPlayer) {
    player.addEventListener('loadeddata', function() {
      player.style.display = 'block';
    });
  }

  /* ── Favoriten — speichern & teilen ── */
  var _savedFavorites = {};

  function loadFavorites() {
    var base = API_PATH.substring(0, API_PATH.lastIndexOf('/'));
    fetch(base + '/shortcuts')
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(data) {
        _savedFavorites = {};
        if (data && Array.isArray(data.items)) {
          data.items.forEach(function(s) { _savedFavorites[s.id] = true; });
        }
        updateFavoriteButtons();
        /* If favorites filter is active, re-apply so newly loaded state is reflected */
        if (filterFav && inPlaylist) applyFilter();
      })
      .catch(function() {});
  }

  function updateFavoriteButtons() {
    document.querySelectorAll('.track-pin-btn').forEach(function(btn) {
      var rp = btn.dataset.relativePath;
      if (_savedFavorites[rp]) {
        btn.classList.add('pinned');
        btn.title = 'Favorit entfernen';
      } else {
        btn.classList.remove('pinned');
        btn.title = 'Favorit';
      }
    });
  }

  /* ── metadata edit modal ── */
  function openEditModal(idx) {
    if (!METADATA_EDIT_ENABLED) return;
    var t = filteredItems[idx];
    if (!t) return;
    var backdrop = document.getElementById('edit-modal-backdrop');
    if (!backdrop) return;
    document.getElementById('edit-modal-title-input').value = t.title || '';
    document.getElementById('edit-modal-artist-input').value = t.artist || '';
    document.getElementById('edit-modal-album-input').value = '';
    document.getElementById('edit-modal-path').value = t.relative_path || '';
    document.getElementById('edit-modal-idx').value = String(idx);
    backdrop.removeAttribute('hidden');
    document.body.classList.add('modal-open');
    document.getElementById('edit-modal-title-input').focus();
  }

  function closeEditModal() {
    var backdrop = document.getElementById('edit-modal-backdrop');
    if (backdrop) backdrop.setAttribute('hidden', '');
    document.body.classList.remove('modal-open');
  }

  function submitEditModal() {
    var path = document.getElementById('edit-modal-path').value;
    var idx = parseInt(document.getElementById('edit-modal-idx').value, 10);
    var title = document.getElementById('edit-modal-title-input').value.trim();
    var artist = document.getElementById('edit-modal-artist-input').value.trim();
    var album = document.getElementById('edit-modal-album-input').value.trim();
    var saveBtn = document.getElementById('edit-modal-save-btn');
    if (!path) return;
    if (saveBtn) saveBtn.disabled = true;
    fetch(METADATA_EDIT_PATH, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: path, title: title, artist: artist, album: album || null })
    })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (saveBtn) saveBtn.disabled = false;
        if (d.ok) {
          /* Update in-memory items so the list reflects changes immediately */
          var updates = { title: title, artist: artist };
          if (filteredItems[idx]) {
            filteredItems[idx] = Object.assign({}, filteredItems[idx], updates);
          }
          for (var i = 0; i < allItems.length; i++) {
            if (allItems[i].relative_path === path) {
              allItems[i] = Object.assign({}, allItems[i], updates);
              break;
            }
          }
          closeEditModal();
          renderTracks(filteredItems);
          /* Update player display if this is the currently playing track */
          if (idx === currentIndex) {
            if (playerTitle) playerTitle.textContent = title;
            if (playerArtist) playerArtist.textContent = artist;
          }
          showToast('Gespeichert \u2713');
        } else {
          showToast('Fehler beim Speichern');
        }
      })
      .catch(function() {
        if (saveBtn) saveBtn.disabled = false;
        showToast('Netzwerkfehler beim Speichern');
      });
  }

  function toggleFavorite(item, btn) {
    if (!item || !item.relative_path) return;
    var base = API_PATH.substring(0, API_PATH.lastIndexOf('/'));
    var isPinned = _savedFavorites[item.relative_path];

    if (isPinned) {
      /* Remove favorite */
      fetch(base + '/shortcuts?id=' + encodeURIComponent(item.relative_path), { method: 'DELETE' })
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function() {
          delete _savedFavorites[item.relative_path];
          if (btn) { btn.classList.remove('pinned'); btn.title = 'Favorit'; }
          showToast('Favorit entfernt');
        })
        .catch(function() {});
    } else {
      /* Add favorite */
      fetch(base + '/shortcuts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: item.relative_path,
          title: item.title || item.relative_path,
          icon: '/thumb?path=' + encodeURIComponent(item.relative_path)
        })
      })
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function() {
        _savedFavorites[item.relative_path] = true;
        if (btn) { btn.classList.add('pinned'); btn.title = 'Favorit entfernen'; }
        showToast('Als Favorit gespeichert');
        /* On mobile: additionally offer share sheet for home screen shortcut */
        if (navigator.share && ('ontouchstart' in window || navigator.maxTouchPoints > 0)) {
          var deepUrl = window.location.origin + '/?id=' + encodeURIComponent(item.relative_path);
          setTimeout(function() {
            navigator.share({
              title: item.title || 'Favorit',
              text: item.title || '',
              url: deepUrl
            }).catch(function() {});
          }, 600);
        }
      })
      .catch(function() { showToast('Favorit konnte nicht gespeichert werden'); });
    }
  }

  function showToast(msg) {
    var t = document.getElementById('ht-toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'ht-toast';
      t.style.cssText = 'position:fixed;bottom:100px;left:50%;transform:translateX(-50%);background:#333;color:#fff;padding:10px 20px;border-radius:8px;z-index:9999;font-size:14px;max-width:90%;text-align:center;transition:opacity .3s';
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.style.opacity = '1';
    t.style.display = 'block';
    clearTimeout(t._timer);
    t._timer = setTimeout(function() { t.style.opacity = '0'; setTimeout(function() { t.style.display = 'none'; }, 300); }, 3500);
  }

  viewToggle.addEventListener('click', function() {
    if (viewMode === 'list') viewMode = 'grid';
    else if (viewMode === 'grid') viewMode = 'filenames';
    else viewMode = 'list';
    localStorage.setItem('ht-view-mode', viewMode);
    if (inPlaylist) {
      applyViewMode();
      renderTracks(filteredItems);
    } else {
      showFolderView();
    }
  });
  searchInput.addEventListener('input', applyFilter);
  sortField.addEventListener('change', applyFilter);
  if (filterRatingBtn) {
    filterRatingBtn.addEventListener('click', function() {
      /* cycle 0 → 1 → 2 → 3 → 4 → 5 → 0 */
      filterRating = (filterRating + 1) % 6;
      localStorage.setItem('ht-filter-rating', String(filterRating));
      updateFilterChips();
      applyFilter();
    });
  }
  if (filterFavBtn) {
    filterFavBtn.addEventListener('click', function() {
      filterFav = !filterFav;
      localStorage.setItem('ht-filter-fav', filterFav ? '1' : '0');
      updateFilterChips();
      applyFilter();
    });
  }
  if (filterGenreBtn) {
    filterGenreBtn.addEventListener('click', function() {
      /* Collect genres from current playlist, cycle through them */
      var genres = {};
      (playlistItems || []).forEach(function(t) {
        if (t.genre) genres[t.genre] = true;
      });
      var genreList = Object.keys(genres).sort();
      if (!genreList.length) return;
      var idx = filterGenre ? genreList.indexOf(filterGenre) : -1;
      filterGenre = (idx + 1 < genreList.length) ? genreList[idx + 1] : '';
      localStorage.setItem('ht-filter-genre', filterGenre);
      updateFilterChips();
      applyFilter();
    });
  }
  updateFilterChips();

  /* ── init ── */
  if (METADATA_EDIT_ENABLED) {
    var _editCancelBtn = document.getElementById('edit-modal-cancel-btn');
    var _editSaveBtn   = document.getElementById('edit-modal-save-btn');
    var _editBackdrop  = document.getElementById('edit-modal-backdrop');
    if (_editCancelBtn) _editCancelBtn.addEventListener('click', closeEditModal);
    if (_editSaveBtn)   _editSaveBtn.addEventListener('click', submitEditModal);
    /* Close on backdrop click (outside the panel) */
    if (_editBackdrop) {
      _editBackdrop.addEventListener('click', function(e) {
        if (e.target === _editBackdrop) closeEditModal();
      });
    }
    /* Submit on Enter inside inputs, Escape to close */
    document.addEventListener('keydown', function(e) {
      var backdrop = document.getElementById('edit-modal-backdrop');
      if (!backdrop || backdrop.hasAttribute('hidden')) return;
      if (e.key === 'Escape') { e.preventDefault(); closeEditModal(); }
      if (e.key === 'Enter' && e.target.tagName === 'INPUT') { e.preventDefault(); submitEditModal(); }
    });
  }

  if (!OFFLINE_ENABLED) {
    if (downloadedPill) {
      downloadedPill.textContent = 'Safe Mode';
      downloadedPill.classList.add('is-offline');
    }
  } else if (typeof indexedDB !== 'undefined') {
    initDownloadDB().catch(function(err) {
      console.warn('IndexedDB not available:', err);
    }).then(function() {
      updateAllDownloadButtons();
      refreshOfflineLibrary();
    });
  } else {
    refreshOfflineLibrary();
  }
  applyViewMode();

  /* ── Deep Linking: ?id=relative/path auto-navigates & plays ── */
  var _deepLinkId = (new URLSearchParams(window.location.search)).get('id');

  function handleDeepLink() {
    if (!_deepLinkId || !allItems.length) return;
    var target = allItems.find(function(it) { return it.relative_path === _deepLinkId; });
    if (!target) { _deepLinkId = null; return; }
    /* Navigate to the item's parent folder */
    var slash = _deepLinkId.lastIndexOf('/');
    currentPath = slash > 0 ? _deepLinkId.substring(0, slash) : '';
    /* Gather siblings in that folder */
    var c = contentsAt(currentPath);
    var siblings = c.files.length ? c.files : itemsUnder(currentPath);
    var idx = siblings.findIndex(function(it) { return it.relative_path === _deepLinkId; });
    if (idx < 0) { idx = 0; }
    showPlaylist(siblings, true, idx);
    /* Clean the URL so reload doesn't re-trigger deep link */
    var cleanUrl = window.location.pathname;
    history.replaceState(null, '', cleanUrl);
    _deepLinkId = null;
  }

  /* ── User Playlists ── */
  var _userPlaylists = [];
  var _playlistAddPath = '';
  var _currentPlaylistId = '';

  /* ── Favorites custom order (server-side + localStorage fallback) ── */
  function _loadFavoritesOrder() {
    try {
      var raw = localStorage.getItem('ht-favorites-order');
      return raw ? JSON.parse(raw) : [];
    } catch (e) { return []; }
  }
  function _saveFavoritesOrder(paths) {
    try { localStorage.setItem('ht-favorites-order', JSON.stringify(paths)); }
    catch (e) { /* quota exceeded — ignore */ }
    /* persist to server (fire-and-forget) */
    fetch(FOLDER_ORDER_API_PATH, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder_path: '__favorites__', items: paths })
    }).catch(function() {});
  }
  function _loadFavoritesOrderAsync(cb) {
    fetch(FOLDER_ORDER_API_PATH + '?path=__favorites__')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        var items = d.items || [];
        if (items.length) {
          try { localStorage.setItem('ht-favorites-order', JSON.stringify(items)); }
          catch (e) {}
          cb(items);
        } else {
          cb(_loadFavoritesOrder());
        }
      }).catch(function() { cb(_loadFavoritesOrder()); });
  }
  function _sortFavoritesByOrder(favItems) {
    var order = _loadFavoritesOrder();
    if (!order.length) return favItems;
    var orderMap = {};
    order.forEach(function(rp, i) { orderMap[rp] = i; });
    return favItems.slice().sort(function(a, b) {
      var ia = orderMap[a.relative_path], ib = orderMap[b.relative_path];
      if (ia === undefined && ib === undefined) return 0;
      if (ia === undefined) return 1;
      if (ib === undefined) return -1;
      return ia - ib;
    });
  }

  /* ── Folder custom order (server-side + localStorage fallback) ── */
  function _folderOrderKey(folderPath) {
    return 'ht-folder-order-' + (folderPath || '__root__');
  }
  function _loadFolderOrder(folderPath) {
    try {
      var raw = localStorage.getItem(_folderOrderKey(folderPath));
      return raw ? JSON.parse(raw) : [];
    } catch (e) { return []; }
  }
  function _saveFolderOrder(folderPath, paths) {
    try { localStorage.setItem(_folderOrderKey(folderPath), JSON.stringify(paths)); }
    catch (e) { /* quota exceeded — ignore */ }
    /* persist to server (fire-and-forget) */
    fetch(FOLDER_ORDER_API_PATH, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder_path: folderPath || '__root__', items: paths })
    }).catch(function() {});
  }
  function _loadFolderOrderAsync(folderPath, cb) {
    var key = folderPath || '__root__';
    fetch(FOLDER_ORDER_API_PATH + '?path=' + encodeURIComponent(key))
      .then(function(r) { return r.json(); })
      .then(function(d) {
        var items = d.items || [];
        if (items.length) {
          try { localStorage.setItem(_folderOrderKey(folderPath), JSON.stringify(items)); }
          catch (e) {}
          cb(items);
        } else {
          cb(_loadFolderOrder(folderPath));
        }
      }).catch(function() { cb(_loadFolderOrder(folderPath)); });
  }
  function _sortByFolderOrder(folderPath, items) {
    var order = _loadFolderOrder(folderPath);
    if (!order.length) return items;
    var orderMap = {};
    order.forEach(function(rp, i) { orderMap[rp] = i; });
    return items.slice().sort(function(a, b) {
      var ia = orderMap[a.relative_path], ib = orderMap[b.relative_path];
      if (ia === undefined && ib === undefined) return 0;
      if (ia === undefined) return 1;
      if (ib === undefined) return -1;
      return ia - ib;
    });
  }

  var _playlistRevision = 0;
  var _playlistSyncTimer = null;
  var _PLAYLIST_SYNC_INTERVAL = """
        + str(playlist_sync_interval_ms)
        + """; /* ms */

  function loadUserPlaylists() {
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
    if (!pl || !pl.items || pl.items.length === 0) return null;
    var resolved = [];
    pl.items.forEach(function(rp) {
      var match = allItems.find(function(it) { return it.relative_path === rp; });
      if (match) resolved.push(match);
    });
    if (resolved.length === 0) return null;
    return { pl: pl, resolved: resolved };
  }

  function showUserPlaylistView(plId) {
    /* Show playlist content without auto-playing (browse mode) */
    if (plId === '__favorites__') {
      var favItems = allItems.filter(function(t) { return !!_savedFavorites[t.relative_path]; });
      if (favItems.length === 0) { showToast('Keine Favoriten vorhanden'); return; }
      _currentPlaylistId = '__favorites__';
      playlistItems = _sortFavoritesByOrder(favItems);
      inPlaylist = true;
      currentPath = '';
      var hdr = document.getElementById('header-title');
      if (hdr) hdr.textContent = 'Favoriten';
      backBtn.style.display = 'inline-block';
      folderGrid.classList.add('view-hidden');
      trackView.classList.remove('view-hidden');
      filterBar.classList.remove('view-hidden');
      playerBar.classList.remove('view-hidden');
      searchInput.value = '';
      renderBreadcrumb();
      applyFilter();
      /* Pre-warm: fetch server-side favorites order and re-sort if different */
      _loadFavoritesOrderAsync(function(serverOrder) {
        if (!serverOrder.length) return;
        if (_currentPlaylistId !== '__favorites__') return;
        var localOrder = _loadFavoritesOrder();
        if (JSON.stringify(localOrder) === JSON.stringify(serverOrder)) return;
        playlistItems = _sortFavoritesByOrder(favItems);
        applyFilter();
      });
      return;
    }
    var data = _resolvePlaylistItems(plId);
    if (!data) { showToast('Keine Titel in dieser Playlist gefunden'); return; }
    _currentPlaylistId = plId;
    playlistItems = data.resolved;
    inPlaylist = true;
    currentPath = '';
    var hdr = document.getElementById('header-title');
    if (hdr) hdr.textContent = data.pl.name;
    backBtn.style.display = 'inline-block';
    folderGrid.classList.add('view-hidden');
    trackView.classList.remove('view-hidden');
    filterBar.classList.remove('view-hidden');
    playerBar.classList.remove('view-hidden');
    searchInput.value = '';
    renderBreadcrumb();
    applyFilter();
  }

  function playUserPlaylist(plId) {
    if (plId === '__favorites__') {
      var favItems = allItems.filter(function(t) { return !!_savedFavorites[t.relative_path]; });
      if (favItems.length === 0) { showToast('Keine Favoriten vorhanden'); return; }
      _currentPlaylistId = '__favorites__';
      var sorted = _sortFavoritesByOrder(favItems);
      playlistItems = sorted;
      filteredItems = sorted;
      inPlaylist = true;
      currentPath = '';
      var hdr = document.getElementById('header-title');
      if (hdr) hdr.textContent = 'Favoriten';
      renderTracks(favItems, true);
      playTrack(0);
      return;
    }
    var data = _resolvePlaylistItems(plId);
    if (!data) { showToast('Keine Titel in dieser Playlist gefunden'); return; }
    _currentPlaylistId = plId;
    playlistItems = data.resolved;
    filteredItems = data.resolved;
    inPlaylist = true;
    currentPath = '';
    var hdr = document.getElementById('header-title');
    if (hdr) hdr.textContent = data.pl.name;
    renderTracks(data.resolved, true);
    playTrack(0);
  }

  function deleteUserPlaylist(plId) {
    /* TODO: Nach Entwicklungsphase → Nachfrage + Archivierung statt L\u00f6schung */
    var pl = _userPlaylists.find(function(p) { return p.id === plId; });
    var name = pl ? pl.name : 'Playlist';
    if (!confirm('Playlist "' + name + '" wirklich l\u00f6schen?')) return;
    /* Optimistic: remove locally first */
    var snap = _snapshotPlaylists();
    _userPlaylists = _userPlaylists.filter(function(p) { return p.id !== plId; });
    if (!currentPath && !inPlaylist) showFolderView();
    fetch(PLAYLISTS_API_PATH + '?id=' + encodeURIComponent(plId), { method: 'DELETE' })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        _userPlaylists = d.items || [];
        if (typeof d.revision === 'number') _playlistRevision = d.revision;
        showToast('Playlist gel\u00f6scht');
        if (!currentPath && !inPlaylist) showFolderView();
      })
      .catch(function() {
        _restorePlaylists(snap);
        showToast('Fehler beim L\u00f6schen \u2014 r\u00fcckg\u00e4ngig');
        if (!currentPath && !inPlaylist) showFolderView();
      });
  }

  /* ── add-to-playlist modal ── */
  function openPlaylistModal(relativePath) {
    _playlistAddPath = relativePath;
    var backdrop = document.getElementById('playlist-modal-backdrop');
    if (!backdrop) return;
    backdrop.hidden = false;
    document.body.classList.add('modal-open');
    renderPlaylistModalList();
  }

  function closePlaylistModal() {
    var backdrop = document.getElementById('playlist-modal-backdrop');
    if (backdrop) backdrop.hidden = true;
    document.body.classList.remove('modal-open');
    _playlistAddPath = '';
  }

  function renderPlaylistModalList() {
    var listEl = document.getElementById('playlist-modal-list');
    if (!listEl) return;
    if (_userPlaylists.length === 0) {
      listEl.innerHTML = '<li style="padding:0.5rem;color:var(--sub);font-size:0.85rem">Noch keine Playlists. Erstelle eine neue!</li>';
      return;
    }
    listEl.innerHTML = _userPlaylists.map(function(pl) {
      var cnt = (pl.items || []).length;
      return '<li class="playlist-modal-item" data-id="' + escHtml(pl.id) + '">' +
        '<span class="playlist-modal-item-name">' + escHtml(pl.name) + '</span>' +
        '<span class="playlist-modal-item-count">' + cnt + ' Titel</span></li>';
    }).join('');
    listEl.querySelectorAll('.playlist-modal-item').forEach(function(el) {
      el.addEventListener('click', function() {
        addToPlaylist(el.dataset.id, _playlistAddPath);
      });
    });
  }

  function addToPlaylist(plId, relativePath) {
    /* Optimistic: add item locally first */
    var snap = _snapshotPlaylists();
    var localPl = _userPlaylists.find(function(p) { return p.id === plId; });
    if (localPl && (localPl.items || []).indexOf(relativePath) < 0) {
      localPl.items = (localPl.items || []).slice();
      localPl.items.push(relativePath);
    }
    updatePlaylistPill();
    closePlaylistModal();
    showToast('Zur Playlist hinzugef\\u00fcgt');
    fetch(PLAYLISTS_API_PATH + '/items', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ playlist_id: plId, relative_path: relativePath })
    }).then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.playlist) {
          var idx = _userPlaylists.findIndex(function(p) { return p.id === plId; });
          if (idx >= 0) _userPlaylists[idx] = d.playlist;
        }
        updatePlaylistPill();
      }).catch(function() {
        _restorePlaylists(snap);
        showToast('Fehler beim Hinzuf\\u00fcgen \\u2014 r\\u00fcckg\\u00e4ngig');
      });
  }

  function createAndAddToPlaylist(name, relativePath) {
    fetch(PLAYLISTS_API_PATH, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name })
    }).then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.playlist) {
          _userPlaylists.unshift(d.playlist);
          updatePlaylistPill();
          addToPlaylist(d.playlist.id, relativePath);
        }
      }).catch(function() { showToast('Fehler beim Erstellen'); });
  }

  function movePlaylistItem(relativePath, direction) {
    if (!_currentPlaylistId) return;
    /* Optimistic: swap locally first */
    var snap = _snapshotPlaylists();
    var localPl = _userPlaylists.find(function(p) { return p.id === _currentPlaylistId; });
    if (localPl) {
      var litems = (localPl.items || []).slice();
      var li = litems.indexOf(relativePath);
      if (li >= 0) {
        var ni = direction === 'up' ? li - 1 : li + 1;
        if (ni >= 0 && ni < litems.length) {
          var tmp = litems[li]; litems[li] = litems[ni]; litems[ni] = tmp;
          localPl.items = litems;
          _applyPlaylistUpdate(localPl);
        }
      }
    }
    var savedPlId = _currentPlaylistId;
    fetch(PLAYLISTS_API_PATH + '/items', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ playlist_id: savedPlId, relative_path: relativePath, direction: direction })
    }).then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.playlist) {
          var idx = _userPlaylists.findIndex(function(p) { return p.id === savedPlId; });
          if (idx >= 0) _userPlaylists[idx] = d.playlist;
          if (_currentPlaylistId === savedPlId) _applyPlaylistUpdate(d.playlist);
        }
      }).catch(function() {
        _restorePlaylists(snap);
        if (_currentPlaylistId === savedPlId && localPl) _applyPlaylistUpdate(snap.find(function(p) { return p.id === savedPlId; }) || localPl);
        showToast('Fehler beim Verschieben \u2014 r\u00fcckg\u00e4ngig');
      });
  }

  function reorderPlaylistItem(relativePath, toIndex) {
    if (!_currentPlaylistId) return;

    /* Favorites: client-side reorder via localStorage */
    if (_currentPlaylistId === '__favorites__') {
      var paths = playlistItems.map(function(it) { return it.relative_path; });
      var oldIdx = paths.indexOf(relativePath);
      if (oldIdx < 0) return;
      paths.splice(oldIdx, 1);
      var clamped = Math.max(0, Math.min(toIndex, paths.length));
      paths.splice(clamped, 0, relativePath);
      _saveFavoritesOrder(paths);
      /* rebuild playlistItems in new order */
      var itemMap = {};
      playlistItems.forEach(function(it) { itemMap[it.relative_path] = it; });
      var reordered = paths.map(function(rp) { return itemMap[rp]; }).filter(Boolean);
      var playingPath = currentIndex >= 0 && filteredItems[currentIndex]
        ? filteredItems[currentIndex].relative_path : null;
      playlistItems = reordered;
      filteredItems = reordered;
      if (playingPath) {
        var newIdx = reordered.findIndex(function(it) { return it.relative_path === playingPath; });
        if (newIdx >= 0) currentIndex = newIdx;
      }
      renderTracks(reordered, true);
      return;
    }

    /* Folder: client-side reorder via localStorage */
    if (_currentPlaylistId === '__folder__') {
      var fpaths = playlistItems.map(function(it) { return it.relative_path; });
      var fOldIdx = fpaths.indexOf(relativePath);
      if (fOldIdx < 0) return;
      fpaths.splice(fOldIdx, 1);
      var fClamped = Math.max(0, Math.min(toIndex, fpaths.length));
      fpaths.splice(fClamped, 0, relativePath);
      _saveFolderOrder(currentPath, fpaths);
      var fItemMap = {};
      playlistItems.forEach(function(it) { fItemMap[it.relative_path] = it; });
      var fReordered = fpaths.map(function(rp) { return fItemMap[rp]; }).filter(Boolean);
      var fPlayingPath = currentIndex >= 0 && filteredItems[currentIndex]
        ? filteredItems[currentIndex].relative_path : null;
      playlistItems = fReordered;
      filteredItems = fReordered;
      if (fPlayingPath) {
        var fNewIdx = fReordered.findIndex(function(it) { return it.relative_path === fPlayingPath; });
        if (fNewIdx >= 0) currentIndex = fNewIdx;
      }
      renderTracks(fReordered, true);
      return;
    }

    /* Server-backed playlist: optimistic local reorder first */
    var snap = _snapshotPlaylists();
    var localPl = _userPlaylists.find(function(p) { return p.id === _currentPlaylistId; });
    if (localPl) {
      var litems = (localPl.items || []).slice();
      var lOld = litems.indexOf(relativePath);
      if (lOld >= 0) {
        litems.splice(lOld, 1);
        var lClamped = Math.max(0, Math.min(toIndex, litems.length));
        litems.splice(lClamped, 0, relativePath);
        localPl.items = litems;
        _applyPlaylistUpdate(localPl);
      }
    }
    var savedPlId = _currentPlaylistId;
    fetch(PLAYLISTS_API_PATH + '/items', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ playlist_id: savedPlId, relative_path: relativePath, to_index: toIndex })
    }).then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.playlist) {
          var idx = _userPlaylists.findIndex(function(p) { return p.id === savedPlId; });
          if (idx >= 0) _userPlaylists[idx] = d.playlist;
          if (_currentPlaylistId === savedPlId) _applyPlaylistUpdate(d.playlist);
        }
      }).catch(function() {
        _restorePlaylists(snap);
        if (_currentPlaylistId === savedPlId && localPl) _applyPlaylistUpdate(snap.find(function(p) { return p.id === savedPlId; }) || localPl);
        showToast('Fehler beim Verschieben \u2014 r\u00fcckg\u00e4ngig');
      });
  }

  function _applyPlaylistUpdate(pl) {
    var resolved = [];
    pl.items.forEach(function(rp) {
      var match = allItems.find(function(it) { return it.relative_path === rp; });
      if (match) resolved.push(match);
    });
    var playingPath = currentIndex >= 0 && filteredItems[currentIndex] ? filteredItems[currentIndex].relative_path : null;
    playlistItems = resolved;
    filteredItems = resolved;
    if (playingPath) {
      var newIdx = resolved.findIndex(function(it) { return it.relative_path === playingPath; });
      if (newIdx >= 0) currentIndex = newIdx;
    }
    renderTracks(resolved, true);
    updatePlaylistPill();
  }

  /* ── Drag-and-drop reorder for playlist view ── */
  var _dndCleanup = null;

  function destroyPlaylistDragDrop() {
    if (_dndCleanup) { _dndCleanup(); _dndCleanup = null; }
  }

  function initPlaylistDragDrop() {
    destroyPlaylistDragDrop();

    var trackList = document.getElementById('track-list');
    if (!trackList) return;
    var items = trackList.querySelectorAll('.track-item:not(.missing-episode)');
    if (items.length < 2) return;

    var _dragItem = null;
    var _dragPath = '';
    var _dragFromIdx = -1;
    var _ghost = null;
    var _dropTarget = null;
    var _dropAbove = true;
    var _longPressTimer = null;
    var _touchStartY = 0;
    var _touchStartX = 0;
    var _dragActive = false;
    var _pendingDrag = null;
    var LONG_PRESS_MS = 500;
    var MOVE_THRESHOLD = 10;

    function getTrackItem(el) {
      while (el && el !== trackList) {
        if (el.classList && el.classList.contains('track-item')) return el;
        el = el.parentElement;
      }
      return null;
    }

    function createGhost(item, x, y) {
      var g = document.createElement('div');
      g.className = 'playlist-drag-ghost';
      var img = item.querySelector('.track-thumb');
      var title = item.querySelector('.track-title');
      if (img && img.src) g.innerHTML = '<img src="' + img.src + '">';
      g.innerHTML += '<span>' + (title ? title.textContent : '') + '</span>';
      g.style.left = (x - 20) + 'px';
      g.style.top = (y - 20) + 'px';
      document.body.appendChild(g);
      return g;
    }

    function moveGhost(x, y) {
      if (!_ghost) return;
      _ghost.style.left = (x - 20) + 'px';
      _ghost.style.top = (y - 20) + 'px';
    }

    function clearDragClasses() {
      trackList.querySelectorAll('.drag-over-above,.drag-over-below,.dragging').forEach(function(el) {
        el.classList.remove('drag-over-above', 'drag-over-below', 'dragging');
      });
    }

    function clearDropIndicator() {
      if (_dropTarget) {
        _dropTarget.classList.remove('drag-over-above', 'drag-over-below');
        _dropTarget = null;
      }
    }

    function updateDropTarget(x, y) {
      if (_ghost) _ghost.style.display = 'none';
      var el = document.elementFromPoint(x, y);
      if (_ghost) _ghost.style.display = '';
      var target = el ? getTrackItem(el) : null;

      if (!target) {
        if (_dragItem) {
          var dragRect = _dragItem.getBoundingClientRect();
          if (dragRect.height > 0 &&
              x >= dragRect.left && x <= dragRect.right &&
              y >= dragRect.top && y <= dragRect.bottom) {
            clearDropIndicator();
            return;
          }
        }
        var tlRect = trackList.getBoundingClientRect();
        if (x >= tlRect.left && x <= tlRect.right &&
            y >= tlRect.top && y <= tlRect.bottom) {
          var visibleItems = trackList.querySelectorAll(
            '.track-item:not(.missing-episode):not(.dragging)');
          if (visibleItems.length > 0) {
            var lastItem = visibleItems[visibleItems.length - 1];
            if (_dropTarget !== lastItem) clearDropIndicator();
            _dropTarget = lastItem;
            _dropAbove = false;
            lastItem.classList.remove('drag-over-above');
            lastItem.classList.add('drag-over-below');
            return;
          }
        }
        clearDropIndicator();
        return;
      }

      if (target === _dragItem) { clearDropIndicator(); return; }

      var rect = target.getBoundingClientRect();
      var mid = rect.top + rect.height / 2;
      var above = y < mid;

      if (!above) {
        var nextSib = target.nextElementSibling;
        while (nextSib && (!nextSib.classList.contains('track-item') ||
               nextSib.classList.contains('missing-episode') ||
               nextSib === _dragItem)) {
          nextSib = nextSib.nextElementSibling;
        }
        if (nextSib && nextSib.classList.contains('track-item')) {
          target = nextSib;
          above = true;
        }
      }

      _dropAbove = above;

      var candidateIdx = Number(target.dataset.index);
      var candidateTo = above ? candidateIdx : candidateIdx + 1;
      if (_dragFromIdx < candidateTo) candidateTo--;
      if (candidateTo === _dragFromIdx) { clearDropIndicator(); return; }

      if (_dropTarget !== target) clearDropIndicator();
      _dropTarget = target;
      target.classList.toggle('drag-over-above', above);
      target.classList.toggle('drag-over-below', !above);
    }

    function startDrag(item, x, y) {
      _dragActive = true;
      _dragItem = item;
      _dragPath = '';
      var idx = Number(item.dataset.index);
      if (filteredItems[idx]) {
        _dragPath = filteredItems[idx].relative_path;
        _dragFromIdx = idx;
      }
      item.classList.add('dragging');
      document.body.classList.add('playlist-dragging');
      _ghost = createGhost(item, x, y);
    }

    function endDrag() {
      if (_longPressTimer) { clearTimeout(_longPressTimer); _longPressTimer = null; }
      if (!_dragActive) return;
      _dragActive = false;
      if (_ghost) { _ghost.remove(); _ghost = null; }
      document.body.classList.remove('playlist-dragging');

      if (_dropTarget && _dragPath) {
        var targetIdx = Number(_dropTarget.dataset.index);
        var toIndex = _dropAbove ? targetIdx : targetIdx + 1;
        if (_dragFromIdx < toIndex) toIndex--;
        if (toIndex !== _dragFromIdx && toIndex >= 0) {
          reorderPlaylistItem(_dragPath, toIndex);
        }
      }
      clearDragClasses();
      _dragItem = null;
      _dropTarget = null;
    }

    /* --- Named handlers for proper cleanup --- */
    function onMouseDown(e) {
      if (e.button !== 0) return;
      if (e.target.closest('.track-dl-btn,.track-pin-btn,.track-edit-btn,.track-playlist-btn')) return;
      var item = getTrackItem(e.target);
      if (!item) return;
      _pendingDrag = { item: item, x: e.clientX, y: e.clientY };
    }
    function onMouseMove(e) {
      if (_pendingDrag && !_dragActive) {
        var pdx = Math.abs(e.clientX - _pendingDrag.x);
        var pdy = Math.abs(e.clientY - _pendingDrag.y);
        if (pdx > MOVE_THRESHOLD || pdy > MOVE_THRESHOLD) {
          startDrag(_pendingDrag.item, e.clientX, e.clientY);
          _pendingDrag = null;
        } else {
          return;
        }
      }
      if (!_dragActive) return;
      e.preventDefault();
      moveGhost(e.clientX, e.clientY);
      updateDropTarget(e.clientX, e.clientY);
      var rect = trackList.getBoundingClientRect();
      var scrollZone = 50;
      if (e.clientY < rect.top + scrollZone) trackList.scrollTop -= 8;
      if (e.clientY > rect.bottom - scrollZone) trackList.scrollTop += 8;
    }
    function onMouseUp() { _pendingDrag = null; endDrag(); }

    function onTouchStart(e) {
      if (e.touches.length !== 1) return;
      if (e.target.closest('.track-dl-btn,.track-pin-btn,.track-edit-btn,.track-playlist-btn')) return;
      var item = getTrackItem(e.target);
      if (!item) return;
      _touchStartX = e.touches[0].clientX;
      _touchStartY = e.touches[0].clientY;
      _longPressTimer = setTimeout(function() {
        _longPressTimer = null;
        startDrag(item, _touchStartX, _touchStartY);
        if (navigator.vibrate) navigator.vibrate(30);
      }, LONG_PRESS_MS);
    }
    function onTouchMove(e) {
      if (_longPressTimer) {
        var dx = Math.abs(e.touches[0].clientX - _touchStartX);
        var dy = Math.abs(e.touches[0].clientY - _touchStartY);
        if (dx > MOVE_THRESHOLD || dy > MOVE_THRESHOLD) {
          clearTimeout(_longPressTimer);
          _longPressTimer = null;
        }
      }
      if (!_dragActive) return;
      e.preventDefault();
      var tx = e.touches[0].clientX;
      var ty = e.touches[0].clientY;
      moveGhost(tx, ty);
      updateDropTarget(tx, ty);
      var rect = trackList.getBoundingClientRect();
      var scrollZone = 50;
      if (ty < rect.top + scrollZone) trackList.scrollTop -= 6;
      if (ty > rect.bottom - scrollZone) trackList.scrollTop += 6;
    }
    function onTouchEnd() { endDrag(); }
    function onTouchCancel() {
      if (_longPressTimer) { clearTimeout(_longPressTimer); _longPressTimer = null; }
      endDrag();
    }

    /* --- Attach listeners --- */
    trackList.addEventListener('mousedown', onMouseDown);
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    trackList.addEventListener('touchstart', onTouchStart, { passive: true });
    trackList.addEventListener('touchmove', onTouchMove, { passive: false });
    trackList.addEventListener('touchend', onTouchEnd, { passive: true });
    trackList.addEventListener('touchcancel', onTouchCancel, { passive: true });

    /* --- Cleanup function --- */
    _dndCleanup = function() {
      trackList.removeEventListener('mousedown', onMouseDown);
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      trackList.removeEventListener('touchstart', onTouchStart);
      trackList.removeEventListener('touchmove', onTouchMove);
      trackList.removeEventListener('touchend', onTouchEnd);
      trackList.removeEventListener('touchcancel', onTouchCancel);
      if (_dragActive) {
        _dragActive = false;
        if (_ghost) { _ghost.remove(); _ghost = null; }
        document.body.classList.remove('playlist-dragging');
      }
      clearDragClasses();
    };
  }

  /* ── playlist event wiring ── */
  (function() {
    if (!PLAYLISTS_ENABLED) return;
    var modalClose = document.getElementById('playlist-modal-close-btn');
    if (modalClose) modalClose.addEventListener('click', closePlaylistModal);
    var modalBackdrop = document.getElementById('playlist-modal-backdrop');
    if (modalBackdrop) modalBackdrop.addEventListener('click', function(e) { if (e.target === modalBackdrop) closePlaylistModal(); });
    var newBtn = document.getElementById('playlist-modal-new-btn');
    var newInput = document.getElementById('playlist-modal-new-name');
    if (newBtn && newInput) {
      newBtn.addEventListener('click', function() {
        var n = newInput.value.trim();
        if (!n) return;
        createAndAddToPlaylist(n, _playlistAddPath);
        newInput.value = '';
      });
      newInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { newBtn.click(); }
      });
    }
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        var mb = document.getElementById('playlist-modal-backdrop');
        if (mb && !mb.hidden) closePlaylistModal();
      }
    });
  }());

  /* ── Touch swipe gestures (mobile navigation) ── */
  (function() {
    var _swipeStartX = 0;
    var _swipeStartY = 0;
    var _swipeStartT = 0;
    var _swipeActive = false;
    var SWIPE_MIN_DIST = 60;   /* px minimum horizontal distance */
    var SWIPE_MAX_VERT = 80;   /* px max vertical deviation */
    var SWIPE_MAX_TIME = 400;  /* ms max duration */

    function swipeTarget(el) {
      /* Don't intercept swipes on range inputs (progress bar, volume) */
      while (el) {
        if (el.tagName === 'INPUT' && el.type === 'range') return null;
        if (el.tagName === 'CANVAS') return null;
        if (el.classList && el.classList.contains('edit-modal-backdrop')) return null;
        if (el.classList && el.classList.contains('lyrics-panel')) return null;
        if (el.classList && el.classList.contains('offline-library')) return null;
        if (el.classList && el.classList.contains('playlist-modal-backdrop')) return null;
        el = el.parentElement;
      }
      return true;
    }

    document.addEventListener('touchstart', function(e) {
      if (!swipeTarget(e.target)) return;
      if (e.touches.length !== 1) return;
      _swipeStartX = e.touches[0].clientX;
      _swipeStartY = e.touches[0].clientY;
      _swipeStartT = Date.now();
      _swipeActive = true;
    }, { passive: true });

    document.addEventListener('touchend', function(e) {
      if (!_swipeActive) return;
      _swipeActive = false;
      if (e.changedTouches.length !== 1) return;
      var dx = e.changedTouches[0].clientX - _swipeStartX;
      var dy = e.changedTouches[0].clientY - _swipeStartY;
      var dt = Date.now() - _swipeStartT;
      if (dt > SWIPE_MAX_TIME) return;
      if (Math.abs(dy) > SWIPE_MAX_VERT) return;
      if (Math.abs(dx) < SWIPE_MIN_DIST) return;

      /* Swipe right = go back (folder view or playlist view) */
      if (dx > 0) {
        if (inPlaylist) { goBack(); }
        else if (currentPath) { goBack(); }
      }
    }, { passive: true });
  }());

  loadInitialCatalog().then(function() {
    handleDeepLink();
    loadFavorites();
    loadUserPlaylists().then(function() {
      /* Re-render root folder view to show playlist pseudo-folder cards */
      if (!currentPath && !inPlaylist) showFolderView();
      _startPlaylistSync();
    });
  });
}());
"""
    )


# ---------------------------------------------------------------------------
# Audit / Control-Panel HTML
# ---------------------------------------------------------------------------

_AUDIT_PANEL_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
:root { --bg:#121212; --surface:#1e1e1e; --surface2:#2a2a2a; --accent:#1db954;
        --text:#e0e0e0; --sub:#999; --danger:#cf6679; --warn:#ffd700; }
body { background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
       font-size:14px; min-height:100vh; }
header { display:flex; align-items:center; gap:1rem; padding:0.75rem 1.2rem;
         background:var(--surface); border-bottom:1px solid #333; flex-wrap:wrap; }
header h1 { font-size:1rem; font-weight:600; flex:1; }
.filter-bar { display:flex; gap:0.5rem; flex-wrap:wrap; padding:0.75rem 1.2rem; background:var(--surface2); border-bottom:1px solid #333; }
.filter-bar input, .filter-bar select { background:var(--bg); color:var(--text); border:1px solid #444;
  border-radius:6px; padding:0.35rem 0.6rem; font-size:0.82rem; flex:1; min-width:140px; }
.filter-bar input:focus, .filter-bar select:focus { outline:none; border-color:var(--accent); }
.filter-bar button { background:var(--accent); color:#000; border:none; border-radius:6px;
  padding:0.35rem 0.9rem; cursor:pointer; font-weight:600; font-size:0.82rem; white-space:nowrap; }
.filter-bar button:hover { background:#1ed760; }
.empty { text-align:center; color:var(--sub); padding:3rem 1rem; font-size:0.9rem; }
table { width:100%; border-collapse:collapse; }
thead th { text-align:left; padding:0.5rem 0.75rem; font-size:0.75rem; text-transform:uppercase;
           letter-spacing:.06em; color:var(--sub); border-bottom:1px solid #333; white-space:nowrap; }
tbody tr { border-bottom:1px solid #262626; transition:background 0.1s; }
tbody tr:hover { background:var(--surface2); }
tbody tr.undone { opacity:0.45; }
td { padding:0.5rem 0.75rem; vertical-align:middle; }
.td-time { font-size:0.72rem; color:var(--sub); white-space:nowrap; }
.td-action { font-size:0.72rem; font-family:monospace; background:var(--surface2);
             padding:1px 5px; border-radius:4px; white-space:nowrap; }
.td-path { font-size:0.78rem; max-width:280px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.td-path a { color:var(--accent); text-decoration:none; }
.td-path a:hover { text-decoration:underline; }
.td-change { font-size:0.82rem; white-space:nowrap; }
.old-val { color:var(--sub); text-decoration:line-through; }
.arrow { color:var(--sub); margin:0 0.25rem; }
.new-val { color:var(--accent); font-weight:600; }
.td-undo { white-space:nowrap; }
.undo-btn { background:none; border:1px solid #555; color:var(--text); border-radius:5px;
            padding:0.2rem 0.55rem; cursor:pointer; font-size:0.75rem; transition:all 0.12s; }
.undo-btn:hover { border-color:var(--warn); color:var(--warn); }
.undo-btn:disabled { opacity:0.35; cursor:default; }
.undo-btn.done { border-color:#555; color:var(--sub); }
.badge-undone { font-size:0.7rem; color:var(--sub); font-style:italic; }
.stars { color:var(--warn); letter-spacing:-1px; }
.rating-hist-link { font-size:0.7rem; color:var(--sub); margin-left:0.4rem; text-decoration:none; }
.rating-hist-link:hover { color:var(--accent); }
.toast { position:fixed; bottom:1.5rem; right:1.5rem; background:var(--surface);
         border:1px solid #444; border-radius:8px; padding:0.7rem 1rem; font-size:0.82rem;
         box-shadow:0 4px 20px #0008; opacity:0; transform:translateY(10px);
         transition:all 0.25s; pointer-events:none; z-index:999; }
.toast.show { opacity:1; transform:translateY(0); pointer-events:auto; }
"""

_AUDIT_PANEL_JS = """
var SERVER_LABEL = document.querySelector('header h1')?.textContent || '';

function fmtDate(iso) {
  try {
    var d = new Date(iso);
    return d.toLocaleDateString('de-DE', {day:'2-digit',month:'2-digit',year:'numeric'})
      + ' ' + d.toLocaleTimeString('de-DE', {hour:'2-digit',minute:'2-digit',second:'2-digit'});
  } catch(e) { return iso; }
}

function fmtStars(v) {
  if (v == null || v === '') return '–';
  var n = parseFloat(v);
  if (isNaN(n)) return String(v);
  var full = Math.round(n);
  return '★'.repeat(full) + '☆'.repeat(5 - full) + ' (' + n.toFixed(1) + ')';
}

function fmtValue(field, v) {
  if (field === 'rating') return '<span class="stars">' + fmtStars(v) + '</span>';
  return v == null ? '–' : String(v);
}

function showToast(msg, duration) {
  var t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(function() { t.classList.remove('show'); }, duration || 2800);
}

var _entries = [];

function renderTable(entries) {
  _entries = entries;
  var tbody = document.querySelector('#log-table tbody');
  if (!tbody) return;
  if (!entries.length) {
    tbody.innerHTML = '<tr><td colspan="5" class="empty">Noch keine Einträge.</td></tr>';
    return;
  }
  tbody.innerHTML = entries.map(function(e) {
    var undone = !!e.undone;
    var filename = e.path ? e.path.split('/').pop() : '–';
    var shortPath = e.path || '–';
    var histLink = '<a class="rating-hist-link" href="?path_filter=' + encodeURIComponent(e.path) + '" title="Nur dieses File anzeigen">📋</a>';
    var changeHtml = fmtValue(e.field, e.old_value)
      + '<span class="arrow">→</span>'
      + fmtValue(e.field, e.new_value);
    var undoHtml = undone
      ? '<span class="badge-undone">Rückgängig ' + fmtDate(e.undone_at) + '</span>'
      : '<button class="undo-btn" data-id="' + e.entry_id + '" onclick="doUndo(this)">Rückgängig</button>';
    return '<tr class="' + (undone ? 'undone' : '') + '">'
      + '<td class="td-time">' + fmtDate(e.timestamp) + '</td>'
      + '<td class="td-action">' + (e.action || '–') + '</td>'
      + '<td class="td-path" title="' + shortPath + '">' + filename + histLink + '</td>'
      + '<td class="td-change">' + changeHtml + '</td>'
      + '<td class="td-undo">' + undoHtml + '</td>'
      + '</tr>';
  }).join('');
}

function loadEntries() {
  var path = document.getElementById('f-path')?.value || '';
  var action = document.getElementById('f-action')?.value || '';
  var url = '/api/' + MEDIA_TYPE + '/audit?limit=500';
  if (path) url += '&path_filter=' + encodeURIComponent(path);
  if (action) url += '&action_filter=' + encodeURIComponent(action);
  fetch(url)
    .then(function(r) { return r.ok ? r.json() : null; })
    .then(function(d) { if (d) renderTable(d.items || []); })
    .catch(function() { showToast('Fehler beim Laden der Einträge'); });
}

function doUndo(btn) {
  var entryId = btn.dataset.id;
  if (!entryId) return;
  btn.disabled = true;
  btn.textContent = '…';
  fetch('/api/' + MEDIA_TYPE + '/audit/undo', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ entry_id: entryId })
  })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.ok) {
        showToast('Rückgängig gemacht ✓');
        loadEntries();
      } else {
        showToast('Fehler: ' + (d.detail || 'Unbekannt'));
        btn.disabled = false;
        btn.textContent = 'Rückgängig';
      }
    })
    .catch(function() {
      showToast('Netzwerkfehler');
      btn.disabled = false;
      btn.textContent = 'Rückgängig';
    });
}

/* Pre-fill filters from URL params */
var _params = new URLSearchParams(window.location.search);
if (_params.get('path_filter')) document.getElementById('f-path').value = _params.get('path_filter');

document.getElementById('f-form')?.addEventListener('submit', function(e) {
  e.preventDefault();
  loadEntries();
});
document.getElementById('f-clear')?.addEventListener('click', function() {
  document.getElementById('f-path').value = '';
  document.getElementById('f-action').value = '';
  history.replaceState(null, '', window.location.pathname);
  loadEntries();
});

loadEntries();
"""


def render_audit_panel_html(*, server: str, media_type: str, title: str) -> str:
    """Return the standalone audit / control-panel HTML page.

    *server*     — display label, e.g. ``"hometools audio"``
    *media_type* — ``"audio"`` or ``"video"`` (used in JS for API calls)
    *title*      — ``<title>`` text
    """
    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{_AUDIT_PANEL_CSS}</style>
</head>
<body>
  <header>
    <h1>🗒 Audit-Log — {html.escape(server)}</h1>
    <a href="/" style="color:var(--sub);font-size:0.82rem;text-decoration:none;">← Zurück zur App</a>
  </header>
  <div class="filter-bar">
    <form id="f-form" style="display:contents">
      <input id="f-path" type="text" placeholder="Datei-Filter (Teilstring)…">
      <select id="f-action">
        <option value="">Alle Aktionen</option>
        <option value="rating_write">rating_write</option>
        <option value="tag_write">tag_write</option>
        <option value="file_rename">file_rename</option>
      </select>
      <button type="submit">Filter anwenden</button>
      <button id="f-clear" type="button" style="background:var(--surface2);border:1px solid #555;color:var(--text);">Zurücksetzen</button>
    </form>
  </div>
  <table id="log-table">
    <thead>
      <tr>
        <th>Zeitpunkt</th>
        <th>Aktion</th>
        <th>Datei</th>
        <th>Änderung</th>
        <th>Rückgängig</th>
      </tr>
    </thead>
    <tbody>
      <tr><td colspan="5" class="empty">Lade…</td></tr>
    </tbody>
  </table>
  <div id="toast" class="toast"></div>
  <script>var MEDIA_TYPE = '{media_type}';</script>
  <script>{_AUDIT_PANEL_JS}</script>
</body>
</html>"""


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
    safe_mode: bool = False,
    enable_shuffle: bool = False,
    enable_rating_write: bool = False,
    enable_metadata_edit: bool = False,
    enable_recent: bool = True,
    enable_lyrics: bool = False,
    enable_playlists: bool = False,
    playlist_sync_interval_ms: int = 30000,
) -> str:
    """Build the complete HTML page for a media streaming UI.

    The page starts in folder-grid view.  Clicking a folder shows the
    track list with the player.  A back button returns to the grid.
    *media_element_tag* should be ``audio`` or ``video``.

    *player_bar_style* selects the bottom player layout:
    ``classic``  — single-row with inline range slider (default).
    ``waveform`` — two-row layout with audio waveform / video thumbnails.

    *enable_rating_write* adds clickable rating stars to the player bar
    and wires up the ``POST /api/<media>/rating`` endpoint (audio only).

    *enable_metadata_edit* adds a pencil edit button per track that opens
    an inline modal for editing title / artist / album tags (audio only).
    Wires up to ``POST /api/<media>/metadata/edit``.
    """
    css = render_base_css() + extra_css
    js = render_player_js(
        api_path=api_path,
        item_noun=item_noun,
        file_emoji=emoji,
        player_bar_style=player_bar_style,
        enable_offline=not safe_mode,
        enable_shuffle=enable_shuffle,
        enable_rating_write=enable_rating_write,
        enable_metadata_edit=enable_metadata_edit,
        enable_recent=enable_recent,
        enable_lyrics=enable_lyrics,
        enable_playlists=enable_playlists,
        playlist_sync_interval_ms=playlist_sync_interval_ms,
    )
    is_video = media_element_tag == "video"
    pwa_tags = "" if safe_mode else render_pwa_head_tags(theme_color=theme_color, standalone=not is_video)
    shuffle_btn_html = (
        f'<button class="ctrl-btn shuffle-btn" id="btn-shuffle" title="Shuffle">{SVG_SHUFFLE}</button>' if enable_shuffle else ""
    )
    sw_register = (
        ""
        if safe_mode
        else """
  <script>
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(function(){});
    }
  </script>"""
    )
    mode_controls_html = (
        '<span class="downloaded-pill is-offline" id="downloaded-pill">Safe Mode</span>'
        if safe_mode
        else '<span class="downloaded-pill" id="downloaded-pill" title="Offline-Downloads anzeigen">Downloaded (0)</span>'
    )
    offline_library_html = (
        ""
        if safe_mode
        else """
  <div class="offline-library" id="offline-library" hidden>
    <div class="offline-panel">
      <div class="offline-head">
        <div class="offline-title-wrap">
          <div class="offline-title">Offline-Bibliothek</div>
          <div class="offline-subtitle">Gespeicherte Downloads verwalten und direkt offline abspielen</div>
        </div>
        <button class="offline-close" id="offline-close" title="Schließen">Schließen</button>
      </div>
      <div class="offline-summary" id="offline-storage-summary">Noch keine Offline-Downloads.</div>
      <div class="offline-summary-detail" id="offline-storage-detail"></div>
      <div class="offline-toolbar">
        <select id="offline-sort">
          <option value="newest">Neueste zuerst</option>
          <option value="oldest">Älteste zuerst</option>
          <option value="title">Titel A–Z</option>
          <option value="size">Größte zuerst</option>
        </select>
        <button class="offline-action-btn" id="offline-persist-btn" type="button">Speicher persistent halten</button>
        <button class="offline-action-btn" id="offline-prune-btn" type="button">Alte Downloads aufräumen</button>
      </div>
      <ul class="offline-download-list" id="offline-download-list"></ul>
    </div>
  </div>"""
    )

    edit_modal_html = (
        ""
        if not enable_metadata_edit
        else """
  <!-- metadata edit modal -->
  <div class="edit-modal-backdrop" id="edit-modal-backdrop" hidden>
    <div class="edit-modal" role="dialog" aria-modal="true" aria-labelledby="edit-modal-heading">
      <div class="edit-modal-heading" id="edit-modal-heading">Metadaten bearbeiten</div>
      <div class="edit-field">
        <label for="edit-modal-title-input">Titel</label>
        <input id="edit-modal-title-input" type="text" autocomplete="off" />
      </div>
      <div class="edit-field">
        <label for="edit-modal-artist-input">Interpret</label>
        <input id="edit-modal-artist-input" type="text" autocomplete="off" />
      </div>
      <div class="edit-field">
        <label for="edit-modal-album-input">Album <span style="color:var(--sub);font-size:0.75rem">(optional)</span></label>
        <input id="edit-modal-album-input" type="text" autocomplete="off" />
      </div>
      <input type="hidden" id="edit-modal-path" />
      <input type="hidden" id="edit-modal-idx" />
      <div class="edit-modal-actions">
        <button class="edit-modal-cancel" id="edit-modal-cancel-btn">Abbrechen</button>
        <button class="edit-modal-save" id="edit-modal-save-btn">Speichern</button>
      </div>
    </div>
  </div>"""
    )

    playlist_pill_html = ""  # Pill entfernt — Playlists als Pseudo-Ordner unter Downloaded

    playlist_library_html = ""  # Library-Panel entfernt — Playlists als Pseudo-Ordner

    playlist_modal_html = (
        ""
        if not enable_playlists or safe_mode
        else """
  <div class="playlist-modal-backdrop" id="playlist-modal-backdrop" hidden>
    <div class="playlist-modal" role="dialog" aria-modal="true">
      <div class="playlist-modal-heading">Zur Playlist hinzuf\u00fcgen</div>
      <ul class="playlist-modal-list" id="playlist-modal-list"></ul>
      <div class="playlist-modal-new">
        <input id="playlist-modal-new-name" type="text" placeholder="Neue Playlist\u2026" autocomplete="off" />
        <button id="playlist-modal-new-btn">Erstellen</button>
      </div>
      <div class="playlist-modal-close"><button id="playlist-modal-close-btn">Abbrechen</button></div>
    </div>
  </div>"""
    )

    recent_section_html = (
        """  <div class="recent-section" id="recent-section" hidden>
    <div class="recent-section-title">Zuletzt gespielt</div>
    <div class="recent-scroll"></div>
  </div>"""
        if enable_recent
        else ""
    )

    lyrics_btn_html = (
        f'<button class="ctrl-btn lyrics-btn" id="btn-lyrics" title="Songtext anzeigen">{SVG_LYRICS}</button>' if enable_lyrics else ""
    )
    lyrics_panel_html = (
        """  <div class="lyrics-panel" id="lyrics-panel">
    <div class="lyrics-panel-head">
      <span class="lyrics-panel-title">Songtext</span>
      <button class="lyrics-close-btn" id="lyrics-close-btn" title="Schlie\u00dfen">\u00d7</button>
    </div>
    <div class="lyrics-body" id="lyrics-body">
      <div class="lyrics-loading">Lade Songtext\u2026</div>
    </div>
  </div>"""
        if enable_lyrics
        else ""
    )

    if player_bar_style == "waveform":
        player_bar_html = f"""
  <div class="player-bar waveform view-hidden">
    <div class="player-bar-top">
      <img class="track-thumb" id="player-thumb" src="" alt="" style="display:none">
      <div class="player-info">
        <div class="player-title"  id="player-title">No {item_noun} selected</div>
        <div class="player-artist" id="player-artist">&ndash;</div>
        <div class="player-rating" id="player-rating" hidden></div>
      </div>
      <div class="player-controls">
        <button class="ctrl-btn"            id="btn-prev" title="Previous">{SVG_PREV}</button>
        <button class="ctrl-btn play-pause" id="btn-play" title="Play / Pause">{SVG_PLAY}</button>
        <button class="ctrl-btn"            id="btn-next" title="Next">{SVG_NEXT}</button>
        <button class="ctrl-btn pip-btn"    id="btn-pip"  title="Bild-in-Bild" hidden>{SVG_PIP}</button>
        {lyrics_btn_html}
        {shuffle_btn_html}
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
    <img class="track-thumb" id="player-thumb" src="" alt="" style="display:none">
    <div class="player-info">
      <div class="player-title"  id="player-title">No {item_noun} selected</div>
      <div class="player-artist" id="player-artist">&ndash;</div>
      <div class="player-rating" id="player-rating" hidden></div>
    </div>
    <div class="player-controls">
      <button class="ctrl-btn"            id="btn-prev" title="Previous">{SVG_PREV}</button>
      <button class="ctrl-btn play-pause" id="btn-play" title="Play / Pause">{SVG_PLAY}</button>
      <button class="ctrl-btn"            id="btn-next" title="Next">{SVG_NEXT}</button>
      <button class="ctrl-btn pip-btn"    id="btn-pip"  title="Bild-in-Bild" hidden>{SVG_PIP}</button>
      {lyrics_btn_html}
      {shuffle_btn_html}
    </div>
    <div class="progress-wrap">
      <span class="time-label"     id="time-cur">0:00</span>
      <div class="progress-track" id="progress-track">
        <input type="range" id="progress-bar" min="0" step="0.1" value="0" />
        <div class="thumb-preview" id="thumb-preview">
          <canvas id="thumb-canvas" width="160" height="90"></canvas>
          <span class="thumb-time" id="thumb-time"></span>
        </div>
      </div>
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
    <button class="back-btn" id="back-btn" title="Back to folders">{SVG_BACK}</button>
    <button class="logo-home-btn" id="header-logo" title="Zurück zur Startseite">{emoji}</button>
    <span class="logo-title" id="header-title">{html.escape(title)}</span>
    <button class="play-all-btn" id="play-all-btn" title="Play all">{SVG_PLAY} Play All</button>
    <button class="view-toggle" id="view-toggle" title="Ansicht wechseln">{SVG_MENU}</button>
    <a class="audit-btn" href="/audit" title="Änderungsverlauf">{SVG_HISTORY}</a>
    {mode_controls_html}
    {playlist_pill_html}
    <span class="track-count" id="track-count"></span>
  </header>

  <!-- breadcrumb navigation -->
  <nav class="breadcrumb" id="breadcrumb"></nav>

  <!-- folder filter bar (visible on start screen, hidden when empty) -->
  <div class="folder-filter-bar" id="folder-filter-bar" hidden></div>

  <!-- recently played (root view only, hidden until JS populates) -->
  {recent_section_html}

  <!-- folder grid (default view) -->
  <div class="folder-grid" id="folder-grid"></div>

  <!-- filter bar (visible inside a folder) -->
  <div class="filter-bar view-hidden">
    <input id="search-input" type="search" placeholder="Search…" autocomplete="off" />
    <select id="sort-field">
      <option value="custom">Liste &#x21C5;</option>
      <option value="title">Title &#x21C5;</option>
      <option value="artist">Artist &#x21C5;</option>
      <option value="path">Path &#x21C5;</option>
      <option value="recent">Neueste &#x21C5;</option>
    </select>
    <button class="filter-chip" id="filter-rating" title="Nach Bewertung filtern"></button>
    <button class="filter-chip" id="filter-fav" title="Nur Favoriten anzeigen"></button>
    <button class="filter-chip" id="filter-genre" title="Nach Genre filtern"></button>
  </div>

  <!-- track list (visible inside a folder) -->
  <div class="track-list-wrap view-hidden" id="track-view">
    <ul class="track-list" id="track-list"></ul>
  </div>

{offline_library_html}
{edit_modal_html}
{lyrics_panel_html}
{playlist_library_html}
{playlist_modal_html}

  <{media_element_tag} id="player" preload="auto" playsinline{" controls autopictureinpicture" if media_element_tag == "video" else ""}></{media_element_tag}>
{player_bar_html}

  <script id="initial-data" type="application/json">{items_json}</script>
  <script>{js}</script>
{sw_register}
</body>
</html>
"""
