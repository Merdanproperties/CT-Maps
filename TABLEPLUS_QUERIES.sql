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

-- 8. Properties in a specific town (change 'Bridgeport' to any town)
SELECT 
    parcel_id,
    address,
    property_type,
    ROUND(lot_size_sqft, 0) as lot_size_sqft
FROM properties
WHERE municipality = 'Bridgeport'
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
