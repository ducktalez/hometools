# Implementation Plan

## Backlog — Medium

### Vite/TypeScript migration (in progress, Phase 1 done — 2026-07-30)

**Ziel:** `server_utils/_player_js.py` + `player_js/*.py` + `_css.py` +
`css/*.py` (aktuell ~8900 Zeilen JS/CSS als Python-String-Konkatenation)
schrittweise durch echte `.ts`/`.css`-Dateien ersetzen, gebaut mit Vite,
ausgeliefert von FastAPI als statische Assets. Backend (FastAPI, Katalog,
Sync, ...) bleibt unverändert — reine Frontend-Tooling-Migration.

**Phase 1 (done, 2026-07-30):** Scaffold unter
`src/hometools/streaming/core/webui/` (`package.json`, `vite.config.ts`,
`tsconfig.json`, `src/main.ts` mit `PlayerConfig`-Typ als Vertrag für das
künftige `<script id="ht-config">`-JSON-Blob). `npm run build` /
`npm run typecheck` laufen isoliert und grün, ohne dass Server-Code
angefasst wurde. `node_modules/`, `dist-typecheck/` und der Build-Output
(`../static/`) sind `.gitignore`-Einträge. Details + volle Migrationsschritte
→ `src/hometools/streaming/core/webui/README.md`.

**Phase 2 (done, 2026-07-30) — Config extraction (additive):** `_html.py` now
builds an `#ht-config` JSON `<script>` tag (`_render_player_config_json()`)
mirroring `PlayerConfig` in `main.ts`, embedded next to `#initial-data`.
**Not yet consumed** by `render_player_js()` — the existing flat vars
(`SHUFFLE_ENABLED`, `API_PATH`, ...) keep being generated exactly as before,
so all ~20 existing test call sites and `render_player_js()`'s signature are
untouched. Malformed `language_groups_json` degrades to `{}` instead of
crashing (`try/except` around `json.loads`). New tests:
`tests/test_streaming_player_ui.py::TestHtConfigJson` (4 cases: presence/
valid JSON, feature flags reflected, language groups parsed, malformed input
survives).

**Phase 3 (done — 2026-07-30) — Switch-over:** all of `render_player_js()`'s
former Python parameters are gone. Only `player_bar_style` remains (a
genuinely structural choice — waveform vs. classic emits different JS).
Everything else — `enable_shuffle`, `enable_repeat`, `enable_skip_intro`,
`enable_rating_write`, `min_rating`, `debug_filter`, `enable_recent`,
`enable_auto_resume`, `crossfade_duration`, `enable_metadata_edit`,
`enable_lyrics`, `enable_playlists`, `playlist_sync_interval_ms`,
`language_groups_json`/`default_language`, `item_noun`, `file_emoji`,
`api_path` — is read at runtime from `CFG` (parsed from `#ht-config`).

- **First three slices** (`enable_shuffle`, `enable_repeat`,
  `enable_skip_intro`) done incrementally with their own test fixes — see
  history below.
- **Remaining twelve variables done in one larger pass:** `enable_rating_write`,
  `min_rating`, `debug_filter`, `enable_recent`, `enable_auto_resume`,
  `crossfade_duration`, `enable_metadata_edit`, `enable_lyrics`,
  `enable_playlists`, `playlist_sync_interval_ms` (moved out of
  `render_library_tools_js(playlist_sync_interval_ms)` into
  `CFG.playlistSyncIntervalMs`, function now takes no params),
  `language_groups_json`/`default_language`, `item_noun`, `file_emoji`.
- **`api_path` fully migrated too** — the biggest structural change. Every
  derived endpoint path (`INTRO_API_PATH`, `RATING_API_PATH`,
  `AUDIT_UNDO_PATH`, `RECENT_API_PATH`, `METADATA_EDIT_PATH`,
  `LYRICS_API_PATH`, `PLAYLISTS_API_PATH`/`_VERSION_PATH`/`_SMART_PATH`,
  `FOLDER_ORDER_API_PATH`, `MOVE_API_PATH`, `DELETE_API_PATH`,
  `REVEAL_API_PATH`, `FOLDERS_API_PATH`, and classic-mode
  `WAVEFORM_API_PATH`) used to be built in Python via
  `api_path.rsplit("/", 1)[0] + "/xxx"`. All of these now use a single new
  JS helper `function _apiBase() { return API_PATH.split('/').slice(0, -1).join('/'); }`
  defined once near the top of the IIFE (right after `CFG` is parsed) —
  `var XXX_API_PATH = _apiBase() + '/xxx';`. `AUDIOBOOK_DIRS` also moved
  from an inline `__import__("hometools.config", ...)` hack in
  `_player_js.py` to `CFG.audiobookDirs` (computed once in
  `_html.py::_render_player_config_json`, same `get_audiobook_dirs()` call,
  just in one place instead of two).
