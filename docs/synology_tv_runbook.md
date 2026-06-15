# Runbook: hometools auf Synology NAS + Philips TV (Jellyfin-ähnlich)

Dieses Runbook bringt die hometools-Streaming-Server auf eine Synology
Diskstation (Docker / Container Manager) und zeigt, wie du vom Philips TV
darauf zugreifst.

## Konzeptvergleich zu Jellyfin

| Aspekt | Jellyfin | hometools |
|--------|----------|-----------|
| Server | Medienserver auf NAS | 2 FastAPI-Server (Audio :8010, Video :8011) auf NAS |
| Client | Native TV-Apps + Web | **Browser-PWA** (kein nativer TV-App-Store-Client) |
| TV-Zugriff | App / DLNA / Web | Browser-URL **oder** Casting vom Handy |
| Transcoding | Adaptiv pro Client (HLS) | Container-Remux + On-Demand-H.264-Transcode (Range/MP4) |
| DLNA | ja | **nein** (bewusst Browser-zentriert) |

Kurz: Das Konzept ist sehr ähnlich (Server auf NAS, Zugriff über das
Heimnetz), aber hometools setzt auf die **PWA im Browser** statt auf native
TV-Apps. Für Philips-TVs heißt das: TV-Browser öffnen **oder** vom Handy casten.

## 1. Repo auf die NAS bringen

**Variante A – SSH + git (empfohlen):**
```bash
# DSM → Systemsteuerung → Terminal & SNMP → SSH aktivieren
ssh deinuser@NAS-IP
sudo mkdir -p /volume1/docker && cd /volume1/docker
git clone https://github.com/ducktalez/hometools.git
cd hometools
```

**Variante B – ohne git:** Auf GitHub „Code → Download ZIP", entpacken und
den Ordner via File Station nach `/volume1/docker/hometools` legen.

## 1b. Ein-Befehl-Deploy (Skript)

Statt die Schritte 2–3 von Hand zu machen, gibt es ein idempotentes
Deploy-Skript, das **auf der NAS** läuft (nach `git clone`):

```bash
cd /volume1/docker/hometools
sudo bash scripts/deploy-synology.sh
```

Das Skript:
1. `git pull` (wenn es ein git-Checkout ist),
2. legt `.env` aus `docker/.env.synology.example` an und füllt **PUID/PGID**
   automatisch aus dem aufrufenden DSM-User; danach stoppt es **einmalig**,
   damit du die Bibliothekspfade in `.env` eintragen kannst,
3. prüft beim erneuten Lauf, dass die Library-Pfade existieren,
4. `docker compose up -d --build`,
5. zeigt die erreichbaren URLs + einen `/health`-Check.

Erneut ausführen = Update (git pull + Rebuild). Es nimmt **kein Passwort**
entgegen; Docker auf DSM braucht `sudo`.


## 2. `.env` anlegen

```bash
cp docker/.env.example .env
```

In `.env` anpassen:

- **PUID/PGID** – der DSM-User mit Leserechten auf deine Medien. Ermitteln:
  ```bash
  id deinuser        # z. B. uid=1026(simon) gid=100(users)
  ```
  → `PUID=1026`, `PGID=100`.
- **Bibliothekspfade** (die echten Freigaben auf der Diskstation):
  ```dotenv
  VIDEO_LIBRARY_PATH=/volume1/video
  ```
  > **Nur Video?** Per Default startet **ausschließlich der Video-Server**.
  > `AUDIO_LIBRARY_PATH` darf dann fehlen/leer bleiben — der Audio-Service
  > liegt hinter dem Compose-Profil `audio` und wird ohne `--profile audio`
  > (bzw. `ENABLE_AUDIO=1` beim Skript) gar nicht erst angelegt. Audio nur
  > aktivieren, wenn du eine Musik-Freigabe hast:
  > ```dotenv
  > AUDIO_LIBRARY_PATH=/volume1/music
  > ```
- Ports bei Bedarf (`AUDIO_PORT=8010`, `VIDEO_PORT=8011`).
- **Optional für TV** (Default **aus**): `HOMETOOLS_PRETRANSCODE=true`
  baut beim Start die **gesamte** Bibliothek (`.avi`/`.mkv`/XviD) im Hintergrund
  in Range-fähige MP4s um. ⚠️ Das kann den Cache-Datenträger stark füllen
  (eine große `.avi`-Sammlung → leicht zweistellige GB). Ohne diese Option
  werden Nicht-MP4-Dateien **on-demand beim Abspielen** transkodiert — der Cache
  bleibt dann proportional zum tatsächlich Geschauten.

## 3. Starten

**Container Manager (DSM 7.2+):**
1. Container Manager → **Projekt** → **Erstellen**.
2. Pfad: `/volume1/docker/hometools` (enthält `docker-compose.yml`).
3. Container Manager erkennt die Compose-Datei → **Erstellen + Starten**
   (baut das Image beim ersten Mal, dauert ein paar Minuten).

