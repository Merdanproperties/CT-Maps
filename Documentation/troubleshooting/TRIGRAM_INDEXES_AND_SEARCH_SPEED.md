# Trigram Indexes and Search Speed

## Do I have trigram indexes?

Trigram indexes speed up `ILIKE '%...%'` on `address`, `municipality`, `owner_name`, and `owner_address`. They **do not** get created automatically when you start Docker.

**Apply them (Docker):**
```bash
./scripts/apply_trigram_indexes_in_docker.sh
```

**Verify they exist:**
```bash
docker compose exec postgres psql -U ctmaps -d ct_properties -c "SELECT indexname FROM pg_indexes WHERE tablename = 'properties' AND indexname LIKE '%trgm%';"
```
You should see: `idx_properties_address_trgm`, `idx_properties_municipality_trgm`, `idx_properties_owner_name_trgm`, `idx_properties_owner_address_trgm`.

## Why is search still slow?

Indexes make the **text filter** fast (finding rows that match the address/town/owner). The rest of the request can still dominate:

1. **Search endpoint**
   - **`query.count()`** – counts all matching rows; with many matches this can be heavy even with an index.
   - **OR of 7 conditions** – the search uses `address OR owner_name OR owner_address OR ...`. The planner may use the indexes via bitmap scan, or fall back to a seq scan if it thinks that’s cheaper.
   - **Geometry N+1** – for each result row we run a separate `SELECT ST_AsGeoJSON(geometry)`. With 50–200 rows per page that’s 50–200 extra queries. This often dominates response time more than the initial filter.

2. **Autocomplete (address)**
   - The address subquery can use `idx_properties_address_trgm`.
   - We then **JOIN back to `properties`** to compute `ST_Centroid(geometry)` for each suggestion. That geometry work can be slower than the text match.

3. **First time vs cached**
   - Trigram indexes help the **first** search (they reduce how many rows Postgres scans). They do not cache results; something like Redis would be needed for that.

## What to do

- **Ensure indexes exist:** Run `./scripts/apply_trigram_indexes_in_docker.sh` once (and after any DB restore). Re-run is safe (`IF NOT EXISTS`).
- **After creating indexes:** Run `ANALYZE properties;` (the script does this) so the planner uses the new indexes.
- **If it’s still slow:** The main gains will come from reducing the geometry N+1 (e.g. bulk-fetch geometry or include it in the main query) and/or limiting or approximating the total count. Indexes alone won’t fix those parts.
