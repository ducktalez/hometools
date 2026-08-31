# Implementation Plan

Backlog + open design discussions only. Completed items removed, history
in `git log`.

## Backlog — Medium

### Vite/TypeScript migration

Goal: replace `_player_js.py`/`player_js/*.py`/`_css.py`/`css/*.py` (~8900
lines JS/CSS as Python strings) module-by-module with real `.ts`/`.css`,
built via Vite, served as FastAPI static assets. Backend untouched.

**Rule:** port one pure, dependency-free function/module at a time (proven:
`pathUtils.ts`, `dupeUtils.ts`, `breadcrumb.ts`, `smartPlaylist.ts`,
`recentMoveTargets.ts`, `catalogCache.ts`, `offlineDownloads.ts`,
`langDetect.ts`, `episodeGaps.ts`). Never bulk-port via `eval()` — tried
once, broke prod (see git log 2026-08-06). `legacy.ts` sits unused in tree
as raw material — don't re-enable as-is.

Blocker for stateful fragments (`_core.py`, `_library_tools.py`, ...):
cross-fragment coupling — see "Player-JS-Modulkopplung" below.

### Streaming UI
- „Ähnliche Titel" vorschlagen (Artist/Genre/Album/TMDB) — zurückgestellt

### Video
- Multi-Language-Linking Phase 2: Fuzzy-Name-Matching
- Englische Serien: Metadaten/Titel in Englisch
- Untertitelfiles + TMDB-Integration bei Umbenennungen
- `hometools_overrides.yaml`: weitere Felder bei Bedarf (`tmdb_id`, `imdb_id`)

### Infrastruktur
- Optionales HTTPS
- iOS Background Video Playback → [plans/background_video_playback.md](plans/background_video_playback.md)
- `_library_tools.py` (~2300 Zeilen) weiter splitten, sobald sichere Grenze gefunden
- `test_streaming_player_ui.py` (~2100 Zeilen) thematisch splitten

## Backlog — Low / Experimental

- DJ-Extension (Mixing, Stems, Auto-DJ)
- „MTV"-Modus, „Sleep Mode", Photo-Management-Server
- HTTP-Obscurification (Port-Knock)
- Pro-Nutzer Ordnerstruktur (N8N)
- Lennyface-Board

## Mobile Features (postponed)

- Native iOS Apps (WebView-Wrapper) → [plans/native_app_plan.md](plans/native_app_plan.md)

## Design Discussions

### UI-Template-Vereinheitlichung: Header, List-Toolbar, List-Item

**Status:** Phase 1 (Header) fertig. Phase 2 (Toolbar) teilweise. Phase 3+ offen.
Offline/„Downloaded"-View (`openOfflineLibrary()`, `_track_render.py`) ging
bisher über `showPlaylist()` + manuellen `headerTitle.textContent`-Patch
danach (gleicher Drift-Bug wie das alte `playUserPlaylist()`) — jetzt direkt
über `_enterTrackListView({title:'Downloaded', ...})`, wie Favoriten/Titel/
Duplikate. Spart nebenbei einen sinnlosen Folder-Order-Netzwerkaufruf für
den virtuellen `__offline__`-Pfad.

Geklärt: kein Home-Emoji; Filtern (Rating+Favorit+Genre) ein Popover-Button;
Video-3-Wege-Toggle vorbereitet, keine Priorität.

Offen:
1. Sortieren als eigene Komponente (aktuell ad hoc pro Aufrufer)
2. Listen-Item-Templates (Folder/Playlist/Smart-Playlist/Duplicate-Card, Track-Row rows|table)
3. Track-Count-als-Refresh-Button
4. Video-Parity-Tests
5. `_applyTrackViewMode`s Tabellen-Header-Inject-Hack aufräumen
   (totes `folder-filter-bar`-Div bereits entfernt, 2026-08-08)

### Player-JS-Modulkopplung

**Status:** offen, blockiert Modul-für-Modul-TS-Port.

Jedes `player_js/*.py`-Fragment liest/schreibt Bezeichner aus anderen
Fragmenten (`filteredItems`, `allItems`, `showFolderView`, ...) — verlässt
sich auf gemeinsame nicht-strikte Konkatenation, kein echtes Modul.

Zwei Bridging-Muster etabliert:
- **`window`-Bridge** (read-only/einmalig gesetzte Globals wie `originalTitle`) — Contract in `legacy-globals.d.ts`
- **Explizite Parameter** (häufig mutierte Globals wie `allItems`) — siehe `smartPlaylist.ts`: nimmt Daten als Parameter statt `window`-Read, Call-Sites reichen lokale Variablen durch

Vor jedem Port eines gekoppelten Fragments: welches Muster passt an der
jeweiligen Grenze besser?

### Smart-Playlist-Kaskaden (Phase 2)

**Status:** offen. Aktuell (Phase 1) liefern `in_playlist`-Regeln auf andere
Smart Playlists immer `false` (keine Zyklen möglich, keine Topologie nötig).

Bei Bedarf: Graph `pl_id → referenzierte pl_ids`, DFS-Zyklencheck, topologisch
sortiert auswerten, Tiefenlimit ~5, Memoization pro Refresh-Zyklus.
Trade-off: Komplexität/UX (Zyklus-Fehlermeldung) vs. Power-User-Nutzen.

### `added_at`-Feld auf MediaItem (Phase 2)

**Status:** offen. Smart Playlists nutzen `mtime` als Proxy für „hinzugefügt"
— Tag-Edits/Resync setzen das zurück.

Vorschlag: `first_seen_at: float`, beim ersten Index-Build gesetzt, nie
überschrieben; `catalog.py` übernimmt Wert aus vorigem Snapshot. Fallback
auf `mtime` bei Cache-Wipe.

### Skip-Intro Phase 2: Audio-Fingerprinting

**Status:** offen. Phase 1: manuelle Marker, YAML-Overrides, ffprobe-Kapitel
(nur Minderheit der Releases hat benannte Kapitel).

Keine freie API für Intro-Timestamps. Robuste Technik: Cross-Episode-Audio-
Fingerprinting (chromaprint/fpcalc, vgl. Jellyfin Intro Skipper) — pro
Staffel gemeinsames Audiosegment über Episoden suchen. Rechenintensiv →
Daemon-Thread, persistenter Cache, optionales `HOMETOOLS_INTRO_FINGERPRINT`-Flag.
Trade-off: hoher CPU/IO-Aufwand vs. Komfort ganz ohne manuelle Pflege.
