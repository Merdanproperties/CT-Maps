-- Useful SQL Queries for TablePlus
-- Copy and paste these into the SQL tab in TablePlus

-- 1. See total count and statistics
SELECT 
    COUNT(*) as total_properties,
    COUNT(DISTINCT municipality) as total_towns,
    COUNT(DISTINCT property_type) as property_types,
    COUNT(*) FILTER (WHERE is_vacant = 1) as vacant_properties,
    COUNT(*) FILTER (WHERE is_absentee = 1) as absentee_owners
FROM properties;

-- 2. Properties by municipality (top 20)
SELECT 
    municipality,
    COUNT(*) as property_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM properties), 2) as percentage
FROM properties
WHERE municipality IS NOT NULL
GROUP BY municipality
ORDER BY property_count DESC
LIMIT 20;

-- 3. Property types breakdown
SELECT 
    property_type,
    COUNT(*) as count,
    ROUND(AVG(lot_size_sqft), 0) as avg_lot_size
FROM properties
WHERE property_type IS NOT NULL
GROUP BY property_type
ORDER BY count DESC
LIMIT 15;

-- 4. Sample properties with details
SELECT 
    parcel_id,
    address,
    municipality,
    property_type,
    ROUND(lot_size_sqft, 0) as lot_size_sqft,
    CASE WHEN is_vacant = 1 THEN 'Yes' ELSE 'No' END as vacant,
    CASE WHEN is_absentee = 1 THEN 'Yes' ELSE 'No' END as absentee_owner
FROM properties
WHERE address IS NOT NULL
ORDER BY municipality, address
LIMIT 50;

-- 5. Vacant properties
SELECT 
    parcel_id,
    address,
    municipality,
    property_type,
    ROUND(lot_size_sqft, 0) as lot_size_sqft
FROM properties
WHERE is_vacant = 1
ORDER BY municipality, address
LIMIT 50;

-- 6. Absentee owners
SELECT 
    parcel_id,
    address,
    municipality,
    property_type
FROM properties
WHERE is_absentee = 1
ORDER BY municipality, address
LIMIT 50;

-- 7. Properties by lot size (largest)
SELECT 
    parcel_id,
    address,
    municipality,
    property_type,
    ROUND(lot_size_sqft, 0) as lot_size_sqft,
    ROUND(lot_size_sqft / 43560, 2) as acres
FROM properties
WHERE lot_size_sqft IS NOT NULL AND lot_size_sqft > 0
ORDER BY lot_size_sqft DESC
LIMIT 20;

-- 8. Properties in a specific town (case-insensitive - change 'Bridgeport' to any town)
SELECT 
    parcel_id,
    address,
    property_type,
    ROUND(lot_size_sqft, 0) as lot_size_sqft
FROM properties
WHERE LOWER(municipality) = LOWER('Bridgeport')  -- Case-insensitive match
ORDER BY address
LIMIT 100;

-- 9. Search by address pattern
SELECT 
    parcel_id,
    address,
    municipality,
    property_type
FROM properties
WHERE address ILIKE '%BATTERY%'  -- Change this to search for any address
ORDER BY address
LIMIT 50;

-- 10. Properties with CAMA links (for future data joining)
SELECT 
    parcel_id,
    address,
    municipality,
    additional_data->>'cama_link' as cama_link
FROM properties
WHERE additional_data IS NOT NULL
  AND additional_data->>'cama_link' IS NOT NULL
LIMIT 20;

-- 11. DELETE all towns except Bridgeport, Middletown, and Torrington
-- WARNING: This will permanently delete data! Use with caution.
-- First, delete related records from child tables
DELETE FROM property_comments
WHERE property_id IN (
    SELECT id FROM properties 
    WHERE municipality NOT IN ('Bridgeport', 'Middletown', 'Torrington')
       OR municipality IS NULL
);

DELETE FROM sales
WHERE property_id IN (
    SELECT id FROM properties 
    WHERE municipality NOT IN ('Bridgeport', 'Middletown', 'Torrington')
       OR municipality IS NULL
);

-- Then delete the properties themselves
DELETE FROM properties
WHERE municipality NOT IN ('Bridgeport', 'Middletown', 'Torrington')
   OR municipality IS NULL;

-- 12. Town import statistics and coverage analysis (case-sensitive - shows duplicates)
SELECT 
    municipality as town,
    COUNT(*) as properties_imported,
    COUNT(*) FILTER (WHERE address IS NOT NULL AND address != '') as properties_with_address,
    ROUND(100.0 * COUNT(*) FILTER (WHERE address IS NOT NULL AND address != '') / NULLIF(COUNT(*), 0), 2) as address_coverage_pct,
    COUNT(*) FILTER (WHERE owner_name IS NOT NULL AND owner_name != '') as properties_with_owner,
    COUNT(*) FILTER (WHERE assessed_value IS NOT NULL) as properties_with_assessment,
    MIN(last_updated) as first_import,
    MAX(last_updated) as last_import
