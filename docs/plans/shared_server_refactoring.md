# Shared Streaming Server — Refactoring-Plan

## Das Problem: Code-Duplikation

Aktuell:
- `audio/server.py` — ~200 Zeilen
- `video/server.py` — ~200 Zeilen
- ~80% identischer Code

**Beide haben:**
- Identische `create_app()` Struktur
- Identische Endpoints (`/health`, `/manifest.json`, `/sw.js`, `/icon-*.png`)
- Identische PWA-Logik
- Identische Error-Handling
- Identische Startup-Hooks

## Lösung: Generic Server Factory

```
src/hometools/streaming/
├── core/
│   ├── server_utils.py  (UI-Rendering)
│   └── server_factory.py ← NEU: Generic Server erstellen
│
├── audio/
│   ├── server.py        ← wird minimal (nur Audio-Config)
│   └── catalog.py
│
└── video/
    ├── server.py        ← wird minimal (nur Video-Config)
    └── catalog.py
```

## Implementierung

### Step 1: `core/server_factory.py` erstellen

```python
# Generic Factory für beide Server
class MediaStreamingApp:
    """Factory für Audio/Video-Streaming Server."""
    
    def __init__(
        self,
        media_type: Literal["audio", "video"],
        library_dir_getter,
        index_builder,
        resolver_func,
        title: str,
        emoji: str,
        theme_color: str,
        api_path: str,
        item_noun: str,
        extra_css: str,
    ):
        self.media_type = media_type
        self.library_dir_getter = library_dir_getter
        self.index_builder = index_builder
        self.resolver = resolver_func
        self.config = {
            "title": title,
            "emoji": emoji,
            "theme_color": theme_color,
            "api_path": api_path,
            "item_noun": item_noun,
            "extra_css": extra_css,
        }
    
    def create_app(self) -> FastAPI:
        """Erstelle das FastAPI app mit allen Endpoints."""
        app = FastAPI(title=f"hometools {self.media_type} streaming")
        
        # Generic Endpoints
        self._add_health_endpoint(app)
        self._add_pwa_endpoints(app)
        self._add_stream_endpoint(app)
        self._add_catalog_endpoint(app)
        
        # Media-spezifische Startup-Hook
        @app.on_event("startup")
        async def startup():
            await self._startup_hook()
        
        return app
```

### Step 2: Audio-Server wird minimal

```python
# audio/server.py
from hometools.streaming.core.server_factory import MediaStreamingApp
from hometools.streaming.audio.catalog import build_audio_index

def create_app(library_dir: Path | None = None) -> FastAPI:
    """Create audio streaming app."""
    app_factory = MediaStreamingApp(
        media_type="audio",
        library_dir_getter=get_audio_library_dir,
        index_builder=build_audio_index,
        resolver_func=resolve_audio_path,
        title="hometools audio",
        emoji="🎵",
        theme_color="#1db954",
        api_path="/api/audio/tracks",
        item_noun="track",
        extra_css=AUDIO_CSS_EXTRA,
    )
    return app_factory.create_app()
```

### Step 3: Video-Server wird minimal

```python
# video/server.py
from hometools.streaming.core.server_factory import MediaStreamingApp
from hometools.streaming.video.catalog import build_video_index

def create_app(library_dir: Path | None = None) -> FastAPI:
    """Create video streaming app."""
    app_factory = MediaStreamingApp(
        media_type="video",
        library_dir_getter=get_video_library_dir,
        index_builder=build_video_index,
        resolver_func=resolve_video_path,
        title="hometools video",
        emoji="🎬",
        theme_color="#bb86fc",
        api_path="/api/video/items",
        item_noun="video",
        extra_css=VIDEO_CSS_EXTRA,
    )
    return app_factory.create_app()
```

## Was dadurch passiert

