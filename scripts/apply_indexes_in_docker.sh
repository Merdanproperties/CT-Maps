#!/bin/bash
# Apply options + geometry indexes to the Postgres running in Docker.
# Run this once (or after restoring DB) so /api/search/unit-types/options etc. are fast.
# Requires: docker compose up (postgres + backend).
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"
docker compose exec -T -e DATABASE_URL="postgresql+psycopg2://ctmaps:ctmaps@postgres:5432/ct_properties" backend python -c "
import os, sys
sys.path.insert(0, '/app')
os.chdir('/app')
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['DATABASE_URL'])
indexes = [
    ('idx_property_owner_city', 'properties', 'owner_city', 'btree'),
    ('idx_property_owner_state', 'properties', 'owner_state', 'btree'),
    ('idx_property_property_type', 'properties', 'property_type', 'btree'),
    ('idx_property_land_use', 'properties', 'land_use', 'btree'),
    ('idx_property_zoning', 'properties', 'zoning', 'btree'),
    ('idx_property_geometry', 'properties', 'geometry', 'gist'),
]
with engine.connect() as conn:
    for name, table, col, using in indexes:
        try:
            conn.execute(text(f'CREATE INDEX IF NOT EXISTS \"{name}\" ON \"{table}\" USING {using} (\"{col}\")'))
            conn.commit()
            print('OK:', name)
        except Exception as e:
            conn.rollback()
            print('Skip', name, ':', e)
"
echo "Done. Run: docker compose exec postgres psql -U ctmaps -d ct_properties -c 'ANALYZE;' to update stats (optional)."
