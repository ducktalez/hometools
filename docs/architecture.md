# Architecture

## Native client layer (`clients/`) & API contract (2026-06-15)

Native apps (Android TV active; iOS/Android phone reserved) live under
`clients/`. They are **thin REST clients** of the Python backend — the
single source of truth. No business logic is duplicated in client code.

**Anti-duplication strategy ("don't build admin + remote-UI twice"):**

- All functionality stays server-side, exposed via the JSON API.
- The web admin UI is the **full** client; native clients implement only the
  **read/playback subset** (`/api/video/items`, `/api/video/continue`,
  `/api/video/metadata`, `/api/video/progress`, `/api/video/intro`, plus the
  binary `GET /video/stream` and `GET /thumb`). Admin write-endpoints
  (rating/tag/move/delete/playlists) are **never** ported to a native client.
- **Contract = OpenAPI.** `hometools export-openapi --server {video,audio}`
  (CLI in `cli.py:run_export_openapi`) writes `clients/shared/openapi/*.json`.
  Only the JSON API surface (`/api/*` + `/health`) is included; HTML/binary
  routes are excluded (they also trip FastAPI's schema builder under
  `from __future__ import annotations`). `tests/test_openapi_export.py` locks
  the playback-relevant paths.
- **Browser-testable API (`/openapi.json` + `/docs`).** Both servers install a
  filtered schema builder via `streaming/core/openapi_schema.py`
  (`install_filtered_openapi`) in `create_app`. This reuses the same
  `build_api_openapi` helper the CLI export uses, so the live servers serve a
  working Swagger UI at **`http://<host>:<port>/docs`** for interactive testing
  without breaking on the HTML/binary routes. The helper is exception-safe and
  never blocks startup.

**Continue-Watching feed:** `streaming/core/progress.py:get_continue_watching()`
filters the recent-progress store to *unfinished* items (watched past 30 s,
below 95 % of duration). `GET /api/video/continue` joins it with the catalog so
each entry carries full `MediaItem` metadata + resume position. Audio has no
equivalent (audiobook resume is automatic). Tests in
`tests/test_continue_watching.py`.

**Android TV (`clients/androidtv/`):** Kotlin + Jetpack **Compose for TV**
(`androidx.tv.material3`, D-pad focus) + **Media3/ExoPlayer**. ExoPlayer plays
MP4/MKV/AVI with HTTP Range straight from `/video/stream` — the reason a native
app handles formats the TV browser cannot, and why a WebView wrapper was
rejected for TV. Three screens: server setup → browse → player. Data layer
(`data/`) mirrors `MediaItem.to_dict()` and tolerates unknown fields.

### Designregeln (Clients)

- API-first: ein API-Change → Schema neu exportieren + Client im selben Change anpassen.
- Admin-Tools bleiben **web-only**; native Clients rufen nur die Playback-Teilmenge.
- `MediaItem`-Feldnamen sind der Contract; Clients parsen vorwärtskompatibel.
- Backend-Lücken werden **im Backend** geschlossen (Endpoint + Test), nicht clientseitig.
- Build-Artefakte (`clients/**/build/`, Gradle) sind git- und docker-ignoriert.

## Streaming issue pipeline

Die Streaming-Server schreiben Warnungen/Errors nicht nur in Logs, sondern zusätzlich in den Shared-Core-Mechanismus unter `src/hometools/streaming/core/issue_registry.py`.

Ablauf:

1. Logs/Fehlerquellen erzeugen offene Unregelmäßigkeiten in `issues/open_issues.json`
2. Jede Beobachtung wird zusätzlich in `issues/issue_events.jsonl` angehängt
3. Offene Issues werden im Shared Core zu stabileren Aufgabenfamilien gebündelt und als `issues/todo_candidates.json` persistiert
4. Der Scheduler-Stub dämpft wiederkehrende Aufgaben über `issues/todo_state.json` per Cooldown
5. `todo_state.json` speichert zusätzlich manuelle Zustände wie `acknowledged` und `snoozed`
6. Die Status-Endpunkte (`/api/audio/status`, `/api/video/status`) liefern neben `issues` eine kompakte `todos`-Summary — ausschließlich für serverseitiges Monitoring und CLI-Zugriff, **nicht** in der Browser-UI sichtbar
7. Beide Server bieten zusätzlich denselben Schreib-Endpunkt (`POST /api/<media>/todos/state`) für `acknowledge`, `snooze` und `clear`
8. Jeder Scheduler-Lauf wird in `issues/scheduler_runs.jsonl` protokolliert

## Designregeln

- TODO-Ableitung bleibt **shared core**, nicht audio-/video-spezifisch.
- Aufgaben werden **konservativ gebündelt** (primär nach Quelle + Kategorie), damit wiederkehrende Einzel-Issues nicht sofort Aufgabenfluten erzeugen.
- Der Scheduler meldet standardmäßig nur **aktive** Aufgaben; kürzlich bereits gemeldete Aufgaben werden bis zum Cooldown unterdrückt, außer ihre Severity steigt.
- Manuelle Zustände (`acknowledge`, `snooze`) gelten pro `todo_key` und leben bewusst im Shared Core statt in audio-/video-spezifischen Modulen.
- Issues/TODOs werden **nicht** in der Browser-UI angezeigt. Die Status-/State-Endpunkte dienen ausschließlich dem serverseitigen Monitoring und der CLI.
- Der Scheduler-Stub führt **noch keine** destruktiven oder langsamen Aktionen automatisch aus; er erzeugt nur priorisierte Kandidaten.
- Alle Funktionen liefern bei Fehlern robuste Defaults zurück und dürfen keine Aufrufer abstürzen lassen.
- Offene Issues, TODO-Kandidaten und spätere Automationsschritte müssen mit dem Schattenverzeichnis unter `HOMETOOLS_CACHE_DIR` koordiniert bleiben.

## Mobile-Player: Seek, Resume & PiP

**Tap/Drag-to-Seek (`initTrackSeek`):** Der sichtbare Fortschrittsbalken nutzt einen über die Spur gelegten, transparenten `<input type=range>` mit 1px-Thumb. Auf Touch-Geräten (iOS Safari) ist dieser Thumb nicht greifbar und ein Tap auf die Spur springt nicht — Vorspulen war unmöglich. `initTrackSeek()` registriert daher Pointer-Events (`pointerdown`/`move`/`up`/`cancel`, decken Maus + Touch + Pen ab) auf der gesamten `.progress-track`, rechnet die Zielzeit aus `clientX`/Bounding-Box und setzt `player.currentTime` (und `bgAudio.currentTime`, falls Hintergrund-Audio aktiv). `setPointerCapture` hält den Drag über die Track-Grenzen hinweg; im CSS sorgt `touch-action: none` auf `.progress-track` dafür, dass die vertikale Scroll-Geste den Seek-Drag nicht abbricht.

**Spurious-`ended`-Guard:** Bei Verbindungsverlust/Stream-Fehlern feuern manche Browser ein `ended`-Event, obwohl die Wiedergabeposition nicht am Ende ist. Ohne Schutz würde `playNextItem()` weiterschalten und bei `repeat-all` auf Index 0 (= S01E01) zurückspringen. Der `ended`-Handler prüft `reachedEnd = !isFinite(dur) || dur<=0 || pos >= dur-1.5`; ist das Ende nicht erreicht, wird nur gespeichert und **nicht** weitergeschaltet.

**Progress-Robustheit (Recent-Aktualität):** `saveProgressNow()` sendet bevorzugt via `navigator.sendBeacon` (überlebt Page-Unload/App-Background auf Mobil; Fallback `fetch` mit `keepalive`). Ein Flush erfolgt zusätzlich bei `visibilitychange→hidden` und `pagehide`. `playItem()` flusht den Stand des **ausgehenden** Tracks, bevor `_progressRelPath` neu gesetzt wird — vorher cancelte das `clearTimeout(_progressTimer)` den noch ausstehenden Debounce-Save des vorigen Tracks, wodurch die server-seitige „Weiterschauen"-Liste hinterherhinkte.

**PiP am Handy:** Der dedizierte PiP-Button (`#btn-pip`) wird auf Touch-Geräten (`isIOS || (navigator.maxTouchPoints>0 && matchMedia('(pointer: coarse)'))`) ausgeblendet. PiP funktioniert dort „wie im klassischen Browser" über die native Steuerung + automatische `autopictureinpicture`-Transition beim Backgrounden. Desktop behält den Button.

**„Folge fehlt"-Platzhalter:** `withMissingEpisodes()` fügt Platzhalterzeilen für fehlende Episoden ein — jetzt **pro benachbartem Episodenpaar derselben Staffel** (beide `season>0`, gleiche Staffel, positive Lücke, max. 20), statt nur wenn *alle* Tracks der Ordneransicht Serien-Episoden sind. So bekommen auch gemischte Ordner Platzhalter. Render: `Folge fehlt` + `S0XE0Y — nicht in der Bibliothek`; CSS-Klasse `.missing-episode` mit roter (`#cf6679`) Tönung und diagonalem Schraffur-Pattern. Spiegelt das `/board` direkt in der Liste.

## Aufgaben-Board: Fehlende Folgen (Video)

Die Seite `/board` (nur Video-Server) zeigt offene Bibliotheks-Aufgaben — primär **fehlende Einzelfolgen** innerhalb existierender Serien-Staffeln. „Ganze Staffeln" werden bewusst nicht gemeldet.

**Erkennung — `streaming/core/episode_gaps.py`:**

