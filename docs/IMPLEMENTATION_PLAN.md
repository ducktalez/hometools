# Implementation Plan

Backlog + open design discussions only. Completed items removed, history
in `git log`.

## Backlog — Medium

### Vite/TypeScript migration

Goal: replace `_player_js.py`/`player_js/*.py` (~6900 lines JS as Python
strings) module-by-module with real `.ts`, built via Vite, served as
FastAPI static assets. Backend untouched. CSS side already fully migrated
(see below).

**Rule:** port one pure, dependency-free function/module at a time (proven:
`pathUtils.ts`, `dupeUtils.ts` (+ `buildDuplicateIndex`), `breadcrumb.ts`, `smartPlaylist.ts`,
`recentMoveTargets.ts`, `catalogCache.ts`, `offlineDownloads.ts`,
`langDetect.ts` (inkl. Flag-Badge-HTML), `episodeGaps.ts`, `catalogQuery.ts`, `clickGuard.ts`,
`toast.ts`, `folderCache.ts`, `shuffle.ts`, `offlineUrl.ts`,
`catalogQuery.ts::sortTracks`, `search.ts`, `filterChain.ts`, `intro.ts`, `queue.ts`, `folderContents.ts`, `offlineDb.ts`, `progress.ts`, `playerControls.ts`, `customOrder.ts`, `filterPopover.ts` (+ Chip-Views), `offlineDownloads.ts::storageSummaryView`, `catalogQuery.ts::findItemByStreamUrl`). Never bulk-port via `eval()` —
tried once, broke prod (see git log 2026-08-06). `legacy.ts` sits unused in
tree as raw material — don't re-enable as-is.

Third pattern (since `clickGuard.ts`): if a stateful block's state is
*private* to it (no other fragment reads it), move state + listeners along
with the function — no bridge, no param. Check that first, it beats both
other patterns.

**CSS-Teil fertig** — alle Fragmente aus `css/*.py` nach
`webui/src/styles/*.css` portiert (`metaPill`, `root`, `toolsPanel`,
`modals`, `playlistCards`, `playerBar`, `tableView`, `trackList`,
`videoOverlay`). `_css.py`/`css/` komplett entfernt; `render_base_css()`
bleibt als No-Op (`""`) nur für `_html.py`s Signatur erhalten.

**Regel seit vitest-Setup:** jeder Port bringt einen Verhaltenstest in
`webui/test/*.test.ts` mit (läuft auch via pytest `test_webui_unit.py`).
Ältere Ports ohne Test nachziehen, wenn angefasst (`pathUtils.ts`,
`dupeUtils.ts` (+ `buildDuplicateIndex`), `breadcrumb.ts`, `smartPlaylist.ts`, `catalogCache.ts`,
`offlineDownloads.ts`, `langDetect.ts`, `episodeGaps.ts`, `folderCache.ts`,
`offlineUrl.ts`, `clickGuard.ts`, `toast.ts`).

Blocker for stateful fragments (`_core.py`, `_library_tools.py`, ...):
cross-fragment coupling — **gelöst** via `htState`-Bridge, siehe
"Player-JS-Modulkopplung" below. Verbleibende Arbeit ist Fließband:
Funktion für Funktion über eines der vier Muster portieren.

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
(`_enterTrackListView` / `_enterFolderGridView`, `player_js/_folder_browse.py`)
delegieren dorthin. Regel: **jedes Control existiert in jedem View**, nur
Inhalt/enabled-Zustand unterscheidet sich — kein Control darf in einem View
fehlen. Die alte Regel „globale Suche nur in Ordneransicht" ist damit weg
(Suche fehlte sichtbar in Playlists). `globalSearch()`,
`showLoadingState()`, `showCatalogLoadError()` delegieren ebenfalls;
Error-View nutzt disabled-Klasse statt `style.display='none'`;
recent-section-Hide zentral. `IC_LIST`/`SVG_LIST` mit Bullets, damit der
View-Toggle nicht mehr wie ein Hamburger-Menü aussieht.
Phase 2 (Toolbar) teilweise. Phase 3+ offen.
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

**Status:** Blocker gelöst durch `htState`-Bridge — Port-Reihenfolge bleibt
Aufwandsfrage, keine Architekturfrage mehr.

Jedes `player_js/*.py`-Fragment liest/schreibt Bezeichner aus anderen
Fragmenten (`filteredItems`, `allItems`, `showFolderView`, ...) — verlässt
sich auf gemeinsame nicht-strikte Konkatenation, kein echtes Modul.

Vier Bridging-Muster etabliert (in dieser Reihenfolge prüfen):
1. **State mitnehmen** (Zustand nur fragment-intern, z.B. `_mdX`/`_allFoldersCache`) — `clickGuard.ts`/`folderCache.ts`: State wandert mit, kein Bridge
2. **Explizite Parameter** (nur *gelesene* mutierte Globals) — `smartPlaylist.ts`: Call-Sites reichen lokale Variablen durch
3. **`window`-Bridge** (read-only/einmalig gesetzte Globals wie `originalTitle`) — Contract in `legacy-globals.d.ts`
4. **`htState`-Bridge** (geteilte Globals, die der Port *schreiben* muss) — `window.htState` in `_core.py`: Getter/Setter-Closures über den IIFE-vars, TS-Writes reassignen das Original, Legacy-Mutationsstellen bleiben unangetastet. Typ-Contract `stateBridge.ts::HtState`, erster Consumer `shuffle.ts`. Pro Port nur benötigte Properties ergänzen (Getter UND Setter, Test erzwingt Paare).

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
