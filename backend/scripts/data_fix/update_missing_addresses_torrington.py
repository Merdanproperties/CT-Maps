"""
Update missing addresses for Torrington properties from Excel
Matches properties to Excel by spatial proximity or parcel ID and updates addresses
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from sqlalchemy.orm import Session
import re

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models import Property
from database import SessionLocal
from scripts.data_import.import_bridgeport_cama_2025 import (
    read_cleaned_excel,
    read_raw_csv,
    match_and_combine,
    normalize_address
)

CLEANED_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Post Duplicate Clean/Torrington_CAMA_2025_CLEANED.xlsx"
RAW_CSV_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Parcel Collection/Torrington_CAMA_2025.csv"
MUNICIPALITY = "Torrington"

def get_street_number(address: str) -> Optional[str]:
    """Extract street number from address (must start with number)"""
    if not address:
        return None
    match = re.match(r'^(\d+)', address.strip())
    return match.group(1) if match else None

def build_excel_lookups(excel_records: List[Dict]) -> Dict[str, Dict]:
    """
    Build lookup dictionaries from Excel:
    - parcel_lookup: parcel_id -> excel_record
    - address_lookup: normalized_address -> excel_record
    """
    parcel_lookup = {}
    address_lookup = {}
    
    for record in excel_records:
        # Parcel ID lookup
        parcel_id = record.get('parcel_id')
        if not parcel_id and 'raw_Parcel ID' in record:
            parcel_id = str(record['raw_Parcel ID']).strip()
        
        if parcel_id and parcel_id != 'nan' and parcel_id:
            parcel_lookup[parcel_id] = record
        
        # Address lookup
        address = record.get('Property Address')
        if address:
            norm_addr = normalize_address(address)
            if norm_addr:
                address_lookup[norm_addr] = record
    
    return parcel_lookup, address_lookup

def update_missing_addresses(db: Session, dry_run: bool = False):
    """
    Update missing addresses for Torrington properties from Excel
    """
    print("\n" + "=" * 60)
    print("Updating Missing Addresses for Torrington Properties")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No database changes will be made")
    
    # Step 1: Find properties missing addresses
    print("\nStep 1: Finding properties missing addresses...")
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).all()
    
    missing_address_props = []
    invalid_address_props = []
    
    for prop in properties:
        if not prop.address or prop.address.strip() == '':
            missing_address_props.append(prop)
        else:
            street_number = get_street_number(prop.address)
            if not street_number:
                invalid_address_props.append(prop)
    
    print(f"  Properties missing addresses: {len(missing_address_props):,}")
    print(f"  Properties with invalid addresses: {len(invalid_address_props):,}")
    print(f"  Total properties needing address updates: {len(missing_address_props) + len(invalid_address_props):,}")
    
    if not missing_address_props and not invalid_address_props:
        print("\n✅ All properties already have valid addresses!")
        return
    
    # Step 2: Load Excel data
    print("\nStep 2: Loading Excel CAMA data...")
    cleaned_df = read_cleaned_excel(CLEANED_FILE)
    raw_df, raw_lookup = read_raw_csv(RAW_CSV_FILE)
    combined_records = match_and_combine(cleaned_df, raw_lookup)
    
    print(f"  Loaded {len(combined_records):,} Excel records")
    
    # Step 3: Build Excel lookups
    print("\nStep 3: Building Excel lookups...")
    parcel_lookup, address_lookup = build_excel_lookups(combined_records)
    
    # Step 4: Match and update properties
    print("\nStep 4: Matching and updating properties...")
    updated_count = 0
    not_found_count = 0
    
    all_props_to_update = missing_address_props + invalid_address_props
    
    for prop in all_props_to_update:
        excel_record = None
        
        # Try parcel ID match first
        if prop.parcel_id:
            parcel_id_str = str(prop.parcel_id).strip()
            if parcel_id_str and parcel_id_str != 'nan':
                if parcel_id_str in parcel_lookup:
                    excel_record = parcel_lookup[parcel_id_str]
        
        # Try address match (if property has partial address)
        if not excel_record and prop.address:
            norm_addr = normalize_address(prop.address)
            if norm_addr and norm_addr in address_lookup:
                excel_record = address_lookup[norm_addr]
        
        # Update address if found
        if excel_record:
            new_address = excel_record.get('Property Address')
            if new_address and new_address.strip():
                # Verify address starts with number
                street_number = get_street_number(new_address)
                if street_number:
                    if not dry_run:
                        prop.address = new_address.strip()
                    updated_count += 1
                    if updated_count % 100 == 0:
                        print(f"  Progress: {updated_count:,} properties updated...")
                else:
                    # Address doesn't start with number, but still update it
                    if not dry_run:
                        prop.address = new_address.strip()
                    updated_count += 1
        else:
            not_found_count += 1
    
    # Commit changes
    if not dry_run and updated_count > 0:
        print(f"\nStep 5: Committing changes to database...")
        db.commit()
        print(f"  ✅ Committed {updated_count:,} address updates")
    elif dry_run:
        print(f"\n  🔍 DRY RUN: Would update {updated_count:,} addresses")
    
    print(f"\n📊 Update Summary:")
    print(f"  ✅ Updated: {updated_count:,}")
    print(f"  ❌ Not found in Excel: {not_found_count:,}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Update missing addresses for Torrington properties')
    parser.add_argument('--dry-run', action='store_true', help='Run without making database changes')
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        update_missing_addresses(db, dry_run=args.dry_run)
    finally:
        db.close()

if __name__ == "__main__":
    main()
