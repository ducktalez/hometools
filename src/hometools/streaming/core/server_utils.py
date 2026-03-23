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
.logo { font-size: 1.1rem; font-weight: 700; color: var(--accent); }
.track-count { font-size: 0.8rem; color: var(--sub); margin-left: auto; }
.offline-btn, .offline-close, .offline-action-btn {
  background: var(--surface2); color: var(--text); border: 1px solid #444;
  border-radius: 999px; cursor: pointer; padding: 0.4rem 0.8rem;
  font-size: 0.8rem; -webkit-tap-highlight-color: transparent;
}
.offline-btn:hover, .offline-close:hover, .offline-action-btn:hover {
  color: var(--accent); border-color: var(--accent);
}
.offline-status-pill {
  font-size: 0.72rem; color: var(--sub); border: 1px solid #3a3a3a;
  border-radius: 999px; padding: 0.28rem 0.55rem; margin-left: 0.45rem;
}
.offline-status-pill.is-offline { color: #ffcc00; border-color: #ffcc00; }
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
/* original-title toggle */
.orig-title-toggle {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 0.78rem; color: var(--sub); cursor: pointer; user-select: none;
  white-space: nowrap; flex-shrink: 0;
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
  padding: 0; line-height: 1;
}
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
  flex: 1 1 0; position: relative; min-width: 0;
}
.player-bar.classic input[type=range] {
  -webkit-appearance: none; appearance: none;
  width: 100%; height: 4px; background: #555;
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
) -> str:
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

  var allItems = Array.isArray(INITIAL) ? INITIAL : [];
  var currentPath = '';
  var playlistItems = [];
  var filteredItems = [];
  var currentIndex = -1;
  var inPlaylist = false;
  var initialCatalogRetryTimer = null;
  var initialCatalogRetryCount = 0;

  var player       = document.getElementById('player');
  var btnPlay      = document.getElementById('btn-play');
  var btnPrev      = document.getElementById('btn-prev');
  var btnNext      = document.getElementById('btn-next');
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
  var showOrigChk  = document.getElementById('show-original-titles');
  var folderGrid   = document.getElementById('folder-grid');
  var trackView    = document.getElementById('track-view');
  var filterBar    = document.querySelector('.filter-bar');
  var backBtn      = document.getElementById('back-btn');
  var headerTitle  = document.querySelector('.logo');
  var playerBar    = document.querySelector('.player-bar');
  var playAllBtn   = document.getElementById('play-all-btn');
  var offlineBtn   = document.getElementById('offline-btn');
  var offlineLibrary = document.getElementById('offline-library');
  var offlineClose = document.getElementById('offline-close');
  var offlineSort  = document.getElementById('offline-sort');
  var offlinePersistBtn = document.getElementById('offline-persist-btn');
  var offlinePruneBtn = document.getElementById('offline-prune-btn');
  var offlineDownloadList = document.getElementById('offline-download-list');
  var offlineStorageSummary = document.getElementById('offline-storage-summary');
  var offlineStorageDetail = document.getElementById('offline-storage-detail');
  var offlineStatusPill = document.getElementById('offline-status-pill');
  var originalTitle = headerTitle.textContent;
  var breadcrumb  = document.getElementById('breadcrumb');
  var viewToggle  = document.getElementById('view-toggle');
  var viewMode    = localStorage.getItem('ht-view-mode') || 'list';
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
  function scheduleBackgroundRefresh() {
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
    }, 2000);
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
        if (!folderMap[name]) folderMap[name] = 0;
        folderMap[name]++;
        if (!folderThumb[name] && it.thumbnail_url) folderThumb[name] = it.thumbnail_url;
        if (!folderThumbLg[name] && it.thumbnail_lg_url) folderThumbLg[name] = it.thumbnail_lg_url;
      } else {
        files.push(it);
      }
    });
    var folders = Object.keys(folderMap)
      .sort(function(a, b) { return a.localeCompare(b); })
      .map(function(n) { return { name: n, count: folderMap[n], thumbnail_url: folderThumb[n] || '', thumbnail_lg_url: folderThumbLg[n] || '' }; });
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
    if (currentIndex < 0) playerBar.classList.add('view-hidden');
    folderGrid.innerHTML = '<div class="empty-hint">' + escHtml(message || 'Loading library…') + '</div>';
    renderBreadcrumb();
    applyViewMode();
  }

  function showCatalogLoadError(detail) {
    folderGrid.classList.remove('view-hidden');
    trackView.classList.add('view-hidden');
    filterBar.classList.add('view-hidden');
    playAllBtn.style.display = 'none';
    if (currentIndex < 0) playerBar.classList.add('view-hidden');
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
    }, 1500);
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
  function applyViewMode() {
    if (viewMode === 'list') {
      folderGrid.classList.add('list-mode');
      viewToggle.innerHTML = IC_GRID;
      viewToggle.title = 'Zur Kachelansicht wechseln';
    } else {
      folderGrid.classList.remove('list-mode');
      viewToggle.innerHTML = IC_LIST;
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
      var thumbSrc = f.thumbnail_lg_url || f.thumbnail_url || FOLDER_PLACEHOLDER;
      html += '<div class="folder-card" data-folder="' + escHtml(f.name) + '">' +
        '<img class="folder-thumb" src="' + escHtml(thumbSrc) + '" alt="" loading="lazy">' +
        '<div class="folder-name">' + escHtml(f.name) + '</div>' +
        '<div class="folder-count">' + f.count + ' ' + noun + '</div>' +
        '<button class="folder-play-btn" title="Play all">' + IC_FOLDER_PLAY + '</button>' +
      '</div>';
    });
    c.files.forEach(function(it, i) {
      var thumbSrc = it.thumbnail_url || FILE_PLACEHOLDER;
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
      var sa = a.season || 0, sb = b.season || 0;
      var ea = a.episode || 0, eb = b.episode || 0;
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
    var noun = tracks.length !== 1 ? ITEM_NOUN + 's' : ITEM_NOUN;
    trackCount.textContent = tracks.length + ' ' + noun;
    if (!tracks.length) {
      trackList.innerHTML = '<li class="empty-hint">No matching items.</li>';
      return;
    }
    var showOrig = showOrigChk && showOrigChk.checked;
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
        '</li>';
    }).join('');
    document.querySelectorAll('.track-item:not(.missing-episode)').forEach(function(el) {
      el.addEventListener('click', function() { playTrack(Number(el.dataset.index)); });
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
    if (offlineStatusPill) {
      var net = navigator.onLine ? 'Online' : 'Offline';
      offlineStatusPill.textContent = net + (info.downloads.length ? ' · ' + info.downloads.length : '');
      offlineStatusPill.classList.toggle('is-offline', !navigator.onLine);
    }
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
      var sortBy = offlineSort ? offlineSort.value : 'newest';
      var sorted = sortDownloads(downloads, sortBy);
      renderOfflineDownloadList(sorted);
      return estimateOfflineStorage(sorted).then(function(info) {
        renderStorageSummary(info);
        return info;
      });
    });
  }

  function openOfflineLibrary() {
    if (!offlineLibrary) return;
    offlineLibrary.hidden = false;
    document.body.classList.add('modal-open');
    refreshOfflineLibrary();
  }

  function closeOfflineLibrary() {
    if (!offlineLibrary) return;
    offlineLibrary.hidden = true;
    document.body.classList.remove('modal-open');
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
      var match = findItemByStreamUrl(streamUrl);
      closeOfflineLibrary();
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

  if (offlineBtn) offlineBtn.addEventListener('click', openOfflineLibrary);
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
      playerThumb.src = t.thumbnail_url;
      playerThumb.style.display = '';
    } else {
      playerThumb.src = FILE_PLACEHOLDER;
      playerThumb.style.display = '';
    }
    btnPlay.innerHTML = IC_PAUSE;
    playerBar.classList.remove('view-hidden');
    markActive();
    updateMediaSession(t);
    refreshMetadata(t);

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

  btnPlay.addEventListener('click', togglePlay);
  btnPrev.addEventListener('click', function() {
    playTrack(currentIndex > 0 ? currentIndex - 1 : filteredItems.length - 1);
  });
  btnNext.addEventListener('click', function() {
    playTrack(currentIndex < filteredItems.length - 1 ? currentIndex + 1 : 0);
  });
  player.addEventListener('ended', function() {
    clearProgressFor(_progressRelPath);
    playTrack(currentIndex < filteredItems.length - 1 ? currentIndex + 1 : 0);
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
    viewMode = viewMode === 'list' ? 'grid' : 'list';
    localStorage.setItem('ht-view-mode', viewMode);
    applyViewMode();
  });
  searchInput.addEventListener('input', applyFilter);
  sortField.addEventListener('change', applyFilter);
  if (showOrigChk) {
    showOrigChk.checked = localStorage.getItem('ht-show-orig') === '1';
    showOrigChk.addEventListener('change', function() {
      localStorage.setItem('ht-show-orig', showOrigChk.checked ? '1' : '0');
      applyFilter();
    });
  }

  /* ── init ── */
  if (!OFFLINE_ENABLED) {
    if (offlineStatusPill) {
      offlineStatusPill.textContent = 'Safe Mode';
      offlineStatusPill.classList.add('is-offline');
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

  loadInitialCatalog().then(function() {
    handleDeepLink();
    loadFavorites();
  });
}());
"""
    )


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
    js = render_player_js(
        api_path=api_path,
        item_noun=item_noun,
        file_emoji=emoji,
        player_bar_style=player_bar_style,
        enable_offline=not safe_mode,
    )
    is_video = media_element_tag == "video"
    pwa_tags = "" if safe_mode else render_pwa_head_tags(theme_color=theme_color, standalone=not is_video)
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
        '<span class="offline-status-pill is-offline" id="offline-status-pill">Safe Mode</span>'
        if safe_mode
        else (
            '<button class="offline-btn" id="offline-btn" title="Offline-Bibliothek öffnen">Offline</button>'
            '<span class="offline-status-pill" id="offline-status-pill">Online</span>'
        )
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

    if player_bar_style == "waveform":
        player_bar_html = f"""
  <div class="player-bar waveform view-hidden">
    <div class="player-bar-top">
      <img class="track-thumb" id="player-thumb" src="" alt="" style="display:none">
      <div class="player-info">
        <div class="player-title"  id="player-title">No {item_noun} selected</div>
        <div class="player-artist" id="player-artist">&ndash;</div>
      </div>
      <div class="player-controls">
        <button class="ctrl-btn"            id="btn-prev" title="Previous">{SVG_PREV}</button>
        <button class="ctrl-btn play-pause" id="btn-play" title="Play / Pause">{SVG_PLAY}</button>
        <button class="ctrl-btn"            id="btn-next" title="Next">{SVG_NEXT}</button>
        <button class="ctrl-btn pip-btn"    id="btn-pip"  title="Bild-in-Bild" hidden>{SVG_PIP}</button>
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
    </div>
    <div class="player-controls">
      <button class="ctrl-btn"            id="btn-prev" title="Previous">{SVG_PREV}</button>
      <button class="ctrl-btn play-pause" id="btn-play" title="Play / Pause">{SVG_PLAY}</button>
      <button class="ctrl-btn"            id="btn-next" title="Next">{SVG_NEXT}</button>
      <button class="ctrl-btn pip-btn"    id="btn-pip"  title="Bild-in-Bild" hidden>{SVG_PIP}</button>
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
    <span class="logo">{emoji} {html.escape(title)}</span>
    <button class="play-all-btn" id="play-all-btn" title="Play all">{SVG_PLAY} Play All</button>
    <button class="view-toggle" id="view-toggle" title="Ansicht wechseln">{SVG_MENU}</button>
    {mode_controls_html}
    <span class="track-count" id="track-count"></span>
  </header>

  <!-- breadcrumb navigation -->
  <nav class="breadcrumb" id="breadcrumb"></nav>

  <!-- folder grid (default view) -->
  <div class="folder-grid" id="folder-grid"></div>

  <!-- filter bar (visible inside a folder) -->
  <div class="filter-bar view-hidden">
    <input id="search-input" type="search" placeholder="Search…" autocomplete="off" />
    <label class="orig-title-toggle" title="Originale Dateinamen anzeigen"><input type="checkbox" id="show-original-titles" /> Original</label>
    <select id="sort-field">
      <option value="title">Title &#x21C5;</option>
      <option value="artist">Artist &#x21C5;</option>
      <option value="path">Path &#x21C5;</option>
      <option value="recent">Neueste &#x21C5;</option>
    </select>
  </div>

  <!-- track list (visible inside a folder) -->
  <div class="track-list-wrap view-hidden" id="track-view">
    <ul class="track-list" id="track-list"></ul>
  </div>

{offline_library_html}

  <{media_element_tag} id="player" preload="auto" playsinline{" controls autopictureinpicture" if media_element_tag == "video" else ""}></{media_element_tag}>
{player_bar_html}

  <script id="initial-data" type="application/json">{items_json}</script>
  <script>{js}</script>
{sw_register}
</body>
</html>
"""
