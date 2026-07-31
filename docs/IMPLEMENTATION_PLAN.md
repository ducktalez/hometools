# Implementation Plan

Backlog + open design discussions only. Completed items are removed from
here, not archived — their history is `git log`, not this file.

## Backlog — Medium

### Vite/TypeScript migration (in progress)

**Goal:** replace `server_utils/_player_js.py` + `player_js/*.py` + `_css.py`
+ `css/*.py` (~8900 lines of JS/CSS as Python string concatenation)
module-by-module with real `.ts`/`.css` files, built with Vite, served by
FastAPI as static assets. Backend (FastAPI, catalog, sync, ...) is
unaffected — pure frontend-tooling migration. See
`src/hometools/streaming/core/webui/README.md` for the scaffold and
`docs/architecture.md` → "Vite/TypeScript migration" for the current state.

**Remaining:**
- Module-by-module port of the rest of `player_js/*.py` — blocked for the
  *stateful* fragments (`_core.py`, `_library_tools.py`, ...) by the
  cross-fragment coupling described in "Player-JS-Modulkopplung" below.
  The ambient `.d.ts` contract for those shared globals now exists
  (`webui/src/legacy-globals.d.ts`) — extend it as more state gets
  bridged onto `window`, don't start a new one. Non-stateful (pure) leaf
  helpers no longer need to wait for this — see "Opportunistic
  migration" in `webui/README.md`: port them the moment an unrelated
  change touches their fragment (done so far: `needsConversion`/
  `filenameFromPath`/`parentPath`/`leafName`/`currentFolderOf` →
  `pathUtils.ts`;
  `_fmtDuration`/`_fmtFileSize`/`_fmtDate`/`_normalizeStem`/`_dupeKey` →
  `dupeUtils.ts`; `cleanFolderName`/`renderBreadcrumbHtml` → `breadcrumb.ts`;
  `_isDupeGroupSafe` → `dupeUtils.ts`;
  `_getRecentMoveTargets`/`_saveRecentMoveTarget` → `recentMoveTargets.ts`).
  ✅ **Larger, deliberate slice (not opportunistic):** the entire smart
  playlist rule evaluator (`_smartCompile`/`_smartGetField`/
  `_smartEvalRule`/`_buildSmartPlIndex`/`_smartApplySort`/
  `_evaluateSmartPlaylist`, previously in `_playlists.py`) → one cohesive
  module `smartPlaylist.ts`. Sidesteps the mutable-global bridging
  problem entirely: instead of mirroring `allItems`/`_userPlaylists`/
  `_savedFavorites` onto `window` (which would need every mutation site
  touched to stay in sync), the ported functions take them as explicit
  parameters — genuinely pure, no `window` reads at all. The two
  remaining call sites (`_folder_browse.py`, `_playlists.py`'s
  `_resolvePlaylistItems`/`refreshSmartPlaylist`) just pass their local
  globals as arguments to `window._evaluateSmartPlaylist(...)`.
- Delete the Python JS/CSS generators and the `esprima`-based
  `tests/test_js_syntax.py` once `tsc` covers syntax safety for the whole
  surface.

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
- `server_utils/player_js/_library_tools.py` (~2300 lines) is still the
  largest fragment (duplicates + file-mover + delete/reveal) — split
  further once a safe internal boundary (no embedded Python interpolation)
  is identified.
- `tests/test_streaming_player_ui.py` (~2100 lines) should be split into
  thematic files (e.g. `test_streaming_player_ui_playlists.py`,
  `..._smart_playlists.py`, `..._queue.py`, `..._catalog_cache.py`)
  mirroring the `player_js/` module split.
- `docs/IMPLEMENTATION_PLAN.md` is still German; `docs/architecture.md` and
  all `.github/instructions/*.md` are already English. Decide whether to
  translate this file for full project-wide consistency.

## Backlog — Low / Experimental

- **DJ-Extension** — Mixing, Stems (Gesang/Instrumental/Beat), Auto-DJ-Modus
- **„MTV"-Modus** — Musikvideos + visuelle Begleitung zu Musik
- **„Sleep Mode"** — nur Audio aus Serien, kein Bildschirm
- **Photo-Management-Server**
- **HTTP-Obscurification** — Port-Knock statt HTTPS für Privat-Server
- **Pro-Nutzer Ordnerstruktur** (N8N-Integration)
- **Lennyface-Board**

## Mobile Features (postponed)

- **Phase 3: Native iOS Apps** — Hybrid WebView Wrapper für Video + Audio → [plans/native_app_plan.md](plans/native_app_plan.md)

## Design Discussions

### UI-Template-Vereinheitlichung: Header, List-Toolbar, List-Item

**Status:** Phase 1 (Header) abgeschlossen. Phase 2+ offen.

**Problem:** Header, Breadcrumb, Filter-Bar/Toolbar und Listeneinträge
(Folder-Card, Playlist-Card, Smart-Playlist-Card, Track-Row, Track-Table-Row)
werden aktuell ad hoc an vielen Stellen einzeln zusammengebaut statt aus
einer gemeinsamen Vorlage. Header-Zustand wurde bisher in 7 verschiedenen
Funktionen über 5 Dateien separat gesetzt — genau dieses Auseinanderdriften
verursachte den Smart-Playlist-Header-Bug.

**Geklärte Entscheidungen:**
1. Home-Button-Emoji entfällt komplett.
2. "Filtern" (Bewertung + Favorit + Genre) wird zu einem Button mit Popover
   zusammengefasst; "Ausgeblendet" bleibt eigener Toggle-Slot.
3. Video-3-Wege-Toggle (Liste/Tabelle/Kachel) strukturell vorbereitet, aber
   keine Priorität — Tabellenmodus bleibt vorerst Audio-only.

**Phasenplan:**
1. ✅ **Header vereinheitlichen** — Breadcrumb (`renderBreadcrumb()` in
   `_queue.py`) lebt jetzt inline im Header (zwischen Home-Button und
   `.header-spacer`), keine separate `<nav>`-Zeile mehr. Home-Button hat
   kein Emoji mehr (`SVG_HOME`, neu in `_svg.py`); `emoji`-Parameter von
   `render_media_page`/`_render_player_config_json` bleibt für
   `fileEmoji`/PWA-Icon erhalten, wird aber nicht mehr im Header gerendert.
   Breadcrumb zeigt keinen eigenen "Home"-Eintrag mehr (redundant zum
   Home-Button) und keine Unicode-Icons. `.logo-title` (aktueller
   Titel/Ordnername) blendet sich aus, sobald die Breadcrumb sichtbar ist
   (echte Ordnerpfade), und wieder ein für Playlist-/Such-/Duplikat-Titel
   ohne Pfad — Struktur bleibt in jeder Ansicht identisch (kein Header-
   Sprung mehr).
2. **List-Toolbar vereinheitlichen** (View-Toggle, Ausgeblendet, Sortieren,
   zusammengefasster Filtern-Button, Suche+Zähler) — teilweise erledigt:
   ✅ Alle Track-Listen-Ansichten (Ordner-Playlist, Nutzer-Playlist,
   Favoriten, "Titel", Smart Playlist, Duplikate) rufen jetzt
   `_enterTrackListView(opts)` (`_folder_browse.py`) statt den Header-/
   Toolbar-DOM-Zustand einzeln zu duplizieren — behebt konkret das
   Auseinanderdriften, das u.a. die fehlende Header-Suche bei "Intelligenter
   Wiedergabeliste" verursachte. `_enterTrackListView()` ruft jetzt auch
   `applyViewMode()` (vorher nur von `showFolderView()` aufgerufen) — das
   View-Toggle-Icon (Liste/Tabelle) blieb sonst beim direkten Einstieg in
   eine Playlist/Smart-Playlist/Duplikate-Ansicht im alten Zustand hängen.
   ✅ `playUserPlaylist()` (`_smart_playlists.py`, Autoplay-Variante der
   Playlist-Karten) hat den Header bisher weiterhin manuell gesetzt
   (`header-title`-Textinhalt direkt, ohne Breadcrumb/Suchfeld-Reset/
   `applyViewMode()`) statt wie `showUserPlaylistView()` durch
   `_enterTrackListView()` zu gehen — genau dieser Bypass war die Ursache
   für den zuletzt gemeldeten Header-Drift beim Playlist-Autoplay. Jetzt
   delegiert `playUserPlaylist()` an `showUserPlaylistView(plId)` und
   startet danach nur noch `playTrack(0)`.
   ✅ **Zusammengefasster Filtern-Button** — Bewertung, Favorit und Genre
   waren als drei separate `.filter-chip`-Buttons (`filter-rating`,
   `filter-fav`, `filter-genre`) verdrahtet; jeder Klick zyklte den
   jeweiligen Filter unabhängig weiter. Jetzt ein einziger Button
   `filter-combined` ("Filtern", mit Zähler-Badge bei aktiven Filtern),
   der ein Popover (`_toggleFilterPopover()`/`_closeFilterPopover()` in
   `_search_filter.py`, CSS in `css/_track_list.py` unter
   `.filter-popover`) mit Sterne-Reihe, Favoriten-Checkbox und
   Genre-`<select>` (dynamisch aus `playlistItems`) öffnet — plus einem
   "Zurücksetzen"-Button, der alle drei auf einmal löscht. Positionierung/
   Open-Outside-Click/Escape-Handling folgt demselben Muster wie der
   generische `_openCtxMenu()` (Kebab-Menü) in `_library_tools.py`, ist
   aber eine eigene kleine Implementierung, da die Popover-Inhalte
   interaktive Formularelemente statt einer reinen Aktionsliste sind.
   "Ausgeblendet" (`filter-hidden`) bleibt wie geplant ein eigener
   Toggle-Slot. Sortieren ist weiterhin ein einfaches `<select>` ohne
   eigene Komponente.
   Offen: Sortieren als eigene Komponente ist weiterhin pro Aufrufer ad
   hoc verdrahtet.
