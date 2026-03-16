# hometools

A collection of Python tools for managing personal media libraries — music file sanitization, video organizing with TMDB, and local audio & video streaming prototypes with a shared core.


## Plan/TODOs

- dynamisches synchronisieren: Update an Handy schicken
- Metadaten vom Handy aus ändern soll auch Änderungen im Filesystem triggern. Hier soll aber nur eine Liste generiert werden, die dann am PC "akzeptiert" werden kann.
- Implement a "Recently Added" section in the streaming UI
- Während des Scans der Files für den Audio- und Video Streaming Server: Hinweise wenn die Organisation mit dem Filesystem genügend Informationen gibt oder ob es Probleme
- "Malcolm mittendrin" (deutsch) vs. "Malcolm in the Middle" vs. "Malcolm Mittendrin [engl]" - Lösung finden
- Untertitelfiles verwenden und in die TMDB-Integration einbinden. Pfadanpassungen bei Namensänderungen nicht vergessen
- "swipe"-gesture für die mobile UI implementieren (z.B. für "Ordner nach oben/zurück gehen, ...")
- Album-cover/thumbnail bei Video- und Audio-Streaming anzeigen
- "Zufällige Wiedergabe" (shuffle) in der Audio-Streaming UI
- Songwertung (1–5 Sterne) in der UI anzeigen und in den ID3-POPM-Tags speichern
- Feature: "Ähnliche Titel" vorschlagen basierend auf Artist/Genre/Album (Audio) oder TMDB-Genre/Regisseur/Schauspieler (Video)
- Feature: "Wiedergabelisten" erstellen und verwalten in der Audio-Streaming UI, mit Möglichkeit zur manuellen Sortierung
- Feature: Tags bei Musik nutzen
- Videostreaming: Sprache und Untertiteloptionen in Ordnern einblenden (nachladen, wenn vorhanden). Hier gilt zu beachten dass es mehrere Arten der Untertitel geben kann. Entweder sind sie als Files vorhanden oder aber das gesamte Video hat die Untertitel eingeblendet. 
- Feature: Musiktitel übereinanderlegen (mixen)? Automatische Übergänge?
- DJ-feature: songs automatisch aufeinander abstimmen (BPM, Tonart) und nahtlos überblenden. Besondere Songeigenschaften (zum mixen oder samplen) beim laden der lieder speichern (oder vom Nutzer beschreiben lassen).
- Anzeige von Songtexten (sofern in den ID3-Tags vorhanden) in der Audio-Streaming UI
- Anzeige des Vorspul-balkens als die Welleform des Songs (ggf. mit markierten Stellen für Strophen/Refrains) in der Audio-Streaming UI und mit Thumbnails beim Video-Streaming.
- Plan: Einführung eines Management-servers, der die Synchronisation und das Streaming steuert, damit man nicht von Hand die Synchronisation und das Starten der Server triggern muss. Hier muss auch ein Scheduler regelmäßig die NAS-Ordner scannen und die Synchronisation triggern, damit die Streaming-Server immer auf dem neuesten Stand sind. Scheduler muss auch entwickelt werden.
- Plan: Letzte Wiedergabe + Fortschrittsanzeige in der Streaming-UI speichern, damit man auch von einem anderen Gerät aus weitermachen kann. Hier muss auch die Synchronisation der Fortschrittsdaten zwischen den Geräten implementiert werden (z.B. über eine JSON-Datei oder eine kleine Datenbank).
- Plan: Implementierung eines "Offline-Modus", Downloads ermöglichen, Speicherfreigabe ebenfalls ermöglichen
- "Intro überspringen" Feature für die Video-Streaming UI, basierend auf TMDB-Daten oder manueller Markierung
- "Crossfade" Feature für die Audio-Streaming UI, um nahtlose Übergänge zwischen Songs zu ermöglichen
- DJ-extended: Bei songs für die DJ-Nutzung sollten folgende Spuren extrahiert werden: Gesang, Instrumental, Bass/Beat. Loopregionen sollen festgelegt werden.
- DJ-extension: Zwischen Songs braucht Er ist ein Analyse-Autor, der schaut ob ein flüssiger Übergang möglich ist oder ob es eine andere Art von Übergang braucht.
- DJ-extension: "Keep something playing"-option, um zu verhindern, dass gar nichts läuft.
- DJ-extension: "Auto-DJ"-modus, in dem die Software automatisch Songs auswählt und Übergänge basierend auf den analysierten Eigenschaften erstellt, um eine kontinuierliche Wiedergabe zu gewährleisten. Hier sollte auch die Möglichkeit bedacht werden, eine Art Geschichte aus den Songs zu machen und verschiedene aufeinander folgende Themes etc. zu ermöglichen. 
- "Fernsehsender", der automatisch (nach Plan) immer Serien oder Filme Oder Musikvideos oder News abspielt. 

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