# CT Maps — Technical Architecture

High-level architecture of the application (frontend, backend, database, and external services).

![CT Maps architecture diagram](images/ct-maps-architecture.png)

---

## Stack overview

| Layer        | Technology              | Port (Docker) | Notes |
|-------------|--------------------------|---------------|--------|
| **Client**  | Browser                  | —             | User accesses app at `http://localhost:3000` |
| **Frontend**| React, TypeScript, Vite  | 3000          | Proxies API to backend; Mapbox GL or Leaflet for maps |
| **Backend** | FastAPI (uvicorn)        | 8000          | REST API; in-memory options cache (no Redis yet) |
| **Database**| PostgreSQL 15 + PostGIS | 5432 (host 5433) | `ct_properties`; Property, Sale, geometry |
| **Cache**   | In-memory (OptionsCache) | —             | Towns, zoning, unit types; 10 min TTL. Redis optional/future. |
| **Maps**    | Mapbox or OpenStreetMap  | External      | Tiles + geocoding when Mapbox token is set |

---

## Request flow

1. **Browser** → **Frontend** (HTTP, port 3000).
2. **Frontend** → **Backend** (Vite proxy `/api` → `http://backend:8000`).
3. **Backend** → **PostgreSQL** (SQLAlchemy, PostGIS for geometry).
4. **Frontend** → **Mapbox / OSM** (map tiles; Mapbox when token present, else Leaflet/OSM).

---

## Backend API routes

- **properties** — List, get by id/parcel, update, comments.
- **search** — Full-text and filtered search, pagination, GeoJSON.
- **filters** — Zoning and unit-type options (cached).
- **autocomplete** — Address/town/owner suggestions (towns cached).
- **export** — Excel/CSV export.
- **analytics** — Usage/analytics (in-memory store; production would use Redis or DB).
- **remediation** — Auto-fix / remediation endpoints.

---

## Data

- **PostgreSQL + PostGIS**: Property records, geometry (`geometry` column), Sales, PropertyComment. PostGIS used for `ST_AsGeoJSON`, centroids, spatial queries.
- **Options cache**: In-memory, 10 min TTL; shared across requests in one process. Redis would add shared cache across instances and optional response caching (e.g. property detail, autocomplete).

---

## Deployment (Docker)

- `docker compose up` runs: **postgres** (PostGIS 15), **backend** (FastAPI with reload), **frontend** (Vite dev server).
- Backend connects to `postgres:5432`; host exposes Postgres on **5433** to avoid conflict with local Postgres.
- Source is mounted so code changes apply without full rebuild.

For more on running the stack, see [DOCKER_AND_LOCAL_OPERATIONS.md](guides/DOCKER_AND_LOCAL_OPERATIONS.md) and [scripts/README-Docker.md](../scripts/README-Docker.md).
