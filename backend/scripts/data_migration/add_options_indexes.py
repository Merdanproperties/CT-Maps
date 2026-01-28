#!/usr/bin/env python3
"""
Add btree indexes for options endpoints (unit_type, zoning, owner_city, owner_state)
and ensure GiST on geometry. Safe to run on existing DBs (IF NOT EXISTS).

Run from repo root:
  python -c "
  import sys; sys.path.insert(0, 'backend')
  from scripts.data_migration.add_options_indexes import run
  run()
  "
Or from backend with DB URL:
  DATABASE_URL=postgresql+psycopg2://ctmaps:ctmaps@localhost:5432/ct_properties python scripts/data_migration/add_options_indexes.py
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

    indexes = [
        ("idx_property_owner_city", "properties", "owner_city", "btree"),
        ("idx_property_owner_state", "properties", "owner_state", "btree"),
        ("idx_property_property_type", "properties", "property_type", "btree"),
        ("idx_property_land_use", "properties", "land_use", "btree"),
        # zoning and geometry may already exist from models
        ("idx_property_zoning", "properties", "zoning", "btree"),
        ("idx_property_geometry", "properties", "geometry", "gist"),
    ]

    with engine.connect() as conn:
        for name, table, column, using in indexes:
            try:
                conn.execute(
                    text(
                        f'CREATE INDEX IF NOT EXISTS "{name}" ON "{table}" USING {using} ("{column}")'
                    )
                )
                conn.commit()
                print(f"OK: {name}")
            except Exception as e:
                print(f"Skip {name}: {e}")
                conn.rollback()


if __name__ == "__main__":
    run()
