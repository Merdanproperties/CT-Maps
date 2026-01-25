#!/bin/bash
# Quick start script for the backend

cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Skip validation for now (script has path issues)
# Can be re-enabled once validation script is fixed

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
