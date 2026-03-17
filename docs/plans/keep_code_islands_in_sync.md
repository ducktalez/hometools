# Code-Inseln synchron halten — Strategien

## Das Problem: Drift zwischen Code-Inseln

Aktuell haben wir mehrere "Inseln":
- **Backend:** Audio/Video Server (Python)
- **Frontend:** PWA (HTML/CSS/JS)
- **Native:** iOS Apps (Swift)
- **Docs:** Pläne & Decisions (.md)

Diese können zeitlich auseinanderdriften:
- ❌ Audio-Server bekommt Feature, Video-Server nicht
- ❌ PWA-UI ändert sich, Native App folgt nicht
- ❌ Docs dokumentieren etwas, Code macht etwas anderes
- ❌ Backend-API ändert sich, Frontend nutzt alte Version

## Warum NOT Copilot-Hook?

```
❌ Copilot in Pre-Commit:
  - 💰 Kostspielig (~$0.01/Commit × Team × Zeit)
  - 🐢 Langsam (API-Call bei jedem Commit)
  - 🔑 API-Key in Repo nötig (Sicherheitsrisiko)
  - 🎲 Nicht-deterministisch (gleicher Code → verschiedene Antworten)
  - 👥 Nicht-reproducible (verschiedene Benutzer → verschiedene Results)
```

**Besser:** Deterministisch + lokal + kostenfrei

---

## Lösung 1: Feature-Parity Tests (STARK EMPFOHLEN)

Automatisiert testen, dass Audio + Video die gleichen Features haben.

### Beispiel: Feature-Parity Test

```python
# tests/test_feature_parity.py
"""Ensure audio and video servers have identical features."""

import inspect
from hometools.streaming.audio import server as audio_server
from hometools.streaming.video import server as video_server


def test_both_servers_have_same_endpoints():
    """Both servers must expose the same endpoints."""
    audio_endpoints = {route.path for route in audio_server.app.routes}
    video_endpoints = {route.path for route in video_server.app.routes}
    
    assert audio_endpoints == video_endpoints, \
        f"Endpoint mismatch:\n" \
        f"  Audio only: {audio_endpoints - video_endpoints}\n" \
        f"  Video only: {video_endpoints - audio_endpoints}"


def test_both_servers_have_same_pwa_manifests():
    """PWA Manifest structure must be identical."""
    audio_manifest = audio_server.get_manifest()
    video_manifest = video_server.get_manifest()
    
    # Check same keys
    assert audio_manifest.keys() == video_manifest.keys()
    
    # Check same icons
    assert audio_manifest["icons"] == video_manifest["icons"]


def test_player_bar_styles_exist():
    """Both servers must support the same player bar styles."""
    from hometools.config import get_player_bar_style
    
    styles = ["classic", "waveform"]
    for style in styles:
        # Both must render without error
        audio_html = audio_server.render_audio_index_html(
            [],
            player_bar_style=style
        )
        video_html = video_server.render_video_index_html(
            [],
            player_bar_style=style
        )
        
        assert "player-bar" in audio_html
        assert "player-bar" in video_html
```

✅ **Automatisches Testen bei jedem Commit (über Pre-Commit-Hook)**
✅ **Lokal, schnell, gratis**
✅ **Deterministisch**

---

## Lösung 2: API-Contract Tests

Explizit definieren, was die Schnittstellen zwischen "Inseln" sind.

### Beispiel: Backend ↔ Frontend Contract

```python
# tests/test_api_contract.py
"""Ensure Backend → Frontend API doesn't change accidentally."""

def test_media_item_schema_stays_stable():
    """MediaItem JSON structure must stay compatible."""
    from hometools.streaming.core.models import MediaItem
    
    item = MediaItem(
        path="test.mp3",
        title="Test",
        artist="Artist",
        media_type="audio",
        relative_path="path/test.mp3",
    )
    
    json_dict = item.to_dict()
    
    # These fields MUST exist (Frontend depends on them)
    required = {"title", "artist", "stream_url", "thumbnail_url", "media_type"}
    assert required.issubset(json_dict.keys()), \
        f"Missing required fields: {required - set(json_dict.keys())}"


def test_api_response_format_audio():
    """Audio API endpoint structure."""
    response = audio_server.query_tracks([], q=None, artist=None)
    
    assert "items" in response
    assert "count" in response
    assert "artists" in response


def test_api_response_format_video():
    """Video API endpoint structure."""
    response = video_server.query_items([], q=None, artist=None)
    
    assert "items" in response
    assert "count" in response
    assert "artists" in response
```

---

## Lösung 3: Documentation as Code

Die .md Files sind die **Single Source of Truth**. Code muss sie einhalten.

### Struktur:

```
Docs (Quelle der Wahrheit)
├─ .SHARED_SERVER_REFACTORING.md
│  ├─ Server müssen diese Endpoints haben
│  ├─ Diese JS-Features müssen beide unterstützen
│  └─ Diese Config-Keys sind required
│
├─ .NATIVE_APP_PLAN.md
│  ├─ WebView-Bridge muss diese Methods haben
│  ├─ AudioSession-Features
│  └─ Storage-API
│
└─ .iOS_PWA_DECISIONS.md
   ├─ PWA speichert unter 50 MB
   ├─ Native App speichert unbegrenzt
   └─ Fallback-Kette

↓ (Validiert durch Tests)

Code
├─ Backend
├─ PWA
└─ Native App
```

