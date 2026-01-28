#!/bin/bash

# Restart Backend Script - Can be called by remediation API

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
LOG_DIR="$PROJECT_ROOT/logs"

mkdir -p "$LOG_DIR"

# Kill existing backend
if [ -f "$LOG_DIR/backend.pid" ]; then
    BACKEND_PID=$(cat "$LOG_DIR/backend.pid")
    if ps -p "$BACKEND_PID" > /dev/null 2>&1; then
        kill "$BACKEND_PID" 2>/dev/null || true
        sleep 2
        kill -9 "$BACKEND_PID" 2>/dev/null || true
    fi
    rm -f "$LOG_DIR/backend.pid"
fi

# Kill any process on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Start backend
cd "$BACKEND_DIR"
source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate

nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload >> "$LOG_DIR/backend.log" 2>&1 &
echo $! > "$LOG_DIR/backend.pid"

# Wait a bit and verify (retry once after 2s if slow start)
sleep 3
if curl -s http://localhost:8000/health > /dev/null; then
    echo "Backend restarted successfully"
    exit 0
fi
sleep 2
if curl -s http://localhost:8000/health > /dev/null; then
    echo "Backend restarted successfully"
    exit 0
fi
echo "Backend restart may have failed - check logs: $LOG_DIR/backend.log"
exit 1
