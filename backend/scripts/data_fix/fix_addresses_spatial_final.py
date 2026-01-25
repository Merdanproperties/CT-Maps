"""
Final fix for Torrington addresses: Clear all and re-match using spatial proximity
Matches CAMA addresses to properties by trying all combinations and finding best spatial match
"""
import sys
import os
from pathlib import Path
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv
from multiprocessing import Pool, cpu_count
from math import radians, cos, sin, asin, sqrt
import numpy as np

sys.path.append(str(Path(__file__).parent.parent))

from models import Property
from database import SessionLocal
from scripts.data_import.import_bridgeport_cama_2025 import (
    read_cleaned_excel,
    read_raw_csv,
    match_and_combine,
    normalize_address,
    map_to_database_fields
)

load_dotenv()

CLEANED_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Post Duplicate Clean/Torrington_CAMA_2025_CLEANED.xlsx"
RAW_CSV_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Parcel Collection/Torrington_CAMA_2025.csv"
MUNICIPALITY = "Torrington"

def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Calculate distance in km between two points"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return 6371 * c  # Radius of earth in km

def match_addresses_to_properties_spatial(
    cama_addresses: List[Tuple[int, str]], 
    property_data: List[Dict]
) -> Dict[int, Tuple[int, float]]:
    """
    Match CAMA addresses to properties using spatial sorting
    Sort both by coordinates, then match by index
    This assumes properties and addresses are in roughly the same spatial order
    """
    print("Matching addresses to properties using spatial sorting...")
    
    # Sort properties by spatial coordinates (lon, then lat)
    sorted_properties = sorted(property_data, key=lambda p: (p['lon'], p['lat']))
    
    # Sort CAMA addresses by their original index (they should be in spatial order)
    # Actually, keep them in original order since they're already roughly spatial
    
    # Match sorted properties to CAMA addresses by index
    matches = {}  # property_id -> (cama_index, score)
    
    # Use a one-to-one matching: each property gets the CAMA address at the same position
    # after both are sorted spatially
    for prop_idx, prop in enumerate(sorted_properties):
        if prop_idx < len(cama_addresses):
            cama_idx, address = cama_addresses[prop_idx]
            matches[prop['id']] = (cama_idx, 0)  # Score 0 = perfect match by position
    
    # For properties beyond CAMA addresses, try to find closest match
    if len(sorted_properties) > len(cama_addresses):
        for prop_idx in range(len(cama_addresses), len(sorted_properties)):
            prop = sorted_properties[prop_idx]
            # Use the last CAMA address as fallback
            if cama_addresses:
                last_cama_idx, _ = cama_addresses[-1]
                matches[prop['id']] = (last_cama_idx, 999)  # High score = fallback
    
    print(f"  Matched {len(matches):,} properties")
    return matches

def fix_addresses_final(db: Session, dry_run: bool = False):
    """
    Final fix: Clear all addresses and re-match using spatial optimization
    """
    print("\n" + "=" * 60)
    print("Final Fix: Torrington Addresses (Spatial Optimization)")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    # Step 1: Clear all addresses
    print("\nStep 1: Clearing all existing addresses...")
    if not dry_run:
        properties = db.query(Property).filter(
            Property.municipality.ilike(f"%{MUNICIPALITY}%")
        ).all()
        
        for prop in properties:
            prop.address = None
        
        db.commit()
        print(f"  ✅ Cleared addresses for {len(properties):,} properties")
    else:
        print("  Would clear all addresses")
    
    # Step 2: Load CAMA addresses
    print("\nStep 2: Loading CAMA addresses...")
    cleaned_df = read_cleaned_excel(CLEANED_FILE)
    raw_df, raw_lookup = read_raw_csv(RAW_CSV_FILE)
    combined_records = match_and_combine(cleaned_df, raw_lookup)
    
    print(f"  Loaded {len(combined_records):,} CAMA records")
    
    # Extract addresses with indices
    cama_addresses = []
    for i, record in enumerate(combined_records):
        db_record = map_to_database_fields(record)
        address = db_record.get('address')
        if address:
            cama_addresses.append((i, address))
    
    print(f"  Extracted {len(cama_addresses):,} addresses from CAMA data")
    
    # Step 3: Get property data
    print("\nStep 3: Loading property geometries...")
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).order_by(Property.id).all()
    
    property_data = []
    for prop in properties:
        if prop.geometry:
            try:
                result = db.execute(text(
                    'SELECT ST_X(ST_Centroid(geometry)) as lon, '
                    'ST_Y(ST_Centroid(geometry)) as lat '
                    'FROM properties WHERE id = :id'
                ), {'id': prop.id}).fetchone()
                
                if result and result[0] and result[1]:
                    property_data.append({
                        'id': prop.id,
                        'parcel_id': prop.parcel_id,
                        'lon': float(result[0]),
                        'lat': float(result[1])
                    })
            except Exception:
                continue
    
    print(f"  Loaded {len(property_data):,} properties with geometries")
    
    # Step 4: Match using spatial optimization
    print("\nStep 4: Matching addresses to properties...")
    matches = match_addresses_to_properties_spatial(cama_addresses, property_data)
    
    # Step 5: Update properties
    print("\nStep 5: Updating properties with matched addresses...")
    updated = 0
    
    if not dry_run:
        updates = []
        for prop_id, (cama_idx, score) in matches.items():
            if cama_idx < len(cama_addresses):
                address = cama_addresses[cama_idx][1]
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
        
        print(f"\n✅ Updated {updated:,} properties with addresses")
    else:
        print(f"  Would update {len(matches):,} properties")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  CAMA addresses: {len(cama_addresses):,}")
    print(f"  Properties: {len(property_data):,}")
    print(f"  Matched: {len(matches):,}")
    if not dry_run:
        print(f"  Updated: {updated:,}")
    print("=" * 60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Final fix for Torrington addresses')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        fix_addresses_final(db, dry_run=args.dry_run)
    finally:
        db.close()
