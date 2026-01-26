"""
Update missing CAMA data for Torrington properties from Excel
Matches properties to Excel by address or parcel ID and updates missing owner info, assessed values, etc.
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from sqlalchemy.orm import Session
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models import Property
from database import SessionLocal
from scripts.data_import.import_bridgeport_cama_2025 import (
    read_cleaned_excel,
    read_raw_csv,
    match_and_combine,
    normalize_address,
    map_to_database_fields
)

CLEANED_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Post Duplicate Clean/Torrington_CAMA_2025_CLEANED.xlsx"
RAW_CSV_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Parcel Collection/Torrington_CAMA_2025.csv"
MUNICIPALITY = "Torrington"

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

def find_missing_cama_fields(prop: Property) -> List[str]:
    """Identify which CAMA fields are missing for a property"""
    missing = []
    
    if not prop.owner_name or prop.owner_name.strip() == '':
        missing.append('owner_name')
    
    if not prop.assessed_value or prop.assessed_value == 0:
        missing.append('assessed_value')
    
    if not prop.building_area_sqft or prop.building_area_sqft == 0:
        missing.append('building_area_sqft')
    
    if not prop.owner_address or prop.owner_address.strip() == '':
        missing.append('owner_address')
    
    if not prop.year_built:
        missing.append('year_built')
    
    return missing

def update_property_from_excel(
    prop: Property,
    excel_record: Dict,
    missing_fields: List[str],
    dry_run: bool = False
) -> Dict:
    """
    Update property with data from Excel record
    Only updates fields that are missing
    Returns dict of what was updated
    """
    updates = {}
    
    # Map Excel record to database fields
    db_record = map_to_database_fields(excel_record)
    
    # Only update missing fields
    if 'owner_name' in missing_fields and db_record.get('owner_name'):
        if not dry_run:
            prop.owner_name = db_record['owner_name']
        updates['owner_name'] = db_record['owner_name']
    
    if 'assessed_value' in missing_fields and db_record.get('assessed_value'):
        if not dry_run:
            prop.assessed_value = db_record['assessed_value']
        updates['assessed_value'] = db_record['assessed_value']
    
    if 'building_area_sqft' in missing_fields and db_record.get('building_area_sqft'):
        if not dry_run:
            prop.building_area_sqft = db_record['building_area_sqft']
        updates['building_area_sqft'] = db_record['building_area_sqft']
    
    if 'owner_address' in missing_fields and db_record.get('owner_address'):
        if not dry_run:
            prop.owner_address = db_record['owner_address']
        updates['owner_address'] = db_record['owner_address']
    
    if 'year_built' in missing_fields and db_record.get('year_built'):
        if not dry_run:
            prop.year_built = db_record['year_built']
        updates['year_built'] = db_record['year_built']
    
    # Update other fields if missing (but not in the required list)
    if not prop.owner_city and db_record.get('owner_city'):
        if not dry_run:
            prop.owner_city = db_record['owner_city']
        updates['owner_city'] = db_record['owner_city']
    
    if not prop.owner_state and db_record.get('owner_state'):
        if not dry_run:
            prop.owner_state = db_record['owner_state']
        updates['owner_state'] = db_record['owner_state']
    
    if not prop.owner_phone and db_record.get('owner_phone'):
        if not dry_run:
            prop.owner_phone = db_record['owner_phone']
        updates['owner_phone'] = db_record['owner_phone']
    
    if not prop.owner_email and db_record.get('owner_email'):
        if not dry_run:
            prop.owner_email = db_record['owner_email']
        updates['owner_email'] = db_record['owner_email']
    
    if not prop.last_sale_price and db_record.get('last_sale_price'):
        if not dry_run:
            prop.last_sale_price = db_record['last_sale_price']
        updates['last_sale_price'] = db_record['last_sale_price']
    
    if not prop.last_sale_date and db_record.get('last_sale_date'):
        if not dry_run:
            prop.last_sale_date = db_record['last_sale_date']
        updates['last_sale_date'] = db_record['last_sale_date']
    
    if not prop.property_type and db_record.get('property_type'):
        if not dry_run:
            prop.property_type = db_record['property_type']
        updates['property_type'] = db_record['property_type']
    
    if not prop.land_use and db_record.get('land_use'):
        if not dry_run:
            prop.land_use = db_record['land_use']
        updates['land_use'] = db_record['land_use']
    
    if not prop.land_value and db_record.get('land_value'):
        if not dry_run:
            prop.land_value = db_record['land_value']
        updates['land_value'] = db_record['land_value']
    
    if not prop.building_value and db_record.get('building_value'):
        if not dry_run:
            prop.building_value = db_record['building_value']
        updates['building_value'] = db_record['building_value']
    
    # Update address if missing
    if not prop.address and db_record.get('address'):
        if not dry_run:
            prop.address = db_record['address']
        updates['address'] = db_record['address']
    
    return updates

def update_missing_cama_data(db: Session, dry_run: bool = False):
    """
    Update missing CAMA data for Torrington properties from Excel
    """
    print("\n" + "=" * 60)
    print("Updating Missing CAMA Data for Torrington Properties")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No database changes will be made")
    
    # Step 1: Find properties missing CAMA data
    print("\nStep 1: Finding properties missing CAMA data...")
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).all()
    
    properties_needing_cama = []
    
    for prop in properties:
        missing_fields = find_missing_cama_fields(prop)
        if missing_fields:
            properties_needing_cama.append({
                'property': prop,
                'missing_fields': missing_fields
            })
    
    print(f"  Properties needing CAMA data: {len(properties_needing_cama):,}")
    
    if not properties_needing_cama:
        print("\n✅ All properties already have complete CAMA data!")
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
    total_fields_updated = 0
    
    for item in properties_needing_cama:
        prop = item['property']
        missing_fields = item['missing_fields']
        
        excel_record = None
        
        # Try parcel ID match first
        if prop.parcel_id:
            parcel_id_str = str(prop.parcel_id).strip()
            if parcel_id_str and parcel_id_str != 'nan':
                if parcel_id_str in parcel_lookup:
                    excel_record = parcel_lookup[parcel_id_str]
        
        # Try address match
        if not excel_record and prop.address:
            norm_addr = normalize_address(prop.address)
            if norm_addr and norm_addr in address_lookup:
                excel_record = address_lookup[norm_addr]
        
        # Update property if Excel record found
        if excel_record:
            updates = update_property_from_excel(prop, excel_record, missing_fields, dry_run)
            if updates:
                updated_count += 1
                total_fields_updated += len(updates)
                if updated_count % 100 == 0:
                    print(f"  Progress: {updated_count:,} properties updated ({total_fields_updated:,} fields)...")
        else:
            not_found_count += 1
    
    # Commit changes
    if not dry_run and updated_count > 0:
        print(f"\nStep 5: Committing changes to database...")
        db.commit()
        print(f"  ✅ Committed {updated_count:,} property updates ({total_fields_updated:,} fields)")
    elif dry_run:
        print(f"\n  🔍 DRY RUN: Would update {updated_count:,} properties ({total_fields_updated:,} fields)")
    
    print(f"\n📊 Update Summary:")
    print(f"  ✅ Updated: {updated_count:,} properties")
    print(f"  ❌ Not found in Excel: {not_found_count:,} properties")
    print(f"  📝 Total fields updated: {total_fields_updated:,}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Update missing CAMA data for Torrington properties')
    parser.add_argument('--dry-run', action='store_true', help='Run without making database changes')
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        update_missing_cama_data(db, dry_run=args.dry_run)
    finally:
        db.close()

if __name__ == "__main__":
    main()
