# Background Video Playback — Analyse & Plan

> **Siehe auch:** [`.iOS_PWA_DECISIONS.md`](.iOS_PWA_DECISIONS.md) für iOS-spezifische Limitations und wann eine Native App nötig wird.

## Problem

Wenn der Benutzer die Video-App minimiert (Tab wechseln, App-Switcher, Home-Taste),
passiert Folgendes:

1. Das Video **pausiert sofort** (kein Ton, kein Bild)
2. Der **Miniplayer (PiP) erscheint nicht**
3. Über die Lockscreen-/Notification-Controls kann man den Sound manuell
   wieder starten, aber das Video bleibt unsichtbar

Das Ergebnis: Hintergrund-Playback ist praktisch kaputt.

---

## Root-Cause-Analyse

### Bug 1: Race Condition bei `visibilitychange`

```
User wechselt App →
  Browser pausiert <video> automatisch →          ← passiert ZUERST
    "pause" Event feuert →
      Button wechselt zu ▶ →
        visibilitychange feuert (document.hidden=true) →
          Handler prüft: !player.paused → FALSE →  ← hier ist das Problem
            NICHTS PASSIERT (weder PiP noch bgAudio)
```

**Der alte Code:**
```javascript
if (document.hidden && !player.paused) {  // ← player IST schon paused!
    requestPiP();
    bgAudio.muted = false;
}
```

**Fix:** Einen `wasPlaying`-Flag verwenden, der auf dem `playing`-Event gesetzt
und nur bei **bewusstem User-Pause** (Button-Klick) zurückgesetzt wird.
Die Browser-Auto-Pause ändert den Flag nicht.

### Bug 2: PiP braucht User-Gesture

`requestPictureInPicture()` wird von den meisten Browsern **nur** aus einem
User-Gesture-Event heraus erlaubt (click, touchend, keydown etc.).
`visibilitychange` ist **kein** User-Gesture → der Aufruf wird abgelehnt.

**Fix:**
- **Safari:** `autopictureinpicture`-Attribut auf dem `<video>` → Safari
  aktiviert PiP automatisch beim App-Wechsel (kein JS-Aufruf nötig)
- **Chrome/Desktop:** PiP muss über den manuellen Button ausgelöst werden,
  ODER Chrome's `documentPictureInPicture` API verwenden (erfordert Feature-Flag)
- Als Fallback: bgAudio-Mechanismus

### Bug 3: `muted=true` vs. `volume=0` auf iOS

~~iOS Safari behandelt `muted=true` auf einem `<audio>` Element so, dass die
**gesamte Audio-Pipeline deaktiviert** wird.~~

**KORREKTUR:** Auf iOS ist die `volume`-Property **READ-ONLY** und gibt immer 1
zurück.  `element.volume = 0` hat **keine Wirkung**.  Das bedeutet:
- `bgAudio.volume = 0` → bgAudio spielt bei voller Lautstärke → **Doppel-Audio!**
- `bgAudio.muted = true` → bgAudio ist korrekt stumm ✓

**Fazit:** `muted` ist der **einzig richtige** Weg, um bgAudio auf iOS stumm zu
halten.  Die Audio-Pipeline bleibt trotz `muted=true` aktiv, solange das Element
bereits aus einem User-Gesture heraus gestartet wurde (was bei uns der Fall ist,
da `startBgMirror()` im `.then()` von `player.play()` aufgerufen wird).

### Bug 4: `pause`-Event unterscheidet nicht User vs. Browser

```javascript
player.addEventListener('pause', function() {
    btnPlay.textContent = '▶';  // ← auch bei Browser-Auto-Pause!
});
```

Wenn der Browser das Video automatisch pausiert, zeigt die UI fälschlich
den Play-Button, obwohl der bgAudio gerade übernimmt.

**Fix:** Im `pause`-Handler prüfen, ob `document.hidden` ist (= Browser-Pause)
und den Button-Status nur bei Vordergrund-Pause ändern.

---

## Lösungs-Plan

### Schritt 1: `wasPlaying`-Flag einführen

```javascript
var wasPlaying = false;

player.addEventListener('playing', function() { wasPlaying = true; });
// NUR bei bewusstem User-Pause zurücksetzen (togglePlay, nicht im
// generischen pause-handler)
```

### Schritt 2: bgAudio bleibt bei `muted` (NICHT `volume`)

iOS ignoriert `volume`-Änderungen (Property ist read-only, gibt immer 1
zurück).  `bgAudio.muted = true/false` ist der korrekte Weg.
Das bgAudio wird aus einem User-Gesture-Kontext (`play().then(...)`) gestartet,
dadurch bleibt die Audio-Pipeline auch mit `muted=true` aktiv.

### Schritt 3: `visibilitychange`-Handler fixen

