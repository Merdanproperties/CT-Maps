"""
BETTER SOLUTION: Reverse geocode property geometries to get addresses
This is more reliable than forward geocoding CAMA addresses!

We have:
- Property geometries (correct locations)
- Need: Addresses for those locations

Solution: Reverse geocode each property's centroid to get its address,
then match that to CAMA data to get owner/assessment info.
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

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from models import Property
from database import SessionLocal

load_dotenv()

MUNICIPALITY = "Torrington"
REVERSE_GEOCODE_CACHE_FILE = "logs/reverse_geocode_cache_torrington.json"
NOMINATIM_URL = os.getenv('NOMINATIM_URL', 'https://nominatim.openstreetmap.org')

def load_reverse_geocode_cache() -> Dict[str, str]:
    """Load cached reverse geocoding results: (lon,lat) -> address"""
    if os.path.exists(REVERSE_GEOCODE_CACHE_FILE):
        try:
            with open(REVERSE_GEOCODE_CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_reverse_geocode_cache(cache: Dict[str, str]):
    """Save reverse geocoding results"""
    os.makedirs(os.path.dirname(REVERSE_GEOCODE_CACHE_FILE), exist_ok=True)
    with open(REVERSE_GEOCODE_CACHE_FILE, 'w') as f:
        json.dump(cache, f)

def reverse_geocode_nominatim(lon: float, lat: float, retries: int = 3) -> Optional[str]:
    """
    Reverse geocode coordinates to get address
    Returns address string or None
    """
    cache_key = f"{lon:.6f},{lat:.6f}"
    
    base_url = NOMINATIM_URL.rstrip('/')
    is_local = 'localhost' in base_url or '127.0.0.1' in base_url
    
    for attempt in range(retries):
        try:
            url = f"{base_url}/reverse"
            params = {
                'lat': lat,
                'lon': lon,
                'format': 'json',
                'addressdetails': 1
            }
            headers = {
                'User-Agent': 'CT-Maps-Property-Import/1.0'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data and 'address' in data:
                    # Extract street address
                    addr = data.get('address', {})
                    
                    # Build address from components
                    house_number = addr.get('house_number', '')
                    road = addr.get('road', '')
                    city = addr.get('city', addr.get('town', addr.get('municipality', '')))
                    
                    if road:
                        address_parts = []
                        if house_number:
                            address_parts.append(house_number)
                        address_parts.append(road.upper())
                        address = ' '.join(address_parts)
                        return address
            elif response.status_code == 429:
                time.sleep(10)
                continue
        except requests.exceptions.RequestException as e:
            if attempt == retries - 1:
                pass  # Log on final attempt
            if not is_local:
                time.sleep(2 ** attempt)
    
    return None

def reverse_geocode_batch_worker(args: Tuple) -> List[Tuple[int, Optional[str]]]:
    """
    Worker function to reverse geocode a batch of coordinates
    """
    coordinates, cache = args
    results = []
    
    for prop_id, lon, lat in coordinates:
        cache_key = f"{lon:.6f},{lat:.6f}"
        
        # Check cache
        if cache_key in cache:
            results.append((prop_id, cache[cache_key]))
        else:
            address = reverse_geocode_nominatim(lon, lat)
            if address:
                cache[cache_key] = address
            results.append((prop_id, address))
            
            # Rate limiting for public API
            if 'localhost' not in NOMINATIM_URL and '127.0.0.1' not in NOMINATIM_URL:
                time.sleep(1.1)
    
    return results

def fix_addresses_reverse_geocode(db: Session, dry_run: bool = False, limit: Optional[int] = None):
    """
    Fix addresses by reverse geocoding property geometries
    This is MORE RELIABLE than forward geocoding CAMA addresses!
    """
    print("\n" + "=" * 60)
    print("Fixing Torrington Addresses Using Reverse Geocoding")
    print("=" * 60)
    print("\n💡 This approach is BETTER because:")
    print("   - We have correct property geometries (locations)")
    print("   - Reverse geocode to get addresses for those locations")
    print("   - More accurate than forward geocoding CAMA addresses")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    # Check if using local Nominatim
    is_local = 'localhost' in NOMINATIM_URL or '127.0.0.1' in NOMINATIM_URL
    if is_local:
        print(f"\n✅ Using local Nominatim at {NOMINATIM_URL} (no rate limits!)")
    else:
        print(f"\n⚠️  Using public Nominatim (1 req/sec) - will take ~3 hours")
        print("   💡 Install local Nominatim for faster results")
    
    # Load cache
    cache = load_reverse_geocode_cache()
    print(f"  Loaded {len(cache):,} cached reverse geocoding results")
    
    # Step 1: Get all properties with geometries
    print("\nStep 1: Loading property geometries...")
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).all()
    
    coordinates_to_geocode = []
    for prop in properties:
        if prop.geometry:
            try:
                result = db.execute(text(
                    'SELECT ST_X(ST_Centroid(geometry)) as lon, '
                    'ST_Y(ST_Centroid(geometry)) as lat '
                    'FROM properties WHERE id = :id'
                ), {'id': prop.id}).fetchone()
                
                if result and result[0] and result[1]:
                    coordinates_to_geocode.append((prop.id, float(result[0]), float(result[1])))
            except Exception:
                continue
    
    if limit:
        coordinates_to_geocode = coordinates_to_geocode[:limit]
        print(f"  Limited to {limit} properties for testing")
    
    print(f"  Found {len(coordinates_to_geocode):,} properties with geometries")
    
    # Step 2: Reverse geocode
    print("\nStep 2: Reverse geocoding property locations...")
    
    # Filter out cached
    coordinates_new = [(pid, lon, lat) for pid, lon, lat in coordinates_to_geocode 
                      if f"{lon:.6f},{lat:.6f}" not in cache]
    print(f"  {len(coordinates_new):,} properties need reverse geocoding")
    print(f"  {len(coordinates_to_geocode) - len(coordinates_new):,} already cached")
    
    reverse_geocoded = {}  # property_id -> address
    
    # Add cached results
    for prop_id, lon, lat in coordinates_to_geocode:
        cache_key = f"{lon:.6f},{lat:.6f}"
        if cache_key in cache:
            reverse_geocoded[prop_id] = cache[cache_key]
    
    # Reverse geocode new coordinates
    if coordinates_new:
        if is_local:
            # Parallel processing for local instance
            num_workers = cpu_count()
            chunk_size = max(10, len(coordinates_new) // num_workers)
            chunks = [coordinates_new[i:i+chunk_size] 
                     for i in range(0, len(coordinates_new), chunk_size)]
            
            print(f"  Reverse geocoding in parallel with {num_workers} workers...")
            with Pool(processes=num_workers) as pool:
                worker_args = [(chunk, cache) for chunk in chunks]
                for i, chunk_results in enumerate(pool.imap(reverse_geocode_batch_worker, worker_args), 1):
                    for prop_id, address in chunk_results:
                        if address:
                            reverse_geocoded[prop_id] = address
                            # Cache it
                            for pid, lon, lat in chunks[i-1]:
                                if pid == prop_id:
                                    cache[f"{lon:.6f},{lat:.6f}"] = address
                                    break
                    
                    print(f"  Progress: {i}/{len(chunks)} chunks | "
                          f"Geocoded: {len(reverse_geocoded):,}")
                    save_reverse_geocode_cache(cache)
        else:
            # Sequential for public API
            print("  Reverse geocoding sequentially (1 req/sec)...")
            start_time = datetime.now()
            for i, (prop_id, lon, lat) in enumerate(coordinates_new, 1):
                address = reverse_geocode_nominatim(lon, lat)
                if address:
                    reverse_geocoded[prop_id] = address
                    cache[f"{lon:.6f},{lat:.6f}"] = address
                
                if i % 100 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    rate = i / elapsed if elapsed > 0 else 0
                    remaining = (len(coordinates_new) - i) / rate if rate > 0 else 0
                    print(f"  Progress: {i:,}/{len(coordinates_new):,} | "
                          f"Rate: {rate:.2f}/sec | ETA: {remaining/60:.1f} min")
                    save_reverse_geocode_cache(cache)
    
    # Save final cache
    save_reverse_geocode_cache(cache)
    print(f"\n  ✅ Reverse geocoded {len(reverse_geocoded):,} properties")
    
    # Step 3: Update properties
    print("\nStep 3: Updating properties with reverse geocoded addresses...")
    updated = 0
    
    if not dry_run:
        updates = []
        for prop_id, address in reverse_geocoded.items():
            updates.append({'id': prop_id, 'address': address})
            
            if len(updates) >= 500:
                db.bulk_update_mappings(Property, updates)
                db.commit()
                updated += len(updates)
                print(f"  Progress: {updated:,}/{len(reverse_geocoded):,} updated")
                updates = []
        
        if updates:
            db.bulk_update_mappings(Property, updates)
            db.commit()
            updated += len(updates)
        
        print(f"\n✅ Updated {updated:,} properties with reverse geocoded addresses")
    else:
        print(f"  Would update {len(reverse_geocoded):,} properties")
    
    print("\n" + "=" * 60)
    print("✅ Reverse geocoding complete!")
    print("=" * 60)
    print("\nThis approach is better because:")
    print("  ✅ Uses correct property locations (geometries)")
    print("  ✅ Gets addresses directly from those locations")
    print("  ✅ More accurate than forward geocoding CAMA addresses")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Fix Torrington addresses using reverse geocoding')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--limit', type=int, help='Limit number of properties (for testing)')
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        fix_addresses_reverse_geocode(db, dry_run=args.dry_run, limit=args.limit)
    finally:
        db.close()
