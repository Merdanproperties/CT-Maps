# Remaining Towns Summary

Checked **2026-02-03** from project logs and **database**.

## Totals (DB-verified)

| Source | Count |
|--------|-------|
| **Towns in DB** (distinct `municipality`) | **156** |
| **Expected** (134 + 35 lists, unique) | 169 |
| **Remaining** (in list but no data in DB) | **13** |

So **13 towns** are still missing; once they’re imported, you’ll have all 169.

---

### All 13 missing towns (from DB)

| Town | Flow | Likely reason |
|------|------|----------------|
| Barkhamsted | 134 | Cleaned Excel not found |
| Bethel | 134 | Property Address column not found in raw CSV |
| Canaan | 134 | Cleaned Excel not found |
| FRANKLIN | 134 | Cleaned Excel not found |
| **Hartland** | **35** | Cleaned Excel/CSV missing (skipped in geocode run) |
| Litchfield | 134 | Cleaned Excel not found |
| Morris | 134 | Cleaned Excel not found |
| New Fairfield | 134 | Cleaned Excel not found |
| New hartford | 134 | Cleaned Excel not found |
| Sherman | 134 | Property Address column not found in raw CSV |
| WINCHESTER | 134 | Cleaned Excel not found |
| Wolcott | 134 | Cleaned Excel not found |
| Woodbridge | 134 | Cleaned Excel not found |

- **134 flow:** 12 remaining (10 skipped, 2 failed).
- **35 flow:** 1 remaining (Hartland).

---

## 134-town flow (from logs)

- **Source:** `import_output.log` → `export_import_results_to_excel.py`
- **Excel:** `134_towns/logs/Import_Results_By_Town_20260203_095945.xlsx`

### Failed (2)

- **Bethel** — Property Address column not found in raw CSV (column name mapping needed).
- **Sherman** — Property Address column not found in raw CSV (column name mapping needed).

### Skipped (10)

All due to *Cleaned Excel not found* (missing file under `.../2025 Post Duplicate Clean/`):

- WINCHESTER  
- Wolcott  
- New Fairfield  
- Litchfield  
- Woodbridge  
- New hartford  
- Barkhamsted  
- Morris  
- FRANKLIN  
- Canaan  

**134 flow remaining: 12 towns** (fix data/paths or column mapping, then re-run from the appropriate town).

---

## 35-town flow

- You already ran the 35-town flow end-to-end. The **DB** shows only **Hartland** missing from the 35 list (no rows in `properties`). So the 35-town run had **1 skip** (Hartland); the other 34 are in the DB.
- **Logs checked (reference):** `geocode_spatial_import.log`, `geocode_spatial_from_redding_20260202_184844.log`, `geocode_spatial_rerun_20260201_182522.log`
- No single log shows a **full 35-town run** with a final “IMPORT COMPLETE” summary.
- The run that **started from Redding** (`geocode_spatial_from_redding_20260202_184844.log`) completed **13 towns** (Redding through Woodstock) with **Success: 13 | Skipped: 0 | Failed: 0**.

So for the 35-town flow, **skipped/failed counts are not available** from the current logs. To get them:

1. Run the 35-town import to completion:
   ```bash
   PYTHONUNBUFFERED=1 python3 backend/scripts/data_import/35_towns/import_town_geocode_spatial.py \
     --towns-file backend/scripts/data_import/35_towns/towns_35_geocode_spatial.txt 2>&1 | tee geocode_spatial_full.log
   ```
2. At the end it will print:
   - `Success: X | Skipped: Y | Failed: Z`
   - **TOWNS TO ADDRESS** (list of skipped + failed).

Then: **Total remaining = 12 (134 flow) + Y + Z (35 flow).**

---

## Quick reference

- **134-town list:** `backend/scripts/data_import/134_towns/towns_to_import.txt`
- **35-town list:** `backend/scripts/data_import/35_towns/towns_35_geocode_spatial.txt`
- **Re-export 134 results:**  
  `python3 backend/scripts/data_import/134_towns/export_import_results_to_excel.py`  
  (reads `import_output.log` at project root; writes timestamped Excel under `134_towns/logs/`)
