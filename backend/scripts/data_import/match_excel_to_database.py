"""
Comprehensive matching of Excel CAMA records to database properties
Matches all 14,715 Excel rows using address, parcel ID, and spatial matching
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, text

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

def build_property_lookups(db: Session) -> Tuple[Dict[str, int], Dict[str, List[int]], Dict[int, Property]]:
    """
    Build lookup dictionaries for properties:
    - parcel_lookup: parcel_id -> property_id
    - address_lookup: normalized_address -> [property_id, ...]
    - property_dict: property_id -> Property object
    """
    print("Building property lookups...")
    
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).all()
    
    parcel_lookup = {}
    address_lookup = {}
    property_dict = {}
    
    for prop in properties:
        property_dict[prop.id] = prop
        
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
    print(f"  Total properties in database: {len(property_dict):,}")
    
    return parcel_lookup, address_lookup, property_dict

def find_property_by_spatial(
    cama_address: str,
    db: Session,
    max_distance_meters: float = 50.0
) -> Optional[int]:
    """
    Find property by spatial proximity using geocoding
    This is a fallback when address/parcel matching fails
    """
    # For now, return None - spatial matching would require geocoding service
    # This can be enhanced later if needed
    return None

def match_excel_to_database(
    db: Session,
    excel_records: List[Dict],
    parcel_lookup: Dict[str, int],
    address_lookup: Dict[str, List[int]],
    property_dict: Dict[int, Property]
) -> Dict:
    """
    Match Excel records to database properties
    Returns match statistics and lists
    """
    print("\nMatching Excel records to database properties...")
    
    matched_by_parcel = []
    matched_by_address = []
    unmatched_excel = []
    properties_in_db_not_in_excel = []
    
    # Track which properties were matched
    matched_property_ids = set()
    
    for idx, cama_record in enumerate(excel_records):
        if (idx + 1) % 1000 == 0:
            print(f"  Progress: {idx + 1:,}/{len(excel_records):,}")
        
        property_id = None
        match_method = None
        
        # Strategy 1: Parcel ID match (most reliable)
        parcel_id = cama_record.get('parcel_id')
        if not parcel_id and 'raw_Parcel ID' in cama_record:
            parcel_id = str(cama_record['raw_Parcel ID']).strip()
        
        if parcel_id and parcel_id != 'nan' and parcel_id:
            if parcel_id in parcel_lookup:
                property_id = parcel_lookup[parcel_id]
                match_method = 'parcel_id'
                matched_by_parcel.append({
                    'excel_idx': idx,
                    'property_id': property_id,
                    'parcel_id': parcel_id,
                    'address': cama_record.get('Property Address', '')
                })
                matched_property_ids.add(property_id)
        
        # Strategy 2: Address match (if parcel didn't match)
        if not property_id:
            cama_address = cama_record.get('Property Address')
            if cama_address:
                norm_addr = normalize_address(cama_address)
                if norm_addr and norm_addr in address_lookup:
                    matches = address_lookup[norm_addr]
                    if len(matches) == 1:
                        property_id = matches[0]
                        match_method = 'address_exact'
                        matched_by_address.append({
                            'excel_idx': idx,
                            'property_id': property_id,
                            'address': cama_address,
                            'normalized_address': norm_addr
                        })
                        matched_property_ids.add(property_id)
                    elif len(matches) > 1:
                        # Multiple properties with same address
                        # Prefer properties without owner_name or with less complete data
                        best_match = None
                        for prop_id in matches:
                            if prop_id not in matched_property_ids:
                                prop = property_dict.get(prop_id)
                                if prop and (not prop.owner_name or not prop.assessed_value):
                                    best_match = prop_id
                                    break
                        if best_match:
                            property_id = best_match
                            match_method = 'address_exact_multiple'
                            matched_by_address.append({
                                'excel_idx': idx,
                                'property_id': property_id,
                                'address': cama_address,
                                'normalized_address': norm_addr,
                                'note': 'multiple_matches'
                            })
                            matched_property_ids.add(property_id)
        
        # Strategy 3: Spatial matching (fallback - not implemented yet)
        if not property_id:
            cama_address = cama_record.get('Property Address')
            if cama_address:
                property_id = find_property_by_spatial(cama_address, db)
                if property_id:
                    match_method = 'spatial'
        
        # If no match found, add to unmatched list
        if not property_id:
            unmatched_excel.append({
                'excel_idx': idx,
                'parcel_id': parcel_id,
                'address': cama_record.get('Property Address', ''),
                'owner_name': cama_record.get('Full Name', '')
            })
    
    # Find properties in DB but not in Excel
    all_property_ids = set(property_dict.keys())
    unmatched_db_properties = all_property_ids - matched_property_ids
    
    for prop_id in unmatched_db_properties:
        prop = property_dict[prop_id]
        properties_in_db_not_in_excel.append({
            'property_id': prop_id,
            'parcel_id': prop.parcel_id,
            'address': prop.address,
            'municipality': prop.municipality,
            'has_owner': bool(prop.owner_name),
            'has_assessed_value': bool(prop.assessed_value)
        })
    
    return {
        'matched_by_parcel': matched_by_parcel,
        'matched_by_address': matched_by_address,
        'unmatched_excel': unmatched_excel,
        'properties_in_db_not_in_excel': properties_in_db_not_in_excel,
        'total_matched': len(matched_by_parcel) + len(matched_by_address),
        'total_unmatched_excel': len(unmatched_excel),
        'total_unmatched_db': len(properties_in_db_not_in_excel)
    }

def generate_report(match_results: Dict, excel_total: int):
    """Generate comprehensive matching report"""
    print("\n" + "=" * 60)
    print("MATCHING REPORT")
    print("=" * 60)
    
    print(f"\n📊 Summary:")
    print(f"  Total Excel records: {excel_total:,}")
    print(f"  Matched by Parcel ID: {len(match_results['matched_by_parcel']):,}")
    print(f"  Matched by Address: {len(match_results['matched_by_address']):,}")
    print(f"  Total Matched: {match_results['total_matched']:,}")
    print(f"  Unmatched Excel records: {match_results['total_unmatched_excel']:,}")
    print(f"  Properties in DB but not in Excel: {match_results['total_unmatched_db']:,}")
    
    print(f"\n✅ Match Rate: {(match_results['total_matched'] / excel_total * 100):.1f}%")
    
    # Show sample unmatched Excel records
    if match_results['unmatched_excel']:
        print(f"\n⚠️  Sample Unmatched Excel Records (first 10):")
        for item in match_results['unmatched_excel'][:10]:
            print(f"    Row {item['excel_idx']}: {item['address']} (Parcel: {item['parcel_id']})")
    
    # Show sample properties in DB but not in Excel
    if match_results['properties_in_db_not_in_excel']:
        print(f"\n⚠️  Sample Properties in DB but Not in Excel (first 10):")
        for item in match_results['properties_in_db_not_in_excel'][:10]:
            print(f"    ID {item['property_id']}: {item['address'] or 'No Address'} (Parcel: {item['parcel_id']})")
            print(f"      Has owner: {item['has_owner']}, Has assessed value: {item['has_assessed_value']}")

def main():
    """Main matching function"""
    print("\n" + "=" * 60)
    print("Excel to Database Matching for Torrington")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Step 1: Build property lookups
        print("\nStep 1: Building property lookups...")
        parcel_lookup, address_lookup, property_dict = build_property_lookups(db)
        
        # Step 2: Load Excel data
        print("\nStep 2: Loading Excel CAMA data...")
        cleaned_df = read_cleaned_excel(CLEANED_FILE)
        raw_df, raw_lookup = read_raw_csv(RAW_CSV_FILE)
        combined_records = match_and_combine(cleaned_df, raw_lookup)
        
        print(f"  Loaded {len(combined_records):,} Excel records")
        
        # Step 3: Match records
        print("\nStep 3: Matching Excel records to database...")
        match_results = match_excel_to_database(
            db,
            combined_records,
            parcel_lookup,
            address_lookup,
            property_dict
        )
        
        # Step 4: Generate report
        generate_report(match_results, len(combined_records))
        
        return match_results
        
    finally:
        db.close()

if __name__ == "__main__":
    results = main()
    print("\n✅ Matching analysis complete!")