```javascript
document.addEventListener('visibilitychange', function() {
    if (!isVideoPlayer) return;
    if (document.hidden && wasPlaying) {
        // bgAudio übernimmt
        bgAudio.currentTime = player.currentTime;
        bgAudio.muted = false;
        // Video nicht explizit pausieren — Browser macht das selbst
    } else if (!document.hidden && wasPlaying) {
        // Zurück im Vordergrund
        if (pipActive) exitPiP();
        if (bgAudio && !bgAudio.muted) {
            player.currentTime = bgAudio.currentTime;
            player.play().catch(function() {});
            bgAudio.muted = true;
        }
    }
});
```

### Schritt 4: `autopictureinpicture` Attribut

Auf dem `<video>` Element das Safari-spezifische Attribut setzen:
```html
<video id="player" preload="auto" playsinline autopictureinpicture></video>
```

Zusätzlich per JS für Webkit:
```javascript
if (player.webkitSetPresentationMode) {
    player.setAttribute('autopictureinpicture', '');
}
```

### Schritt 5: `pause`-Event Handler fixen

```javascript
player.addEventListener('pause', function() {
    // Nicht reagieren wenn der Browser auto-pausiert hat (Hintergrund)
    if (document.hidden) return;
    if (!player.ended && !(bgAudio && !bgAudio.muted)) {
        btnPlay.textContent = '▶';
    }
});
```

### Schritt 6: MediaSession korrekt setzen

```javascript
// Beim Hintergrund-Wechsel den playbackState explizit setzen
navigator.mediaSession.playbackState = 'playing';
```

Das signalisiert dem OS, dass Playback läuft und die Lockscreen-Controls
angezeigt werden sollen.

---

## Test-Szenarien

1. **iOS Safari (Tab):** Video starten → Tab wechseln → Audio muss weiterlaufen
2. **iOS Safari (Home-Screen-App, minimal-ui):** Video starten → Home-Taste →
   Audio muss weiterlaufen → App öffnen → Video sync'd zum Audio zurück
3. **Safari macOS:** Video starten → Tab wechseln → PiP sollte erscheinen
   (autopictureinpicture)
4. **Chrome Android:** Video starten → Home-Taste → PiP oder Audio-Fallback
5. **Chrome Desktop:** Video starten → Tab wechseln → Video spielt weiter
   (Chrome pausiert Videos in Tabs normalerweise nicht)
6. **Lockscreen-Controls:** Play/Pause/Skip müssen auf allen Plattformen
   funktionieren
7. **Fullscreen-Button:** Nativer Fullscreen-Button muss im Video-Player
   sichtbar sein + custom Fullscreen-Button in der Player-Bar

---

## Architektur: Zwei-Server-Ansatz (To-Do)

**Erkenntnis (2026-03-16):** Es gibt einen nicht auflösbaren Trade-off auf iOS:

| PWA-Mode | Fullscreen | PiP | Background Audio | Installierbar |
|---|---|---|---|---|
| `standalone` | ❌ blockiert | ❌ blockiert | ❌ wird suspendiert | ✅ echte PWA |
| `minimal-ui` | ✅ funktioniert | ✅ funktioniert | ⚠️ teilweise | ⚠️ nur Web-Link |

**Aktuelle Lösung:** `minimal-ui` wählen → Background-Audio + PiP/Fullscreen funktionieren,
aber **keine echte Home-Screen-App mehr** (nur Browser-Link).

**To-Do: Zwei-Server-Architektur**

Perspektive: zwei Instanzen der Video-App starten:
1. **Port 8001 — `display: standalone`** (schöne App, Fullscreen, aber kein Background)
2. **Port 8002 — `display: minimal-ui`** (Web-Link, aber Background + PiP)

Benutzer kann dann wählen, welche Variante ihnen besser gefällt, oder beide nutzen.
Implementierung erfordert: Umgebungsvariable `VIDEO_PWA_DISPLAY_MODE` in `render_video_index_html()`.

Betroffene Dateien:
- `src/hometools/streaming/video/server.py` — manifest() Endpoint
- `src/hometools/config.py` — neue Konfiguration `VIDEO_PWA_DISPLAY_MODE`
- `.env.example` — Dokumentation

### Warum nicht einfach `display: browser`?

`display: browser` = vollständige Browser-Chrome + alle APIs verfügbar.
Problem: Sieht nicht wie App aus (URL-Bar, Tabs sichtbar) → schlechte UX.

## Betroffene Dateien

- `src/hometools/streaming/core/server_utils.py` — JS-Logik + HTML-Template + PWA
- `src/hometools/streaming/video/server.py` — Video-Server (PWA manifest)
- `tests/test_streaming_player_ui.py` — Unit-Tests für die neuen Features

---

## Pitfalls & Erkenntnisse (IMMER HIER DOKUMENTIEREN)

> **REGEL:** Wenn ein iOS/Safari/Browser-Pitfall entdeckt wird, MUSS er hier
> mit Datum, Symptom und Erklärung dokumentiert werden, auch wenn das Problem
> nicht sofort gelöst werden kann. Wissen darf nicht verloren gehen.

### Pitfall 1: iOS `volume`-Property ist READ-ONLY (2026-03-16)

