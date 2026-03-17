# iOS / PWA Device Validation — Phase 1 Abschluss

## Zweck

Diese Checkliste ist der **manuelle Abschluss für Phase 1** des Offline-PWA-Features.

Die Implementierung und automatisierten Tests sind bereits im Repo vorhanden. Hier wird nur noch auf **echten iPhone-/iPad-Geräten** überprüft, ob Safari/PWA unter realen Bedingungen genauso zuverlässig funktioniert.

> Diese Datei bitte aktualisieren, sobald echte Messwerte oder neue iOS-Sonderfälle bekannt sind.

---

## Testmatrix

| Kontext | Pflicht | Ziel |
|--------|--------|------|
| Safari-Tab | ✅ | Basisfunktion im normalen Browser |
| Home-Screen / PWA | ✅ | Verhalten als installierte Web-App |
| WLAN online | ✅ | Download + normaler Stream |
| Flugmodus / offline | ✅ | Offline-Playback |
| kleines File (<10 MB) | ✅ | Grundfunktion |
| größeres File (20–80 MB) | ✅ | Quota / Seek / Stabilität |
| Audio | ✅ | Offline-Musik |
| Video | ✅ | Offline-Video + Seek |

---

## Vorbedingungen

- Server läuft lokal im Heimnetz
- iPhone/iPad ist im selben Netz
- PWA/Seite ist erreichbar
- Mindestens:
  - 1 Audio-Datei mit funktionierendem Download
  - 1 Video-Datei mit funktionierendem Download
- Optional sinnvoll:
  - 1 größere Datei zum Quota-/Seek-Test

---

## Testprotokoll

Vor jedem Lauf kurz festhalten:

- Gerät:
- iOS-Version:
- Browser-Kontext: Safari-Tab / Home-Screen-App
- Server-URL:
- Getesteter Medientyp: Audio / Video
- Dateigröße ungefähr:
- Ergebnis: PASS / FAIL
- Auffälligkeiten:

---

## Checkliste A — Safari-Basis

### A1. Seite lädt
- [ ] Audio-Server in Safari öffnen
- [ ] Video-Server in Safari öffnen
- [ ] UI lädt vollständig
- [ ] Listenansicht / Navigation / Offline-Button sichtbar

### A2. Normaler Stream funktioniert
- [ ] Audio anklicken → Wiedergabe startet
- [ ] Video anklicken → Wiedergabe startet
- [ ] Seek funktioniert online
- [ ] Pause / Weiter / Nächstes / Vorheriges funktionieren

---

## Checkliste B — Offline-Download

### B1. Audio herunterladen
- [ ] Audio-Titel in Listenansicht herunterladen
- [ ] Download-Status wechselt von Pfeil zu Haken
- [ ] Eintrag erscheint in der Offline-Bibliothek
- [ ] Größe / Titel / Sortierung wirken plausibel

### B2. Video herunterladen
- [ ] Video herunterladen
- [ ] Download-Status wechselt korrekt
- [ ] Eintrag erscheint in der Offline-Bibliothek
- [ ] Thumbnail / Metadaten sehen plausibel aus

### B3. Entfernen testen
- [ ] Download in Listenansicht entfernen
- [ ] Download in Offline-Bibliothek entfernen
- [ ] Eintrag verschwindet in beiden Ansichten

---

## Checkliste C — Offline-Playback

### C1. Audio offline
- [ ] Audio herunterladen
- [ ] Server stoppen **oder** Gerät offline schalten
- [ ] Seite/App neu öffnen
- [ ] Gedownloadeten Audio-Titel starten
- [ ] Audio spielt wirklich ohne Server
- [ ] Seek innerhalb des Audios funktioniert

### C2. Video offline
- [ ] Video herunterladen
- [ ] Server stoppen **oder** Gerät offline schalten
- [ ] Seite/App neu öffnen
- [ ] Gedownloadetes Video starten
- [ ] Video spielt wirklich ohne Server
- [ ] Seek / Scrubbing funktioniert
- [ ] Mehrfaches Springen führt nicht zu Hängern

