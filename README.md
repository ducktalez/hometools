# hometools

A collection of Python tools for managing personal media libraries — music file sanitization, video organizing with TMDB, and local audio & video streaming prototypes with a shared core.

## 📚 Dokumentation

- **[docs/plans/](docs/plans/)** — Roadmap, Feature-Pläne (Offline, Native App, Server Refactoring, PWA Shortcuts, ...)
- **[docs/ios/](docs/ios/)** — iOS/PWA-Entscheidungen, Gerätetests, Test-Runbooks
- **[docs/docker.md](docs/docker.md)** — Docker-Deployment (Synology + generisch)
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** — Coding-Regeln für Copilot/Agents

## Docker (Quickstart)

```bash
cp docker/.env.example .env
# in .env: AUDIO_LIBRARY_PATH + VIDEO_LIBRARY_PATH eintragen
docker compose up -d --build
```

Audio auf Port 8010, Video auf Port 8011. Details und Synology-Anleitung in
[docs/docker.md](docs/docker.md).

## Plan/TODOs


---


- Bug: In intelligenten Wiedergabelisten ist die Anzeige der Kopfleiste und Layout anders. Wie kann das sein? Diese sollte überall gleich sein. (zB.: Die Suchfunktionen fehlen, "Tools"-Pille wird angezeigt, aber kann nicht angeklickt werden)
- Bei serien (ducktales: staffel 1) erschienen die Folgen in der Liste mit unterschiedlichem Format links als Nummern (1-17), danach ging es weiter als „S01E12“. Das Problem waren falsche Dateinamen ("S01.E01" statt "S01E02"). Die Einrückung sollte aber trotzdem passen. Für solche Fälle sollte im Dashboard zusätzlich eine Warnung für die Datei erscheinen. Auch eine bessere Staffel/Folgeerkennung aus Strings über Regex wäre denkbar. 
- Layout: Es gibt drei Listentypen: Ordner, normale Wiedergabeliste, intelligente Wiedergabeliste. Diese sollen erkennbar sein. Intelligente Wiedergabelisten haben bereits ein Symbol. 
  - Wiedergabelisten sollen auch ein Cover haben (Wie bei Ordnern).
  - Ordner sollen ein überblendendes Ordnersymbol über dem Cover haben, WIedergabelisten 
  - 
