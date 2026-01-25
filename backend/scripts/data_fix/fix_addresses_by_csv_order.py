"""
Fix Torrington addresses by matching using raw CSV row order
The raw CSV Location field has addresses in a specific order that should match properties
"""
import sys
import os
from pathlib import Path
from datetime import date
from typing import Dict, List, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))

from models import Property
from database import SessionLocal
from scripts.data_import.import_bridgeport_cama_2025 import normalize_address

load_dotenv()

RAW_CSV_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Parcel Collection/Torrington_CAMA_2025.csv"
MUNICIPALITY = "Torrington"

def fix_addresses_by_csv_order(db: Session, dry_run: bool = False):
    """
    Fix addresses by using raw CSV order - addresses should match properties in same order
    """
    print("\n" + "=" * 60)
    print("Fixing Torrington Addresses Using CSV Row Order")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    # Step 1: Load raw CSV addresses in order
    print("\nStep 1: Loading addresses from raw CSV...")
    df = pd.read_csv(RAW_CSV_FILE, low_memory=False)
    
    # Get addresses in CSV order
    csv_addresses = []
    for idx, row in df.iterrows():
        location = str(row.get('Location', '')).strip() if pd.notna(row.get('Location')) else None
        if location and location != 'None' and location != 'nan':
            csv_addresses.append((idx, location))
    
    print(f"  Loaded {len(csv_addresses):,} addresses from CSV")
    
    # Step 2: Get properties in database order (by ID, which should match import order)
    print("\nStep 2: Loading properties...")
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).order_by(Property.id).all()
    
    print(f"  Loaded {len(properties):,} properties")
    
    # Step 3: Match by index (CSV row order should match property import order)
    print("\nStep 3: Matching addresses to properties...")
    matches = {}  # property_id -> address
    
    # Match properties to CSV addresses by index
    for prop_idx, prop in enumerate(properties):
        if prop_idx < len(csv_addresses):
            csv_idx, address = csv_addresses[prop_idx]
            matches[prop.id] = address
    
    print(f"  Matched {len(matches):,} properties")
    
    # Step 4: Update properties
    print("\nStep 4: Updating properties...")
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
        
        print(f"\n✅ Updated {updated:,} properties")
    else:
        print(f"  Would update {len(matches):,} properties")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  CSV addresses: {len(csv_addresses):,}")
    print(f"  Properties: {len(properties):,}")
    print(f"  Matched: {len(matches):,}")
    if not dry_run:
        print(f"  Updated: {updated:,}")
    print("=" * 60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Fix Torrington addresses using CSV order')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        fix_addresses_by_csv_order(db, dry_run=args.dry_run)
    finally:
        db.close()
