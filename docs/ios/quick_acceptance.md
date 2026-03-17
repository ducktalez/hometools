# iPhone PWA Quick Acceptance — 5 Minuten

## Zweck

Diese Kurzfassung ist die **schnellste praktische Abnahme für Phase 1**.

Wenn du nur kurz prüfen willst, ob das Offline-PWA-Feature auf dem iPhone im Alltag grundsätzlich funktioniert, reicht diese Checkliste.

Für die vollständige Abnahme siehe [device_validation.md](device_validation.md).

Für den konkreten Ablauf mit den aktuellen Server-URLs siehe [test_runbook.md](test_runbook.md).

---

## Vorbereitung

- Server läuft im Heimnetz
- iPhone ist im selben WLAN
- mindestens 1 Audio-Datei und 1 Video-Datei sind in der UI sichtbar

---

## 5-Minuten-Check

### 1. Seite öffnen
- [ ] Audio- oder Video-Server in Safari öffnen
- [ ] UI lädt vollständig
- [ ] `Offline`-Button ist sichtbar

### 2. Einen Download auslösen
- [ ] Einen Song **oder** ein Video herunterladen
- [ ] Download-Button wechselt am Ende auf Haken
- [ ] Eintrag erscheint in der Offline-Bibliothek

### 3. Offline testen
- [ ] Flugmodus aktivieren **oder** Server stoppen
- [ ] Seite erneut öffnen
- [ ] Genau den eben heruntergeladenen Eintrag starten
- [ ] Medium spielt trotzdem ab

### 4. Seek testen
- [ ] Innerhalb des offline abgespielten Mediums vorspulen / springen
- [ ] Wiedergabe läuft danach weiter

### 5. Löschen testen
- [ ] Download wieder entfernen
- [ ] Eintrag verschwindet aus Offline-Bibliothek und Listenstatus

---

## Ergebnis

### ✅ PASS
Alles oben funktioniert ohne auffällige Hänger.

### ⚠️ PASS mit Einschränkung
Grundsätzlich funktioniert es, aber z. B.:
- Seek ist hakelig
- Home-Screen-App verhält sich anders als Safari
- größere Dateien verhalten sich komisch

Dann bitte Details in [device_validation.md](device_validation.md) ergänzen.

### ❌ FAIL
Wenn einer dieser Punkte fehlschlägt, ist Phase 1 noch nicht praktisch abgeschlossen:
- Download wird nicht gespeichert
- Offline-Playback startet nicht
- Seek bricht offline ab
- Download lässt sich nicht wieder entfernen

---

## Ergebnis-Notiz

- Datum:
- Gerät / iOS:
- Kontext: Safari / Home-Screen
- Medium: Audio / Video
- Ergebnis: PASS / PASS mit Einschränkung / FAIL
- Notizen:


