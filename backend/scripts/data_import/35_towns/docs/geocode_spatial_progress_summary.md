# Geocode + Spatial Import — Progress by Town

From `geocode_spatial_import.log`.

**Columns:** Excel+CSV matched = combined records (with address) going into geocoding. Geocoded = addresses that got lat/lon. Spatial match = geocoded addresses matched to a parcel. DB = rows written (inserted + updated).

| # | Town        | Excel+CSV matched | Geocoded     | Spatial match | DB (inserted + updated) |
|---|-------------|-------------------|--------------|---------------|--------------------------|
| 1 | Avon        | 7,820             | 213 / 7,820  | 213 / 213     | 213 (0 ins, 213 upd)     |
| 2 | Bolton      | 2,344             | 1,660 / 2,344| 1,660 / 1,660 | 1,660 (0 ins, 1,660 upd) |
| 3 | Bridgewater | 1,065             | 793 / 1,065  | 793 / 793     | 793 (0 ins, 793 upd)     |
| 4 | Chaplin     | 1,243             | 993 / 1,243  | 993 / 993     | 993 (0 ins, 993 upd)     |
| 5 | Chester     | 1,840             | 1,074 / 1,840| 1,074 / 1,074 | 938 (938 ins, 0 upd)     |
| 6 | Danbury     | 28,188            | *in progress*| —             | —                        |
| 7–35 | (remaining) | —              | —            | —             | *pending*                |

**Completed so far:** 5 towns.

**Totals (towns 1–5):** Excel+CSV 14,312 → Geocoded 4,733 → Spatial 4,733 → DB 4,597 (Chester: 1,074 matched → 938 unique parcels inserted).
