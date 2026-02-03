# Batch 1 Results — Discrepancy Analysis

## Funnel by town (Excel+CSV → Geocoded → Spatial → DB)

| Town        | Excel+CSV | Geocoded | Geocode % | Spatial | DB (ins+upd) | DB vs Excel+CSV |
|-------------|-----------|----------|-----------|---------|--------------|------------------|
| Avon        | 7,820     | 213      | **2.7%**  | 213     | 213          | **2.7%**         |
| Bolton      | 2,344     | 1,660    | 70.8%     | 1,660   | 1,660        | 70.8%            |
| Bridgewater | 1,065     | 793      | 74.5%     | 793     | 793          | 74.5%            |
| Chaplin     | 1,243     | 993      | 79.9%     | 993     | 993          | 79.9%            |
| Chester     | 1,840     | 1,074    | 58.4%     | 1,074   | 938          | 51.0%            |
| Danbury     | 28,188    | 15,663   | 55.6%     | 15,663  | 13,312       | 47.2%            |
| Enfield     | 15,968    | 12,513   | 78.4%     | 12,513  | 12,013       | 75.2%            |
| Essex       | 3,431     | 2,124    | 61.9%     | 2,124   | 1,976        | 57.6%            |
| Hartford    | 28,356    | 10,548   | **37.2%** | 10,548  | 10,030       | **35.4%**        |
| **Batch 1 total** | **89,247** | **45,571** | **51.0%** | **45,571** | **42,028** | **47.1%** |

(Hartland skipped — no cleaned Excel.)

---

## Where the discrepancy comes from

### 1. **Geocoding (main loss)**

- **~49% of records never get coordinates** (89,247 → 45,571 geocoded). Nominatim returns nothing for many addresses.
- **Avon is an extreme outlier:** 2.7% geocoded (213 of 7,820). Suggests address format or locality handling for Avon is bad for Nominatim.
- **Hartford** is also low: 37.2% geocoded (urban, non-standard or abbreviated addresses likely).
- Towns with **70–80%** geocoded (Bolton, Bridgewater, Chaplin, Enfield) show that higher rates are possible when addresses are cleaner or more standard.

So the **primary** discrepancy is **Excel+CSV → Geocoded**: we lose roughly half the records at Nominatim.

### 2. **Spatial → DB (smaller loss)**

- **Spatial match is 100%** for all towns (every geocoded address matched to some parcel).
- **DB rows < spatial** when several addresses match the **same** parcel (one row per parcel). Examples:
  - Chester: 1,074 spatial → 938 DB (136 duplicate parcel_ids).
  - Danbury: 15,663 → 13,312 (2,351 duplicate parcel_ids).
- This is expected and much smaller than the geocoding loss.

---

## Root cause (high discrepancy)

1. **Nominatim fails on many addresses**  
   - Address format (abbreviations, missing street type, “ARTS CENTER LANE” style names).  
   - “CT” vs “Connecticut” (we retry Connecticut; still many failures).  
   - Local Nominatim data/coverage may miss or rank CT addresses poorly.

2. **Avon (2.7%)**  
   - Likely a mix of: addresses that don’t parse well, or a few bad patterns that repeat.  
   - Worth inspecting a sample of **failed** Avon addresses (from cleaned Excel) to see common patterns.

3. **Urban / large towns (Hartford, Danbury)**  
   - More non-standard or multi-unit addresses, so geocode rate drops.

---

## Recommendations to reduce discrepancy

1. **Improve address normalization before geocoding**  
   - Expand abbreviations (ST → STREET, AVE → AVENUE).  
   - Ensure “123 Main Street” style (number + street + type).  
   - Strip or normalize units (APT 2, #3) and retry without unit if first attempt fails.

2. **Inspect failed addresses**  
   - Export a sample of addresses that **did not** geocode (e.g. Avon, Hartford) and compare with ones that did.  
   - Use that to tune normalization and query format.

3. **Fallback geocoder**  
   - Use a second source (e.g. US Census Geocoder, free for US addresses) when Nominatim returns no result.  
   - Can significantly improve coverage without changing the rest of the pipeline.

4. **Per-town or per-region checks**  
   - For towns with very low geocode % (e.g. Avon 2.7%), consider:  
     - Running with improved normalization only, or  
     - Trying a different geocoder first for that town.

5. **Accept current pipeline as “best effort”**  
   - If 47% of Excel+CSV records making it to DB is acceptable for the 35-town geocode_spatial flow, no code change needed.  
   - If not, the lever is **geocoding** (normalization + fallback), not spatial match or DB logic.

---

## Summary

| Stage              | Loss (batch 1)        | Main cause                          |
|--------------------|------------------------|-------------------------------------|
| Excel+CSV → Geocoded| **~49%** (51% geocoded)| Nominatim returns no result         |
| Geocoded → Spatial | 0%                     | All geocoded match a parcel         |
| Spatial → DB       | ~8%                    | Multiple addresses → same parcel_id |
| **Overall**        | **~53%** (47% in DB)   | Dominated by geocoding              |

**Next step:** Decide whether to invest in better address normalization and/or a fallback geocoder to raise the Excel+CSV → DB rate, or to keep the current setup and document that ~47% is expected for this flow.
