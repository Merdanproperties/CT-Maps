#!/usr/bin/env python3
"""
Parse the batch import log and DB to produce an Excel report of results per town.
Columns: Town, Status, Properties_In_DB, Inserted, Updated, Geodatabase_Count,
         Final_DB_Count, Discrepancy_Count, Discrepancy_Pct, Matched_With_Geometry,
         Unmatched_No_Geometry, Discrepancy_Note, Reason_Or_Error
"""
import re
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

# Script lives in backend/scripts/data_import/134_towns_output/; project root is 5 levels up
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

LOG_PATH = PROJECT_ROOT / "import_output.log"
TOWNS_FILE = Path(__file__).resolve().parent / "towns_to_import.txt"  # same folder
OUTPUT_DIR = Path(__file__).resolve().parent  # Write Excel here
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_log(log_path: Path) -> list:
    """Parse import_output.log and return list of per-town result dicts."""
    text = log_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    rows = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Start of a town block: TOWN X/132: TOWNNAME
        town_match = re.match(r"^TOWN\s+(\d+)/132:\s+(.+)$", line.strip())
        if town_match:
            town_num = int(town_match.group(1))
            town_name = town_match.group(2).strip()
            # Look ahead for this town's outcome and stats
            block_end = min(i + 2000, len(lines))  # reasonable search window
            inserted = updated = matched = unmatched = None
            geo_total = final_count = discrepancy_count = discrepancy_pct = None
            discrepancy_note = ""
            status = "success"
            reason = ""
            j = i + 1
            while j < block_end:
                l = lines[j]
                # Next town or batch - stop
                if re.match(r"^TOWN\s+\d+/132:", l.strip()) and j > i + 5:
                    break
                if re.match(r"^BATCH\s+\d+/\d+", l.strip()) and j > i + 5:
                    break
                # Import complete block
                if "✅ Import complete:" in l:
                    j += 1
                    while j < block_end and (lines[j].strip().startswith("Inserted:") or
                                             lines[j].strip().startswith("Updated:") or
                                             "Matched with geometry:" in lines[j] or
                                             "Unmatched (no geometry):" in lines[j]):
                        ll = lines[j]
                        if "Inserted:" in ll:
                            m = re.search(r"Inserted:\s*([\d,]+)", ll)
                            if m:
                                inserted = int(m.group(1).replace(",", ""))
                        if "Updated:" in ll:
                            m = re.search(r"Updated:\s*([\d,]+)", ll)
                            if m:
                                updated = int(m.group(1).replace(",", ""))
                        if "Matched with geometry:" in ll:
                            m = re.search(r"Matched with geometry:\s*([\d,]+)", ll)
                            if m:
                                matched = int(m.group(1).replace(",", ""))
                        if "Unmatched (no geometry):" in ll:
                            m = re.search(r"Unmatched \(no geometry\):\s*([\d,]+)", ll)
                            if m:
                                unmatched = int(m.group(1).replace(",", ""))
                        j += 1
                    continue
                # IMPORT SUMMARY block
                if "Geodatabase Excel total:" in l:
                    m = re.search(r"Geodatabase Excel total:\s*([\d,]+)", l)
                    if m:
                        geo_total = int(m.group(1).replace(",", ""))
                if "Final database count:" in l:
                    m = re.search(r"Final database count:\s*([\d,]+)", l)
                    if m:
                        final_count = int(m.group(1).replace(",", ""))
                if "Discrepancy:" in l and "(" in l:
                    m = re.search(r"Discrepancy:\s*([\d,]+)\s*\(([\d.]+)%\)", l)
                    if m:
                        discrepancy_count = int(m.group(1).replace(",", ""))
                        discrepancy_pct = float(m.group(2))
                if "WARNING: Significant discrepancy" in l:
                    discrepancy_note = "Significant discrepancy (>10%)"
                if "NOTE: Moderate discrepancy" in l:
                    discrepancy_note = "Moderate discrepancy (5-10%)"
                if "Counts are close" in l:
                    discrepancy_note = "Counts close"
                # Town completed
                if re.match(r"^✅\s+.+completed in", l.strip()):
                    m = re.match(r"^✅\s+(.+?)\s+completed in", l.strip())
                    if m:
                        status = "success"
                    break
                # Skipped
                if "skipped:" in l and "⚠️" in l:
                    m = re.match(r"^⚠️\s+(.+?)\s+skipped:\s*(.+)", l.strip())
                    if m:
                        status = "skipped"
                        reason = m.group(2).strip()[:200]
                    break
                # Failed
                if "failed:" in l and "❌" in l:
                    m = re.match(r"^❌\s+(.+?)\s+failed:\s*(.+)", l.strip())
                    if m:
                        status = "failed"
                        reason = m.group(2).strip()[:200]
                    break
                j += 1
            rows.append({
                "town_num": town_num,
                "town": town_name,
                "status": status,
                "inserted": inserted,
                "updated": updated,
                "geodatabase_count": geo_total,
                "final_db_count": final_count,
                "discrepancy_count": discrepancy_count,
                "discrepancy_pct": discrepancy_pct,
                "matched_with_geometry": matched,
                "unmatched_no_geometry": unmatched,
                "discrepancy_note": discrepancy_note,
                "reason_or_error": reason,
            })
            i = j if j > i else i + 1
            continue
        # Standalone skipped/failed (no TOWN X/132 line before, e.g. from final summary)
        skip_match = re.match(r"^\s*-\s+(.+?):\s+(.+)$", line)
        if skip_match and ("Cleaned Excel not found" in line or "Property Address" in line or "not found" in line.lower()):
            # Might be from "Skipped towns:" or "Failed towns:" at end of log
            pass  # we'll add these from the final summary below
        i += 1

    # Also parse the final "Skipped towns:" and "Failed towns:" sections to ensure we have all 12
    skipped_towns = []
    failed_towns = []
    in_skipped = in_failed = False
    for line in lines:
        if "Skipped towns:" in line:
            in_skipped = True
            in_failed = False
            continue
        if "Failed towns:" in line:
            in_failed = True
            in_skipped = False
            continue
        if in_skipped and line.strip().startswith("-"):
            m = re.match(r"^\s*-\s+(.+?):\s+(.+)", line)
            if m:
                skipped_towns.append({"town": m.group(1).strip(), "reason": m.group(2).strip()[:200]})
        if in_failed and line.strip().startswith("-"):
            m = re.match(r"^\s*-\s+(.+?):\s+(.+)", line)
            if m:
                failed_towns.append({"town": m.group(1).strip(), "error": m.group(2).strip()[:200]})

    # Build a full list of all 132 towns from towns_to_import.txt
    with open(TOWNS_FILE, "r") as f:
        all_towns = [line.strip() for line in f if line.strip()]
    # Merge: start with parsed rows (keyed by town name normalized), then fill in skipped/failed from final summary
    by_town = {}
    for r in rows:
        by_town[r["town"].upper()] = r
    for s in skipped_towns:
        t = s["town"].upper()
        if t not in by_town:
            by_town[t] = {
                "town_num": 0,
                "town": s["town"],
                "status": "skipped",
                "inserted": None,
                "updated": None,
                "geodatabase_count": None,
                "final_db_count": None,
                "discrepancy_count": None,
                "discrepancy_pct": None,
                "matched_with_geometry": None,
                "unmatched_no_geometry": None,
                "discrepancy_note": "",
                "reason_or_error": s["reason"],
            }
        else:
            by_town[t]["reason_or_error"] = s["reason"]
    for s in failed_towns:
        t = s["town"].upper()
        if t not in by_town:
            by_town[t] = {
                "town_num": 0,
                "town": s["town"],
                "status": "failed",
                "inserted": None,
                "updated": None,
                "geodatabase_count": None,
                "final_db_count": None,
                "discrepancy_count": None,
                "discrepancy_pct": None,
                "matched_with_geometry": None,
                "unmatched_no_geometry": None,
                "discrepancy_note": "",
                "reason_or_error": s["error"],
            }
        else:
            by_town[t]["reason_or_error"] = s["error"]

    # Order by all_towns and assign town_num
    result = []
    for idx, t in enumerate(all_towns):
        row = by_town.get(t.upper())
        if row:
            row = row.copy()
            row["town_num"] = idx + 1
            row["town"] = t
        else:
            row = {
                "town_num": idx + 1,
                "town": t,
                "status": "not_in_log",
                "inserted": None,
                "updated": None,
                "geodatabase_count": None,
                "final_db_count": None,
                "discrepancy_count": None,
                "discrepancy_pct": None,
                "matched_with_geometry": None,
                "unmatched_no_geometry": None,
                "discrepancy_note": "",
                "reason_or_error": "",
            }
        result.append(row)
    return result


