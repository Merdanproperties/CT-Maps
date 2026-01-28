#!/usr/bin/env bash
# Copy local Postgres ct_properties database into Docker Postgres.
# Run this whenever you update your local DB and want Docker to use the same data.
# Requires: Docker Postgres running (docker compose up -d postgres), pg_dump and pg_restore on host.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_ENV="$PROJECT_ROOT/backend/.env"
DUMP_FILE="${DUMP_FILE:-$PROJECT_ROOT/.pg_sync_dump}"

# Ensure pg_dump/pg_restore are on PATH (Postgres.app, Homebrew)
if ! command -v pg_dump >/dev/null 2>&1; then
  for dir in /Applications/Postgres.app/Contents/Versions/*/bin /opt/homebrew/bin /usr/local/bin; do
    [ -x "$dir/pg_dump" ] && [ -x "$dir/pg_restore" ] && export PATH="$dir:$PATH" && break
  done
fi
if ! command -v pg_dump >/dev/null 2>&1; then
  echo "pg_dump not found. Install PostgreSQL client tools (Postgres.app, Homebrew, or add to PATH)."
  exit 1
fi

# Local DB URL: from env, or from backend/.env, or default
if [ -n "$LOCAL_DATABASE_URL" ]; then
  LOCAL_URL="$LOCAL_DATABASE_URL"
elif [ -f "$BACKEND_ENV" ]; then
  LOCAL_URL=$(grep -E '^DATABASE_URL=' "$BACKEND_ENV" | cut -d= -f2- | tr -d '"' | tr -d "'")
fi
LOCAL_URL="${LOCAL_URL:-postgresql://localhost:5432/ct_properties}"

# pg_dump expects postgresql:// (no +psycopg2)
LOCAL_URL="${LOCAL_URL//+psycopg2/}"

echo "Copying local Postgres → Docker Postgres"
echo "  Local:  $LOCAL_URL"
echo "  Docker: postgres (ctmaps@postgres:5432/ct_properties)"
echo ""

# Dump from local FIRST (so we don't dump from Docker if it's already on 5432)
# Use plain SQL (-Fp) so dump from Postgres 18 works when restoring into Postgres 15
echo "Dumping local database (plain SQL for version compatibility)..."
if ! pg_dump "$LOCAL_URL" -Fp --no-owner --clean -f "$DUMP_FILE"; then
  echo "Dump failed. If Docker is already running, it may be using port 5432."
  echo "Stop Docker Postgres first: docker compose stop postgres"
  echo "Then ensure your local Postgres is on 5432 and run this script again."
  exit 1
fi

# Now ensure Docker Postgres is running
cd "$PROJECT_ROOT"
if ! docker compose ps postgres 2>/dev/null | grep -q "Up"; then
  echo "Starting Docker Postgres..."
  docker compose up -d postgres
  echo "Waiting for Postgres to be ready..."
  for i in {1..30}; do
    if docker compose exec -T postgres pg_isready -U ctmaps -d ct_properties 2>/dev/null; then
      break
    fi
    sleep 1
  done
fi

echo "Copying dump into container and restoring..."
CONTAINER=$(docker compose ps -q postgres)
docker cp "$DUMP_FILE" "$CONTAINER:/tmp/ct_sync.sql"
docker compose exec -T postgres psql -U ctmaps -d ct_properties -v ON_ERROR_STOP=0 -f /tmp/ct_sync.sql >/dev/null 2>&1 || true
docker compose exec -T postgres rm -f /tmp/ct_sync.sql

rm -f "$DUMP_FILE"
COUNT=$(docker compose exec -T postgres psql -U ctmaps -d ct_properties -t -c "SELECT COUNT(*) FROM properties;" 2>/dev/null | tr -d ' ')
echo "Done. Properties in Docker: ${COUNT:-?}"
echo "Start the full stack with: docker compose up -d"
echo "  (Or already running: backend/frontend will use the updated data.)"
echo ""
echo "If count is 0: ensure backend/.env DATABASE_URL points at the DB that has your data (e.g. same host/port as in your DB client)."
