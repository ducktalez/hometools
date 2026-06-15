# syntax=docker/dockerfile:1.7

# ─── Stage 1: builder ──────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Build deps only — runtime image stays minimal
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Isolated venv we copy into the runtime stage
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies first (better layer caching)
COPY pyproject.toml requirements.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy source and install hometools itself (no extra deps fetched)
COPY src/ ./src/
COPY README.md LICENSE ./
RUN pip install --no-deps .


# ─── Stage 2: runtime ──────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    # Bind to all interfaces inside the container — published ports map this out
    HOMETOOLS_STREAM_HOST=0.0.0.0 \
    # Disposable + permanent state live on mounted volumes
    HOMETOOLS_CACHE_DIR=/data/cache \
    HOMETOOLS_AUDIT_DIR=/data/audit \
    # Default library paths inside the container — overridable via compose env
    HOMETOOLS_AUDIO_LIBRARY_DIR=/media/audio \
    HOMETOOLS_VIDEO_LIBRARY_DIR=/media/video

# Runtime deps:
#   ffmpeg/ffprobe — thumbnails, waveforms, remux, channel transcode
#   tini           — proper PID 1, clean signal forwarding for uvicorn
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        tini \
    && rm -rf /var/lib/apt/lists/*

# Bring in the venv (with hometools installed)
COPY --from=builder /opt/venv /opt/venv

# Non-root user — UID/GID overridable at build time so the container can
# read NAS shares mounted with specific ownership (Synology PUID/PGID pattern).
# Robust against pre-existing GID/UID: on Synology PGID=100 ("users") already
# exists in the base image, so a naive `groupadd -g 100` would fail. We reuse
# an existing group/user when present and only create what's missing.
ARG PUID=1000
ARG PGID=1000
RUN set -eux; \
    if ! getent group "${PGID}" >/dev/null; then \
        groupadd -g "${PGID}" hometools; \
    fi; \
    if ! getent passwd "${PUID}" >/dev/null; then \
        useradd -u "${PUID}" -g "${PGID}" -m -s /usr/sbin/nologin hometools; \
    fi; \
    mkdir -p /data/cache /data/audit /media/audio /media/video; \
    chown -R "${PUID}:${PGID}" /data /home/hometools 2>/dev/null || chown -R "${PUID}:${PGID}" /data

USER ${PUID}:${PGID}
WORKDIR /home/hometools

# Healthcheck: every server exposes /health.  HC_PORT is set per-service in
# docker-compose so audio/video/channel containers each probe their own port.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request,sys; \
port=os.environ.get('HC_PORT','8010'); \
sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=3).status==200 else 1)" \
        || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "hometools"]
# Service-specific arguments come from `command:` in docker-compose.yml.
CMD ["serve-all"]

