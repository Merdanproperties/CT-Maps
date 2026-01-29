# Docker helper scripts

## Live code changes (no rebuild)

`docker-compose.yml` mounts your source so you see changes without rebuilding:

- **Backend**: `./backend` is mounted; uvicorn runs with `--reload` and restarts when you edit Python files.
- **Frontend**: `./frontend/src` and `./frontend/index.html` are mounted; Vite dev server hot-reloads when you edit.

After editing code, refresh the browser (frontend) or wait a few seconds (backend). Rebuild only when you change dependencies (e.g. `package.json`, `requirements-docker.txt`) or Dockerfiles.

## docker_compose_up.sh

Runs `docker compose up --build` with `TMPDIR` set to a writable directory (`$HOME/tmp/docker-build`). Use this if you see:

```
can't access os.tempDir /var/folders/zz/.../T/: permission denied
```

on macOS when building the backend or frontend images. Docker Buildx uses the host temp dir; if that path has restricted permissions, the build fails. Setting `TMPDIR` to a dir you own fixes it.

**Usage:**

```bash
./scripts/docker_compose_up.sh
```

To pass flags (e.g. run in background):

```bash
./scripts/docker_compose_up.sh -d
```

**Manual fix (same effect):**

```bash
mkdir -p "$HOME/tmp/docker-build"
export TMPDIR="$HOME/tmp/docker-build"
docker compose up --build
```

## rebuild_frontend.sh / rebuild_backend.sh

Use these when you change **dependencies or Dockerfiles** (e.g. `package.json`, `requirements-docker.txt`, or Dockerfile). For normal code edits, the mounted source is used and no rebuild is needed.

```bash
./scripts/rebuild_frontend.sh   # frontend only
./scripts/rebuild_backend.sh    # backend only
```

## apply_indexes_in_docker.sh

If options endpoints (towns, zoning, unit-types, owner-cities, owner-states) time out or retry, the Postgres in Docker may be missing indexes. Run once (or after restoring DB):

```bash
./scripts/apply_indexes_in_docker.sh
```

Then run `ANALYZE` (optional):  
`docker compose exec postgres psql -U ctmaps -d ct_properties -c "ANALYZE;"`