3. **Listen-Item-Templates** (Folder/Playlist/Smart-Playlist/Duplicate-Card;
   Track-Row mit `mode: 'rows'|'table'`) — offen.
4. **Track-Count-als-Refresh-Button** — offen.
5. **Video-Parity-Tests** — offen.
6. **Aufräumen** (totes `folder-filter-bar`-Div, `_applyTrackViewMode`s
   Tabellen-Header-Inject-Hack) — offen.

### Player-JS-Modulkopplung blockiert einfachen Modul-für-Modul-Port

**Status:** offen — beeinflusst Reihenfolge/Aufwand der verbleibenden
Vite/TS-Migrationsschritte.

Praktisch **jedes** `player_js/*.py`-Fragment (`_drag_drop_init.py`,
`_playlists.py`, `_smart_playlists.py`, ...) liest und schreibt Bezeichner,
die in einer *anderen* Fragmentdatei deklariert sind (z. B.
`filteredItems`, `PLAYLISTS_ENABLED`, `showFolderView`, `allItems`,
`inPlaylist`) — alles verlässt sich darauf, in **eine** gemeinsame,
nicht-strikte Funktions-Scope konkateniert zu werden. Ein Fragment ist
damit kein JS-„Modul" im eigentlichen Sinn, sondern nur eine Datei-Grenze
zur besseren Python-Quelltext-Pflege.

Konkreter Code-Smell (bewusst nicht repariert — funktioniert wie
vorgesehen, aber ein Blocker für jeden künftigen strict-mode-Port):
`_drag_drop_init.py` weist `_dndCleanup = function() {...}` zu, ohne
`var _dndCleanup` irgendwo zu deklarieren — funktioniert nur, weil das im
nicht-strict mode ein implizites globales `window._dndCleanup` erzeugt,
auf das `destroyPlaylistDragDrop()` in `_smart_playlists.py` zugreift.

**Plan für die nächsten Slices:** vor dem Port eines Fragments mit
Querverweisen zuerst ein Ambient-Types-Contract (`.d.ts`) für die von ihm
konsumierten globalen Bezeichner schreiben — **erledigt**:
`webui/src/legacy-globals.d.ts` deckt den aktuell bekannten Bedarf
(Core-State, Config-Flags, Icon-Konstanten, geteilte Funktionen) ab und
wird bei jedem weiteren Port um neu gebrauchte Identifier erweitert.
Abhängigkeitsfreie Formatierungs-/Validierungs-Helfer wurden bereits
opportunistisch portiert (`needsConversion`/`filenameFromPath` →
`pathUtils.ts`; `_fmtDuration`/`_fmtFileSize`/`_fmtDate`/`_normalizeStem`/
`_dupeKey` → `dupeUtils.ts`, siehe `webui/README.md` → "Opportunistic
migration rule"); größere zustandsbehaftete Fragmente (`_core.py`,
`_library_tools.py`) bleiben bis zu einer künftigen dedizierten
Bridging-Änderung unportiert.

**Zweites Muster gefunden (Smart-Playlist-Evaluator, `smartPlaylist.ts`):**
nicht jedes zustandsabhängige Fragment braucht den `window`-Bridge-Weg.
Wenn die gelesenen Globals (hier `allItems`/`_userPlaylists`/
`_savedFavorites`) an vielen Stellen im ganzen `player_js/`-Baum neu
zugewiesen/mutiert werden, wäre ein `window`-Spiegel an jeder dieser
Stellen zu pflegen — fehleranfällig. Alternative: die portierte
TS-Funktion nimmt sie als **explizite Parameter** statt sie zu lesen;
die (wenigen) verbleibenden Python-Call-Sites reichen ihre aktuellen
lokalen Variablen einfach als Argumente durch. Ergebnis: echte Pure-
Funktion, kein `window`-Read nötig. Für zukünftige Ports von
`_core.py`/`_library_tools.py`-Fragmenten prüfen, ob dieses Muster
(Parameter statt Bridge) an der jeweiligen Fragmentgrenze güns­tiger ist
als ein neuer `legacy-globals.d.ts`-Eintrag — abhängig davon, ob der
Global read-only/einmalig gesetzt (→ Bridge, wie `originalTitle`) oder
häufig mutiert wird (→ Parameter, wie hier).

### Smart-Playlist-Kaskaden (Phase 2)

**Status:** offen.

Aktuell (Phase 1) werden `in_playlist`-Regeln nur gegen *nicht-smarte*
Playlists aufgelöst — Verweise auf andere Smart Playlists liefern
garantiert `false` und werden im Index-Bau übersprungen. Damit sind Zyklen
ausgeschlossen, ohne dass eine Topologie-Analyse nötig ist.

**Phase-2-Vorschlag** (sobald praktisch benötigt):

1. Vor der Auswertung einen gerichteten Graphen `pl_id → set(referenzierte pl_ids)` aus allen `in_playlist`-Regeln aufbauen.
2. Per DFS auf Zyklen prüfen. Bei Zyklus: betroffene Smart Playlists markieren, im UI mit einem Warn-Badge versehen und in der Auswertung wie leer behandeln.
3. Bei zyklenfreiem DAG topologisch sortieren und Smart Playlists in dieser Reihenfolge auswerten — vorgelagerte Ergebnisse stehen damit nachgelagerten als „virtuelle Playlist-Mitgliedschaft" zur Verfügung.
4. Tiefen-Limit (z.B. max. 5) als Safety-Net gegen Performance-Spitzen.
5. Cache der Auswertungsergebnisse pro Refresh-Zyklus (Memoization), damit eine Smart Playlist nicht mehrfach evaluiert wird, wenn sie von mehreren anderen referenziert wird.

**Trade-offs:** Komplexität + UX-Kosten (Fehlermeldung „Zyklus erkannt") gegen die seltene Nützlichkeit (Power-User-Feature). Bis ein User-Wunsch existiert, bleibt Phase 1 als bewusst einfache Lösung.

### `added_at`-Feld auf MediaItem (Phase 2)

**Status:** offen.

Smart Playlists nutzen aktuell `MediaItem.mtime` als Proxy für „Datum hinzugefügt". Problem: Tag-Edits oder NAS-Resync setzen `mtime` zurück, sodass „Zuletzt hinzugefügt" Treffer „verlieren" kann.

**Vorschlag:** Neues Feld `first_seen_at: float` auf `MediaItem`, das beim ersten Build im Index-Cache vermerkt und nie überschrieben wird. `catalog.py` (Audio + Video) liest den Wert aus dem vorigen Snapshot vor dem Persistieren des neuen. Bei vollständigem Cache-Wipe fällt der Wert auf `mtime` zurück. Smart-Playlist-Evaluator bevorzugt `first_seen_at`, fällt auf `mtime` zurück.

### Skip-Intro Phase 2: Audio-Fingerprinting (automatische Erkennung ohne Kapitel)

**Status:** offen.

Phase 1 bestimmt Intro-Längen über drei Quellen: manuelle UI-Marker (serverseitiger JSON-Store), `hometools_overrides.yaml` (`intro_start`/`intro_end`) und ffprobe-Kapitelmarken („Intro"/„Opening"). Letztere greifen nur bei Releases, die benannte Kapitel mitliefern — das ist die Minderheit.

**Es gibt keine zuverlässige freie öffentliche API für Intro-Timestamps** (TMDB liefert sie nicht). Die robuste vollautomatische Technik ist **Cross-Episode-Audio-Fingerprinting** (vgl. Jellyfins *Intro Skipper*-Plugin): Pro Staffel wird das gemeinsame Audiosegment (= Titelmelodie) gesucht, das in mehreren Episoden identisch auftaucht, und daraus `[intro_start, intro_end]` abgeleitet.

**Vorschlag** (sobald praktisch benötigt): chromaprint/fpcalc (oder ffmpeg-basierte MFCC-Fingerprints) pro Episode berechnen, paarweise Episoden einer Staffel auf das längste gemeinsame Audio-Subsegment abgleichen, Ergebnis als `source="fingerprint"` in den bestehenden `intro_markers`-Store schreiben (gleiche Präzedenz wie `auto`). Rechenintensiv → Daemon-Thread + persistenter Fingerprint-Cache im Shadow-Cache, nur bei `season>0`-Items. Optionales `HOMETOOLS_INTRO_FINGERPRINT`-Flag (Default aus).

**Trade-offs:** hoher CPU-/IO-Aufwand (ganze Staffeln dekodieren) + zusätzliche optionale Dependency (chromaprint) gegen den Komfort, dass Intros ohne jegliche manuelle Pflege erkannt werden.
