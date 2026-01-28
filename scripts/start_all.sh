#!/bin/bash

# Start All Services - Orchestrates startup of all application services
# This script ensures proper startup order and health checks

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
LOG_DIR="$PROJECT_ROOT/logs"

mkdir -p "$LOG_DIR"

echo "🚀 Starting CT Maps Application Services..."
echo ""

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 0
    else
        return 1
    fi
}

# Function to wait for service to be healthy
wait_for_health() {
    local url=$1
    local max_attempts=30
    local attempt=0
    
    echo "Waiting for $url to be healthy..."
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            echo "✅ Service is healthy!"
            return 0
        fi
        attempt=$((attempt + 1))
        echo "  Attempt $attempt/$max_attempts..."
        sleep 1
    done
    
    echo "❌ Service failed to become healthy"
    return 1
}

# Check and kill processes on ports if needed
if check_port 8000; then
    echo "⚠️  Port 8000 is in use. Killing existing process..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

if check_port 3000; then
    echo "⚠️  Port 3000 is in use. Killing existing process..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Start Backend
echo ""
echo "📦 Starting Backend Server..."
cd "$BACKEND_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Install dependencies if needed
if [ ! -f ".deps_installed" ]; then
    echo "Installing backend dependencies..."
    pip install -r requirements.txt
    touch .deps_installed
fi

# Start backend (nohup so it keeps running after terminal close)
echo "Starting uvicorn server..."
nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload >> "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"
echo $BACKEND_PID > "$LOG_DIR/backend.pid"

# Wait for backend to be healthy (retry once after 2s if slow start)
if wait_for_health "http://localhost:8000/health"; then
    echo "✅ Backend is ready!"
else
    echo "Backend not ready yet, retrying in 2s..."
    sleep 2
    if wait_for_health "http://localhost:8000/health"; then
        echo "✅ Backend is ready!"
    else
        echo "❌ Backend failed to start. Check logs: $LOG_DIR/backend.log"
        exit 1
    fi
fi

# Start Frontend
echo ""
echo "🎨 Starting Frontend Server..."
cd "$FRONTEND_DIR"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Start frontend (nohup so it keeps running after terminal close)
echo "Starting Vite dev server..."
nohup npm run dev >> "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"
echo $FRONTEND_PID > "$LOG_DIR/frontend.pid"

# Wait for frontend to be ready
sleep 5
if wait_for_health "http://localhost:3000"; then
    echo "✅ Frontend is ready!"
else
    echo "⚠️  Frontend may still be starting (this is normal)"
fi

echo ""
echo "🎉 All services started successfully!"
echo ""
echo "📍 Services:"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "📋 Logs:"
echo "   Backend:  $LOG_DIR/backend.log"
echo "   Frontend: $LOG_DIR/frontend.log"
echo ""
echo "🛑 To stop all services, run: ./scripts/stop_all.sh"
echo ""

# Keep script running
wait
