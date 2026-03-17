# Roadmap & TODOs

> Ausgelagert aus der README.  Detailpläne siehe die jeweiligen Dateien in `docs/plans/` und `docs/ios/`.

## 🔴 High Priority

- **Phase 1: Offline-Download Feature (PWA)** — ✅ Implementiert (2026-03-17)
  - Siehe [offline_feature.md](offline_feature.md)
  - ✅ Service Worker, Download UI, IndexedDB, Offline-Playback, Quota-UI, Tests
  - 🚧 Manuelle Geräte-Verifikation auf iPhone/iPad — siehe [docs/ios/device_validation.md](../ios/device_validation.md)

- **Phase 2: PWA Shortcuts — Quick Win**
  - Siehe [pwa_shortcuts.md](pwa_shortcuts.md)
  - Einzelne Filme/Songs auf Home-Bildschirm speichern
  - Deep Linking + Quick Access

- **Phase 3: Native iOS Apps (Hybrid WebView Wrapper)**
  - Siehe [native_app_plan.md](native_app_plan.md)
  - Zwei separate Apps: HometoolsVideo + HometoolsAudio
  - WebView Wrapper, Native Features (Background Audio, Lock Screen)

## 🟡 Medium Priority

### Management & Sync
- Serverstatus-Seite mit Managementaufgaben
- Metadaten-Änderungen vom Handy: Review-Queue → erst bei "Akzeptieren" schreiben
- Dynamisches Synchronisieren: Änderungs-DB für zielgerichtetes Handy-Update
- Scheduler für planbare, zyklische Aufgaben
- Management-Server: Sync + Streaming steuern, NAS-Ordner automatisch scannen
- Fehler/Warnungen zusätzlich in offenes Aufgaben-File → Scheduler prüft → TODOs erzeugen

### Streaming UI
- "Recently Added"-Sektion
- Shuffle-Modus (Long Touch: gewichteter Shuffle nach Bewertung)
- Songwertung (1–5 Sterne) in UI anzeigen + ID3-POPM-Tags speichern
- "Ähnliche Titel" vorschlagen (Artist/Genre/Album bzw. TMDB-Genre/Regisseur)
- Wiedergabelisten erstellen und verwalten
- Tags bei Musik nutzen
- Filteroptionen für die Suche
- Songtexte anzeigen (aus ID3-Tags)
- Letzte Wiedergabe + Fortschritt speichern (geräteübergreifend)
- Swipe-Geste für mobile UI
- Offline-Downloads-Liste
- ✅ ~~Failure-Tracking für Thumbnails~~ → implementiert (thumbnail_failures.json)

### Video-spezifisch
- Ordnerstruktur-Interpretation für Video Server (Umbenennungen nur als Liste vorschlagen!)
- Englische Serien: Metadaten in englisch laden, englische Titel einfügen
- Sprach-Varianten verlinken ("Malcolm Mittendrin" ↔ "Malcolm in the Middle")
- Untertitelfiles + TMDB-Integration, Pfadanpassungen bei Umbenennung
- Sprache/Untertitel/Auflösung in UI taggen und auswählbar machen
- "Intro überspringen" (TMDB-Daten oder manuelle Markierung)
- Scan-Hinweise: Filesystem-Organisation ausreichend?

### Audio-spezifisch
- Crossfade für nahtlose Übergänge
- iPhone-Pitfall: Pause-Button ist noch ein Emoji
- Tools-Code restrukturieren + umfassende Tests (Edge Cases, LUTs, Dummy-Dateien)

### DJ-Extension
- Songs mixen, automatische Übergänge
- BPM/Tonart-Analyse, nahtloses Überblenden
- Stem-Separation (Gesang, Instrumental, Bass/Beat) im Schattenverzeichnis
- BPM-Anpassung (Geschwindigkeitsregler via Long Touch auf Pause)
- Übergangs-Analyse zwischen Songs
- "Keep something playing"-Option
- "Auto-DJ"-Modus mit thematischen Verläufen

### Experimentell / Langfristig
- "Fernsehsender" (automatische Wiedergabe nach Plan, mit "Werbung")
- "MTV"-Modus (Musikvideos + visuelle Begleitung zu Musik)
- "Sleep Mode" (nur Audio aus Serien, kein Bildschirm)
- Lennyface-Board
- Photo-Management Server
- Pro-Nutzer Ordnerstruktur-Anpassung (N8N-Integration?)
- HTTP-Obscurification (Port-Knock statt HTTPS)
- Optionales HTTPS

## ✅ Erledigt
- Thumbnail Failure-Tracking → `thumbnail_failures.json`, MTime-basierter Retry
- Phase 1 Offline-Download Feature (PWA)

