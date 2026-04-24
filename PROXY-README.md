# Proxy Auto-Start System

## What was created:

### 1. `start-proxy.sh`
Robust startup script that:
- Auto-installs uv if missing
- Kills any existing processes on port 8082
- Syncs dependencies before starting
- Waits for health check before declaring success
- Logs everything with timestamps

### 2. `proxy-daemon.sh` (Optional)
Background daemon that:
- Watches proxy every 10 seconds
- Auto-restarts if it crashes
- Runs silently in background

Use: `nohup ./proxy-daemon.sh &`

### 3. LaunchAgent (macOS Auto-Start)
`~/Library/LaunchAgents/com.ragspro.free-claude-code.plist`
- Starts proxy automatically on login
- Keeps it alive (auto-restart if crashes)
- Logs to proxy.log

## Quick Commands:

```bash
# Manual start
~/free-claude-code/start-proxy.sh

# Check status
curl http://localhost:8082/health

# View logs
tail -f ~/free-claude-code/proxy.log

# Stop proxy
lsof -ti:8082 | xargs kill -9
launchctl unload ~/Library/LaunchAgents/com.ragspro.free-claude-code.plist
```

## How ragscode works now:

1. Checks if proxy is running
2. If not, runs `start-proxy.sh` which handles all setup
3. Waits for health check
4. Only then starts Claude

**Result:** Proxy always works, no manual intervention needed.
