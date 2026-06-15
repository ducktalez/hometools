---
applyTo: "clients/androidtv/**"
---
# Android TV App

Native Android TV client (Kotlin + Jetpack Compose for TV + Media3/ExoPlayer).
Read `clients/androidtv/README.md` and the general `clients.instructions.md`
first.

## Key rules

- **Compose for TV, not phone Material3.** Use `androidx.tv.material3` and
  `androidx.tv.foundation` (TvLazyRow/TvLazyColumn) so D-pad focus works. Never
  import `androidx.compose.material3` components for the 10-foot UI.
- **No WebView.** The TV UI is fully native — a browser/WebView cannot deliver
  the D-pad 10-foot experience. (WebView wrapping stays an iOS-only idea.)
- **Playback via Media3/ExoPlayer** against `/video/stream`. ExoPlayer handles
  MP4/MKV/AVI + HTTP Range; do not require server-side transcoding for formats
  ExoPlayer supports.
- **Three screens only:** server setup → browse → player. Keep navigation a
  simple state machine in `MainActivity`; no heavy nav framework unless it grows.
- **Versions live in `gradle/libs.versions.toml`.** Add dependencies via the
  version catalog (`libs.*`), not hardcoded coordinates.
- **LAN HTTP is intentional.** `usesCleartextTraffic="true"` + `INTERNET`
  permission; the backend is `http://<NAS>:8011`. Don't add TLS assumptions.
- **Exception-safe data calls.** Wrap API calls in `runCatching`; show a
  fallback/empty state, never crash on a backend hiccup (mirrors the backend's
  "never crash the caller" rule).
- **Progress writes** use `POST /api/video/progress` periodically + on exit;
  resume via `GET /api/video/progress`.

## Data layer

`app/src/main/java/com/hometools/tv/data/` mirrors the OpenAPI contract:
`Models.kt` (MediaItem/ItemsResponse), `VideoApi.kt` (Retrofit, playback subset),
`ApiClient.kt` (Retrofit + URL helpers), `ServerConfig.kt` (persisted base URL).
When the surface grows, switch to an OpenAPI-generated client and keep the
generated code out of git (`/generated/`).

## Don't

- Don't add admin endpoints (rating/tag/move/delete/playlists) to `VideoApi`.
- Don't commit a Gradle wrapper jar/binary or build outputs (see `.gitignore`).
- Don't hardcode the server IP in code paths other than the setup default.

