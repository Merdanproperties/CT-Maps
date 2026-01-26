"""
Final verification that all properties have correct CAMA data from cleaned Excel file
Verifies no properties are using wrong data source
"""
import sys
from pathlib import Path
from typing import Dict, List
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

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

def verify_property_completeness(db: Session):
    """Verify all properties have complete CAMA data"""
    print("\n" + "=" * 60)
    print("Verifying CAMA Data Completeness")
    print("=" * 60)
    
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).all()
    
    complete = 0
    missing_owner = 0
    missing_address = 0
    missing_assessed = 0
    missing_mailing = 0
    
    for prop in properties:
        has_owner = bool(prop.owner_name and prop.owner_name.strip())
        has_address = bool(prop.address and prop.address.strip())
        has_assessed = bool(prop.assessed_value and prop.assessed_value > 0)
        has_mailing = bool(prop.owner_address and prop.owner_address.strip())
        
        if has_owner and has_address and has_assessed:
            complete += 1
        else:
            if not has_owner:
                missing_owner += 1
            if not has_address:
                missing_address += 1
            if not has_assessed:
                missing_assessed += 1
            if not has_mailing:
                missing_mailing += 1
    
    print(f"\nTotal properties: {len(properties):,}")
    print(f"✅ Complete CAMA data: {complete:,} ({complete/len(properties)*100:.1f}%)")
    print(f"❌ Missing owner_name: {missing_owner:,}")
    print(f"❌ Missing address: {missing_address:,}")
    print(f"❌ Missing assessed_value: {missing_assessed:,}")
    print(f"❌ Missing mailing address: {missing_mailing:,}")
    
    return {
        'total': len(properties),
        'complete': complete,
        'missing_owner': missing_owner,
        'missing_address': missing_address,
        'missing_assessed': missing_assessed,
        'missing_mailing': missing_mailing
    }

def verify_data_source(db: Session):
    """Verify all properties have data from cleaned Excel file"""
    print("\n" + "=" * 60)
    print("Verifying Data Source (Cleaned Excel File)")
    print("=" * 60)
    
    # Load cleaned Excel file
    print("\nLoading cleaned Excel file...")
    cleaned_df = read_cleaned_excel(CLEANED_FILE)
    raw_df, raw_lookup = read_raw_csv(RAW_CSV_FILE)
    combined_records = match_and_combine(cleaned_df, raw_lookup)
    
    print(f"  Loaded {len(combined_records):,} records from cleaned Excel file")
    
    # Build lookups
    parcel_lookup = {}
    address_lookup = {}
    
    for idx, record in enumerate(combined_records):
        parcel_id = record.get('parcel_id')
        if not parcel_id and 'raw_Parcel ID' in record:
            parcel_id = str(record['raw_Parcel ID']).strip()
        
        if parcel_id and parcel_id != 'nan' and parcel_id:
            parcel_lookup[str(parcel_id).strip()] = idx
        
        address = record.get('Property Address')
        if address:
            norm_addr = normalize_address(address)
            if norm_addr:
                if norm_addr not in address_lookup:
                    address_lookup[norm_addr] = []
                address_lookup[norm_addr].append(record)
    
    # Check all properties
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).all()
    
    matched_to_excel = 0
    not_matched = []
    
    for prop in properties:
        is_matched = False
        
        # Check parcel ID match
        if prop.parcel_id and str(prop.parcel_id).strip() in parcel_lookup:
            is_matched = True
        
        # Check address match
        if not is_matched and prop.address:
            norm_addr = normalize_address(prop.address)
            if norm_addr and norm_addr in address_lookup:
                is_matched = True
        
        if is_matched:
            matched_to_excel += 1
        else:
            not_matched.append({
                'id': prop.id,
                'parcel_id': prop.parcel_id,
                'address': prop.address
            })
    
    print(f"\n📊 Data Source Verification:")
    print(f"  ✅ Matched to cleaned Excel: {matched_to_excel:,} ({matched_to_excel/len(properties)*100:.1f}%)")
    print(f"  ❌ Not matched: {len(not_matched):,}")
    
    if not_matched:
        print(f"\n⚠️  Properties not matched to cleaned Excel (first 10):")
        for item in not_matched[:10]:
            print(f"    ID {item['id']}: {item['address']} (Parcel: {item['parcel_id']})")
    
    return {
        'matched': matched_to_excel,
        'not_matched': len(not_matched),
        'not_matched_list': not_matched
    }

