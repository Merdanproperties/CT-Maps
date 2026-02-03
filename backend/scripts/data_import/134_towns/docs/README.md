# 134 towns output

This folder holds the **134-town import flow**: batch import, per-town script, export to Excel, and reference docs. All in one place under `backend/scripts/data_import/134_towns/`.

## Scripts (run from project root)

- **Batch import** (processes all towns from `towns_to_import.txt`):  
  `PYTHONUNBUFFERED=1 python3 backend/scripts/data_import/134_towns/import_all_remaining_towns.py`  
  Optionally: `--start-batch N`. Create `APPROVE_NEXT_BATCH.txt` in this folder to continue between batches; `STOP_IMPORT.txt` to stop.

- **Per-town import** (called by the batch script; can also run single-town):  
  `import_town_optimized.py` in this folder.

- **Export results to Excel**:  
  `python3 backend/scripts/data_import/134_towns/export_import_results_to_excel.py`  
  Reads `import_output.log` at project root; writes timestamped Excel here.

## Where the 132-town list came from (reference)

The split between **132 towns** (this flow) and the **remaining ~37 towns** is based on the **Location Analysis Report**:

- **Script:** `Analysis scripts/analyze_missing_locations.py`
- **Report:** `Analysis scripts/Excel geodatabase all towns/Location_Analysis_Report_*.xlsx`
- **What it does:** Reads each town's geodatabase Excel in that folder and analyzes the **Location** column (with vs missing location). Outputs per-town stats and categories (Excellent 90%+, Partial, Few, No Locations).
- **How we use it:** Towns that **have location** in their geodatabase Excel → go in `towns_to_import.txt` → use this flow (`import_town_optimized`, no geocoding). Towns that **don't have (or barely have) location** → remaining towns → need a different strategy (e.g. lat/lon via geocoding).

To regenerate the report: from project root, `python3 "Analysis scripts/analyze_missing_locations.py"`. New report is written to `Analysis scripts/Excel geodatabase all towns/Location_Analysis_Report_{timestamp}.xlsx`.

---

## Contents

- `import_town_optimized.py` — per-town import (geometry from geodatabase Excel, no geocoding)
- `import_all_remaining_towns.py` — batch runner
- `towns_to_import.txt` — list of towns (derived from Location Analysis Report: towns with location in geodatabase Excel)
- `export_import_results_to_excel.py` — builds per-town Excel from import log + DB
- `docs/IMPORT_TOWN_OPTIMIZED_REFERENCE.md` — reference for import behavior and safe re-runs
- `logs/Import_Results_By_Town_*.xlsx` — export outputs
