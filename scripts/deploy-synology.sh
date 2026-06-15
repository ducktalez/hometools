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
#   3. validate that the required library path(s) exist
#   4. docker compose up -d --build
#   5. print the reachable URLs + a health probe
#
# By default only the VIDEO server is deployed. To also run the audio server:
#   ENABLE_AUDIO=1 sudo bash scripts/deploy-synology.sh
# (requires AUDIO_LIBRARY_PATH in .env to point at an existing share).
#
# It never handles passwords. Docker on DSM needs root → run with sudo.

set -euo pipefail

REPO_URL="https://github.com/ducktalez/hometools.git"
ENABLE_AUDIO="${ENABLE_AUDIO:-0}"
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

    warn "Edit .env now and set VIDEO_LIBRARY_PATH to your real share,"
    warn "e.g. /volume1/Serien, then re-run this script."
    warn "(Audio is optional — only needed with ENABLE_AUDIO=1.)"
    die  "Stopping so you can fill in the library path in $PROJECT_DIR/.env"
fi

# ── 3. Validate required library paths ──────────────────────────────────────
# shellcheck disable=SC1091
set -a; . ./.env; set +a

required_vars=(VIDEO_LIBRARY_PATH)
if [ "$ENABLE_AUDIO" = "1" ]; then
    required_vars+=(AUDIO_LIBRARY_PATH)
    log "Audio server ENABLED (ENABLE_AUDIO=1)."
else
    log "Audio server skipped (default). Set ENABLE_AUDIO=1 to include it."
fi

for var in "${required_vars[@]}"; do
    val="${!var:-}"
    case "$val" in
        ""|/path/to/*)
            die "$var is not configured in .env (still a placeholder). Set it to a real directory." ;;
    esac
    [ -d "$val" ] || die "$var=$val does not exist or is not a directory (check the share path)."
done
log "Library path(s) OK."

# ── 4. Build + start ────────────────────────────────────────────────────────
profile_args=()
[ "$ENABLE_AUDIO" = "1" ] && profile_args=(--profile audio)

log "Building and starting containers (first build can take several minutes) …"
"${COMPOSE[@]}" "${profile_args[@]}" up -d --build

# ── 5. Report ───────────────────────────────────────────────────────────────
AUDIO_PORT="${AUDIO_PORT:-8010}"
VIDEO_PORT="${VIDEO_PORT:-8011}"
HOST_IP="$(hostname -i 2>/dev/null | awk '{print $1}')"
[ -n "${HOST_IP:-}" ] || HOST_IP="<NAS-IP>"

log "Containers:"
"${COMPOSE[@]}" ps

log "Probing /health endpoints …"
probe_ports=("$VIDEO_PORT")
[ "$ENABLE_AUDIO" = "1" ] && probe_ports+=("$AUDIO_PORT")
for port in "${probe_ports[@]}"; do
    if curl -fsS "http://127.0.0.1:${port}/health" >/dev/null 2>&1; then
        log "  port ${port}: healthy"
    else
        warn "  port ${port}: not healthy yet (the index may still be building — give it a minute)."
    fi
done

if [ "$ENABLE_AUDIO" = "1" ]; then
    audio_line="   Audio : http://${HOST_IP}:${AUDIO_PORT}
"
    fw_ports="${VIDEO_PORT},${AUDIO_PORT}"
else
    audio_line=""
    fw_ports="${VIDEO_PORT}"
fi

cat <<EOF

────────────────────────────────────────────────────────────
 hometools is up. Open from any device in your LAN:

   Video : http://${HOST_IP}:${VIDEO_PORT}
${audio_line}
 If the DSM firewall blocks it:
   Control Panel → Security → Firewall → allow TCP ${fw_ports}.

 Logs:   ${COMPOSE[*]} logs -f video
 Update: re-run this script (git pull + rebuild).
 Audio:  add audio server with  ENABLE_AUDIO=1 sudo bash scripts/deploy-synology.sh
────────────────────────────────────────────────────────────
EOF


