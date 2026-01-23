#!/bin/bash

# Stop All Services - Gracefully stops all application services

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"

echo "🛑 Stopping CT Maps Application Services..."
echo ""

# Stop backend
if [ -f "$LOG_DIR/backend.pid" ]; then
    BACKEND_PID=$(cat "$LOG_DIR/backend.pid")
    if ps -p "$BACKEND_PID" > /dev/null 2>&1; then
        echo "Stopping backend (PID: $BACKEND_PID)..."
        kill "$BACKEND_PID" 2>/dev/null || true
        sleep 2
        kill -9 "$BACKEND_PID" 2>/dev/null || true
        echo "✅ Backend stopped"
    fi
    rm -f "$LOG_DIR/backend.pid"
fi

# Stop frontend
if [ -f "$LOG_DIR/frontend.pid" ]; then
    FRONTEND_PID=$(cat "$LOG_DIR/frontend.pid")
    if ps -p "$FRONTEND_PID" > /dev/null 2>&1; then
        echo "Stopping frontend (PID: $FRONTEND_PID)..."
        kill "$FRONTEND_PID" 2>/dev/null || true
        sleep 2
        kill -9 "$FRONTEND_PID" 2>/dev/null || true
        echo "✅ Frontend stopped"
    fi
    rm -f "$LOG_DIR/frontend.pid"
fi

# Kill any remaining processes on ports
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "Killing remaining processes on port 8000..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
fi

if lsof -ti:3000 > /dev/null 2>&1; then
    echo "Killing remaining processes on port 3000..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
fi

echo ""
echo "✅ All services stopped"
