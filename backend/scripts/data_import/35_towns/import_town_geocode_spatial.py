"""
Import remaining towns (no Location column in geodatabase) using geocode + spatial match.
Uses: cleaned Excel + CSV for CAMA/address; local Nominatim for geocoding; FileGDB for parcels.
Writes to same properties table as 132-town import. Batch mode: 10 towns per batch, approve to continue.

Use towns_35_geocode_spatial.txt in this folder for towns with No/Low Location per Location Analysis Report (includes Avon; excludes Bridgeport, Middletown—those use import_town_optimized in 134_towns/).

Run from project root with live progress:
  # 36 towns (recommended list):
  PYTHONUNBUFFERED=1 python3 backend/scripts/data_import/35_towns/import_town_geocode_spatial.py --towns-file backend/scripts/data_import/35_towns/towns_35_geocode_spatial.txt 2>&1 | tee geocode_spatial_import.log

  # Start from a specific town (e.g. after Hebron succeeded):
  PYTHONUNBUFFERED=1 python3 backend/scripts/data_import/35_towns/import_town_geocode_spatial.py --towns-file backend/scripts/data_import/35_towns/towns_35_geocode_spatial.txt --start-from-town Killingly 2>&1 | tee geocode_batch2.log

  In another terminal: tail -f geocode_spatial_import.log

Prerequisites: Local Nominatim running (e.g. Docker on http://localhost:8080).

To run all towns without pausing: use --no-approval (24/7 run). To stop: create STOP_IMPORT.txt in this folder.
To continue between batches (default): create APPROVE_NEXT_BATCH.txt in this folder.

Re-runs: Geocode cache (logs/geocode_cache) and spatial cache (logs/spatial_cache) make re-runs faster.
Geocode debug: One Excel per town in logs/geocode_debug with all success and all failure rows (no row limits).
"""
import sys
import os
import re
import time
import json
import hashlib
import argparse
import threading
import signal
import subprocess
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2 import WKTElement
from geopandas import GeoSeries
from shapely import force_2d

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# #region agent log
DEBUG_LOG_PATH = Path("/Users/jacobmermelstein/Desktop/CT Maps/.cursor/debug.log")
def _debug_log(message: str, data: dict, hypothesis_id: str = "Z"):
    try:
        import json as _j
        with open(DEBUG_LOG_PATH, "a") as f:
            f.write(_j.dumps({"message": message, "data": data, "hypothesisId": hypothesis_id, "timestamp": time.time(), "sessionId": "geocode-spatial"}) + "\n")
    except Exception:
        pass
# #endregion

from models import Property, Base
from database import engine, SessionLocal
from scripts.data_import.import_bridgeport_cama_2025 import (
    read_cleaned_excel,
    read_raw_csv,
    match_and_combine,
    map_to_database_fields,
    normalize_address,
)

# Paths
DEFAULT_DATA_DIR = Path("/Users/jacobmermelstein/Desktop/CT Data")
GDB_PATH = Path("/Users/jacobmermelstein/Desktop/CT Maps/2025 Parcel Layer.gdb")
SCRIPT_DIR = Path(__file__).parent
# Logs and caches go under 35_towns/logs (geocode_cache, geocode_debug, spatial_cache)
CACHE_DIR = SCRIPT_DIR / "logs"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
GEOCODE_CACHE_DIR = CACHE_DIR / "geocode_cache"
GEOCODE_DEBUG_DIR = CACHE_DIR / "geocode_debug"
SPATIAL_CACHE_DIR = CACHE_DIR / "spatial_cache"
for _d in (GEOCODE_CACHE_DIR, GEOCODE_DEBUG_DIR, SPATIAL_CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)
MAX_DISTANCE_METERS = 200.0

# All 169 CT towns (standardized names) for normalization
ALL_169_CT_TOWNS = [
    "Andover", "Ansonia", "Ashford", "Avon", "Barkhamsted", "Beacon Falls",
    "Berlin", "Bethany", "Bethel", "Bethlehem", "Bloomfield", "Bolton",
    "Bozrah", "Branford", "Bridgeport", "Bridgewater", "Bristol", "Brookfield",
    "Brooklyn", "Burlington", "Canaan", "Canterbury", "Canton", "Chaplin",
    "Cheshire", "Chester", "Clinton", "Colchester", "Colebrook", "Columbia",
    "Cornwall", "Coventry", "Cromwell", "Danbury", "Darien", "Deep River",
    "Derby", "Durham", "East Granby", "East Haddam", "East Hampton", "East Hartford",
    "East Haven", "East Lyme", "East Windsor", "Eastford", "Easton", "Ellington",
    "Enfield", "Essex", "Fairfield", "Farmington", "Franklin", "Glastonbury",
    "Goshen", "Granby", "Greenwich", "Griswold", "Groton", "Guilford",
    "Haddam", "Hamden", "Hampton", "Hartford", "Hartland", "Harwinton",
    "Hebron", "Kent", "Killingly", "Killingworth", "Lebanon", "Ledyard",
    "Lisbon", "Litchfield", "Lyme", "Madison", "Manchester", "Mansfield",
    "Marlborough", "Meriden", "Middlebury", "Middlefield", "Middletown", "Milford",
    "Monroe", "Montville", "Morris", "Naugatuck", "New Britain", "New Canaan",
    "New Fairfield", "New Hartford", "New Haven", "New London", "New Milford",
    "Newington", "Newtown", "Norfolk", "North Branford", "North Canaan", "North Haven",
    "North Stonington", "Norwalk", "Norwich", "Old Lyme", "Old Saybrook", "Orange",
    "Oxford", "Plainfield", "Plainville", "Plymouth", "Pomfret", "Portland",
    "Preston", "Prospect", "Putnam", "Redding", "Ridgefield", "Rocky Hill",
    "Roxbury", "Salem", "Salisbury", "Scotland", "Seymour", "Sharon",
    "Shelton", "Sherman", "Simsbury", "Somers", "South Windsor", "Southbury",
    "Southington", "Sprague", "Stafford", "Stamford", "Sterling", "Stonington",
    "Stratford", "Suffield", "Thomaston", "Thompson", "Tolland", "Torrington",
    "Trumbull", "Union", "Vernon", "Voluntown", "Wallingford", "Warren",
    "Washington", "Waterbury", "Waterford", "Watertown", "West Hartford", "West Haven",
    "Westbrook", "Weston", "Westport", "Wethersfield", "Willington", "Wilton",
    "Winchester", "Windham", "Windsor", "Windsor Locks", "Wolcott", "Woodbridge",
    "Woodbury", "Woodstock",
]


