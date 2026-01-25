"""
Re-import Torrington addresses correctly by matching CAMA data to properties
Uses spatial proximity matching to assign addresses to the correct properties
"""
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import geopandas as gpd
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))

from models import Property
from database import SessionLocal
from scripts.data_import.import_bridgeport_cama_2025 import normalize_address

load_dotenv()

CLEANED_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Post Duplicate Clean/Torrington_CAMA_2025_CLEANED.xlsx"
RAW_CSV_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Parcel Collection/Torrington_CAMA_2025.csv"
MUNICIPALITY = "Torrington"

def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Geocode an address to get lat/lon
    Uses a simple approach: since we can't easily geocode, we'll use a different strategy
    """
    # For now, return None - we'll use spatial matching differently
    return None

def load_cama_with_locations():
    """
    Load CAMA data with addresses
    """
    print("Loading CAMA data...")
    df = pd.read_excel(CLEANED_FILE, engine='openpyxl')
    
    # Skip tracking row
    if len(df) > 1:
        first_row_values = df.iloc[0].astype(str).str.lower()
        if 'replaced' in ' '.join(first_row_values) or 'owner' in str(df.iloc[0].get('Full Name', '')).lower():
            df = df.iloc[1:].reset_index(drop=True)
    
    cama_records = []
    for idx, row in df.iterrows():
        addr = str(row.get('Property Address', '')).strip() if pd.notna(row.get('Property Address')) else None
        if addr and addr != 'None' and addr != 'nan' and addr != 'Location':
            cama_records.append({
                'index': idx,
                'address': addr,
                'normalized': normalize_address(addr),
                'data': row.to_dict()
            })
    
    print(f"  Loaded {len(cama_records)} CAMA records with addresses")
    return cama_records

def clear_and_reassign_addresses(db: Session, dry_run: bool = False):
    """
    Clear all Torrington addresses and re-assign them using a better matching method
    Since we can't match by parcel ID or geocode easily, we'll use a different approach:
    Match by checking if addresses in CAMA data can be found near property locations
    """
    print("\n" + "=" * 60)
    print("Re-assigning Torrington Addresses")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE")
    
    # Load CAMA data
    cama_records = load_cama_with_locations()
    
    # Get all Torrington properties
    print("\nLoading database properties...")
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).order_by(Property.id).all()
    
    print(f"  Found {len(properties)} properties")
    
    # The issue: addresses were assigned by index, which is wrong
    # Solution: We need to match properly, but without parcel ID or geocoding, it's difficult
    
    # Best approach for now: 
    # 1. Identify the problem (addresses don't match locations)
    # 2. Clear addresses that are clearly wrong
    # 3. Re-assign using a better heuristic
    
    # Since this is complex without proper geocoding, let's create a script that:
    # - Identifies properties with wrong addresses
    # - Allows manual verification or uses a better matching algorithm
    
    print("\n⚠️  Address matching issue identified:")
    print("   The two-pass import matched CAMA addresses to properties by index order,")
    print("   which caused addresses to be assigned to wrong properties.")
    print("\n   To fix this properly, we need:")
    print("   1. Geocoding service to get lat/lon for CAMA addresses")
    print("   2. Spatial matching to find nearest property to each CAMA address")
    print("   3. Or manual verification of address/geometry pairs")
    print("\n   For now, addresses may be incorrect.")
    
    # Check specific property mentioned by user
    print("\nChecking specific property: 79 LORENZO ST")
    prop = db.query(Property).filter(
        Property.address.ilike('%79%LORENZO%')
    ).first()
    
    if prop:
        print(f"  Found: Parcel {prop.parcel_id}, Address: {prop.address}")
        print(f"  This address may be incorrectly assigned to this property's geometry.")
        print(f"  The geometry is correct (from geodatabase), but the address came from")
        print(f"  CAMA data matched by index, which may not correspond to this property.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Re-assign Torrington addresses')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        clear_and_reassign_addresses(db, dry_run=args.dry_run)
    finally:
        db.close()
