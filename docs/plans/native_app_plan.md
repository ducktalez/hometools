# Native iOS App — Implementierungsplan mit Code-Reuse

## 🎯 Ziel

Zwei native iOS Apps (Video & Audio) mit **minimalem Overhead** — maximale Wiederverwendung des bestehenden Backend + Web-UI.

**Strategie:** WebView Wrapper + Native Controls (nicht pure Swift)

---

## Architektur: Das große Bild

```
hometools Repository
├── src/hometools/          ← Backend bleibt UNVERÄNDERT
│   ├── streaming/
│   ├── video/
│   └── audio/
│
├── ios/                     ← NEUE Ordner für Native Apps
│   ├── HometoolsVideo/     ← Xcode Project (Swift)
│   │   ├── App.swift
│   │   ├── WebViewContainer.swift
│   │   └── NativeControls.swift
│   │
│   └── HometoolsAudio/     ← Xcode Project (Swift)
│       ├── App.swift
│       ├── WebViewContainer.swift
│       └── NativeControls.swift
│
└── web/                     ← PWA Komponenten (unverändert)
    └── streaming UI (React/HTML/CSS/JS)
```

**Wichtig:** Der Python-Backend bleibt **100% unverändert**. Die Native App ist nur ein Wrapper.

---

## Phase 1: PWA-Version fertigstellen (bevor Native)

### Schritt 1.1: Offline-Feature implementieren
- Service Worker erweitern (Cache API)
- IndexedDB für Downloads
- Download-Manager UI
- ~10-12 Stunden (siehe `offline_feature.md`)

**Output:** Funktionierende PWA mit Offline-Support

### Schritt 1.2: PWA-Tests auf iPhone
- Safari + Home-Screen-App testen
- Speicher-Limits prüfen
- Background-Playback verifizieren

**Output:** Knowhow, was PWA kann/nicht kann

---

## Phase 2: Native App — Strategie

### Ansatz: WebView Wrapper + Hybrid

```
┌─────────────────────────────────────┐
│  iOS Native App (Swift)             │
├─────────────────────────────────────┤
│  ┌─────────────────────────────────┐│
│  │  WKWebView (Browser-Engine)     ││
│  │  ┌─────────────────────────────┐││
│  │  │  PWA (HTML/CSS/JS)          │││
│  │  │  (exakt gleicher Code)      │││
│  │  └─────────────────────────────┘││
│  └─────────────────────────────────┘│
├─────────────────────────────────────┤
│  Native Bridge (Swift ↔ JS)         │
│  • AVAudioSession (Hintergrund)     │
│  • MediaPlayer (Lock Screen)        │
│  • FileManager (Persistent Storage) │
└─────────────────────────────────────┘
```

**Vorteile:**
- ✅ PWA-Code bleibt identisch
- ✅ Updates: nur Backend updaten (beide Versionen automatisch)
- ✅ Minimale Swift-Codezeilen (~500-800 LOC pro App)
- ✅ Full iOS Integration (Lock Screen, Background Audio, etc.)

**Nachteile:**
- Abhängig von WebView-Rendering (aber Safari WebKit ist sehr gut)
- Kleine App-Size (~5-10 MB)

---

## Phase 3: Native App Struktur

### 3.1 Projekt-Layout

```
ios/
├── HometoolsVideo/
│   ├── HometoolsVideo.xcodeproj
│   ├── HometoolsVideo/
│   │   ├── App.swift                 ← Main App
│   │   ├── WebViewController.swift    ← WKWebView Wrapper
│   │   ├── NativeBridge.swift        ← JS ↔ Swift Bridge
│   │   ├── AudioSession.swift        ← Background Audio
│   │   ├── LockScreen.swift          ← MediaPlayer + Lock Screen
│   │   ├── Storage.swift             ← FileManager + Documents/
│   │   └── Assets.xcassets
│   └── HometoolsVideo.xcconfig
│
├── HometoolsAudio/
│   ├── HometoolsAudio.xcodeproj
│   └── (gleiche Struktur)
│
└── Shared/
    ├── NativeBridgeProtocol.swift    ← Code beide Apps verwenden
    ├── AudioSessionManager.swift
    └── LockScreenManager.swift
```

### 3.2 Code-Größe Schätzung

| Datei | Zeilen | Zweck |
|-------|--------|-------|
| App.swift | 50 | SwiftUI Einstieg |
| WebViewController.swift | 150 | WKWebView + Config |
| NativeBridge.swift | 200 | JS-Bridge (Storage, Audio-Session) |
| AudioSession.swift | 150 | Background Audio + Interruption |
| LockScreen.swift | 150 | MediaPlayer Commands |
| Storage.swift | 100 | FileManager + Caching |
| **Pro App Gesamt** | **~800** | |
| **Beide Apps** | **~1600** | + Shared Code |

