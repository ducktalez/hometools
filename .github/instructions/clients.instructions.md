---
applyTo: "clients/**"
---
# Native Clients

Native client apps (Android TV now; iOS/Android phone later) for the hometools
streaming backend. See `clients/README.md` for the architecture.

## Core rules

- **API-first, no duplicated logic.** All business logic lives in the Python
  backend and is exposed via REST. Clients are thin consumers — never
  re-implement catalog/progress/intro/rating logic in client code.
- **Admin tools stay web-only.** Clients call **only** the read/playback subset
  (`items`, `continue`, `metadata`, `progress`, `intro`, `/video/stream`,
  `/thumb`). Never add rating writes, tag edits, file move/delete or playlist
  mutation to a native client.
- **Contract is the OpenAPI schema.** `clients/shared/openapi/*.json` is the
  single source of truth. After any backend API change, regenerate it with
  `hometools export-openapi --server {video,audio}` and update dependent client
  code in the same change.
- **`MediaItem` field names are the contract.** Client models mirror
  `src/hometools/streaming/core/models.py:MediaItem.to_dict()`. Tolerate unknown
  fields (forward-compatible JSON parsing); never assume admin-only fields.
- **API responses use the `items` key** (not `tracks`/`videos`) — same as the
  backend rule.
- **Backend gaps belong in the backend.** If a client needs data the API does
  not provide (e.g. a feed, larger artwork), add/extend a backend endpoint +
  test — do not scrape or compute it client-side.

## When adding a client feature

1. Check the endpoint exists in `clients/shared/openapi/`. If not, add it to the
   backend first (with a test), then re-export the schema.
2. Keep the playback/admin split: if it's an admin action, it does **not** go
   into a native client.
3. Update the relevant `clients/<platform>/README.md` and
   `docs/IMPLEMENTATION_PLAN.md`.

