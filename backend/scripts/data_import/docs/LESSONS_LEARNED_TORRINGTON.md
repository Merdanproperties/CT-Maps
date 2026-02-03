# Lessons Learned from Torrington Implementation

This document captures ALL critical lessons learned from the Torrington property data import and matching implementation. These lessons must be followed to avoid repeating mistakes.

## CRITICAL: Data Source Priority

### Single Source of Truth
- **`Torrington_CAMA_2025_CLEANED.xlsx`** from "2025 Post Duplicate Clean" folder is the **ONLY** source for CAMA data
- This cleaned Excel file contains the most accurate, verified data
- **NEVER** use raw Excel files or other sources for primary CAMA data
- CSV (`Torrington_CAMA_2025.csv`) is **ONLY** for supplementing fields missing in cleaned Excel
- Every property MUST get its data from the cleaned Excel file - no exceptions, no shortcuts

### Data Source Priority Order
1. **Cleaned Excel** (`Torrington_CAMA_2025_CLEANED.xlsx`) - Use for ALL CAMA fields
2. **CSV** (`Torrington_CAMA_2025.csv`) - Use ONLY for fields missing in cleaned Excel
3. **Existing database value** - Keep ONLY if cleaned Excel doesn't have it

### Common Mistake: Wrong Data Source
- **Mistake**: Using raw Excel or other sources instead of cleaned Excel
- **Example**: "12 MARGERIE ST" showed data from wrong source
- **Prevention**: Always verify data source before updating properties
- **Rule**: If a field exists in cleaned Excel, it MUST come from cleaned Excel

## Spatial Matching Lessons

### CRS Conversion is Critical
- **Always** convert geodatabase geometries from CT State Plane (EPSG:6434) to WGS84 (EPSG:4326) before distance calculations
- Distance calculations will fail catastrophically if coordinate systems don't match (100km+ errors)
- Geodatabase parcels are in EPSG:6434 (CT State Plane)
- Geocoded addresses are in EPSG:4326 (WGS84)
- **Never** calculate distances between different coordinate systems

### Geometry Conversion Process
1. Load geometry from geodatabase (EPSG:6434)
2. Convert to WGS84 using GeoPandas: `geom_series.to_crs('EPSG:4326')`
3. Extract centroid in WGS84
4. Calculate distance using Haversine formula (works with WGS84 coordinates)