- Reine Funktion `find_missing_episodes(items, *, min_present=2) -> list[SeasonGap]`.
- Arbeitet auf dem bereits gebauten Katalog (`MediaItem.season`/`episode` werden von `parse_season_episode` befüllt). Kein Dateisystem-Zugriff, kein I/O.
- Gruppierung nach `(Elternordner-Posix-Pfad, Staffel)` — Gruppierung über den *Elternordner* (statt nur dem Seriennamen) hält unverwandte Shows getrennt und behandelt Staffel-Unterordner (`Show/Staffel 1/…`) korrekt isoliert.
- Nur Items mit `season>0 & episode>0` zählen. Eine Staffel braucht ≥ `min_present` (Default 2) distinkte Folgen, sonst gibt es keine verlässliche Innen-Range.
- Lücke = jede Episodennummer zwischen `min`- und `max`-vorhandener Folge, die fehlt. Eine komplett fehlende Staffel erzeugt nie einen Befund (keine Innen-Range → „nur Einzelfolgen").
- Exception-safe: gibt `[]` bei jedem Fehler zurück. `SeasonGap.to_dict()` ist JSON-serialisierbar (`series`, `folder`, `season`, `present_episodes`, `missing_episodes`, `missing_count`, `first_episode`, `last_episode`).

**Endpoint — `GET /api/video/board`:**

```json
{ "missing_episodes": [ {"SeasonGap": "…"} ], "missing_count": 3, "issues": [ {"ScanIssue": "…"} ] }
```

- `missing_episodes` kommt aus dem In-Memory-Katalog (instant, kein NAS-Walk).
- `issues` kommt best-effort aus `scan_video_library()` (Episode-Naming, Oversized-Folder, Untagged-Language) als „weitere Aufgaben". Best-effort + exception-safe; bei Fehler bleibt `issues: []`.

**Seite — `render_board_page_html()` in `server_utils/_board.py`:**

- Standalone-Dark-Theme-Seite (gleiche Familie wie `/audit`), eigenes CSS+JS als Python-Strings.
- Zwei Sektionen: „Fehlende Folgen" (Karten mit Serie/Staffel/Ordner, rote `E0X`-Badges, vorhandene Range) und „Bibliotheks-Hinweise".
- Fetch auf `GET /api/<media>/board`, „Aktualisieren"-Button, Retry bei Fehler. Re-exportiert über `server_utils/__init__.py`.

**Einstieg:** Board-Button `#board-btn` (Icon `SVG_BOARD`, Checklist-Clipboard) im Tools-Panel-Header neben dem Audit-Button — **nur Video** über den `is_video`-Guard in `_html.py`. Kein Audio-Pendant (Audio hat keine Episoden).

**CLI:** `hometools missing-episodes [--library-dir PATH] [--json]` baut den Video-Index und gibt dieselben Gaps human-readable oder als JSON aus.

## Non-blocking Index-Aufbau

Die Katalog-API-Endpunkte (`/api/audio/tracks`, `/api/video/items`) prüfen zuerst den Cache und starten ggf. einen Background-Refresh. `check_library_accessible` wird **nur** aufgerufen, wenn keine gecachten Items vorhanden sind (Cold-Start oder leerer Cache). Dadurch blockiert der Library-Check (bis zu 3 s bei NAS-Pfaden) nie die Auslieferung bereits verfügbarer Daten.

### Snapshot-Frische statt Rebuild-bei-jedem-Start (2026-06-12)

Früher setzte `IndexCache.get_cached()` beim Laden eines persistierten Snapshots `_built_at = 0.0` und erzwang damit bei **jedem** Serverstart einen vollständigen Neu-Index der Bibliothek (Symptom: „lädt immer alle Datei-Indizes neu"). Jetzt wird das **reale Alter** des Snapshots übernommen (`_built_at = built_at` aus `saved_at`): ein Snapshot, der jünger als die TTL ist (`HOMETOOLS_STREAM_INDEX_CACHE_TTL`, Default 900 s), gilt als *fresh* → kein Rebuild beim Start. Nur ältere Snapshots lösen einen Hintergrund-Rescan aus (für offline hinzugefügte Dateien). Für sofortiges, vollständiges Neuladen dient weiterhin der „Katalog neu laden"-Button (`POST /api/<media>/refresh` → `invalidate()` + Rebuild).

## CLI-Dashboard

`hometools stream-dashboard` kombiniert Issues, TODO-Kandidaten und den letzten Scheduler-Lauf in einer einzigen Box-Drawing-Tabelle. Daten-Logik lebt in `streaming/core/issue_registry.py`, Präsentation in `streaming/core/issue_dashboard.py`. Unterstützt `--json` für maschinelle Auswertung und `--fail-on-match` als Scheduler-Gate.

## Action Hints

TODO-Kandidaten und Scheduler-Ergebnisse enthalten ein `action_hints`-Feld mit strukturierten CLI-Empfehlungen pro Kategorie. Jeder Hint hat `action_id`, `label`, `cli_command` und `make_target`. Mapping in `_ACTION_HINT_MAP`: `thumbnail` → `prewarm-thumbnails`, `cache` → `reindex`, `sync` → `check-nas`, `metadata` → `check-metadata`. Platzhalter `{server}` wird aus dem Source-String aufgelöst.

## Noise-Unterdrückung

`_NOISE_RULES` in `issue_registry.py` definieren quellspezifische Schwellen. Jede Regel hat `source_prefix`, `category`, `min_severity_for_todo` und `min_count_for_todo`. CRITICAL-Issues passieren immer. Noise-gefilterte Kandidaten werden als `noise_suppressed_count` im Payload und Dashboard ausgewiesen.

## Root-Cause-Deduplizierung

`_ROOT_CAUSE_PATTERNS` in `issue_registry.py` gruppieren Issues über Sources und Kategorien hinweg nach gemeinsamer Root-Cause. Erkannte Muster (`library-unreachable`, `ffmpeg-missing`, `permission-denied`) erzeugen einen einzigen TODO statt mehrerer per-Source-TODOs. Der Family-Key wird dann `root-cause|{cause_id}` statt `{category}|{source}`.

## Serien-Episoden-Ordnung (Video)

`parse_season_episode()` in `streaming/core/catalog.py` ist die zentrale Funktion zur Extraktion von Staffel/Episode aus Dateinamen. Unterstützte Muster: `S##E##` und `##x##` (Priorität in dieser Reihenfolge). Gibt `(0, 0)` zurück wenn kein Muster erkannt wird — wirft nie Exceptions.

`MediaItem` trägt die Felder `season: int = 0` und `episode: int = 0`. `build_video_index()` und `quick_folder_scan()` befüllen diese automatisch. `sort_items()` sortiert innerhalb desselben Ordners (artist) nach `(season, episode, title)`, wodurch Serien-Episoden chronologisch statt alphabetisch geordnet werden. Der Client-seitige JS-Sort in `applyFilter()` verwendet dieselbe Logik.

`serie_path_to_numbers()` in `video/organizer.py` delegiert an die Shared-Funktion, wirft aber weiterhin `ValueError` für den Organizer-Workflow.

## YAML-Media-Overrides

Per-Ordner `hometools_overrides.yaml`-Dateien erlauben manuelle Korrektur von Anzeigenamen, Staffel/Episode-Nummern und dem Serientitel. Ähnlich zu Jellyfin NFO-Dateien, aber als einzelne YAML-Datei pro Ordner.

**Modul:** `streaming/core/media_overrides.py`

**Dateiformat:**
```yaml
series_title: "Avatar: Der Herr der Elemente"
episodes:
  "filename.mp4":
    title: "Episodentitel"
    season: 1
    episode: 1
```

**Ablauf:**
1. `load_all_overrides(library_root)` scannt alle Unterordner nach Override-Dateien
2. `apply_overrides(items, library_root)` erstellt neue `MediaItem`-Instanzen mit überschriebenen Werten (frozen dataclass)
3. `series_title` überschreibt das `artist`-Feld (Ordnername) für alle Items im Ordner
4. Fehlende Felder behalten ihren auto-detektierten Wert
5. Integration in `build_video_index()` (vor dem Sortieren) und `quick_folder_scan()`

**Design-Regeln:**
- Override-Dateien leben im Library-Ordner neben den Media-Dateien
- Fehlerhafte/fehlende YAML wird lautlos ignoriert (robustes Fallback)
- `MediaItem` wird nie mutiert — neue Instanzen bei Override

## Shadow-Cache

Das Shadow-Cache-Verzeichnis (Default: `.hometools-cache/` im Repo-Root, überschreibbar via `HOMETOOLS_CACHE_DIR`) speichert alle generierten Artefakte:

- `audio/` — Audio-Thumbnails (Cover-Art, 120px + 480px) **und Waveform-Caches** (`*.waveform.json`)
- `video/` — Video-Thumbnails (Frame-Extraktion via ffmpeg, 120px + 480px)
- `indexes/` — Persisted Index-Snapshots (JSON, library-dir-spezifisch via MD5-Hash)
- `progress/` — Wiedergabe-Fortschritt (JSON)
- `issues/` — Issue-Registry, TODO-Kandidaten, Scheduler-Logs
- `logs/` — Server-Log-Dateien
- `thumbnail_failures.json` — Failure-Registry für fehlgeschlagene Thumbnails
- `video_metadata_cache.json` — Persistierter Metadaten-Cache (ffprobe-Ergebnisse)

### Index-Snapshots

Der vollständige Index wird nach einem erfolgreichen Rebuild atomar als JSON-Snapshot gespeichert (`_save_snapshot`). **Es gibt kein inkrementelles Speichern während des Builds** — wird der Server während der Indizierung beendet, geht der laufende Scan-Fortschritt verloren. Der **letzte erfolgreiche Snapshot bleibt erhalten** und wird beim nächsten Start als Fallback geladen, sodass der Server sofort funktionsfähig ist (ohne Scan-Wartezeit).

### `make clean`

`make clean` löscht **alle** Artefakte unter `.hometools-cache/`:

- Ordner: `audio/`, `video/`, `indexes/`, `issues/`, `logs/`, `progress/`, `shortcuts/`, `playlists/`, `channel/`
- Dateien: `video_metadata_cache.json`, `thumbnail_failures.json`

Das Audit-Log liegt seit dem Refactoring in einem eigenen Verzeichnis (`.hometools-audit/`, konfigurierbar via `HOMETOOLS_AUDIT_DIR`) und wird von `make clean` **nicht berührt**.

### Thumbnails

Zwei Größen pro Mediendatei:
- **Klein** (120px, `.thumb.jpg`) — für Listen- und Grid-Ansichten, schnell ladend
- **Groß** (480px, `.thumb-lg.jpg`) — für Serien-Vorschauen und Detail-Ansichten, nachladend

Beide werden im Hintergrund-Thread generiert (`start_background_thumbnail_generation`). MTime-basierte Invalidierung: Thumbnails werden regeneriert wenn die Quelldatei neuer ist.

### Waveform-Cache (Audio)

**Modul:** `streaming/core/waveform.py`

Für jede Audio-Datei werden 128 normalisierte Peak-Werte (0.0–1.0) im Shadow Cache gespeichert:

```
<cache_dir>/audio/<relative_path>.waveform.json
→ {"peaks": [0.0, ..., 1.0], "segments": 128}
```

**Extraktion:** ffmpeg dekodiert die Audiodatei bei 1 kHz Mono (`-ar 1000 -ac 1 -f f32le`) und schreibt rohes Float32-PCM auf stdout. Python liest es via `struct.unpack`, teilt in 128 gleichgroße Blöcke auf und berechnet pro Block den Peak-Wert (`max(abs(sample))`). Anschließend wird auf [0, 1] normalisiert.

**API-Endpunkt:** `GET /api/audio/waveform?path=<relative_path>`
- Prüft zuerst den Shadow Cache (schnell).
- Generiert bei Cache-Miss on-demand (dauert < 5 s für typische Songs).
- Gibt `{"peaks": [...128 floats...], "segments": 128}` zurück oder 404 bei Fehler.

**Hintergrund-Warmup:** Audio-Server-Startup startet neben dem Thumbnail-Thread auch einen `waveform-bg`-Thread, der alle Waveform-Caches vorab befüllt (`start_background_waveform_generation`). Gleicher Work-Item-Typ wie Thumbnails: `(media_path, cache_dir, media_type, relative_path)`.

**Classic-Mode-UI (Waveform-Overlay):**
Im classic Player-Bar (28 px hoch, `<canvas id="waveform-canvas">`) werden die gecacheten Peaks als semi-transparente Amplituden-Streifen über den Fortschrittsbalken gelegt:
- **Layer 1:** Basis-Fortschrittsbalken (5 px hoch, `#333` / Akzentfarbe je gespielt/ungespielt)
- **Layer 2:** 128 Waveform-Balken zentriert auf der Canvas-Mittellinie (`globalAlpha 0.38` gespielt / `0.22` ungespielt, Farbe `#fff`)
- **Layer 3:** Playhead-Dot (weißer Kreis r=6 an der aktuellen Position)

Die JS-Variable `WAVEFORM_API_PATH = '/api/audio/waveform'` wird in `_player_js.py` beim Rendern injiziert. Ist kein Waveform verfügbar oder `!isAudioMode`, fällt `drawWaveform` auf den reinen Fortschrittsbalken zurück.

**MTime-Invalidierung:** Shadow-Cache wird regeneriert wenn `source.st_mtime > waveform.st_mtime`.

**Exception Safety:** Alle Public-Funktionen in `waveform.py` geben im Fehlerfall `None`/`False` zurück, nie eine Exception.

## On-the-fly Remux & FastStart

**Modul:** `streaming/core/remux.py`

Nicht alle Videoformate sind direkt im Browser streambar. Der Remux-Mechanismus löst zwei Probleme:

### Nicht-native Container (FLV, AVI, MKV)

`needs_remux(path)` erkennt anhand der Dateiendung, ob ein Container nicht nativ vom Browser unterstützt wird. Solche Dateien werden on-the-fly über ffmpeg als **Fragmented MP4** (`-movflags frag_keyframe+empty_moov`) gestreamt.

- **Container Copy** (`-c copy`): Wenn die enthaltenen Codecs browserkompatibel sind (H.264/H.265 Video, AAC/MP3/Opus Audio) — `can_copy_codecs()` prüft via `probe_codecs()` (ffprobe).
- **Transcode**: Wenn die Codecs nicht kompatibel sind (z. B. XviD → H.264, MP2 → AAC).

### Non-FastStart MP4s

`has_faststart(path)` liest die MP4-Atom-Struktur (ftyp/moov/mdat) und erkennt Dateien, bei denen das `moov`-Atom am Ende liegt. Solche Dateien können vom Browser nicht gestreamt werden (HTTP 200 statt 206, gesamte Datei muss heruntergeladen werden).

**Lösung:** Der `/video/stream`-Endpoint erkennt Non-FastStart-MP4s und leitet sie automatisch durch `remux_stream()` mit `-c copy -movflags frag_keyframe+empty_moov`. Für den Browser transparent — sofortige Wiedergabe.

**Design-Regeln:**
- Originaldateien werden **nie** modifiziert
- Remux-Ergebnisse werden **nicht** gecacht — immer on-the-fly (vermeidet Speicherprobleme bei großen Dateien)
- UI zeigt ein ⚡-Badge bei Dateien, die Konvertierung benötigen
- `ffmpeg`/`ffprobe`-Fehler werden graceful behandelt (optimistisches Fallback auf `FileResponse`)

## Wiedergabelisten (User Playlists)

**Module:** `streaming/core/playlists.py`, `streaming/core/smart_playlists.py`, `streaming/audio/server.py`, `streaming/video/server.py`, `streaming/core/server_utils.py`

### Übersicht

Benutzer können benannte Playlists erstellen und Medien-Items (Tracks / Videos) hinzufügen. Playlists sind server-spezifisch (Audio und Video getrennt) und werden im Shadow-Cache persistiert. Playlists erscheinen als **Pseudo-Ordner-Karten** auf der Root-Startseite, direkt nach der „Downloaded"-Karte.

### Storage

```
<cache_dir>/playlists/audio.json   ← Audio-Playlists
<cache_dir>/playlists/video.json   ← Video-Playlists
```

Jede Datei enthält ein JSON-Array von Playlist-Objekten:

```json
[
  {
    "id": "a1b2c3d4e5f6",
    "name": "Meine Playlist",
    "created": "2026-04-01T00:00:00+00:00",
    "items": ["artist/song.mp3", "artist/other.mp3"]
  }
]
```

Thread-sicher via `threading.Lock`. Atomare Schreibvorgänge (NamedTemporaryFile + replace). Alle Read-Modify-Write-Operationen halten den Lock für die gesamte Dauer — keine Race Conditions bei konkurrierenden Schreibzugriffen.

### Limits

- Max **50 Playlists** pro Server
- Max **500 Items** pro Playlist
- Duplikate innerhalb einer Playlist werden silently ignoriert

### API-Endpoints (Audio + Video)

| Endpoint | Methode | Beschreibung |
|---|---|---|
| `/api/<media>/playlists` | `GET` | Alle Playlists laden (`{items: [...]}`) |
| `/api/<media>/playlists` | `POST` | Neue Playlist erstellen (`{name}` → `{playlist}`) |
| `/api/<media>/playlists?id=` | `DELETE` | Playlist löschen (`{items: [...]}`) |
| `/api/<media>/playlists/items` | `POST` | Item hinzufügen (`{playlist_id, relative_path}` → `{playlist}`) |
| `/api/<media>/playlists/items?playlist_id=&path=` | `DELETE` | Item entfernen (`{playlist}`) |
| `/api/<media>/playlists/items` | `PATCH` | Item verschieben (`{playlist_id, relative_path, direction}` → `{playlist}`) |
| `/api/<media>/playlists/items` | `PUT` | Item auf Ziel-Index verschieben (`{playlist_id, relative_path, to_index}` → `{playlist}`) |

### Feature-Flag

```python
# render_media_page(enable_playlists=True)   →  Audio + Video
# render_media_page()                         →  Default: False
```

`render_media_page()` und `render_player_js()` haben den Parameter `enable_playlists: bool = False`. Er steuert:
1. `PLAYLISTS_ENABLED = true` im generierten JS
2. `PLAYLISTS_API_PATH = '/api/<media>/playlists'`
3. `IC_PLAYLIST` — SVG-Icon als JS-Variable
4. Playlist-Button (`.track-playlist-btn`) pro Track in der Liste
5. Playlist-Pseudo-Ordner-Karten auf der Root-Startseite (`.playlist-folder-card`)
6. „Neue Playlist…"-Karte (`.playlist-new-card`) — gemeinsam mit „Downloaded" und „Titel" in der kompakten **Tools-Row** (`.playlist-tools-row`)
7. „Zur Playlist hinzufügen"-Modal (`#playlist-modal-backdrop`)

### Tools-Row (Root-Startseite, seit 2026-05-17)

Drei spezielle Aktionen sind oberhalb des Folder-Grids in einer kompakten horizontalen Leiste zusammengefasst (`.playlist-tools-row`, `grid-column: 1 / -1`):

| Element | ID | Aktion |
|---|---|---|
| **Downloaded** | `#offline-folder-card` | Öffnet die Offline-Library (`openOfflineLibrary()`). Count = Anzahl ready-Downloads. |
| **Neue Playlist…** | `#playlist-new-card` | `prompt()` → `POST /api/<media>/playlists` |
| **Titel** | `#all-titles-card` (`data-playlist-id="__alltitles__"`) | Pseudo-Playlist: zeigt alle Titel aus **allen** User-Playlists in einer deduplizierten Liste (`showUserPlaylistView('__alltitles__')`). Nur sichtbar wenn ≥ 1 Titel in irgendeiner Playlist. **Read-only** — Reorder/Remove sind blockiert. |

Helper-Funktionen: `_collectAllPlaylistRelPaths()`, `_countAllPlaylistTitles()`, `_resolveAllPlaylistItems()`.

Die alten großen `folder-card`-Quadrate für „Downloaded" und „Neue Playlist…" wurden ersetzt; die Klassennamen `.offline-folder-card`, `.playlist-new-card`, `.playlist-folder-card` bleiben für Selektor-Kompatibilität (Click-Handler, Feature-Parity-Tests) erhalten.

### UI-Elemente (Redesign 2026-04-02)

| Element | ID/Klasse | Funktion |
|---|---|---|
| **Playlist-Ordner-Karte** | `.playlist-folder-card` | Pro Playlist eine Karte auf der Root-Startseite mit IC_PLAYLIST-Icon, Name, Item-Count, Play- und Delete-Button |
| **Neue-Playlist-Karte** | `#playlist-new-card`, `.playlist-new-card` | Dashed-Border-Karte mit "+"-Icon, öffnet `prompt()` für Playlist-Name |
| **Add-Modal** | `#playlist-modal-backdrop`, `.playlist-modal-backdrop` | „Zur Playlist hinzufügen" mit Dropdown + Inline-Erstellen |
| **Track-Button** | `.track-playlist-btn` | Pro Track, öffnet Add-Modal |
| **Drag Ghost** | `.playlist-drag-ghost` | Floating-Element beim Drag (Thumbnail + Titel), folgt Cursor/Finger |
| **Drag Marker** | `.drag-over-above` / `.drag-over-below` | Farbige Insertion-Line via `box-shadow` auf dem Ziel-Track |

**Entfernte Elemente (seit Redesign):**
- `#playlist-pill` (Header-Button) — Zugang über Pseudo-Ordner statt Header
- `#playlist-library` (Overlay-Panel) — nicht mehr nötig
- `.playlist-lib-*` CSS-Klassen
- `openPlaylistLibrary()`, `closePlaylistLibrary()`, `renderPlaylistLibrary()` JS

### JS-Architektur

```
PLAYLISTS_ENABLED: bool           ← aus enable_playlists
PLAYLISTS_API_PATH: str           ← '/api/<media>/playlists'
IC_PLAYLIST: str                  ← SVG-Icon
_userPlaylists: []                ← lokaler State (geladen via API)
_playlistAddPath: ''              ← relative_path des aktuell hinzuzufügenden Items
_currentPlaylistId: ''            ← ID der aktuell gespielten Playlist (für Reorder)

loadUserPlaylists()               ← GET → _userPlaylists, danach Root-View re-rendern
playUserPlaylist(plId)            ← Playlist-Items in allItems auflösen, playTrack(0), setzt _currentPlaylistId
deleteUserPlaylist(plId)          ← DELETE → _userPlaylists aktualisieren, Folder-View re-rendern
openPlaylistModal(relativePath)   ← Add-Modal anzeigen
addToPlaylist(plId, relativePath) ← POST /items → Toast
createAndAddToPlaylist(name, rp)  ← POST (create) → addToPlaylist
movePlaylistItem(rp, direction)   ← PATCH /items → _applyPlaylistUpdate (Legacy, bleibt für Abwärtskompatibilität)
reorderPlaylistItem(rp, toIndex)  ← PUT /items → _applyPlaylistUpdate (Drag-and-Drop)
_applyPlaylistUpdate(pl)          ← re-resolve Items, currentIndex anpassen, renderTracks()
initPlaylistDragDrop()            ← Bindet Mouse/Touch-Events auf track-list (nur in Playlist-Ansicht + filenames/list-Modus)
```

### Drag-and-Drop

Reordering wird per Drag-and-Drop durchgeführt — keine Pfeil-Buttons.

**DnD ist nur aktiv wenn:**
1. `inPlaylist && _currentPlaylistId` (Playlist-Kontext)
2. `viewMode === 'filenames'` oder `viewMode === 'list'` (Dateinamen- oder Listenansicht)

In `grid`-Modus ist DnD **deaktiviert**. Klick auf einen Track spielt ihn ab.

| Plattform | Aktivierung | Verhalten |
|---|---|---|
| **Desktop** | Mousedown + Mausbewegung > 10px | Drag startet erst nach Schwellenwert, nicht sofort bei Klick |
| **Mobile** | Long-Touch (500 ms) | Haptic-Feedback (`navigator.vibrate`), dann Drag |

**Visuelles Verhalten:** Das gezogene Item wird ausgegraut (`opacity: 0.25`, `pointer-events: none`) und bleibt an seiner Position sichtbar. Ghost-Element folgt dem Cursor. No-Op-Unterdrückung: Wenn die berechnete Zielposition identisch mit der Ausgangsposition wäre (= direkt neben dem gezogenen Item, Richtung Originalplatz), wird die Insertion-Line unterdrückt — das verhindert visuelles Springen der Linie.

**Drop-Target-Berechnung (`updateDropTarget`):**

1. `elementFromPoint(x, y)` → nächstes `.track-item` finden
2. Kein Item gefunden, aber Cursor in Track-List-Bounds → letztes sichtbares Item mit `_dropAbove = false` (Fallback „ans Ende")
3. `target === _dragItem` → Indicator löschen, return (nichts markieren)
4. Cursor-Y < Mitte des Items → `above = true` (Einfügung VOR diesem Item)
5. Cursor-Y ≥ Mitte → `above = false` (Einfügung NACH diesem Item)
6. **Normalisierung:** „below N" wird zu „above N+1" umgerechnet (nächstes sichtbares Sibling, überspringe `missing-episode` und `_dragItem`). Nur wenn N das letzte sichtbare Item ist, bleibt `above = false`. → Es gibt pro logischer Position nur EINE Linie.
7. **No-Op-Unterdrückung:** Effektiven `toIndex` berechnen (same as `endDrag`-Logik). Wenn `toIndex === _dragFromIdx` → Indicator löschen, return.
8. `drag-over-above` bzw. `drag-over-below` auf das Ziel-Item setzen.

**CSS Insertion-Line:** `box-shadow: 0 3px 0 0 var(--accent) inset` für `.drag-over-above` (Linie am oberen Rand) und `0 -3px inset` für `.drag-over-below` (Linie am unteren Rand). `drag-over-below` wird durch die Normalisierung nur noch für die allerletzte Position verwendet (nach dem letzten Item). 

### Sort-Option „Liste" (custom)

Neue Sort-Option `<option value="custom">Liste ⇅</option>` im Sort-Dropdown. **Ist der Default** (erste Option im Dropdown):

- **In Playlist-Kontext:** Behält die Server-Reihenfolge bei (kein Re-Sort). DnD-Reorder verändert die Reihenfolge.
- **In Filesystem-Ordner:** Sortiert nach benutzerdefinierter Reihenfolge (server-seitig gespeichert, localStorage als Offline-Fallback).

---

## Intelligente Wiedergabelisten (Smart Playlists)

**Module:** `streaming/core/smart_playlists.py`, `streaming/core/playlists.py`, `streaming/audio/server.py`, `streaming/video/server.py`, `streaming/core/server_utils/_player_js.py`, `streaming/core/server_utils/_css.py`

### Konzept

Eine intelligente Playlist speichert anstelle einer Item-Liste eine **Regelgruppe**.  Beim Anzeigen wird die Playlist clientseitig gegen `allItems` ausgewertet — die `items`-Liste der Playlist bleibt auf dem Server permanent leer.  Beispiele aus iTunes: „Zuletzt hinzugefügt" (`added_at within_days 60`), „Best of Rock" (`in_playlist any_of [Rock, Rock-Alt]` UND `rating >= 4`).

### Storage (v2 Envelope, neues optionales Feld)

```jsonc
{
  "id": "abc123",
  "name": "Best of Rock",
  "created": "…",
  "updated_at": "…",
  "items": [],            // immer leer bei Smart Playlists
  "smart": {
    "match": "all" | "any",
    "rules": [
      {"field": "rating",      "op": "gte",         "value": 4},
      {"field": "in_playlist", "op": "any_of",      "value": ["p1", "p2"]},
      {"field": "added_at",    "op": "within_days", "value": 60},
      {"field": "genre",       "op": "matches",     "value": "^Rock"}
    ],
    "limit": 100,          // optional
    "sort": "rating_desc"  // optional
  }
}
```

Reguläre Playlists haben **kein** `smart`-Feld — die beiden Typen koexistieren in derselben Datei.  `playlists.py` schützt Smart Playlists: `add_item` / `remove_item` / `move_item` / `reorder_item` sind No-Ops (kein Revision-Bump, Warn-Log).

### Operatoren

| Field-Typ | Operatoren |
|---|---|
| Strings (`title`, `artist`, `genre`, `relative_path`, `language`) | `eq`, `contains`, `starts_with`, `matches` (Regex, case-insensitive, ≤ 256 Zeichen) |
| Zahlen (`rating`, `duration`, `season`, `episode`, `bitrate`, `file_size`) | `eq`, `gte`, `lte`, `between` (Liste `[lo, hi]`), `in` |
| `added_at` (Proxy: `MediaItem.mtime`) | `within_days`, `before`, `after` |
| `in_playlist` (Cross-Playlist-Referenz) | `any_of` (OR), `all_of` (AND), `none_of` |
| `is_favorite` (audio-spezifisch) | `eq` (bool) |
| `in_folder` (abgeleitet aus `relative_path`-Prefix) | `eq`, `starts_with` |

`match: "all"` = UND über alle Top-Level-Regeln, `match: "any"` = ODER.  Innerhalb einer Regel realisieren `any_of`/`all_of`/`none_of` (für `in_playlist`) sowie `in` (für Werte-Listen) eine eingebaute Sub-OR-/AND-Semantik — dies reicht für die Phase-1-Use-Cases ohne echtes Sub-Group-Nesting.

### API-Endpoints

| Methode + Pfad | Body | Wirkung |
|---|---|---|
| `POST /api/<media>/playlists/smart` | `{name, smart}` | Neue Smart Playlist anlegen |
| `PUT /api/<media>/playlists/smart` | `{playlist_id, smart}` | `smart`-Block einer (auch regulären) Playlist ersetzen → promotet sie ggf. zur Smart Playlist |

Validierung: `validate_smart_rules()` lehnt fehlende `match`/`rules`/`field`/`op`/`value`-Felder oder eine `limit > 10_000` ab (HTTP 400).

### Auswertung (Client-seitig)

`_evaluateSmartPlaylist(pl)` in [`_player_js.py`](../src/hometools/streaming/core/server_utils/_player_js.py) ist der JS-Mirror von `evaluate_smart()` in `smart_playlists.py`.  Beide:

1. Bauen einen Index `pl_id → set(relative_path)` aus allen **nicht-smarten** User-Playlists (zur Auflösung von `in_playlist`).  Smart-Playlists werden hier übersprungen — siehe Phase-2-Diskussion in `IMPLEMENTATION_PLAN.md`.
2. Iterieren über `allItems` und werten jede Regel via Operator-Dispatch aus.
3. Wenden optional `sort` (`title`, `rating`, `added_at`, `duration`, jeweils auch `_desc`, plus `random`) und `limit` an.
4. Geben eine Liste von `relative_path`-Strings zurück (Python) bzw. `MediaItem`-Objekten (JS).

`_resolvePlaylistItems(plId)` erkennt anhand von `pl.smart` automatisch eine Smart Playlist und füllt `playlistItems` aus der Live-Auswertung — bestehende Track-Render-/Play-/Browse-Pfade brauchen keine Änderung.

### UI-Elemente

| Element | Selektor | Funktion |
|---|---|---|
| **Smart-Playlist-Karte** | `.playlist-folder-card.smart-playlist-card` | Normale Playlist-Karte, plus Lightning-Bolt-Badge (`.smart-pl-badge` mit `SVG_SMART_PLAYLIST`) in der rechten unteren Ecke des Logos |
| **Refresh-Button** | `.playlist-folder-refresh` | Kleiner Button oben links auf Smart-Karten; ruft `refreshSmartPlaylist()` auf (Re-Evaluation + In-Place-Re-Render falls aktuell sichtbar) |
| **Neue-Smart-Playlist-Karte** | `#smart-playlist-new-card` (Klasse `.smart-new-card`) | Zweite „Neu…"-Karte rechts neben „Neue Playlist…" in `.playlist-tools-row`, öffnet den Editor-Modal |
| **Editor-Modal** | `#smart-editor-backdrop`, `.smart-editor-modal` | Reine JS-DOM-Injektion via `openSmartPlaylistEditor(pl?)`.  Name-Feld, AND/OR-Radio, Regelzeilen (`<select field>` + `<select op>` + Wert-Input), „+ Regel"-Button, optionales Limit-Feld, Speichern → `POST` oder `PUT` auf `PLAYLISTS_SMART_PATH` |
| **Wertinput-Varianten** | `.smart-rule-value` | Text/Zahl/`<select multiple>` (für `in_playlist`) / Boolean-Select (für `is_favorite`) / zwei Inputs (für `between`) — automatisch passend zum gewählten Feld+Op |

### Designregeln

- **Keine Server-seitige Re-Evaluation.**  Server speichert nur Regeln; Auswertung lebt 1:1 im Client.  Refresh = lokal neu auswerten.  Bei Wiedergabe-Start auf einer Smart-Karte wird vorher implizit re-evaluiert (kein expliziter API-Call).
- **Kaskaden vermieden in Phase 1.**  `in_playlist`-Referenzen auf Smart Playlists werden beim Index-Bau übersprungen → keine Zyklen, keine Tiefen-Probleme.  Phase 2 plant DAG-Auflösung (siehe Implementation-Plan).
- **`added_at`-Proxy.**  Da kein dediziertes „added_at"-Feld auf `MediaItem` existiert, wird `mtime` (File-Modification-Time) verwendet.  Konsequenz: Tag-Edits oder NAS-Resync können die Zuordnung verschieben.  Phase-2-Verbesserung (persistentes `first_seen_at` im Index-Cache) ist im Implementation-Plan dokumentiert.
- **Regex-Sicherheit.**  Patterns sind auf ≤ 256 Zeichen begrenzt; ungültige Patterns matchen nichts (statt zu crashen).  Compile-Cache pro Pattern.
- **Smart Playlists sind read-only**, was Item-Listen-Mutationen angeht — sowohl an der Storage-Schicht (Guards in `playlists.py`) als auch im Client (kein Add-to-Playlist-Modal-Eintrag für Smart Playlists).

## Tools-Panel (UI-Einstellungen)

**Modul:** `streaming/core/server_utils.py` (CSS + JS + HTML)

Benutzer-steuerbares Panel zum Ein-/Ausblenden von UI-Funktionen. Öffnet sich über die "Tools"-Pill in der Kopfzeile.

### UI

- **Pill:** `<span class="tools-pill" id="tools-pill">Tools</span>` im `<header>`
- **Panel:** Modal-Dialog mit Backdrop (`#tools-panel-backdrop`), Toggle-Switches pro Feature
- **Toggle-Switches:** CSS-only Toggle (`.tools-toggle` mit `<input type="checkbox">` + `.tools-toggle-track`-Slider)
- **State:** `localStorage` unter Key `ht-tools` (JSON-Objekt mit Boolean-Feldern)

### Verfügbare Tools

| Tool-ID | Label | Beschreibung | CSS-Klasse | Status |
|---------|-------|-------------|------------|--------|
| `inlineRatings` | Inline-Ratings | Bewertungssterne direkt in der Track-Liste | `body.tool-inline-ratings` | Implementiert |
| `downloads` | Downloads | Download-Buttons pro Track ein/ausblenden | `body.tool-hide-downloads` | Implementiert |
| `playlists` | Zur Playlist hinzufügen | Playlist-Buttons pro Track ein/ausblenden | `body.tool-hide-playlists` | Implementiert |
| `duplicates` | Duplikate suchen | Doppelte Dateien finden | `body.tool-show-duplicates` | Implementiert |
| `fileMover` | Dateien verschieben | Songs in andere Ordner verschieben | `body.tool-show-file-mover` | Implementiert |

### Globale Tools (Abschnitt im Tools-Panel)

Enthält katalogweite Aktionen und Einstellungen — unabhängig vom Tool-Modus:

- **"Ordnerdaten aller Ordner erneuern"** (`#tools-global-refresh-btn`): Führt sofort `refreshCatalog()` aus und schließt das Panel. Löst ein vollständiges serverseitiges Re-Indexing aller Ordner aus, äquivalent zum manuellen Klick auf die Refresh-Karte in der Startansicht.
- **Auto/Aus-Buttongroup** (`#tool-auto-refresh`): Steuert ob beim Laden der Seite der Hintergrund-Index-Refresh automatisch startet. `"auto"` (Standard) = `scheduleBackgroundRefresh()` wird bei laufendem Index-Build aufgerufen. `"aus"` = kein automatisches Polling; Nutzer muss manuell erneuern. Der Wert wird in `_toolState.autoRefresh` gespeichert.

### Katalog-Refresh-Button (Tools-Row)

Der "Katalog neu laden"-Button **wurde aus dem Header entfernt** und ist jetzt ganz rechts in der `playlist-tools-row` auf der Startansicht (Root) platziert:

- **Karte:** `<button class="tools-row-item refresh-catalog-card" id="refresh-catalog-card">` mit `IC_REFRESH`-Icon
- **Rendering:** Wird in `showFolderView()` immer wenn `isRoot` zum `_toolsRowParts`-Array hinzugefügt
- **Spinner:** `_getRefreshBtn()` (dynamische DOM-Abfrage bei Bedarf) + `.spinning`-Klasse; CSS: `.refresh-catalog-card.spinning .tools-row-icon svg { animation: spin ... }`
- **Click:** Event-Delegation auf `folderGrid` via `.refresh-catalog-card`-Selektor → `refreshCatalog()`
- **Styling:** Gedämpfte Optik (gestrichelte Border, transparent); Square 40×40px, `margin-right: 6px`

### Split-Pill im Header (Tools-Modus-Toggle)

Die `tools-pill` im Seiten-`<header>` ist jetzt ein **zweiteiliger Split-Pill** (`#tools-pill-wrap`):

- **Linker Teil** `#tools-pill` (.tools-pill): "Tools"-Text → öffnet das Tools-Panel (unverändertes Verhalten)
- **Rechter Teil** `#tools-pill-toggle` (.tools-pill-toggle): Kleiner Dot-Indicator-Button → togglet den Tool-Modus **direkt, ohne das Panel zu öffnen**
  - Inaktiv: hohler Kreis (CSS `::before`)
  - Aktiv (`.active`): gefüllter Kreis in Akzentfarbe
  - `e.stopPropagation()` verhindert Bubbling zum linken Tools-Text
- **Wrap** `#tools-pill-wrap` (.tools-pill-wrap): Gemeinsame Border + Hover/`has-active`-Hervorhebung
- **Sync:** `_updateActivateBtn()` aktualisiert sowohl `#tools-activate-all` (Panel) als auch `#tools-pill-toggle` (Header-Split-Pill) — beide zeigen immer denselben Zustand
- **Click-Handler:** `_toolsPillToggle.addEventListener('click', ...)` — identische Toggle-Logik wie `#tools-activate-all`

### Inline-Ratings

Wenn aktiv, werden 5 klickbare Bewertungssterne (`.track-inline-rating`) rechts neben jedem Track-Item angezeigt. Gleichzeitig werden andere Track-Buttons (Download, Pin, Edit, Playlist, Queue) ausgeblendet, um Platz zu schaffen. Die Sterne nutzen dieselben `IC_STAR_FILLED`/`IC_STAR_EMPTY`-Icons und das gleiche `POST /api/<media>/rating`-API wie der Player-Rating im Player-Bar.

- **`renderInlineRating(t, idx)`** — generiert den HTML-String für die 5 Sterne pro Track
- **`setInlineRating(idx, stars)`** — sendet Rating an den Server, aktualisiert Sterne in-place, Toast-Feedback mit Undo
- **Event-Delegation:** Sterne-Clicks werden via `stopPropagation` abgefangen, um Playback-Trigger zu verhindern
- **DnD-Kompatibilität:** `.track-inline-rating-star` ist in den DnD-Exclusion-Selektoren enthalten

### Duplikat-Erkennung (Client-Side)

Rein client-seitige Erkennung von Duplikaten über die bereits geladene `allItems`-Liste. Kein zusätzlicher Backend-Endpoint nötig.

**Algorithmus:**
1. **`_normalizeStem(s)`** — JS-Port von `stem_identifier()` aus `audio/sanitize.py`: Normalisiert `feat.`/`prod.`/`vs.`-Varianten, entfernt Bitrate-Tags, URLs, Emojis, Official-Video-Marker, trimmt Leerzeichen, lowercased.
2. **`_dupeKey(item)`** — Erzeugt stabilen Key aus **Artist + Titel**: Strippt zuerst Download-Duplikat-Suffixe (`_2`, `(2)`, `-2`, `_copy`, `(kopie)` etc.), dann splittet normalisierten Titel an Trennzeichen (`feat.`, `prod.`, `vs.`, `-`, `,`, `&`, Klammern), entfernt aggressiv Musik-Keywords (Remix, Mix, Version, Edit, Remaster, Live, Acoustic, etc.), strippt Non-Word-Chars, filtert Parts ≤ 2 Zeichen, sortiert und joined zu stabilem Key. **Artist-Prefix:** Der normalisierte `item.artist` (>2 Zeichen) wird als `artist::titleKey` vorangestellt, sodass verschiedene Interpreten mit gleichem Titel (z.B. "Blümchen - Nur Geträumt" vs. "Nena - Nur Geträumt") NICHT als Duplikate erkannt werden.
3. **`_buildDuplicateMap()`** — Iteriert einmal über `allItems`, baut `Map<dupeKey, [itemIndex, ...]>`, filtert auf Gruppen mit `length > 1`. Speichert zusätzlich `_dupePaths` (Set aller `relative_path`-Strings) für O(1)-Lookup beim Rendering.
4. **Cache-Invalidierung:** `_invalidateDupeMap()` wird bei jedem `allItems`-Replacement aufgerufen (Background-Refresh, Initial-Catalog-Load, Explicit-Refresh, File-Delete, File-Move). Lazy Re-Build beim nächsten Zugriff. `renderTracks()` ruft `_ensureDupeMap()` auf, wenn `_toolState.duplicates` aktiv ist — dadurch sind Badges sofort beim ersten Rendering und nach Löschvorgängen stabil sichtbar.

**UI-Elemente:**
- **`.dupe-badge`** — kleines orangenes Pill-Badge neben dem Track-Titel; via CSS `body.tool-show-duplicates .dupe-badge { display:inline-flex }` gesteuert. Enthält den Text „Duplikat" und bei Duplikaten den Trash-Button (`.track-delete-btn`).
- **Dupe-Show-Link** — Link unter dem Toggle im Tools-Panel (`"N Duplikat-Gruppen gefunden — anzeigen"`), öffnet das Duplikat-Panel.
- **Duplikat-Panel** — Modal-Dialog (`.dupe-panel-backdrop` + `.dupe-panel`) mit Gruppenübersicht: pro Gruppe Header (Titel + Anzahl), pro Item Thumbnail, Titel, Ordner-Pfad, **Metadaten-Zeile** (Länge · kbps · Dateigröße · Datum). Click navigiert zum Ordner und spielt den Track ab.
- **Metadaten im Dupe-Panel** — Jedes Duplikat-Item zeigt eine `.dupe-group-item-meta`-Zeile mit formatierter Wiedergabelänge (`_fmtDuration`), Bitrate in kbps, Dateigröße (`_fmtFileSize`) und Änderungsdatum (`_fmtDate`). Alle Werte werden aus den neuen `MediaItem`-Feldern `duration`, `bitrate`, `file_size`, `mtime` gelesen. Fehlende Werte (0) werden ausgeblendet.
- **`MediaItem` neue Felder** — `file_size: int = 0` (Bytes), `duration: float = 0.0` (Sekunden), `bitrate: int = 0` (kbps). Werden in Audio- und Video-Catalog befüllt (Audio: mutagen `info.length`/`info.bitrate` via `get_audio_file_info()`; Video: `_read_media_info_fast()` incl. Metadata-Cache). Vorbereitung für konfigurierbare Anzeige in der normalen Ansicht (spätere Erweiterung).
- **"Alle Duplikate abspielen"** — `.dupe-panel-play-all` Button im Panel. `playDuplicates()` sammelt alle Items aus `_dupeMap`-Gruppen, schließt das Panel und zeigt sie als virtuelle Playlist (`_currentPlaylistId = '__duplicates__'`). Header zeigt "Duplikate (N Gruppen)". Items sind nach Dupe-Gruppen geordnet, sodass zusammengehörige Duplikate nacheinander gespielt werden.
- **Trash-Button (Panel)** — Pro Duplikat-Item ein `.dupe-trash-btn` (Mülleimer-Icon `IC_TRASH`/`SVG_TRASH`), nur im Duplikat-Panel sichtbar. Click öffnet `confirm()`-Dialog, bei Bestätigung wird die Datei per Soft-Delete in den Papierkorb verschoben.
- **Inline-Delete-Button** — `.track-delete-btn` (kleines Mülleimer-Icon `IC_TRASH`) sitzt direkt innerhalb der `.dupe-badge`-Pill in `renderTracks()`. Da die Badge nur bei `body.tool-show-duplicates` sichtbar ist, braucht der Button keine eigene Visibility-Regel. Click löst `_deleteTrackFromList(filteredIdx)` aus.

### Duplikat-Löschung (Soft-Delete)

Ermöglicht das Löschen einzelner Duplikat-Dateien direkt aus dem Duplikat-Panel. Dateien werden nie hart gelöscht, sondern per Soft-Delete in das Trash-Verzeichnis (`HOMETOOLS_DELETE_DIR`, Default: `~/Music/DELETE_ME`) verschoben.

**Backend:**
- **`POST /api/audio/delete-file`** in `audio/server.py`: Body `{ "path": "Folder/song.mp3" }`. Validiert Pfad via `resolve_audio_path()`, verschiebt via `attention_delete_files()` (Soft-Delete), loggt `file_delete`-AuditEntry, invalidiert IndexCache. Returns `{ "ok": true, "entry_id": "..." }`.
- **`POST /api/video/delete-file`** in `video/server.py`: Identisch mit `resolve_video_path()` — Feature-Parity.
- **Audit-Log:** `log_file_delete()` in `audit_log.py`, Action `"file_delete"`, `undo_payload` enthält `original_path` und `trash_path`. Kein automatisches Undo im Audit-Panel (Datei manuell aus Trash wiederherstellbar).

**Frontend (JS in `server_utils.py`):**
- **`IC_TRASH`** — JS-Variable mit SVG-Trash-Icon (aus `SVG_TRASH`).
- **`DELETE_API_PATH`** — JS-Variable abgeleitet aus `api_path` (Pattern wie `MOVE_API_PATH`).
- **`_deleteDuplicateFile(allIndex)`** — `confirm()`-Dialog, dann `fetch(DELETE_API_PATH, {method:'POST', body: {path}})`. Bei Erfolg: `allItems[allIndex]._deleted = true` (kein `splice`!), `_invalidateDupeMap()`, `_invalidateFolderCache()`, `showToast()`, `applyFilter()` + `openDupePanel()`. Item bleibt in `allItems`, Dupe-Gruppe bleibt sichtbar. Playback-aware: erkennt ob der gelöschte Track aktuell spielt und springt ggf. zum nächsten.
- **`_deleteTrackFromList(filteredIdx)`** — Wie `_deleteDuplicateFile`, aber nutzt `filteredItems[idx]`. Findet das Item per `relative_path` in `allItems` und setzt `._deleted = true`. Re-render via `applyFilter()`.
- **`.dupe-trash-btn`** — Icon-Button mit `stopPropagation()` (verhindert Click-to-Play des Parent-Items). Nur für nicht-gelöschte Items gerendert (`._deleted` → Badge statt Button). CSS: transparent, rot-auf-hover.
- **`.track-delete-btn`** — Inline-Delete-Button in der Track-Liste, nur für Duplikate gerendert.

**Ghost-Anzeige nach Löschung:**
- Gelöschte Items bleiben mit `._deleted = true` in `allItems` und fließen durch `applyFilter()`.
- `renderTracks()`: `_deleted`-Items gehören NICHT zu `filteredItems` (= nicht abspielbar). Sie werden als separate Ghost-Zeile in `displayTracks` re-injiziert (identisches Muster wie `_movedTo`-Ghosts).
- Ghost-Zeile hat Klasse `.track-item--deleted`: ausgegraut (`opacity: 0.35`), `pointer-events: none`, Titel durchgestrichen, **× statt Numbering**, rotes "Gelöscht"-Badge.
- Der Track-Zähler zeigt `(N gelöscht)` wenn gelöschte Items vorhanden sind.
- `applyFilter()`: `_deleted`-Items werden durch alle Filter (Threshold, Quick-Filter, Text) durchgelassen, damit sie immer sichtbar bleiben.
- Im Duplikat-Panel: gelöschte Items haben Klasse `.dupe-group-item--deleted` (ausgegraut, `pointer-events: none`, Titel durchgestrichen, rotes Badge im Titel). Kein Trash-Button, kein Click-to-Play. Die Gruppe bleibt sichtbar (beide Items: gelöschtes + überlebendes), bis die Seite neu geladen wird.

**Design-Prinzipien:**
1. **Nur Duplikate löschbar** — Kein allgemeiner Delete-Button in der UI. Trash im Duplikat-Panel und als Inline-Button (`.track-delete-btn`) in der Track-Liste, nur für als Duplikat erkannte Items gerendert. Soft-Delete via `attention_delete_files()`, Bestätigung via `confirm()`.
2. **Soft-Delete** — Datei wird verschoben, nie gelöscht. Trash-Verzeichnis konfigurierbar.
3. **Bestätigung erforderlich** — `confirm()`-Dialog vor jeder Löschung.
4. **Feature-Parity** — Beide Server (Audio + Video) haben den Endpoint.
5. **Session-Sichtbarkeit** — Gelöschte Items bleiben bis zum nächsten Page-Reload sichtbar (Ghost-Zeile). Nach Reload ist das Item weg (Backend hat es aus dem Index entfernt).

### Dateien verschieben (File Mover)

Inline-Widget zum Verschieben von Audio-Dateien in einen anderen Ordner der Bibliothek. Kombiniert Schnellwahl mit Vollauswahl.

**Backend:**
- **`POST /api/audio/move-file`** in `audio/server.py`: Body `{ "path": "OLD/song.mp3", "target_folder": "NEW" }`. Validiert Quell-/Zielpfad, prüft Traversal-Schutz, verhindert Überschreiben, verschiebt via `shutil.move`, loggt `file_move`-AuditEntry, invalidiert IndexCache. Returns `{ "ok": true, "new_path": "NEW/song.mp3", "entry_id": "..." }`.
- **`GET /api/audio/folders`** in `audio/server.py`: Gibt alle Top-Level-Ordnernamen als `{ "folders": [...] }` zurück.
- **Audit-Log:** `log_file_move()` in `audit_log.py`, Action `"file_move"`, undo_payload enthält `old_path` und `new_path` für Rück-Verschiebung.
- **Undo:** Im `audio_audit_undo()`-Handler wird `file_move` unterstützt: Datei wird von `new_path` zurück nach `old_path` verschoben.

**Frontend (JS in `server_utils.py`):**
- **`_getRecentMoveTargets()`** — Liest die letzten 4 Zielordner aus `localStorage` Key `ht-move-recent`.
- **`_saveRecentMoveTarget(folder)`** — Speichert einen Ordner als MRU-Eintrag (max. 4, neuester zuerst).
- **`_getAllFolders()`** — Berechnet alle Top-Level-Ordner aus `allItems` (lazy, mit `_allFoldersCache`). Wird bei `allItems`-Replacement invalidiert via `_invalidateFolderCache()`.
- **`renderMoveWidget(t, idx)`** — Generiert pro Track: (1) aktueller Ordner als farbiges Tag, (2) 2×2-Grid der letzten 4 Ordner als Quick-Pick-Buttons, (3) `<select>` Dropdown mit allen Ordnern.
- **`moveFileToFolder(idx, targetFolder)`** — Sendet `POST /api/audio/move-file`, aktualisiert `allItems` in-place (neuer `relative_path`, `stream_url`, `artist`), invalidiert Caches, rendert View neu.

**CSS:**
- `.track-move-widget` — `display:none` default, via `body.tool-show-file-mover .track-move-widget { display:flex }` sichtbar.
- Wenn File-Mover aktiv, werden andere Track-Buttons ausgeblendet (analog Inline-Ratings).
- `.move-current-folder` — grüner Tag mit aktuellem Ordnernamen.
- `.move-quick-grid` — 2×2 CSS-Grid für Schnellwahl-Buttons.
- `.move-quick-btn` — kompakter Button pro MRU-Ordner, `.is-current` bei aktuellem Ordner (disabled, dimmed).
- `.move-folder-select` — Dropdown mit allen Ordnern.

### Designregeln

1. **Shared-Core-UI** — Tools-Panel lebt in `server_utils.py`, nicht pro Server dupliziert
2. **Keine Feature-Flags nötig** — Tools sind client-seitig (localStorage), kein Server-Flag
3. **CSS-only Visibility** — `body`-Klassen steuern Sichtbarkeit via CSS, kein JS-DOM-Manipulation pro Element
4. **Inline-Ratings exklusiv** — Wenn aktiv, werden andere Track-Buttons ausgeblendet (kein Platzproblem auf Mobile)
5. **State persistent** — `ht-tools` in localStorage, überlebt Page-Reloads und Server-Restarts
6. **Duplikat-Erkennung rein client-seitig** — Kein zusätzlicher Backend-Endpoint, keine Server-Last. Dupe-Map wird lazy berechnet und bei Catalog-Wechsel invalidiert.
7. **File-Mover exklusiv** — Wenn aktiv, werden andere Track-Buttons ausgeblendet (wie Inline-Ratings). MRU-Ordner in `localStorage`, Ordnerliste aus `allItems` gecached.
8. **Duplikat-Löschung nur für Duplikate** — Trash-Button im Duplikat-Panel und als Inline-Button (`.track-delete-btn`) in der Track-Liste, nur für als Duplikat erkannte Items gerendert. Soft-Delete via `attention_delete_files()`, Bestätigung via `confirm()`.

## iOS-kompatibler Video-Stream (Faststart-Cache)

### Problem

iOS Safari erfordert zwingend HTTP Range Requests (`Accept-Ranges: bytes` + `206 Partial Content`), um Video-Playback zu starten. FastAPI's `StreamingResponse` unterstützt diese nicht nativ. MP4-Dateien, deren `moov`-Atom am Ende liegt (kein Faststart), wurden bisher on-the-fly per ffmpeg geremuxed — was auf iOS komplett stumm scheitert.

### Lösung

Für `.mp4`-Dateien ohne Faststart wird **einmalig eine gecachte Faststart-Kopie** im Shadow Cache erstellt (`ffmpeg -c copy -movflags +faststart`). Diese wird per `FileResponse` ausgeliefert, das Range Requests vollständig unterstützt. Für MKV/AVI/andere Container bleibt der bestehende `StreamingResponse`-Pfad (fragmented MP4) als Fallback aktiv.

### Module

- `streaming/core/remux.py` — `ensure_faststart_cache()`, `get_faststart_cache_path()`
- `streaming/video/server.py` — `GET /video/stream` entscheidet zwischen Cache-Pfad und Remux-Pfad

### Cache-Pfad

```
{cache_dir}/video/{relative_path}.faststart.mp4
```

### Entscheidungslogik in `/video/stream`

1. `.mp4` + Faststart vorhanden → `FileResponse` (direkt, Range-konform)
2. `.mp4` + **kein** Faststart → `ensure_faststart_cache()` → `FileResponse` (Cache, Range-konform)  
   Fallback wenn ffmpeg fehlt: `StreamingResponse` (wie vorher)
3. Nicht-native Container (MKV, AVI…) → **gecachte Remux-/Transcode-MP4** (siehe unten) → `FileResponse`; nur als Fallback `remux_stream()` → `StreamingResponse`

### Nicht-native Container: Range-fähiger Remux-Cache (2026-06-12)

**Problem:** `.avi`/`.mkv`/`.flv` (`needs_remux`) wurden bisher ausschließlich über `StreamingResponse(remux_stream())` ausgeliefert — ein Live-ffmpeg-Pipe **ohne** HTTP-Range-Support. iOS Safari (und mobile Browser allgemein) verweigern dann die Wiedergabe. **Symptom:** MP4-Serien laufen am Handy, `.avi`-Serien „laden nicht".

**Lösung:** Wie beim Faststart-Cache wird eine **vollständige, fast-start-fähige MP4-Kopie** im Shadow-Cache erzeugt und per `FileResponse` (Range/206) ausgeliefert.

- **Module:** `remux.py` — `ensure_remux_cache()`, `get_remux_cache_path()`, `start_background_remux()` (einzelne Datei, dedupliziert), `start_background_remux_generation()` (Batch-Daemon).
- **Cache-Pfad:** `{cache_dir}/video/{relative_path}.remux.mp4`.
- **copy vs. transcode:** `can_copy_codecs()` entscheidet — H.264-in-MKV/FLV → `-c copy +faststart` (Sekunden); XviD-`.avi` → Transcode `libx264/aac +faststart` (CPU-intensiv).
- **`/video/stream`-Logik bei `needs_remux`:** (1) frischer Remux-Cache → `FileResponse`; (2) sonst `copyable` → synchroner Copy-Remux → `FileResponse`; (3) sonst (Transcode nötig) → Hintergrund-Transcode anstoßen + für **diesen** Request `StreamingResponse`-Fallback (Desktop spielt sofort; Handy nach Cache-Fertigstellung erneut antippen).
- **Pre-Transcode beim Start (opt-in):** `collect_remux_work()` + `start_background_remux_generation()` bauen die Caches im Hintergrund vor (ein ffmpeg gleichzeitig), gesteuert via `HOMETOOLS_PRETRANSCODE` (**Default aus**, benötigt ffmpeg). MTime-Invalidierung, exception-safe, blockiert Start/Katalog nie. ⚠️ Aktiviert transkodiert es die **gesamte** Bibliothek → der Shadow-Cache kann zweistellige GB erreichen; standardmäßig erfolgt die Transkodierung daher **on-demand** beim Abspielen (`start_background_remux`), sodass der Cache proportional zum Geschauten bleibt.

> **HTTPS / Brave-Hinweis:** Eine „SSL-Fehlermeldung" in Brave kommt von dessen „Always use secure connections"/HTTPS-Upgrade, das den HTTP-Server auf `https://` umbiegt. Lokal ohne TLS ist das ein Client-Setting (für die Server-IP deaktivieren). Server-seitiges optionales HTTPS bleibt Backlog.

### Designregeln

- Faststart-Konvertierung ist **-c copy** (keine Neukodierung), dauert Sekunden auch für große Dateien.
- MTime-basierte Invalidierung: Cache wird neu erzeugt, wenn die Quelldatei neuer ist.
- `ensure_faststart_cache()` ist idempotent, thread-safe über tmp→rename-Pattern.
- Fehler (ffmpeg fehlt, Timeout, Disk-Fehler) werden geloggt; die Funktion gibt `None` zurück und der Aufrufer fällt auf den alten Remux-Pfad zurück — kein Absturz.

### Temp-File-Hygiene für Remux/Faststart-Caches (2026-06-15)

**Problem:** `ensure_remux_cache()` und `ensure_faststart_cache()` schreiben zuerst in eine `*.tmp.mp4`-Datei und benennen sie nach Erfolg um (atomares tmp→rename-Pattern). Der partielle Temp-File wurde aber **nur** im `returncode != 0`-Zweig gelöscht. Bei einem **Timeout** (Transcode-Timeout bis zu 7200 s!), beim Kill des Daemon-Threads beim Interpreter-Shutdown oder bei einer unerwarteten Exception (z. B. Disk-Full während des `rename`) blieb die halb geschriebene Datei zurück. Bei knappem Speicher scheiterten viele Transcodes mitten im Schreiben → **angesammelte, teils mehrere GB große `.tmp.mp4`-Leichen** im Shadow-Cache.

**Lösung:**
- Beide Funktionen kapseln die Temp-Datei-Behandlung in `try/finally`: `tmp_path` wird nach erfolgreichem `rename` auf `None` gesetzt; das `finally` entfernt jede noch existierende Temp-Datei (`unlink(missing_ok=True)`), unabhängig vom Exit-Pfad. Exception-safe.
- Neue `cleanup_stale_remux_tmp(cache_dir)`-Funktion durchsucht `{cache_dir}/video/**/*.tmp.mp4` und entfernt Altlasten aus der Zeit vor diesem Fix. Best-effort, wirft nie.
- Beim Video-Server-Start läuft die Bereinigung einmalig in einem Daemon-Thread (`video-remux-tmp-sweep`), blockiert Start/Katalog nie. Fertige `*.remux.mp4`/`*.faststart.mp4`-Caches bleiben unangetastet.


### Background-Prewarm (2026-05-29)

Der erste Stream-Request einer großen MP4-Datei ohne Faststart blockierte
mehrere Sekunden im Request-Handler, weil `ensure_faststart_cache()` synchron
lief (besonders spürbar bei Serien-Episoden auf langsamem NAS-Storage).
`thumbnailer._prewarm_faststart_if_needed()` läuft jetzt innerhalb des
Hintergrund-Thumbnail-Workers nach jeder erfolgreich erzeugten Video-Thumbnail
und baut die Faststart-Kopie proaktiv. Bedingungen für den Lauf:

1. Datei ist Browser-nativ (kein Remux nötig) und besitzt **kein** moov-at-start.
2. Cache fehlt oder ist älter als die Quelldatei (mtime).
3. Quelldatei ≥ 8 MiB (kleinere Dateien bauen ohnehin sofort).

Best-Effort, exception-safe, blockiert weder den Server-Start noch den
Catalog-Scan. Zur Pflege via CLI siehe `make video-prewarm` /
`hometools stream-prewarm --server video --mode missing` — dort wird der
gleiche Worker explizit aufgerufen.

---

## UI-Layout-Änderungen: Suchleisten-Umstrukturierung (2026-05-15)

### Bibliotheks-Suchleiste (Global Search) im Header

Die globale Bibliotheks-Suchleiste (`#global-search-input`) wurde aus dem `#folder-filter-bar`-Container (der dynamisch bestückt wurde) in den `<header>` direkt verschoben. Sie erscheint dauerhaft als letztes Element im Header-Flex-Container, rechts ausgerichtet.

- **CSS-Klasse:** `.header-search` — `flex: 0 1 200px`, `border-radius: 20px`, Pill-Form
- **Sichtbarkeit:** Gesteuert über `view-hidden`-Klasse. `initGlobalSearch()` entfernt die Klasse (zeigt an). `_hideGlobalSearch()` fügt sie wieder hinzu (versteckt).
- **Event-Wiring:** Nur einmalig via `_globalSearchListenersInit`-Flag — verhindert doppelte Listener-Registrierung.
- **`#folder-filter-bar`:** Bleibt im DOM (Tests prüfen `id="folder-filter-bar"`), aber immer `hidden`. Kein HTML-Inhalt mehr.

### Track-Count in der Filter-Bar

Der `<span id="track-count">` wurde aus dem `<header>` in die `.filter-bar` (Listen-Suchleiste) verschoben — als letztes Element mit `margin-left: auto`. Er zeigt die Anzahl der gefilterten Tracks direkt neben den Suchfiltern an.

### Filter-Bar Scroll-Reveal (erscheint beim Hochscrollen)

Die Listen-Suchleiste (`.filter-bar`) ist standardmäßig verborgen, wenn eine Playlist/Ordner-Ansicht geöffnet wird, und erscheint erst beim Hochscrollen.

**Mechanismus:**
1. Wenn `filterBar.classList.remove('view-hidden')` aufgerufen wird (in `showPlaylist`, `showUserPlaylistView`, `playDuplicates`), wird **sofort** `filterBar.classList.add('fb-scroll-hidden')` gesetzt — damit startet die Filter-Bar versteckt.
2. `_initFilterBarScrollReveal()` registriert (einmalig, via `_fbScrollInitDone`-Flag) einen `scroll`-EventListener auf `#track-view`.
3. Der Listener: wenn `scrollTop < 10` oder der User nach oben scrollt → `fb-scroll-hidden` entfernen (einblenden). Wenn nach unten gescrollt wird → `fb-scroll-hidden` hinzufügen (ausblenden).

**CSS:**
```css
.filter-bar {
  overflow: hidden;
  max-height: 100px;
  transition: max-height 0.22s ease, padding-top 0.22s ease, padding-bottom 0.22s ease, border-bottom-width 0.22s ease;
}
.filter-bar.fb-scroll-hidden {
  max-height: 0; padding-top: 0; padding-bottom: 0; border-bottom-width: 0;
}
```

**Alle Eintrittspunkte** (die die Filter-Bar sichtbar machen) rufen jetzt auch `_hideGlobalSearch()` auf und setzen `fb-scroll-hidden`, damit der Zustand konsistent ist.

---

## Waveform-Peak-Caching (Shadow Cache)

**Module:** `streaming/core/waveform.py`, `streaming/audio/server.py` (Endpunkt)

### Zweck

256 normalisierte Amplitude-Peak-Werte pro Kanal (L + R) werden via ffmpeg aus Audio-Dateien extrahiert und im Shadow-Cache gespeichert. Das ermöglicht eine stereo-bewusste Wellenform-Visualisierung im Classic-Mode Progress-Bar ohne client-seitiges Audio-Decoding.

### Pfad-Konvention

`<cache_dir>/audio/<relative_path>.waveform.json` — spiegelt die Library-Struktur exakt wider, analog zu Thumbnails (`.thumb.jpg`).

### Extraction (Stereo)

`extract_waveform_peaks(media_path, segments=256)` dekodiert via ffmpeg (`-ac 2 -f f32le -ar 1000 pipe:1`), deinterleaved die L/R-Samples (`all_samples[0::2]` / `all_samples[1::2]`), berechnet Peak-Absolutwert pro Segment-Block, normalisiert **gemeinsam** (relative Lautstärke zwischen Kanälen bleibt erhalten). Mono-Quellen werden von ffmpeg automatisch auf Stereo hochgemischt (beide Kanäle identisch). Gibt `(peaks_l, peaks_r) | None` zurück.

### Cache-Format

```json
{"peaks_l": [...256 floats 0.0–1.0...], "peaks_r": [...256 floats...], "segments": 256}
```

Backward-Kompatibilität: alte Caches mit nur `"peaks"`-Key → Client rendert Mono-Fallback.

### Cache-Lebenszyklus

- **MTime-Invalidierung:** Nur regeneriert wenn `source.mtime > cache.mtime`.
- **Background-Only:** `start_background_waveform_generation(items)` → Daemon-Thread `waveform-bg`.
- **On-Demand-Fallback:** `GET /api/audio/waveform?path=...` generiert synchron wenn Cache kalt ist.

### API-Endpunkt

`GET /api/audio/waveform?path=<relative_path>`
- Response: `{"peaks_l": [...], "peaks_r": [...], "segments": 256}`
- 404: Datei nicht im Cache + Generierung fehlgeschlagen
- 400: leerer `path`-Parameter

### Frontend-Integration (Classic-Modus)

- `var waveformData = null` (L-Kanal oder Legacy-Mono-Peaks)
- `var waveformDataR = null` (R-Kanal; `null` = Mono-Modus)
- `generateWaveform(url, relativePath)` fetcht `/api/audio/waveform`, befüllt beide Variablen
- `drawWaveform(progress)` zeichnet drei Zustände:

| Zustand | Layer 1 | Layer 2 |
|---------|---------|---------|
| **Stereo** | 1px weisse Mittellinie | L wächst nach oben, R nach unten; gespielt = Akzentfarbe α0.72, ungespielt = #999 α0.28 |
| **Mono** | 5px Progressbar (grau/Akzent) | Zentrierte Balken, weiss semi-transparent |
| **Leer** | 5px Progressbar | — |

Layer 3 (immer): weißer Playhead-Dot am aktuellen Fortschritt.

---

## `server_utils` Paket-Split

**Modul:** `streaming/core/server_utils/` (Paket, vorher monolithische Datei `server_utils.py` mit ~9000 Zeilen)

Die UI-Generierung lebte ursprünglich in einer einzigen `server_utils.py`-Datei,
die durch Wachstum auf >9000 Zeilen für Agent-gestützte Entwicklung
(Kontextfenster-Druck, Edit-Risiko, Navigations-Latenz) zum Problem wurde.
Die Datei wurde in ein Paket aufgeteilt — **rein strukturell, keine
Verhaltensänderung**.

### Struktur

| Datei | Inhalt | Zweck |
|-------|--------|-------|
| `__init__.py` | Re-Exports, `logger` | Backward-Compatible Public-API |
| `_svg.py` | 37 `SVG_*`-Konstanten (Icons + Flaggen) | Zentrale Icon-Bibliothek |
| `_css.py` | `render_base_css` | Komplettes dark-theme CSS als Python-String |
| `_player_js.py` | `render_player_js` | Großer JS-Generator (Player + Listen + Modals) |
| `_html.py` | `render_media_page` | Einziges HTML-Skelett für Audio + Video |
| `_pwa.py` | `render_pwa_manifest`, `render_pwa_service_worker`, `render_pwa_icon_svg`, `render_pwa_icon_png`, `render_pwa_head_tags` | PWA-Assets |
| `_audit.py` | `render_audit_panel_html` | Audit-Log-Panel |
| `_library.py` | `build_index_status_payload`, `check_library_accessible`, `render_error_page` | Status- & Fehlerseiten |
| `_paths.py` | `resolve_media_path`, `safe_resolve` | Pfad-Validierung gegen Traversal |

### Backward-Compatibility

`__init__.py` re-exportiert sämtliche öffentlichen Symbole. Externe Importe
wie `from hometools.streaming.core.server_utils import render_player_js`
oder `from hometools.streaming.core.server_utils import SVG_PLAY`
funktionieren **unverändert** — kein Aufruferkode wurde angepasst.

### Designregeln

- **Keine Quer-Imports zwischen den Submodulen außer für `_svg`.** `_player_js`
  importiert `SVG_*`-Konstanten via `from ._svg import ...`. Sonst keine
  Abhängigkeiten zwischen den Submodulen.
- **`__init__.py` enthält keine Logik**, nur Re-Exports. Wenn neue Helpers
  hinzukommen, gehören sie in eines der Submodule (oder ein neues).
- **Public-API-Drift vermeiden:** Wer ein neues Public-Symbol exportieren
  will, muss es explizit in `__init__.py` ergänzen.
- **Bestehende Architektur-Regeln (insb. Regel 13 SVG-Icons) gelten weiterhin.**
  Neue `SVG_*`-Konstanten kommen in `_svg.py` (nicht in `_player_js.py`).
- Architecture-Doku-Verweise auf `server_utils.py` bleiben gültig (das Paket
  trägt denselben Namen wie die alte Datei) und werden nicht massenhaft
  umgeschrieben.

## Library-Scan (`streaming/core/library_scan.py`)

Read-only Bibliotheks-Analyse für den CLI-Befehl `hometools scan-library`.

### Zweck

Kein ffprobe, keine External-APIs — rein dateisystembasiert. Hilft beim Erkennen
von Organisations-Problemen in der Videobibliothek, die durch `hometools_overrides.yaml`
oder Ordnerumbenennung gelöst werden könnten.

### Checks (Video)

| Check-Code          | Schwere     | Beschreibung |
|---------------------|-------------|--------------|
| `episode_naming`    | `warning`   | Ordner mit ≥ 4 Videodateien, aber < 50 % enthalten S##E##-Muster. Hinweis auf `generate-overrides`. |
| `oversized_folder`  | `info`      | Direktordner mit > 30 Videodateien ohne Unterordner-Struktur. |
| `untagged_language` | `info`      | Top-Level-Ordner ohne Sprach-Tag im Namen UND ohne `language`/`language_group`-Override. |

### Checks (Audio)

| Check-Code          | Schwere     | Beschreibung |
|---------------------|-------------|--------------|
| `oversized_folder`  | `info`      | Direktordner mit > 100 Audiodateien ohne Unterordner-Struktur. |

### API

```python
report = scan_video_library(library_dir, overrides=None)
report = scan_audio_library(library_dir)
```

`ScanReport.to_dict()` liefert JSON-serialisierbares Dict. `--fail-on-warning` gibt Exit-Code 1.

### CLI

```bash
hometools scan-library [--media video|audio] [--library-dir PATH] [--json] [--fail-on-warning]
```

### Designregeln

- Niemals originale Mediendateien modifizieren.
- Exception Safety: alle Public-Funktionen geben bei Fehler leere `ScanReport`-Instanz zurück.
- Overrides können pre-geladen übergeben werden (Effizienz-Optimierung für Tests und Batches).
- Schwellen (`oversized_threshold`, `min_files`, `min_ratio`) sind keyword-only Parameter
  für testbare Konfigurierbarkeit.

## Video-Server UI-Anpassungen

Der Video-Server unterscheidet sich an zwei Stellen bewusst vom Audio-Server.
Beide Anpassungen erfolgen im gemeinsamen `_player_js.py` über die Laufzeit-
flag `_isVideo = (ITEM_NOUN === 'video')`, sodass kein duplizierter Code in
`streaming/video/` entsteht.

### Tools-Row ohne Playlist-Aktionen

Auf dem Root-Screen des Video-Servers werden die Tools-Row-Karten
„Neue Playlist…", „Intelligente Playlist…" und „Titel" nicht gerendert.
Begründung: Playlists und Smart Playlists sind im Video-Streaming aktuell
ohne Mehrwert (keine Queue-Mechanik wie im Audio-Player), und „Titel" als
flache Liste aller Videos ist redundant zur Ordneransicht.

Die Karten existieren weiterhin im Audio-Server.  Der Block wird über
`if (isRoot && PLAYLISTS_ENABLED && !_isVideo)` geschützt.  Der „Neu laden"-
Button und „Downloaded"-Karte bleiben auch auf Video sichtbar.

### Sprachflagge am Folder-Card

Für Video-Folder wird **immer** eine einzelne Sprachflagge gerendert — auch
für mono-linguale Ordner ohne erkannte Sprache, die dann auf
`DEFAULT_LANG` zurückfallen.  Position: feste obere rechte Ecke der Karte
über die neue CSS-Klasse `.folder-lang-corner` (absolute Positionierung,
halbtransparenter dunkler Background damit die Flagge auf hellen Thumbnails
lesbar bleibt).

Verhalten:

- **Mono-Lingual** (`!hasVariants`): Flagge = `f.languages[0] || DEFAULT_LANG`,
  ggf. mit Sub-Sprache als Composite-Flagge.  Der bisherige inline
  `langBadges`-Span neben dem Folder-Namen wird auf Video unterdrückt, um
  keine doppelte Anzeige zu erzeugen.
- **Multi-Variant** (`hasVariants`): keine Eck-Flagge — die Variant-Flag-
  Buttons im `folder-count`-Bereich übernehmen die Sprachanzeige (jede
  Variante als klickbarer Button).

Audio-Server bleibt unverändert: die bisherigen kleinen Inline-Badges neben
dem Folder-Namen werden weiterhin nur bei tatsächlich erkannten Sprachen
gezeigt.


### iOS-Background-Playback (Auto-PiP)

Das `<video>`-Element trägt das Attribut `autopictureinpicture`.  Auf iOS
Safari (≥ 14) schiebt das System das Video beim Backgrounden der App
(Home-Button / App-Switcher) automatisch in das System-PiP-Overlay — ohne
User-Geste, ohne expliziten Aufruf.

**Voraussetzung:** Das Video muss zum Zeitpunkt von `visibilitychange`
*noch laufen*.  Der `visibilitychange`-Handler in `_player_js.py` darf
auf iOS daher **nicht** `player.pause()` aufrufen, da Safari die
PiP-Transition sonst abbricht (Regression sichtbar ab iOS 17).

Implementierung:

- iOS-Detection via UA + `MacIntel + maxTouchPoints>1` (`isIOS`-Flag).
- Bei `document.hidden && wasPlaying`:
  - PiP-Status prüfen: `document.pictureInPictureElement === player`
    bzw. `player.webkitPresentationMode === 'picture-in-picture'`.
  - `player.pause()` nur auf **Nicht-iOS** und nur wenn **nicht** in PiP.
  - Background-Audio-Mirror nur aktivieren wenn **nicht** in PiP
    (sonst Doppel-Ton parallel zum PiP-Video).
- Beim Zurückkehren in den Vordergrund: PiP explizit beenden,
  Video-Position aus Mirror synchronisieren, Mirror stummschalten.

Desktop-Verhalten unverändert: pause + bg-audio-mirror verhindert
Doppel-Ton bei Tab-Wechsel.


## Cast-Button (HTML5 Remote Playback API)

Im Video-Overlay-Header rechts neben dem Fullscreen-Button platzierter
`#video-cast-btn` (Icon `SVG_CAST`).  Erlaubt das Streamen des laufenden
`<video>` auf jedes erreichbare Cast-Ziel im Netzwerk — auf Philips
Android TV (Chromecast-built-in) oder Apple TV (AirPlay).

**Implementierung:** ausschließlich Standard-Browser-APIs, kein Google-Cast-
SDK, keine App-ID, kein zusätzlicher Netzwerk-Code im Server.

| Browser                                  | API                                                      |
|------------------------------------------|----------------------------------------------------------|
| Chromium (Android-Chrome, Desktop-Chrome, Edge) | `player.remote.watchAvailability()` + `player.remote.prompt()` |
| iOS Safari                               | `webkitplaybacktargetavailabilitychanged` + `webkitShowPlaybackTargetPicker()` |
| Firefox / Safari (macOS) / WebViews ohne Support | Button bleibt `hidden` — keine Regression                 |

**Sichtbarkeit:** Der Button startet `hidden` und wird **nur** entblendet,
wenn der Browser ein Cast-Ziel im Netzwerk gefunden hat.  Verbindungs-
status (`connect`/`disconnect`-Events) setzt die CSS-Klasse `.active`
am Button.

**Designregeln:**

- Cast ist **video-only** — der Button ist nur im Video-Overlay vorhanden,
  da nur `<video>` die Remote Playback API hat.
- Server-Container muss für das Cast-Gerät **erreichbar** sein.  Bei VLAN-
  Trennung scheitert das Casting, auch wenn der Picker das Ziel anbietet.
  Workaround dokumentiert in `docs/docker.md` (`network_mode: host`).
- Keine Native-TV-App nötig.  Bedienung bleibt am Handy/Tablet, Wiedergabe
  läuft am TV.  Falls später erweiterte Steuerung (Queue, Lautstärke)
  gewünscht ist, kann das Google-Cast-SDK additiv geladen werden, ohne
  diesen Pfad zu brechen.


## Docker-Deployment

Multi-Stage-Image (Python 3.12-slim + ffmpeg + tini, Non-Root-User
`hometools` mit konfigurierbarer UID/GID via Build-Arg).  `docker-compose.yml`
startet pro Service einen eigenen Container vom gleichen Image:

| Service | Port | Command         | Library-Mount                                       |
|---------|------|-----------------|------------------------------------------------------|
| audio   | 8010 | `serve-audio`   | `${AUDIO_LIBRARY_PATH}:/media/audio:ro`              |
| video   | 8011 | `serve-video`   | `${VIDEO_LIBRARY_PATH}:/media/video:ro`              |
| channel | 8012 | `serve-channel` | `${VIDEO_LIBRARY_PATH}:/media/video:ro` + Schedule   |

Gemeinsame Named-Volumes `hometools-cache` und `hometools-audit` halten
Shadow-Cache (`/data/cache`) und Audit-Log (`/data/audit`) getrennt von
der Library und überleben Container-Rebuilds.

**Konfigurations-Mapping (`.env`):**

| `.env`-Variable          | Wirkt auf                                | Default          |
|--------------------------|------------------------------------------|------------------|
| `PUID`, `PGID`           | Build-Arg, Owner für `/data` und Prozess | `1000` / `1000`  |
| `AUDIO_LIBRARY_PATH`     | Host-Pfad → `/media/audio`               | **pflicht**      |
| `VIDEO_LIBRARY_PATH`     | Host-Pfad → `/media/video`               | **pflicht**      |
| `AUDIO_PORT`/`VIDEO_PORT`/`CHANNEL_PORT` | Port-Mapping auf Host       | `8010/8011/8012` |
| `HOMETOOLS_*`            | Direkt durchgereichte Server-Env-Vars    | wie im Image     |

**Designregeln:**

1. Mounts standardmäßig `:ro` — Write-Features (Rating-POPM, Tag-Edit,
   File-Move, Soft-Delete) erfordern bewussten Wechsel auf `rw`.
2. `HOMETOOLS_STREAM_HOST=0.0.0.0` ist im Image fixiert; Erreichbarkeit
   regelt das Host-Port-Mapping.
3. `HOMETOOLS_CACHE_DIR=/data/cache`, `HOMETOOLS_AUDIT_DIR=/data/audit`
   sind im Image fixiert — die Volumes folgen dieser Konvention.
4. ffmpeg/ffprobe sind Pflicht-Runtime-Deps (Faststart-Cache,
   Channel-Transcode, Waveforms, Thumbnails).  Image-Bau ohne ffmpeg
   würde Features still ausfallen lassen.
5. `tini` als PID 1 sorgt für saubere SIGTERM-Weiterleitung an uvicorn,
   damit `docker compose down` nicht in den Kill-Timeout läuft.
6. Healthcheck nutzt den existierenden `/health`-Endpoint via `HC_PORT`-
   Env-Variable je Container (audio = 8010, video = 8011, channel = 8012).
7. Tests werden über `.dockerignore` aus dem Build ausgeschlossen — das
   Runtime-Image enthält ausschließlich Produktcode.
8. `serve-all`-Variante steht als auskommentierter `all-in-one`-Service
   im Compose zur Verfügung, ist aber nicht Default (drei separate
   Container = sauberere Logs und Restarts).


## Global Search — Ordner-/Serien-Treffer (2026-05-29)

`globalSearch(needle)` in `streaming/core/server_utils/_player_js.py`
durchsucht zuerst alle Ordner-Pfade und zeigt passende Ordner (bei Video
typischerweise Serien-Titel) **vor** den einzelnen Tracks/Episoden an.

**Vorgehen:**
1. Iteriere alle `allItems`, splitte `relative_path` in Segmente, sammle
   jeden Pfad-Prefix, dessen Leaf-Segment (oder dessen `cleanFolderName()`)
   den Such-Begriff enthält.
2. Zähle Items unter jedem Folder-Prefix → `count`.
3. Sortiere: flache Tiefe zuerst, dann größere Count, dann alphabetisch.
4. `renderSearchResults(results, folderMatches)` rendert Ordner-Items
   (CSS-Klasse `.search-folder-item`, Folder-Icon, "Ordner"-Label,
   Klick → `navigateToSearchFolder(path)` → verlässt Search-Modus und
   navigiert in den Ordner) **vor** den Track-Items.

Header zeigt z. B. `"3 Ordner · 27 Videos"` statt nur Track-Count.

## Indexing-Toast — antippen zum Ausblenden (2026-05-29)

Die "Building index…"-Benachrichtigung (`.ht-indexing-toast`) verdeckte
auf schmalen Viewports die Header-Suchleiste. Lösung:

- **Auf Mobile** (`max-width: 600px`) positioniert per Media-Query an
  `bottom: calc(env(safe-area-inset-bottom) + 84px); right: 0.5rem;`
  also direkt über der Player-Bar.
- **Tap-to-dismiss:** `pointer-events: auto; cursor: pointer`, Click
  setzt `_indexToastDismissed = true`. Solange das Flag steht, ruft
  `showIndexingToast()` früh `return` — der Hintergrund-Poll
  (`scheduleBackgroundRefresh`) läuft weiter, zeigt aber nichts.
- **Reset:** `hideIndexingToast()` (Index ist fertig) setzt das Flag
  zurück → nächste Indexing-Runde zeigt den Toast wieder an.
