# Android phone app (reserved)

Not started yet. Priority order: **Android TV first** (`../androidtv/`), then
iOS, then this phone app.

A phone app should reuse the same API-first approach as the TV app: thin client
over `clients/shared/openapi/`, playback-focused, **no admin tools** (those stay
in the web UI). Likely Kotlin + Jetpack Compose + Media3, sharing data-layer
code with `androidtv/` via a future `:shared` Gradle module.