- **Test fallout** (grepped the *entire* `tests/` directory per the Phase 3
  lesson-learned rule before starting, not just the historically-known
  files): ~80 direct `render_player_js(...)` call sites across
  `test_audit_log.py`, `test_offline_downloads.py`, `test_pwa_shortcuts.py`,
  `test_smart_playlists.py`, `test_streaming_player_ui.py`,
  `test_streaming_progress.py` had their now-invalid kwargs
  (`api_path=...`, `item_noun=...`, `enable_*=...`, etc.) stripped via a
  one-off Python script (paren-balanced call-site rewrite, kept only
  `player_bar_style=...` where present — see git history for the script if
  a similar bulk edit is ever needed again). `test_js_syntax.py`'s
  `CONFIGS` dict collapsed from 5 verbose per-server kwarg sets down to
  just `player_bar_style` per entry (every other kwarg is now runtime-only,
  so `audio_classic`/`video_classic` produce byte-identical JS — the
  distinct dict keys are kept only as readable test IDs).
  Literal-value assertions (`"RATING_WRITE_ENABLED = true" in js`,
  `"MIN_RATING_THRESHOLD = 2" in js`, `"DEFAULT_LANG = 'en'" in js`,
  `"RECENT_API_PATH = '/api/audio/recent'" in js`, etc.) were rewritten to
  either (a) assert the new `CFG.xxx`-based JS expression structurally, or
  (b) render a real page via `render_media_page()`/a live `TestClient` and
  parse the actual `#ht-config` JSON for the value — new shared test helper
  `_extract_ht_config(page)` added to `test_streaming_player_ui.py` and
  `test_streaming_progress.py` for this. `TestHtConfigJson._config` in
  `test_streaming_player_ui.py` now delegates to the same module-level
  helper instead of duplicating the regex/`json.loads`.
- **Verified end-to-end:** live `TestClient` requests against both audio
  and video servers confirm every migrated `CFG.*` field and every
  `_apiBase()`-derived path expression is present and correctly populated
  (`apiPath`, `minRating`, `crossfadeDuration`, `playlistSyncIntervalMs`,
  `defaultLanguage`, `audiobookDirs`, all boolean flags).
- 1388 tests passing, `ruff check`/`ruff format` clean,
  `tests/test_feature_parity.py` green (51/51).

**Phase 4 (done — 2026-07-30) — Static Serving:** FastAPI `StaticFiles`-Mount
für `/static/` (`server_utils/_static.py::mount_static_assets()`, wired into
`audio/server.py`, `video/server.py` and `channel/server_playlist.py`'s
`create_app()`). `_html.py::render_media_page()` now renders
`<script src="/static/player.<hash>.js"></script>` (resolved from Vite's
`build.manifest: true` output, `server_utils/_static.py::get_static_script_tag()`)
directly before the remaining inline `<script>{js}</script>`. Both halves
degrade gracefully when `streaming/core/static/` hasn't been built yet
(local dev without `npm run build`): `mount_static_assets()` logs one
warning and skips the mount; `get_static_script_tag()` returns `""` so no
broken `<script src>` is ever rendered. `vite.config.ts` now builds in
`format: "iife"` (not an ES module) so ported symbols can be bridged onto
`window` for the still-inline legacy script to consume as bare identifiers
— see Phase 5 below. Dockerfile gained a `webui-builder` Node stage that
runs `npm ci && npm run build` and copies the output into the python-builder
stage's source tree before `pip install .`; `pyproject.toml` gained
`[tool.setuptools.package-data]` so the wheel includes `static/**/*` when
present. New tests: `tests/test_streaming_static.py` (11 cases covering
missing/malformed/valid manifest, mount graceful-skip + real FastAPI mount,
`render_media_page()` tag placement).

