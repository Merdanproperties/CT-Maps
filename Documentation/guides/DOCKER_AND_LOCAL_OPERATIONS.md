# Docker and Local Operations — Why It Works and How to Keep It Healthy

This note captures why the CT Maps stack is working and how to run it reliably.

**We run on Docker only.** All commands below assume you use `docker compose`; backend/frontend code changes require rebuilding the relevant container (`./scripts/rebuild_backend.sh` or `./scripts/rebuild_frontend.sh`).

---

## How to Run the App

| Mode | Command | When to use |
|------|---------|-------------|
| **Docker (primary)** | `docker compose up -d` | Normal use: one command, frontend + backend + Postgres stay in sync. |
| **Local (no Docker)** | `./scripts/start_all.sh` or watchdog | Optional: only when you need the app to talk directly to **local** Postgres (e.g. same DB as your DB client). |

**Rule of thumb:** Use **one** mode at a time. Don’t run `start_all.sh` or `npm run dev` while Docker is running — only Docker should use port 3000 so the browser hits the Docker frontend, which proxies to the Docker backend.

---

## Why Docker Works Now

1. **Single source of truth for the stack**  
   `docker compose up -d` starts postgres, backend, and frontend. The frontend proxies `/api` and `/health` to the backend by service name (`backend:8000`). No dependency on a separate local backend or port 8000 on the host.

2. **Reachability check uses shallow `/health`**  
   The frontend checks **`/health`** (not `/health/ready`) to decide if the backend is reachable. `/health` returns immediately with no DB work, so refreshes don’t hit "Backend connection timeout" when `/health/ready` is slow (DB check + recovery can take several seconds).

3. **Backend health**  
   The backend container can show "unhealthy" briefly on first start or after a restart (healthcheck runs before the app is ready). If the UI shows "Backend connection timeout":
   - Run: `docker compose restart backend`
   - Wait ~15 seconds for the healthcheck to pass
   - Refresh http://localhost:3000

3. **Data in Docker**  
   Docker Postgres starts empty. To use your local `ct_properties` data in Docker:
   - Run `./scripts/sync_local_db_to_docker.sh` **with Docker stopped** (`docker compose down`) so the script dumps from your **local** Postgres (port 5432), then starts Docker Postgres and restores.
   - Sync uses **plain SQL** dump (`-Fp`) so Postgres 18 (local) and Postgres 15 (Docker) are compatible.
   - After sync, run `docker compose up -d`.

5. **No version mismatch on restore**  
   Earlier, `pg_restore` failed with "unsupported version (1.16)" because the dump was from Postgres 18 (custom format) and Docker runs Postgres 15. The sync script now uses `pg_dump -Fp` (plain SQL) and `psql` to restore, so version differences don’t block the copy.

---

## Keeping Operations Healthy

- **Only Docker when you want Docker:**  
  Start with `docker compose up -d`. Don’t start the app again with `./scripts/start_all.sh` or `npm run dev` — that can bind 3000/8000 and cause timeouts or wrong backend.

- **After backend code changes (Docker):**  
  Backend runs from a **built image**. Code changes (routes, services, cache, etc.) do **not** apply until you rebuild and restart: run **`./scripts/rebuild_backend.sh`**. If you forget, the container keeps the old code and issues like API timeouts can persist until the new image is running. See `Documentation/troubleshooting/API_TIMEOUT_PREVENTION.md` for details.

- **Refreshing data from local into Docker:**  
  1. `docker compose down`  
  2. Ensure local Postgres (with `ct_properties`) is running on 5432  
  3. `./scripts/sync_local_db_to_docker.sh`  
  4. `docker compose up -d`  
  If the stack is already up and you sync (e.g. after re-running the script with Docker down then up again), you can just run `docker compose restart backend` so the app sees the updated data.

- **High CPU and API errors:** Backend is limited to **1 CPU and 1GB RAM** in Docker so it can't starve the stack. High CPU or near-full memory (e.g. 7GB/7.5GB) can cause timeouts and "Backend connection timeout". If you see extra containers (e.g. a separate ctmaps or nominatim), stop any you don't need: `docker stop <container>` to free CPU and memory. Backend runs one worker and 60s DB monitor to reduce load.

