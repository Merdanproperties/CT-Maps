# Zoning Data Import Notes

## Important: Zoning Must Be Imported for All Future Imports

**CRITICAL**: The `zoning` field is now mapped from the "Zone" column in cleaned Excel files. When importing CAMA data for any municipality, zoning will automatically be imported if:

1. The cleaned Excel file contains a "Zone" column
2. The mapping functions in `import_bridgeport_cama_2025.py` and `import_missing_cama_data.py` are used
3. The update functions in `update_all_cama_from_cleaned_excel.py` and `cama_update.py` are used

## Files That Handle Zoning Import

- `backend/scripts/data_import/import_bridgeport_cama_2025.py` - Maps "Zone" column to `zoning` field
- `backend/scripts/data_import/import_missing_cama_data.py` - Maps "Zone" column to `zoning` field
- `backend/scripts/data_import/update_all_cama_from_cleaned_excel.py` - Updates `zoning` field from Excel
- `backend/scripts/data_import/cama_update.py` - Updates `zoning` field from Excel (generic municipality support)

## How to Import Zoning for a New Municipality

1. Ensure the cleaned Excel file has a "Zone" column
2. Run the update script for that municipality:
   ```python
   from database import SessionLocal
   from scripts.data_import.cama_tools.cama_update import update_all_cama_from_cleaned_excel
   
   db = SessionLocal()
   update_all_cama_from_cleaned_excel('MunicipalityName', db, dry_run=False)
   db.close()
   ```

## Current Status

- ✅ Torrington: 12,008/12,688 properties (94.6%) have zoning data
- ✅ Bridgeport: 26,392/27,710 properties (95.2%) have zoning data
