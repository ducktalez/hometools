# hometools

A collection of Python tools for managing personal media libraries — music file sanitization, video organizing with TMDB, and local audio & video streaming prototypes with a shared core.


## Plan/TODOs

- Management Server.
  - Ich will eine Seite, die den Serverstatus anzeigt und wichtige Managementaufgaben repräsentiert.
  - Vom Handy aus soll man die Metadaten von Files ändern können. Diese sollen aber nicht direkt eingetragen werden sondern in einer Liste festgehalten. Erst wenn man diese Liste im Management Server "akzeptiert" hat, werden die Metadaten in den Files festgeschrieben. 
  - dynamisches synchronisieren: Die neuesten Änderungen müssen in einer Datenbank festgehalten werden so dass man das Handy zielgerichtet updaten kann.
  - Ein Scheduler, der die wichtigsten Aufgaben planbar und zyklisch ausführt.  
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
- Filteroptionen für die Suche
- DJ-feature (Plan): 
  - Musiktitel übereinanderlegen (mixen)? Automatische Übergänge?
  - DJ-feature: songs automatisch aufeinander abstimmen (BPM, Tonart) und nahtlos überblenden. Besondere Songeigenschaften (zum mixen oder samplen) beim laden der lieder speichern (oder vom Nutzer beschreiben lassen).
- Anzeige von Songtexten (sofern in den ID3-Tags vorhanden) in der Audio-Streaming UI
- Plan: Einführung eines Management-servers, der die Synchronisation und das Streaming steuert, damit man nicht von Hand die Synchronisation und das Starten der Server triggern muss. Hier muss auch ein Scheduler regelmäßig die NAS-Ordner scannen und die Synchronisation triggern, damit die Streaming-Server immer auf dem neuesten Stand sind. Scheduler muss auch entwickelt werden.
- Plan: Letzte Wiedergabe + Fortschrittsanzeige in der Streaming-UI speichern, damit man auch von einem anderen Gerät aus weitermachen kann. Hier muss auch die Synchronisation der Fortschrittsdaten zwischen den Geräten implementiert werden (z.B. über eine JSON-Datei oder eine kleine Datenbank).
- Plan: Implementierung eines "Offline-Modus", Downloads ermöglichen, Speicherfreigabe ebenfalls ermöglichen
- "Intro überspringen" Feature für die Video-Streaming UI, basierend auf TMDB-Daten oder manueller Markierung
- "Crossfade" Feature für die Audio-Streaming UI, um nahtlose Übergänge zwischen Songs zu ermöglichen
- DJ-extension: Bei songs für die DJ-Nutzung sollten folgende Spuren extrahiert werden (Gespeichert im Schattenverzeichnis): Gesang, Instrumental, Bass/Beat. Loopregionen sollen festgelegt werden.
- DJ-extension: Um flüssige Übergänge zu ermöglichen müssen die BPM von Songs, die abweichen, schneller oder langsamer abgespielt werden können. Hier muss eine solche Funktion implementiert werden. Zusätzlich würde ich auch gerne bei einem Long Touch auf den Pause-Button eine Scroll-Funktion nach oben und unten aufploppen lassen, wo man die BPM einstellen kann und so auch die Abspiel-Geschwindigkeit verändern kann. 
- DJ-extension: Zwischen Songs braucht Er ist ein Analyse-Autor, der schaut ob ein flüssiger Übergang möglich ist oder ob es eine andere Art von Übergang braucht. 
- DJ-extension: "Keep something playing"-option, um zu verhindern, dass gar nichts läuft.
- DJ-extension: "Auto-DJ"-modus, in dem die Software automatisch Songs auswählt und Übergänge basierend auf den analysierten Eigenschaften erstellt, um eine kontinuierliche Wiedergabe zu gewährleisten. Hier sollte auch die Möglichkeit bedacht werden, eine Art Geschichte aus den Songs zu machen und verschiedene aufeinander folgende Themes etc. zu ermöglichen. 
- "Fernsehsender", der automatisch (nach Plan) immer Serien oder Filme oder Musikvideos oder News abspielt.
- Photo-Management: Alles online oder zumindest mit einem lokalen Server

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
- **Browser-based audio player** — dark-theme web UI with search, artist filter, sort, and bottom player bar (⏮ ▶ ⏭ + progress)
- **Browser-based video player** — same UI as audio but with an inline `<video>` element, folder-based filtering
- **Track discovery controls** — search by title/artist/path, filter by artist or folder, sort by multiple fields
- **iPhone-friendly MVP** — no native iOS client, no Xcode project, just local web apps accessible via Safari

## Quick Start

```bash
# Clone and set up
git clone https://github.com/ducktalez/hometools.git
cd hometools
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"

# Configure secrets and paths
Copy-Item .env.example .env
# Edit .env with your TMDB_API_KEY and library paths

# Run tests
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
HOMETOOLS_AUDIO_PORT=8000
HOMETOOLS_VIDEO_PORT=8001
```

### Both servers at once

```powershell
hometools streaming-config        # show current config overview
hometools serve-all               # start audio (:8000) + video (:8001)
hometools setup-pycharm           # generate PyCharm run configurations
```

### Audio

```powershell
hometools sync-audio --dry-run    # preview
hometools sync-audio              # copy files
hometools serve-audio             # start web UI → http://127.0.0.1:8000/
```

### Video

```powershell
hometools sync-video --dry-run    # preview
hometools sync-video              # copy files
hometools serve-video             # start web UI → http://127.0.0.1:8001/
```

Both servers share the same dark-theme UI. Open them from any device on your home network (including Safari on iPhone).

## Project Structure

See [INSTRUCTIONS.md](.github/INSTRUCTIONS.md) for detailed module documentation and developer guidelines.

Regenerate the developer instructions after structural changes:

```powershell
hometools update-instructions
```

```
src/hometools/
├── audio/              # Sanitization, metadata, silence removal, merging
├── streaming/
│   ├── core/           # Shared MediaItem model, catalog, sync, UI helpers
│   ├── audio/          # Audio catalog, sync and FastAPI server
│   └── video/          # Video catalog, sync and FastAPI server
├── video/              # TMDB-based movie & series renaming
├── cli.py              # CLI commands for sync, streaming and maintenance
├── config.py           # Environment-based configuration
├── constants.py        # Shared constants
├── utils.py            # File/path utilities
└── print_tools.py      # Terminal colors & diff highlighting
```

## Requirements

- Python >= 3.10
- ffmpeg (for silence removal / trimming)
- A mounted NAS/share path if you want to use the manual sync workflow

## License

See [LICENSE](LICENSE).