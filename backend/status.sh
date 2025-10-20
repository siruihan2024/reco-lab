#!/usr/bin/env bash

PID_FILE="/data/xbx/KDD/server.pid"
LOG_FILE="/data/xbx/KDD/server.log"

echo "=== Server Status ==="

if [ ! -f "$PID_FILE" ]; then
    echo "❌ Server not running (no PID file)"
    exit 1
fi

PID=$(cat "$PID_FILE")

if ps -p "$PID" > /dev/null 2>&1; then
    echo "✅ Server is running"
    echo "   PID: $PID"
    echo "   Port: $(ss -ltnp | grep "$PID" | awk '{print $4}' | grep -o '[0-9]*$' | head -1)"
    echo "   Memory: $(ps -p "$PID" -o rss= | awk '{printf "%.1f MB\n", $1/1024}')"
    echo "   Uptime: $(ps -p "$PID" -o etime= | xargs)"
    echo ""
    echo "Recent logs (last 10 lines):"
    tail -n 10 "$LOG_FILE"
else
    echo "❌ Server not running (stale PID file)"
    rm -f "$PID_FILE"
    exit 1
fi