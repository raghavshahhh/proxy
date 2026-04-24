#!/bin/bash
# Robust Proxy Startup Script
# Handles: uv install, port conflicts, auto-restart, health checks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROXY_LOG="${SCRIPT_DIR}/proxy.log"
PIDFILE="${SCRIPT_DIR}/.proxy.pid"
PORT=8082
HEALTH_URL="http://localhost:${PORT}/health"
MAX_WAIT=30

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date +%H:%M:%S)] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date +%H:%M:%S)] ERROR:${NC} $1"; }

# Ensure uv is installed
ensure_uv() {
    if ! command -v uv &> /dev/null; then
        log "uv not found, installing..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    fi
    # Always ensure PATH has uv
    export PATH="$HOME/.local/bin:$PATH"
}

# Kill any existing proxy processes
kill_existing() {
    # Try graceful shutdown first
    if [ -f "$PIDFILE" ]; then
        local pid=$(cat "$PIDFILE" 2>/dev/null)
        if kill -0 "$pid" 2>/dev/null; then
            warn "Stopping existing proxy (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 2
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$PIDFILE"
    fi

    # Kill any remaining uvicorn on port 8082
    local pids=$(lsof -ti:$PORT 2>/dev/null || netstat -van | grep ".$PORT " | awk '{print $9}' | cut -d'.' -f2 | sort -u || true)
    if [ -n "$pids" ]; then
        warn "Killing leftover processes on port $PORT..."
        echo "$pids" | xargs -I {} kill -9 {} 2>/dev/null || true
        sleep 1
    fi
}

# Wait for health check
wait_for_health() {
    local attempts=0
    log "Waiting for proxy to be ready..."
    while [ $attempts -lt $MAX_WAIT ]; do
        if curl -sf "$HEALTH_URL" &>/dev/null; then
            log "Proxy is healthy!"
            return 0
        fi
        attempts=$((attempts + 1))
        sleep 1
    done
    error "Proxy failed to start within ${MAX_WAIT}s"
    return 1
}

# Start the proxy
start_proxy() {
    cd "$SCRIPT_DIR"

    # Sync dependencies
    log "Syncing dependencies..."
    uv sync --quiet

    # Start server
    log "Starting proxy on port $PORT..."
    nohup uv run uvicorn server:app --host 0.0.0.0 --port $PORT --timeout-graceful-shutdown 5 >> "$PROXY_LOG" 2>&1 &
    echo $! > "$PIDFILE"

    # Wait for it to be ready
    if ! wait_for_health; then
        error "Failed to start proxy. Check logs: $PROXY_LOG"
        tail -20 "$PROXY_LOG"
        return 1
    fi
}

# Check if already running
check_running() {
    if curl -sf "$HEALTH_URL" &>/dev/null; then
        log "Proxy is already running and healthy"
        return 0
    fi
    return 1
}

# Main
main() {
    log "=== Proxy Startup ==="

    ensure_uv

    if check_running; then
        exit 0
    fi

    kill_existing
    start_proxy

    log "=== Proxy Ready ==="
    echo "$(date): Proxy started" >> "${SCRIPT_DIR}/.proxy.history"
}

main "$@"
