-- Trigram indexes for fast ILIKE '%...%' (autocomplete + search).
-- Run once per database. Safe to re-run (IF NOT EXISTS).
--
-- IMPORTANT: Run the extension (step 1) FIRST, by itself. Then run step 2.
-- If you get "operator class gin_trgm_ops does not exist", the extension
-- was not enabled—run step 1 as a superuser (e.g. user "postgres" in Docker).

-- 1. Enable extension — RUN THIS FIRST (requires superuser in PostgreSQL)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 2. GIN trigram indexes (CONCURRENTLY = no table lock; run each separately if needed)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_properties_address_trgm
  ON properties USING gin (address gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_properties_municipality_trgm
  ON properties USING gin (municipality gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_properties_owner_name_trgm
  ON properties USING gin (owner_name gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_properties_owner_address_trgm
  ON properties USING gin (owner_address gin_trgm_ops);
