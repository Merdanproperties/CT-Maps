"""
Fix Torrington addresses by matching using CAMA_Link from geodatabase
This is the proper way - no geocoding needed!
"""
import sys
import os
from pathlib import Path
from datetime import date
from typing import Dict, List, Optional
import pandas as pd
import geopandas as gpd
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))

from models import Property
from database import SessionLocal

load_dotenv()

GDB_PATH = "/Users/jacobmermelstein/Desktop/CT Maps/2025 Parcel Layer.gdb"
RAW_CSV_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Parcel Collection/Torrington_CAMA_2025.csv"
MUNICIPALITY = "Torrington"

def parse_cama_link_to_parcel_id(cama_link: str) -> Optional[str]:
    """
    Parse CAMA_Link from geodatabase to parcel_id format
    Example: "76570-141/005/072" -> "141/5/72"
    """
    if not cama_link or pd.isna(cama_link):
        return None
    
    cama_link = str(cama_link).strip()
    if '-' in cama_link:
        parts = cama_link.split('-', 1)
        if len(parts) == 2:
            parcel_part = parts[1]
            # Remove leading zeros: "141/005/072" -> "141/5/72"
            segments = parcel_part.split('/')
            normalized_segments = []
            for seg in segments:
                if seg.isdigit():
                    normalized_segments.append(str(int(seg)))
                else:
                    normalized_segments.append(seg)
            return '/'.join(normalized_segments)
    
    return None

def build_cama_link_to_address_map() -> Dict[str, str]:
    """
    Build map from CAMA_Link (parsed) to address from raw CSV
    """
    print("Building CAMA_Link to address map from raw CSV...")
    
    df = pd.read_csv(RAW_CSV_FILE, low_memory=False)
    
    # Create mapping: CAMA Site Link -> Location (address)
    cama_to_address = {}
    
    for idx, row in df.iterrows():
        location = str(row.get('Location', '')).strip() if pd.notna(row.get('Location')) else None
        cama_site_link = str(row.get('CAMA Site Link', '')).strip() if pd.notna(row.get('CAMA Site Link')) else None
        
        if location and location != 'None' and location != 'nan':
            # Try to match by CAMA Site Link if available
            if cama_site_link and cama_site_link != 'None' and cama_site_link != 'nan':
                # Parse CAMA Site Link to match geodatabase format
                # Format might be like "76570-141/005/072" or just the parcel part
                if '-' in cama_site_link:
                    parsed = parse_cama_link_to_parcel_id(cama_site_link)
                    if parsed:
                        cama_to_address[parsed] = location
                else:
                    # Try direct match
                    cama_to_address[cama_site_link] = location
    
    print(f"  Built map with {len(cama_to_address):,} CAMA_Link -> address mappings")
    return cama_to_address

def fix_addresses_by_cama_link(db: Session, dry_run: bool = False):
    """
    Fix addresses by matching geodatabase CAMA_Link to CSV addresses
    """
    print("\n" + "=" * 60)
    print("Fixing Torrington Addresses Using CAMA_Link Matching")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    # Step 1: Build CAMA_Link to address map from CSV
    cama_to_address = build_cama_link_to_address_map()
    
    # Step 2: Get all Torrington properties with their CAMA_Link
    print("\nStep 2: Loading properties with CAMA_Link...")
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).all()
    
    matches = {}  # property_id -> address
    
    for prop in properties:
        if prop.additional_data and isinstance(prop.additional_data, dict):
            cama_link = prop.additional_data.get('cama_link')
            if cama_link:
                # Parse CAMA_Link to parcel_id format
                parsed = parse_cama_link_to_parcel_id(cama_link)
                if parsed and parsed in cama_to_address:
                    matches[prop.id] = cama_to_address[parsed]
    
    print(f"  Found {len(matches):,} properties with matching CAMA_Link")
    
    # Step 3: Also try matching by parcel_id directly
    print("\nStep 3: Matching by parcel_id...")
    # Load CSV with parcel_id -> address mapping
    df = pd.read_csv(RAW_CSV_FILE, low_memory=False)
    
    # Try to match by parcel_id if we can extract it
    # CSV has PID which doesn't match, but we can try Location -> address mapping
    # Actually, let's use the geodatabase to get the mapping
    
    # Load geodatabase to get CAMA_Link -> Location mapping
    print("\nStep 4: Loading geodatabase for CAMA_Link -> Location mapping...")
    gdf = gpd.read_file(GDB_PATH, layer='Full_State_Parcels_25', driver='FileGDB')
    torrington_gdf = gdf[gdf['Town_Name'].str.contains('Torrington', case=False, na=False)]
    
    # Build geodatabase mapping: parcel_id -> CAMA_Link -> Location (if available)
    gdb_cama_map = {}
    for idx, row in torrington_gdf.iterrows():
        parcel_id = str(row.get('Parcel_ID', '')).strip()
        cama_link = str(row.get('CAMA_Link', '')).strip() if pd.notna(row.get('CAMA_Link')) else None
        location = str(row.get('Location', '')).strip() if pd.notna(row.get('Location')) else None
        
        if parcel_id and cama_link:
            gdb_cama_map[parcel_id] = {
                'cama_link': cama_link,
                'location': location if location and location != 'None' else None
            }
    
    print(f"  Loaded {len(gdb_cama_map):,} parcel mappings from geodatabase")
    
    # Step 5: Match properties by parcel_id -> CAMA_Link -> CSV address
    print("\nStep 5: Matching properties to CSV addresses...")
    additional_matches = 0
    
    for prop in properties:
        if prop.id not in matches and prop.parcel_id:
            parcel_id = str(prop.parcel_id).strip()
            
            if parcel_id in gdb_cama_map:
                cama_link = gdb_cama_map[parcel_id]['cama_link']
                parsed = parse_cama_link_to_parcel_id(cama_link)
                
                if parsed and parsed in cama_to_address:
                    matches[prop.id] = cama_to_address[parsed]
                    additional_matches += 1
    
    print(f"  Added {additional_matches:,} additional matches")
    print(f"  Total matches: {len(matches):,}")
    
    # Step 6: Update properties
    print("\nStep 6: Updating properties...")
    updated = 0
    
    if not dry_run:
        updates = []
        for prop_id, address in matches.items():
            updates.append({'id': prop_id, 'address': address})
            
            if len(updates) >= 500:
                db.bulk_update_mappings(Property, updates)
                db.commit()
                updated += len(updates)
                print(f"  Progress: {updated:,}/{len(matches):,} updated")
                updates = []
        
        if updates:
            db.bulk_update_mappings(Property, updates)
            db.commit()
            updated += len(updates)
        
        print(f"\n✅ Updated {updated:,} properties with correct addresses")
    else:
        print(f"  Would update {len(matches):,} properties")
    
    print("\n" + "=" * 60)
    print("✅ Address matching complete using CAMA_Link!")
    print("=" * 60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Fix Torrington addresses using CAMA_Link')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        fix_addresses_by_cama_link(db, dry_run=args.dry_run)
    finally:
        db.close()
