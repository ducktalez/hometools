#!/usr/bin/env bash
#
# deploy-synology.sh — One-shot deploy / update of hometools on a Synology NAS.
#
# Run this ON the Synology (via SSH), NOT on your dev machine:
#
#   ssh <dsm-user>@192.168.178.87
#   sudo mkdir -p /volume1/docker && cd /volume1/docker
#   git clone https://github.com/ducktalez/hometools.git   # first time only
#   cd hometools
#   sudo bash scripts/deploy-synology.sh
#
# What it does (idempotent — safe to re-run for updates):
#   1. git pull  (if this is a git checkout)
#   2. create .env from docker/.env.example if missing, auto-filling PUID/PGID
#   3. validate that the library paths in .env are real, existing directories
#   4. docker compose up -d --build
#   5. print the reachable URLs + a health probe
#
# It never handles passwords. Docker on DSM needs root → run with sudo.

set -euo pipefail

REPO_URL="https://github.com/ducktalez/hometools.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

log()  { printf '\033[1;36m[deploy]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[deploy] WARN:\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[deploy] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# ── Pick the available compose command ──────────────────────────────────────
if docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
else
    die "Neither 'docker compose' nor 'docker-compose' is available. Install/enable Container Manager."
fi
log "Using compose command: ${COMPOSE[*]}"

# ── 1. Update the checkout ──────────────────────────────────────────────────
if [ -d .git ]; then
    log "Updating source via git pull …"
    git pull --ff-only || warn "git pull failed (local changes?) — continuing with current checkout."
else
    warn "Not a git checkout — skipping update. (Cloned via ZIP? Replace the folder to update.)"
    warn "Tip: git clone $REPO_URL"
fi

# ── 2. Ensure .env exists ───────────────────────────────────────────────────
if [ ! -f .env ]; then
    if [ -f docker/.env.synology.example ]; then
        TEMPLATE="docker/.env.synology.example"
    else
        TEMPLATE="docker/.env.example"
    fi
    log "No .env found — creating one from ${TEMPLATE} …"
    cp "$TEMPLATE" .env

    # Auto-fill PUID/PGID from the invoking (pre-sudo) user when possible.
    REAL_USER="${SUDO_USER:-$(id -un)}"
    REAL_UID="$(id -u "$REAL_USER" 2>/dev/null || id -u)"
    REAL_GID="$(id -g "$REAL_USER" 2>/dev/null || id -g)"
    sed -i "s/^PUID=.*/PUID=${REAL_UID}/" .env
    sed -i "s/^PGID=.*/PGID=${REAL_GID}/" .env
    log "Set PUID=${REAL_UID} PGID=${REAL_GID} (user: ${REAL_USER})."

    warn "Edit .env now and set AUDIO_LIBRARY_PATH / VIDEO_LIBRARY_PATH to your real shares,"
    warn "e.g. /volume1/music and /volume1/video, then re-run this script."
    die  "Stopping so you can fill in the library paths in $PROJECT_DIR/.env"
fi

# ── 3. Validate library paths ───────────────────────────────────────────────
# shellcheck disable=SC1091
set -a; . ./.env; set +a

for var in AUDIO_LIBRARY_PATH VIDEO_LIBRARY_PATH; do
    val="${!var:-}"
    case "$val" in
        ""|/path/to/*)
            die "$var is not configured in .env (still a placeholder). Set it to a real directory." ;;
    esac
    [ -d "$val" ] || die "$var=$val does not exist or is not a directory (check the share path)."
done
log "Library paths OK: AUDIO=$AUDIO_LIBRARY_PATH  VIDEO=$VIDEO_LIBRARY_PATH"

# ── 4. Build + start ────────────────────────────────────────────────────────
log "Building and starting containers (first build can take several minutes) …"
"${COMPOSE[@]}" up -d --build

# ── 5. Report ───────────────────────────────────────────────────────────────
AUDIO_PORT="${AUDIO_PORT:-8010}"
VIDEO_PORT="${VIDEO_PORT:-8011}"
HOST_IP="$(hostname -i 2>/dev/null | awk '{print $1}')"
[ -n "${HOST_IP:-}" ] || HOST_IP="<NAS-IP>"

log "Containers:"
"${COMPOSE[@]}" ps

log "Probing /health endpoints …"
for port in "$AUDIO_PORT" "$VIDEO_PORT"; do
    if curl -fsS "http://127.0.0.1:${port}/health" >/dev/null 2>&1; then
        log "  port ${port}: healthy"
    else
        warn "  port ${port}: not healthy yet (the index may still be building — give it a minute)."
    fi
done

cat <<EOF

────────────────────────────────────────────────────────────
 hometools is up. Open from any device in your LAN:

   Audio : http://${HOST_IP}:${AUDIO_PORT}
   Video : http://${HOST_IP}:${VIDEO_PORT}

 If the DSM firewall blocks it:
   Control Panel → Security → Firewall → allow TCP ${AUDIO_PORT},${VIDEO_PORT}.

 Logs:   ${COMPOSE[*]} logs -f video
 Update: re-run this script (git pull + rebuild).
────────────────────────────────────────────────────────────
EOF