**If the site shows "Backend connection timeout" or "Backend check failed":**  
  1. Check stack: `docker compose ps` — backend should be **(healthy)**.  
  2. If backend is **(unhealthy)**: `docker compose restart backend`, wait ~15s, refresh the page.  
  3. If you're not using Docker, ensure backend and frontend are running (e.g. `./scripts/start_all.sh`) and that nothing else is using ports 3000 or 8000.

- **Logs:**  
  - Docker: `docker compose logs backend frontend`  
  - Local: `logs/backend.log`, `logs/frontend.log`

---

## Diagnostics (high CPU / slow API)

If the backend container is pegging CPU or options/search endpoints time out:

1. **See which process is burning CPU (inside backend container)**  
   `docker compose exec backend sh -c "ps aux --sort=-%cpu | head -20"`  
   If uvicorn/python is at the top, get its PID and check threads:  
   `PID=$(docker compose exec backend sh -c "ps aux | awk '/uvicorn|python/ && !/awk/ {print \$2; exit}'"); docker compose exec backend sh -c "top -H -p $PID"`

2. **See if backend is stuck on DB vs Python**  
   From inside the backend container (or `docker compose exec backend sh`):  
   `time curl -s -o /dev/null -w "health: %{http_code} in %{time_total}s\n" http://localhost:8000/health`  
   `time curl -s -o /dev/null -w "unit-types: %{http_code} in %{time_total}s\n" http://localhost:8000/api/search/unit-types/options`  
   `time curl -s -o /dev/null -w "zoning: %{http_code} in %{time_total}s\n" http://localhost:8000/api/search/zoning/options`  
   If `/health` is fast but options are slow, the bottleneck is likely DB (missing indexes or heavy query). If `/health` is also slow, the process may be blocked or starved.

3. **Check DB reachability and long-running queries**  
   `docker compose exec postgres psql -U ctmaps -d ct_properties -c "SELECT 1;"`  
   To list long-running queries:  
   `docker compose exec postgres psql -U ctmaps -d ct_properties -c "SELECT pid, now()-query_start AS runtime, state, wait_event_type, wait_event, left(query,120) AS q FROM pg_stat_activity WHERE datname='ct_properties' AND state <> 'idle' ORDER BY runtime DESC LIMIT 20;"`

4. **Add indexes for options and spatial queries**  
   Without these, options endpoints (towns, zoning, unit-types, owner-cities, owner-states) do full table scans and time out. **For Docker Postgres**, run once (or after restoring DB):  
   `./scripts/apply_indexes_in_docker.sh`  
   Then optionally: `docker compose exec postgres psql -U ctmaps -d ct_properties -c "ANALYZE;"`  
   For a local (non-Docker) DB: `cd backend && DATABASE_URL=postgresql+psycopg2://ctmaps:ctmaps@localhost:5432/ct_properties python scripts/data_migration/add_options_indexes.py`

---

## Stability fixes (search + CPU)

- **Search:** Backend caps `page_size` at 200 and rejects bounding boxes larger than 5000 km² (returns 400). Frontend requests 200 per page; oversized bbox returns a clear error so users can zoom in.
- **Workers:** Backend runs 2 uvicorn workers with a 2 CPU limit so health and heavy search/options requests don't block each other.
- **Verify after startup (via frontend proxy on 3000):**  
  `curl -s "http://localhost:3000/api/search/?bbox=-73.4,41.2,-72.9,41.6&page_size=5" | head -c 200`  
  (should return JSON).  
  `curl -s -o /dev/null -w "%{http_code}" "http://localhost:3000/api/search/?bbox=-180,0,180,90&page_size=10"`  
  (should return 400 for oversized bbox.)

---

## Quick Reference

| Task | Command |
|------|---------|
| Start app (Docker) | `docker compose up -d` |
| Stop app (Docker) | `docker compose down` |
| Copy local DB to Docker | `docker compose down` then `./scripts/sync_local_db_to_docker.sh` then `docker compose up -d` |
| Backend unhealthy | `docker compose restart backend` then refresh http://localhost:3000 |
| Check status | `docker compose ps` |

See [QUICKSTART.md](../../QUICKSTART.md) for full run options and validation steps.
