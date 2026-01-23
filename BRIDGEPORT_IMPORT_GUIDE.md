# Bridgeport CAMA Data Import Guide

## Overview

This guide explains how to import Bridgeport 2025 CAMA data using the hybrid approach that combines cleaned/standardized files with raw CSV data.

## Prerequisites

1. Database migration must be run first to add new columns
2. Bridgeport parcels must already exist in database (from geodatabase import)
3. Source files must be available:
   - `/Users/jacobmermelstein/Desktop/CT Data/2025 Post Duplicate Clean/Bridgeport_CAMA_2025_CLEANED.xlsx`
   - `/Users/jacobmermelstein/Desktop/CT Data/2025 Parcel Collection/Bridgeport_CAMA_2025.csv`

## Step 1: Run Database Migration

Add new columns to the properties table:

```bash
cd backend
python scripts/migrate_add_cama_fields.py
```

This will add:
- Tax information fields (tax_amount, tax_year, tax_exemptions)
- Building exterior details (roof_type, roof_material, exterior_finish, etc.)
- Building interior details (heating_type, cooling_type, fireplace_count, etc.)
- Additional property characteristics (stories, total_rooms)

## Step 2: Test Import (Small Sample)

Test with a small sample first (100-500 properties):

```bash
cd backend
python scripts/import_cama_2025_hybrid.py --limit 500 --dry-run
```

Review the output to ensure:
- Records are matching correctly
- Data mapping looks accurate
- No critical errors

Then run without dry-run:

```bash
python scripts/import_cama_2025_hybrid.py --limit 500
```

## Step 3: Full Import

Once testing is successful, run full import for all Bridgeport properties:

```bash
python scripts/import_cama_2025_hybrid.py
```

This will process all ~34,505 Bridgeport properties.

## What the Script Does

1. **Reads cleaned Excel file** (owner/address data - standardized and fixed)
2. **Reads raw CSV file** (assessments, building details, exterior/interior info)
3. **Matches records** by normalized Property Address
4. **Combines data** using cleaned file as base, enriching with raw CSV
5. **Updates database** by matching to existing properties (by parcel_id or address)
6. **Generates coverage report** showing which parcels have data and which are missing

## Coverage Report

After import, a coverage report will be saved to:
`logs/bridgeport_cama_coverage_report_YYYYMMDD_HHMMSS.csv`

The report shows:
- Total parcels in database for Bridgeport
- Parcels with CAMA data (successfully imported)
- Parcels missing CAMA data (list of parcel_ids)
- Match rate percentage

## Data Sources (Read-Only)

- **Cleaned File**: Provides standardized owner/address data with fixes applied
- **Raw CSV**: Provides assessments, building details, tax info, exterior/interior details
- **Database**: Properties are updated (not created - they must exist from geodatabase import)

## Matching Strategy

1. Primary: Match by Parcel ID from raw CSV to database parcel_id
2. Fallback: Match by normalized Property Address
3. Properties not found in database are logged (can't create without geometry)

## Troubleshooting

- **No matches found**: Check if Bridgeport parcels exist in database from geodatabase import
- **Address matching issues**: The script normalizes addresses, but some variations may not match
- **Missing data**: Check coverage report to see which parcels need data
- **Errors**: First 10 errors are logged to console, check logs for details

## Next Steps

After successful import:
1. Review coverage report to identify missing parcels
2. Check PropertyDetail page to verify all new fields display correctly
3. Plan data collection for missing parcels if needed
