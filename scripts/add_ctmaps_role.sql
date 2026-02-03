-- Run this once in your local Postgres 18 while connected to database ct_properties as a superuser.
-- This creates the ctmaps role so the import script can connect.

-- 1. Create ctmaps role (if it doesn't exist)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ctmaps') THEN
    CREATE ROLE ctmaps WITH LOGIN PASSWORD 'ctmaps';
  END IF;
END
$$;

-- 2. Give ctmaps full access to this database
GRANT ALL ON SCHEMA public TO ctmaps;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ctmaps;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ctmaps;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ctmaps;

-- 3. PostGIS (needed for geometry)
CREATE EXTENSION IF NOT EXISTS postgis;