def get_db_counts():
    """Return dict town_upper -> property count from database."""
    try:
        from database import SessionLocal
        from models import Property
        from sqlalchemy import func
        db = SessionLocal()
        rows = db.query(func.upper(Property.municipality).label("town"), func.count(Property.id).label("count")).group_by(func.upper(Property.municipality)).all()
        db.close()
        return {r[0]: r[1] for r in rows}
    except Exception as e:
        print(f"Warning: could not get DB counts: {e}")
        return {}


def main():
    if not LOG_PATH.exists():
        print(f"Log not found: {LOG_PATH}")
        return
    print("Parsing log...")
    rows = parse_log(LOG_PATH)
    print("Getting DB counts...")
    db_counts = get_db_counts()
    # Add current properties in DB (match by town name)
    for r in rows:
        r["properties_in_db"] = db_counts.get(r["town"].upper(), 0)
    # Build DataFrame
    df = pd.DataFrame(rows)
    column_order = [
        "town_num", "town", "status", "properties_in_db",
        "inserted", "updated", "geodatabase_count", "final_db_count",
        "discrepancy_count", "discrepancy_pct", "matched_with_geometry", "unmatched_no_geometry",
        "discrepancy_note", "reason_or_error",
    ]
    df = df[[c for c in column_order if c in df.columns]]
    df = df.rename(columns={
        "town_num": "Town #",
        "town": "Town",
        "status": "Status",
        "properties_in_db": "Properties in DB",
        "inserted": "Inserted",
        "updated": "Updated",
        "geodatabase_count": "Geodatabase Count",
        "final_db_count": "Final DB Count",
        "discrepancy_count": "Discrepancy Count",
        "discrepancy_pct": "Discrepancy %",
        "matched_with_geometry": "Matched With Geometry",
        "unmatched_no_geometry": "Unmatched (No Geometry)",
        "discrepancy_note": "Discrepancy Note",
        "reason_or_error": "Reason / Error",
    })
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"Import_Results_By_Town_{timestamp}.xlsx"
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="By Town")
        # Summary sheet
        summary = []
        summary.append(["Import Results Summary", ""])
        summary.append(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        summary.append(["Total towns in list", len(df)])
        summary.append(["Success (imported)", len(df[df["Status"] == "success"])])
        summary.append(["Skipped", len(df[df["Status"] == "skipped"])])
        summary.append(["Failed", len(df[df["Status"] == "failed"])])
        summary.append(["Not in log (earlier run)", len(df[df["Status"] == "not_in_log"])])
        summary.append(["Total properties in DB", df["Properties in DB"].sum()])
        summary.append(["", ""])
        summary.append(["Skipped towns (reason)", ""])
        for _, r in df[df["Status"] == "skipped"].iterrows():
            summary.append([r["Town"], r["Reason / Error"] if pd.notna(r["Reason / Error"]) else ""])
        summary.append(["", ""])
        summary.append(["Failed towns (error)", ""])
        for _, r in df[df["Status"] == "failed"].iterrows():
            summary.append([r["Town"], r["Reason / Error"] if pd.notna(r["Reason / Error"]) else ""])
        pd.DataFrame(summary).to_excel(writer, index=False, header=False, sheet_name="Summary")
    print(f"Written: {out_path}")
    print(f"Total rows: {len(df)}")
    print(f"  Success: {len(df[df['Status'] == 'success'])}")
    print(f"  Skipped: {len(df[df['Status'] == 'skipped'])}")
    print(f"  Failed:  {len(df[df['Status'] == 'failed'])}")


if __name__ == "__main__":
    main()
