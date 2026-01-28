# Docker helper scripts

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

After editing frontend or backend code, rebuild that service so the container picks up changes:

```bash
./scripts/rebuild_frontend.sh   # frontend only
./scripts/rebuild_backend.sh    # backend only
```

Then refresh the browser (frontend) or retry API calls (backend).

## apply_indexes_in_docker.sh

If options endpoints (towns, zoning, unit-types, owner-cities, owner-states) time out or retry, the Postgres in Docker may be missing indexes. Run once (or after restoring DB):

```bash
./scripts/apply_indexes_in_docker.sh
```

Then run `ANALYZE` (optional):  
`docker compose exec postgres psql -U ctmaps -d ct_properties -c "ANALYZE;"`
