# 134 towns output

This folder holds the **134-town import flow**: batch import, per-town script, export to Excel, and reference docs. All in one place under `backend/scripts/data_import/134_towns_output/`.

## Scripts (run from project root)

- **Batch import** (processes all towns from `towns_to_import.txt`):  
  `PYTHONUNBUFFERED=1 python3 backend/scripts/data_import/134_towns_output/import_all_remaining_towns.py`  
  Optionally: `--start-batch N`. Create `APPROVE_NEXT_BATCH.txt` in this folder to continue between batches; `STOP_IMPORT.txt` to stop.

- **Per-town import** (called by the batch script; can also run single-town):  
  `import_town_optimized.py` in this folder.

- **Export results to Excel**:  
  `python3 backend/scripts/data_import/134_towns_output/export_import_results_to_excel.py`  
  Reads `import_output.log` at project root; writes timestamped Excel here.

## Contents

- `import_town_optimized.py` — per-town import (geometry from geodatabase Excel, no geocoding)
- `import_all_remaining_towns.py` — batch runner
- `towns_to_import.txt` — list of towns
- `export_import_results_to_excel.py` — builds per-town Excel from import log + DB
- `IMPORT_TOWN_OPTIMIZED_REFERENCE.md` — reference for import behavior and safe re-runs
- `Import_Results_By_Town_*.xlsx` — export outputs