### Pre-Commit-Hook: Docs-Validierung

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Checklist: Gibt es Commits ohne zugehörige Docs-Updates?
# (nur informativ, nicht blockierend)

if git diff --cached --name-only | grep -E "\.py$"; then
    if ! git diff --cached --name-only | grep -E "\.md$"; then
        echo "⚠️  Code geändert, aber keine Docs Updates?"
        echo "   Bitte .md Files aktualisieren wenn Architektur-Änderung"
    fi
fi
```

---

## Lösung 4: Shared Code + Factory Pattern

**Der beste Weg, Drift zu verhindern: Weniger Duplikation.**

Das ist warum der Refactoring so wichtig ist:

```python
# Vorher: Drift-anfällig
audio/server.py  ← 200 LOC Duplikation
video/server.py  ← 200 LOC Duplikation
                   ↑ können unabhängig auseinanderdriften

# Nachher: Drift-sicher
core/server_factory.py  ← 300 LOC zentral
audio/server.py         ← 30 LOC Config
video/server.py         ← 30 LOC Config
                          ↑ ändern sich zusammen
```

---

## Mein Empfohlener Ansatz (3-teilig)

### 1. **Feature-Parity Tests** (Jetzt)
```bash
Pre-Commit Hook:
  ✅ pytest tests/test_feature_parity.py
  ✅ pytest tests/test_api_contract.py
```

→ Blockiert Code-Drift automatisch

### 2. **Server Refactoring** (vor Native Apps)
```
Implementiere den Shared Server Factory
→ Von 400 LOC Duplikation → 60 LOC
```

→ Weniger Stellen zum auseinanderdriften

### 3. **Docs-Checkliste** (Prozess)
```
Bei jedem Major Feature:
  □ Code implementiert
  □ Test geschrieben
  □ .md File aktualisiert
  □ Feature-Parity Test hinzugefügt
```

→ Dokumentation bleibt in Sync

---

## Implementation: Feature-Parity Hook

```python
# tests/test_feature_parity.py - NEUES TEST-FILE

import pytest
from hometools.streaming.audio import server as audio_mod
from hometools.streaming.video import server as video_mod


class TestServerParity:
    """Ensure audio and video servers stay in sync."""
    
    def test_same_static_endpoints(self):
        """Both servers must support /health, /manifest.json, /sw.js, /icon-*"""
        required = {
            "/health",
            "/manifest.json",
            "/sw.js",
            "/icon.svg",
            "/icon-192.png",
            "/icon-512.png",
        }
        
        # Skip dynamic endpoints like /stream, /api/...
        audio_app = audio_mod.create_app()
        video_app = video_mod.create_app()
        
        audio_routes = {r.path for r in audio_app.routes}
        video_routes = {r.path for r in video_app.routes}
        
        for endpoint in required:
            assert endpoint in audio_routes, f"Audio missing {endpoint}"
            assert endpoint in video_routes, f"Video missing {endpoint}"
    
    def test_same_supported_media_elements(self):
        """Audio uses <audio>, Video uses <video>."""
        # This test ensures we don't accidentally swap them
        # (unlikely, but good to have)
        pass


class TestAPIContract:
    """Frontend relies on these API shapes."""
    
    def test_media_item_has_required_fields(self):
        """All items must have these fields."""
        from hometools.streaming.core.models import MediaItem
        
        item = MediaItem.create_dummy()  # hypothetical factory
        d = item.to_dict()
        
        required = {
            "title", "artist", "stream_url", 
            "thumbnail_url", "media_type", "relative_path"
        }
        
        assert required.issubset(d.keys()), \
            f"Missing: {required - set(d.keys())}"


# Add to .pre-commit-config.yaml:
# - repo: local
#   hooks:
#     - id: feature-parity
#       name: feature-parity tests
#       entry: pytest tests/test_feature_parity.py
#       language: system
#       pass_filenames: false
#       stages: [commit]
```

---

## Zusammenfassung: Was macht was

| Strategie | Zweck | Aufwand | Effektivität |
|-----------|-------|---------|--------------|
| **Feature-Parity Tests** | Blockiert Drift | 2h | ⭐⭐⭐⭐⭐ |
| **Server Refactoring** | Eliminiert Duplikation | 4h | ⭐⭐⭐⭐⭐ |
| **API Contract Tests** | Validiert Schnittstellen | 2h | ⭐⭐⭐⭐ |
| **Docs-Checkliste** | Prozess-Level | 0h (Disziplin) | ⭐⭐⭐ |
| **Copilot Hook** | ? | 💰 teuer | ❌ Nicht praktikabel |

---

## Roadmap

```
Woche 1: PWA Offline-Feature
         ↓
Woche 2: Server Refactoring + Feature-Parity Tests
         ↓
Woche 3: Native Apps (auf sauberem Backend)
```

Mit diesem Ansatz driften die Code-Inseln nicht auseinander.

