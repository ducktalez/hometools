# hometools

A collection of Python tools for managing personal media libraries — music file sanitization, video organizing with TMDB, and local audio & video streaming prototypes with a shared core.

## 📚 Dokumentation

- **[docs/plans/](docs/plans/)** — Roadmap, Feature-Pläne (Offline, Native App, Server Refactoring, PWA Shortcuts, ...)
- **[docs/ios/](docs/ios/)** — iOS/PWA-Entscheidungen, Gerätetests, Test-Runbooks
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** — Coding-Regeln für Copilot/Agents

## Plan/TODOs

### 🔴 High Priority

- **Phase 1: Offline-Download Feature (PWA)** — ✅ Code fertig
  - Siehe [docs/plans/offline_feature.md](docs/plans/offline_feature.md)
  - ✅ Service Worker, Download UI, IndexedDB, Offline-Playback, Storage-Quota/Pruning, automatisierte Tests
  - 📱 **Manuelle Abnahme auf iPhone/iPad:** [docs/ios/quick_acceptance.md](docs/ios/quick_acceptance.md) (5 min) oder [docs/ios/device_validation.md](docs/ios/device_validation.md) (vollständig)

- **Phase 2: PWA Shortcuts — Quick Win** — Woche 2-3
  - Siehe [docs/plans/pwa_shortcuts.md](docs/plans/pwa_shortcuts.md)
  - Speichere einzelne Filme/Songs auf Home-Bildschirm
  - Deep Linking + Quick Access (~8-10h)
  - 🎯 Native-App-Feeling ohne native App
  - **Output:** Favoriten direkt zugänglich

- **Phase 3: Native iOS Apps (Hybrid WebView Wrapper)** — Woche 4-6
  - Siehe [docs/plans/native_app_plan.md](docs/plans/native_app_plan.md)
  - Zwei separate Apps: HometoolsVideo + HometoolsAudio
  - WebView Wrapper (reuse PWA-Code 100%)
  - Native Features: Background Audio, Lock Screen, Persistent Storage
  - **Strategy:** Minimal Swift Code (~2000 LOC total, vs. 15000+ pure native)
  - **Timeline:** ~3-4 weeks für beide Apps
  - **Output:** App Store ready native Apps mit voller iOS-Integration

### 🟡 Medium Priority
  - Ich will eine Seite, die den Serverstatus anzeigt und wichtige Managementaufgaben repräsentiert.
  - Vom Handy aus soll man die Metadaten von Files ändern können. Diese sollen aber nicht direkt eingetragen werden sondern in einer Liste festgehalten. Erst wenn man diese Liste im Management Server "akzeptiert" hat, werden die Metadaten in den Files festgeschrieben.
  - dynamisches synchronisieren: Die neuesten Änderungen müssen in einer Datenbank festgehalten werden so dass man das Handy zielgerichtet updaten kann.
  - Ein Scheduler, der die wichtigsten Aufgaben planbar und zyklisch ausführt.

### 🟡 Medium Priority

- Änderungen am Server müssen nicht mit erfolgreichen Tests der Tools abgeschlossen werden. Vielleicht kann man hier etwas Aufwand sparen. Das muss nur im Pre-Commit-Hook stattfinden, Nach Änderungen reicht es nur, die betroffenen Tests nochmal zu machen und auch bei denen nur wenn eine Änderung der Ergebnisse möglich ist. 
- Clean extensive device-checks. Are they all necessary?
- iphone-pitfall: der Pause-button ist immernoch ein emoji.
- Plan: Restrukturiere den Inhalt in Tools komplett neu und schreibe für alles, inklusive aller möglichen oder denkbaren Edge Cases Tests.
  - In WA Unterdaten findest du zwei LUTs, die hierfür herangezogen werden können. Vermutlich ist es dennoch sinnvoll, dieses Lookup Table File dauerhaft aus dem Repo zu entfernen und durch generelle Tests und Edge Cases zu ersetzen.
  - Ich halte beim Analysieren von sehr großen Datenbeständen Lookup Tables generell für eine gute Idee. So muss nicht bei jedem Test jedes Pfeil neu angeschaut werden. Bitte schaue hier was übliche State of the Art Lösungen sind.
  - Für die Tests sollten auch sehr einfache Dateien aller möglichen Audio- und Video-Files Teil des Tests sein. Entweder sollten diese automatisch generiert werden falls das denn möglich ist. Sie könnten zum Beispiel dummy Daten enthalten oder aber wir kopieren sehr kleine Files für die Tests in ein Testdir.
- Für den Video Server sollen folgende Regelungen zur Interpretation Der Ordner Struktur implementiert werden.
  - Es können Umbenennungen vorgeschlagen werden. Diese dürfen aber auf keinen Fall direkt durchgeführt werden sondern sollen als Liste generiert werden. In den Tools soll hier dafür auch der Code angepasst werden.
