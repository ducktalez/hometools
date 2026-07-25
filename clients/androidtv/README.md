# hometools TV (Android TV)

Native Android TV app — a lean, D-pad-driven, Netflix/Jellyfin-style client for
the hometools **video** backend. It is **not** a WebView wrapper: a 10-foot UI
needs native focus handling and a native player.

## Why native (not the website)

- **D-pad / 10-foot UI** via Jetpack **Compose for TV** (`androidx.tv.material3`).
- **Media3 / ExoPlayer** plays MP4 **and MKV/AVI** with HTTP Range directly from
  `/video/stream` — formats the TV browser refuses. Less reliance on
  server-side transcoding.
- Appears on the Android TV home screen (LEANBACK_LAUNCHER + banner).

## Scope (read/playback only)

Calls only the playback subset of the API: `items`, `continue`, `metadata`,
`progress`, `intro`, plus `/video/stream` and `/thumb`. **No admin tools**
(rating/tag/move/delete/playlists) — those stay in the web UI. See
[`../README.md`](../README.md).

## Project structure

```
androidtv/
├── settings.gradle.kts
├── build.gradle.kts
├── gradle/libs.versions.toml      ← version catalog (AGP, Kotlin, TV, Media3…)
└── app/
    ├── build.gradle.kts
    └── src/main/
        ├── AndroidManifest.xml    ← LEANBACK_LAUNCHER, INTERNET, cleartext (LAN HTTP)
        ├── java/com/hometools/tv/
        │   ├── MainActivity.kt    ← setup ▸ browse ▸ player navigation
        │   ├── data/              ← Models, VideoApi (Retrofit), ApiClient, ServerConfig
        │   └── ui/                ← BrowseScreen, PlayerScreen, ServerSetupScreen, theme
        └── res/                   ← strings, theme, placeholder icon/banner
```

## Build (requires Android SDK + JDK 17)

```bash
cd clients/androidtv
# Add a Gradle wrapper once (not committed): gradle wrapper --gradle-version 8.9
./gradlew assembleDebug
# Install to a connected Android TV / emulator:
./gradlew installDebug
```

> **Backend must be reachable** from the TV (same LAN). On first run, confirm the
> server URL (default `http://192.168.178.87:8011`).

## Contract / codegen

The data layer mirrors [`../shared/openapi/video-openapi.json`](../shared/openapi).
Regenerate the schema after backend API changes:

```bash
hometools export-openapi --server video
```

## Known scaffold gaps (tracked in docs/IMPLEMENTATION_PLAN.md)

- Wrapper scripts committed; wrapper JAR is generated locally (`gradle wrapper`).
- Placeholder icon/banner (vector) — replace with branded artwork.
- Server URL entry is a stub (TV text input is awkward) — add IP stepper / QR pairing.
- Larger poster art: backend thumbs are 120 px / 480 px; true posters/backdrops TBD.
- No auth (LAN only) — device token/discovery is a follow-up.

