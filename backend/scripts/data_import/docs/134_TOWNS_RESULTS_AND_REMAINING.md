# 134 Towns: Results So Far & What’s Remaining

Last updated: **2026-02-06** (after Bethel + Sherman re-run).

---

## Results we have so far

### 134-town flow

- **Source:** Batch run logs + `import_output.log` → Excel: `134_towns/logs/Import_Results_By_Town_20260203_095945.xlsx`
- **List:** `backend/scripts/data_import/134_towns/towns_to_import.txt` (132 towns in batch)
- **Status:** Batch had **120 success**, **10 skipped**, **2 failed**. We then ran the 6 filename-variant towns and fixed + re-ran Bethel and Sherman; all 8 are now in DB.

### Six towns fixed and imported (2026-02-05)

These were “skipped” due to filename mismatches; we ran them with `--cleaned-excel` and `--csv` paths:

| Town          | Inserted | Geodatabase total | Note                    |
|---------------|----------|-------------------|-------------------------|
| Barkhamsted   | 1,916    | 2,014             | Counts close            |
| Franklin      | 1,057    | 1,111             | Counts close            |
| New Fairfield | 6,470    | 6,581             | Counts close            |
| Winchester    | 5,238    | 7,710             | **High discrepancy (32.1%)** |
| Wolcott       | 6,690    | 6,809             | Counts close            |
| Woodbridge    | 3,604    | 3,628             | Counts close            |

**Log:** `134_towns/logs/six_towns_import_20260205_234349.log`

### Bethel and Sherman (2026-02-06)

- **Bethel:** 6,941 inserted; **high discrepancy (11.1%)** — consider lat/lon flow for rest.
- **Sherman:** 111 inserted; **high discrepancy (95.8%)** — address match to geodatabase is poor; consider lat/lon flow for rest.

### 35-town flow

- **List:** `backend/scripts/data_import/35_towns/towns_35_geocode_spatial.txt`
- **Status:** 34 of 35 in DB; **Hartland** missing (no cleaned Excel/CSV in folder).

### Overall DB count

- **Towns in DB:** 164 (after Bethel + Sherman).
- **Target:** 169 (134 + 35, de-duplicated).
- **Still missing:** **5 towns**.

---

## 134 towns with significant discrepancy (>10%)

The importer flags **“Significant discrepancy”** when (geodatabase total − DB count) / geodatabase total &gt; 10%. These towns may benefit from the lat/lon/geocode import for unmatched parcels.

**From batch run** (`import_output.log`):  
Groton, Farmington, Simsbury, Southbury, Watertown, Darien, New Canaan, Old Saybrook, East Hampton, Cromwell, Thompson, Windsor Locks, Portland, Derby, New Hartford, Middlebury, Harwinton, Easton, Salisbury, Sharon, Ashford, Kent, Bozrah, Norfolk, Eastford, Franklin, Union.

**From manual runs:**  
Winchester (32.1%), Bethel (11.1%), Sherman (95.8%).

**Total:** 30 towns with significant discrepancy. Full per-town stats are in `134_towns/logs/Import_Results_By_Town_*.xlsx` (re-export from `import_output.log` to refresh).

**Discrepancy % for every town (21–132):** see [134_TOWNS_DISCREPANCY_PERCENTAGES.md](134_TOWNS_DISCREPANCY_PERCENTAGES.md).

---

## What’s remaining

### 5 towns still missing from the DB

| # | Town         | Flow | Reason |
|---|--------------|------|--------|
| 1 | Canaan       | 134  | No file in `2025 Post Duplicate Clean` |
| 2 | Hartland     | 35   | No cleaned Excel/CSV in folder |
| 3 | Litchfield   | 134  | No file in `2025 Post Duplicate Clean` |
| 4 | Morris       | 134  | No file in `2025 Post Duplicate Clean` |
| 5 | New Hartford | 134  | No file in `2025 Post Duplicate Clean` |

### By next step

- **Need data files (5):** Canaan, Hartland, Litchfield, Morris, New Hartford — add cleaned Excel (and CSV for 134 flow) to the right folders, then run the appropriate import.

---

## Reference

- **134 results Excel:** `backend/scripts/data_import/134_towns/logs/Import_Results_By_Town_*.xlsx`
- **Re-export 134 results:**  
  `python3 backend/scripts/data_import/134_towns/export_import_results_to_excel.py`  
  (reads `import_output.log` at project root)
- **Six-town script (variant paths):** `backend/scripts/data_import/134_towns/run_six_towns_with_variant_paths.sh`
- **Full remaining-towns detail:** `backend/scripts/data_import/docs/REMAINING_TOWNS_SUMMARY.md`
