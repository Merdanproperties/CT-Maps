#!/usr/bin/env python3
"""
Add pg_trgm extension and GIN trigram indexes on properties for fast ILIKE '%...%'
searches (autocomplete and search by address). Safe to run on existing DBs (IF NOT EXISTS).

Run from repo root:
  python -c "
  import sys; sys.path.insert(0, 'backend')
  from scripts.data_migration.add_trigram_indexes import run
  run()
  "
Or from backend with DB URL:
  DATABASE_URL=postgresql+psycopg2://ctmaps:ctmaps@localhost:5432/ct_properties python scripts/data_migration/add_trigram_indexes.py

For Docker Postgres (from host):
  DATABASE_URL=postgresql+psycopg2://ctmaps:ctmaps@localhost:5432/ct_properties python backend/scripts/data_migration/add_trigram_indexes.py
"""
import os
import sys


def run():
    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        print("Install sqlalchemy and psycopg2; run from backend or set PYTHONPATH.")
        sys.exit(1)

    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://ctmaps:ctmaps@localhost:5432/ct_properties",
    )
    engine = create_engine(database_url)

    # CONCURRENTLY cannot run inside a transaction; use autocommit
    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")

        # 1. Enable trigram extension (required for gin_trgm_ops)
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            print("OK: extension pg_trgm")
        except Exception as e:
            print(f"Skip extension pg_trgm: {e}")
            sys.exit(1)

        # 2. GIN trigram indexes for ILIKE '%...%' on autocomplete/search columns
        indexes = [
            ("idx_properties_address_trgm", "properties", "address"),
            ("idx_properties_municipality_trgm", "properties", "municipality"),
            ("idx_properties_owner_name_trgm", "properties", "owner_name"),
            ("idx_properties_owner_address_trgm", "properties", "owner_address"),
        ]

        for name, table, column in indexes:
            try:
                conn.execute(
                    text(
                        f'CREATE INDEX CONCURRENTLY IF NOT EXISTS "{name}" ON "{table}" USING gin ("{column}" gin_trgm_ops)'
                    )
                )
                print(f"OK: {name}")
            except Exception as e:
                print(f"Skip {name}: {e}")


if __name__ == "__main__":
    run()
