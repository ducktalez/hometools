# INSTRUCTIONS — hometools

> Auto-generated. Run `hometools update-instructions` after structural changes.

## Scope

hometools = media library tools + local streaming prototypes (audio & video).
One shared core, two servers, common dark-theme UI.

## Architecture

| Domain | Package | Instruction file |
|--------|---------|-----------------|
| **Audio/Video file tools** | `audio/`, `video/` | [tools.instructions.md](instructions/tools.instructions.md) |
| **Streaming** | `streaming/` | [streaming.instructions.md](instructions/streaming.instructions.md) |

## Rules (global)

1. **Keep instructions lean.** Only include what an AI assistant needs to make correct changes. Avoid repeating information that is obvious from the code. Overly verbose instructions distort task focus.
2. **No hardcoded paths.** Use `config.py` helpers or CLI args.
3. **No secrets in source.** Use `.env` (gitignored).
4. **No side effects at import time.** Code behind CLI commands or explicit calls.
5. **Pure functions first.** Separate I/O from transformation; test the logic.
6. **Tests for every new pure function.** `tests/`, run `pytest`.
7. **Logging, not print.** `logging.getLogger(__name__)` in library code.
8. **Sync only on explicit command.** Never auto-pull from NAS.
9. **Update instructions after structural changes.** `hometools update-instructions`.
10. **Robust exception handling.** Every public function must handle errors gracefully and never crash the caller. Use try/except with logging — return sensible defaults (e.g. empty list, `None`, `False`) on failure.
11. **No blocking on long-running operations.** Expensive work (thumbnail extraction, network I/O, large file scans) must run in background threads or be deferred. Use dummy/placeholder values until results are ready so the UI stays responsive on first start.

## CLI

```
hometools serve-audio / serve-video [--library-dir] [--host] [--port]
hometools sync-audio  / sync-video  [--source] [--target] [--dry-run]
hometools serve-all [--host] [--audio-port] [--video-port]
hometools streaming-config
hometools setup-pycharm [--project-root]
hometools update-instructions [--repo-root]
```

## Config (env vars → `config.py`)

```
TMDB_API_KEY, HOMETOOLS_DELETE_DIR,
HOMETOOLS_AUDIO_LIBRARY_DIR, HOMETOOLS_AUDIO_NAS_DIR,
HOMETOOLS_VIDEO_LIBRARY_DIR, HOMETOOLS_VIDEO_NAS_DIR,
HOMETOOLS_STREAM_HOST, HOMETOOLS_AUDIO_PORT, HOMETOOLS_VIDEO_PORT
```