FROM properties
WHERE municipality IS NOT NULL
GROUP BY municipality
ORDER BY properties_imported DESC;

-- 12b. Town import statistics (case-insensitive - combines duplicates like "FAIRFIELD" and "Fairfield")
SELECT 
    INITCAP(LOWER(municipality)) as town,  -- Normalize to title case for display
    COUNT(*) as properties_imported,
    COUNT(*) FILTER (WHERE address IS NOT NULL AND address != '') as properties_with_address,
    ROUND(100.0 * COUNT(*) FILTER (WHERE address IS NOT NULL AND address != '') / NULLIF(COUNT(*), 0), 2) as address_coverage_pct,
    COUNT(*) FILTER (WHERE owner_name IS NOT NULL AND owner_name != '') as properties_with_owner,
    COUNT(*) FILTER (WHERE assessed_value IS NOT NULL) as properties_with_assessment,
    MIN(last_updated) as first_import,
    MAX(last_updated) as last_import
FROM properties
WHERE municipality IS NOT NULL
GROUP BY LOWER(municipality)  -- Group by lowercase to combine case variations
ORDER BY properties_imported DESC;

-- 13. Normalize all municipality names to title case (fixes case sensitivity issues)
-- WARNING: This will update all municipality names. Review first with query below.
-- First, preview what will change:
SELECT 
    municipality as current_name,
    INITCAP(LOWER(municipality)) as normalized_name,
    COUNT(*) as property_count
FROM properties
WHERE municipality IS NOT NULL
  AND municipality != INITCAP(LOWER(municipality))  -- Only show ones that will change
GROUP BY municipality
ORDER BY property_count DESC;

-- Then run this to actually normalize (uncomment to execute):
-- UPDATE properties
-- SET municipality = INITCAP(LOWER(municipality))
-- WHERE municipality IS NOT NULL
--   AND municipality != INITCAP(LOWER(municipality));

-- =============================================================================
-- 14. IMPORT INTEGRITY: No duplicates (run after imports to verify correctness)
--    Like Torrington had: same town imported twice with different parcel_id
--    formats (geodatabase IDs vs address-hash). These queries should return
--    zero rows when imports are correct.
-- =============================================================================

-- 14a. Duplicate (parcel_id, municipality) — should be 0 rows.
--      DB has unique constraint; this catches any legacy or constraint bypass.
SELECT
    parcel_id,
    municipality,
    COUNT(*) AS row_count
FROM properties
GROUP BY parcel_id, municipality
HAVING COUNT(*) > 1
ORDER BY municipality, parcel_id;

-- 14b. Same address + municipality with different parcel_ids — "Torrington-style"
--      Same town, same normalized address, but multiple rows (different parcel_id).
--      Should be 0 rows. If any rows appear, one import may have duplicated
--      the same address with a different key (e.g. geodatabase vs geocode flow).
SELECT
    LOWER(TRIM(municipality))   AS municipality_norm,
    LOWER(TRIM(address))        AS address_norm,
    COUNT(DISTINCT parcel_id)    AS distinct_parcel_ids,
    COUNT(*)                    AS row_count,
    STRING_AGG(parcel_id, ' | ' ORDER BY parcel_id) AS parcel_ids
FROM properties
WHERE address IS NOT NULL AND TRIM(address) != ''
GROUP BY LOWER(TRIM(municipality)), LOWER(TRIM(address))
HAVING COUNT(*) > 1
ORDER BY municipality_norm, address_norm;

-- 14c. One-line integrity summary (run after 14a and 14b).
--      duplicate_keys = 0 and duplicate_addresses = 0 means imports are clean.
SELECT
    (SELECT COUNT(*) FROM (
        SELECT parcel_id, municipality
        FROM properties
        GROUP BY parcel_id, municipality
        HAVING COUNT(*) > 1
    ) t) AS duplicate_parcel_municipality_pairs,
    (SELECT COUNT(*) FROM (
        SELECT LOWER(TRIM(municipality)), LOWER(TRIM(address))
        FROM properties
        WHERE address IS NOT NULL AND TRIM(address) != ''
        GROUP BY LOWER(TRIM(municipality)), LOWER(TRIM(address))
        HAVING COUNT(*) > 1
    ) u) AS duplicate_address_per_town_groups;
