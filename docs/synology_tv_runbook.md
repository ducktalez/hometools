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
  AUDIO_LIBRARY_PATH=/volume1/music
  VIDEO_LIBRARY_PATH=/volume1/video
  ```
- Ports bei Bedarf (`AUDIO_PORT=8010`, `VIDEO_PORT=8011`).
- **Empfohlen für TV** (Default bereits an): `HOMETOOLS_PRETRANSCODE=true`
  baut `.avi`/`.mkv`/XviD im Hintergrund in Range-fähige MP4s um, damit sie
  im TV-Browser laufen (sonst spielen nur native MP4/H.264).

## 3. Starten

**Container Manager (DSM 7.2+):**
1. Container Manager → **Projekt** → **Erstellen**.
2. Pfad: `/volume1/docker/hometools` (enthält `docker-compose.yml`).
3. Container Manager erkennt die Compose-Datei → **Erstellen + Starten**
   (baut das Image beim ersten Mal, dauert ein paar Minuten).

**Oder per SSH:**
```bash
docker compose up -d --build
docker compose logs -f video      # Startfortschritt
```

Erreichbar:
- Audio: `http://NAS-IP:8010`
- Video: `http://NAS-IP:8011`

DSM-Firewall: ggf. Ports **8010/8011** für das LAN freigeben
(Systemsteuerung → Sicherheit → Firewall).

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
| `/health` nicht erreichbar | Firewall-Port nicht offen, oder Container nicht „running" (`docker compose ps`). |
| „Permission denied" beim Library-Lesen | PUID/PGID stimmen nicht mit der Datei-Ownership überein (`docker exec hometools-video id`). |
| `.avi` lädt am TV nicht | `HOMETOOLS_PRETRANSCODE=true` setzen; ffmpeg ist im Image enthalten; erste Konvertierung im Hintergrund abwarten. |
| Cast-Button fehlt | Client-Browser muss Remote-Playback können (Chrome/Edge/Android, iOS-Safari). Firefox kann es nicht. |
| TV-Browser zeigt nur Tonspur | Codec/Container nicht TV-tauglich → Pre-Transcode greifen lassen oder Quelle als H.264-MP4 bereitstellen. |

> Siehe auch `docs/docker.md` (allgemeiner Docker-Betrieb) und die Hinweise zu
> Cast/Netzwerk/VLAN dort.