**Vergleich:**
- Native Swift App (pure): 15,000+ LOC
- Diese Hybrid-Lösung: ~2000 LOC (87% kleiner!)

---

## Phase 4: Implementierungs-Details

### 4.1 WebView Setup (Swift)

```swift
// WebViewController.swift
import WebKit

class WebViewController: UIViewController, WKNavigationDelegate {
    var webView: WKWebView!
    let serverURL: URL
    
    init(serverURL: URL) {
        self.serverURL = serverURL
        super.init(nibName: nil, bundle: nil)
    }
    
    required init?(coder: NSCoder) { fatalError() }
    
    override func viewDidLoad() {
        super.viewDidLoad()
        setupWebView()
        setupNativeBridge()
        loadServer()
    }
    
    func setupWebView() {
        let config = WKWebViewConfiguration()
        config.mediaTypesRequiringUserActionForPlayback = []  // ← Autoplay erlauben
        config.allowsInlineMediaPlayback = true
        config.ignoresViewportScaleLimits = true
        
        webView = WKWebView(frame: view.bounds, configuration: config)
        webView.navigationDelegate = self
        view.addSubview(webView)
    }
    
    func setupNativeBridge() {
        // Swift ↔ JavaScript Communication
        // Siehe: NativeBridge.swift
    }
    
    func loadServer() {
        let request = URLRequest(url: serverURL)
        webView.load(request)
    }
}
```

### 4.2 Native Bridge (Swift ↔ JavaScript)

```swift
// NativeBridge.swift
class NativeBridge: NSObject, WKScriptMessageHandler {
    let audioSessionManager: AudioSessionManager
    let storageManager: StorageManager
    
    func userContentController(
        _ userContentController: WKUserContentController,
        didReceive message: WKScriptMessage
    ) {
        guard let command = message.body as? [String: Any],
              let action = command["action"] as? String else { return }
        
        switch action {
        case "requestPersistentStorage":
            // iOS: Speicher-Limit anfordern
            audioSessionManager.requestPersistentStorage()
            
        case "getStorageQuota":
            // IndexedDB-Größe abfragen
            let quota = storageManager.getQuota()
            evaluateJS("window.onStorageQuota(\(quota))")
            
        case "enableBackgroundAudio":
            // Background-Audio-Session starten
            audioSessionManager.setupForBackgroundPlayback()
            
        case "updateLockScreen":
            // Lock Screen mit Track-Info updaten
            if let metadata = command["metadata"] as? [String: String] {
                mediaPlayerManager.updateLockScreen(title: metadata["title"])
            }
        }
    }
}
```

### 4.3 Background Audio (Swift)

```swift
// AudioSession.swift
import AVFoundation
import MediaPlayer

class AudioSessionManager {
    func setupForBackgroundPlayback() {
        let audioSession = AVAudioSession.sharedInstance()
        try? audioSession.setCategory(.playback, options: [.duckOthers])
        try? audioSession.setActive(true)
        
        // Lock Screen Commands
        let commandCenter = MPRemoteCommandCenter.shared()
        commandCenter.playCommand.isEnabled = true
        commandCenter.pauseCommand.isEnabled = true
        
        commandCenter.playCommand.addTarget { _ in
            self.evaluateJS("window.player.play()")
            return .success
        }
        commandCenter.pauseCommand.addTarget { _ in
            self.evaluateJS("window.player.pause()")
            return .success
        }
    }
}
```

### 4.4 Persistent Storage (Swift)

```swift
// Storage.swift
import Foundation

class StorageManager {
    let documentsPath = FileManager.default.urls(
        for: .documentDirectory,
        in: .userDomainMask
    )[0]
    
    func saveDownload(filename: String, data: Data) {
        let fileURL = documentsPath.appendingPathComponent(filename)
        try? data.write(to: fileURL)
    }
    
    func getQuota() -> [String: Int] {
        let attrs = try? FileManager.default.attributesOfFileSystem(
            forPath: documentsPath.path
        )
        return [
            "available": attrs?[.systemFreeSize] as? Int ?? 0,
            "total": attrs?[.systemSize] as? Int ?? 0
        ]
    }
}
```

---

## Phase 5: JS-Bridge für PWA (HTML/CSS/JS)

Die PWA-UI bleibt **100% identisch**. Nur die JS-Bridge wird erweitert:

```javascript
// In der PWA: Prüfe ob Native App oder Browser
const isNativeApp = window.webkit !== undefined;

// Native App: Speicher über Swift
if (isNativeApp) {
  window.webkit.messageHandlers.nativeBridge.postMessage({
    action: 'enableBackgroundAudio'
  });
}

// Browser: Wie bisher (IndexedDB)
else {
  navigator.storage.persist().then(...);
}
```

---

## Phase 6: Build & Deployment

