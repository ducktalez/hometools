# Implementation Plan

Backlog + open design discussions only. Completed items removed, history
in `git log`.

## Backlog — Medium

### Web UI: app.ts typisieren

`app.ts` nutzt noch viele `any` + late-bound `var`-Wrapper. Schrittweise typisieren, Wrapper durch direkte Wiring-Deps ersetzen. Vite 6+/vitest 4+ Update wegen npm-audit-Hinweisen (siehe `webui/README.md`).

### Streaming UI
- „Ähnliche Titel" vorschlagen (Artist/Genre/Album/TMDB) — zurückgestellt

### Video
- Multi-Language-Linking Phase 2: Fuzzy-Name-Matching
- Englische Serien: Metadaten/Titel in Englisch
- Untertitelfiles + TMDB-Integration bei Umbenennungen
- `hometools_overrides.yaml`: weitere Felder bei Bedarf (`tmdb_id`, `imdb_id`)

### Infrastruktur
- webui Toolchain-Major-Upgrade (vite 5→6+/7, vitest 2→4+): schließt
  `npm audit`-Advisories (esbuild Dev-Server, @vitest/mocker). Aktuell nicht
  ausnutzbar (nur `vite build`/`vitest run`, keine Mocks) — siehe
  `webui/README.md`. Braucht Node-Baseline-Check fürs Docker-Image.
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

**Status:** Phase 1 (Header) fertig — `_applyHeaderState()` ist der einzige
Schreiber von Header-Controls; die zwei Entry-Points
(`_enterTrackListView` / `_enterFolderGridView`, `app.ts`)
delegieren dorthin. Regel: **jedes Control existiert in jedem View**, nur
Inhalt/enabled-Zustand unterscheidet sich — kein Control darf in einem View
fehlen. Die alte Regel „globale Suche nur in Ordneransicht" ist damit weg
(Suche fehlte sichtbar in Playlists). `globalSearch()`,
`showLoadingState()`, `showCatalogLoadError()` delegieren ebenfalls;
Error-View nutzt disabled-Klasse statt `style.display='none'`;
recent-section-Hide zentral. `IC_LIST`/`SVG_LIST` mit Bullets, damit der
View-Toggle nicht mehr wie ein Hamburger-Menü aussieht.
Phase 2 (Toolbar) teilweise. Phase 3+ offen.
Offline/„Downloaded"-View (`openOfflineLibrary()`) ging
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