| Aspekt | Vorher | Nachher |
|--------|--------|---------|
| Audio-Server Code | 200 LOC | 30 LOC |
| Video-Server Code | 200 LOC | 30 LOC |
| Gemeinsamer Code | verteilt | 300 LOC zentral |
| **Duplikation** | 80% | ~5% |
| Maintainability | Schwer | Einfach |

**Ersparnis:** 370 LOC Duplikation eliminiert

## Weitere Optimierungen

### 1. **Shared Endpoints Factory**

```python
# core/server_factory.py
class MediaStreamingApp:
    
    def _add_stream_endpoint(self, app):
        """Generic /stream endpoint für beide Server."""
        @app.get("/stream")
        def stream(path: str) -> FileResponse:
            try:
                file_path = self.resolver(path)
                media_type = mimetypes.guess_type(file_path.name)[0]
                return FileResponse(file_path, media_type=media_type)
            except (FileNotFoundError, ValueError) as exc:
                raise HTTPException(...) from exc
    
    def _add_pwa_endpoints(self, app):
        """Manifest, Service Worker, Icons — 100% identisch."""
        # Vollständig shared
        
    def _add_health_endpoint(self, app):
        """Health-Check — 100% identisch."""
        # Vollständig shared
```

### 2. **Catalog Query Abstraction**

Audio + Video haben unterschiedliche Query-Funktionen:
- Audio: `query_tracks()`
- Video: `query_items()`

**Solution:** Beide `core.catalog` als generische Operationen abstrahieren.

```python
# core/catalog.py — neue abstrakte Klasse
class MediaCatalog:
    """Base-Klasse für Audio/Video Kataloge."""
    
    def build_index(self, library_dir) -> list[MediaItem]:
        """Implementiert von Subklassen."""
        raise NotImplementedError
    
    def query(self, items, q=None, artist=None, sort_by="title"):
        """Generische Query-Logik."""
        # Shared zwischen Audio + Video
```

### 3. **WebView Swift Integration**

Die Native Apps können auch von dieser Abstraction profitieren:

```swift
// iOS App: Verbindet sich zum generischen Server
let serverURL = URL(string: "http://localhost:8001")
// Ob Audio oder Video — gleicher Code!
```

## Migration Plan (2-3 Stunden)

### Phase 1: Factory erstellen
- [ ] `core/server_factory.py` schreiben
- [ ] Generic Endpoints implementieren
- [ ] Tests schreiben

### Phase 2: Audio-Server migrieren
- [ ] `audio/server.py` reduzieren
- [ ] Testen
- [ ] Tests aktualisieren

### Phase 3: Video-Server migrieren
- [ ] `video/server.py` reduzieren
- [ ] Testen
- [ ] Tests aktualisieren

### Phase 4: Optional — Catalog abstrahieren
- [ ] `core/catalog.py` generische Base-Klasse
- [ ] Audio/Video erben davon

## Auswirkungen auf Native Apps

✅ **Positiv:**
- Gleicher Python-Backend für beide Apps
- Einfacher zu maintainen
- Weniger Boilerplate im Backend

❌ **Keine negativen Auswirkungen:**
- Swift-Code ändert sich nicht
- PWA-Code ändert sich nicht
- Nur Backend-Struktur wird optimiert

## Frage: Sollen wir das machen?

**Optionen:**

### Option A: Jetzt machen (3-4 Stunden)
- ✅ Backend wird sauberer
- ✅ Weniger Wartungsaufwand
- ✅ Basis für weitere Medien-Typen (Podcasts, eBooks?)
- ❌ Zeitaufwand jetzt

### Option B: Später machen (nach PWA-Feature)
- ✅ PWA-Feature zuerst fertig
- ✅ Weniger parallele Refactorings
- ❌ Duplikation bleibt länger

### Option C: Gar nicht machen
- ✅ Funktioniert auch so
- ❌ Duplikation bleibt
- ❌ Hard zu ändern wenn neue Medien-Typen kommen

**Meine Empfehlung:** Option B — Erst PWA Offline-Feature (Phase 1), dann diesen Refactoring vor der Native App.