**Oder per SSH:**
```bash
docker compose up -d --build          # startet nur den Video-Server (Default)
docker compose logs -f video          # Startfortschritt
```

> **Audio zusätzlich** (optional): `docker compose --profile audio up -d --build`.
> Ohne `--profile audio` wird der Audio-Container nicht angelegt, und ein
> fehlender/leerer `AUDIO_LIBRARY_PATH` ist dann **kein** Fehler.

Erreichbar:
- Video: `http://NAS-IP:8011`
- Audio (nur mit `--profile audio`): `http://NAS-IP:8010`

DSM-Firewall: ggf. Ports **8010/8011** für das LAN freigeben
(Systemsteuerung → Sicherheit → Firewall).

## 3b. Komplett über den Container Manager (ohne SSH) — Schritt für Schritt

Der gesamte Ablauf geht rein über die DSM-Oberfläche. Voraussetzung:
**Container Manager** ist im Paket-Zentrum installiert und du bist auf
**DSM 7.2 oder neuer** (dort kann Container Manager Projekte aus einem
`Dockerfile` **bauen**; bei DSM 7.0/7.1 fehlt die Build-Funktion — siehe
Hinweis unten).

**Schritt 1 — Repo-Ordner auf die NAS legen (File Station):**
1. Am PC auf GitHub: **Code → Download ZIP**, entpacken.
2. In DSM **File Station** einen Ordner anlegen, z. B. `docker/hometools`
   (unter einer freigegebenen Volume, also `/volume1/docker/hometools`).
3. Den **kompletten** entpackten Repo-Inhalt dort hochladen
   (`Dockerfile`, `docker-compose.yml`, `src/`, `pyproject.toml`,
   `requirements.txt`, … — der ganze Projektbaum, weil das Image aus dem
   Quellcode gebaut wird).

**Schritt 2 — `.env` im Projektordner erstellen:**
1. In File Station in `docker/hometools` die Datei `docker/.env.example`
   markieren → **Kopieren** → in denselben Ordner einfügen und in **`.env`**
   umbenennen (Endung wirklich `.env`, kein `.env.txt`).
2. `.env` mit dem **Texteditor** von File Station öffnen und setzen:
   - `PUID` / `PGID` (DSM-User-IDs; siehe Abschnitt 2).
   - `AUDIO_LIBRARY_PATH=/volume1/music`, `VIDEO_LIBRARY_PATH=/volume1/video`.
   - optional `HOMETOOLS_PRETRANSCODE=true` (Default **aus**; transkodiert beim Start die ganze Bibliothek — Cache-Speicher beachten).

   > Wird `.env` nicht gefunden, bricht der Build mit
   > „set VIDEO_LIBRARY_PATH in .env" ab — dann liegt die Datei nicht im
   > Projektordner oder heißt falsch.

**Schritt 3 — Projekt im Container Manager anlegen:**
1. **Container Manager → Projekt → Erstellen**.
2. **Projektname:** z. B. `hometools`.
3. **Pfad:** den Ordner `/volume1/docker/hometools` wählen.
4. **Quelle:** „Verwende vorhandene `docker-compose.yml`" (Container Manager
   liest die Compose-Datei aus dem Ordner ein und zeigt sie zur Kontrolle an).
5. Den Assistenten durchklicken (Web-Portal-Frage kannst du überspringen).
6. **Erstellen** → Container Manager **baut das Image** und startet die
   Container `hometools-audio` und `hometools-video`. Den Fortschritt siehst
   du im Tab **Protokoll/Log** des Projekts.

**Schritt 4 — Prüfen:**
- Projekt-Status muss **„running"** sein (grün).
- Im Browser `http://NAS-IP:8011` öffnen → die Video-PWA lädt.
- Bei Fehlern: Projekt → **Protokoll** ansehen (häufig PUID/PGID- oder
  Pfad-Themen, siehe Troubleshooting unten).

**Updates über den Container Manager:** Neue Repo-Version per File Station
über den Ordner kopieren (oder ZIP neu hochladen) → Projekt → **Erstellen
neu/Build** → **Aktion → Neu erstellen**. Die Daten-Volumes (`hometools-cache`,
`hometools-audit`) bleiben erhalten.

> **DSM 7.0 / 7.1 (kein Build im Projekt):** Dort kann das Projekt kein Image
> aus dem `Dockerfile` bauen. Optionen:
> 1. Auf DSM 7.2 aktualisieren (empfohlen), **oder**
> 2. das Image auf einem PC mit Docker bauen
>    (`docker build -t hometools:latest .`), als Tar exportieren
>    (`docker save hometools:latest -o hometools.tar`), in DSM
>    **Container Manager → Abbild → Hinzufügen → Von Datei** importieren und im
>    Compose die `build:`-Blöcke durch `image: hometools:latest` ersetzen.

