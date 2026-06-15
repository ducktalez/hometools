# hometools clients

Native client applications for the hometools streaming backend.

> **Status:** Android TV is the active target. `android/` (phone) and `ios/`
> are reserved for later.

## Architecture: API-first, no duplicated logic

The Python backend (`src/hometools/`) owns **all** business logic and exposes
it as a JSON REST API. The web admin UI (server-rendered) and every native
client are **thin clients of the same API** — none of them re-implement
catalog, progress, intro-detection, etc.

```
                ┌──────────────────────────────┐
                │   Python backend (FastAPI)    │  ← single source of truth
                │   /api/video/*  /api/audio/*  │
                └───────────────┬──────────────┘
            REST/JSON           │           REST/JSON
        ┌───────────────────────┼────────────────────────┐
        ▼                       ▼                         ▼
  Web admin UI            Android TV app            iOS / Android (later)
 (full feature set)   (lean, D-pad, playback)       (lean, playback)
```

### Why this prevents double development

- **Functionality lives server-side.** Clients call endpoints; they don't
  re-encode rating/tag/move logic.
- **Admin tools stay web-only.** Rating writes, tag edits, file move/delete,
  playlist management (`POST/PUT/DELETE /api/.../*`) are **never** ported to
  the TV app. The TV app calls only the **read/playback subset**
  (`items`, `continue`, `metadata`, `progress`, `intro`, `stream`, `thumb`).
- **One contract, generated clients.** `clients/shared/openapi/` holds the
  exported OpenAPI schema. Typed clients are generated from it, so a backend
  API change surfaces as a client compile error instead of silent drift.

## Contract source

Regenerate the OpenAPI schema after any API change:

```bash
hometools export-openapi --server video   # -> clients/shared/openapi/video-openapi.json
hometools export-openapi --server audio   # -> clients/shared/openapi/audio-openapi.json
```

Only the JSON API surface (`/api/*` + `/health`) is in the schema. Binary
endpoints are simple GETs documented in `clients/shared/openapi/README.md`:

- `GET /video/stream?path=<relative_path>` → video bytes (Range-capable MP4)
- `GET /thumb?path=<relative_path>&size=lg` → JPEG thumbnail

## Layout

```
clients/
├── README.md                ← this file
├── shared/
│   └── openapi/             ← exported OpenAPI schema (contract) + codegen notes
├── androidtv/              ← Android TV native app (Kotlin, Compose for TV, Media3)
├── android/                ← reserved: phone app
└── ios/                    ← reserved: iOS app (see docs/plans/native_app_plan.md)
```

