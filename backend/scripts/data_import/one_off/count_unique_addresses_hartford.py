"""
Count unique property addresses in Hartford CAMA 2025 CLEANED.xlsx.
Only the base address (e.g. 77 EVERGREEN AVE), not unit/apt/suite extensions.
"""
import re
from pathlib import Path

import pandas as pd

HARTFORD_CLEAN = Path("/Users/jacobmermelstein/Desktop/CT Data/2025 Post Duplicate Clean/Hartford_CAMA_2025_CLEANED.xlsx")


def base_address_only(addr: str) -> str:
    """
    Return only the first part of an address: strip Unit 0AA2, Apt 5, #103, Suite 100, etc.
    """
    if not addr or pd.isna(addr):
        return ""
    addr = str(addr).strip()
    # Strip from Unit/Apt/#/Suite/Ste (and common variants) onward; suffix can be alphanumeric e.g. 0AA2
    pattern = re.compile(
        r"\s*(?:,|;)?\s*(?:Unit|Apt\.?|Apartment|#|Suite|Ste\.?)\s+[\w-]+.*",
        re.IGNORECASE
    )
    base = pattern.sub("", addr).strip()
    # Normalize: uppercase, single spaces
    base = re.sub(r"\s+", " ", base).upper().strip()
    return base


def main():
    if not HARTFORD_CLEAN.exists():
        print(f"File not found: {HARTFORD_CLEAN}")
        return
    df = pd.read_excel(HARTFORD_CLEAN, engine="openpyxl")
    # Skip tracking row if present
    if len(df) > 1:
        first_vals = df.iloc[0].astype(str).str.lower()
        if "replaced" in " ".join(first_vals) or "owner" in str(df.iloc[0].get("Full Name", "")).lower():
            df = df.iloc[1:].reset_index(drop=True)
    # Find address column
    addr_col = None
    for c in df.columns:
        if "property" in str(c).lower() and "address" in str(c).lower():
            addr_col = c
            break
    if addr_col is None and "Location" in df.columns:
        addr_col = "Location"
    if addr_col is None:
        print("Columns:", list(df.columns))
        raise SystemExit("No address column found")
    df["base_address"] = df[addr_col].apply(base_address_only)
    df = df[df["base_address"].str.len() > 0]
    unique = df["base_address"].nunique()
    total = len(df)
    print(f"Total rows with non-empty base address: {total:,}")
    print(f"Unique base addresses (no Unit/Apt/Suite/#): {unique:,}")
    return unique


if __name__ == "__main__":
    main()