## 4. Zugriff vom Philips TV

Philips-TVs laufen je nach Modell unter verschiedenen Systemen – das
bestimmt den besten Weg:

### a) Philips mit Android TV / Google TV (Modelle mit Google-Logo)
- **Browser:** Eine Browser-App installieren (z. B. „TV Bro" aus dem Play
  Store, da der vorinstallierte Browser oft fehlt) und `http://NAS-IP:8011`
  öffnen. Die PWA lädt, Videos spielen im Chromium-WebView des TVs.
- **Casting (am bequemsten):** Video am Handy in **Chrome** öffnen
  (`http://NAS-IP:8011`), im Video-Overlay den **Cast-Button** tippen und den
  TV (Chromecast built-in) wählen. Das Bild läuft dann auf dem TV, das Handy
  ist die Fernbedienung.

### b) Philips mit Saphi / Titan OS (Nicht-Android, Mittelklasse)
- **Eingebauter Browser:** Im App-Menü „Web Browser" öffnen und
  `http://NAS-IP:8011` ansurfen. Funktioniert für **MP4/H.264** gut; PWA- und
  Codec-Support ist eingeschränkter als bei Chrome.
- **Zuverlässiger:** Vom Handy casten (siehe oben), wenn das Gerät Chromecast
  built-in / AirPlay hat.

### c) Tipp für alle Philips-TVs
- TV und NAS müssen im **selben Netz/Subnetz** sein.
- Falls der TV-Browser ein Video nicht abspielt: liegt fast immer am Codec.
  Mit `HOMETOOLS_PRETRANSCODE=true` werden Nicht-MP4-Container in H.264/AAC-MP4
  vorkonvertiert. Beim **ersten** Antippen einer großen `.avi` kann der
  Hintergrund-Transcode noch laufen – kurz warten / erneut starten.

## 5. „Zum Startbildschirm hinzufügen" (PWA)

Auf Android-TV-Chrome bzw. am Handy kann die Video-Seite als PWA installiert
werden (Menü → „Zum Startbildschirm/Installieren"). Dann startet sie wie eine
App im Vollbild – das kommt der Jellyfin-App am nächsten.

## 6. Schreibrechte (optional)

Standardmäßig sind beide Bibliotheken **read-only** gemountet (`:ro`).
Ratings, Tag-Edits, Datei-Verschieben/Löschen brauchen Schreibzugriff →
`:ro` beim jeweiligen Volume in `docker-compose.yml` entfernen und PUID/PGID
mit Schreibrechten verwenden. Details: `docs/docker.md`.

## 7. Updates

```bash
cd /volume1/docker/hometools
git pull
docker compose build --pull && docker compose up -d
```
Die `hometools-cache`/`hometools-audit`-Volumes (Thumbnails, Index, Audit)
bleiben erhalten.

## Troubleshooting

| Symptom | Ursache / Lösung |
|---------|------------------|
| Build bricht ab: `groupadd: GID '100' already exists` | `PGID=100` (Synology-Gruppe `users`) existiert im Image bereits. Aktuelle `Dockerfile`-Version ziehen (`git pull`) — sie legt Gruppe/User nur an, wenn die ID noch fehlt. Ad-hoc ohne Pull: im `Dockerfile` den `RUN groupadd …`-Block durch die getent-Variante ersetzen (siehe README/Runbook). |
| Build/Start bricht ab, „AUDIO_LIBRARY_PATH … does not exist" / Musikordner fehlt | Du willst nur Video → Audio ist optional. Mit `docker compose up -d --build` (ohne `--profile audio`) wird der Audio-Container gar nicht angelegt; `AUDIO_LIBRARY_PATH` darf leer bleiben. Falls eine alte `.env` noch `AUDIO_LIBRARY_PATH:?` erzwang: aktuelle `docker-compose.yml` ziehen (`git pull`). |
| `/health` nicht erreichbar | Firewall-Port nicht offen, oder Container nicht „running" (`docker compose ps`). |
| „Permission denied" beim Library-Lesen | PUID/PGID stimmen nicht mit der Datei-Ownership überein (`docker exec hometools-video id`). |
| `.avi` lädt am TV nicht | `HOMETOOLS_PRETRANSCODE=true` setzen; ffmpeg ist im Image enthalten; erste Konvertierung im Hintergrund abwarten. |
| Cast-Button fehlt | Client-Browser muss Remote-Playback können (Chrome/Edge/Android, iOS-Safari). Firefox kann es nicht. |
| TV-Browser zeigt nur Tonspur | Codec/Container nicht TV-tauglich → Pre-Transcode greifen lassen oder Quelle als H.264-MP4 bereitstellen. |

> Siehe auch `docs/docker.md` (allgemeiner Docker-Betrieb) und die Hinweise zu
> Cast/Netzwerk/VLAN dort.