- Management Server & Scheduler
  - Status-Dashboard (Server, Syncs, Tasks)
  - Metadata-Änderungen in Review-Queue
  - Auto-Sync-Scheduler (regelmäßig NAS scannen)
- Fehler, Warnungen und Errors sollen zusätzlich zum in das Log auch noch in ein offener Aufgaben-File angefügt werden oder ein Unregelmäßigkeits File. Dieses wird dann von einem Task im Scheduler regelmäßig überprüft und hieraus müssen dann To-Dos erzeugt werden.
- OPTIONALE https-kommunikation. Es handelt sich um einen privaten Streaming-Server und wir erwarten keine Angriffe. HTTP ist schneller.
- Für englische Serien müssen die Metadaten anders geladen werden und das Programm, welches die Files automatisch umbennt, muss hier die englischen Titel etc. einfügen. Bisher ist das nicht der Fall.
- Implement a "Recently Added" section in the streaming UI
- Während des Scans der Files für den Audio- und Video Streaming Server: Hinweise wenn die Organisation mit dem Filesystem genügend Informationen gibt oder ob es Probleme geben kann
- "Malcolm mittendrin" (deutsch) vs. "Malcolm in the Middle" vs. "Malcolm Mittendrin [engl]" - Lösung finden.
  - Deutsche und englische Versionen einer Serie müssen irgendwie miteinander verlinkt werden, damit man nicht zwei Einträge in der UI hat.
  - Ich will eine Verlinkung bereits durch die richtige Namensgebung in der Ordnerstruktur ermöglichen. Ist das überhaupt eine gute Idee?
  - Ein Match wäre dann ein Match wenn der Serientitel im Ordner gleich ist, bloß mit einem "(engl)" oder "[engl]" dahinter. Die Files in dem Ordner sollen aber nach der original englischen Serie benannt werden. (zB. 'Malcolm Mittendrin (engl)/Malcolm in the Middle S01E01.mp4').
- Untertitelfiles verwenden und in die TMDB-Integration einbinden. Pfadanpassungen bei Namensänderungen nicht vergessen
- "swipe"-gesture für die mobile UI implementieren (z.B. für "Ordner nach oben/zurück gehen, ...")
- "Zufällige Wiedergabe" (shuffle) in der Audio-Streaming UI. Mit Long Touch soll ein anderer Shuffle-Modus genutzt werden bei dem die Songs proportional zu ihrer Bewertung häufiger oder weniger oft dran kommen.
- Songwertung (1–5 Sterne) in der UI anzeigen und in den ID3-POPM-Tags speichern
- Feature: "Ähnliche Titel" vorschlagen basierend auf Artist/Genre/Album (Audio) oder TMDB-Genre/Regisseur/Schauspieler (Video)
- Feature: "Wiedergabelisten" erstellen und verwalten in der Audio-Streaming UI, mit Möglichkeit zur manuellen Sortierung
- Feature: Tags bei Musik nutzen
- Videostreaming Medianeigenschaften taggen:
  - Sprache und Untertiteloptionen in Ordnern einblenden (nachladen, wenn vorhanden). Hier gilt zu beachten dass es mehrere Arten der Untertitel geben kann. Entweder sind sie als Files vorhanden oder aber das gesamte Video hat die Untertitel eingeblendet.
  - Auflösung ()ab 1080p, 4K, ...). Codec denkbar auch, aber ich sehe keinen direkten Nutzen davon
  - Bei mehreren Sprachen soll bei Klick auf eine der Sprach-Flaggen das entsprechende File ausgewählt werden.
  - Es soll angezeigt werden ob ein File heruntergeladen worden ist und wenn man drauf klickt soll man den Speicherplatz wieder freigeben können.
- Alle runtergeladenen Dateien sollen in einer Offline-Downloads-Liste aufgelistet werden.
- Filteroptionen für die Suche
- Minimum an HTTP-Sicherheit durch Obscurification? Verschlüsselung ist aufwendig.
  - Ich würde gerne HTTP als Standard lassen denn es ist ja ein privater Server.
  - Aber ich würde gerne eine komische Connection haben wollen damit das nicht bei dem Standardportscan direkt auffliegt.
  - Das heißt es würde ein Protokoll genutzt werden, das dazu führt dass die Schnittstelle bei einem Port Scan nicht antwortet wenn ein bestimmtes Bit an einer bestimmten Stelle nicht gesetzt ist. Es funktioniert nur wenn man eben da ein Passwort übergibt.
