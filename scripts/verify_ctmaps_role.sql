-- Run this to verify the ctmaps role exists and has access (connect to ct_properties as any user).

-- 1. Does the ctmaps role exist?
SELECT rolname AS role_name,
       rolcanlogin AS can_login,
       rolcreatedb AS can_create_db
FROM pg_roles
WHERE rolname = 'ctmaps';

-- 2. Schema privileges for ctmaps on public (PostgreSQL: use has_schema_privilege)
SELECT 'public' AS schema_name,
       has_schema_privilege('ctmaps', 'public', 'USAGE')   AS usage,
       has_schema_privilege('ctmaps', 'public', 'CREATE')  AS create_priv;

-- 3. Table privileges (sample: first 5 tables ctmaps can access)
SELECT table_schema, table_name, privilege_type
FROM information_schema.table_privileges
WHERE grantee = 'ctmaps'
ORDER BY table_schema, table_name
LIMIT 20;

-- 4. PostGIS extension (should exist)
SELECT extname, extversion
FROM pg_extension
WHERE extname = 'postgis';
