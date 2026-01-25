"""
Fix Torrington addresses using geocoding with proper rate limiting
Works with free Nominatim API (1 req/sec) - will take ~4 hours for 14k addresses
OR can use paid services for faster results
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
import requests
import time
from multiprocessing import Pool, cpu_count
import json

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
GEOCODE_CACHE_FILE = "logs/geocode_cache_torrington.json"

# Geocoding service configuration
GEOCODE_SERVICE = os.getenv('GEOCODE_SERVICE', 'nominatim')  # 'nominatim', 'google', 'mapbox'
GOOGLE_API_KEY = os.getenv('GOOGLE_GEOCODING_API_KEY', '')
MAPBOX_API_KEY = os.getenv('MAPBOX_ACCESS_TOKEN', '')
NOMINATIM_URL = os.getenv('NOMINATIM_URL', 'https://nominatim.openstreetmap.org')  # Use local instance if available

def load_geocode_cache() -> Dict[str, Tuple[float, float]]:
    """Load cached geocoding results"""
    if os.path.exists(GEOCODE_CACHE_FILE):
        try:
            with open(GEOCODE_CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_geocode_cache(cache: Dict[str, Tuple[float, float]]):
    """Save geocoding results to cache"""
    os.makedirs(os.path.dirname(GEOCODE_CACHE_FILE), exist_ok=True)
    with open(GEOCODE_CACHE_FILE, 'w') as f:
        json.dump(cache, f)

def geocode_nominatim(address: str, city: str = "Torrington", state: str = "CT", retries: int = 3) -> Optional[Tuple[float, float]]:
    """
    Geocode using Nominatim (free, 1 req/sec limit for public API, no limit for local)
    """
    full_address = f"{address}, {city}, {state}, USA"
    
    # Use local instance if available, otherwise use public API
    base_url = NOMINATIM_URL.rstrip('/')
    is_local = 'localhost' in base_url or '127.0.0.1' in base_url
    
    for attempt in range(retries):
        try:
            url = f"{base_url}/search"
            params = {
                'q': full_address,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1
            }
            headers = {
                'User-Agent': 'CT-Maps-Property-Import/1.0'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    lon = float(data[0]['lon'])
                    lat = float(data[0]['lat'])
                    return (lon, lat)
            elif response.status_code == 429:
                time.sleep(10)
                continue
        except requests.exceptions.RequestException as e:
            if attempt == retries - 1:
                print(f"      ⚠️  Geocoding failed for '{address}': {e}")
            if not is_local:  # Only sleep for public API
                time.sleep(2 ** attempt)
    
    return None

def geocode_google(address: str, city: str = "Torrington", state: str = "CT") -> Optional[Tuple[float, float]]:
    """
    Geocode using Google Geocoding API (paid, but faster)
    Requires GOOGLE_GEOCODING_API_KEY in .env
    """
    if not GOOGLE_API_KEY:
        return None
    
    full_address = f"{address}, {city}, {state}, USA"
    
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'address': full_address,
            'key': GOOGLE_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'OK' and data.get('results'):
                location = data['results'][0]['geometry']['location']
                return (location['lng'], location['lat'])
    except Exception as e:
        print(f"      ⚠️  Google geocoding failed: {e}")
    
    return None

def geocode_mapbox(address: str, city: str = "Torrington", state: str = "CT") -> Optional[Tuple[float, float]]:
    """
    Geocode using Mapbox API (paid, but faster)
    Requires MAPBOX_ACCESS_TOKEN in .env
    """
    if not MAPBOX_API_KEY:
        return None
    
    full_address = f"{address}, {city}, {state}, USA"
    
    try:
        url = "https://api.mapbox.com/geocoding/v5/mapbox.places/" + requests.utils.quote(full_address) + ".json"
        params = {
            'access_token': MAPBOX_API_KEY,
            'limit': 1
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('features'):
                coords = data['features'][0]['geometry']['coordinates']
                return (coords[0], coords[1])  # lon, lat
    except Exception as e:
        print(f"      ⚠️  Mapbox geocoding failed: {e}")
    
    return None

def geocode_address(address: str, city: str = "Torrington", state: str = "CT", cache: Dict = None) -> Optional[Tuple[float, float]]:
    """
    Geocode address using configured service
    """
    if not address or address.strip() == '':
        return None
    
    address = address.strip()
    
    # Check cache first
    if cache and address in cache:
        coords = cache[address]
        return (float(coords[0]), float(coords[1]))
    
    # Geocode based on service
    if GEOCODE_SERVICE == 'google':
        coords = geocode_google(address, city, state)
    elif GEOCODE_SERVICE == 'mapbox':
        coords = geocode_mapbox(address, city, state)
    else:  # nominatim (default)
        coords = geocode_nominatim(address, city, state)
        # Rate limiting for Nominatim: 1 req/sec
        time.sleep(1.1)
    
    # Cache result
    if coords and cache is not None:
        cache[address] = coords
    
    return coords

def geocode_batch_worker(args: Tuple) -> List[Tuple[int, Optional[Tuple[float, float]]]]:
    """
    Worker function to geocode a batch of addresses
    """
    addresses, cache = args
    results = []
    
    for idx, address in addresses:
        if address and address.strip():
            coords = geocode_address(address, MUNICIPALITY, "CT", cache)
            results.append((idx, coords))
        else:
            results.append((idx, None))
    
    return results

def fix_addresses_with_geocoding(db: Session, dry_run: bool = False, limit: Optional[int] = None):
    """
    Fix addresses using geocoding to match CAMA addresses to property geometries
    """
    print("\n" + "=" * 60)
    print("Fixing Torrington Addresses Using Geocoding")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    print(f"\nGeocoding Service: {GEOCODE_SERVICE}")
    if GEOCODE_SERVICE == 'nominatim':
        if 'localhost' in NOMINATIM_URL or '127.0.0.1' in NOMINATIM_URL:
            print("  ✅ Using local Nominatim instance (no rate limits!)")
            print("  🚀 Can process all addresses quickly with parallel processing")
        else:
            print("  ⚠️  Using public Nominatim (1 req/sec) - This will take ~4 hours for 14k addresses")
            print("  💡 Tip: Install local Nominatim for free unlimited geocoding")
            print("  💡 Or set GEOCODE_SERVICE=google or mapbox in .env for faster results")
    elif GEOCODE_SERVICE == 'google':
        print("  ✅ Using Google Geocoding API (requires API key)")
    elif GEOCODE_SERVICE == 'mapbox':
        print("  ✅ Using Mapbox Geocoding API (requires access token)")
    
    # Load cache
    cache = load_geocode_cache()
    print(f"  Loaded {len(cache):,} cached geocoding results")
    
    # Step 1: Load CAMA addresses
    print("\nStep 1: Loading CAMA addresses...")
    cleaned_df = read_cleaned_excel(CLEANED_FILE)
    raw_df, raw_lookup = read_raw_csv(RAW_CSV_FILE)
    combined_records = match_and_combine(cleaned_df, raw_lookup)
    
    if limit:
        combined_records = combined_records[:limit]
        print(f"  Limited to {limit} records for testing")
    
    print(f"  Loaded {len(combined_records):,} CAMA records")
    
    # Extract addresses
    addresses_to_geocode = []
    for i, record in enumerate(combined_records):
        db_record = map_to_database_fields(record)
        address = db_record.get('address')
        if address:
            addresses_to_geocode.append((i, address))
    
    print(f"  Extracted {len(addresses_to_geocode):,} addresses to geocode")
    
    # Step 2: Get property centroids
    print("\nStep 2: Loading property geometries...")
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).all()
    
    property_centroids = {}
    for prop in properties:
        if prop.geometry:
            try:
                result = db.execute(text(
                    'SELECT ST_X(ST_Centroid(geometry)) as lon, '
                    'ST_Y(ST_Centroid(geometry)) as lat '
                    'FROM properties WHERE id = :id'
                ), {'id': prop.id}).fetchone()
                
                if result and result[0] and result[1]:
                    property_centroids[prop.id] = (float(result[0]), float(result[1]))
            except Exception:
                continue
    
    print(f"  Loaded {len(property_centroids):,} property centroids")
    
    # Step 3: Geocode addresses
    print("\nStep 3: Geocoding addresses...")
    print("  This may take a while depending on service and rate limits...")
    
    # Filter out already cached addresses
    addresses_to_geocode_new = [(idx, addr) for idx, addr in addresses_to_geocode if addr not in cache]
    print(f"  {len(addresses_to_geocode_new):,} addresses need geocoding")
    print(f"  {len(addresses_to_geocode) - len(addresses_to_geocode_new):,} addresses already cached")
    
    geocoded_results = {}  # index -> (lon, lat)
    
    # Add cached results
    for idx, address in addresses_to_geocode:
        if address in cache:
            geocoded_results[idx] = cache[address]
    
    # Geocode new addresses
    if addresses_to_geocode_new:
        is_local_nominatim = GEOCODE_SERVICE == 'nominatim' and ('localhost' in NOMINATIM_URL or '127.0.0.1' in NOMINATIM_URL)
        
        if GEOCODE_SERVICE == 'nominatim' and not is_local_nominatim:
            # Sequential for public Nominatim (rate limit: 1 req/sec)
            print("  Geocoding sequentially (Public Nominatim rate limit: 1 req/sec)...")
            print("  ⚠️  This will take ~4 hours. Consider installing local Nominatim for faster results.")
            start_time = datetime.now()
            for i, (idx, address) in enumerate(addresses_to_geocode_new, 1):
                coords = geocode_address(address, MUNICIPALITY, "CT", cache)
                if coords:
                    geocoded_results[idx] = coords
                    cache[address] = coords
                
                if i % 100 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    rate = i / elapsed if elapsed > 0 else 0
                    remaining = (len(addresses_to_geocode_new) - i) / rate if rate > 0 else 0
                    print(f"  Progress: {i:,}/{len(addresses_to_geocode_new):,} | "
                          f"Rate: {rate:.2f}/sec | ETA: {remaining/60:.1f} min")
                    
                    # Save cache periodically
                    save_geocode_cache(cache)
        else:
            # Parallel for paid services
            num_workers = min(cpu_count(), 8)
            chunk_size = max(10, len(addresses_to_geocode_new) // num_workers)
            chunks = [addresses_to_geocode_new[i:i+chunk_size] 
                     for i in range(0, len(addresses_to_geocode_new), chunk_size)]
            
            print(f"  Geocoding in parallel with {num_workers} workers...")
            with Pool(processes=num_workers) as pool:
                worker_args = [(chunk, cache) for chunk in chunks]
                for i, chunk_results in enumerate(pool.imap(geocode_batch_worker, worker_args), 1):
                    for idx, coords in chunk_results:
                        if coords:
                            geocoded_results[idx] = coords
                            if idx < len(addresses_to_geocode_new):
                                _, address = addresses_to_geocode_new[idx]
                                cache[address] = coords
                    
                    print(f"  Progress: {i}/{len(chunks)} chunks | "
                          f"Geocoded: {len(geocoded_results):,}")
                    
                    # Save cache periodically
                    save_geocode_cache(cache)
    
    # Save final cache
    save_geocode_cache(cache)
    print(f"\n  ✅ Geocoded {len(geocoded_results):,} addresses")
    
    # Step 4: Match to properties using spatial proximity
    print("\nStep 4: Matching geocoded addresses to properties...")
    from math import radians, cos, sin, asin, sqrt
    
    def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        """Calculate distance in km"""
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return 6371 * c
    
    matches = {}  # property_id -> (cama_index, distance_km)
    max_distance_km = 0.5  # 500 meters
    
    for i, record in enumerate(combined_records):
        if i not in geocoded_results:
            continue
        
        db_record = map_to_database_fields(record)
        address = db_record.get('address')
        coords = geocoded_results[i]
        
        # Find nearest property
        nearest_prop_id = None
        min_distance = float('inf')
        
        for prop_id, (prop_lon, prop_lat) in property_centroids.items():
            distance = haversine_distance(coords[0], coords[1], prop_lon, prop_lat)
            if distance < min_distance and distance <= max_distance_km:
                min_distance = distance
                nearest_prop_id = prop_id
        
        if nearest_prop_id:
            # Only match if not already matched or if this is closer
            if nearest_prop_id not in matches or matches[nearest_prop_id][1] > min_distance:
                matches[nearest_prop_id] = (i, min_distance)
    
    print(f"  ✅ Matched {len(matches):,} addresses to properties")
    
    # Step 5: Update properties
    print("\nStep 5: Updating properties...")
    updated = 0
    
    if not dry_run:
        updates = []
        for prop_id, (cama_idx, distance) in matches.items():
            if cama_idx < len(combined_records):
                db_record = map_to_database_fields(combined_records[cama_idx])
                address = db_record.get('address')
                if address:
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
    print("✅ Geocoding and matching complete!")
    print("=" * 60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Fix Torrington addresses using geocoding')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--limit', type=int, help='Limit number of addresses (for testing)')
    parser.add_argument('--service', choices=['nominatim', 'google', 'mapbox'], 
                       help='Geocoding service to use')
    args = parser.parse_args()
    
    if args.service:
        os.environ['GEOCODE_SERVICE'] = args.service
    
    db = SessionLocal()
    try:
        fix_addresses_with_geocoding(db, dry_run=args.dry_run, limit=args.limit)
    finally:
        db.close()