**Symptom:** Doppel-Audio — zwei Tonspuren gleichzeitig, leicht versetzt.
**Ursache:** `HTMLMediaElement.volume` ist auf iOS Safari **read-only** und
gibt immer `1` zurück. `element.volume = 0` hat **keine Wirkung**.
**Lösung:** `element.muted = true/false` verwenden. Das ist der einzige Weg,
ein Element auf iOS stumm zu schalten.

### Pitfall 2: `display: standalone` deaktiviert PiP + Fullscreen auf iOS (2026-03-16)

**Symptom:** Kein PiP-Miniplayer, kein Fullscreen-Button, aggressives
Media-Suspending beim App-Wechsel.
**Ursache:** `"display": "standalone"` im PWA-Manifest + `apple-mobile-web-app-capable`
Meta-Tag isoliert die App vollständig vom Safari-Browser. In diesem Modus:
- `requestPictureInPicture()` wird abgelehnt / ist nicht verfügbar
- `autopictureinpicture` funktioniert nicht
- `requestFullscreen()` ist nicht verfügbar (App ist „bereits fullscreen")
- Die WebView suspendiert Media **aggressiver** als normale Safari-Tabs
- Auch `bgAudio`-Elemente werden mit-suspendiert
**Lösung:** `display: "minimal-ui"` verwenden und `apple-mobile-web-app-capable` weglassen.
Damit funktionieren alle APIs → **Das war der Schlüssel für PiP!**
**Trade-off:** "Add to Home Screen" erstellt nur einen Web-Link, keine echte PWA.
Für Audio bleibt `standalone` weiterhin sinnvoll.

### Pitfall 3: `visibilitychange` feuert NACH Browser-Auto-Pause (2026-03-16)

**Symptom:** `visibilitychange`-Handler hat keine Wirkung beim Minimieren.
**Ursache:** Mobile Browser pausieren `<video>` **bevor** `visibilitychange`
feuert. `!player.paused` ist bereits `false` → Handler-Bedingung wird nie wahr.
**Lösung:** `wasPlaying`-Flag verwenden, das nur bei bewusstem User-Pause
zurückgesetzt wird (nicht bei Browser-Auto-Pause).

### Pitfall 4: `requestPictureInPicture()` braucht User-Gesture (2026-03-16)

**Symptom:** PiP-Anforderung im `visibilitychange`-Handler wird abgelehnt.
**Ursache:** Die PiP-API erfordert einen User-Gesture (click/tap/keydown).
`visibilitychange` ist kein User-Gesture.
**Lösung:** `autopictureinpicture`-Attribut auf dem `<video>`-Element setzen
(Safari macht PiP dann automatisch). Für manuelles PiP: Button bereitstellen.

### Pitfall 5: `<video>` ohne `controls`-Attribut = kein nativer Fullscreen (2026-03-16)

**Symptom:** Kein Fullscreen-Button im Video-Player.
**Ursache:** Das `<video>`-Element hatte kein `controls`-Attribut. Alle Controls
waren custom (JS-Buttons). Aber die custom Player-Bar hatte keinen
Fullscreen-Button, und ohne `controls` zeigt der Browser keine nativen Controls.
**Lösung:** `controls`-Attribut zum `<video>`-Element hinzufügen UND einen
custom Fullscreen-Button in der Player-Bar (`webkitEnterFullscreen` für iOS).

### Pitfall 6: `display: minimal-ui` = PiP/Fullscreen funktionieren, aber (noch) keine PWA (2026-03-16)

**Symptom:** "Add to Home Screen" erstellt nur einen Browser-Link, keine echte App.
**Ursache:** `display: minimal-ui` wird von iOS Safari nicht als PWA erkannt.
**Situation:** Aktuell müssen Benutzer zwischen zwei Varianten wählen:
- `display: standalone` = echte PWA, aber alle APIs blockiert
- `display: minimal-ui` = alle APIs funktionieren, aber nur Web-Link

**Wichtig:** Das ist nicht unsolvbar — wir haben die Lösung nur noch nicht gefunden.
Es gibt wahrscheinlich eine Kombination aus Meta-Tags / iOS-spezifischen Hints,
die beides gleichzeitig ermöglicht. Zu-Do für Zukunft.

### Success Stories (2026-03-16)

✅ **Fullscreen funktioniert** — Nativer Fullscreen-Button + custom Button in Player-Bar
✅ **Miniplayer (PiP) funktioniert** — **Kritische Eigenschaft:** `display: "minimal-ui"` im PWA-Manifest
❌ **Beides zusammen mit installierter PWA** — Wir haben es noch nicht geschafft, aber es ist wahrscheinlich möglich

### Status (2026-03-16)

**Aktueller Stand:**
- `display: minimal-ui` brachte PiP zum Funktionieren
- Das Trade-off ist: echte PWA-Installation (Home-Screen) ODER volle Funktionalität
- Benutzer müssen aktuell wählen (oder zwei Server parallel laufen lassen)

**To-Do (Zukunft):**
- Untersuchen, ob `display: "standalone"` + zusätzliche Meta-Tags / iOS-spezifische Hacks 
  beides gleichzeitig ermöglichen
- Perspektive: Zwei-Server-Ansatz ist ein gutes Interim-Design