def normalize_municipality(municipality: str) -> Optional[str]:
    """Normalize municipality to standard Title Case (match 134-town script)."""
    if not municipality or (hasattr(pd, "isna") and pd.isna(municipality)):
        return None
    name = str(municipality).strip()
    if "REVAL" in name:
        name = name.replace("REVAL", "").strip()
    if "STATIC" in name or "DATA BASE" in name:
        return None
    if name.split() and name.split()[0].isdigit():
        return None
    parts = name.split()
    if len(parts) > 1 and parts[-1].isdigit() and len(parts[-1]) == 4:
        name = " ".join(parts[:-1])
    abbreviation_map = {"e berlin": "East Berlin", "s glastonbury": "Glastonbury", "n glastonbury": "Glastonbury", "w glastonbury": "Glastonbury"}
    name_lower = name.lower()
    if name_lower in abbreviation_map:
        return abbreviation_map[name_lower]
    typo_corrections = {"kensjngton": "Kensington", "sxouthington": "Southington", "bristtol": "Bristol", "wallinfdord": "Wallingford", "milfrd": "Milford", "woobridge": "Woodbridge", "barkhamstead": "Barkhamsted", "winsted": "Winchester"}
    if name_lower in typo_corrections:
        return typo_corrections[name_lower]
    for town in ALL_169_CT_TOWNS:
        if town.lower() == name_lower:
            return town
    normalized_input = " ".join(name.split())
    for town in ALL_169_CT_TOWNS:
        if town.lower() == normalized_input.lower():
            return town
    return normalized_input.title()


# Nominatim (local Docker)
NOMINATIM_URL = os.getenv("NOMINATIM_URL", "http://localhost:8080")


