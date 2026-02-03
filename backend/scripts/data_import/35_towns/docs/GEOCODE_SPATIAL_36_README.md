# Geocode + Spatial Import: Towns with No/Low Location

These **35 towns** have **No or Low Location** (0% or &lt;50%) in the **Location Analysis Report** (`Analysis scripts/Excel geodatabase all towns/Location_Analysis_Report_*.xlsx`). Use **geocode_spatial** to import them: addresses are geocoded with local Nominatim, then matched to FileGDB parcels by proximity.

**Source:** This list is the exact set of towns with **No/Low Location (&lt;50%)** from the Location Analysis Report. It includes **Avon** (0% Location in report). **Bridgeport** and **Middletown** are not in this list—the report shows they have Location (90%+); run them with **import_town_optimized** instead.

## Prerequisites

1. **Docker Postgres** running so imports update the map directly: `docker compose up -d postgres` (and `backend/.env` with `DATABASE_URL=postgresql+psycopg2://ctmaps:ctmaps@localhost:5432/ct_properties`).
2. **Local Nominatim** running (e.g. Docker on `http://localhost:8080`).
3. **CT Data** paths:
   - Cleaned Excel: `CT Data/2025 Post Duplicate Clean/{Town}_CAMA_2025_CLEANED.xlsx`
   - CSV: `CT Data/2025 Parcel Collection/{Town}_CAMA_2025.csv`
4. **FileGDB**: `2025 Parcel Layer.gdb` (for parcel geometry).

Towns missing cleaned Excel or CSV will be skipped (e.g. Hartland).

## How to Run

From **project root**:

```bash
# Start Nominatim if not already running (see backend/scripts/setup_nominatim.sh or your Docker setup)

# Run the 36-town import (batches of 10, approval between batches)
PYTHONUNBUFFERED=1 python3 backend/scripts/data_import/35_towns/import_town_geocode_spatial.py \
  --towns-file backend/scripts/data_import/35_towns/towns_35_geocode_spatial.txt \
  2>&1 | tee geocode_spatial_import.log
```

In another terminal, watch progress:

```bash
tail -f geocode_spatial_import.log
```

## Between Batches

- After each batch of 10 towns, the script waits for approval.
- To **continue**: create `backend/scripts/data_import/APPROVE_NEXT_BATCH.txt` (script will delete it and proceed).
- To **stop**: create `backend/scripts/data_import/STOP_IMPORT.txt` (script will exit after current batch).

## Resuming

- Geocoding results are cached per town in `backend/scripts/data_import/35_towns/logs/geocode_cache_{Town}.json`.
- To re-run from a later batch: use `--start-batch N` (1-based). Example: start from batch 2:
  ```bash
  PYTHONUNBUFFERED=1 python3 backend/scripts/data_import/import_town_geocode_spatial.py \
    --towns-file backend/scripts/data_import/towns_35_geocode_spatial.txt \
    --start-batch 2 \
    2>&1 | tee geocode_spatial_import.log
  ```

## Coverage Note

Only addresses that **successfully geocode** get geometry and are inserted. The script retries with "Connecticut" and with a simplified address to improve the hit rate. Re-running (with cache) does not re-geocode; clear the cache file for a town to retry geocoding. For towns where many addresses still fail, consider improving address normalization or adding another geocoder as fallback.
