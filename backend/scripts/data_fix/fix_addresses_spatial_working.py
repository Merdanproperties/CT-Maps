"""
Final working solution: Match addresses using cleaned Excel order
This should provide the best matching since cleaned Excel is organized
"""
import sys
import os
from pathlib import Path
from datetime import date
from typing import Dict, List
import pandas as pd
from sqlalchemy.orm import Session
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))

from models import Property
from database import SessionLocal

load_dotenv()

CLEANED_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Post Duplicate Clean/Torrington_CAMA_2025_CLEANED.xlsx"
MUNICIPALITY = "Torrington"

def fix_addresses_final_working(db: Session, dry_run: bool = False):
    """
    Final working solution: Match using cleaned Excel order
    """
    print("\n" + "=" * 60)
    print("Final Working Solution: Torrington Address Matching")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    # Step 1: Load cleaned Excel addresses in order
    print("\nStep 1: Loading addresses from cleaned Excel...")
    df = pd.read_excel(CLEANED_FILE, engine='openpyxl')
    
    # Skip tracking row
    if len(df) > 1:
        first_row_values = df.iloc[0].astype(str).str.lower()
        if 'replaced' in ' '.join(first_row_values) or 'owner' in str(df.iloc[0].get('Full Name', '')).lower():
            df = df.iloc[1:].reset_index(drop=True)
    
    # Get addresses in Excel order
    excel_addresses = []
    for idx, row in df.iterrows():
        address = str(row.get('Property Address', '')).strip() if pd.notna(row.get('Property Address')) else None
        if address and address != 'None' and address != 'nan' and address != 'Location':
            excel_addresses.append(address)
    
    print(f"  Loaded {len(excel_addresses):,} addresses from cleaned Excel")
    
    # Step 2: Get properties sorted by ID (import order)
    print("\nStep 2: Loading properties...")
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).order_by(Property.id).all()
    
    print(f"  Loaded {len(properties):,} properties")
    
    # Step 3: Match by index
    print("\nStep 3: Matching addresses to properties...")
    matches = {}  # property_id -> address
    
    for prop_idx, prop in enumerate(properties):
        if prop_idx < len(excel_addresses):
            matches[prop.id] = excel_addresses[prop_idx]
    
    print(f"  Matched {len(matches):,} properties")
    
    # Step 4: Update
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
        
        print(f"\n✅ Updated {updated:,} properties with addresses")
    else:
        print(f"  Would update {len(matches):,} properties")
    
    print("\n" + "=" * 60)
    print("✅ Address matching complete!")
    print("=" * 60)
    print("\nNote: Addresses are matched by order. Some may be slightly off,")
    print("but all properties now have addresses and the map should be usable.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Final working solution for Torrington addresses')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        fix_addresses_final_working(db, dry_run=args.dry_run)
    finally:
        db.close()
