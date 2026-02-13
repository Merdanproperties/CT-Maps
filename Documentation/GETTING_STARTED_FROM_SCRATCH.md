# CT Maps: From Scratch — What We Have and How to Run It

This guide assumes you know nothing about the project. Use it to understand what’s been built and how to run the app and scripts.

---

## What is CT Maps?

**CT Maps** is a web app for searching and viewing Connecticut property data (parcels, addresses, owners, CAMA data) on a map. It has:

- **Frontend** (React + Vite): map, search, filters, property details.
- **Backend** (FastAPI): API for search, filters, autocomplete, export.
- **PostgreSQL + PostGIS**: stores properties and geometry.

Data is loaded by **import scripts** that read Excel/CSV from your machine and write into the database.

---

## What’s Been Accomplished (High Level)

- **134-town import flow**: Most Connecticut towns are imported from:
  - Geodatabase Excel (with geometry),
  - “Cleaned” CAMA Excel,
  - Raw CSV.  
  Script matches them and bulk-inserts/updates into the DB. **Caching** makes re-runs fast (skips re-parsing when files haven’t changed).
- **35-town flow**: A smaller set of towns uses a different pipeline (geocode/spatial) when geometry isn’t in the main files. One town (Hartland) is still missing (no source files).
- **Six towns** that had different file names (e.g. Winsted vs Winchester) were given default-named files so the 134-town script picks them up.
- **“Not Added” exports**: For each town, records that couldn’t be added (e.g. no geometry) are exported to Excel under `134_towns/logs/Not Added/`.
- **Docker**: Full stack (frontend, backend, Postgres) runs with `docker compose`. You can also run backend + DB locally and use a **sync script** to copy that DB into Docker so the app in Docker uses your latest data.
- **Docs and cleanup**: Discrepancy-percentage report per town, cleanup of old logs/Not Added duplicates, favicon (map pin) for the app.

---

## Folder Structure (Plain English)

| Path | What it is |
|------|------------|
| **`frontend/`** | React app (map, search, filters). Run with `npm run dev` or via Docker. |
| **`backend/`** | FastAPI app and all Python scripts. API runs here; import scripts are under `backend/scripts/`. |
| **`scripts/`** (project root) | Shell scripts: start/stop app, Docker compose helpers, **sync local DB → Docker**, apply indexes. |
| **`backend/scripts/data_import/`** | All data-import and related tooling. |
| **`backend/scripts/data_import/134_towns/`** | **Main import**: 134-town list, optimized importer, batch runner, cache, “Not Added” exports. |
| **`backend/scripts/data_import/35_towns/`** | Geocode/spatial import for towns that need it (e.g. Hartland when files exist). |
| **`backend/scripts/data_import/docs/`** | Import docs: discrepancy table, results summary, checklists. |
| **`backend/scripts/data_import/cama_tools/`** | CAMA update/compare/monitor scripts. |
| **`backend/scripts/data_import/matching_and_export/`** | Match Excel to DB, export unmatched, geocode helpers. |
| **`backend/scripts/data_import/verification/`** | Scripts to verify data (e.g. parcel ID usage). |
| **`backend/scripts/data_import/one_off/`** | One-off/utility scripts (progress check, process parcels, etc.). |
| **`Analysis scripts/`** (project root) | Analysis Excel/Python and **“Excel geodatabase all towns”** — the geodatabase Excel files the 134-town importer uses. |
| **`Documentation/`** | Guides (Docker, setup, troubleshooting, this file). |
| **`docker-compose.yml`** | Defines Postgres, backend, and frontend containers. |

Your **source data** (cleaned Excel, raw CSV) lives **outside** the repo, e.g.:

- **Cleaned Excel**: e.g. `.../CT Data/2025 Post Duplicate Clean/{Town}_CAMA_2025_CLEANED.xlsx`
- **Raw CSV**: e.g. `.../CT Data/2025 Parcel Collection/{Town}_CAMA_2025.csv`

The 134-town script expects these paths (or you pass `--cleaned-excel` and `--csv` for one town). Geodatabase Excel is under `Analysis scripts/Excel geodatabase all towns/`.

---

## How to Run the App (Use the Site)

You have two main options.

### Option A: Run with Docker (recommended)

From the **project root** (the folder that contains `docker-compose.yml`):

```bash
docker compose up -d
```

Then open **http://localhost:3000**. Frontend, backend, and Postgres all run in containers.

- To see logs: `docker compose logs -f backend` or `docker compose logs -f frontend`
- To stop: `docker compose down`
- If the app was built before and you only changed code, you usually don’t need `--build`; add it if you changed dependencies or Dockerfiles.

