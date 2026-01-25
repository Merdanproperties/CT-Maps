"""
Fix Torrington addresses using spatial matching
Geocodes CAMA addresses and matches them to nearest property geometries
"""
import sys
import os
from pathlib import Path
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
import geopandas as gpd
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv
import requests
import time
from multiprocessing import Pool, cpu_count
from functools import lru_cache

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

@lru_cache(maxsize=10000)
def geocode_nominatim(address: str, city: str = "Torrington", state: str = "CT", retries: int = 3) -> Optional[Tuple[float, float]]:
    """
    Geocode address using Nominatim (OpenStreetMap) with caching
    Returns (lon, lat) or None
    """
    full_address = f"{address}, {city}, {state}, USA"
    
    for attempt in range(retries):
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': full_address,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1
            }
            headers = {
                'User-Agent': 'CT-Maps-Property-Import/1.0 (contact@example.com)'
            }
            
            # Rate limiting: 1 request per second
            if attempt > 0:
                time.sleep(2 ** attempt)  # Exponential backoff
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    lon = float(data[0]['lon'])
                    lat = float(data[0]['lat'])
                    return (lon, lat)
            elif response.status_code == 429:
                # Rate limited, wait longer
                time.sleep(5)
                continue
        except Exception as e:
            if attempt == retries - 1:
                pass  # Log on final attempt
            time.sleep(1)
    
    return None

def geocode_batch_worker(addresses: List[Tuple[int, str]]) -> List[Tuple[int, Optional[Tuple[float, float]]]]:
    """
    Worker function to geocode a batch of addresses
    Returns list of (index, (lon, lat) or None)
    """
    results = []
    for idx, address in addresses:
        if address and address.strip():
            coords = geocode_nominatim(address, MUNICIPALITY, "CT")
            results.append((idx, coords))
            # Rate limiting: 1 request per second per worker (Nominatim requirement)
            time.sleep(1.1)
        else:
            results.append((idx, None))
    return results

def get_property_centroids(db: Session) -> Dict[int, Tuple[float, float]]:
    """
    Get centroid coordinates for all Torrington properties
    Returns dict: property_id -> (lon, lat)
    """
    print("Loading property geometries...")
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).all()
    
    centroids = {}
    for prop in properties:
        if prop.geometry:
            try:
                result = db.execute(text(
                    'SELECT ST_X(ST_Centroid(geometry)) as lon, '
                    'ST_Y(ST_Centroid(geometry)) as lat '
                    'FROM properties WHERE id = :id'
                ), {'id': prop.id}).fetchone()
                
                if result and result[0] and result[1]:
                    centroids[prop.id] = (float(result[0]), float(result[1]))
            except Exception:
                continue
    
    print(f"  Loaded {len(centroids):,} property centroids")
    return centroids

def find_nearest_property(geocoded_coords: Tuple[float, float], 
                         property_centroids: Dict[int, Tuple[float, float]],
                         max_distance_km: float = 0.5) -> Optional[int]:
    """
    Find nearest property to geocoded coordinates
    Returns property_id or None if too far
    """
    if not geocoded_coords:
        return None
    
    from math import radians, cos, sin, asin, sqrt
    
    def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        """Calculate distance in km between two points"""
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Radius of earth in km
        return c * r
    
    geocoded_lon, geocoded_lat = geocoded_coords
    nearest_id = None
    min_distance = float('inf')
    
    for prop_id, (prop_lon, prop_lat) in property_centroids.items():
        distance = haversine(geocoded_lon, geocoded_lat, prop_lon, prop_lat)
        if distance < min_distance and distance <= max_distance_km:
            min_distance = distance
            nearest_id = prop_id
    
    return nearest_id if min_distance <= max_distance_km else None

