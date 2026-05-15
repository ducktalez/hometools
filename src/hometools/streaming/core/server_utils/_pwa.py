"""Progressive Web App (PWA) support — manifest, service worker, icons, head tags."""

from __future__ import annotations

import json


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
  
  // Streaming endpoints — only intercept if we have an offline download cached.
  // If not cached, bypass the SW entirely (no event.respondWith) so background-tab
  // throttling of SW fetch handlers cannot interrupt continuous video/audio playback.
  if (url.pathname.includes('/stream') || url.pathname.includes('/audio/') || url.pathname.includes('/video/')) {
    event.respondWith(
      caches.open(DOWNLOAD_CACHE).then(cache => cache.match(event.request)).then(cached => {
        if (cached) return cached;          // offline download → serve from cache
        return fetch(event.request);        // online → pass through; errors propagate naturally
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