### Empty Parcel IDs
- Some properties may have empty or missing parcel_ids
- Generate unique IDs: `EXCEL-{PID}` or EXCEL-ADDR-{hash}`
- Never skip properties due to missing parcel_id
- Always check for duplicates before inserting

### Existing Properties
- **Always** check if property exists before creating new one
- Update existing properties instead of creating duplicates
- Match by parcel_id first, then by address
- If property exists, update it with new data rather than skipping

## Matching Strategy Lessons

### Address Normalization is Essential
- Addresses must be normalized before matching
- Handle abbreviations: ST → STREET, AVE → AVENUE, RD → ROAD, etc.
- Remove unit numbers, apartment numbers
- Uppercase and trim whitespace
- Example: "12 MARGERIE ST" and "12 MARGERIE STREET" should match

### Multiple Matching Strategies
Always use multiple matching strategies in order:
1. **Parcel ID Match** (most reliable when available)
2. **Exact Normalized Address Match** (addresses match exactly after normalization)
3. **Partial Address Match** (street name and number match, handle variations)
4. **Fuzzy Match** (similar addresses, use Levenshtein distance)
5. **Spatial Match** (geocode address, find nearest parcel - requires CRS conversion)

### Matching Priority
- Parcel ID matching is most reliable (if available)
- Address matching requires careful normalization
- Spatial matching is fallback but requires proper CRS handling
- Never assume data is correct without verification

## Import Process Lessons

### Always Check Existing Properties
- Before importing, query database for existing properties
- Build lookup dictionaries (parcel_id → property_id, address → property_id)
- Check if property exists before creating new one
- Update existing properties instead of creating duplicates

### Batch Processing
- Process in batches for performance (500-1000 records per batch)
- Commit periodically to avoid long transactions
- Use bulk_update_mappings for efficiency
- Handle errors gracefully - log and continue

### Edge Cases
- Empty fields: Handle None, empty strings, 'nan' values
- Missing data: Check if field exists before accessing
- Duplicates: Check for unique constraint violations
- Invalid geometry: Validate before inserting
- Missing addresses: Generate or skip appropriately

### Verification
- Always verify imports with comprehensive checks
- Count properties before and after
- Verify data matches source
- Check for missing fields
- Generate reports of unmatched records

## Common Mistakes to Avoid

### 1. Using Wrong Data Source
- **Mistake**: Using raw Excel instead of cleaned Excel
- **Impact**: Incorrect data in database
- **Prevention**: Always use `Torrington_CAMA_2025_CLEANED.xlsx` as primary source
- **Example**: "12 MARGERIE ST" showed data from wrong source

### 2. Skipping CRS Conversion
- **Mistake**: Calculating distances without converting coordinate systems
- **Impact**: 100km+ distance errors, no matches found
- **Prevention**: Always convert geodatabase geometries to WGS84 before distance calculations

### 3. Creating Duplicates
- **Mistake**: Creating new properties instead of updating existing ones
- **Impact**: Duplicate properties, data inconsistency
- **Prevention**: Always check if property exists before creating

### 4. Not Normalizing Addresses
- **Mistake**: Matching addresses without normalization
- **Impact**: Missed matches, incorrect data assignment
- **Prevention**: Always normalize addresses before matching

### 5. Assuming Data is Correct
- **Mistake**: Not verifying data after import
- **Impact**: Incorrect data goes unnoticed
- **Prevention**: Always verify imports with comprehensive checks

### 6. Index-Based Matching
- **Mistake**: Matching by index position instead of actual data
- **Impact**: Wrong data assigned to wrong properties
- **Prevention**: Always match by parcel_id or normalized address

### 7. Skipping Properties
- **Mistake**: Skipping properties that don't match easily
- **Impact**: Missing data, incomplete database
- **Prevention**: Use multiple matching strategies, log unmatched for review

## Best Practices

### Data Import Process
1. Load cleaned Excel file (primary source)
2. Load CSV file (supplement only)
3. Match and combine (cleaned Excel primary, CSV supplement)
4. Build comprehensive lookups (parcel_id, normalized address)
5. Match each database property to cleaned Excel record
6. Update ALL CAMA fields from cleaned Excel
7. Supplement with CSV only for missing fields
8. Verify all updates

### Code Quality
- Always handle exceptions gracefully
- Log errors with context
- Use dry-run mode for testing
- Generate comprehensive reports
- Verify results after import

### Data Integrity
- Never overwrite with empty values
- Preserve existing data if source doesn't have it
- Handle conflicts: cleaned Excel always wins
- Verify data source before updating
- Check for duplicates before inserting

## Verification Checklist

Before considering an import complete:
- [ ] All properties matched to cleaned Excel file
- [ ] All owner_name fields match cleaned Excel "Full Name"
- [ ] All addresses match cleaned Excel "Property Address"
- [ ] All CAMA fields populated from cleaned Excel
- [ ] No properties using wrong data source
- [ ] No duplicate properties created
- [ ] All geometries valid and in WGS84
- [ ] All coordinate systems converted properly
- [ ] Comprehensive verification report generated

## Key Takeaways

1. **Cleaned Excel is SINGLE SOURCE OF TRUTH** - Never use other sources for primary data
2. **CRS conversion is mandatory** - Always convert geometries before distance calculations
3. **Address normalization is essential** - Normalize before matching
4. **Update, don't create duplicates** - Always check existing properties
5. **Verify everything** - Never assume data is correct without verification
6. **Be meticulous** - Every property must get data from cleaned Excel file
7. **No shortcuts** - Follow the process completely, no exceptions

## Automated Verification Requirements

### 0% Mismatch Tolerance Policy

**CRITICAL**: The system enforces a **0% mismatch tolerance** policy. This means:
- **Zero Tolerance**: Any mismatch is a failure
- **Fail-Fast**: Stop import if mismatches found
- **Auto-Fix**: Attempt to fix mismatches automatically
- **Manual Review**: If auto-fix fails, require manual review
- **No Proceed**: Cannot proceed with import if mismatches exist
- **Protection**: Existing towns must remain at 0% mismatch

### Automated Verification System

The automated verification system (`automated_cama_verification.py`) provides:
- **Pre-Import Verification**: Verify all existing towns before importing new town
- **Post-Import Verification**: Verify new town after import
- **Re-Verification**: Re-verify all existing towns to ensure no corruption
- **All Towns Verification**: Verify all towns in database
- **Fail-Fast**: Raises errors if mismatches found (0% tolerance)

### Continuous Monitoring

The monitoring system (`monitor_cama_data.py`) provides:
- **On-Demand Monitoring**: Verify all towns on-demand
- **Scheduled Monitoring**: Can be run via cron job for regular checks
- **Daily Reports**: Generate daily monitoring reports
- **Alerts**: Notify if mismatch rate > 0%

### Standard Import Workflow

The standard import workflow (`import_with_verification.py`) ensures:
1. Pre-import verification (check existing towns - 0% mismatch required)
2. Import new town properties
3. Import/update CAMA data from cleaned Excel
4. Post-import verification (check new town - 0% mismatch required)
5. Re-verify all existing towns (ensure no corruption - 0% mismatch required)
6. Fix any mismatches (0% tolerance - fail if can't fix)
7. Final verification (all towns - 0% mismatch required)
8. Generate report

**All steps must pass** - workflow fails if any step fails.

### Verification Metrics

For each town, verify:
- **Match Rate**: 100% of properties matched to cleaned Excel
- **Data Accuracy**: 100% of CAMA fields match cleaned Excel
- **Completeness**: All required fields populated
- **Data Source**: 100% from cleaned Excel (single source of truth)
- **Mismatch Rate**: 0% (zero tolerance)

### Integration Points

- **Import Scripts**: Must call verification before/after
- **Update Scripts**: Must verify after updates
- **Monitoring**: Runs continuously or on-demand
- **CI/CD**: Can be integrated into deployment pipeline
- **Alerts**: Notify if mismatch rate > 0%

## Future Work

When implementing similar functionality for other towns:
- Follow the same data source priority (cleaned Excel first)
- Use the same matching strategies
- Convert coordinate systems properly
- **ALWAYS use automated verification system** - never skip verification
- **ALWAYS enforce 0% mismatch tolerance** - no exceptions
- **ALWAYS protect existing towns** - verify before and after imports
- Verify all imports using automated system
- Document any new lessons learned
