#!/bin/bash
# Apply pg_trgm extension and trigram indexes so address/town/owner search and
# autocomplete use GIN indexes (faster ILIKE '%...%').
# Run once per database (or after restore). Requires: docker compose up (postgres + backend).
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "1. Enabling pg_trgm extension..."
docker compose exec -T postgres psql -U ctmaps -d ct_properties -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

echo "2. Creating trigram indexes (this may take a minute on large tables)..."
docker compose exec -T -e DATABASE_URL="postgresql+psycopg2://ctmaps:ctmaps@postgres:5432/ct_properties" backend python -c "
import os, sys
sys.path.insert(0, '/app')
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    conn.execution_options(isolation_level='AUTOCOMMIT')
    for name, table, column in [
        ('idx_properties_address_trgm', 'properties', 'address'),
        ('idx_properties_municipality_trgm', 'properties', 'municipality'),
        ('idx_properties_owner_name_trgm', 'properties', 'owner_name'),
        ('idx_properties_owner_address_trgm', 'properties', 'owner_address'),
    ]:
        try:
            conn.execute(text(f'CREATE INDEX CONCURRENTLY IF NOT EXISTS \"{name}\" ON \"{table}\" USING gin (\"{column}\" gin_trgm_ops)'))
            print('OK:', name)
        except Exception as e:
            print('Skip', name, ':', e)
"

echo "3. Updating table stats (optional but recommended)..."
docker compose exec -T postgres psql -U ctmaps -d ct_properties -c "ANALYZE properties;" 2>/dev/null || true

echo "Done. Trigram indexes are in place for address/town/owner search."
echo ""
echo "To verify indexes exist:"
echo "  docker compose exec postgres psql -U ctmaps -d ct_properties -c \"SELECT indexname FROM pg_indexes WHERE tablename = 'properties' AND indexname LIKE '%trgm%';\""