**Phase 5 (in progress — first slice done, 2026-07-30) — Modulweiser Port:**
`fmtTime`/`escHtml`/`formatBytes` (previously top-level `function` declarations
in `player_js/_core.py::render_core_js()`) are now real, typed functions in
`streaming/core/webui/src/main.ts`, exported for `tsc`/tests and additionally
assigned onto `window` (`window.fmtTime = fmtTime;` etc.) so the remaining
Python-generated inline script's bare `fmtTime(...)` / `escHtml(...)` /
`formatBytes(...)` references keep resolving via the normal JS scope chain —
this only works because the bundle loads (as a classic, blocking `<script
src>`, not `type="module"`) strictly before the inline script in the same
document, so execution order matches today's behavior exactly. The three
Python definitions were deleted from `_core.py` (single source of truth per
`copilot-instructions.md`); every call site elsewhere in `player_js/*.py`
was left untouched (calls, not definitions — grepped first to confirm no
other file also defines any of the three names).

These three were deliberately chosen as the **first** slice: they are the
only fragments in the entire ~8900-line JS surface with zero references to
any other identifier defined elsewhere in the concatenated script — a hard
precondition for a safe module boundary today, since (see Design
Discussions below) every other `player_js/*.py` fragment freely reads and
writes identifiers declared in a *different* fragment file, all relying on
being concatenated into one shared non-strict function scope.

**Phase 6 (offen) — Cleanup:** Python-Generatoren + `tests/test_js_syntax.py`
(esprima-basiert) entfernen, sobald `tsc` die Syntax-Absicherung übernimmt.

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

**Status:** superseded 2026-07-30 — see "Vite/TypeScript migration" above,
now in progress (Phase 1-4 done, Phase 5 first slice done). The concerns
below were valid at the time and shaped the migration's design (gradual,
additive, `#ht-config` JSON extraction before any JS is touched, graceful
degradation when the bundle isn't built) rather than ruling it out entirely.

**Kurzfassung (Why not then):** Server-Werte (z. B. `api_path`,
`enable_shuffle`, `language_groups_json`) wurden damals direkt in den
JS-Text interpoliert (`render_player_js()`), nicht als separates JSON
injiziert — ein Bundler braucht aber statische Dateien zur Build-Zeit,
bevor diese Werte bekannt sind. Das wurde mit der `#ht-config`-Extraktion
(Phase 2/3) gelöst, bevor Phase 4 (Static Serving) begonnen wurde.
Zusätzlich: neue Laufzeit-Dependency (Node) nur zur **Build**-Zeit (nicht
zur Laufzeit — `server_utils/_static.py` degradiert graceful, falls
`static/` fehlt), Docker-Image-Kosten (gelöst über eine eigene
`webui-builder`-Stage im Dockerfile), Test-Anpassung (Feature-Parity-Tests
grep'en weiterhin direkt im JS-String für alles, was noch nicht portiert
ist), ~8900 Zeilen JS nachträglich typisieren (bewusst **modulweise**,
nicht auf einmal — siehe "Player-JS-Modulkopplung" unten für die dabei
entdeckte strukturelle Hürde).

**Revisit, wenn:** mehrere Personen parallel am JS arbeiten, echtes
Code-Splitting/Lazy-Loading nötig wird, oder komplexere Client-State-
Verwaltung ansteht, die von echten ES-Modulen profitiert.

### Player-JS-Modulkopplung blockiert einfachen Modul-für-Modul-Port (2026-07-30)

**Status:** offen — beeinflusst die Reihenfolge/den Aufwand von Phase 5.

Beim Auswählen der ersten Phase-5-Slice (`fmtTime`/`escHtml`/`formatBytes`)
zeigte sich: praktisch **jedes** andere `player_js/*.py`-Fragment
(`_drag_drop_init.py`, `_playlists.py`, `_smart_playlists.py`, ...) liest
und schreibt Bezeichner, die in einer *anderen* Fragmentdatei deklariert
sind (z. B. `filteredItems`, `PLAYLISTS_ENABLED`, `showFolderView`,
`reorderPlaylistItem`, `_userPlaylists`, `allItems`, `inPlaylist`) — alles
verlässt sich darauf, in **eine** gemeinsame, nicht-strikte
Funktions-Scope konkateniert zu werden. Ein Fragment ist damit kein
JS-„Modul" im eigentlichen Sinn, sondern nur eine Datei-Grenze zur
besseren Python-Quelltext-Pflege.

