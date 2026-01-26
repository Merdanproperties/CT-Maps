"""
Generic CAMA Verification Module
Works for any town/municipality with 0% mismatch tolerance
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models import Property
from scripts.data_import.import_bridgeport_cama_2025 import (
    read_cleaned_excel,
    read_raw_csv,
    match_and_combine,
    normalize_address
)

def get_file_paths(municipality: str) -> Dict[str, str]:
    """
    Auto-detect file paths based on municipality name
    Returns paths to cleaned Excel and CSV files
    """
    base_path = "/Users/jacobmermelstein/Desktop/CT Data"
    cleaned_file = f"{base_path}/2025 Post Duplicate Clean/{municipality}_CAMA_2025_CLEANED.xlsx"
    csv_file = f"{base_path}/2025 Parcel Collection/{municipality}_CAMA_2025.csv"
    
    return {
        'cleaned_excel': cleaned_file,
        'csv': csv_file
    }

def find_excel_match_for_property(
    prop: Property,
    excel_records: List[Dict],
    parcel_lookup: Dict[str, int],
    address_lookup: Dict[str, List[Dict]]
) -> Optional[Dict]:
    """
    Find matching cleaned Excel record for a property
    Returns the best matching Excel record or None
    """
    # Strategy 1: Parcel ID match
    if prop.parcel_id:
        parcel_id_str = str(prop.parcel_id).strip()
        if parcel_id_str and parcel_id_str != 'nan':
            if parcel_id_str in parcel_lookup:
                excel_idx = parcel_lookup[parcel_id_str]
                if excel_idx < len(excel_records):
                    return excel_records[excel_idx]
    
    # Strategy 2: Address match (normalized)
    if prop.address:
        norm_addr = normalize_address(prop.address)
        if norm_addr and norm_addr in address_lookup:
            matches = address_lookup[norm_addr]
            if len(matches) == 1:
                return matches[0]
            elif len(matches) > 1:
                # Multiple matches - use best match (exact address match)
                for match in matches:
                    excel_addr = match.get('Property Address', '')
                    if excel_addr and normalize_address(excel_addr) == norm_addr:
                        return match
                # Return first match if no exact match
                return matches[0]
    
    return None

def compare_cama_fields(prop: Property, excel_record: Dict) -> Dict:
    """
    Compare property CAMA fields with cleaned Excel record
    Returns dict of mismatches and missing fields
    """
    mismatches = []
    missing_in_db = []
    missing_in_excel = []
    
    # Owner Name
    excel_owner = str(excel_record.get('Full Name', '')).strip() if pd.notna(excel_record.get('Full Name')) else ''
    db_owner = prop.owner_name or ''
    if excel_owner and excel_owner != db_owner:
        mismatches.append({
            'field': 'owner_name',
            'excel': excel_owner,
            'database': db_owner
        })
    elif excel_owner and not db_owner:
        missing_in_db.append('owner_name')
    
    # Property Address
    excel_address = str(excel_record.get('Property Address', '')).strip() if pd.notna(excel_record.get('Property Address')) else ''
    db_address = prop.address or ''
    if excel_address:
        norm_excel = normalize_address(excel_address)
        norm_db = normalize_address(db_address) if db_address else ''
        if norm_excel != norm_db:
            mismatches.append({
                'field': 'address',
                'excel': excel_address,
                'database': db_address
            })
    
    # Mailing Address
    excel_mailing = str(excel_record.get('Mailing Address', '')).strip() if pd.notna(excel_record.get('Mailing Address')) else ''
    db_mailing = prop.owner_address or ''
    if excel_mailing and excel_mailing != db_mailing:
        mismatches.append({
            'field': 'owner_address',
            'excel': excel_mailing,
            'database': db_mailing
        })
    elif excel_mailing and not db_mailing:
        missing_in_db.append('owner_address')
    
    # Mailing City
    excel_city = str(excel_record.get('Mailing City', '')).strip() if pd.notna(excel_record.get('Mailing City')) else ''
    db_city = prop.owner_city or ''
    if excel_city and excel_city != db_city:
        mismatches.append({
            'field': 'owner_city',
            'excel': excel_city,
            'database': db_city
        })
    elif excel_city and not db_city:
        missing_in_db.append('owner_city')
    
    # Mailing State
    excel_state = str(excel_record.get('Mailing State', '')).strip() if pd.notna(excel_record.get('Mailing State')) else ''
    db_state = prop.owner_state or ''
    if excel_state and excel_state != db_state:
        mismatches.append({
            'field': 'owner_state',
            'excel': excel_state,
            'database': db_state
        })
    elif excel_state and not db_state:
        missing_in_db.append('owner_state')
    
    # Sale Price
    excel_sale_price = excel_record.get('Sale Price')
    if pd.notna(excel_sale_price):
        try:
            excel_price = float(excel_sale_price)
            db_price = prop.last_sale_price or 0
            if excel_price != db_price:
                mismatches.append({
                    'field': 'last_sale_price',
                    'excel': excel_price,
                    'database': db_price
                })
        except (ValueError, TypeError):
            pass
    
    # Sale Date
    excel_sale_date = excel_record.get('Sale Date')
    if pd.notna(excel_sale_date):
        try:
            if isinstance(excel_sale_date, str):
                excel_date = pd.to_datetime(excel_sale_date).date()
            else:
                excel_date = excel_sale_date.date() if hasattr(excel_sale_date, 'date') else excel_sale_date
            db_date = prop.last_sale_date
            if excel_date != db_date:
                mismatches.append({
                    'field': 'last_sale_date',
                    'excel': str(excel_date),
                    'database': str(db_date) if db_date else None
                })
        except (ValueError, TypeError):
            pass
    
    return {
        'mismatches': mismatches,
        'missing_in_db': missing_in_db,
        'missing_in_excel': missing_in_excel
    }

def verify_cama_data(municipality: str, db: Session) -> Dict:
    """
    Verify all CAMA data for a municipality matches cleaned Excel file
    Returns detailed report with 0% mismatch requirement
    Raises ValueError if mismatches found (fail-fast)
    """
    print(f"\n{'='*60}")
    print(f"Verifying CAMA Data for {municipality}")
    print(f"{'='*60}")
    print(f"\nCRITICAL: Cleaned Excel file is SINGLE SOURCE OF TRUTH")
    
    # Get file paths
    file_paths = get_file_paths(municipality)
    cleaned_file = file_paths['cleaned_excel']
    csv_file = file_paths['csv']
    
    # Check if files exist
    if not Path(cleaned_file).exists():
        raise FileNotFoundError(f"Cleaned Excel file not found: {cleaned_file}")
    
    print(f"File: {Path(cleaned_file).name}")
    
    # Step 1: Load cleaned Excel file
    print("\nStep 1: Loading cleaned Excel file...")
    cleaned_df = read_cleaned_excel(cleaned_file)
    
    # Load CSV if it exists (for supplementing)
    raw_lookup = {}
    if Path(csv_file).exists():
        _, raw_lookup = read_raw_csv(csv_file)
    
    combined_records = match_and_combine(cleaned_df, raw_lookup)
    
    print(f"  Loaded {len(combined_records):,} records from cleaned Excel file")
    
    # Step 2: Build Excel lookups
    print("\nStep 2: Building Excel lookups...")
    parcel_lookup = {}  # parcel_id -> excel_index
    address_lookup = {}  # normalized_address -> [excel_records]
    
    for idx, record in enumerate(combined_records):
        # Parcel ID lookup
        parcel_id = record.get('parcel_id')
        if not parcel_id and 'raw_Parcel ID' in record:
            parcel_id = str(record['raw_Parcel ID']).strip()
        
        if parcel_id and parcel_id != 'nan' and parcel_id:
            parcel_lookup[str(parcel_id).strip()] = idx
        
        # Address lookup
        address = record.get('Property Address')
        if address:
            norm_addr = normalize_address(address)
            if norm_addr:
                if norm_addr not in address_lookup:
                    address_lookup[norm_addr] = []
                address_lookup[norm_addr].append(record)
    
    print(f"  Built parcel lookup: {len(parcel_lookup):,} entries")
    print(f"  Built address lookup: {len(address_lookup):,} unique addresses")
    
    # Step 3: Load all database properties
    print("\nStep 3: Loading database properties...")
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{municipality}%")
    ).all()
    
    print(f"  Loaded {len(properties):,} properties from database")
    
    # Step 4: Verify each property
    print("\nStep 4: Verifying CAMA data for each property...")
    matched = []
    unmatched = []
    mismatched = []
    missing_data = []
    
    for i, prop in enumerate(properties, 1):
        if i % 1000 == 0:
            print(f"  Progress: {i:,}/{len(properties):,} | Matched: {len(matched):,} | Unmatched: {len(unmatched):,} | Mismatched: {len(mismatched):,}")
        
        excel_match = find_excel_match_for_property(prop, combined_records, parcel_lookup, address_lookup)
        
        if excel_match:
            comparison = compare_cama_fields(prop, excel_match)
            
            if comparison['mismatches']:
                mismatched.append({
                    'property_id': prop.id,
                    'parcel_id': prop.parcel_id,
                    'address': prop.address,
                    'mismatches': comparison['mismatches']
                })
            
            if comparison['missing_in_db']:
                missing_data.append({
                    'property_id': prop.id,
                    'parcel_id': prop.parcel_id,
                    'address': prop.address,
                    'missing_fields': comparison['missing_in_db']
                })
            
            matched.append({
                'property_id': prop.id,
                'parcel_id': prop.parcel_id,
                'address': prop.address,
                'has_mismatches': len(comparison['mismatches']) > 0,
                'has_missing': len(comparison['missing_in_db']) > 0
            })
        else:
            unmatched.append({
                'property_id': prop.id,
                'parcel_id': prop.parcel_id,
                'address': prop.address
            })
    
    # Step 5: Generate report
    print("\n" + "=" * 60)
    print("VERIFICATION REPORT")
    print("=" * 60)
    
    print(f"\n📊 Summary:")
    print(f"  Total properties: {len(properties):,}")
    print(f"  ✅ Matched to cleaned Excel: {len(matched):,}")
    print(f"  ❌ Unmatched: {len(unmatched):,}")
    print(f"  ⚠️  Mismatched data: {len(mismatched):,}")
    print(f"  ⚠️  Missing data in database: {len(missing_data):,}")
    
    # Calculate mismatch rate
    total_issues = len(mismatched) + len(missing_data)
    mismatch_rate = (total_issues / len(properties) * 100) if properties else 0
    
    print(f"\n⚠️  Mismatch Rate: {mismatch_rate:.2f}%")
    
    # 0% Mismatch Tolerance - Fail if any mismatches
    if total_issues > 0:
        print(f"\n❌ FAILURE: Mismatch rate is {mismatch_rate:.2f}% (required: 0%)")
        print(f"   {len(mismatched):,} properties have mismatched data")
        print(f"   {len(missing_data):,} properties have missing data")
        
        # Show sample mismatches
        if mismatched:
            print(f"\n⚠️  Sample Properties with Mismatched Data (first 10):")
            for item in mismatched[:10]:
                print(f"    Property ID {item['property_id']}: {item['address']} (Parcel: {item['parcel_id']})")
                for mismatch in item['mismatches'][:3]:  # Show first 3 mismatches
                    print(f"      {mismatch['field']}: Excel='{mismatch['excel']}' vs DB='{mismatch['database']}'")
        
        # Show sample missing data
        if missing_data:
            print(f"\n⚠️  Sample Properties with Missing Data (first 10):")
            for item in missing_data[:10]:
                print(f"    Property ID {item['property_id']}: {item['address']} (Parcel: {item['parcel_id']})")
                print(f"      Missing: {', '.join(item['missing_fields'])}")
        
        # Show sample unmatched
        if unmatched:
            print(f"\n⚠️  Sample Unmatched Properties (first 10):")
            for item in unmatched[:10]:
                print(f"    Property ID {item['property_id']}: {item['address']} (Parcel: {item['parcel_id']})")
        
        raise ValueError(
            f"Verification failed: {total_issues:,} issues found (mismatch rate: {mismatch_rate:.2f}%). "
            f"0% mismatch tolerance requires all issues to be resolved."
        )
    else:
        print(f"\n✅ SUCCESS: 0% mismatch rate achieved!")
        print(f"   All {len(properties):,} properties verified successfully")
    
    return {
        'municipality': municipality,
        'total': len(properties),
        'matched': len(matched),
        'unmatched': len(unmatched),
        'mismatched': len(mismatched),
        'missing_data': len(missing_data),
        'mismatch_rate': mismatch_rate,
        'mismatched_list': mismatched,
        'missing_data_list': missing_data,
        'unmatched_list': unmatched,
        'status': 'PASS' if total_issues == 0 else 'FAIL'
    }

def find_mismatches(municipality: str, db: Session) -> List[Dict]:
    """
    Find all properties with mismatched CAMA data
    Returns list of mismatched properties (does not raise error)
    """
    result = verify_cama_data(municipality, db)
    return result['mismatched_list'] + result['missing_data_list']

def check_completeness(municipality: str, db: Session) -> Dict:
    """
    Check data completeness for a municipality
    Returns completeness statistics
    """
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{municipality}%")
    ).all()
    
    total = len(properties)
    if total == 0:
        return {
            'municipality': municipality,
            'total': 0,
            'completeness': 0.0,
            'missing_owner': 0,
            'missing_address': 0,
            'missing_assessed': 0
        }
    
    missing_owner = sum(1 for p in properties if not p.owner_name or p.owner_name == '')
    missing_address = sum(1 for p in properties if not p.address or p.address == '')
    missing_assessed = sum(1 for p in properties if not p.assessed_value or p.assessed_value == 0)
    
    completeness = ((total - missing_owner - missing_address) / total * 100) if total > 0 else 0
    
    return {
        'municipality': municipality,
        'total': total,
        'completeness': completeness,
        'missing_owner': missing_owner,
        'missing_address': missing_address,
        'missing_assessed': missing_assessed,
        'missing_owner_pct': (missing_owner / total * 100) if total > 0 else 0,
        'missing_address_pct': (missing_address / total * 100) if total > 0 else 0,
        'missing_assessed_pct': (missing_assessed / total * 100) if total > 0 else 0
    }
