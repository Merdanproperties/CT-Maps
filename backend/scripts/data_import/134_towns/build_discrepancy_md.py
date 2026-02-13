#!/usr/bin/env python3
"""
Parse a full 134-town import log and write docs/134_TOWNS_DISCREPANCY_PERCENTAGES.md.
Usage: python3 build_discrepancy_md.py [path/to/full_134_import_YYYYMMDD_HHMMSS.log]
"""
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent.parent
TOWNS_FILE = SCRIPT_DIR / "towns_to_import.txt"
DOC_PATH = SCRIPT_DIR.parent / "docs" / "134_TOWNS_DISCREPANCY_PERCENTAGES.md"


def parse_log(log_path: Path) -> dict:
    """Parse log; return dict town_upper -> row (inserted, updated, cleaned_count, geo_total, final_db, discrepancy_n, discrepancy_pct, status, reason)."""
    text = log_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    by_town = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        # TOWN N/134: NAME or TOWN N/132: NAME
        town_match = re.match(r"^TOWN\s+(\d+)/\d+:\s+(.+)$", line.strip())
        if town_match:
            town_name = town_match.group(2).strip()
            town_upper = town_name.upper()
            block_end = min(i + 2500, len(lines))
            inserted = updated = cleaned_count = geo_total = final_db = disc_n = disc_pct = None
            status = "success"
            reason = ""
            j = i + 1
            while j < block_end:
                l = lines[j]
                if re.match(r"^TOWN\s+\d+/\d+:", l.strip()) and j > i + 5:
                    break
                if re.match(r"^BATCH\s+\d+/\d+", l.strip()) and j > i + 5:
                    break
                if "✅ Import complete:" in l:
                    j += 1
                    while j < block_end:
                        ll = lines[j]
                        if "Inserted:" in ll:
                            m = re.search(r"Inserted:\s*([\d,]+)", ll)
                            if m:
                                inserted = int(m.group(1).replace(",", ""))
                        if "Updated:" in ll:
                            m = re.search(r"Updated:\s*([\d,]+)", ll)
                            if m:
                                updated = int(m.group(1).replace(",", ""))
                        if not (ll.strip().startswith("Inserted:") or ll.strip().startswith("Updated:") or
                                "Matched with geometry:" in ll or "Unmatched (no geometry):" in ll):
                            break
                        j += 1
                    continue
                if "Loaded " in l and "records from cleaned Excel" in l:
                    m = re.search(r"Loaded\s+([\d,]+)\s+records from cleaned Excel", l)
                    if m:
                        cleaned_count = int(m.group(1).replace(",", ""))
                if "Geodatabase Excel total:" in l:
                    m = re.search(r"Geodatabase Excel total:\s*([\d,]+)", l)
                    if m:
                        geo_total = int(m.group(1).replace(",", ""))
                if "Final database count:" in l:
                    m = re.search(r"Final database count:\s*([\d,]+)", l)
                    if m:
                        final_db = int(m.group(1).replace(",", ""))
                if "Discrepancy:" in l and "(" in l:
                    m = re.search(r"Discrepancy:\s*(-?[\d,]+)\s*\((-?[\d.]+)%\)", l)
                    if m:
                        disc_n = int(m.group(1).replace(",", ""))
                        disc_pct = float(m.group(2))
                if "WARNING: Significant discrepancy" in l:
                    reason = "Significant discrepancy (>10%)"
                if "NOTE: Moderate discrepancy" in l:
                    reason = "Moderate discrepancy (5-10%)"
                if "Counts are close" in l or "Counts close" in l:
                    reason = "Counts close"
                if re.match(r"^✅\s+.+completed in", l.strip()):
                    status = "success"
                    break
                if "skipped:" in l and "⚠️" in l:
                    m = re.match(r"^⚠️\s+(.+?)\s+skipped:\s*(.+)", l.strip())
                    if m:
                        status = "skipped"
                        reason = m.group(2).strip()[:120]
                    break
                if "failed:" in l and "❌" in l:
                    m = re.match(r"^❌\s+(.+?)\s+failed:\s*(.+)", l.strip())
                    if m:
                        status = "failed"
                        reason = m.group(2).strip()[:120]
                    break
                j += 1
            by_town[town_upper] = {
                "town": town_name,
                "inserted": inserted,
                "updated": updated,
                "cleaned_count": cleaned_count,
                "geo_total": geo_total,
                "final_db": final_db,
                "discrepancy_n": disc_n,
                "discrepancy_pct": disc_pct,
                "status": status,
                "reason": reason,
            }
        i += 1

    # Skipped towns from "Skipped towns:" section
    in_skipped = False
    for line in lines:
        if "Skipped towns:" in line:
            in_skipped = True
            continue
        if in_skipped and line.strip().startswith("-"):
            m = re.match(r"^\s*-\s+(.+?):\s+(.+)", line)
            if m:
                t = m.group(1).strip()
                by_town[t.upper()] = {
                    "town": t,
                    "inserted": None,
                    "updated": None,
                    "cleaned_count": None,
                    "geo_total": None,
                    "final_db": None,
                    "discrepancy_n": None,
                    "discrepancy_pct": None,
                    "status": "skipped",
                    "reason": m.group(2).strip()[:120],
                }
        elif in_skipped and line.strip() and not line.strip().startswith("-"):
            in_skipped = False
    return by_town


