# Implementation Plan

## Backlog — Medium

### Streaming UI (Audio + Video)
- „Ähnliche Titel" vorschlagen (Artist/Genre/Album bzw. TMDB) (zurückstellen)

### Video-spezifisch
- Multi-Language-Linking — Phase 2: Fuzzy-Name-Matching (Phase 1b + manuelles YAML-Mapping via `language_group` sind abgeschlossen)
- Englische Serien: Metadaten + Titel in Englisch laden
- „Intro überspringen" (TMDB-Daten oder manuelle Markierung)
- Untertitelfiles + TMDB-Integration bei Umbenennungen
- `hometools_overrides.yaml` Erweiterung: weitere Override-Felder bei Bedarf (z.B. `tmdb_id`, `imdb_id`)

### Infrastruktur
- Tools-Code restrukturieren + umfassende Tests (Edge Cases, Dummy-Dateien)
- Optionales HTTPS
- iOS Background Video Playback → [plans/background_video_playback.md](plans/background_video_playback.md)
- **Agent-friendly codebase cleanup (follow-ups from the 2026-07-24 refactor):**
  - `server_utils/player_js/_library_tools.py` (~2300 lines) is still the
    largest fragment (duplicates + file-mover + delete/reveal) — split
    further once a safe internal boundary (no embedded Python
    interpolation) is identified.
  - `tests/test_streaming_player_ui.py` (~2100 lines) should be split into
    thematic files (e.g. `test_streaming_player_ui_playlists.py`,
    `..._smart_playlists.py`, `..._queue.py`, `..._catalog_cache.py`)
    mirroring the `player_js/` module split, so no single test file
    re-grows into the same "too big to read cheaply" problem.
  - **Done (2026-07-25):** JS syntax-safety net added —
    `tests/test_js_syntax.py` parses the concatenated
    `render_player_js()` output (4 representative audio/video ×
    classic/waveform configs) plus a brace-balance check for
    `render_base_css()`, via the `esprima` pure-Python JS parser (added as
    a `dev` extra in `pyproject.toml`/`requirements.txt`). No Node
    toolchain involved. See the "TypeScript/bundler switch" note in
    Design Discussions below for why a full TS/bundler migration was
    rejected instead.
  - `docs/CHANGELOG.md` and `docs/IMPLEMENTATION_PLAN.md` are still German;
    `docs/architecture.md` and all `.github/instructions/*.md` are already
    English. Decide whether to translate the remaining two docs for full
    project-wide consistency (not done in the 2026-07-24 pass to limit
    scope/risk).

## Backlog — Low / Experimental

- **DJ-Extension** — Mixing, Stems (Gesang/Instrumental/Beat), BPM-Analyse, Auto-DJ-Modus
- **„MTV"-Modus** — Musikvideos + visuelle Begleitung zu Musik
- **„Sleep Mode"** — nur Audio aus Serien, kein Bildschirm
- **Photo-Management-Server**
- **HTTP-Obscurification** — Port-Knock statt HTTPS für Privat-Server
- **Pro-Nutzer Ordnerstruktur** (N8N-Integration)
- **Lennyface-Board**

## Mobile Features (postponed)

- **Phase 3: Native iOS Apps** — Hybrid WebView Wrapper für Video + Audio → [plans/native_app_plan.md](plans/native_app_plan.md)

## Design Discussions

### TypeScript/bundler switch (2026-07-25)

**Status:** rejected for now, revisit if conditions below change.

