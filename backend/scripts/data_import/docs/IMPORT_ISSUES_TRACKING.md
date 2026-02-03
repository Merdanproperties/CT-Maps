# Import Issues Tracking - 138 Towns Batch Import

## Critical Issues Identified

### 1. Bulk Insert Failures (ALL TOWNS)
**Problem**: Every bulk insert fails and falls back to individual inserts, but then reports "Imported: 0 properties"

**Root Cause**: 
- Bulk inserts are failing (likely due to geometry constraints or data format issues)
- Individual insert fallback is running but not properly committing properties
- Error handling is catching errors but not logging them properly

**Status**: FIXED - Improved error handling and commit logic

**Towns Affected**: ALL towns with properties to import

### 2. CSV Format Variations

#### Bethel CSV Format
**Problem**: CSV uses `ADRNO`, `ADRADD`, `ADRSTR` instead of `Property Address`
**Error**: `Property Address column not found in raw CSV`
**Status**: FIXED - Added support for Bethel format (ADRNO + ADRSTR + ADRADD)

#### Bozrah CSV Format  
**Problem**: CSV uses `Street_Number`, `Street_Name`, `Street_Unit` instead of `Property Address`
**Error**: `Property Address column not found in raw CSV`
**Status**: FIXED - Added support for Street_Number/Street_Name format

#### Bristol CSV Format
**Problem**: Malformed CSV line 14936 - "Expected 137 fields, saw 138"
**Error**: `Error tokenizing data. C error: Expected 137 fields in line 14936, saw 138`
**Status**: FIXED - Added CSV error handling to skip malformed lines

### 3. Properties Not Importing

**Problem**: Towns show "Found X missing properties" but "Imported: 0 properties"

**Possible Causes**:
- Properties filtered out as duplicates (but check might be too aggressive)
- Geometry validation failing silently
- Commit not happening after individual inserts
- Properties with EXCEL-GEOM-* parcel IDs causing unique constraint violations

**Status**: IN PROGRESS - Added better error logging and commit logic

### 4. Missing Excel Files

**Towns Missing Excel Files**:
- Barkhamsted
- Canaan

**Impact**: Properties can still be imported from geodatabase, but CAMA data cannot be updated

### 5. CAMA Matching Issues

**Problem**: Many properties cannot be matched to Excel files

**Common Patterns**:
- Properties with `EXCEL-GEOM-*` parcel IDs (generated IDs for properties without parcel IDs)
- Properties with special parcel IDs: `HYDRO*`, `MM*`, `ROW*`, etc.
- Properties with None/null addresses

**Impact**: These properties exist in geodatabase but not in Excel files, so CAMA data cannot be updated

**Status**: EXPECTED - These are edge cases that need manual review

## Fixes Applied

1. ✅ Fixed bulk insert fallback to properly commit properties
2. ✅ Added Bethel CSV format support (ADRNO, ADRSTR, ADRADD)
3. ✅ Added Bozrah CSV format support (Street_Number, Street_Name, Street_Unit)
4. ✅ Added CSV parsing error handling for malformed lines
5. ✅ Improved error logging to identify actual failure reasons
6. ✅ Added issue tracking per town for comprehensive reporting

## Next Steps

1. Restart import to pick up fixes
2. Monitor logs for actual error messages
3. Generate comprehensive report with all issues per town
4. Review properties with EXCEL-GEOM-* parcel IDs
5. Manually review towns with high "not found in Excel" counts
