#!/usr/bin/env bash

PID_FILE="/data/xbx/KDD/server.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "❌ PID file not found: $PID_FILE"
    echo "Server may not be running or was started manually."
    echo ""
    echo "Try manual cleanup:"
    echo "  ps aux | grep 'uvicorn app.server:app'"
    echo "  pkill -f 'uvicorn app.server:app'"
    exit 1
fi

PID=$(cat "$PID_FILE")

if ps -p "$PID" > /dev/null 2>&1; then
    echo "Stopping server (PID: $PID)..."
    kill "$PID"
    
    # 等待进程结束（最多5秒）
    for i in {1..5}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            echo "✅ Server stopped successfully"
            rm -f "$PID_FILE"
            exit 0
        fi
        sleep 1
    done
    
    # 如果还没停止，强制杀死
    echo "⚠️  Server not responding, forcing kill..."
    kill -9 "$PID"
    rm -f "$PID_FILE"
    echo "✅ Server force-killed"
else
    echo "⚠️  Process $PID not found (may have already stopped)"
    rm -f "$PID_FILE"
fi