def fmt(v, is_pct=False):
    if v is None:
        return "—"
    if is_pct:
        return f"{v:.1f}%"
    return f"{v:,}"


def main():
    log_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not log_path or not log_path.exists():
        # Default: latest full_134_import_*.log in logs/
        logs_dir = SCRIPT_DIR / "logs"
        candidates = sorted(logs_dir.glob("full_134_import_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            print("No log file found. Pass path: python3 build_discrepancy_md.py path/to/full_134_import_*.log")
            sys.exit(1)
        log_path = candidates[0]
    print(f"Using log: {log_path}")

    with open(TOWNS_FILE, "r") as f:
        all_towns = [line.strip() for line in f if line.strip()]
    by_town = parse_log(log_path)

    rows = []
    for idx, town in enumerate(all_towns):
        r = by_town.get(town.upper(), {})
        if not r:
            r = {"town": town, "status": "not in log", "inserted": None, "updated": None, "cleaned_count": None,
                 "geo_total": None, "final_db": None, "discrepancy_n": None, "discrepancy_pct": None, "reason": ""}
        r["num"] = idx + 1
        r["town"] = town  # Use list casing for display
        rows.append(r)

    # Build markdown
    total = len(rows)
    header = f"""# Discrepancy % and import stats for all {total} towns (134 flow)

**Source:** Log `{log_path.name}` (full 134-town run).
**Columns:**
- **Inserted** = number of properties inserted in this run
- **Updated** = number updated
- **Cleaned Excel count** = records in cleaned Excel (when present in log)
- **Geodatabase total** = total parcels in geodatabase Excel (with geometry)
- **Final DB count** = properties for this town in DB after run
- **Discrepancy (n)** = Geodatabase total − Final DB count
- **Discrepancy %** = Discrepancy (n) / Geodatabase total; >10% = significant.
- **Status** = success / skipped / failed / not in log

| # | Town | Inserted | Updated | Cleaned Excel count | Geodatabase total | Final DB count | Discrepancy (n) | Discrepancy % | Status |
|---|------|----------|---------|---------------------|-------------------|----------------|-----------------|---------------|--------|
"""
    body = []
    for r in rows:
        num = r["num"]
        town = r["town"]
        ins = fmt(r.get("inserted"))
        upd = fmt(r.get("updated"))
        clean = fmt(r.get("cleaned_count"))
        geo = fmt(r.get("geo_total"))
        final = fmt(r.get("final_db"))
        disc_n = fmt(r.get("discrepancy_n"))
        disc_pct = fmt(r.get("discrepancy_pct"), is_pct=True) if r.get("discrepancy_pct") is not None else "—"
        status = r.get("status", "")
        body.append(f"| {num} | {town} | {ins} | {upd} | {clean} | {geo} | {final} | {disc_n} | {disc_pct} | {status} |")
    footer = f"""
**How to refresh:** Re-run after a full 134-town run:
`python3 backend/scripts/data_import/134_towns/build_discrepancy_md.py backend/scripts/data_import/134_towns/logs/full_134_import_YYYYMMDD_HHMMSS.log`
Or with no args to use the latest full_134_import_*.log in that folder.
"""
    doc_path = DOC_PATH
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(header + "\n".join(body) + footer, encoding="utf-8")
    print(f"Written: {doc_path}")
    print(f"  Success: {sum(1 for r in rows if r.get('status') == 'success')}")
    print(f"  Skipped: {sum(1 for r in rows if r.get('status') == 'skipped')}")
    print(f"  Failed:  {sum(1 for r in rows if r.get('status') == 'failed')}")
    print(f"  Not in log: {sum(1 for r in rows if r.get('status') == 'not in log')}")


if __name__ == "__main__":
    main()
