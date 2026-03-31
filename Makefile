PYTHON ?= hometools-env/Scripts/python.exe
RUFF ?= hometools-env/Scripts/ruff.exe

SERVER ?= audio
MODE ?= missing
SCOPE ?= all
TODO_KEY ?=
TODO_ACTION ?= acknowledge
TODO_SECONDS ?= 3600

.PHONY: help lint format test parity streaming-config issues issues-json issues-errors todos todos-json scheduler-once todo-state dashboard dashboard-json \
	serve-audio serve-video serve-all \
	serve-audio-safe serve-video-safe serve-all-safe \
	reset reset-hard reset-all-hard \
	prewarm prewarm-full audio-prewarm video-prewarm audio-reindex video-reindex \
	clean

help:
	@echo "Targets:"
	@echo "  lint                - ruff check src/tests"
	@echo "  format              - ruff format src/tests"
	@echo "  test                - pytest tests -q"
	@echo "  parity              - pytest tests/test_feature_parity.py -v"
	@echo "  streaming-config    - print resolved streaming config"
	@echo "  issues              - show currently open irregularities from warning/error collection"
	@echo "  issues-json         - show current irregularities as JSON"
	@echo "  issues-errors       - return non-zero when error/critical issues are open"
	@echo "  todos               - derive TODO candidates from open irregularities"
	@echo "  todos-json          - derive TODO candidates as JSON"
	@echo "  scheduler-once      - run the first scheduler stub once and persist todo_candidates.json"
	@echo "  todo-state          - acknowledge/snooze/clear TODO state (TODO_KEY=..., TODO_ACTION=..., TODO_SECONDS=... for snooze)"
	@echo "  dashboard           - show combined issues/TODOs/scheduler dashboard"
	@echo "  dashboard-json      - show combined dashboard as JSON"
	@echo "  serve-audio         - start audio server"
	@echo "  serve-video         - start video server"
	@echo "  serve-all           - start both servers"
	@echo "  serve-audio-safe    - start audio server in safe mode"
	@echo "  serve-video-safe    - start video server in safe mode"
	@echo "  serve-all-safe      - start both servers in safe mode"
	@echo "  reset               - remove generated artifacts for SERVER=audio|video|all"
	@echo "  reset-hard          - remove generated artifacts incl. thumbs/logs for SERVER=..."
	@echo "  reset-all-hard      - hard reset for both servers"
	@echo "  prewarm             - build caches for SERVER=audio|video MODE=missing|full SCOPE=all|index|thumbnails"
	@echo "  prewarm-full        - full rebuild for SERVER=audio|video"
	@echo "  audio-prewarm       - missing-only prewarm for audio"
	@echo "  video-prewarm       - missing-only prewarm for video"
	@echo "  audio-reindex       - full audio index rebuild (no thumbnails)"
	@echo "  video-reindex       - full video index rebuild (no thumbnails)"
	@echo "  clean               - delete all generated cache files"
	@echo "                        (thumbnails, indexes, progress, issues, logs, shortcuts,"
	@echo "                         video_metadata_cache.json, thumbnail_failures.json)"
	@echo "                        Audit log (.hometools-audit/) is a separate directory"
	@echo "                        and is NOT affected by clean."

lint:
	$(RUFF) check src tests --fix

format:
	$(RUFF) format src tests

test:
	$(PYTHON) -m pytest tests -q

parity:
	$(PYTHON) -m pytest tests/test_feature_parity.py -v

streaming-config:
	$(PYTHON) -m hometools streaming-config

issues:
	$(PYTHON) -m hometools stream-issues

issues-json:
	$(PYTHON) -m hometools stream-issues --json

issues-errors:
	$(PYTHON) -m hometools stream-issues --only-errors --fail-on-match

todos:
	$(PYTHON) -m hometools stream-todos

todos-json:
	$(PYTHON) -m hometools stream-todos --json

scheduler-once:
	$(PYTHON) -m hometools stream-scheduler --json

todo-state:
	$(PYTHON) -m hometools stream-todo-state --todo-key "$(TODO_KEY)" --action $(TODO_ACTION) --seconds $(TODO_SECONDS)

dashboard:
	$(PYTHON) -m hometools stream-dashboard

dashboard-json:
	$(PYTHON) -m hometools stream-dashboard --json

serve-audio:
	$(PYTHON) -m hometools serve-audio

serve-video:
	$(PYTHON) -m hometools serve-video

serve-all:
	$(PYTHON) -m hometools serve-all

serve-audio-safe:
	$(PYTHON) -m hometools serve-audio --safe-mode

serve-video-safe:
	$(PYTHON) -m hometools serve-video --safe-mode

serve-all-safe:
	$(PYTHON) -m hometools serve-all --safe-mode

reset:
	$(PYTHON) -m hometools stream-reset --server $(SERVER)

reset-hard:
	$(PYTHON) -m hometools stream-reset --server $(SERVER) --hard

reset-all-hard:
	$(PYTHON) -m hometools stream-reset --server all --hard

prewarm:
	$(PYTHON) -m hometools stream-prewarm --server $(SERVER) --mode $(MODE) --scope $(SCOPE)

prewarm-full:
	$(PYTHON) -m hometools stream-prewarm --server $(SERVER) --mode full --scope all

audio-prewarm:
	$(PYTHON) -m hometools stream-prewarm --server audio --mode missing --scope all

video-prewarm:
	$(PYTHON) -m hometools stream-prewarm --server video --mode missing --scope all

audio-reindex:
	$(PYTHON) -m hometools stream-prewarm --server audio --mode full --scope index

video-reindex:
	$(PYTHON) -m hometools stream-prewarm --server video --mode full --scope index

clean:
	@echo "Deleting generated cache files (thumbnails, indexes, progress, issues, logs, shortcuts) ..."
	$(PYTHON) -c "\
import shutil, pathlib; \
cache = pathlib.Path('.hometools-cache'); \
deleted = []; \
[( \
    (deleted.append(str(p)), shutil.rmtree(p)) if p.is_dir() \
    else (deleted.append(str(p)), p.unlink()) \
) for p in sorted(cache.iterdir())] if cache.exists() else None; \
print('  deleted:', len(deleted), 'items') \
"
	@echo "Done. Run 'make audio-prewarm' or 'make video-prewarm' to rebuild."

