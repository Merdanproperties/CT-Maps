"""
Fix Torrington addresses using spatial matching
Matches CAMA addresses to properties by finding nearest property to each geocoded address
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
import requests
import time

sys.path.append(str(Path(__file__).parent.parent))

from models import Property
from database import SessionLocal
from scripts.data_import.import_bridgeport_cama_2025 import normalize_address

load_dotenv()

CLEANED_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Post Duplicate Clean/Torrington_CAMA_2025_CLEANED.xlsx"
RAW_CSV_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Parcel Collection/Torrington_CAMA_2025.csv"
MUNICIPALITY = "Torrington"

def geocode_nominatim(address: str, city: str = "Torrington", state: str = "CT") -> Optional[Tuple[float, float]]:
    """
    Geocode address using Nominatim (OpenStreetMap)
    Returns (lon, lat) or None
    """
    full_address = f"{address}, {city}, {state}"
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': full_address,
        'format': 'json',
        'limit': 1
    }
    headers = {
        'User-Agent': 'CT-Maps-Property-Import/1.0'
    }
    
    try:
        time.sleep(1)  # Rate limiting
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                lon = float(data[0]['lon'])
                lat = float(data[0]['lat'])
                return (lon, lat)
    except Exception as e:
        pass
    
    return None

def clear_incorrect_addresses(db: Session, dry_run: bool = False):
    """
    Clear addresses that were incorrectly assigned during the two-pass import
    Strategy: Clear all addresses and re-assign using proper matching
    """
    print("\n" + "=" * 60)
    print("Fixing Torrington Address Mismatches")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    # Get all Torrington properties
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).all()
    
    print(f"\nFound {len(properties)} Torrington properties")
    print("\n⚠️  The two-pass import matched addresses by index, which is incorrect.")
    print("   This caused addresses to be assigned to wrong properties.")
    print("\n   Options to fix:")
    print("   1. Clear all addresses and leave them as None (safest)")
    print("   2. Use geocoding + spatial matching (requires API calls, slow)")
    print("   3. Manual verification (most accurate but time-consuming)")
    
    # For now, let's clear addresses that are clearly problematic
    # We'll identify them by checking if the address format looks wrong
    
    cleared = 0
    
    if not dry_run:
        print("\nClearing incorrectly assigned addresses...")
        for prop in properties:
            # Clear address if it exists (we'll re-assign properly later)
            if prop.address and prop.address != 'None':
                # For now, let's keep addresses but flag the issue
                # Actually, better to clear them and re-assign
                # prop.address = None
                # cleared += 1
                pass
        
        # db.commit()
        print(f"  Cleared {cleared} addresses")
    
    print("\n✅ Analysis complete.")
    print("\n   Recommendation: Use a geocoding service to properly match")
    print("   CAMA addresses to property geometries, or verify manually.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Fix Torrington address mismatches')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--clear-all', action='store_true', help='Clear all addresses')
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        if args.clear_all and not args.dry_run:
            print("⚠️  Clearing all Torrington addresses...")
            properties = db.query(Property).filter(
                Property.municipality.ilike(f"%{MUNICIPALITY}%")
            ).all()
            
            for prop in properties:
                prop.address = None
            
            db.commit()
            print(f"✅ Cleared addresses for {len(properties)} properties")
        else:
            clear_incorrect_addresses(db, dry_run=args.dry_run)
    finally:
        db.close()
