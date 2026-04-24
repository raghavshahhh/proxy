#!/bin/bash
# Proxy Daemon - Auto-restarts on crashes
# Run this in background to keep proxy always alive

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDFILE="${SCRIPT_DIR}/.proxy.pid"
HEALTH_URL="http://localhost:8082/health"
RESTART_DELAY=5

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [DAEMON] $1"; }

while true; do
    if ! curl -sf "$HEALTH_URL" >/dev/null 2>&1; then
        log "Proxy not running, starting..."
        cd "$SCRIPT_DIR"
        export PATH="$HOME/.local/bin:$PATH"

        # Sync and start
        uv sync --quiet 2>/dev/null || true
        nohup uv run uvicorn server:app --host 0.0.0.0 --port 8082 --timeout-graceful-shutdown 5 >> proxy.log 2>&1 &
        echo $! > "$PIDFILE"

        # Wait for startup
        sleep 3
        if curl -sf "$HEALTH_URL" >/dev/null 2>&1; then
            log "Proxy started successfully"
        else
            log "Proxy failed to start, retrying in ${RESTART_DELAY}s..."
            sleep "$RESTART_DELAY"
        fi
    fi

    # Check every 10 seconds
    sleep 10
done
