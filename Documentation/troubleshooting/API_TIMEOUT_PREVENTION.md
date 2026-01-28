# API Timeout Prevention — Why It Works and How to Avoid It

This doc explains why the "timeout of 30000ms exceeded" errors on options/autocomplete endpoints were fixed and how to avoid the same issue in the future.

---

## What Was Failing

The frontend was logging timeouts on:

- `/api/autocomplete/towns`
- `/api/search/unit-types/options`
- `/api/search/zoning/options`
- `/api/autocomplete/owner-cities`
- `/api/autocomplete/owner-states`

These endpoints run heavy `SELECT DISTINCT`-style queries on a large `properties` table. Without safeguards, they could run for 30+ seconds and hit the frontend’s Axios timeout.

---

## Why It Works Now

1. **Backend in Docker must run the latest code**  
   The fix only takes effect after the backend container is **rebuilt and restarted**. Until then, the old image (no cache, no statement timeout) keeps running. After `./scripts/rebuild_backend.sh`, the new code is in the container and timeouts stop.

2. **In-memory options cache** (`services/options_cache.py`)  
   Responses for towns, zoning, unit-types, owner-cities, and owner-states are cached for **10 minutes** per (endpoint + filter params). The first request for a given combination may still hit the DB; all subsequent requests for that combination are served from memory and return quickly. No Redis or other service required.

3. **PostgreSQL `statement_timeout` (10s)**  
   Each of these endpoints sets `statement_timeout = '10s'` for its query. If the query exceeds 10 seconds, Postgres cancels it and the backend returns an empty list (or empty response) instead of hanging. The frontend therefore gets a response within ~10s instead of waiting 30s and timing out.

4. **Efficient queries**  
   Options/towns endpoints use `with_entities(...).distinct()` so the DB does `SELECT DISTINCT` on only the needed columns instead of loading full rows. That reduces data transfer and CPU.

5. **Frontend timeout increased to 60s**  
   The API client timeout was raised from 30s to 60s so that when the backend is under load or the first (uncached) request is slow, the client doesn’t give up before the backend responds (or returns empty after 10s).

6. **Health check display**  
   The "Database temporarily unavailable; backend is reachable" banner only shows when the health check explicitly reports `database === 'disconnected'`, not on initial "unknown" state, so users don’t see a false warning on load.

---

## How to Avoid the Same Error Moving Forward

### 1. **Always rebuild backend after backend code changes (Docker)**

When you change backend code (routes, services, models, etc.) and the app runs in Docker:

```bash
./scripts/rebuild_backend.sh
```

This rebuilds the backend image and restarts the backend container. **If you skip this, the running container keeps using the old image** and fixes (cache, timeouts, new routes) won’t apply. That was the main reason timeouts persisted until the container was rebuilt.

### 2. **Confirm deployment**

After rebuilding:

- `docker compose ps` — backend should be **Up** and **(healthy)**.
- Open the app, open DevTools → Network/Console: options and autocomplete requests should return **200** (and often fast after the first load due to cache).

### 3. **If timeouts return**

- **Rebuild first:** `./scripts/rebuild_backend.sh` in case a previous deploy didn’t complete.
- **Check backend CPU:** High CPU can slow all requests. See *Diagnostics* in `Documentation/guides/DOCKER_AND_LOCAL_OPERATIONS.md`.
- **Check DB:** Slow or stuck queries can still trigger the 10s statement timeout (backend returns empty). Check Postgres logs and consider indexes/ANALYZE if options endpoints often return empty under load.
- **Cache TTL:** Options cache is 10 minutes. If you need fresher data, reduce `DEFAULT_TTL_SECONDS` in `backend/services/options_cache.py` (or add a cache-clear endpoint for admin use).

### 4. **Indexes**

The `Property` model already defines indexes used by these queries (e.g. `municipality`, `zoning`, `owner_city`, `owner_state`, `property_type`, `land_use`). After large data imports, run `ANALYZE` so the planner can use them:

```bash
docker compose exec postgres psql -U ctmaps -d ct_properties -c "ANALYZE;"
```

### 5. **Logging (optional)**

If you want to see when the 10s statement timeout is hit (backend returning empty due to slow query), add or keep logging in the `except OperationalError` blocks in `autocomplete.py` and `search.py` so you can tune queries or indexes.

---

## Quick Reference

| What you changed      | What to do (Docker)           |
|-----------------------|-------------------------------|
| Backend Python code   | `./scripts/rebuild_backend.sh` |
| Frontend code         | `./scripts/rebuild_frontend.sh` or refresh if dev server is running |
| Only data (no code)   | `docker compose restart backend` (optional; backend will see new data on next query) |