def verify_specific_property(db: Session, address: str):
    """Verify a specific property has correct data from cleaned Excel"""
    print("\n" + "=" * 60)
    print(f"Verifying Specific Property: {address}")
    print("=" * 60)
    
    # Find property
    search_term = f"%{address}%"
    normalized_q = address.upper().strip()
    normalized_q = normalized_q.replace(' ST ', ' STREET ').replace(' ST,', ' STREET,').replace(' ST', ' STREET')
    normalized_search_term = f"%{normalized_q}%"
    
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).filter(
        or_(
            Property.address.ilike(search_term),
            func.upper(Property.address).ilike(normalized_search_term)
        )
    ).all()
    
    if not properties:
        print(f"❌ Property not found: {address}")
        return False
    
    # Load cleaned Excel
    cleaned_df = read_cleaned_excel(CLEANED_FILE)
    raw_df, raw_lookup = read_raw_csv(RAW_CSV_FILE)
    combined_records = match_and_combine(cleaned_df, raw_lookup)
    
    # Find Excel match
    for prop in properties:
        print(f"\nProperty ID: {prop.id}")
        print(f"  Address: {prop.address}")
        print(f"  Parcel ID: {prop.parcel_id}")
        print(f"  Owner: {prop.owner_name}")
        
        # Find Excel match
        excel_match = None
        if prop.parcel_id:
            for record in combined_records:
                parcel_id = record.get('parcel_id')
                if not parcel_id and 'raw_Parcel ID' in record:
                    parcel_id = str(record['raw_Parcel ID']).strip()
                if parcel_id and str(parcel_id).strip() == str(prop.parcel_id).strip():
                    excel_match = record
                    break
        
        if not excel_match and prop.address:
            norm_addr = normalize_address(prop.address)
            for record in combined_records:
                excel_addr = record.get('Property Address', '')
                if excel_addr and normalize_address(excel_addr) == norm_addr:
                    excel_match = record
                    break
        
        if excel_match:
            excel_owner = str(excel_match.get('Full Name', '')).strip() if pd.notna(excel_match.get('Full Name')) else ''
            excel_address = str(excel_match.get('Property Address', '')).strip() if pd.notna(excel_match.get('Property Address')) else ''
            
            print(f"\n  ✅ Matched to cleaned Excel:")
            print(f"    Excel Owner: {excel_owner}")
            print(f"    Excel Address: {excel_address}")
            
            # Verify data matches
            if excel_owner == (prop.owner_name or ''):
                print(f"    ✅ Owner matches cleaned Excel")
            else:
                print(f"    ❌ Owner MISMATCH: DB='{prop.owner_name}' vs Excel='{excel_owner}'")
            
            if normalize_address(excel_address) == normalize_address(prop.address or ''):
                print(f"    ✅ Address matches cleaned Excel")
            else:
                print(f"    ❌ Address MISMATCH: DB='{prop.address}' vs Excel='{excel_address}'")
            
            return True
        else:
            print(f"  ❌ No match found in cleaned Excel file")
            return False

def main():
    """Main verification function"""
    print("\n" + "=" * 60)
    print("Final Verification: CAMA Data from Cleaned Excel File")
    print("=" * 60)
    print("\nCRITICAL: Cleaned Excel file is SINGLE SOURCE OF TRUTH")
    
    db = SessionLocal()
    
    try:
        # Verify completeness
        completeness = verify_property_completeness(db)
        
        # Verify data source
        data_source = verify_data_source(db)
        
        # Verify specific property
        verify_specific_property(db, "12 MARGERIE ST")
        
        # Summary
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"\nTotal Properties: {completeness['total']:,}")
        print(f"Complete CAMA Data: {completeness['complete']:,} ({completeness['complete']/completeness['total']*100:.1f}%)")
        print(f"Matched to Cleaned Excel: {data_source['matched']:,} ({data_source['matched']/completeness['total']*100:.1f}%)")
        
        if completeness['complete'] == completeness['total'] and data_source['matched'] == completeness['total']:
            print("\n✅ All verifications passed!")
            print("   All properties have complete CAMA data from cleaned Excel file")
        else:
            print("\n⚠️  Some verifications need attention")
            if completeness['complete'] < completeness['total']:
                print(f"   {completeness['total'] - completeness['complete']:,} properties missing CAMA data")
            if data_source['matched'] < completeness['total']:
                print(f"   {completeness['total'] - data_source['matched']:,} properties not matched to cleaned Excel")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
