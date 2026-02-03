"""
Verify the 37 'no Location' towns: geodatabase Excel, cleaned Excel, CSV, and Parcel_ID matchability.
Output: breakdown of which towns can use import_town_optimized (Parcel_ID matching) vs need geocode_spatial.

Run from project root:
  python backend/scripts/data_import/verification/verify_37_towns_parcel_id.py

Or from backend:
  python scripts/data_import/verification/verify_37_towns_parcel_id.py
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

# Paths (script lives in data_import/verification/)
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent.parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
DEFAULT_DATA_DIR = Path("/Users/jacobmermelstein/Desktop/CT Data")
GEO_EXCEL_DIR = PROJECT_ROOT / "Analysis scripts" / "Excel geodatabase all towns"
TOWNS_FILE = SCRIPT_DIR.parent / "35_towns" / "towns_no_location.txt"

# Sample size for Parcel_ID overlap check (cap to avoid slow reads)
SAMPLE_SIZE = 2000
MIN_OVERLAP_PCT = 50.0  # Consider "can use Parcel_ID" if at least this % of CSV IDs appear in geo Excel


def get_geodatabase_excel_path(municipality: str) -> Optional[Path]:
    """Resolve geodatabase Excel path (same logic as import_town_optimized)."""
    possible_names = [
        f"{municipality}.xlsx",
        f"{municipality.replace(' ', '_')}.xlsx",
        f"{municipality.upper()}.xlsx",
        f"{municipality.lower()}.xlsx",
        f"{municipality.replace(' ', '_').upper()}.xlsx",
        f"{municipality.replace(' ', '_').lower()}.xlsx",
    ]
    for name in possible_names:
        path = GEO_EXCEL_DIR / name
        if path.exists():
            return path
    return None


def get_parcel_id_column_geo(df: pd.DataFrame) -> Optional[str]:
    """Return column name for parcel ID in geodatabase Excel (Parcel_ID or Parcel ID)."""
    for col in ["Parcel_ID", "Parcel ID"]:
        if col in df.columns:
            return col
    for col in df.columns:
        if "parcel" in str(col).lower() and "id" in str(col).lower():
            return col
    return None


def get_parcel_id_column_csv(df: pd.DataFrame) -> Optional[str]:
    """Return column name for parcel ID in CSV (Parcel ID, PID, etc.)."""
    for col in ["Parcel ID", "PID", "Parcel_ID"]:
        if col in df.columns:
            return col
    for col in df.columns:
        if "parcel" in str(col).lower() and "id" in str(col).lower():
            return col
    return None


def get_parcel_ids_from_df(df: pd.DataFrame, col: str, sample_size: int) -> set:
    """Extract set of normalized parcel IDs from a column."""
    if col not in df.columns:
        return set()
    s = df[col].dropna().astype(str).str.strip()
    s = s[s != ""]
    s = s[s.str.lower() != "nan"]
    ids = set(s.tolist())
    if len(ids) > sample_size:
        ids = set(list(ids)[:sample_size])
    return ids


def check_town(town: str) -> Dict:
    """Check one town: file existence + Parcel_ID overlap."""
    result = {
        "town": town,
        "geo_excel": False,
        "geo_excel_path": None,
        "cleaned_excel": False,
        "cleaned_excel_path": None,
        "csv": False,
        "csv_path": None,
        "geo_has_parcel_id_col": False,
        "geo_has_geometry": False,
        "csv_has_parcel_id_col": False,
        "parcel_id_overlap_pct": None,
        "geo_parcel_count": None,
        "csv_parcel_count": None,
        "overlap_count": None,
        "can_use_parcel_id_match": False,
        "reason": [],
    }

    # 1) Geodatabase Excel
    geo_path = get_geodatabase_excel_path(town)
    if not geo_path:
        result["reason"].append("missing geodatabase Excel")
        return result
    result["geo_excel"] = True
    result["geo_excel_path"] = str(geo_path)

    # 2) Cleaned Excel
    cleaned_path = DEFAULT_DATA_DIR / "2025 Post Duplicate Clean" / f"{town}_CAMA_2025_CLEANED.xlsx"
    if not cleaned_path.exists():
        result["reason"].append("missing cleaned Excel")
        return result
    result["cleaned_excel"] = True
    result["cleaned_excel_path"] = str(cleaned_path)

    # 3) CSV
    csv_path = DEFAULT_DATA_DIR / "2025 Parcel Collection" / f"{town}_CAMA_2025.csv"
    if not csv_path.exists():
        result["reason"].append("missing CSV")
        return result
    result["csv"] = True
    result["csv_path"] = str(csv_path)

    # 4) Load geodatabase Excel: Parcel_ID column + geometry columns (sample rows for speed)
    try:
        geo_df = pd.read_excel(geo_path, engine="openpyxl")
        geo_df = geo_df.head(SAMPLE_SIZE * 2)
    except Exception as e:
        result["reason"].append(f"geo Excel read error: {e}")
        return result

    geo_pid_col = get_parcel_id_column_geo(geo_df)
    if not geo_pid_col:
        result["reason"].append("geodatabase Excel has no Parcel_ID column")
        return result
    result["geo_has_parcel_id_col"] = True

    has_wkt = "Geometry_WKT" in geo_df.columns and geo_df["Geometry_WKT"].notna().any()
    has_latlon = "Latitude" in geo_df.columns and "Longitude" in geo_df.columns
    if has_wkt or (has_latlon and geo_df["Latitude"].notna().any()):
        result["geo_has_geometry"] = True
    else:
        result["reason"].append("geodatabase Excel has no Geometry_WKT/Lat/Lon")

    geo_ids = get_parcel_ids_from_df(geo_df, geo_pid_col, SAMPLE_SIZE)
    result["geo_parcel_count"] = len(geo_ids)

    # 5) Load CSV: Parcel ID column
    try:
        csv_df = pd.read_csv(csv_path, engine="python", on_bad_lines="skip", nrows=SAMPLE_SIZE * 2)
    except Exception:
        try:
            csv_df = pd.read_csv(csv_path, engine="python", nrows=SAMPLE_SIZE * 2)
        except Exception as e:
            result["reason"].append(f"CSV read error: {e}")
            return result

    csv_pid_col = get_parcel_id_column_csv(csv_df)
    if not csv_pid_col:
        result["reason"].append("CSV has no Parcel ID / PID column")
        return result
    result["csv_has_parcel_id_col"] = True

    csv_ids = get_parcel_ids_from_df(csv_df, csv_pid_col, SAMPLE_SIZE)
    result["csv_parcel_count"] = len(csv_ids)

    # 6) Overlap
    overlap = geo_ids & csv_ids
    result["overlap_count"] = len(overlap)
    if csv_ids:
        pct = 100.0 * len(overlap) / len(csv_ids)
        result["parcel_id_overlap_pct"] = round(pct, 1)
    else:
        result["parcel_id_overlap_pct"] = 0.0

    # Can use Parcel_ID match if: all files exist, geo has geometry, overlap above threshold
    result["can_use_parcel_id_match"] = (
        result["geo_has_geometry"]
        and result["parcel_id_overlap_pct"] is not None
        and result["parcel_id_overlap_pct"] >= MIN_OVERLAP_PCT
    )
    if not result["can_use_parcel_id_match"] and not result["reason"]:
        if result["parcel_id_overlap_pct"] is not None and result["parcel_id_overlap_pct"] < MIN_OVERLAP_PCT:
            result["reason"].append(
                f"Parcel_ID overlap too low ({result['parcel_id_overlap_pct']}% < {MIN_OVERLAP_PCT}%)"
            )

    return result


def main():
    if not TOWNS_FILE.exists():
        print(f"Towns file not found: {TOWNS_FILE}")
        sys.exit(1)

    with open(TOWNS_FILE, "r") as f:
        towns = [line.strip() for line in f if line.strip()]

    print("=" * 80)
    print("VERIFY 37 TOWNS: Geodatabase Excel, Cleaned Excel, CSV, Parcel_ID matchability")
    print("=" * 80)
    print(f"Towns file: {TOWNS_FILE}")
    print(f"Geodatabase Excel dir: {GEO_EXCEL_DIR}")
    print(f"CT Data dir: {DEFAULT_DATA_DIR}")
    print(f"Min overlap for 'can use Parcel_ID': {MIN_OVERLAP_PCT}%")
    print()

    results: List[Dict] = []
    for i, town in enumerate(towns, 1):
        print(f"  Checking {i}/37: {town}...", end=" ", flush=True)
        r = check_town(town)
        results.append(r)
        if r["can_use_parcel_id_match"]:
            print("OK (Parcel_ID match)")
        else:
            print("--" if not r["reason"] else r["reason"][0][:50])

    # Summary tables
    can_use = [r for r in results if r["can_use_parcel_id_match"]]
    cannot_use = [r for r in results if not r["can_use_parcel_id_match"]]

    print()
    print("=" * 80)
    print("BREAKDOWN: Can use import_town_optimized (Parcel_ID matching) — NO geocode_spatial needed")
    print("=" * 80)
    print(f"  Total: {len(can_use)} towns")
    if can_use:
        for r in can_use:
            print(f"    - {r['town']} (overlap {r['parcel_id_overlap_pct']}%)")
    else:
        print("    (none)")
    print()

    print("=" * 80)
    print("BREAKDOWN: Cannot use Parcel_ID matching — need geocode_spatial or fix data")
    print("=" * 80)
    print(f"  Total: {len(cannot_use)} towns")
    for r in cannot_use:
        reasons = "; ".join(r["reason"]) if r["reason"] else f"overlap {r.get('parcel_id_overlap_pct')}%"
        print(f"    - {r['town']}: {reasons}")
    print()

    # Detailed table (all 37)
    print("=" * 80)
    print("DETAILED TABLE (all 37 towns)")
    print("=" * 80)
    print(
        f"{'Town':<16} {'GeoExcel':<8} {'Cleaned':<8} {'CSV':<6} {'GeoPID':<7} {'GeoGeom':<8} "
        f"{'CSVPID':<7} {'Overlap%':<8} {'USE_PARCEL_ID':<12}"
    )
    print("-" * 100)
    for r in results:
        geo_ok = "Y" if r["geo_excel"] else "N"
        clean_ok = "Y" if r["cleaned_excel"] else "N"
        csv_ok = "Y" if r["csv"] else "N"
        geo_pid = "Y" if r["geo_has_parcel_id_col"] else "N"
        geo_geom = "Y" if r["geo_has_geometry"] else "N"
        csv_pid = "Y" if r["csv_has_parcel_id_col"] else "N"
        overlap = str(r["parcel_id_overlap_pct"]) if r["parcel_id_overlap_pct"] is not None else "—"
        use = "YES" if r["can_use_parcel_id_match"] else "NO"
        print(
            f"{r['town']:<16} {geo_ok:<8} {clean_ok:<8} {csv_ok:<6} {geo_pid:<7} {geo_geom:<8} "
            f"{csv_pid:<7} {overlap:<8} {use:<12}"
        )

    print()
    print("Conclusion:")
    print(f"  - Use import_town_optimized (Parcel_ID only) for: {len(can_use)} towns")
    print(f"  - Need geocode_spatial or fix missing data for: {len(cannot_use)} towns")
    print("=" * 80)


if __name__ == "__main__":
    main()
