# hometools TV (Android TV)

Native Android TV app — ein schlanker, D-Pad-getriebener Netflix/Jellyfin-Stil-Client für
das hometools **Video**-Backend. Kein WebView-Wrapper: ein 10-Fuß-UI braucht natives Focus-Handling
und einen nativen Player.

## Warum nativ (statt Website)

- **D-Pad / 10-Fuß-UI** via Jetpack **Compose for TV** (`androidx.tv.material3`).
- **Media3 / ExoPlayer** spielt MP4 **und MKV/AVI** mit HTTP Range direkt von
  `/video/stream` — Formate, die der TV-Browser ablehnt.
- Erscheint im Android TV Home-Screen (LEANBACK_LAUNCHER + Banner).

## Umfang (nur Lesen/Playback)

Ruft nur den Playback-Teil der API auf: `items`, `continue`, `metadata`, `progress`, `intro`,
plus `/video/stream` und `/thumb`. **Keine Admin-Tools** (rating/tag/move/delete/playlists) —
die bleiben im Web-UI. Siehe [`../README.md`](../README.md).

## Projektstruktur

```
androidtv/
├── scripts/
│   └── build.ps1              ← Setup/Build/Test/Deploy-Script (PowerShell)
├── settings.gradle.kts
├── build.gradle.kts
├── gradle/libs.versions.toml  ← Version-Katalog (AGP, Kotlin, TV, Media3 …)
└── app/
    ├── build.gradle.kts
    └── src/
        ├── main/
        │   ├── AndroidManifest.xml   ← LEANBACK_LAUNCHER, INTERNET, cleartext (LAN HTTP)
        │   └── java/com/hometools/tv/
        │       ├── MainActivity.kt   ← setup → browse → player Navigation
        │       ├── data/             ← Models, VideoApi (Retrofit), ApiClient, ServerConfig
        │       └── ui/               ← BrowseScreen, PlayerScreen, ServerSetupScreen, theme
        └── test/
            └── java/com/hometools/tv/data/
                ├── ApiClientTest.kt  ← URL-Joining, baseUrl-Normalisierung
                └── ModelsTest.kt     ← JSON-Parsing, unbekannte Felder, Defaults
```

---

## Schritt 1 — Voraussetzungen installieren

### JDK 17

```powershell
winget install Microsoft.OpenJDK.17
```

Oder manuell: https://adoptium.net/de/temurin/releases/?version=17

Nach der Installation PowerShell neu starten und prüfen:

```powershell
java -version   # muss "17" zeigen
```

### Android SDK

**Option A — Android Studio (empfohlen):**
https://developer.android.com/studio
Das SDK wird automatisch unter `C:\Users\<User>\AppData\Local\Android\Sdk` installiert.

**Option B — Nur Kommandozeilen-Tools:**
https://developer.android.com/studio#command-line-tools-only

```powershell
sdkmanager "platforms;android-34" "build-tools;34.0.0" "platform-tools"
```

### Gradle Wrapper JAR

Das JAR ist git-ignoriert und muss einmalig lokal generiert werden.
`gradle` muss im PATH sein:

```powershell
winget install Gradle.Gradle
# Dann:
cd clients/androidtv
gradle wrapper --gradle-version 8.9
```

---

## Schritt 2 — Voraussetzungen prüfen (automatisch)

```powershell
cd clients/androidtv
powershell -ExecutionPolicy Bypass -File scripts/build.ps1 -Action check
# Oder aus dem Repo-Root:
make android-check
```

Das Script prüft JDK, SDK und Wrapper JAR und erstellt `local.properties` automatisch.

---

## Schritt 3 — Bauen

```powershell
# Über das Script:
powershell -ExecutionPolicy Bypass -File scripts/build.ps1 -Action build
# Oder make:
make android-build
# Oder Gradle direkt:
cd clients/androidtv && .\gradlew.bat assembleDebug
```

APK: `clients/androidtv/app/build/outputs/apk/debug/app-debug.apk`

---

## Schritt 4 — Unit-Tests (kein Emulator nötig)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build.ps1 -Action test
# Oder:
make android-test
# Oder:
cd clients/androidtv && .\gradlew.bat test
```

Report: `app/build/reports/tests/testDebugUnitTest/index.html`

---

## Schritt 5 — Auf dem Fernseher deployen

### ADB Debugging am TV aktivieren

1. **Einstellungen → Gerät → Info** → 7× auf „Build" klicken → Entwickleroptionen
2. **Einstellungen → Gerät → Entwickleroptionen → Netzwerk-Debugging** aktivieren
3. TV-IP notieren: **Einstellungen → Netzwerk → Status**

### Deployen

```powershell
# Alles in einem Schritt (prüfen + bauen + installieren):
powershell -ExecutionPolicy Bypass -File scripts/build.ps1 -Action deploy -TvIp 192.168.178.100
# Oder make:
make android-deploy TV_IP=192.168.178.100
```

> **Backend muss erreichbar sein** vom TV (gleiches WLAN). Beim ersten Start
> Server-URL eingeben (Standard: `http://192.168.178.87:8011`).

---

## Contract / Code-Generierung

Das Data-Layer spiegelt [`../shared/openapi/video-openapi.json`](../shared/openapi).
Nach Backend-API-Änderungen:

```bash
hometools export-openapi --server video
```

---

## Bekannte Lücken (in docs/IMPLEMENTATION_PLAN.md verfolgt)

- Wrapper-JAR lokal generieren (`gradle wrapper`) — nicht committed.
- Platzhalter-Icon/Banner — durch Branding ersetzen.
- Server-URL-Eingabe ist Stub — IP-Stepper / QR-Pairing geplant.
- Größere Poster-Art: Backend-Thumbs 120 px / 480 px; echte Poster TBD.
- Keine Auth (nur LAN) — Device-Token/Discovery als Folge-Task.
- Keine Instrumented Tests (Compose-UI-Tests brauchen Emulator/Gerät).
