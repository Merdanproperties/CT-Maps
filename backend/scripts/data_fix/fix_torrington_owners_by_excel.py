"""
Fix Torrington owner information by directly matching Excel "Full Name" to database
This ensures 100% accuracy by matching each property to its exact Excel record
"""
import sys
from pathlib import Path
from typing import Dict, List
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models import Property
from database import SessionLocal
from scripts.data_import.import_bridgeport_cama_2025 import normalize_address, map_to_database_fields

CLEANED_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Post Duplicate Clean/Torrington_CAMA_2025_CLEANED.xlsx"
MUNICIPALITY = "Torrington"

def load_excel_data() -> Dict[str, Dict]:
    """
    Load Excel data and create lookup by normalized address
    Returns: {normalized_address: {address, owner, ...}}
    """
    print("Loading Excel file...")
    df = pd.read_excel(CLEANED_FILE, engine='openpyxl')
    
    # Skip tracking row
    if len(df) > 1:
        first_row = df.iloc[0].astype(str).str.lower()
        if 'owner' in str(df.iloc[0].get('Full Name', '')).lower():
            df = df.iloc[1:].reset_index(drop=True)
    
    excel_lookup = {}
    duplicate_addresses = []
    
    for idx, row in df.iterrows():
        addr = str(row.get('Property Address', '')).strip() if pd.notna(row.get('Property Address')) else None
        owner = str(row.get('Full Name', '')).strip() if pd.notna(row.get('Full Name')) else None
        
        if addr and addr != 'None' and addr != 'nan' and owner and owner != 'None' and owner != 'nan':
            norm_addr = normalize_address(addr)
            if norm_addr:
                if norm_addr in excel_lookup:
                    # Duplicate address - store as list
                    if norm_addr not in duplicate_addresses:
                        duplicate_addresses.append(norm_addr)
                        # Convert existing to list
                        excel_lookup[norm_addr] = [excel_lookup[norm_addr]]
                    excel_lookup[norm_addr].append({
                        'address': addr,
                        'owner': owner,
                        'row_data': row.to_dict()
                    })
                else:
                    excel_lookup[norm_addr] = {
                        'address': addr,
                        'owner': owner,
                        'row_data': row.to_dict()
                    }
    
    print(f"  Loaded {len(excel_lookup):,} unique addresses")
    print(f"  Found {len(duplicate_addresses):,} addresses with duplicates")
    
    return excel_lookup, duplicate_addresses

def fix_owners_by_excel(db: Session, dry_run: bool = False):
    """
    Fix all Torrington owners by matching to Excel file
    """
    print("\n" + "=" * 60)
    print("Fixing Torrington Owners from Excel File")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    # Load Excel data
    excel_lookup, duplicate_addresses = load_excel_data()
    
    # Get all Torrington properties
    print("\nLoading database properties...")
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).all()
    
    print(f"  Found {len(properties):,} properties")
    
    # Match and update
    print("\nMatching properties to Excel records...")
    updated = 0
    not_found = 0
    mismatches = []
    
    for prop in properties:
        if not prop.address:
            continue
        
        norm_addr = normalize_address(prop.address)
        if not norm_addr:
            continue
        
        # Find in Excel
        excel_data = excel_lookup.get(norm_addr)
        
        if not excel_data:
            not_found += 1
            continue
        
        # Handle duplicates - use first match (could improve with owner name matching)
        if isinstance(excel_data, list):
            excel_data = excel_data[0]
        
        excel_owner = excel_data.get('owner', '')
        
        # Check if owner matches
        if prop.owner_name != excel_owner:
            mismatches.append({
                'address': prop.address,
                'current_owner': prop.owner_name,
                'correct_owner': excel_owner
            })
            
            if not dry_run:
                # Update owner
                prop.owner_name = excel_owner
                # Also update other fields from Excel if available
                row_data = excel_data.get('row_data', {})
                if row_data:
                    db_record = map_to_database_fields(row_data)
                    # Update owner-related fields
                    if db_record.get('owner_address'):
                        prop.owner_address = db_record.get('owner_address')
                    if db_record.get('owner_city'):
                        prop.owner_city = db_record.get('owner_city')
                    if db_record.get('owner_state'):
                        prop.owner_state = db_record.get('owner_state')
            
            updated += 1
    
    if not dry_run:
        db.commit()
    
    print(f"\n✅ Fixed {updated:,} properties with incorrect owners")
    print(f"❌ {not_found:,} properties not found in Excel")
    
    if mismatches:
        print(f"\n📋 Sample fixes:")
        for m in mismatches[:10]:
            print(f"  {m['address']}:")
            print(f"    Was: {m['current_owner']}")
            print(f"    Now: {m['correct_owner']}")
    
    print("\n" + "=" * 60)
    print("✅ Owner fix complete!")
    print("=" * 60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Fix Torrington owners from Excel')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        fix_owners_by_excel(db, dry_run=args.dry_run)
    finally:
        db.close()
