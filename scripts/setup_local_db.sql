-- Run this ONCE in your LOCAL Postgres (e.g. in DBeaver as a superuser) so imports can write to local first.
-- Then: run imports → data goes to local; when good, run: bash scripts/sync_local_db_to_docker.sh

-- ---------------------------------------------------------------------------
-- Option A: Fresh setup (no ct_properties yet)
-- ---------------------------------------------------------------------------
-- Create role and database (adjust if your superuser is not 'postgres')
-- CREATE ROLE ctmaps WITH LOGIN PASSWORD 'ctmaps';
-- CREATE DATABASE ct_properties OWNER ctmaps;
-- Then connect to ct_properties and run the GRANT + PostGIS lines below.

-- ---------------------------------------------------------------------------
-- Option B: ct_properties already exists (you've been using it as postgres/your user)
-- Run this so the import script (which connects as ctmaps) can write to it.
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ctmaps') THEN
    CREATE ROLE ctmaps WITH LOGIN PASSWORD 'ctmaps';
  END IF;
END
$$;
-- Grant ctmaps full access to existing ct_properties (run while connected to ct_properties)
GRANT ALL ON SCHEMA public TO ctmaps;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ctmaps;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ctmaps;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ctmaps;

-- Enable PostGIS (required for properties.geometry). Install PostGIS in local Postgres if not already.
CREATE EXTENSION IF NOT EXISTS postgis;
