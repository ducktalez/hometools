# Docker-Betrieb

## Quickstart (Linux / Mac / Synology DSM)

```bash
cp docker/.env.example .env
# In .env: AUDIO_LIBRARY_PATH und VIDEO_LIBRARY_PATH eintragen
docker compose up -d --build
```

Erreichbar:

- Audio: <http://HOST:8010>
- Video: <http://HOST:8011>
- Channel (optional, im Compose auskommentiert): <http://HOST:8012>

## Architektur

Multi-Stage-Image (Python 3.12-slim + ffmpeg + tini, Non-Root-User).
Compose startet pro Service einen eigenen Container — gemeinsames Image,
getrennte Prozesse. Drei Container teilen sich die Volumes für Cache
und Audit-Log, aber jeder Service hat seine eigene Bibliothek.

| Service   | Port  | Command         | Library-Mount     |
|-----------|-------|-----------------|-------------------|
| `audio`   | 8010  | `serve-audio`   | `/media/audio:ro` |
| `video`   | 8011  | `serve-video`   | `/media/video:ro` |
| `channel` | 8012  | `serve-channel` | `/media/video:ro` + `channel_schedule.yaml` |

Alternativ kann der auskommentierte `all-in-one`-Service aktiviert werden,
der über `serve-all` alle drei Server in einem Container laufen lässt
(geringerer Footprint, aber weniger isoliert).

## Bibliothekspfade

Beide Bibliotheken werden **read-only** in den Container gemountet
(`:ro` im Compose). hometools selbst schreibt **nur** in:

| Containerpfad | Compose-Volume     | Inhalt                                    |
|---------------|--------------------|-------------------------------------------|
| `/data/cache` | `hometools-cache`  | Thumbnails, Waveforms, Index-Snapshots, Logs |
| `/data/audit` | `hometools-audit`  | Permanentes Audit-Log (Ratings, Tag-Edits) |

Schreiboperationen auf Originaldateien (Rating-POPM, Tag-Edit, File-Move,
Soft-Delete) funktionieren also **nicht** mit `:ro`-Mount. Wenn du diese
Features brauchst, in `docker-compose.yml` das `:ro` aus dem entsprechenden
Volume entfernen — *Audio:* meist gewünscht, *Video:* selten.

## Synology — Schritt für Schritt

1. **DSM → Container Manager → Projekt → Erstellen.**
2. Quelle: „Projekt aus docker-compose.yml hochladen".
3. Beide Dateien hochladen: `docker-compose.yml` + `.env`.
4. Vor dem Start in `.env` setzen:
   - `PUID` / `PGID` auf den DSM-User mit Lesezugriff auf die Volumes.
   - `AUDIO_LIBRARY_PATH` / `VIDEO_LIBRARY_PATH` auf die Diskstation-Pfade
     (z. B. `/volume1/music`, `/volume1/video`).
5. „Erstellen + Starten".
6. In der Synology-Firewall ggf. Ports 8010/8011 freischalten.

> **Hinweis:** Wenn der Container die Diskstation-Pfade nicht lesen kann,
> liegt es fast immer am PUID/PGID-Mismatch. `id <username>` in der DSM-
> Shell liefert die richtigen Werte.

## Schreibrechte für Rating-Updates / Tag-Edit

Damit POPM-Ratings, ID3-Tag-Edits, File-Move und Soft-Delete funktionieren:

1. `:ro` aus dem entsprechenden Volume entfernen.
2. PUID/PGID müssen **Schreibrechte** auf den Bibliotheksdateien haben.
3. Soft-Delete schreibt in `HOMETOOLS_DELETE_DIR` — Default
   `~/Music/DELETE_ME` im Container. Bei Bedarf via Env überschreiben und
   als weiteres Volume mounten.

## Cast / Chromecast aufs TV

Der Cast-Button im Video-Overlay nutzt die HTML5 Remote Playback API.
Der Browser des Clients (Android-Chrome, Desktop-Chrome, iOS Safari)
streamt direkt zum Cast-Ziel — der Docker-Container ist *nicht* am
Casting beteiligt, **muss aber für das Cast-Gerät erreichbar sein**
(gleiches Subnetz / kein Firewall-Block).

Wenn TV und Docker-Host in unterschiedlichen VLANs liegen, hilft entweder
ein gemeinsames VLAN oder das Aktivieren von `network_mode: host` für den
Video-Service im Compose (dann braucht es keine Port-Mappings mehr,
aber Healthcheck-Port und Bind-Host müssen passen).

## Logs

```bash
docker compose logs -f audio
docker compose logs -f video
```

Die per `logging_config.setup_logging` konfigurierten rotierenden Logs
(5 MB × 3 Backups) landen zusätzlich im Cache-Volume unter
`/data/cache/logs/`.

## Updates

```bash
git pull
docker compose build --pull
docker compose up -d
```

Die `hometools-cache`- und `hometools-audit`-Volumes bleiben erhalten.

## Aufräumen

```bash
docker compose down                 # Container stoppen, Volumes erhalten
docker compose down -v              # ⚠️  inkl. Cache+Audit-Volumes löschen
docker image rm hometools:latest
```

## Troubleshooting

- **Container startet, aber `/health` nicht erreichbar:** Prüfe, ob
  `HOMETOOLS_STREAM_HOST=0.0.0.0` im Container gesetzt ist (Default im
  Image). Bei `127.0.0.1` ist von außen nichts erreichbar.
- **Permission denied beim Lesen der Library:** PUID/PGID-Mismatch.
  `docker exec hometools-audio id` zeigt die User-ID des Container-Prozesses;
  die muss zur Datei-Ownership auf dem Host passen.
- **`Cast-Button erscheint nicht`:** Browser des Clients prüfen
  (`chrome://media-router`). Firefox unterstützt Remote-Playback nicht.

