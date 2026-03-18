# iPhone / iPad PWA Test Runbook

## Zweck

Dieses Runbook ist die **praktische Brücke** zwischen:

- [quick_acceptance.md](quick_acceptance.md) — 5-Minuten-Schnelltest
- [device_validation.md](device_validation.md) — vollständige Geräteabnahme

Es beschreibt den **konkreten Ablauf für das aktuelle Setup** in diesem Repository.

---

## Verifiziertes aktuelles Setup

Diese Werte wurden lokal aus der aktuellen Konfiguration gelesen:

- `HOMETOOLS_STREAM_HOST = 0.0.0.0`
- Audio-Port: `8010`
- Video-Port: `8011`
- `HOMETOOLS_VIDEO_PWA_DISPLAY = minimal-ui`

Verfügbare IPv4-Adressen auf dem Rechner:

- `192.168.178.21` ← **wahrscheinlich die richtige LAN-Adresse fürs iPhone**
- `172.17.176.1` ← eher virtuelle/Host-intern
- `172.19.160.1` ← eher virtuelle/Host-intern

> Für das iPhone im Heimnetz solltest du sehr wahrscheinlich diese URLs verwenden:
>
> - Audio: `http://192.168.178.21:8010/`
> - Video: `http://192.168.178.21:8011/`

Wenn der Rechner oder das Netz wechselt, bitte die vom CLI-Banner angezeigten Adressen bevorzugen.

---

## Server starten

Im Projektverzeichnis:

```powershell
hometools serve-all
```

Alternativ getrennt:

```powershell
hometools serve-audio
hometools serve-video
```

Beim Start zeigt das CLI bereits die relevanten Verbindungsadressen an.
Siehe dazu auch `_print_server_banner` in `src/hometools/cli.py`.

---

## Testreihenfolge

Die schnellste sinnvolle Reihenfolge ist:

1. **Audio in Safari** testen
2. **Video in Safari** testen
3. **Falls Safari ok:** Home-Screen-Version testen
4. **Dann erst** Detailfälle / große Dateien / Quota prüfen

Warum so?
- Audio ist meist der schnellste Smoke-Test
- Video deckt zusätzlich Seek / größere Blobs / Offline-Range-Support ab
- Home-Screen kann auf iOS anders reagieren als Safari

---

## Teil A — Safari-Tab

### 1. Audio öffnen
Auf dem iPhone in Safari öffnen:

```text
http://192.168.178.21:8010/
```

Prüfen:
- UI lädt vollständig
- `Offline`-Button sichtbar
- Titel startet bei Klick
- Download eines Songs funktioniert
- Song lässt sich offline erneut starten

### 2. Video öffnen
Dann in Safari öffnen:

```text
http://192.168.178.21:8011/
```

Prüfen:
- UI lädt vollständig
- Video startet bei Klick
- Download eines Videos funktioniert
- Offline-Playback funktioniert
- Seek / Scrubbing funktioniert offline weiter

---

## Teil B — Home-Screen / installierte Web-App

### 1. Audio oder Video zu Home-Screen hinzufügen
In Safari:
- Teilen-Menü öffnen
- „Zum Home-Bildschirm“ wählen
- Shortcut starten

### 2. Dasselbe nochmals testen
Mindestens einen kurzen Lauf wiederholen:
- Download starten
- App schließen
- offline gehen
- App erneut öffnen
- Download erneut starten

> Wichtig: Für Video ist aktuell `minimal-ui` konfiguriert. Das ist bewusst so gewählt, damit die Media-APIs auf iOS besser verfügbar bleiben.

---

## Teil C — Offline-Test ohne Rätselraten

Für einen klaren Offline-Test gibt es zwei gute Varianten:

### Variante 1: Flugmodus auf dem iPhone
- Medium herunterladen
- Flugmodus aktivieren
- Seite/App neu öffnen
- denselben Download starten

### Variante 2: Server kurz stoppen
- Medium herunterladen
- Server am Rechner stoppen
- Seite/App neu öffnen
- denselben Download starten

Wenn das Medium dann noch läuft, kommt es **nicht mehr vom Server**.

---

## Teil D — Was du am besten zuerst testest

### Schnellster Audio-Test
- einen kleinen Song nehmen
- downloaden
- Flugmodus
- offline starten
- kurz spulen
- wieder löschen

### Schnellster Video-Test
- ein kurzes Video nehmen
- downloaden
- offline starten
- 2–3 Mal auf andere Zeitpunkte springen
- wieder löschen

### Quota-Test
- danach ein größeres Video nehmen
- Speicheranzeige in der Offline-Bibliothek beobachten
- prüfen, ob Warnung / Aufräumen plausibel wirkt

---

## Erwartete PASS-Kriterien

Der Lauf ist für Phase 1 praktisch gut genug, wenn mindestens das hier klappt:

- Audio-Download in Safari klappt
- Audio spielt offline erneut ab
- Video-Download in Safari klappt
- Video spielt offline erneut ab
- Video-Seek funktioniert offline
- Download lässt sich wieder löschen

Wenn Safari funktioniert, aber Home-Screen nicht sauber ist:
- **nicht sofort alles als kaputt werten**
- stattdessen Ergebnis als **„PASS mit Einschränkung“** notieren
- Details in [device_validation.md](device_validation.md) eintragen

---

## Rückmeldung nach dem Test

Nach dem Lauf am besten genau dieses Mini-Format verwenden:

```text
Datum:
Gerät / iOS:
Kontext: Safari / Home-Screen
Audio: PASS / PASS mit Einschränkung / FAIL
Video: PASS / PASS mit Einschränkung / FAIL
Offline-Seek: PASS / PASS mit Einschränkung / FAIL
Notizen:
```

Danach sollten die Ergebnisse in folgenden Dateien nachgezogen werden:

- *(Phase 1 Status — archived)*
- [device_validation.md](device_validation.md)
- [pwa_decisions.md](pwa_decisions.md)