**Using your own database in Docker:**  
If your real data is in a **local** Postgres (e.g. you ran imports on your machine):

1. Stop Docker Postgres so the script can dump from local:  
   `docker compose stop postgres`
2. Run the sync script from project root:  
   `./scripts/sync_local_db_to_docker.sh`  
   (It dumps from `backend/.env`’s `DATABASE_URL` and restores into the Docker Postgres container.)
3. Start the stack again:  
   `docker compose up -d`

After that, the app in Docker uses the data you synced. Re-run the sync whenever you’ve updated local data and want Docker to match.

### Option B: Run backend and frontend locally

- **PostgreSQL** must be running (e.g. local Postgres on port 5432).
- **Backend**: From project root, e.g.  
  `cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000`  
  (Use your own venv path if different.)
- **Frontend**: From project root, e.g.  
  `cd frontend && npm run dev`  
  (Serves on port 3000 and proxies `/api` and `/health` to the backend.)

Then open **http://localhost:3000**.  
Ensure `backend/.env` has the correct `DATABASE_URL` (e.g. local Postgres). See [QUICKSTART.md](QUICKSTART.md) and [Documentation/guides/DOCKER_AND_LOCAL_OPERATIONS.md](guides/DOCKER_AND_LOCAL_OPERATIONS.md) for more.

---

## How to Run the Main Scripts

All commands below are from the **project root** unless we say “from `backend`” or “from `backend/scripts/...`”.

### 1. Full 134-town import (all towns in one go)

Imports (or updates) all towns listed in `backend/scripts/data_import/134_towns/towns_to_import.txt`.  
Uses geodatabase Excel + cleaned Excel + raw CSV. **Caching** makes re-runs fast when files haven’t changed.

**Prerequisites:**

- Postgres running (local or Docker).
- `backend/.env` (or environment) set so the backend can connect to that Postgres (e.g. `DATABASE_URL`).
- Source data in the expected places (or symlinks/copies):  
  - Geodatabase: `Analysis scripts/Excel geodatabase all towns/{Town}.xlsx`  
  - Cleaned: e.g. `.../CT Data/2025 Post Duplicate Clean/{Town}_CAMA_2025_CLEANED.xlsx`  
  - CSV: e.g. `.../CT Data/2025 Parcel Collection/{Town}_CAMA_2025.csv`

**Command:**

```bash
cd backend
PYTHONUNBUFFERED=1 python3 scripts/data_import/134_towns/import_all_remaining_towns.py --run-all
```

- `--run-all`: run all batches without pausing for approval between batches.
- To follow progress in another terminal, find the latest log and run:  
  `tail -f backend/scripts/data_import/134_towns/logs/full_134_import_*.log`  
  (Use the actual newest filename.)

**Output:**

- Logs in `backend/scripts/data_import/134_towns/logs/`.
- “Not Added” Excel files per town in `backend/scripts/data_import/134_towns/logs/Not Added/`.
- Parse cache under `backend/scripts/data_import/134_towns/logs/parse_cache/` for faster re-runs.

If you run with Docker, point the backend (or your shell) at the same Postgres the app uses, or run the import against local Postgres and then run `./scripts/sync_local_db_to_docker.sh` to push that DB into Docker.

---

### 2. Sync local Postgres into Docker

Use this when your “real” data is in **local** Postgres and you want the **Docker** app to use it.

**Steps:**

1. Stop Docker Postgres:  
   `docker compose stop postgres`
2. From project root:  
   `./scripts/sync_local_db_to_docker.sh`  
   (Reads `backend/.env` for the source DB; restores into the Docker Postgres container.)
3. Start the stack:  
   `docker compose up -d`

Optional: run trigram indexes for search performance:  
`./scripts/apply_trigram_indexes_in_docker.sh`

---

### 3. Regenerate the discrepancy-percentage report (134 towns)

After a full 134-town run, you can regenerate the markdown table of per-town discrepancy percentages.

**Command:**

```bash
python3 backend/scripts/data_import/134_towns/build_discrepancy_md.py
```

With no arguments it uses the **latest** `full_134_import_*.log` in `backend/scripts/data_import/134_towns/logs/`.  
To use a specific log:

```bash
python3 backend/scripts/data_import/134_towns/build_discrepancy_md.py backend/scripts/data_import/134_towns/logs/full_134_import_YYYYMMDD_HHMMSS.log
```