### Struktur für Entwicklung

```bash
# Terminal 1: Backend
cd hometools
python -m venv .venv
.venv\Scripts\activate
hometools serve-video --port 8011

# Terminal 2: Xcode (iOS Simulator)
cd ios/HometoolsVideo
open HometoolsVideo.xcodeproj
# Build + Run in Simulator
# WKWebView lädt: http://localhost:8011
```

### App Store Release

```bash
# 1. Versionsnummern synchronisieren
# 2. SwiftUI UI polieren
# 3. Screenshots für App Store
# 4. Submit zu Apple

# 🔄 Updates: Nur Backend ändern, Native App bleibt gleich
```

---

## Roadmap: PWA → Native

### Phase 1 (Woche 1-2): PWA Offline-Feature ✓
- [ ] Service Worker erweitern
- [ ] IndexedDB Setup
- [ ] Download-Manager UI
- [ ] Tests auf iPhone
- **Output:** Funktionierende PWA mit ~50 MB Offline-Storage

### Phase 2 (Woche 3): Native App Foundation
- [ ] Xcode Projekte erstellen (Video + Audio)
- [ ] WKWebView Wrapper
- [ ] Server-Connection testen
- **Output:** Native App lädt PWA

### Phase 3 (Woche 4): Native Features
- [ ] AudioSession (Background + Lock Screen)
- [ ] Persistent Storage Integration
- [ ] Storage Quota UI
- **Output:** Vollständige Native App mit iOS-Features

### Phase 4 (Woche 5): Polish + Testing
- [ ] UI-Polish
- [ ] Speicher-Management
- [ ] iPhone + iPad testen
- [ ] App Store Preparation
- **Output:** Ready for App Store

**Gesamt-Aufwand:** ~3-4 Wochen (basierend auf ~2000 LOC Swift)

---

## Code-Sharing: Was geht, was nicht

### ✅ Teilt sich zwischen PWA + Native:
- **Backend** (Python) — 100% identisch
- **Streaming UI** (HTML/CSS/JS) — 100% identisch
- **IndexedDB** — PWA + Native (beide über WKWebView)
- **Service Worker** — PWA + Native via WKWebView

### ❌ Native-only:
- `AudioSession` + Background Play (nur Swift)
- `MediaPlayer` + Lock Screen (nur Swift)
- `FileManager` + Documents/ (nur Swift, aber über Bridge abrufbar)
- Share Sheet (nur native)

---

## Repository-Struktur nach Vollständigkeit

```
hometools/
├── src/hometools/               ← Backend (unverändert)
├── web/                         ← PWA Assets (unverändert)
├── ios/                         ← NEU: Native Apps
│   ├── HometoolsVideo/
│   ├── HometoolsAudio/
│   └── Shared/
│
├── .OFFLINE_FEATURE.md          ← PWA Plan
├── .iOS_PWA_DECISIONS.md        ← iOS Limitations
├── .ARCHITECTURE.md             ← Zwei-Server-Ansatz
├── .NATIVE_APP_PLAN.md          ← DIESE DATEI
└── README.md                    ← Update mit iOS App Info
```

---

## Wichtige Hinweise

### 1. **Backend läuft immer** (auch mit Native App)
   - Native App = nur UI-Wrapper
   - Backend muss auf dem Netzwerk erreichbar sein
   - Keine App-internen Server

### 2. **PWA und Native App sind parallel nutzbar**
   - PWA: `http://localhost:8011` im Safari
   - Native App: WKWebView im selben Backend
   - Oder: Native App zeigt PWA von anderem Device

### 3. **Updates sind trivial**
   - UI-Update: Backend-Update (beide automatisch)
   - Feature-Add: PWA (bei Bedarf) + Native (wenn nötig)
   - Keine parallelen Versionen verwalten

### 4. **App Store vs. Sideload**
   - Option A: App Store (Apple Review nötig, ~1-2 Wochen)
   - Option B: TestFlight (schneller, Ad-hoc)
   - Option C: Sideload via Xcode (nur für Entwicklung)

---

## Zu beachtende Punkte

- [ ] Apple Developer Account ($99/Jahr)
- [ ] Provisioning Profile + Signing Certificates
- [ ] App Privacy Policy (datenschutz.eu)
- [ ] Lokale Backend-Funktion dokumentieren
- [ ] TestFlight Beta mit Freunden testen

---

## Nächste Schritte

1. **PWA-Feature zu Ende bringen** (Offline-Downloads)
2. **Diese Architektur diskutieren** — OK für dich?
3. **Xcode Projekte erstellen** (Swift scaffolding)
4. **WebView Bridge implementieren**
5. **Native Features hinzufügen** (Audio, Lock Screen)

**Frage:** Soll ich mit Phase 2 (Xcode Setup) beginnen?