Zusätzlich gefundenes konkretes Beispiel für die Fragilität dieses Musters:
`_drag_drop_init.py` weist `_dndCleanup = function() {...}` zu, **ohne**
`var _dndCleanup` irgendwo zu deklarieren — funktioniert nur, weil die
Zuweisung dadurch (nicht-strict mode) ein implizites globales
`window._dndCleanup` erzeugt, auf das `destroyPlaylistDragDrop()` in
`_smart_playlists.py` dann zugreift. Das ist ein Code-Smell (verlässt sich
auf Sloppy-Mode-Verhalten, das ein `"use strict"` oder ein ES-Modul sofort
bricht) — absichtlich **nicht** in dieser Runde repariert (kein
eindeutiger Bug, funktioniert wie vorgesehen), aber ein Blocker für jeden
künftigen Versuch, ein Fragment als echtes strict-mode ES-Modul zu
bauen, ohne vorher eine explizite geteilte "Player State"-Schnittstelle
einzuführen.

**Plan für die nächsten Slices:** vor dem Port eines Fragments mit
Querverweisen zuerst ein Ambient-Types-Contract (`.d.ts`) für die von ihm
konsumierten globalen Bezeichner schreiben, dann `fmtTime`-artige,
abhängigkeitsfreie Funktionen bevorzugt weiter zuerst portieren
(Kandidaten: reine Formatierungs-/Validierungs-Helfer in `_search_filter.py`
und `_track_render.py`), größere zustandsbehaftete Fragmente
(`_core.py`, `_library_tools.py`) erst danach angehen.


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

- **Bugfix: `_svg.py`-Änderungen an Stern/Edit-Icon zeigten keine Wirkung** (2026-07-25) — `_player_js.py` definierte `IC_PLAY`/`IC_PAUSE`/`IC_DL`/`IC_CHECK`/`IC_FOLDER_PLAY`/`IC_PIN`/`IC_STAR`/`IC_STAR_FILLED`/`IC_STAR_EMPTY`/`IC_SHUFFLE`/`IC_REPEAT`/`IC_EDIT`/`IC_LYRICS` als hartcodierte zweite Kopien der bereits importierten `SVG_*`-Konstanten (durch pauschales `# noqa: F401` verdeckt); `_audit.py` hatte dieselbe Duplikation für `IC_STAR_FILLED`/`IC_STAR_EMPTY` in seinem eigenständigen `_AUDIT_PANEL_JS`-Skript. Das erklärte, warum die vorherige SVG-Politur (Stern-Silhouette, Stift-Icon) in `_svg.py` nicht im Browser ankam. Fix: alle betroffenen `IC_*`-Variablen referenzieren jetzt die importierten `SVG_*`-Konstanten (gleiches Escaping-Muster wie `IC_PLAYLIST`/`IC_TRASH`). Neue Tests `test_ic_star_and_edit_match_svg_py` und `test_audit_panel_star_matches_svg_py` in `tests/test_js_syntax.py` verankern beide Quellen aneinander.
- **SVG polish: Favoriten-Stern + Bearbeiten-Stift** (2026-07-25) — `SVG_STAR`/`SVG_STAR_EMPTY` wurden auf eine klarere, spitzere Sternsilhouette umgestellt; `SVG_EDIT` ist jetzt ein echter Stift-/Pencil-Icon-Pfad statt des vorherigen dokumentartigen Symbols. Nur `_svg.py`, keine API- oder JS-Änderung.
- **UX micro-adjustment: Track "Im Explorer anzeigen" button** (2026-07-25) — Der `track-reveal-btn` sitzt jetzt in Listen- und Tabellenansicht direkt links vom Drei-Punkte-Menü, damit die rechten Track-Aktionsbuttons visuell konsistent bleiben. Nur CSS-Order in `css/_track_list.py` und `css/_table_view.py`; keine API- oder JS-Logikänderung.
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
