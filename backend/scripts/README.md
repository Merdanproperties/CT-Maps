# Backend Scripts

This directory contains all backend scripts organized by purpose.

## Directory Structure

### `data_import/`
Scripts for importing property data from various sources:
- **import_bridgeport_cama_2025.py** - Main CAMA import script for Bridgeport (hybrid approach: Excel + CSV)
- **import_torrington_cama.py** - Import Torrington CAMA data
- **import_torrington_cama_two_pass.py** - Two-pass import for Torrington
- **import_torrington_properties.py** - Import Torrington properties from geodatabase
- **import_missing_cama_data.py** - Import missing CAMA data for properties
- **import_missing_bridgeport.py** - Import missing Bridgeport properties
- **process_parcels.py** - Process geodatabase parcels and import to PostgreSQL
- **reimport_torrington_properties.py** - Re-import Torrington properties with proper matching

### `data_fix/`
Scripts for fixing and repairing data issues:
- **fix_torrington_addresses_original.py** - Original address fixing script
- **fix_addresses_by_cama_link.py** - Fix addresses using CAMA link matching
- **fix_addresses_by_csv_order.py** - Fix addresses using CSV order matching
- **fix_addresses_spatial_final.py** - Final spatial matching approach
- **fix_addresses_spatial_working.py** - Working spatial matching version
- **fix_addresses_with_geocoding.py** - Fix addresses using geocoding
- **fix_addresses_local_matching.py** - Local matching approach
- **fix_addresses_spatial_matching.py** - Spatial matching approach
- **fix_address_mismatches.py** - Fix address mismatches
- **fix_addresses_reverse_geocode.py** - Fix addresses using reverse geocoding
- **fix_addresses_spatial_clear_incorrect.py** - Clear incorrect addresses using spatial matching
- **update_addresses_from_cama.py** - Update addresses from CAMA data
- **reimport_addresses.py** - Re-import addresses

### `data_migration/`
Scripts for database schema migrations:
- **migrate_add_cama_fields.py** - Add CAMA-related fields to database schema

### `utilities/`
Utility scripts for analysis, inspection, and maintenance:
- **analyze_town_addresses.py** - Analyze addresses by town
- **inspect_geodatabase.py** - Inspect geodatabase structure and contents
- **validate_response_constructors.py** - Validate API response constructors
- **populate_zip_codes.py** - Populate missing zip codes
- **populate_zip_codes_simple.py** - Simple zip code population
- **view_data.py** - View database data

### `setup/`
Setup and configuration scripts:
- **setup_database.py** - Set up database tables and enable PostGIS
- **setup_local_nominatim.sh** - Set up local Nominatim instance
- **check_docker_and_setup.sh** - Check Docker installation and guide Nominatim setup

## Usage

All scripts use relative imports and should be run from the project root or with proper Python path setup:

```bash
# From project root
cd "/Users/jacobmermelstein/Desktop/CT Maps"
python -m backend.scripts.data_import.import_bridgeport_cama_2025

# Or from backend directory
cd backend
python -m scripts.data_import.import_bridgeport_cama_2025
```

## Import References

Scripts that import from other scripts use the new directory structure:
- `from scripts.data_import.import_bridgeport_cama_2025 import ...`
- `from scripts.data_fix.fix_addresses_* import ...`

Make sure to update any external references to use the new paths.
