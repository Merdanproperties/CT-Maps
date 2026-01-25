"""
Fix all missing addresses for properties:
1. First try to match from Excel file (by parcel ID or address matching)
2. For remaining, use reverse geocoding with Nominatim
"""
import sys
import os
from pathlib import Path
from datetime import date
from typing import Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv
import requests
import time
from multiprocessing import Pool, cpu_count
import json
from shapely import wkt

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from models import Property
from database import SessionLocal
from scripts.data_import.import_bridgeport_cama_2025 import normalize_address

load_dotenv()

NOMINATIM_URL = os.getenv('NOMINATIM_URL', 'http://localhost:8080')
REVERSE_GEOCODE_CACHE_FILE = "logs/reverse_geocode_cache_all.json"

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
        json.dump(cache, f, indent=2)

def reverse_geocode_nominatim(lon: float, lat: float, retries: int = 3) -> Optional[str]:
    """
    Reverse geocode coordinates to get address
    Returns address string or None
    """
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

def load_excel_addresses(municipality: str) -> Dict[str, str]:
    """Load addresses from Excel file, keyed by normalized address"""
    excel_file = f'/Users/jacobmermelstein/Desktop/CT Data/2025 Post Duplicate Clean/{municipality}_CAMA_2025_CLEANED.xlsx'
    
    if not os.path.exists(excel_file):
        return {}
    
    try:
        df = pd.read_excel(excel_file, engine='openpyxl')
        if len(df) > 1:
            first_row = df.iloc[0].astype(str).str.lower()
            if 'owner' in str(df.iloc[0].get('Full Name', '')).lower():
                df = df.iloc[1:].reset_index(drop=True)
        
        address_map = {}
        for idx, row in df.iterrows():
            addr = row.get('Property Address', '')
            if pd.notna(addr) and addr:
                normalized = normalize_address(str(addr))
                if normalized:
                    address_map[normalized] = str(addr).strip().upper()
        
        return address_map
    except Exception as e:
        print(f"  ⚠️  Error loading Excel for {municipality}: {e}")
        return {}

def process_property_batch(args: Tuple) -> List[Tuple[int, Optional[str]]]:
    """Process a batch of properties to get addresses"""
    property_ids, municipality, excel_addresses, cache = args
    
    results = []
    db = SessionLocal()
    
    try:
        for prop_id in property_ids:
            prop = db.query(Property).filter(Property.id == prop_id).first()
            if not prop:
                results.append((prop_id, None))
                continue
            
            # Skip if already has address
            if prop.address and prop.address != 'None' and prop.address.strip():
                results.append((prop_id, prop.address))
                continue
            
            address = None
            
            # Method 1: Try reverse geocoding first (fastest)
            if prop.geometry:
                try:
                    # Handle both WKT string and WKBElement
                    if hasattr(prop.geometry, 'desc'):
                        # It's a WKBElement, convert to WKT
                        from geoalchemy2.shape import to_shape
                        geom = to_shape(prop.geometry)
                    else:
                        # It's already a WKT string
                        geom = wkt.loads(str(prop.geometry))
                    
                    centroid = geom.centroid
                    lon, lat = centroid.x, centroid.y
                    
                    # Try reverse geocoding
                    cache_key = f"{lon:.6f},{lat:.6f}"
                    if cache_key in cache:
                        address = cache[cache_key]
                    else:
                        address = reverse_geocode_nominatim(lon, lat)
                        if address:
                            cache[cache_key] = address
                    
                    # Normalize and check if it matches Excel
                    if address:
                        normalized = normalize_address(address)
                        if normalized in excel_addresses:
                            # Use Excel version for consistency
                            address = excel_addresses[normalized]
                except Exception as e:
                    pass
            
            results.append((prop_id, address))
            
            # Rate limiting for local Nominatim (no limit, but be nice)
            if 'localhost' not in NOMINATIM_URL and '127.0.0.1' not in NOMINATIM_URL:
                time.sleep(1.1)  # 1 req/sec for public API
            else:
                time.sleep(0.05)  # Very small delay for local
            
    finally:
        db.close()
    
    return results

def fix_missing_addresses(municipality: str = None, dry_run: bool = False):
    """Fix all missing addresses"""
    print("=" * 60)
    print("Fixing Missing Addresses")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    db = SessionLocal()
    try:
        # Get properties without addresses
        query = db.query(Property).filter(
            (Property.address.is_(None)) | 
            (Property.address == '') | 
            (Property.address == 'None')
        )
        
        if municipality:
            query = query.filter(Property.municipality.ilike(f'%{municipality}%'))
        
        properties = query.all()
        
        print(f"\nFound {len(properties):,} properties without addresses")
        
        if len(properties) == 0:
            print("\n✅ All properties have addresses!")
            return
        
        # Load Excel addresses for matching
        municipalities = set()
        for prop in properties:
            municipalities.add(prop.municipality or '')
        
        excel_addresses = {}
        for mun in municipalities:
            if mun:
                print(f"\nLoading Excel addresses for {mun}...")
                mun_addresses = load_excel_addresses(mun)
                excel_addresses.update(mun_addresses)
                print(f"  Loaded {len(mun_addresses):,} addresses")
        
        # Load reverse geocode cache
        cache = load_reverse_geocode_cache()
        print(f"\nLoaded {len(cache):,} cached reverse geocoding results")
        
        # Process in parallel batches
        property_ids = [p.id for p in properties]
        num_workers = min(cpu_count(), 8)  # Limit workers to avoid overwhelming Nominatim
        chunk_size = max(100, len(property_ids) // num_workers)
        chunks = [property_ids[i:i+chunk_size] for i in range(0, len(property_ids), chunk_size)]
        
        print(f"\nProcessing {len(chunks)} batches with {num_workers} workers...")
        print(f"Using Nominatim at: {NOMINATIM_URL}")
        print(f"Estimated time: ~{len(property_ids) * 0.1 / 60:.1f} minutes")
        
        all_results = []
        completed = 0
        with Pool(num_workers) as pool:
            chunk_args = [(chunk, municipality, excel_addresses, cache) for chunk in chunks]
            batch_results = pool.imap(process_property_batch, chunk_args)
            
            for i, batch_result in enumerate(batch_results):
                all_results.extend(batch_result)
                completed += len(batch_result)
                if (i + 1) % 5 == 0 or i == len(chunks) - 1:
                    print(f"  Progress: {completed:,} / {len(property_ids):,} ({completed/len(property_ids)*100:.1f}%)")
        
        # Save cache
        save_reverse_geocode_cache(cache)
        
        # Update database
        updated = 0
        failed = 0
        
        print(f"\nUpdating database...")
        for prop_id, address in all_results:
            if not address:
                failed += 1
                continue
            
            prop = db.query(Property).filter(Property.id == prop_id).first()
            if prop:
                if not dry_run:
                    prop.address = address
                    updated += 1
                else:
                    print(f"  Would update {prop.parcel_id}: {address}")
                    updated += 1
        
        if not dry_run:
            db.commit()
        
        print(f"\n✅ Updated {updated:,} properties with addresses")
        if failed > 0:
            print(f"⚠️  {failed:,} properties still missing addresses")
        
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--municipality', help='Filter by municipality')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    args = parser.parse_args()
    
    fix_missing_addresses(municipality=args.municipality, dry_run=args.dry_run)