- Dashboard. Ich will eine Startseite, die einem einen Überblick über die wichtigsten Funktionen gibt. Im Dashboard kann auch auf die Server zugegriffen werden - evtl laufen diese dann am selben Port. Zu den jeweiligen Servern sollten hier auch Aufgaben angeigt werden. Diese wären zB.
  - Konvertierungen vorschlagen (zB. Konvertierung zu .mp4 bei nicht streambaren files, die sonst gemuxed werden müssen). Würde per Klick direkt erledigt werden.
  - fehlenden Folgen einer Serie
  - Liste mit Duplikaten bei Liedern (Hier könnte ein Link zur Playliste mit Duplikaten führen)
  - Warnungen: Der Nutzer soll bei Titeln/Videos bei den Optionen "Warnung/flaggen" haben. Der Song wird dann im Dashboard angezeigt.
  - Zeitpunkte der letzten Synchronisierung/Indizierung. Wenn gerade eine Synchronisierung läuft, sollte auch per Fortschrittsbalken angezeigt werden, was schon erledigt worden ist und was noch aussteht. (zB. 10 von 100 Dateien synchronisiert). Besonders bei der Synchronisation sollte hier eine Hierarchie der Aufgaben vorherrschen (Vom Nutzer angeforderter Titel (wenn keine Metadaten)-> Vom Nutzer angeforderte Liste -> restliche Wiedergabelisten (bei Neustart bzw. wenn schon lange her).  (!) Thumbnails/Audio-scrolls sollen generell nicht erneuert werden, wenn sie bereits vorhanden sind. Diese Neugenerierung wäre nur bei User-Request nötig. Wenn du hier noch weitere Vorschläge hast, gerne umsetzen.
- Ich überlege, die auf verschiedenen Ports laufenden Hauptfunktionen nicht mehr zu unterscheiden. Ist das eine kluge Idee?
- Die "letzte Wiedergabe fortsetzen" soll nur bei der zuletzt gesehenen Folge (bei Hörbüchern immer) angewandt werden. Momentan starten willkürliche Folgen oft mittendrin, weil sie vor Ewigkeiten mal gesehen wurden.
- Ich würde im nächsten Schritt gerne die Administrator-Dashboard-Seite überarbeiten. Hier sollen Aufgaben, die den Streamingprozess erleichtern, für die vorbereitete Abarbeitung vorgeschlagen werden.
  - Konvertierungen vorschlagen (zB. Konvertierung zu .mp4 bei nicht streambaren files, die sonst gemuxed werden müssen)
  - fehlenden Folgen einer Serie
  - Liste mit Duplikaten bei Liedern
- Idee: Anzeige eines Art "Embeddings" für Lieder
  - Lieder werden in einem 2D-Plot angezeigt, der die Ähnlichkeit der Lieder zueinander darstellt (Lieder als Kreisen mit Coverbild, Titel/Künstler)
  - Wichtig für das Embedding könnte zB. die BPM, das Genre, der Interpret, die Tonart, die Länge, Erscheinungsjahr, Hinzugefügt-am-Zeitpunkt, die Lautstärke, die Stimmung (zB. fröhlich, traurig, aggressiv) sein. Auch die Popularität (zB. Bewertung) könnte ein Faktor sein. Ebenfalls wären tags möglich.
  - Der Algorithmus könnte sich nun durch-"crawlen" und ähnliche Lieder in der Nähe anzeigen und diese als nächstes abspielen
  - Als Nutzer sollte man die insgesamt möglichen Lieder per Filter bestimmen können. Auch die Richtung (schneller, fröhlicher, ...) wären interessant
  - Die Embeddings könnten auch für die Suche genutzt werden. ZB. "ähnliche Lieder wie XY" oder "ähnliche Lieder wie das gerade gespielte Lied"
  - Es würde sich vermutlich um kein echtes Embedding handeln, sondern eher um eine Art "Feature-Space", der die Lieder in einem 2D-Raum anordnet. Die Ähnlichkeit könnte zB. über eine gewichtete Summe der Features berechnet werden. Zwei Embedding-faktoren wären 2d-mäßig anzeigbar, die Sterne könnten durch Farbe oder Größe dargestellt werden. Die anderen Faktoren könnten per Filter ein- und ausgeblendet werden.
  - Dieses Feature-space-embedding sollte titel - sowie Listenspezifische Features abbilden.  Für WIedergabelisten sollte man in einer Tabelle diese Features jeweils bewerten können. (zB. happy (rank 0-5), energy (0-5), party (0-5), sing (0-5))
- Layout/UX Instructions: funktionale Farben
  - Das folgende soll umgesetzt werden, insbesondere sollen aber auch die .github-Instructions dafür angepasst werden. Meine Anweisungen sind Vorschläge, vermutlich kennst du weitere/bessere UI-Sachen.
  - In der Gesamterfahrung sollen Farben nicht allzu dominant und auf Funktionalität ausgelegt sein (ähnlich wie bei einem Pioneer-DJ-Pult. Fokus auf Audio-server, da hier mehr gearbeitet wird als bei Video). Das heißt zB.::
    - zusammenhängende Funktionen haben ähnliche Farben.
      - Hat sich etwas wichtiges verändert, sollte es dort kurz blinken (blink-up wenn aktiv oder blink-down-short wenn inaktiviert)
      - Farben sind eher Zugehörigkeiten - Warnungen/Vorschläge sollten durch blinken/Glow sichtbar gemacht werden
    - Bei Farb-Änderungen sollte zur besseren Aufmerksamkeit die Elemente kurz blinken
    - Cover sollten [optionalerweise im .env-File einstellbar]  weniger gesättigt angezeigt werden, damit Signalfarben immer Signalfarben bleiben.
    - Wird ein neuer Titel zur Warteschlange hinzugefügt, sollte der Handle sanft grün blinken. SOlang Titel in der Warteschlange sind, glowt der Handle grün.
  - Die Bewertungs-Sterne sollten weniger Sättigung haben als bisher. dennoch passt die Farbe Gelb, da diese Info wichtig ist.
  - Bitte frage bei konkreten Ideen oder Problemen nach
- Strg+Z um die letzte Aktion rückgängig machen zu können? (Gute Idee? Zu komplex?)
- Ich hätte gerne eine zusätzliche Funktion: die Möglichkeit, Clips zu erstellen. Die Idee ist, dass man einfach eine normale Serie schaut und Momente sieht, die sich gut für einen Clip eignen, ausgeschneiden werden können. Auch das Markieren interessanter Momente wäre hilfreich. Es handelt sich um eine etwas separate Entwicklung. Das ist mir klar.
- Im tools-modus sollen die anderen Metadaten wysiwig geändert werden können (z.B. Album, Interpret, Genre, Jahr, etc.). Das ist teilweise schon möglich, aber noch nicht vollständig umgesetzt.
- Es soll eine Listenansicht für Titel geben, in der (wie im windows ordner) die Metadaten Spaltenmäßig angezeigt werden. Die Spalten sollen auch ausgewählt werden können.
- wav/mp3 Organisation für DJs.
- bug: Deleted files landen in delete_me statt in den Papierkorb. Da es oft keinen gibt: Hier ist eigentlich der Windows-Papierkorb gemeint. Bitte prüfen, ob das möglich ist. Sonst würde der delete_me Ordner passen oder die Titel könnten umbenannt werden (leading-".", damit versteckt und nicht mehr in Liste sichtbar). Papierkorb-dateien im delete-me Ordner sollten im Dashboard als final löschbar angezeigt werden.
- Bei Serien sollte in der Listenanzeige nur Staffel/Folge 
- original-downloadname vs. syntaktisch korrekter Name
- podcast & Musik gleichzeitig laufen lassen
- TV-Idee: Stream der Wer wird Millionär Show aus dem Quiz Repository. Hier kann eine zufällige Person online teilnehmen. 
- Check if audiobook from metadata is possible too 
- Option zur Erweiterung/Anreicherung mit YouTube Downloads. 
- Drei ??? Alben sind aufeinanderfolgende Titel . automatisch erkennen/automatisch mergen?
- Tests haben immer eine Auswirkung auf den Serverzustand. Kann man tests iwie besser mocken?
- Musik abspielen, während man ein Hörbuch hört?
- Layout Erweiterung: In Spotify und iTunes sind Wiedergabelisten üblicherweise an der linken Seite und die Titel in einem Fenster an der rechten. Dieses Design soll hier auch so umgesetzt werden. 

---

Vollständiger Implementierungsplan mit Backlog: **[docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)**

**Aktuell:** Management-Server & Scheduler, Metadata-Editing
**Nächste:** Phase 3 — Native iOS Apps

- Für folgende Medien soll der letzte Abspielzeitpunkt gespeichert werden
  - Serien: Die letzte Folge + Zeitstempel
  - Hörbücher: Das letzte Kapitel + Zeitstempel. Hörbücher müssen markiert werden, befinden sich in passenden Ordnern befinden sich in passenden Ordnern (einstellbar) oder werden erkannt (Bei abspielzeit > 15min?)

## PyCharm Run-Konfigurationen

Im Repo unter `.idea/runConfigurations/` liegen fertige Konfigurationen:

| Konfiguration | Beschreibung |
|---|---|
| **Serve All** | Audio + Video + Channel Server starten |
| **Serve Audio** | Nur Audio-Server |
| **Serve Video** | Nur Video-Server |
| **Serve Channel** | Nur Channel (TV)-Server |
| **Run Tests** | Vollständige Test-Suite (`pytest -q`) |
| **Feature Parity Tests** | Audio↔Video Drift-Erkennung |
| **Ruff Check + Format** | Lint + Auto-Fix |
| **Dashboard** | CLI-Issues/TODOs Dashboard |
| **Streaming Config** | Aktuelle Konfiguration anzeigen |
## Features

### Music Library
- **Filename sanitization** — normalize `feat.`/`prod.`/`vs.` variants, remove emojis, website URLs, bitrate tags, and fix spacing
- **Duplicate detection** — find and remove duplicate audio files across folders
- **Silence trimming** — losslessly remove leading/trailing silence using ffmpeg
- **MP3 merging** — concatenate multi-part audio files
- **Metadata management** — read/write ID3 tags, POPM ratings, BPM analysis

### Video Library
- **TMDB integration** — automatically match movie & series files against [The Movie Database](https://www.themoviedb.org/)
- **Smart renaming** — rename files to `Title (Year) [tmdbid-ID].ext` format, compatible with Jellyfin/Plex
- **Series support** — parse `S01E03` patterns and fetch episode names

### Streaming (Audio & Video)
- **Shared streaming core** — common `MediaItem` model, catalog query/sort/filter, NAS sync and dark-theme UI used by both servers
- **Manual NAS sync** — copy new or changed media files from a mounted NAS folder into a local library on demand
- **Browser-based audio player** — dark-theme web UI with search, artist filter, sort, and bottom player bar
- **Browser-based video player** — same UI as audio but with an inline `<video>` element, folder-based filtering
- **PWA offline support** — download tracks/videos for offline playback via IndexedDB
- **Shadow cache** — thumbnails, failure tracking, and metadata caches in a mirror directory

## Quick Start

```bash
git clone https://github.com/ducktalez/hometools.git
cd hometools
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"

# Configure secrets and paths
Copy-Item .env.example .env
# Edit .env with your TMDB_API_KEY and library paths

pytest
```

## Streaming

Configure library paths, NAS sources and bind address in `.env`:

```dotenv
HOMETOOLS_AUDIO_LIBRARY_DIR=C:/Media/audio-library
HOMETOOLS_AUDIO_NAS_DIR=Z:/Music
HOMETOOLS_VIDEO_LIBRARY_DIR=C:/Media/video-library
HOMETOOLS_VIDEO_NAS_DIR=Z:/Video
HOMETOOLS_STREAM_HOST=0.0.0.0
HOMETOOLS_AUDIO_PORT=8010
HOMETOOLS_VIDEO_PORT=8011
```

```powershell
hometools streaming-config        # show current config overview
hometools serve-all               # start audio (:8010) + video (:8011)
hometools sync-audio --dry-run    # preview audio sync
hometools sync-video              # copy video files from NAS
```

### Wartung / Debugging

- `make reset-hard SERVER=audio` — löscht generierte Audio-Artefakte (Logs, Index-Snapshot, Thumbnails, Failure-Registry-Einträge)
- `make reset-all-hard` — harter Reset für beide Streaming-Server
- `make prewarm SERVER=video MODE=missing SCOPE=all` — baut Index-Snapshot + fehlende Thumbnails vor, ohne den Server zu starten
- `make video-reindex` — erzwingt kompletten Neuaufbau des Video-Index-Snapshots
- `make serve-all-safe` — startet beide Server im Safe-Mode
- `make issues` — zeigt aktuell offene Unregelmäßigkeiten aus Warnungen/Errors an
- `make issues-json` — gibt offene Unregelmäßigkeiten als JSON für Scheduler aus
- `make issues-errors` — liefert Exit-Code `1`, wenn offene Error/Critical-Issues existieren
- `make todos` — leitet priorisierte TODO-Kandidaten aus offenen Unregelmäßigkeiten ab
- `make scheduler-once` — führt den ersten Scheduler-Stub einmal aus, schreibt `todo_candidates.json` und berücksichtigt den TODO-Cooldown
- `make todo-state TODO_KEY=... TODO_ACTION=acknowledge|snooze|clear` — verwaltet manuelle TODO-Zustände

Für Automatisierung/Scheduler:

```powershell
hometools stream-issues --json
hometools stream-todos --json
hometools stream-scheduler --json
hometools stream-todo-state --todo-key todo::... --action acknowledge --reason "known issue"
hometools stream-todo-state --todo-key todo::... --action snooze --seconds 7200 --reason "later"
hometools stream-issues --only-errors --fail-on-match
```

Die Status-Endpunkte (`/api/audio/status`, `/api/video/status`) enthalten zusätzlich kompakte `issues`- und `todos`-Summaries, damit spätere Dashboards offene Unregelmäßigkeiten und aktive/snoozed/acknowledged Aufgaben direkt mit anzeigen können.

Die gemeinsame Streaming-UI nutzt diese `todos`-Summary inzwischen direkt und kann den obersten Task über denselben Shared-Core-Flow bestätigen, snoozen oder zurücksetzen. Beide Server verwenden dafür identische Endpunkte: `POST /api/audio/todos/state` bzw. `POST /api/video/todos/state`.

Safe-Mode (`HOMETOOLS_STREAM_SAFE_MODE=true` oder `--safe-mode`) deaktiviert absichtlich Snapshot-/Thumbnail-Warmups sowie Service-Worker-/Offline-Features. Gedacht als robuster Fallback, wenn NAS/UNC-Pfade oder Cache-Artefakte Probleme machen.

## Project Structure

```
src/hometools/
├── audio/              # Sanitization, metadata, silence removal, merging
├── streaming/
│   ├── core/           # Shared MediaItem model, catalog, sync, UI helpers
│   ├── audio/          # Audio catalog, sync and FastAPI server
│   └── video/          # Video catalog, sync and FastAPI server
├── video/              # TMDB-based movie & series renaming
├── cli.py              # CLI commands
├── config.py           # Environment-based configuration
├── constants.py        # Shared constants
├── utils.py            # File/path utilities
└── print_tools.py      # Terminal colors & diff highlighting
```

## Requirements

- Python >= 3.10
- ffmpeg (for silence removal / trimming / video thumbnails)
- A mounted NAS/share path if you want to use the manual sync workflow

## License

See [LICENSE](LICENSE).