- DJ-feature (Plan):
  - Musiktitel übereinanderlegen (mixen)? Automatische Übergänge?
  - DJ-feature: songs automatisch aufeinander abstimmen (BPM, Tonart) und nahtlos überblenden. Besondere Songeigenschaften (zum mixen oder samplen) beim laden der lieder speichern (oder vom Nutzer beschreiben lassen).
- Anzeige von Songtexten (sofern in den ID3-Tags vorhanden) in der Audio-Streaming UI
- Plan: Einführung eines Management-servers, der die Synchronisation und das Streaming steuert, damit man nicht von Hand die Synchronisation und das Starten der Server triggern muss. Hier muss auch ein Scheduler regelmäßig die NAS-Ordner scannen und die Synchronisation triggern, damit die Streaming-Server immer auf dem neuesten Stand sind. Scheduler muss auch entwickelt werden.
- Plan: Letzte Wiedergabe + Fortschrittsanzeige in der Streaming-UI speichern, damit man auch von einem anderen Gerät aus weitermachen kann. Hier muss auch die Synchronisation der Fortschrittsdaten zwischen den Geräten implementiert werden (z.B. über eine JSON-Datei oder eine kleine Datenbank).
- "Intro überspringen" Feature für die Video-Streaming UI, basierend auf TMDB-Daten oder manueller Markierung
- "Crossfade" Feature für die Audio-Streaming UI, um nahtlose Übergänge zwischen Songs zu ermöglichen
- DJ-extension: Bei songs für die DJ-Nutzung sollten folgende Spuren extrahiert werden (Gespeichert im Schattenverzeichnis): Gesang, Instrumental, Bass/Beat. Loopregionen sollen festgelegt werden.
- DJ-extension: Um flüssige Übergänge zu ermöglichen müssen die BPM von Songs, die abweichen, schneller oder langsamer abgespielt werden können. Hier muss eine solche Funktion implementiert werden. Zusätzlich würde ich auch gerne bei einem Long Touch auf den Pause-Button eine Scroll-Funktion nach oben und unten aufploppen lassen, wo man die BPM einstellen kann und so auch die Abspiel-Geschwindigkeit verändern kann.
- DJ-extension: Zwischen Songs braucht Er ist ein Analyse-Autor, der schaut ob ein flüssiger Übergang möglich ist oder ob es eine andere Art von Übergang braucht.
- DJ-extension: "Keep something playing"-option, um zu verhindern, dass gar nichts läuft.
- DJ-extension: "Auto-DJ"-modus, in dem die Software automatisch Songs auswählt und Übergänge basierend auf den analysierten Eigenschaften erstellt, um eine kontinuierliche Wiedergabe zu gewährleisten. Hier sollte auch die Möglichkeit bedacht werden, eine Art Geschichte aus den Songs zu machen und verschiedene aufeinander folgende Themes etc. zu ermöglichen.
- "Fernsehsender", der automatisch (nach Plan) immer Serien oder Filme oder Musikvideos oder News abspielt. Lustig wäre, einen Plan für die Zukunft anzulegen und für diesen Plan kurze Werbung einzuspielen. Also quasi morgen 20:15 Uhr kommt Shrek. Auch diese kurzen Einspieler, die man früher hatte mit Toggo oder sowas, wären lustig.
- "Fernsehsender" MTV-version: Zu allen Liedern wird einfach das Musikvideo abgespielt, z.B. von YouTube. Musikvideos könnten auch hinterlegt werden. Ansonsten wird Musik abgespielt aber es gibt eine dazu passende visuelle Begleitung. Das heißt ein DJ bei Partymucke, irgendwelche Night Ride oder Surfvideos bei Drum&Bass oder auch nur ein Feuer. Auf jeden Fall soll irgendeine Visualisierung zu eigentlich vorrangig abgespielter Musik stattfinden.
- "Sleep Mode" Video stream radio: Gibt einfach nur das Audio aus einer Serie wieder so dass man aber keine Helligkeit hat beim Schlafen.
- Ein lennyface-board
- Server: Photo-Management: Alles online oder zumindest mit einem lokalen Server
- Jeder Nutzer hat eine andere Ordnerstruktur. Es wird zwar eine generelle Ordnerstruktur vorgegeben; jedoch sollte folgendes diskutiert werden.
  - Es sollte überlegt werden ob nicht mit N8N hier eine Logik generiert werden kann, auf jede Person zugeschnitten, damit alle Ordner richtig interpretiert werden.
- Wir sollten eine Liste führen mit Technologien, die in Zukunft eventuell ersetzt werden sollen. Entweder in Architecture oder Implementation Plan sollte hier vielleicht auch ein Diskussionsbereich für genau solche Überlegungen festgelegt werden. Wo hältst du es für am sinnvollsten? 

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