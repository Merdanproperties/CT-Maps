#!/bin/bash

# Process Watchdog - Automatically restarts services if they crash
# This script monitors backend and frontend processes and restarts them if they die

BACKEND_DIR="$(cd "$(dirname "$0")/../backend" && pwd)"
FRONTEND_DIR="$(cd "$(dirname "$0")/../frontend" && pwd)"
LOG_DIR="$(cd "$(dirname "$0")/../logs" && pwd)"
mkdir -p "$LOG_DIR"

BACKEND_PID_FILE="$LOG_DIR/backend.pid"
FRONTEND_PID_FILE="$LOG_DIR/frontend.pid"
WATCHDOG_LOG="$LOG_DIR/watchdog.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$WATCHDOG_LOG"
}

check_process() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            return 1
        fi
    else
        return 1
    fi
}

start_backend() {
    log "Starting backend server..."
    cd "$BACKEND_DIR"
    source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate
    nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload > "$LOG_DIR/backend.log" 2>&1 &
    echo $! > "$BACKEND_PID_FILE"
    log "Backend started with PID $(cat $BACKEND_PID_FILE)"
    sleep 3
    # Verify it's actually running
    if curl -s http://localhost:8000/health > /dev/null; then
        log "Backend health check passed"
        return 0
    else
        log "Backend health check failed"
        return 1
    fi
}

start_frontend() {
    log "Starting frontend server..."
    cd "$FRONTEND_DIR"
    nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
    log "Frontend started with PID $(cat $FRONTEND_PID_FILE)"
    sleep 5
    # Verify it's actually running
    if curl -s http://localhost:3000 > /dev/null; then
        log "Frontend health check passed"
        return 0
    else
        log "Frontend health check failed (may still be starting)"
        return 0  # Frontend takes longer to start
    fi
}

stop_backend() {
    if [ -f "$BACKEND_PID_FILE" ]; then
        local pid=$(cat "$BACKEND_PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            log "Stopping backend (PID: $pid)"
            kill "$pid" 2>/dev/null
            sleep 2
            kill -9 "$pid" 2>/dev/null
        fi
        rm -f "$BACKEND_PID_FILE"
    fi
}

stop_frontend() {
    if [ -f "$FRONTEND_PID_FILE" ]; then
        local pid=$(cat "$FRONTEND_PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            log "Stopping frontend (PID: $pid)"
            kill "$pid" 2>/dev/null
            sleep 2
            kill -9 "$pid" 2>/dev/null
        fi
        rm -f "$FRONTEND_PID_FILE"
    fi
}

restart_backend() {
    log "Backend process not running, restarting..."
    stop_backend
    sleep 2
    start_backend
}

restart_frontend() {
    log "Frontend process not running, restarting..."
    stop_frontend
    sleep 2
    start_frontend
}

# Initial startup
log "=== Watchdog starting ==="
log "Backend directory: $BACKEND_DIR"
log "Frontend directory: $FRONTEND_DIR"
log "Log directory: $LOG_DIR"

# Start services if not running
if ! check_process "$BACKEND_PID_FILE"; then
    start_backend
fi

if ! check_process "$FRONTEND_PID_FILE"; then
    start_frontend
fi

# Main monitoring loop
log "Starting monitoring loop (checking every 10 seconds)..."
while true; do
    # Check backend
    if ! check_process "$BACKEND_PID_FILE"; then
        restart_backend
    else
        # Verify backend is actually responding
        if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
            log "Backend not responding to health check, restarting..."
            restart_backend
        fi
    fi
    
    # Check frontend
    if ! check_process "$FRONTEND_PID_FILE"; then
        restart_frontend
    fi
    
    sleep 10
done
