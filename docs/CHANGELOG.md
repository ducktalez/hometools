# Changelog

Detaillierte Beschreibungen aller implementierten Features. Kurzliste in `IMPLEMENTATION_PLAN.md`.

---

## 2026-07

- **Playlist-Karten: Cover als Abspiel-Button + Drei-Punkte-Menü:** Der Abspiel-Button liegt jetzt als zentrierter, halbtransparenter Kreis-Overlay direkt über dem Cover (`.playlist-cover-play-btn` in `.playlist-thumb-wrap`, erscheint beim Hover — gleiches Muster wie `.track-play-btn`). Umbenennen, Regeln bearbeiten, Aktualisieren und Löschen sind nicht mehr als einzelne immer sichtbare Buttons auf der Karte, sondern ausschließlich über ein neues Drei-Punkte-Menü oben rechts erreichbar (`.playlist-folder-kebab` → `_openPlaylistCtxMenu()`). Der bisherige separate Aktualisieren-Button bei intelligenten Playlists (`.playlist-folder-refresh`) entfällt komplett. Die Menü-Logik ist ein neuer generischer, überall wiederverwendbarer Baustein `_openCtxMenu(btn, items)` (`.ht-ctx-menu`/`.ht-ctx-item`, vormals `.track-ctx-menu`/`.track-ctx-item`) — Track-Zeilen-Kebab und Player-Bar-Kebab nutzen jetzt denselben Code. Dadurch sitzen alle Drei-Punkte-Menüs im UI konsistent rechtsbündig an derselben Stelle.
- **UX-Batch: Hover-Play, Queue-Griff, Smart-Playlist-Edit, Tabellenansicht** — Umsetzung der Feedback-Liste vom 2026-07-24:
  - **Hover-Play-Buttons:** `.folder-play-btn` sitzt jetzt links über dem Cover (statt unten rechts) und erscheint beim Hover; Klick spielt die Liste sofort ab (Serien setzen bei der zuletzt gesehenen Episode fort, via `_loadLastPlayedLocal()` in `playAllIn()`). Neuer `.track-play-btn` überlagert das Track-Thumbnail links — Klick spielt sofort. Der normale Zeilenklick markiert auf Hover-fähigen Geräten nur noch (`_selectTrackRow()`, `.row-selected`-Klasse); auf Touch-Geräten (kein Hover) spielt ein Tap weiterhin direkt.
  - **Queue-Griff statt Warteschlangen-Symbol:** `#btn-queue` entfernt; neuer `.queue-peek-handle` (schmaler Griff über der Player-Bar) öffnet/schließt die Queue per Klick oder Drag-nach-oben (`_initQueuePeekHandle()`), nur sichtbar wenn die Queue Einträge hat (`.has-items`). Der bestehende interne Resize-Griff (`.queue-drag-handle`) bleibt für die Höhenanpassung im geöffneten Zustand erhalten.
  - **Smart-Playlists nachträglich bearbeitbar + Umbenennen:** Stift-Button (`.playlist-folder-edit`) auf jeder Smart-Playlist-Karte öffnet den bestehenden Regel-Editor erneut (`openSmartPlaylistEditor()`). Neuer Umbenennen-Button (`.playlist-folder-rename`) auf allen Playlist-Karten ruft `renameUserPlaylist()` → `PATCH /api/<media>/playlists` (neuer Endpoint, nutzt `rename_playlist()`).
  - **Zirkelreferenz-Schutz:** `validate_smart_rules(smart, *, own_id=None)` lehnt `in_playlist`-Regeln ab, die auf die eigene Playlist-ID verweisen. Beide Server übergeben `own_id=playlist_id` beim Update. Client blendet die eigene Playlist zusätzlich aus der Auswahlliste aus und filtert Selbstverweise defensiv vor dem Speichern.
  - **Grün/lila Rahmen komplett:** `.playlist-folder-card` (Standard: Akzentfarbe) und `.smart-playlist-card` (lila `#a259e6`) haben jetzt einen vollständigen `border: 1px solid` auf allen vier Seiten statt eines unvollständigen Rahmens.
  - **Drei-Punkte-Menü rechtsbündig:** CSS-`order`-Werte auf allen Track-Action-Buttons (`.track-dl-btn` … `.track-kebab-btn`, `.track-reveal-btn`) fixieren die visuelle Reihenfolge unabhängig davon, welche Tools-Buttons gerade sichtbar sind — Kebab und „Im Explorer anzeigen" sind immer ganz rechts.
  - **Dateipfad-Modal entfernt:** `_showPathModal()` (Popup mit „Explorer geöffnet") entfernt; `revealInExplorer()` zeigt stattdessen einen kurzen Toast.
  - **Titel/Interpret-Vertauschung beim Neuladen behoben:** `refreshMetadata()` verwirft veraltete Server-Antworten, wenn der Track zwischenzeitlich gewechselt hat (`_progressRelPath !== _requestedFor`-Guard).
  - **Tools-Modus: Move-Quick-Grid nicht mehr umbrechend:** `.move-quick-grid` nutzt `flex-wrap: nowrap` + horizontales Scrollen (`overflow-x: auto`) statt eines 2-Spalten-Grids, das bei aktivem File-Mover die Zeilenhöhe vergrößerte.
  - **Neue Detail-/Tabellenansicht (Audio):** Zusätzlicher Ansichtsmodus, umschaltbar über den View-Toggle-Button während ein Ordner/eine Playlist offen ist (`_toggleTrackViewMode()`, persistiert in `localStorage` als `ht-track-view-mode`). Zeigt Titel/Interpret/Dauer/Genre/Bewertung als eigene Spalten (`#track-table-header`, CSS-Grid `.track-list.table-mode`). Im Tools-Modus werden Titel und Interpret direkt editierbar (`contenteditable`, `_saveInlineTableEdit()` → `POST /api/audio/metadata/edit`). Video-Server behält die klassische Zeilenansicht (Toggle ist dort gesperrt).
  - `HOMETOOLS_RECENT_VIDEO_LIMIT`-Default auf 20 angehoben (vorher 3) — zeigt praktisch alle Serien der letzten 14 Tage statt nur der letzten 3 Episoden.
  - Tests: `TestTrackDetailTableView` (7 neue Tests) in `test_streaming_player_ui.py`; `PATCH /api/*/playlists`-Endpoints; `test_config.py` an neuen Default angepasst.

- **Episode-Nummern: einheitliche Spaltenbreite** — `renderTracks()` setzt `.track-list--series` wenn `season > 0`; CSS `width: 4rem` auf `.track-num` für diese Listen → kein Layout-Shift bei gemischten Formaten (z. B. DuckTales S1).

- **Video-Overlay Immersive Mode** — Header + Player-Bar sind `position: absolute` und überlagern das Video (statt Flex-Blöcke). Video-Wrap `inset: 0` → voller Screen. Gradient-Scrims. `controls-hidden`-Klasse fade-out, Auto-Hide nach 3 s Play, Tap auf Video toggled. Landscape-Gewinn ~136 px. Neue Funktionen: `_showVidControls`, `_hideVidControls`, `_toggleVidControls`.

- **Skip-Intro-Button CSS** — fehlende Regel `.video-skip-intro-btn` nachgetragen.

- **Player-Redesign** — Albumcover-Click → `jumpToCurrentTrack()`. `track-reveal-btn` immer sichtbar. Queue-Button in Classic-Bar als direktes Flex-Kind außerhalb `progress-wrap`. `_applyToolState()` ruft `updatePlayerBarActions()` am Ende auf.

- **renderTracks Performance** — Render Guard (`_rgKey`), Windowed Rendering (IntersectionObserver, 100 Items/Batch), `_ensureRenderedTo()`, Event-Delegation (`_wireTrackListDelegation()`), Search-Debounce 150 ms.

---

## 2026-06

- **Native-Client-Layer + Android-TV-Scaffold** — `get_continue_watching()` + `GET /api/video/continue`, `hometools export-openapi`, `clients/androidtv/` Kotlin-Scaffold, OpenAPI-Contract.

- **Docker: Video-only Default** — `audio`-Service hinter Compose-Profil `audio`, `AUDIO_LIBRARY_PATH` optional.

- **Remux/Faststart Temp-File-Leak** — `try/finally` in `ensure_remux_cache()` + `ensure_faststart_cache()`, `cleanup_stale_remux_tmp()`, Sweep-Thread beim Start.

- **Skip-Intro (Netflix-Stil)** — Button nur im Intro-Fenster `[intro_start, intro_end]`. Quellen (Präzedenz): manuelle UI-Marker (JSON-Store), YAML-Overrides, ffprobe-Kapitel. Endpoints `GET/POST/DELETE /api/video/intro`. Felder `intro_start`/`intro_end` auf `MediaItem`. Config `HOMETOOLS_SKIP_INTRO`, `HOMETOOLS_INTRO_AUTODETECT`.

- **Mobile-Player-Fixes + fehlende Folgen** — Tap/Drag-to-Seek (`initTrackSeek()`), Verbindungsverlust springt nicht mehr auf S01E01 (`reachedEnd`-Guard), `saveProgressNow()` via `sendBeacon`, PiP-Button auf Touch-Geräten versteckt, `withMissingEpisodes()` erkennt Lücken pro Staffelpaar.

- **Aufgaben-Board `/board`** — `find_missing_episodes()` in `episode_gaps.py`, `GET /api/video/board`, Dark-Theme-Seite, CLI `hometools missing-episodes`, `SVG_BOARD`.

- **Global Search Ordner-Treffer zuerst** — Folder-Match-Liste in `globalSearch()`, `.search-folder-item` vor Track-Treffern, `navigateToSearchFolder()`.

- **Indexing-Toast antippbar** — Mobile unterhalb Player-Bar verschoben, `_indexToastDismissed`-Flag, Click-Handler.

- **Faststart-Prewarm im Thumbnail-Worker** — `_prewarm_faststart_if_needed()` warmt Faststart-Cache parallel zur Thumbnail-Generierung.

- **Docker-Deployment** — Multi-Stage-Image, `docker-compose.yml` (audio 8010, video 8011, channel 8012 optional), Named-Volumes, Healthchecks, `docs/docker.md`.

- **Cast/AirPlay-Button** — `#video-cast-btn`, Remote Playback API (Chromium) + `webkitShowPlaybackTargetPicker` (iOS). Kein SDK.

- **Video-Server UI-Anpassungen** — Tools-Row ohne Playlists bei Video, Eck-Sprachflagge (`.folder-lang-corner`), `_isVideo`-Laufzeit-Flag.

- **iOS Auto-PiP Fix** — `visibilitychange` prüft PiP-Status vor Pause, kein Abbruch der `autopictureinpicture`-Transition.

- **asyncio-Log-Noise** — `asyncio`-Logger auf `ERROR`.

---

## 2026-05

- **Smart Playlists** — `streaming/core/smart_playlists.py`, Operator-Registry (eq/gte/lte/between/in/contains/starts_with/matches/within_days/any_of/all_of/none_of), AND/OR, Sort+Limit, client-seitige Auswertung `_evaluateSmartPlaylist()`. Endpoints `POST/PUT /api/<media>/playlists/smart`. Editor-Modal im UI. `SVG_SMART_PLAYLIST`.

- **`hometools scan-library`** — `library_scan.py`, Checks `episode_naming`/`oversized_folder`/`untagged_language`, `--json`, `--fail-on-warning`.

- **`hometools validate-overrides`** — `overrides_validator.py`, Checks `parse_error`/`unknown_language`/`unknown_episode_key`/`unknown_field`/`empty_override`/`non_media_extension`/`lonely_language_group`.

- **Per-Episode `language`/`subtitle_language` Override** — `EpisodeOverride` + `FolderOverrides` um beide Felder erweitert. Episode gewinnt über Folder-Fallback und Auto-Detection.

- **Tools-Row-Redesign** — `.playlist-tools-row` statt großer Karten, `__alltitles__`-Pseudo-Playlist, Reihenfolge: Neue Playlist → Smart Playlist → Titel → Downloaded → reload.

- **Waveform-Peak-Caching + Stereo** — 256 Segmente, `peaks_l`/`peaks_r`, Stereo-Visualisierung (L oben / R unten), Backward-kompatibel (Mono-Fallback).

- **Duplikat-Ghost-Zeilen** — `._deleted`-Marker, Ghost-Row `.track-item--deleted` (Strikethrough), `(N gelöscht)`-Counter.

- **URL-Routing erweitert** — `sort`, `fr`, `ff`, `fg`, `fh`, `vm`, `panel=tools` als Query-Parameter.

- **Rating-Filter-Chip** — `(N/M)`-Format stabil, `min-width`, `opacity 0.4`, `saturate(0.2)`.

- **Bugfixes** — Audit-Button in Tools-Panel-Header, SW-Routing-Bug (API-Check vor Streaming-Check), Audit-Log Exception-Safety, `audit_dir`-Parameter in `create_app()`.

---

## 2026-04

- **File Mover** — `POST /api/audio/move-file`, `GET /api/audio/folders`, `renderMoveWidget()` (2×2 Quick-Grid + Dropdown), MRU in localStorage, `body.tool-show-file-mover`, `SVG_MOVE`.

- **Duplikat-Löschung (Soft-Delete)** — Trash in Duplikat-Panel + Track-Liste, `POST /api/audio/delete-file` + `/api/video/delete-file`, `attention_delete_files()`, Audit `file_delete`.

- **Duplikat-Erkennung (Client-Side)** — `_normalizeStem()`, `_dupeKey()`, `_buildDuplicateMap()`, `.dupe-badge`, Duplikat-Panel.

- **Audit-Panel SVG-Sterne + Rating-Undo-Fix** — `IC_STAR_FILLED`/`IC_STAR_EMPTY` im Audit, `set_rating_stars()` im Undo, `stars_to_popm_raw(old_stars)`.

- **Index-Cache Snapshot-Staleness** — `_built_at = 0.0` beim Laden → sofortiger Hintergrund-Rebuild. `refreshCatalog()` ruft jetzt `POST /api/<media>/refresh` auf.

- **Non-Blocking Video-Server-Start** — Language-Group-Beladung in Daemon-Thread.

- **Multi-Language Phase 1b** — `parse_subtitle_hint()`, `MediaItem.subtitle_language`, `compositeFlagHtml()`, Inline-Flaggen-Buttons in Multi-Language-Ordnerkarten.

- **Sprach-Tags & Flaggen-Badges** — `streaming/core/language.py`, `parse_language_tag()`, `MediaItem.language`, 10 Sprachen, `cleanFolderName()`.

- **Repeat-Modus** — Off / Alle / Einzeltitel, `cycleRepeat()`, `ht-repeat-mode`, `enable_repeat`.

- **M4A Windows Xtra-Box Rating-Sync** — `_read_xtra_rating()`, `_write_xtra_rating()`, immer beide Tags (iTunes + Xtra) synchron schreiben.

- **POPM WMP-Standard-Mapping** — `popm_raw_to_stars()`, `stars_to_popm_raw()`, Step-Mapping 0/1/64/128/196/255.

- **Global Search (Root-View)** — `initGlobalSearch()`, `globalSearch()`, `renderSearchResults()`, kein Backend-Endpoint.

- **Lazy Per-Folder Rating Refresh** — `POST /api/audio/refresh-ratings`, `IndexCache.patch_items()`, `refreshFolderRatings()` nach `showPlaylist()`.

- **Crossfade (Audio)** — `_xfadeAudio`, `HOMETOOLS_CROSSFADE_DURATION`, Sinus-Rampe, Queue-kompatibel.

- **Warteschlange (Queue)** — Queue-Panel Bottom-Drawer, `.track-queue-btn`, `dequeueNext()`, DnD-Reorder, `initQueueDragDrop()`/`destroyQueueDragDrop()`.

- **Playlists** — `streaming/core/playlists.py`, CRUD, Pseudo-Ordner-Karten, DnD-Reorder, Cross-Device-Sync (revision + changelog), Optimistic UI, Smart Playlists.

---

## 2026-03

- **Genre-Tags** — `get_genre()`, `MediaItem.genre`, Genre-Filter-Chip.

- **Audit-Log entkoppelt** — `.hometools-audit/`, `get_audit_dir()`, `HOMETOOLS_AUDIT_DIR`, automatische Migration.

- **Swipe-Gesten** — `touchstart`/`touchend` für Zurück-Navigation.

- **Channel-Server Playlist-basiert** — `server_playlist.py` ersetzt HLS-Architektur, Standard-UI via `render_media_page()`.

- **Channel-Mixer Concat Demuxer** — Pre-Transcode in `tmp/`, ein ffmpeg-Prozess, kein Multi-Prozess.

---

## Frühere Features (ohne genaues Datum)

- Fernsehsender (Channel-Server, Port 8012), YAML-Programmplan, HLS
- Schnellfilter-Chips (Bewertung, Favoriten, Genre)
- Tools-Panel, Inline-Ratings, Downloads-Toggle
- Lyrics-Panel (Audio)
- `make clean`
- Thumbnail-Größen je Ansichtsmodus (small/large)
- Zuletzt gespielt / Continue Watching (`progress.py`, Resume-Toast)
- Ansichtsumschalter (list → grid → filenames)
- Metadaten-Bearbeitung Audio (`write_track_tags()`, Edit-Modal)
- Hörbuch-Ordner-Erkennung (`HOMETOOLS_AUDIOBOOK_DIRS`)
- Audit-Log (`audit_log.py`, JSONL, `/audit`-Panel, Undo)
- Rating-Schreiben Audio (`POST /api/audio/rating`, 5 Sterne, POPM)
- Shuffle-Modus (Fisher-Yates + gewichtet, Long-Press)
- Folder-Favorites (`#`-Prefix, SVG-Badge)
- PWA Shortcuts (Deep Linking, Pin-Button, Manifest)
- Offline-Downloads (Service Worker, IndexedDB)
- FastStart-Erkennung für MP4 (`has_faststart()`, Auto-Remux)
- SVG-Icons überall (iOS-kompatibel, keine Unicode/Emoji)
- Shadow-Cache (`.hometools-cache/`, `HOMETOOLS_CACHE_DIR`)
- Wiedergabe-Fortschritt (`progress.py`)
- Recently Added Sortierung (`mtime`)
- On-the-fly Remux/Transcode (`remux.py`, FLV/AVI/MKV → frag-MP4)
- Serien-Episoden-Ordnung (`parse_season_episode()`, S##E## / ##x##)
- YAML-Overrides (`hometools_overrides.yaml`)
- Cache-First API (Index-Rebuild im Hintergrund)
- Server-Logging (`RotatingFileHandler`)