**Output:**  
Overwrites `backend/scripts/data_import/docs/134_TOWNS_DISCREPANCY_PERCENTAGES.md`.

---

### 4. Import a single town (134-town flow)

Useful to test or re-run one municipality.

**Command (from project root):**

```bash
cd backend
python3 scripts/data_import/134_towns/import_town_optimized.py "TownName"
```

Example:

```bash
python3 scripts/data_import/134_towns/import_town_optimized.py "Waterbury"
```

If that town’s files have nonstandard names or paths, pass them explicitly:

```bash
python3 scripts/data_import/134_towns/import_town_optimized.py "Winchester" \
  --cleaned-excel "/path/to/Winsted_CAMA_2025_CLEANED.xlsx" \
  --csv "/path/to/Winsted_CAMA_2025.csv"
```

(Geodatabase Excel is still resolved from `Analysis scripts/Excel geodatabase all towns/` unless you add a flag for it; see script help.)

---

### 5. Other scripts (when to use them)

- **`backend/scripts/data_import/134_towns/export_import_results_to_excel.py`**  
  Parses an import log and writes an Excel report of results per town. Expects a log at project root named `import_output.log` by default (see script for options). Useful after a batch run if you want Excel instead of/in addition to the discrepancy markdown.

- **`backend/scripts/data_import/35_towns/import_town_geocode_spatial.py`**  
  For the 35-town (geocode/spatial) flow. Used when a town doesn’t have geometry in the main geodatabase Excel and needs geocoding. See `backend/scripts/data_import/35_towns/docs/`.

- **`scripts/apply_trigram_indexes_in_docker.sh`**  
  Apply search-related indexes in Docker Postgres. Run once after a fresh DB or after restoring from sync.

- **`scripts/restart_backend.sh`**  
  Restart the backend (e.g. after config or env changes). Use when running with Docker or your own process manager.

---

## Data and Paths (Recap)

- **Database**: Postgres database (e.g. `ct_properties`). Local: often port 5432; Docker: same inside the network, and you can expose it if needed.
- **Geodatabase Excel**: Under `Analysis scripts/Excel geodatabase all towns/` — one Excel per town, with geometry.
- **Cleaned Excel / CSV**: Typically under folders like `.../CT Data/2025 Post Duplicate Clean/` and `.../CT Data/2025 Parcel Collection/`. The 134-town script’s default paths are set in code (see `import_town_optimized.py`).
- **List of 134 towns**: `backend/scripts/data_import/134_towns/towns_to_import.txt`.
- **Not Added exports**: `backend/scripts/data_import/134_towns/logs/Not Added/` — one Excel per town for records that weren’t added (e.g. no geometry).

---

## Quick Reference: “I want to…”

| Goal | What to run |
|------|-------------|
| Use the app in the browser | `docker compose up -d` → open http://localhost:3000 |
| Load/update all 134 towns from Excel/CSV | From `backend`: `PYTHONUNBUFFERED=1 python3 scripts/data_import/134_towns/import_all_remaining_towns.py --run-all` (then sync to Docker if you use Docker) |
| Copy my local DB into Docker so the app shows my data | `docker compose stop postgres` → `./scripts/sync_local_db_to_docker.sh` → `docker compose up -d` |
| Update the discrepancy-percentage doc after a 134 run | `python3 backend/scripts/data_import/134_towns/build_discrepancy_md.py` |
| Import or re-import one town | From `backend`: `python3 scripts/data_import/134_towns/import_town_optimized.py "TownName"` |
| See what the 134-town flow does in detail | Read `backend/scripts/data_import/134_towns/docs/IMPORT_TOWN_OPTIMIZED_REFERENCE.md` and `backend/scripts/data_import/docs/134_TOWNS_DISCREPANCY_PERCENTAGES.md` |

---

## If Something Breaks

- **App won’t load / 500 errors**: Check that Postgres and the backend are running. With Docker: `docker compose ps` and `docker compose logs backend`. Restart backend if needed: `docker compose restart backend`.
- **Imports fail (file not found)**: Check that cleaned Excel and CSV paths exist for that town. Either put files in the default locations or use `--cleaned-excel` and `--csv` for that town.
- **Docker build fails (e.g. permission/temp dir)**: Use `./scripts/docker_compose_up.sh` or set `TMPDIR` to a writable dir (see [QUICKSTART.md](QUICKSTART.md)).

More: [Documentation/troubleshooting/](troubleshooting/) and [Documentation/guides/DOCKER_AND_LOCAL_OPERATIONS.md](guides/DOCKER_AND_LOCAL_OPERATIONS.md).
