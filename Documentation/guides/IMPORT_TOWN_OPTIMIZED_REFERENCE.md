# import_town_optimized — Reference Notes

Use this when running the batch import or `import_town_optimized` so the script keeps running smoothly.

---

## Why This Script Works (Don’t Break These)

### 1. No duplicates on re-run
- Before processing, it loads all existing `parcel_id`s for that **municipality** into `existing_parcels`.
- For each source record:
  - **parcel_id already in DB for that town** → **update** (same row, no new insert).
  - **parcel_id not in DB** → **insert**.
- Re-running for the same town is safe: it updates existing rows and only inserts records that don’t exist yet. It does **not** create duplicate rows.

### 2. Parcel ID is per-town, not global
- `parcel_id` is unique **per town** (same number can exist in different towns).
- DB uses composite unique constraint: `(parcel_id, municipality)`.
- All “find existing” logic must filter by **both** `parcel_id` and `municipality`. Never treat parcel_id as globally unique in this script.
- If a parcel_id already exists in a **different** town, **skip** inserting (don’t move properties between towns).

### 3. Geometry from source (no geocoding)
- Uses pre-exported geodatabase Excel with `Geometry_WKT`, `Latitude`, `Longitude`.
- No runtime geocoding; imports stay fast and deterministic.

### 4. Bulk ops with safe fallback
- Uses `bulk_insert_mappings` and `bulk_update_mappings`.
- On bulk insert failure (e.g. duplicate), falls back to per-row insert/update with the same “existing same town → update, other town → skip” logic so duplicates are never created.

### 5. Data quality
- **Municipality**: `normalize_municipality()` keeps town names consistent.
- **Updates**: Only non-NULL / non-empty values from source are written; don’t overwrite good existing data with blanks.

### 6. Three-way match
- Combines: geodatabase Excel (geometry), cleaned Excel (addresses), raw CSV (CAMA).
- Only records that match across sources and have geometry are imported.

---

## Before Running

- [ ] DB has composite unique constraint `(parcel_id, municipality)` — not global unique on `parcel_id` alone.
- [ ] Geodatabase Excel, cleaned Excel, and raw CSV exist for the town (or script will skip/fail with clear error).
- [ ] Paths: geodatabase Excel in `Analysis scripts/Excel geodatabase all towns/`, cleaned in `CT Data/2025 Post Duplicate Clean/`, CSV in `CT Data/2025 Parcel Collection/`.

---

## When Running Batch Import

- Use `--start-batch N` to skip earlier batches (e.g. `--start-batch 3`).
- Approval between batches: create `APPROVE_NEXT_BATCH.txt` in `backend/scripts/data_import/` to continue; create `STOP_IMPORT.txt` to stop.
- “Processing towns X–Y” uses global 1-based town numbers (e.g. 71–80 for batch 8); they match “TOWN X/132”.
- Skipped/failed towns are listed in the batch summary and in the Excel report from `export_import_results_to_excel.py`.

---

## Quick Checks If Something Goes Wrong

1. **Counts dropping after refresh** → Likely parcel_id or update logic: ensure all “existing” lookups use **parcel_id + municipality**, and updates don’t overwrite with NULLs.
2. **Duplicate key errors** → Ensure composite unique `(parcel_id, municipality)` is in place; fallback logic should update same-town or skip other-town.
3. **Town not importing** → Check cleaned Excel path and CSV column names (e.g. “Property Address”); some towns need different import (e.g. lat/lon) or fixed CSV.

---

*Last updated: 2026-01-28. See also: backend/scripts/data_import/134_towns_output/IMPORT_TOWN_OPTIMIZED_REFERENCE.md (canonical, same content).*
