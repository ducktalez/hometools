# OpenAPI contract

This directory holds the **exported OpenAPI schema** of the hometools backend.
It is the single source of truth shared by the web admin UI and all native
clients.

## Files

- `video-openapi.json` — Video server JSON API (`/api/video/*` + `/health`).
- `audio-openapi.json` — Audio server JSON API (`/api/audio/*` + `/health`).

**Do not hand-edit.** Regenerate after any backend API change:

```bash
hometools export-openapi --server video
hometools export-openapi --server audio
```

A contract test (`tests/test_openapi_export.py`) locks the playback-relevant
paths so they cannot silently disappear.

## Binary / non-JSON endpoints (not in the schema)

These are intentionally excluded from the schema (FastAPI Response subclasses)
but are part of the client contract. They are plain `GET` requests:

| Endpoint | Query params | Returns |
|----------|--------------|---------|
| `/video/stream` | `path` (URL-encoded relative path) | Range-capable MP4 stream |
| `/thumb` | `path`, optional `size=lg` | JPEG thumbnail (120 px / 480 px) |

`relative_path` values come from the `items[]` entries of
`GET /api/video/items` and `GET /api/video/continue`.

## Generating a typed client (Android TV / Kotlin)

The Android TV app uses a hand-written thin Retrofit interface that mirrors
this schema (see `clients/androidtv/app/src/main/java/.../data/`). When the
surface grows, switch to generated code:

```bash
# Example with openapi-generator (not committed; run on demand)
openapi-generator-cli generate \
  -i clients/shared/openapi/video-openapi.json \
  -g kotlin \
  --library jvm-retrofit2 \
  -o clients/androidtv/generated
```

> Keep generated code out of version control (add to the module `.gitignore`)
> and regenerate from the committed schema.