### C3. Stream-Fallback
- [ ] Falls Offline-Datei fehlschlägt: online erneut probieren
- [ ] Prüfen, ob der Fallback sauber zum Stream zurückkehrt

---

## Checkliste D — Home-Screen / PWA

### D1. Installation
- [ ] Seite zum Home-Bildschirm hinzufügen
- [ ] Home-Screen-App startet korrekt
- [ ] Offline-Bibliothek ist auch dort sichtbar

### D2. Download + Offline in installierter App
- [ ] Download innerhalb der Home-Screen-App starten
- [ ] App schließen
- [ ] Gerät offline schalten
- [ ] Home-Screen-App erneut öffnen
- [ ] Download startet weiterhin offline

### D3. Navigation / Re-Open
- [ ] App mehrfach schließen / wieder öffnen
- [ ] Offline-Einträge bleiben sichtbar
- [ ] Keine kaputten Blob-/Playback-Zustände nach Wiederöffnung

---

## Checkliste E — Speicher / Quota

### E1. Storage-Anzeige
- [ ] Offline-Bibliothek zeigt Speicher-Infos an
- [ ] Browser-/App-Budget wird plausibel angezeigt
- [ ] Warnzustand bei hoher Auslastung ist sichtbar (falls erreichbar)

### E2. Persistent Storage
- [ ] Button für persistenten Speicher erscheint (wenn vom Gerät unterstützt)
- [ ] Klick liefert nachvollziehbaren Status

### E3. Pruning
- [ ] Mehrere größere Dateien laden
- [ ] Prüfen, ob alte Downloads bei Bedarf aufgeräumt werden
- [ ] Keine aktuell genutzte Datei wird unerwartet gelöscht

---

## Checkliste F — Touch / UX

### F1. Listenbedienung
- [ ] Download-Button bleibt gut tappbar
- [ ] Wiedergabe startet weiterhin bei Klick auf Listeneintrag
- [ ] Offline-Bibliothek verdeckt nichts Wichtiges

### F2. Seek / Scroll
- [ ] Audio-Seek ist per Touch präzise genug
- [ ] Video-Seek reagiert stabil
- [ ] Keine offensichtlichen Layout-Sprünge beim Öffnen/Schließen des Offline-Modals

---

## Abnahmekriterien für Phase 1

Phase 1 kann praktisch als abgeschlossen markiert werden, wenn folgende Punkte erfüllt sind:

- [ ] Audio-Download funktioniert auf echtem iPhone/iPad
- [ ] Video-Download funktioniert auf echtem iPhone/iPad
- [ ] Audio-Offline-Playback funktioniert real
- [ ] Video-Offline-Playback funktioniert real
- [ ] Seek funktioniert offline mindestens für einen Audio- und einen Video-Testfall
- [ ] Offline-Bibliothek zeigt Einträge korrekt an
- [ ] Entfernen von Downloads funktioniert stabil
- [ ] Keine blockerhaften Safari-/PWA-Sonderfehler mehr offen

---

## Bekannte Beobachtungspunkte

Besonders auf iOS bitte explizit notieren, falls eines davon auftritt:

- Download verschwindet nach App-Neustart
- Blob/Media startet erst beim zweiten Klick
- Seek funktioniert online, aber nicht offline
- Home-Screen-App verhält sich anders als Safari-Tab
- Speicher-Anzeige ist offensichtlich unplausibel
- Große Videos werden stillschweigend verworfen
- PWA wird durch iOS aggressiv neu geladen

---

## Ergebnis-Log

### Lauf 1
- Datum:
- Gerät / iOS:
- Kontext:
- Ergebnis:
- Notizen:

### Lauf 2
- Datum:
- Gerät / iOS:
- Kontext:
- Ergebnis:
- Notizen:

