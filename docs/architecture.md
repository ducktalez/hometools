# Architecture

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

## Non-blocking Index-Aufbau

Die Katalog-API-Endpunkte (`/api/audio/tracks`, `/api/video/items`) prüfen zuerst den Cache und starten ggf. einen Background-Refresh. `check_library_accessible` wird **nur** aufgerufen, wenn keine gecachten Items vorhanden sind (Cold-Start oder leerer Cache). Dadurch blockiert der Library-Check (bis zu 3 s bei NAS-Pfaden) nie die Auslieferung bereits verfügbarer Daten.

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

