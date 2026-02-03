"""
Identify Excel records that don't match any database properties
These are properties that exist in Excel/CSV but weren't imported from geodatabase
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

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

def build_database_lookups(db: Session) -> Tuple[Dict[str, int], Dict[str, List[int]]]:
    """
    Build lookup dictionaries for existing database properties:
    - parcel_lookup: parcel_id -> property_id
    - address_lookup: normalized_address -> [property_id, ...]
    """
    print("Building database property lookups...")
    
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).all()
    
    parcel_lookup = {}
    address_lookup = {}
    
    for prop in properties:
        # Parcel ID lookup
        if prop.parcel_id:
            parcel_id_str = str(prop.parcel_id).strip()
            if parcel_id_str and parcel_id_str != 'nan':
                parcel_lookup[parcel_id_str] = prop.id
        
        # Address lookup (normalized)
        if prop.address:
            norm_addr = normalize_address(prop.address)
            if norm_addr:
                if norm_addr not in address_lookup:
                    address_lookup[norm_addr] = []
                address_lookup[norm_addr].append(prop.id)
    
    print(f"  Built parcel lookup: {len(parcel_lookup):,} entries")
    print(f"  Built address lookup: {len(address_lookup):,} unique addresses")
    
    return parcel_lookup, address_lookup

def identify_unmatched_excel_records(
    db: Session,
    excel_records: List[Dict],
    parcel_lookup: Dict[str, int],
    address_lookup: Dict[str, List[int]]
) -> List[Dict]:
    """
    Identify Excel records that don't match any database properties
    Returns list of unmatched Excel records with their data
    """
    print("\nIdentifying unmatched Excel records...")
    
    unmatched = []
    matched_count = 0
    
    for idx, cama_record in enumerate(excel_records):
        if (idx + 1) % 1000 == 0:
            print(f"  Progress: {idx + 1:,}/{len(excel_records):,} | Matched: {matched_count:,} | Unmatched: {len(unmatched):,}")
        
        is_matched = False
        
        # Try parcel ID match
        parcel_id = cama_record.get('parcel_id')
        if not parcel_id and 'raw_Parcel ID' in cama_record:
            parcel_id = str(cama_record['raw_Parcel ID']).strip()
        
        if parcel_id and parcel_id != 'nan' and parcel_id:
            if parcel_id in parcel_lookup:
                is_matched = True
                matched_count += 1
        
        # Try address match
        if not is_matched:
            cama_address = cama_record.get('Property Address')
            if cama_address:
                norm_addr = normalize_address(cama_address)
                if norm_addr and norm_addr in address_lookup:
                    is_matched = True
                    matched_count += 1
        
        # If not matched, add to unmatched list
        if not is_matched:
            unmatched.append({
                'excel_idx': idx,
                'address': cama_record.get('Property Address', ''),
                'parcel_id': parcel_id,
                'owner_name': cama_record.get('Full Name', ''),
                'record': cama_record  # Keep full record for later use
            })
    
    print(f"\n  ✅ Matched: {matched_count:,}")
    print(f"  ❌ Unmatched: {len(unmatched):,}")
    
    return unmatched

def generate_report(unmatched: List[Dict]):
    """Generate report of unmatched properties"""
    print("\n" + "=" * 60)
    print("UNMATCHED EXCEL RECORDS REPORT")
    print("=" * 60)
    
    print(f"\nTotal Unmatched Records: {len(unmatched):,}")
    
    # Show sample unmatched records
    if unmatched:
        print(f"\nSample Unmatched Records (first 20):")
        for item in unmatched[:20]:
            print(f"  Row {item['excel_idx']}: {item['address']} (Parcel: {item['parcel_id']})")
            if item['owner_name']:
                print(f"    Owner: {item['owner_name']}")
    
    # Count by address type
    with_address = sum(1 for item in unmatched if item['address'])
    without_address = len(unmatched) - with_address
    
    print(f"\n📊 Unmatched Records Summary:")
    print(f"  With address: {with_address:,}")
    print(f"  Without address: {without_address:,}")

def main():
    """Main function"""
    print("\n" + "=" * 60)
    print("Identifying Unmatched Excel Properties for Torrington")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Step 1: Build database lookups
        print("\nStep 1: Building database property lookups...")
        parcel_lookup, address_lookup = build_database_lookups(db)
        
        # Step 2: Load Excel data
        print("\nStep 2: Loading Excel CAMA data...")
        cleaned_df = read_cleaned_excel(CLEANED_FILE)
        raw_df, raw_lookup = read_raw_csv(RAW_CSV_FILE)
        combined_records = match_and_combine(cleaned_df, raw_lookup)
        
        print(f"  Loaded {len(combined_records):,} Excel records")
        
        # Step 3: Identify unmatched records
        print("\nStep 3: Identifying unmatched Excel records...")
        unmatched = identify_unmatched_excel_records(
            db,
            combined_records,
            parcel_lookup,
            address_lookup
        )
        
        # Step 4: Generate report
        generate_report(unmatched)
        
        return unmatched
        
    finally:
        db.close()

if __name__ == "__main__":
    unmatched = main()
    print("\n✅ Identification complete!")
    print(f"   Found {len(unmatched):,} unmatched Excel records")
