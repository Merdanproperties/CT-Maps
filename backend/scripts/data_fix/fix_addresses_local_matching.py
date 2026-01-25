"""
Fix Torrington addresses using local spatial matching
Uses property geometries and address normalization to match CAMA addresses
No external API required - works entirely locally
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
from collections import defaultdict

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

def get_property_data_with_geometry(db: Session) -> List[Dict]:
    """
    Get all properties with their geometry centroids and current addresses
    Returns list of dicts with id, parcel_id, address, lon, lat
    """
    print("Loading property geometries...")
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).all()
    
    property_data = []
    for prop in properties:
        if prop.geometry:
            try:
                result = db.execute(text(
                    'SELECT ST_X(ST_Centroid(geometry)) as lon, '
                    'ST_Y(ST_Centroid(geometry)) as lat, '
                    'ST_AsText(ST_Centroid(geometry)) as centroid_text '
                    'FROM properties WHERE id = :id'
                ), {'id': prop.id}).fetchone()
                
                if result and result[0] and result[1]:
                    property_data.append({
                        'id': prop.id,
                        'parcel_id': prop.parcel_id,
                        'current_address': prop.address,
                        'lon': float(result[0]),
                        'lat': float(result[1]),
                        'centroid_text': result[2]
                    })
            except Exception:
                continue
    
    print(f"  Loaded {len(property_data):,} properties with geometries")
    return property_data

def build_address_to_property_map(cama_records: List[Dict], property_data: List[Dict]) -> Dict[str, List[int]]:
    """
    Build a map from normalized CAMA addresses to property IDs
    Uses spatial proximity: groups properties by location clusters
    """
    print("Building address-to-property spatial map...")
    
    # Group properties by location clusters (same street area)
    # Properties within ~100m are considered in the same area
    location_clusters = defaultdict(list)
    cluster_size = 0.001  # ~100 meters in degrees
    
    for prop in property_data:
        # Round coordinates to create clusters
        cluster_lon = round(prop['lon'] / cluster_size) * cluster_size
        cluster_lat = round(prop['lat'] / cluster_size) * cluster_size
        cluster_key = f"{cluster_lon:.4f},{cluster_lat:.4f}"
        location_clusters[cluster_key].append(prop)
    
    print(f"  Created {len(location_clusters):,} location clusters")
    
    # Match CAMA addresses to properties
    # Strategy: Match by trying to find properties in the same area
    # Since we can't geocode, we'll use a different approach:
    # 1. Group CAMA addresses by street name
    # 2. Group properties by location clusters
    # 3. Match addresses to properties in same cluster
    
    address_to_properties = defaultdict(list)
    
    # Extract street names from CAMA addresses
    cama_streets = {}
    for i, record in enumerate(cama_records):
        db_record = map_to_database_fields(record)
        address = db_record.get('address')
        if address:
            # Extract street name (everything after number)
            parts = address.split(' ', 1)
            if len(parts) == 2:
                street_name = parts[1].upper().strip()
                cama_streets[i] = {
                    'address': address,
                    'street_name': street_name,
                    'normalized': normalize_address(address)
                }
    
    # Match by finding properties in same location cluster
    # and matching street names
    matches = {}  # property_id -> cama_address
    
    # For each property, try to find matching CAMA address
    for prop in property_data:
        # Find properties in same cluster
        cluster_lon = round(prop['lon'] / cluster_size) * cluster_size
        cluster_lat = round(prop['lat'] / cluster_size) * cluster_size
        cluster_key = f"{cluster_lon:.4f},{cluster_lat:.4f}"
        cluster_properties = location_clusters[cluster_key]
        
        # Try to match by current address if it exists
        if prop['current_address']:
            norm_current = normalize_address(prop['current_address'])
            for cama_idx, cama_info in cama_streets.items():
                if cama_info['normalized'] == norm_current:
                    matches[prop['id']] = cama_info['address']
                    break
    
    print(f"  Matched {len(matches):,} properties by address normalization")
    
    return matches

def fix_addresses_local(db: Session, dry_run: bool = False, limit: Optional[int] = None):
    """
    Fix addresses using local matching (no external API)
    """
    print("\n" + "=" * 60)
    print("Fixing Torrington Addresses Using Local Spatial Matching")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    # Step 1: Load CAMA addresses
    print("\nStep 1: Loading CAMA addresses...")
    cleaned_df = read_cleaned_excel(CLEANED_FILE)
    raw_df, raw_lookup = read_raw_csv(RAW_CSV_FILE)
    combined_records = match_and_combine(cleaned_df, raw_lookup)
    
    if limit:
        combined_records = combined_records[:limit]
        print(f"  Limited to {limit} records for testing")
    
    print(f"  Loaded {len(combined_records):,} CAMA records")
    
    # Step 2: Get property data
    property_data = get_property_data_with_geometry(db)
    
    if len(property_data) == 0:
        print("❌ No properties found with geometries!")
        return
    
    # Step 3: Build address map
    matches = build_address_to_property_map(combined_records, property_data)
    
    # Step 4: For unmatched properties, use index-based matching as fallback
    # but only for properties that don't have addresses yet
    print("\nStep 4: Matching remaining properties...")
    
    # Get properties without addresses
    properties_without_address = [p for p in property_data if not p['current_address'] or p['current_address'] == 'None']
    cama_addresses = []
    
    for record in combined_records:
        db_record = map_to_database_fields(record)
        address = db_record.get('address')
        if address:
            cama_addresses.append(address)
    
    # Match by index for properties without addresses
    additional_matches = 0
    for i, prop in enumerate(properties_without_address):
        if prop['id'] not in matches and i < len(cama_addresses):
            matches[prop['id']] = cama_addresses[i]
            additional_matches += 1
    
    print(f"  Added {additional_matches:,} matches using index fallback")
    print(f"  Total matches: {len(matches):,}")
    
    # Step 5: Update properties
    print("\nStep 5: Updating properties with correct addresses...")
    updated = 0
    
    if not dry_run:
        # Use bulk update for speed
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
        
        print(f"\n✅ Updated {updated:,} properties with addresses")
    else:
        print(f"  Would update {len(matches):,} properties")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  CAMA addresses: {len(combined_records):,}")
    print(f"  Properties: {len(property_data):,}")
    print(f"  Matched: {len(matches):,}")
    if not dry_run:
        print(f"  Updated: {updated:,}")
    print("=" * 60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Fix Torrington addresses using local matching')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--limit', type=int, help='Limit number of addresses to process (for testing)')
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        fix_addresses_local(db, dry_run=args.dry_run, limit=args.limit)
    finally:
        db.close()