**Kurzfassung (Why not now):** Server-Werte (z. B. `api_path`,
`enable_shuffle`, `language_groups_json`) werden aktuell direkt in den
JS-Text interpoliert (`render_player_js()`), nicht als separates JSON
injiziert — ein Bundler braucht aber statische Dateien zur Build-Zeit,
bevor diese Werte bekannt sind. Ein sauberer Umstieg wäre also kein reines
Tooling-Upgrade, sondern eine echte Architekturänderung. Zusätzlich: neue
Laufzeit-Dependency (Node), Build-Schritt vor jedem Testlauf/Server-Start
(widerspricht „sofort verfügbar" + „ein Startbefehl"), Docker-Image-Kosten,
Test-Anpassung (Feature-Parity-Tests grep'en aktuell direkt im JS-String),
~8900 Zeilen JS nachträglich typisieren. Stattdessen: `esprima`-basierter
Pytest-Check (`tests/test_js_syntax.py`, siehe oben) als leichte
Sicherheitsnetz-Alternative ohne Node-Runtime-Dependency.

**Revisit, wenn:** mehrere Personen parallel am JS arbeiten, echtes
Code-Splitting/Lazy-Loading nötig wird, oder komplexere Client-State-
Verwaltung ansteht, die von echten ES-Modulen profitiert.

### Smart-Playlist-Kaskaden (Phase 2)

**Status:** offen.

In Phase 1 (implementiert 2026-05-18) werden `in_playlist`-Regeln nur gegen *nicht-smarte* Playlists aufgelöst — Verweise auf andere Smart Playlists liefern garantiert `false` und werden im Index-Bau übersprungen.  Damit sind Zyklen ausgeschlossen, ohne dass eine Topologie-Analyse nötig ist.

**Phase-2-Vorschlag** (sobald praktisch benötigt):

1. Vor der Auswertung einen gerichteten Graphen `pl_id → set(referenzierte pl_ids)` aus allen `in_playlist`-Regeln aufbauen.
2. Per DFS auf Zyklen prüfen.  Bei Zyklus: betroffene Smart Playlists markieren, im UI mit einem Warn-Badge versehen und in der Auswertung wie leer behandeln.
3. Bei zyklenfreiem DAG topologisch sortieren und Smart Playlists in dieser Reihenfolge auswerten — vorgelagerte Ergebnisse stehen damit nachgelagerten als „virtuelle Playlist-Mitgliedschaft" zur Verfügung.
4. Tiefen-Limit (z.B. max. 5) als Safety-Net gegen Performance-Spitzen.
5. Cache der Auswertungsergebnisse pro Refresh-Zyklus (Memoization), damit eine Smart Playlist nicht mehrfach evaluiert wird, wenn sie von mehreren anderen referenziert wird.

**Trade-offs:**  Komplexität + UX-Kosten (Fehlermeldung „Zyklus erkannt") gegen die seltene Nützlichkeit (Power-User-Feature).  Bis ein User-Wunsch existiert, bleibt Phase 1 als bewusst einfache Lösung.

### `added_at`-Feld auf MediaItem (Phase 2)

**Status:** offen.

Smart Playlists nutzen aktuell `MediaItem.mtime` als Proxy für „Datum hinzugefügt".  Problem: Tag-Edits oder NAS-Resync setzen `mtime` zurück, sodass „Zuletzt hinzugefügt" Treffer „verlieren" kann.

**Vorschlag:** Neues Feld `first_seen_at: float` auf `MediaItem`, das beim ersten Build im Index-Cache vermerkt und nie überschrieben wird.  `catalog.py` (Audio + Video) liest den Wert aus dem vorigen Snapshot vor dem Persistieren des neuen.  Bei vollständigem Cache-Wipe fällt der Wert auf `mtime` zurück.  Smart-Playlist-Evaluator bevorzugt `first_seen_at`, fällt auf `mtime` zurück.

### Skip-Intro Phase 2: Audio-Fingerprinting (automatische Erkennung ohne Kapitel)

**Status:** offen.

Phase 1 (implementiert 2026-06-12) bestimmt Intro-Längen über drei Quellen: manuelle UI-Marker (serverseitiger JSON-Store), `hometools_overrides.yaml` (`intro_start`/`intro_end`) und ffprobe-Kapitelmarken („Intro"/„Opening"). Letztere greifen nur bei Releases, die benannte Kapitel mitliefern — das ist die Minderheit.

**Es gibt keine zuverlässige freie öffentliche API für Intro-Timestamps** (TMDB liefert sie nicht). Die robuste vollautomatische Technik ist **Cross-Episode-Audio-Fingerprinting** (vgl. Jellyfins *Intro Skipper*-Plugin): Pro Staffel wird das gemeinsame Audiosegment (= Titelmelodie) gesucht, das in mehreren Episoden identisch auftaucht, und daraus `[intro_start, intro_end]` abgeleitet.

**Vorschlag** (sobald praktisch benötigt): chromaprint/fpcalc (oder ffmpeg-basierte MFCC-Fingerprints) pro Episode berechnen, paarweise Episoden einer Staffel auf das längste gemeinsame Audio-Subsegment abgleichen, Ergebnis als `source="fingerprint"` in den bestehenden `intro_markers`-Store schreiben (gleiche Präzedenz wie `auto`). Rechenintensiv → Daemon-Thread + persistenter Fingerprint-Cache im Shadow-Cache, nur bei `season>0`-Items. Optionales `HOMETOOLS_INTRO_FINGERPRINT`-Flag (Default aus).

**Trade-offs:** hoher CPU-/IO-Aufwand (ganze Staffeln dekodieren) + zusätzliche optionale Dependency (chromaprint) gegen den Komfort, dass Intros ohne jegliche manuelle Pflege erkannt werden.

## Done

> Details → [`docs/CHANGELOG.md`](CHANGELOG.md)

- **Bugfix: Playlist-Erstellung "Fehler beim Erstellen" + "SVG_EDIT is not defined"** (2026-07-25) — Zwei zusammenhängende Bugs. **(1)** Zwei top-level `function showToast(...)`/`function formatBytes(...)` existierten gleichzeitig (je einmal in `_core.py` und `_library_tools.py`/`_track_render.py`), ein Überbleibsel der CSS/JS-Package-Split-Refaktorierung. JS-Funktionsdeklarationen im selben Scope überschreiben sich stillschweigend (letzte gewinnt) — kein `SyntaxError`, keine Warnung, nur leise falsches Verhalten (`showToast(msg, durationMs)`-Aufrufe verloren den zweiten Parameter). Fix: je genau eine kanonische Definition in `_core.py`, Duplikate entfernt. **(2, eigentliche Ursache des Erstellungs-Fehlers):** `_folder_browse.py` referenzierte beim Rendern der Smart-Playlist-Karte `SVG_EDIT` (ein reiner Python-Konstantenname aus `_svg.py`) statt der tatsächlich deklarierten JS-Variable `IC_EDIT` — führte zu `ReferenceError: SVG_EDIT is not defined` beim Rendern jeder Smart-Playlist-Karte. Erklärt **beide** gemeldeten Symptome: direkte Interaktion mit einer Smart Playlist warf den Fehler sofort; das Erstellen einer **normalen** Playlist rief danach `showFolderView()` zur Aktualisierung auf — falls bereits eine Smart Playlist existierte, warf deren Karten-Rendering denselben ReferenceError, landete im `.catch()` der normalen Playlist-Erstellung und zeigte fälschlich „Fehler beim Erstellen", obwohl die Playlist serverseitig bereits erfolgreich angelegt war. Fix: `SVG_EDIT` → `IC_EDIT`. Zusätzlich `response.ok`-Check in den Playlist-Erstellungs-Fetches (`_folder_browse.py`, `_smart_playlists.py`) ergänzt. **Warum die Tests das nicht gefangen haben:** Die bestehende `esprima.parseScript()`-Prüfung validiert nur Parsebarkeit — ein bloßer Bezeichner-Verweis auf eine nie deklarierte Variable ist syntaktisch valides JS und wird erst zur Laufzeit im Browser zum `ReferenceError`. Zwei neue Tests in `tests/test_js_syntax.py`: `test_no_duplicate_top_level_function_declarations` (AST-Walk, erkennt doppelte Top-Level-Funktionsnamen) und `test_no_leaked_python_svg_constant_names` (Regex-Scan, erkennt jeden bloßen `SVG_[A-Z_]+`-Bezeichner im generierten JS-Text — solche Namen dürfen nur Python-seitig als interpolierte String-Literale/`IC_*`-Zuweisungen auftreten, nie als literale Bezeichner-Referenz im JS).
- **UX-Batch: Hover-Play, Queue-Griff, Smart-Playlist-Edit, Tabellenansicht** (2026-07-24) — Hover-Play-Buttons auf Ordner-Cover und Track-Thumbnail (Desktop-Klick selektiert nur noch); `.queue-peek-handle` ersetzt Warteschlangen-Icon (Klick/Drag öffnet); Smart-Playlists nachträglich editierbar (`.playlist-folder-edit`) + Playlists umbenennbar (`PATCH /api/<media>/playlists`); Zirkelreferenz-Schutz in `validate_smart_rules(own_id=...)`; voller Rahmen auf grün/lila Playlist-Karten; Track-Action-Buttons per CSS-`order` rechtsbündig fixiert; Dateipfad-Modal durch Toast ersetzt; Titel/Interpret-Vertauschungs-Bug behoben (`refreshMetadata`-Staleness-Guard); neue Detail-/Tabellenansicht (Audio) mit editierbaren Titel/Interpret-Zellen im Tools-Modus.
- **Episode-Nummern + Video-Overlay Immersive Mode** (2026-07-23) — Feste Spaltenbreite für S01E12 in Serien-Listen (`.track-list--series`). Video-Overlay: Controls als `position:absolute`-Overlay mit Auto-Hide (3 s), Tap togglet.
- **Player-Redesign: Albumcover-Click, Reveal-Button, Queue-Pos, Bar-Actions-Fix** (2026-07-23) — Albumcover → `jumpToCurrentTrack()`. `track-reveal-btn` immer sichtbar. Queue-Button außerhalb `progress-wrap`. `_applyToolState()` refresht Player-Bar-Actions.
- **renderTracks Performance: Windowed Rendering + Render Guard + Debounce** (2026-07-22) — `_rgKey`-Guard, IntersectionObserver-Batches (100/Batch), `_ensureRenderedTo()`, Event-Delegation, Search-Debounce 150 ms.
- **Native-Client-Layer + Android-TV-Scaffold** (2026-06-15) — `GET /api/video/continue`, `hometools export-openapi`, `clients/androidtv/` Kotlin-Scaffold, OpenAPI-Contract.
- **Docker: Video-only Default** (2026-06-15) — `audio` hinter Compose-Profil, `AUDIO_LIBRARY_PATH` optional.
- **Remux/Faststart Temp-File-Leak** (2026-06-15) — `try/finally` + `cleanup_stale_remux_tmp()` + Sweep-Thread.
- **Skip-Intro (Netflix-Stil)** (2026-06-12) — Button im Intro-Fenster, 3 Quellen: UI-Marker / YAML-Override / ffprobe-Kapitel. Endpoints `GET/POST/DELETE /api/video/intro`. Felder `intro_start`/`intro_end` auf `MediaItem`.
- **Mobile-Player-Fixes + fehlende Folgen** (2026-06-08) — Tap/Drag-to-Seek, Verbindungsverlust-Bug, `sendBeacon` für Progress, PiP-Button versteckt auf Touch, `withMissingEpisodes()` pro Staffelpaar.
- **Aufgaben-Board `/board`** (2026-06-08) — `find_missing_episodes()`, `GET /api/video/board`, `SVG_BOARD`, CLI `hometools missing-episodes`.
- **Global Search: Ordner zuerst + Toast-Fix + Faststart-Prewarm** (2026-05-29) — Folder-Matches vor Track-Treffern. Toast auf Mobile unter Player-Bar, antippbar. Faststart-Prewarm im Thumbnail-Worker.
- **Docker-Deployment** (2026-05-24) — Multi-Stage-Image, `docker-compose.yml`, Healthchecks, `docs/docker.md`.
- **Cast/AirPlay-Button** (2026-05-24) — `#video-cast-btn`, Remote Playback API + AirPlay-Fallback, kein SDK.
- **Video-Server UI** (2026-05-24) — Tools-Row ohne Playlists, Eck-Sprachflagge `.folder-lang-corner`, `_isVideo`-Flag.
- **iOS Auto-PiP Fix** (2026-05-24) — PiP-Check vor Pause in `visibilitychange`.
- **asyncio-Log-Noise** (2026-05-24) — `asyncio`-Logger auf `ERROR`.
- **Smart Playlists** (2026-05-18) — `smart_playlists.py`, Operator-Registry, client-seitige Auswertung, Editor-Modal, `SVG_SMART_PLAYLIST`.
- **`hometools scan-library`** (2026-05-18) — `library_scan.py`, Checks `episode_naming`/`oversized_folder`/`untagged_language`.
- **`hometools validate-overrides`** (2026-05-17) — `overrides_validator.py`, 7 Checks, `--json`, `--fail-on-warning`.
- **Per-Episode `language`/`subtitle_language` Override** (2026-05-17) — `EpisodeOverride` + `FolderOverrides` erweitert.
- **Tools-Row-Redesign** (2026-05-17) — `.playlist-tools-row`, `__alltitles__`-Pseudo-Playlist, Reihenfolge Neue Playlist → Smart → Titel → Downloaded → reload. Katalog-Refresh-Karte statt Header-Button.
- **Waveform-Peak-Caching + Stereo** (2026-05-16) — 256 Segmente, `peaks_l`/`peaks_r`, L oben / R unten. Classic-Mode Progress-Bar 28 px.
- **Duplikat-Ghost-Zeilen** (2026-05-16) — `._deleted`-Marker, Ghost-Row `.track-item--deleted`.
- **URL-Routing erweitert** (2026-05-16) — `sort`, `fr`, `ff`, `fg`, `fh`, `vm`, `panel=tools` als Query-Parameter.
- **Rating-Filter-Chip + Bugfixes** (2026-05-15/16) — `(N/M)`-Format stabil. Audit-Button in Tools-Panel. SW-Routing-Bug (API-Check vor Streaming-Check). Audit-Log Exception-Safety.
- **File Mover** (2026-04-15) — `POST /api/audio/move-file`, `renderMoveWidget()`, MRU-Grid, `body.tool-show-file-mover`, `SVG_MOVE`.
- **Duplikat-Löschung (Soft-Delete)** (2026-04-15) — `POST /api/audio/delete-file` + `/video/delete-file`, `attention_delete_files()`.
- **Duplikat-Erkennung (Client-Side)** (2026-04-14) — `_dupeKey()`, `_buildDuplicateMap()`, `.dupe-badge`, Duplikat-Panel.
- **Audit-Panel SVG-Sterne + Rating-Undo-Fix** (2026-04-14)
- **Index-Cache Staleness + voller Katalog-Refresh** (2026-04-14)
- **Non-Blocking Video-Server-Start** (2026-04-14) — Language-Groups in Daemon-Thread.
- **Multi-Language Phase 1b** (2026-04-13) — `parse_subtitle_hint()`, `MediaItem.subtitle_language`, `compositeFlagHtml()`.
- **Sprach-Tags & Flaggen-Badges** (2026-04-11) — `language.py`, `MediaItem.language`, 10 Sprachen, `cleanFolderName()`.
- **Repeat-Modus** (2026-04-11) — Off / Alle / Einzeltitel, `enable_repeat`.
- **M4A Windows Xtra-Box Rating-Sync** (2026-04-11) — Xtra-Box + iTunes-Atom synchron schreiben.
- **POPM WMP-Standard-Mapping** (2026-04-10) — Step-Mapping 0/1/64/128/196/255.
- **Global Search (Root-View)** (2026-04-10) — `globalSearch()`, kein Backend-Endpoint.
- **Lazy Per-Folder Rating Refresh** (2026-04-10) — `POST /api/audio/refresh-ratings`, `IndexCache.patch_items()`.
- **Crossfade (Audio)** (2026-04-09) — `_xfadeAudio`, `HOMETOOLS_CROSSFADE_DURATION`.
- **Warteschlange (Queue)** (2026-04-02) — Queue-Panel, `.track-queue-btn`, `dequeueNext()`, DnD-Reorder.
- **Playlists** (2026-04-01 → 2026-04-02) — CRUD, Pseudo-Ordner-Karten, DnD-Reorder, Cross-Device-Sync, Optimistic UI.
- **Genre-Tags** (2026-03-31) — `MediaItem.genre`, Genre-Filter-Chip.
- **Audit-Log entkoppelt** (2026-03-31) — `.hometools-audit/`, `HOMETOOLS_AUDIT_DIR`.
- **Swipe-Gesten** (2026-03-31) — Touch-Swipe Zurück-Navigation.
- **Channel-Server Playlist-basiert** (2026-03-31) — `server_playlist.py` ersetzt HLS.
- **Channel-Mixer Concat Demuxer** (2026-03-25) — Pre-Transcode, ein ffmpeg-Prozess.
- Fernsehsender (Channel-Server, Port 8012, YAML-Programmplan)
- Schnellfilter-Chips (Bewertung, Favoriten, Genre)
- Tools-Panel, Inline-Ratings, Downloads-Toggle
- Lyrics-Panel (Audio), `make clean`, Thumbnail-Größen je Ansichtsmodus
- Ansichtsumschalter (list → grid → filenames)
- Metadaten-Bearbeitung Audio (`write_track_tags()`, Edit-Modal)
- Zuletzt gespielt / Continue Watching, Hörbuch-Erkennung
- Audit-Log (`audit_log.py`, `/audit`-Panel, Undo)
- Rating-Schreiben Audio (5 Sterne, POPM), Shuffle (Fisher-Yates + gewichtet)
- Folder-Favorites (`#`-Prefix), PWA Shortcuts, Offline-Downloads
- FastStart-Erkennung, SVG-Icons, Shadow-Cache, Remux/Transcode
- Serien-Episoden-Ordnung, YAML-Overrides, Cache-First API