def fix_addresses_spatial(db: Session, dry_run: bool = False, limit: Optional[int] = None):
    """
    Fix addresses using spatial matching
    """
    print("\n" + "=" * 60)
    print("Fixing Torrington Addresses Using Spatial Matching")
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
    
    print(f"  Loaded {len(combined_records):,} CAMA records with addresses")
    
    # Step 2: Get property centroids
    print("\nStep 2: Loading property geometries...")
    property_centroids = get_property_centroids(db)
    
    if len(property_centroids) == 0:
        print("❌ No properties found with geometries!")
        return
    
    # Step 3: Geocode CAMA addresses in parallel
    print("\nStep 3: Geocoding CAMA addresses...")
    print("  ⚠️  This will take time due to API rate limits (1 req/sec)")
    print("  🚀 Using parallel processing with multiple workers")
    
    # Extract addresses
    addresses_to_geocode = []
    for i, record in enumerate(combined_records):
        db_record = map_to_database_fields(record)
        address = db_record.get('address')
        if address:
            addresses_to_geocode.append((i, address))
    
    print(f"  Geocoding {len(addresses_to_geocode):,} addresses...")
    
    # Geocode in parallel batches
    num_workers = min(cpu_count(), 4)  # Limit workers to avoid overwhelming API
    chunk_size = max(10, len(addresses_to_geocode) // num_workers)
    chunks = [addresses_to_geocode[i:i+chunk_size] 
              for i in range(0, len(addresses_to_geocode), chunk_size)]
    
    geocoded_results = {}  # index -> (lon, lat)
    
    print(f"  Processing {len(chunks)} chunks with {num_workers} workers...")
    start_time = datetime.now()
    
    with Pool(processes=num_workers) as pool:
        for i, chunk_results in enumerate(pool.imap(geocode_batch_worker, chunks), 1):
            for idx, coords in chunk_results:
                if coords:
                    geocoded_results[idx] = coords
            
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = (i * chunk_size) / elapsed if elapsed > 0 else 0
            remaining = (len(chunks) - i) * (chunk_size * 1.1)  # Estimate with rate limiting
            print(f"  Progress: {i}/{len(chunks)} chunks | "
                  f"Geocoded: {len(geocoded_results):,} | "
                  f"Rate: {rate:.2f}/sec | ETA: {remaining/60:.1f} min")
    
    print(f"\n  ✅ Geocoded {len(geocoded_results):,} addresses")
    
    # Step 4: Match addresses to properties
    print("\nStep 4: Matching addresses to properties...")
    matches = {}  # property_id -> (address, distance_km)
    unmatched_addresses = []
    
    for i, record in enumerate(combined_records):
        if i not in geocoded_results:
            continue
        
        db_record = map_to_database_fields(record)
        address = db_record.get('address')
        coords = geocoded_results[i]
        
        nearest_prop_id = find_nearest_property(coords, property_centroids, max_distance_km=0.5)
        
        if nearest_prop_id:
            # Calculate distance for logging
            from math import radians, cos, sin, asin, sqrt
            prop_lon, prop_lat = property_centroids[nearest_prop_id]
            geocoded_lon, geocoded_lat = coords
            
            lon1, lat1, lon2, lat2 = map(radians, [geocoded_lon, geocoded_lat, prop_lon, prop_lat])
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * asin(sqrt(a))
            distance_km = 6371 * c
            
            if nearest_prop_id not in matches or matches[nearest_prop_id][1] > distance_km:
                matches[nearest_prop_id] = (address, distance_km)
        else:
            unmatched_addresses.append(address)
    
    print(f"  ✅ Matched {len(matches):,} addresses to properties")
    print(f"  ⚠️  {len(unmatched_addresses):,} addresses could not be matched")
    
    # Step 5: Update properties
    print("\nStep 5: Updating properties with correct addresses...")
    updated = 0
    
    if not dry_run:
        for prop_id, (address, distance) in matches.items():
            try:
                prop = db.query(Property).filter(Property.id == prop_id).first()
                if prop:
                    prop.address = address
                    updated += 1
                    
                    if updated % 100 == 0:
                        db.commit()
                        print(f"  Progress: {updated:,}/{len(matches):,} updated")
            except Exception as e:
                db.rollback()
                continue
        
        db.commit()
        print(f"\n✅ Updated {updated:,} properties with correct addresses")
    else:
        print(f"  Would update {len(matches):,} properties")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  CAMA addresses processed: {len(addresses_to_geocode):,}")
    print(f"  Successfully geocoded: {len(geocoded_results):,}")
    print(f"  Matched to properties: {len(matches):,}")
    print(f"  Unmatched addresses: {len(unmatched_addresses):,}")
    if not dry_run:
        print(f"  Properties updated: {updated:,}")
    print("=" * 60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Fix Torrington addresses using spatial matching')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--limit', type=int, help='Limit number of addresses to process (for testing)')
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        fix_addresses_spatial(db, dry_run=args.dry_run, limit=args.limit)
    finally:
        db.close()
