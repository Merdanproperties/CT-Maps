# How to run the app

**Normal development (your existing data):** Use your local Postgres (e.g. "CT Properties" with the `properties` table). Ensure [backend/.env](backend/.env) has `DATABASE_URL` pointing at it (or leave unset for `postgresql://localhost:5432/ct_properties`). Then start the app with **Start** below (watchdog or `./scripts/start_all.sh`). The site at http://localhost:3000 will use that database. For why Docker vs local works and how to keep operations healthy, see [Documentation/guides/DOCKER_AND_LOCAL_OPERATIONS.md](Documentation/guides/DOCKER_AND_LOCAL_OPERATIONS.md).

---

## Run with Docker (clean / demo)

Single command, fixed network, no localhost/proxy drift. Requires Docker Desktop (or Docker Engine + Compose).

From the project root:

```bash
docker compose up --build
```

Then open **http://localhost:3000**. Frontend, backend, and Postgres run in containers; the frontend proxies `/api` and `/health` to the backend automatically. For local dev (without Docker), do not set `VITE_PROXY_TARGET` (defaults to http://localhost:8000); Docker Compose sets it to http://backend:8000.

To stop: `Ctrl+C` then `docker compose down`. Data is kept in a volume; use `docker compose down -v` to remove it.

**First run:** The backend creates the database schema (PostGIS + tables) automatically on startup when the DB is empty. No manual migrations needed. Copy [backend/.env.example](backend/.env.example) to `backend/.env` for local runs; Docker Compose sets `DATABASE_URL` for the backend container. For the map, ensure [frontend/.env](frontend/.env) has `VITE_MAPBOX_ACCESS_TOKEN` (Compose passes it into the frontend container).

**Docker validation checklist (run once):**
1. Start: `docker compose up --build`
2. Backend health (shallow): `docker compose exec backend curl -sf http://localhost:8000/health` — expect 200 quickly with `{"status":"ok","api":"operational"}`
3. Open http://localhost:3000 in the browser
4. Proxy resolves: `docker compose exec frontend wget -qO- http://backend:8000/health/ready` — expect JSON with `database` and `status`

**If build fails with "can't access os.tempDir ... permission denied" (macOS):** Docker Buildx is using the system temp dir and hitting a permission issue. Use a writable temp dir and re-run:

```bash
mkdir -p "$HOME/tmp/docker-build"
export TMPDIR="$HOME/tmp/docker-build"
docker compose up --build
```

Or run the helper script: `./scripts/docker_compose_up.sh` (see [scripts/README-Docker.md](scripts/README-Docker.md)).

**Docker with your local data (copy DB into Docker):** To run everything in Docker but use a copy of your local Postgres database:

1. Ensure your local Postgres has the data you want (e.g. "CT Properties" with the `properties` table).
2. From the project root, run: `./scripts/sync_local_db_to_docker.sh`  
   This dumps your local `ct_properties` DB and restores it into the Docker Postgres container. It uses `DATABASE_URL` from [backend/.env](backend/.env) (or `postgresql://localhost:5432/ct_properties`) for the source.
3. Start the stack: `docker compose up -d` (or `./scripts/docker_compose_up.sh`).

Whenever you update your local Postgres (imports, edits), run the sync script again so Docker has the latest data, then restart backend if the stack is already up: `docker compose restart backend`.

---

## Prerequisites (non-Docker)

- **PostgreSQL** running (e.g. `brew services start postgresql` on macOS).
- **Node** and **Python** (with venv) installed.
- Ports **3000** and **8000** free.

## Start (recommended: watchdog)

Run the watchdog once from the project root. It starts backend and frontend and restarts them if they crash. You can close the terminal afterward.

```bash
mkdir -p logs
nohup ./scripts/watchdog.sh >> logs/watchdog.log 2>&1 &
```

Then open http://localhost:3000. To stop everything: `./scripts/stop_all.sh`, then `pkill -f watchdog.sh`.

**Alternative (one-shot, no auto-restart):** Run `./scripts/start_all.sh` from the project root. Backend and frontend keep running after you close the terminal (started with `nohup`), but they will not restart if they crash.

## Always on at login (macOS)

To have the app come back automatically after reboot without running a command, run the watchdog as a LaunchAgent. See [scripts/launchd/README.md](scripts/launchd/README.md) for setup (copy plist, load with `launchctl`).

## Open

- **Frontend:** http://localhost:3000  
- **API docs:** http://localhost:8000/docs  

## Stop

```bash
./scripts/stop_all.sh
```

If you started the watchdog, also run: `pkill -f watchdog.sh`

## If the site does not load

**Docker:** Run `docker compose logs backend frontend` and ensure Postgres is healthy (`docker compose ps`). If you see "Backend connection timeout" or "Backend check failed", ensure you're not also running the app locally (stop any `./scripts/start_all.sh` or `npm run dev`); only Docker should use port 3000. If the backend container is unhealthy, run `docker compose restart backend`, wait ~15s, then refresh http://localhost:3000. Rebuild with `docker compose up --build` if needed.

**Non-Docker:**
1. Check that something is listening on 3000 and 8000:
   - `lsof -i :3000`
   - `lsof -i :8000`
2. Check logs for errors:
   - `logs/backend.log`
   - `logs/frontend.log`
   - `logs/watchdog.log` (if using the watchdog)
3. Ensure PostgreSQL is running (e.g. `brew services start postgresql` on macOS). If the database is down, the backend will return 503 and the app will not load data.