def _check_nominatim_reachable() -> bool:
    """Return True if Nominatim at NOMINATIM_URL is reachable (for geocoding)."""
    url = f"{NOMINATIM_URL.rstrip('/')}/search"
    params = {"q": "1 Main St, Hartford, Connecticut, USA", "format": "json", "limit": 1}
    headers = {"User-Agent": "CT-Maps-Property-Import/1.0"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def _flush():
    sys.stdout.flush()


def load_parcels_for_town(municipality: str):
    """Load parcels for one town from FileGDB; return GeoDataFrame with centroid column (WGS84)."""
    import geopandas as gpd
    from scripts.data_import.matching_and_export.match_to_geodatabase_spatially import (
        get_parcel_centroid,
    )

    if not GDB_PATH.exists():
        raise FileNotFoundError(f"Geodatabase not found: {GDB_PATH}")
    gdf = gpd.read_file(str(GDB_PATH), layer="Full_State_Parcels_25", driver="FileGDB")
    # Exact match on Town_Name so "Chester" doesn't also match Manchester, etc.
    town_norm = municipality.strip()
    town_gdf = gdf[
        gdf["Town_Name"].astype(str).str.strip().str.lower() == town_norm.lower()
    ]
    if len(town_gdf) == 0:
        return None
    source_crs = town_gdf.crs or "EPSG:6434"
    centroids = []
    for idx, row in town_gdf.iterrows():
        cent = get_parcel_centroid(row.geometry, source_crs)
        centroids.append(cent)
    town_gdf = town_gdf.copy()
    town_gdf["centroid"] = centroids
    valid = town_gdf[town_gdf["centroid"].notna()]
    return valid


def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    import math
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _parcel_id_from_row(row, idx) -> str:
    """Same logic as find_nearest_parcel for parcel_id (for cache lookup)."""
    return str(row.get("Parcel_ID", "")).strip() or str(idx)


def _build_parcel_by_id(parcels_gdf):
    """Build parcel_id -> row for cache replay (geometry comes from row)."""
    out = {}
    for idx, row in parcels_gdf.iterrows():
        pid = _parcel_id_from_row(row, idx)
        out[pid] = row
    return out


def find_nearest_parcel(lon: float, lat: float, parcels_gdf, max_m: float = MAX_DISTANCE_METERS) -> Optional[Dict]:
    min_d = float("inf")
    nearest = None
    for idx, row in parcels_gdf.iterrows():
        cent = row["centroid"]
        if cent is None:
            continue
        plon, plat = cent
        d = haversine_m(lon, lat, plon, plat)
        if d < min_d:
            min_d = d
            nearest = {
                "parcel_id": _parcel_id_from_row(row, idx),
                "geometry": row.geometry,
                "distance_meters": d,
                "source_crs": parcels_gdf.crs or "EPSG:6434",
            }
    if nearest and nearest["distance_meters"] > max_m:
        nearest["over_threshold"] = True
    return nearest


def geometry_to_wkt_element(geom, source_crs: str = "EPSG:6434"):
    if geom is None:
        return None
    try:
        gs = GeoSeries([geom], crs=source_crs)
        wgs84 = gs.to_crs("EPSG:4326").iloc[0]
        # DB column is 2D; FileGDB geometries can have Z - strip to avoid InvalidParameterValue
        has_z = getattr(wgs84, "has_z", False)
        if has_z:
            wgs84 = force_2d(wgs84)
            _debug_log("geometry had Z, forced 2D", {"wkt_type": "2D after force_2d"}, "Z")
        wkt = wgs84.wkt
        return WKTElement(wkt, srid=4326)
    except Exception:
        return None


def point_wkt_from_lon_lat(lon: float, lat: float):
    """Return WKTElement for Point(lon, lat), srid=4326."""
    return WKTElement(f"POINT ({lon} {lat})", srid=4326)


def _nominatim_search(query: str, timeout: int = 15) -> Optional[Tuple[float, float]]:
    """Single Nominatim search; returns (lon, lat) or None."""
    url = f"{NOMINATIM_URL.rstrip('/')}/search"
    params = {"q": query, "format": "json", "limit": 1}
    headers = {"User-Agent": "CT-Maps-Property-Import/1.0"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=timeout)
        if r.status_code == 200 and r.json():
            data = r.json()
            return (float(data[0]["lon"]), float(data[0]["lat"]))
    except Exception:
        pass
    return None


# Abbreviations to expand for geocoding (Nominatim often matches full street names better)
_GEOCODE_ABBREV = [
    (r"\bST\b", "STREET"),
    (r"\bAVE\b", "AVENUE"),
    (r"\bRD\b", "ROAD"),
    (r"\bDR\b", "DRIVE"),
    (r"\bLN\b", "LANE"),
    (r"\bCT\b", "COURT"),  # court (not Connecticut)
    (r"\bPL\b", "PLACE"),
    (r"\bBLVD\b", "BOULEVARD"),
    (r"\bPKWY\b", "PARKWAY"),
    (r"\bHWY\b", "HIGHWAY"),
    (r"\bHGWY\b", "HIGHWAY"),
    (r"\bTRL\b", "TRAIL"),
    (r"\bCIR\b", "CIRCLE"),
    (r"\bTER\b", "TERRACE"),
    (r"\bWAY\b", "WAY"),
    (r"\bE\b", "EAST"),
    (r"\bW\b", "WEST"),
    (r"\bN\b", "NORTH"),
    (r"\bS\b", "SOUTH"),
]


def normalize_address_for_geocode(addr: str, strip_units: bool = False) -> str:
    """Normalize address for geocoding: expand street abbreviations, optional strip unit numbers."""
    if not addr or not str(addr).strip():
        return ""
    s = str(addr).strip()
    if strip_units:
        s = re.sub(r"\s*#\s*\d+", "", s)
        s = re.sub(r"\s*(APT|APARTMENT|UNIT|STE|SUITE|FL|FLOOR)\s*\d*\s*", " ", s, flags=re.IGNORECASE)
    for pattern, replacement in _GEOCODE_ABBREV:
        s = re.sub(pattern, replacement, s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def geocode_one(address: str, city: str, state: str = "CT", cache: Dict = None, cache_lock: threading.Lock = None) -> Optional[Tuple[float, float]]:
    """Geocode one address; normalizes (expand abbrevs), retries with Connecticut, then without unit numbers."""
    if not address or not str(address).strip():
        return None
    address = str(address).strip()
    key = f"{address}|{city}"
    if cache is not None:
        with (cache_lock or threading.Lock()):
            if key in cache:
                return tuple(cache[key])

    def save_and_return(coords):
        if coords and cache is not None and cache_lock:
            with cache_lock:
                cache[key] = list(coords)
        return coords

    # Try 1: raw address + city + CT, USA
    coords = _nominatim_search(f"{address}, {city}, {state}, USA")
    if coords:
        return save_and_return(coords)

    # Try 2: raw address + city + Connecticut, USA
    coords = _nominatim_search(f"{address}, {city}, Connecticut, USA")
    if coords:
        return save_and_return(coords)

    # Try 3: normalized (expanded abbreviations) + Connecticut, USA
    normalized = normalize_address_for_geocode(address, strip_units=False)
    if normalized and normalized != address:
        coords = _nominatim_search(f"{normalized}, {city}, Connecticut, USA")
        if coords:
            return save_and_return(coords)

    # Try 4: normalized without unit numbers + Connecticut, USA
    no_units = normalize_address_for_geocode(address, strip_units=True)
    if no_units and no_units != address:
        coords = _nominatim_search(f"{no_units}, {city}, Connecticut, USA")
        if coords:
            return save_and_return(coords)

    # Try 5: simplified (first 6 words) + Connecticut, USA
    words = address.split()
    if len(words) > 6:
        simple = " ".join(words[:6])
        coords = _nominatim_search(f"{simple}, {city}, Connecticut, USA")
        if coords:
            return save_and_return(coords)

    return None


def geocode_records_parallel(
    records: List[Dict],
    municipality: str,
    num_workers: int = 4,
    cache_path: Optional[Path] = None,
    dry_run: bool = False,
    progress_interval: int = 500,
) -> List[Dict]:
    """Add lon/lat to records using parallel geocoding. Cache key: address|town."""
    cache = {}
    if cache_path and cache_path.exists():
        try:
            with open(cache_path, "r") as f:
                cache = json.load(f)
        except Exception:
            cache = {}
    cache_lock = threading.Lock()
    total = len(records)
    done = 0
    failed = 0
    cached = 0

    def task(item):
        i, rec = item
        addr = (rec.get("Property Address") or rec.get("address") or "").strip()
        if not addr:
            return (i, rec, None, "no_address")
        # Normalize key so "123 Main St" and "123 Main St " hit same cache (geocode_one strips before save)
        key = f"{addr}|{municipality}"
        with cache_lock:
            if key in cache:
                return (i, rec, tuple(cache[key]), "cached")
        if dry_run:
            return (i, rec, None, "dry_run")
        coords = geocode_one(addr, municipality, "CT", cache, cache_lock)
        return (i, rec, coords, "geocoded" if coords else "failed")

    results = [None] * total
    with ThreadPoolExecutor(max_workers=num_workers) as ex:
        futures = {ex.submit(task, (i, rec)): i for i, rec in enumerate(records)}
        for fut in as_completed(futures):
            i, rec, coords, status = fut.result()
            if coords:
                rec["lon"] = coords[0]
                rec["lat"] = coords[1]
                rec["geocoded"] = True
            else:
                rec["geocoded"] = False
            results[i] = rec
            done += 1
            if status == "cached":
                cached += 1
            elif status == "failed" or status == "no_address":
                failed += 1
            if done % progress_interval == 0 or done == total:
                print(f"  Geocoding progress: {done:,}/{total:,} | cached: {cached:,} | failed: {failed:,}")
                _flush()

    if cache_path and cache:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(cache, f, indent=0)
    return results


def _delete_old_geocode_debug_files(municipality: str, output_dir: Path) -> None:
    """Remove existing geocode_debug_{town}_*.xlsx so re-runs don't accumulate duplicates."""
    prefix = f"geocode_debug_{municipality.replace(' ', '_')}_"
    for f in output_dir.glob(f"{prefix}*.xlsx"):
        try:
            f.unlink()
        except OSError:
            pass


def export_geocode_skipped_excel(
    municipality: str,
    reason: str,
    output_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Write a one-row Excel for skipped towns so every batch produces output."""
    output_dir = output_dir or CACHE_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _delete_old_geocode_debug_files(municipality, output_dir)
    out_path = output_dir / f"geocode_debug_{municipality.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    df = pd.DataFrame([{"status": "skipped", "town": municipality, "reason": reason, "address": "", "lon": "", "lat": ""}])
    df.to_excel(out_path, index=False, engine="openpyxl")
    print(f"  Geocode debug Excel (skipped): {out_path}")
    _flush()
    return out_path


def export_geocode_debug_excel(
    records: List[Dict],
    municipality: str,
    output_dir: Optional[Path] = None,
    max_failed: Optional[int] = None,
    max_success: Optional[int] = None,
) -> Optional[Path]:
    """Export all failed and successful geocode addresses to Excel (no cap by default)."""
    output_dir = output_dir or CACHE_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _delete_old_geocode_debug_files(municipality, output_dir)

    failed = []
    success = []
    for r in records:
        addr = (r.get("Property Address") or r.get("address") or "").strip()
        if not addr:
            continue
        row = {"status": "failed", "address": addr, "town": municipality, "lon": "", "lat": ""}
        if r.get("geocoded") and "lon" in r and "lat" in r:
            row["status"] = "success"
            row["lon"] = r["lon"]
            row["lat"] = r["lat"]
            success.append(row)
        else:
            failed.append(row)

    n_fail = min(len(failed), max_failed) if max_failed is not None else len(failed)
    n_succ = min(len(success), max_success) if max_success is not None else len(success)
    rows = failed[:n_fail] + success[:n_succ]

    if not rows:
        return None
    out_path = output_dir / f"geocode_debug_{municipality.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    df = pd.DataFrame(rows)
    df.to_excel(out_path, index=False, engine="openpyxl")
    limit_note = " (all rows, no limit)" if max_failed is None and max_success is None else ""
    print(f"  Geocode debug Excel: {out_path} ({n_fail:,} failed, {n_succ:,} success){limit_note}")
    _flush()
    return out_path


def _normalize_address_for_parcel_id(address: str) -> str:
    """Normalize address for stable parcel_id (collapse spaces, strip trailing period)."""
    if not address:
        return "unknown"
    s = (address or "").strip().lower()
    s = " ".join(s.split())  # collapse multiple spaces
    if s.endswith("."):
        s = s[:-1].strip()
    return s or "unknown"


def stable_address_hash(address: str, municipality: str) -> str:
    """Deterministic 16-char hex hash for parcel_id (stable across runs; re-runs = no duplicates)."""
    key = f"{_normalize_address_for_parcel_id(address)}|{municipality}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


def import_town_geocode_spatial(
    municipality: str,
    limit: Optional[int] = None,
    dry_run: bool = False,
    geocode_workers: int = 4,
    town_num: Optional[int] = None,
    town_total: Optional[int] = None,
) -> Dict:
    """Run full pipeline for one town: Excel+CSV -> geocode -> spatial match -> DB."""
    _flush()
    normalized = normalize_municipality(municipality)
    if not normalized:
        return {"town": municipality, "status": "skipped", "reason": f"Invalid municipality name: '{municipality}'"}
    municipality = normalized

    if town_num is not None and town_total is not None:
        print(f"\nTOWN {town_num}/{town_total}: {municipality.upper()}")
    else:
        print(f"\nTOWN: {municipality.upper()}")
    _flush()

    cleaned_path = DEFAULT_DATA_DIR / "2025 Post Duplicate Clean" / f"{municipality}_CAMA_2025_CLEANED.xlsx"
    csv_path = DEFAULT_DATA_DIR / "2025 Parcel Collection" / f"{municipality}_CAMA_2025.csv"
    if not cleaned_path.exists():
        export_geocode_skipped_excel(municipality, f"Cleaned Excel not found: {cleaned_path}", output_dir=GEOCODE_DEBUG_DIR)
        return {"town": municipality, "status": "skipped", "reason": f"Cleaned Excel not found: {cleaned_path}"}
    if not csv_path.exists():
        export_geocode_skipped_excel(municipality, f"CSV not found: {csv_path}", output_dir=GEOCODE_DEBUG_DIR)
        return {"town": municipality, "status": "skipped", "reason": f"CSV not found: {csv_path}"}

    try:
        cleaned_df = read_cleaned_excel(str(cleaned_path), limit=limit)
        raw_df, raw_lookup = read_raw_csv(str(csv_path))
        combined = match_and_combine(cleaned_df, raw_lookup)
    except Exception as e:
        export_geocode_skipped_excel(municipality, f"Failed to load/match: {e}", output_dir=GEOCODE_DEBUG_DIR)
        return {"town": municipality, "status": "failed", "error": str(e)}

    if limit:
        combined = combined[:limit]
    addresses = [
        (r.get("Property Address") or r.get("address") or "").strip()
        for r in combined
    ]
    combined = [r for r in combined if (r.get("Property Address") or r.get("address") or "").strip()]
    if not combined:
        export_geocode_skipped_excel(municipality, "No addresses in combined records", output_dir=GEOCODE_DEBUG_DIR)
        return {"town": municipality, "status": "skipped", "reason": "No addresses in combined records"}

    print(f"  Loaded {len(combined):,} records (Excel+CSV matched)")
    _flush()

    cache_path = GEOCODE_CACHE_DIR / f"geocode_cache_{municipality.replace(' ', '_')}.json"
    combined = geocode_records_parallel(
        combined,
        municipality,
        num_workers=geocode_workers,
        cache_path=cache_path,
        dry_run=dry_run,
    )
    geocoded = [r for r in combined if r.get("geocoded") and "lon" in r and "lat" in r]
    print(f"  Geocoded: {len(geocoded):,}/{len(combined):,}")
    _flush()

    export_geocode_debug_excel(combined, municipality, output_dir=GEOCODE_DEBUG_DIR)

    if not geocoded:
        # Excel already written above (all failed)
        return {"town": municipality, "status": "skipped", "reason": "No addresses geocoded"}

    parcels_gdf = load_parcels_for_town(municipality)
    matched = []
    source_crs = "EPSG:4326"
    if parcels_gdf is None or len(parcels_gdf) == 0:
        print(f"  No parcels; using point for all {len(geocoded):,} geocoded.")
        _flush()
    else:
        print(f"  Loaded {len(parcels_gdf):,} parcels from geodatabase")
        _flush()
        source_crs = str(parcels_gdf.crs or "EPSG:6434")
        parcel_by_id = _build_parcel_by_id(parcels_gdf)
        spatial_cache_path = SPATIAL_CACHE_DIR / f"spatial_cache_{municipality.replace(' ', '_')}.json"
        spatial_cache = {}
        if spatial_cache_path.exists():
            try:
                with open(spatial_cache_path, "r") as f:
                    spatial_cache = json.load(f)
            except Exception:
                spatial_cache = {}
        n_geo = len(geocoded)
        spatial_cached = 0
        for i, r in enumerate(geocoded):
            lon, lat = r["lon"], r["lat"]
            key = f"{round(lon, 6)},{round(lat, 6)}"
            nearest = None
            if key in spatial_cache:
                ent = spatial_cache[key]
                pid, d = ent["p"], float(ent["d"])
                if pid in parcel_by_id:
                    row = parcel_by_id[pid]
                    nearest = {
                        "parcel_id": pid,
                        "geometry": row.geometry,
                        "distance_meters": d,
                        "source_crs": source_crs,
                    }
                    if d > MAX_DISTANCE_METERS:
                        nearest["over_threshold"] = True
                    spatial_cached += 1
            if nearest is None:
                nearest = find_nearest_parcel(lon, lat, parcels_gdf)
                if nearest:
                    spatial_cache[key] = {"p": nearest["parcel_id"], "d": nearest["distance_meters"]}
            if nearest:
                r["_matched_parcel_id"] = nearest["parcel_id"]
                r["_matched_geometry"] = nearest["geometry"]
                r["_matched_source_crs"] = source_crs
                r["_matched_distance"] = nearest["distance_meters"]
                matched.append(r)
            if (i + 1) % 500 == 0 or (i + 1) == n_geo:
                print(f"  Spatial match progress: {i + 1:,}/{n_geo:,} | matched: {len(matched):,} | cached: {spatial_cached:,}")
                _flush()
        if spatial_cache:
            SPATIAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(spatial_cache_path, "w") as f:
                json.dump(spatial_cache, f, indent=0)
        print(f"  Spatial match: {len(matched):,}/{len(geocoded):,} matched to parcel (cached: {spatial_cached:,})")
        n_point = len(geocoded) - len(matched)
        print(f"  Geocoded: {len(geocoded):,} records ({len(matched):,} polygon, {n_point:,} point). One DB row per unique address.")
        _flush()

    if dry_run:
        return {"town": municipality, "status": "dry_run", "geocoded": len(geocoded), "matched": len(matched), "inserted": 0, "updated": 0}

    db = SessionLocal()
    try:
        # Re-runs safe: existing rows are updated by parcel_id; no duplicate inserts.
        existing_parcels = set()
        res = db.query(Property.parcel_id).filter(
            func.lower(Property.municipality) == municipality.lower(),
        ).all()
        existing_parcels = {str(r[0]).strip() for r in res if r[0]}
        print(f"  Found {len(existing_parcels):,} existing properties in database")
        _flush()

        to_insert = []
        to_update = []
        seen_parcel_ids = set()  # De-dup within this batch (no duplicate parcel_id in same run)
        for i, r in enumerate(geocoded):
            db_record = map_to_database_fields(r)
            db_record.pop("municipality", None)
            db_record["address"] = db_record.get("address") or r.get("Property Address") or ""
            addr = db_record["address"]

            parcel_id = f"{municipality}_{stable_address_hash(addr, municipality)}"

            geom = r.get("_matched_geometry")
            if geom is not None:
                geom_wkt = geometry_to_wkt_element(geom, source_crs)
            else:
                geom_wkt = point_wkt_from_lon_lat(r["lon"], r["lat"])
            if not geom_wkt:
                continue

            if parcel_id in seen_parcel_ids:
                continue
            seen_parcel_ids.add(parcel_id)

            if parcel_id in existing_parcels:
                existing = db.query(Property).filter(
                    Property.parcel_id == parcel_id,
                    func.lower(Property.municipality) == municipality.lower(),
                ).first()
                if existing:
                    # Don't update if municipality differs (would move property between towns)
                    if existing.municipality and existing.municipality.lower() != municipality.lower():
                        continue
                    upd = {"id": existing.id, "geometry": geom_wkt, "municipality": municipality}
                    for k, v in db_record.items():
                        if k != "parcel_id" and v is not None and (not isinstance(v, str) or v.strip()):
                            upd[k] = v
                    to_update.append(upd)
            else:
                to_insert.append({
                    "parcel_id": parcel_id,
                    "geometry": geom_wkt,
                    "municipality": municipality,
                    "data_source": f"{municipality} CAMA 2025 (Geocode+Spatial)",
                    "last_updated": date.today(),
                    **db_record,
                })
                existing_parcels.add(parcel_id)

        n_unique = len(to_insert) + len(to_update)
        n_skipped = len(geocoded) - n_unique
        print(f"  {n_unique:,} unique addresses → {n_unique:,} DB rows." + (f" ({n_skipped:,} duplicate addresses skipped.)" if n_skipped else ""))
        _flush()

        inserted = 0
        updated = 0
        BATCH = 500
        for i in range(0, len(to_insert), BATCH):
            batch = to_insert[i : i + BATCH]
            try:
                db.bulk_insert_mappings(Property, batch)
                db.commit()
                inserted += len(batch)
            except Exception as e:
                db.rollback()
                print(f"  ⚠️  Batch insert failed, using individual inserts for batch {i // BATCH + 1}...")
                _flush()
                for prop_data in batch:
                    try:
                        existing_global = db.query(Property).filter(
                            Property.parcel_id == prop_data["parcel_id"],
                        ).first()
                        if existing_global:
                            if existing_global.municipality and existing_global.municipality.lower() == municipality.lower():
                                for key, value in prop_data.items():
                                    if key != "parcel_id":
                                        setattr(existing_global, key, value)
                            else:
                                continue
                        else:
                            db.add(Property(**prop_data))
                            inserted += 1
                    except Exception as ex:
                        error_str = str(ex).lower()
                        if "duplicate" in error_str or "unique" in error_str or "already exists" in error_str:
                            if inserted < 10:
                                print(f"    ⚠️  Skipped duplicate: {prop_data.get('parcel_id', 'unknown')}")
                        else:
                            if inserted < 10:
                                print(f"    ⚠️  Error inserting {prop_data.get('parcel_id', 'unknown')}: {ex}")
                db.commit()
        for i in range(0, len(to_update), BATCH):
            batch = to_update[i : i + BATCH]
            for row in batch:
                db.query(Property).filter(Property.id == row["id"]).update(
                    {k: v for k, v in row.items() if k != "id"},
                    synchronize_session=False,
                )
            db.commit()
            updated += len(batch)

        print(f"  DB: inserted {inserted:,}, updated {updated:,}")
        _flush()

        # Verify town is in DB with at least the unique rows we wrote (matched may have duplicate parcel_ids)
        unique_updates = len({row["id"] for row in to_update})
        expected_count = len(to_insert) + unique_updates
        db_count = db.query(Property).filter(func.lower(Property.municipality) == municipality.lower()).count()
        if db_count < expected_count:
            return {
                "town": municipality,
                "status": "failed",
                "error": f"DB verification failed: {municipality} has {db_count:,} rows in DB, expected at least {expected_count:,}",
                "inserted": inserted,
                "updated": updated,
                "matched": len(matched),
                "db_count": db_count,
            }
        print(f"  Verified: {municipality} has {db_count:,} rows in DB")
        _flush()
        return {"town": municipality, "status": "success", "inserted": inserted, "updated": updated, "matched": len(matched)}
    finally:
        db.close()


def _kill_other_import_processes():
    """Kill any other running instances of this script to avoid duplicate runs."""
    try:
        my_pid = os.getpid()
        out = subprocess.run(
            ["pgrep", "-f", "import_town_geocode_spatial.py"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode != 0 or not out.stdout:
            return
        killed = []
        for line in out.stdout.strip().splitlines():
            try:
                pid = int(line.strip())
                if pid != my_pid:
                    os.kill(pid, signal.SIGTERM)
                    killed.append(pid)
            except (ValueError, ProcessLookupError, PermissionError):
                pass
        if killed:
            print(f"Killed {len(killed)} other import process(es): PIDs {killed}")
            _flush()
            time.sleep(2)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Import towns via geocode + spatial match (no Location column)")
    parser.add_argument("--town", type=str, help="Single town name")
    parser.add_argument("--towns-file", type=str, help="Path to file with one town per line")
    parser.add_argument("--start-batch", type=int, default=1, help="Start from batch N (1-based) when using --towns-file")
    parser.add_argument("--start-from-town", type=str, help="Start from this town (inclusive), e.g. Killingly; overrides --start-batch")
    parser.add_argument("--limit", type=int, default=None, help="Limit records per town (for testing)")
    parser.add_argument("--dry-run", action="store_true", help="No DB writes, no geocoding (cache only)")
    parser.add_argument("--geocode-workers", type=int, default=4, help="Parallel geocoding workers (default 4, max 8)")
    parser.add_argument("--no-approval", action="store_true", help="Run all towns without waiting for approval between batches (24/7 run)")
    args = parser.parse_args()
    geocode_workers = max(1, min(8, args.geocode_workers))

    # Ensure no other instance of this script is running (avoid duplicate runs)
    _kill_other_import_processes()

    if args.town:
        result = import_town_geocode_spatial(
            args.town,
            limit=args.limit,
            dry_run=args.dry_run,
            geocode_workers=geocode_workers,
        )
        print("\nResult:", result)
        return

    if not args.towns_file or not Path(args.towns_file).exists():
        print("Provide --town NAME or --towns-file PATH (file must exist)")
        sys.exit(1)

    with open(args.towns_file, "r") as f:
        all_towns = [line.strip() for line in f if line.strip()]
    BATCH_SIZE = 10
    total_towns = len(all_towns)
    skip = 0
    if args.start_from_town:
        want = args.start_from_town.strip()
        idx = next((i for i, t in enumerate(all_towns) if t.lower() == want.lower()), None)
        if idx is None:
            print(f"Town '{want}' not found in towns file. Available: {', '.join(all_towns[:5])}...")
            sys.exit(1)
        skip = idx
        towns = all_towns[skip:]
        start_batch = (skip // BATCH_SIZE) + 1
        print(f"Starting from town: {want} (town {skip + 1}/{total_towns})")
    else:
        start_batch = max(1, args.start_batch)
        skip = (start_batch - 1) * BATCH_SIZE
        towns = all_towns[skip:] if skip > 0 else all_towns
    total_batches = (len(towns) + BATCH_SIZE - 1) // BATCH_SIZE

    print("=" * 80)
    print("GEOCODE + SPATIAL IMPORT: Remaining towns (no Location column)")
    print("=" * 80)
    print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Towns in file: {total_towns} | Batches: {total_batches} | Geocode workers: {geocode_workers}")
    if skip > 0 and not args.start_from_town:
        print(f"Starting from batch {start_batch} (skipping first {skip} towns)")
    print()
    _flush()

    if not _check_nominatim_reachable():
        print("ERROR: Nominatim is not reachable. Geocoding will fail for all addresses.")
        print(f"  URL: {NOMINATIM_URL}")
        print("  Start local Nominatim (e.g. Docker on port 8080) or set NOMINATIM_URL, then re-run.")
        sys.exit(1)
    print("Nominatim OK (geocoding available)")
    print("Re-runs: geocode + spatial caches will speed up. Geocode debug Excel: all success/failure rows, no limits.")
    _flush()

    results = {"success": [], "failed": [], "skipped": []}
    stop_file = SCRIPT_DIR / "STOP_IMPORT.txt"
    for batch_num in range(total_batches):
        if args.no_approval and stop_file.exists():
            print("\nStop file detected - import stopped.")
            stop_file.unlink(missing_ok=True)
            sys.exit(0)
        batch_start = batch_num * BATCH_SIZE
        batch_end = min(batch_start + BATCH_SIZE, len(towns))
        batch_towns = towns[batch_start:batch_end]
        first_num = skip + batch_start + 1
        last_num = skip + batch_end

        print("\n" + "=" * 80)
        print(f"BATCH {batch_num + 1}/{total_batches}  (towns {first_num}-{last_num} of {total_towns})")
        print("=" * 80)
        print(f"Processing: {', '.join(batch_towns)}")
        _flush()

        batch_success = []
        batch_skipped = []
        batch_failed = []
        for i, town in enumerate(batch_towns):
            town_num = skip + batch_start + i + 1
            r = import_town_geocode_spatial(
                town,
                limit=args.limit,
                dry_run=args.dry_run,
                geocode_workers=geocode_workers,
                town_num=town_num,
                town_total=total_towns,
            )
            if r.get("status") == "success":
                batch_success.append(r)
                results["success"].append(r)
            elif r.get("status") == "skipped":
                batch_skipped.append(r)
                results["skipped"].append(r)
            else:
                batch_failed.append(r)
                results["failed"].append(r)
                print(f"\n  Failed (continuing): {r.get('town')} — {str(r.get('error', ''))[:100]}")
                _flush()
                # Continue to next town; failed towns will be summarized at end

        # Whole-batch summary (always before moving to next batch or waiting for approval)
        print("\n" + "=" * 80)
        print(f"BATCH {batch_num + 1}/{total_batches} — WHOLE BATCH RESULTS (summary before next batch)")
        print("=" * 80)
        batch_inserted = sum(r.get("inserted", 0) or 0 for r in batch_success)
        batch_updated = sum(r.get("updated", 0) or 0 for r in batch_success)
        for r in batch_success:
            ins, upd = r.get("inserted", 0) or 0, r.get("updated", 0) or 0
            print(f"  Success: {r.get('town')}  inserted={ins:,}  updated={upd:,}  matched={r.get('matched', 0):,}")
        for s in batch_skipped:
            print(f"  Skipped: {s.get('town')}  reason: {s.get('reason', '')[:70]}")
        for f in batch_failed:
            print(f"  Failed:  {f.get('town')}  error: {str(f.get('error', ''))[:70]}")
        print("-" * 80)
        print(f"  This batch: Success={len(batch_success)}  Skipped={len(batch_skipped)}  Failed={len(batch_failed)}  |  DB: inserted={batch_inserted:,}  updated={batch_updated:,}")
        cum_success = len(results["success"])
        cum_skipped = len(results["skipped"])
        cum_ins = sum(r.get("inserted", 0) or 0 for r in results["success"])
        cum_upd = sum(r.get("updated", 0) or 0 for r in results["success"])
        print(f"  Running totals: Success={cum_success}  Skipped={cum_skipped}  Inserted={cum_ins:,}  Updated={cum_upd:,}")
        print("=" * 80)
        _flush()

        if batch_num < total_batches - 1 and args.no_approval:
            print("(Batch summary complete. Proceeding to next batch.)\n")
            _flush()

        # Continue to next batch even if some towns failed; issues summarized at end
        _flush()

        if batch_num < total_batches - 1 and not args.no_approval:
            approval_file = SCRIPT_DIR / "APPROVE_NEXT_BATCH.txt"
            approval_file.unlink(missing_ok=True)
            stop_file.unlink(missing_ok=True)
            print("\n" + "=" * 80)
            print("BATCH COMPLETE - WAITING FOR APPROVAL")
            print("=" * 80)
            next_batch_towns = towns[batch_end : batch_end + BATCH_SIZE]
            print(f"Next batch will process: {', '.join(next_batch_towns[:5])}{'...' if len(next_batch_towns) > 5 else ''}")
            print(f"\nTo continue: create {approval_file}")
            print(f"To stop: create {stop_file}")
            print("Waiting for approval file...")
            print("=" * 80)
            _flush()

            # Wait indefinitely for approval (no timeout); create APPROVE_NEXT_BATCH.txt to continue
            waited = 0
            while True:
                if stop_file.exists():
                    print("\nStop file detected - import stopped.")
                    stop_file.unlink(missing_ok=True)
                    sys.exit(0)
                if approval_file.exists():
                    print("\nApproval file detected - continuing to next batch.\n")
                    approval_file.unlink(missing_ok=True)
                    break
                time.sleep(2)
                waited += 2
                if waited % 10 == 0:
                    print(f"  Still waiting... ({waited}s)")
                    _flush()

    print("\n" + "=" * 80)
    print("IMPORT COMPLETE")
    print("=" * 80)
    print(f"Success: {len(results['success'])} | Skipped: {len(results['skipped'])} | Failed: {len(results['failed'])}")
    _flush()

    # Summary of towns that need attention (fix and re-run from that town if desired)
    if results["failed"] or results["skipped"]:
        print("\n" + "=" * 80)
        print("TOWNS TO ADDRESS (fix and re-run with --start-from-town <Name> if desired)")
        print("=" * 80)
        for r in results["failed"]:
            print(f"  FAILED:  {r.get('town')}")
            print(f"           {str(r.get('error', ''))}")
        for s in results["skipped"]:
            print(f"  SKIPPED: {s.get('town')}")
            print(f"           {str(s.get('reason', ''))[:120]}")
        print("=" * 80)
        _flush()


if __name__ == "__main__":
    main()
