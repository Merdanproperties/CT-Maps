"""
Geocode unmatched Excel addresses to get coordinates
Uses Nominatim/Google/Mapbox geocoding services
"""
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import time
import requests
from dotenv import load_dotenv
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.data_import.identify_unmatched_excel_properties import main as identify_unmatched

load_dotenv()

MUNICIPALITY = "Torrington"
GEOCODE_CACHE_FILE = "logs/geocode_unmatched_cache.json"
NOMINATIM_URL = os.getenv('NOMINATIM_URL', 'https://nominatim.openstreetmap.org')
GOOGLE_API_KEY = os.getenv('GOOGLE_GEOCODING_API_KEY')
MAPBOX_API_KEY = os.getenv('MAPBOX_ACCESS_TOKEN')
GEOCODE_SERVICE = os.getenv('GEOCODE_SERVICE', 'nominatim')  # nominatim, google, mapbox

def load_geocode_cache() -> Dict[str, Tuple[float, float]]:
    """Load cached geocoding results: address -> (lon, lat)"""
    if os.path.exists(GEOCODE_CACHE_FILE):
        try:
            with open(GEOCODE_CACHE_FILE, 'r') as f:
                data = json.load(f)
                # Convert list tuples to tuple tuples
                return {k: tuple(v) for k, v in data.items()}
        except Exception:
            return {}
    return {}

def save_geocode_cache(cache: Dict[str, Tuple[float, float]]):
    """Save geocoding results"""
    os.makedirs(os.path.dirname(GEOCODE_CACHE_FILE), exist_ok=True)
    with open(GEOCODE_CACHE_FILE, 'w') as f:
        # Convert tuples to lists for JSON serialization
        json.dump({k: list(v) for k, v in cache.items()}, f, indent=2)

def geocode_nominatim(address: str, city: str = "Torrington", state: str = "CT", retries: int = 3) -> Optional[Tuple[float, float]]:
    """Geocode using Nominatim"""
    full_address = f"{address}, {city}, {state}, USA"
    
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
            if not is_local:
                time.sleep(2 ** attempt)
    
    return None

def geocode_google(address: str, city: str = "Torrington", state: str = "CT") -> Optional[Tuple[float, float]]:
    """Geocode using Google Geocoding API"""
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
    """Geocode using Mapbox API"""
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
    """Geocode address using configured service"""
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
        if 'localhost' not in NOMINATIM_URL and '127.0.0.1' not in NOMINATIM_URL:
            time.sleep(1.1)
    
    # Cache result
    if coords and cache is not None:
        cache[address] = coords
    
    return coords

def geocode_unmatched_addresses(unmatched: List[Dict], dry_run: bool = False) -> List[Dict]:
    """
    Geocode unmatched Excel addresses
    Returns list of unmatched records with geocoded coordinates
    """
    print("\n" + "=" * 60)
    print("Geocoding Unmatched Excel Addresses")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No geocoding will be performed")
    
    # Load cache
    cache = load_geocode_cache()
    print(f"\nLoaded {len(cache):,} cached geocoding results")
    
    # Check geocoding service
    is_local = 'localhost' in NOMINATIM_URL or '127.0.0.1' in NOMINATIM_URL
    if GEOCODE_SERVICE == 'nominatim':
        if is_local:
            print(f"✅ Using local Nominatim at {NOMINATIM_URL} (no rate limits!)")
        else:
            print(f"⚠️  Using public Nominatim (1 req/sec) - will take ~{len(unmatched)} seconds")
    elif GEOCODE_SERVICE == 'google':
        print(f"✅ Using Google Geocoding API")
    elif GEOCODE_SERVICE == 'mapbox':
        print(f"✅ Using Mapbox Geocoding API")
    
    # Filter to records with addresses
    records_with_addresses = [r for r in unmatched if r.get('address')]
    print(f"\nTotal unmatched records: {len(unmatched):,}")
    print(f"Records with addresses: {len(records_with_addresses):,}")
    
    if not records_with_addresses:
        print("\n⚠️  No records with addresses to geocode")
        return []
    
    # Geocode addresses
    geocoded = []
    failed = []
    cached_count = 0
    
    print(f"\nGeocoding {len(records_with_addresses):,} addresses...")
    
    for i, record in enumerate(records_with_addresses, 1):
        address = record['address']
        
        if not dry_run:
            coords = geocode_address(address, MUNICIPALITY, "CT", cache)
            
            if coords:
                record['geocoded'] = True
                record['lon'] = coords[0]
                record['lat'] = coords[1]
                geocoded.append(record)
            else:
                record['geocoded'] = False
                failed.append(record)
            
            # Save cache periodically
            if i % 100 == 0:
                save_geocode_cache(cache)
                print(f"  Progress: {i:,}/{len(records_with_addresses):,} | Geocoded: {len(geocoded):,} | Failed: {len(failed):,} | Cached: {cached_count:,}")
        else:
            # In dry run, check cache only
            if address in cache:
                cached_count += 1
                record['geocoded'] = True
                record['lon'] = cache[address][0]
                record['lat'] = cache[address][1]
                geocoded.append(record)
            else:
                record['geocoded'] = False
                failed.append(record)
    
    # Save final cache
    if not dry_run:
        save_geocode_cache(cache)
    
    print(f"\n📊 Geocoding Summary:")
    print(f"  ✅ Geocoded: {len(geocoded):,}")
    print(f"  ❌ Failed: {len(failed):,}")
    if dry_run:
        print(f"  💾 Cached: {cached_count:,}")
    
    # Show sample failures
    if failed:
        print(f"\n⚠️  Sample Failed Geocoding (first 10):")
        for record in failed[:10]:
            print(f"    {record['address']}")
    
    # Save geocoded results to JSON file for next step
    output_file = "logs/geocoded_unmatched.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Prepare serializable records (remove any non-serializable objects)
    geocoded_serializable = []
    for record in geocoded:
        rec = {k: v for k, v in record.items() if k != 'record' or isinstance(v, (dict, list, str, int, float, bool, type(None)))}
        if 'record' in record:
            rec['record'] = record['record']  # Keep the full record
        geocoded_serializable.append(rec)
    
    with open(output_file, 'w') as f:
        json.dump(geocoded_serializable, f, indent=2, default=str)
    
    print(f"\n✅ Saved {len(geocoded):,} geocoded records to {output_file}")
    
    return geocoded

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Geocode unmatched Excel addresses')
    parser.add_argument('--dry-run', action='store_true', help='Run without geocoding (check cache only)')
    args = parser.parse_args()
    
    # First identify unmatched records
    print("Step 1: Identifying unmatched Excel records...")
    unmatched = identify_unmatched()
    
    if not unmatched:
        print("\n✅ All Excel records are matched!")
        return []
    
    # Then geocode them
    print("\nStep 2: Geocoding unmatched addresses...")
    geocoded = geocode_unmatched_addresses(unmatched, dry_run=args.dry_run)
    
    return geocoded

if __name__ == "__main__":
    geocoded = main()
    print("\n✅ Geocoding complete!")
    if geocoded:
        print(f"   Geocoded {len(geocoded):,} addresses")
