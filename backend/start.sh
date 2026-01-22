#!/bin/bash
# Quick start script for the backend

cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Validate code before starting (catch duplicate keyword arguments)
echo "🔍 Validating response constructors..."
if ! python scripts/validate_response_constructors.py; then
    echo "❌ Validation failed! Fix duplicate keyword arguments before starting."
    exit 1
fi
echo "✅ Validation passed!"

# Set up PostgreSQL path
export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"

# Set database URL
export DATABASE_URL="postgresql://localhost:5432/ct_properties"

# Start the server
echo "🚀 Starting CT Property Search Backend..."
echo "📍 API will be available at: http://localhost:8000"
echo "📚 API docs at: http://localhost:8000/docs"
echo ""
uvicorn main:app --reload --host 0.0.0.0 --port 8000
