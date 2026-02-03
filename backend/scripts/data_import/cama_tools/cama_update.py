"""
Generic CAMA Update Module
Works for any town/municipality
Ensures cleaned Excel is single source of truth
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import date
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from models import Property
from scripts.data_import.import_bridgeport_cama_2025 import (
    read_cleaned_excel,
    read_raw_csv,
    match_and_combine,
    normalize_address,
    map_to_database_fields
)
from scripts.data_import.verification.cama_verification import get_file_paths

def build_excel_lookups(excel_records: List[Dict]) -> Tuple[Dict[str, int], Dict[str, List[Dict]]]:
    """
    Build lookup dictionaries from cleaned Excel records:
    - parcel_lookup: parcel_id -> excel_index
    - address_lookup: normalized_address -> [excel_records]
    """
    parcel_lookup = {}
    address_lookup = {}
    
    for idx, record in enumerate(excel_records):
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
    
    return parcel_lookup, address_lookup

def find_best_excel_match(
    prop: Property,
    excel_records: List[Dict],
    parcel_lookup: Dict[str, int],
    address_lookup: Dict[str, List[Dict]]
) -> Optional[Dict]:
    """
    Find best matching cleaned Excel record for a property
    Uses multiple strategies in priority order
    """
    # Strategy 1: Parcel ID match (most reliable)
    if prop.parcel_id:
        parcel_id_str = str(prop.parcel_id).strip()
        if parcel_id_str and parcel_id_str != 'nan':
            if parcel_id_str in parcel_lookup:
                excel_idx = parcel_lookup[parcel_id_str]
                if excel_idx < len(excel_records):
                    return excel_records[excel_idx]
    
    # Strategy 2: Exact normalized address match
    if prop.address:
        norm_addr = normalize_address(prop.address)
        if norm_addr and norm_addr in address_lookup:
            matches = address_lookup[norm_addr]
            if len(matches) == 1:
                return matches[0]
            elif len(matches) > 1:
                # Multiple matches - find best by exact address match
                for match in matches:
                    excel_addr = match.get('Property Address', '')
                    if excel_addr and normalize_address(excel_addr) == norm_addr:
                        return match
                # Return first match if no exact match
                return matches[0]
    
    # Strategy 3: Partial address match (fuzzy)
    if prop.address:
        norm_addr = normalize_address(prop.address)
        if norm_addr:
            # Try to find partial matches
            for lookup_addr, matches in address_lookup.items():
                if norm_addr and lookup_addr:
                    # Check if street name matches
                    norm_street = ' '.join(norm_addr.split()[1:]) if len(norm_addr.split()) > 1 else norm_addr
                    lookup_street = ' '.join(lookup_addr.split()[1:]) if len(lookup_addr.split()) > 1 else lookup_addr
                    if norm_street == lookup_street:
                        # Street name matches, return first match
                        return matches[0]
    
    return None

def update_property_from_cleaned_excel(
    prop: Property,
    excel_record: Dict,
    municipality: str,
    dry_run: bool = False
) -> Dict:
    """
    Update property with CAMA data from cleaned Excel record
    Returns dict of what was updated
    """
    updates = {}
    
    # Map Excel record to database fields
    db_record = map_to_database_fields(excel_record)
    
    # Update ALL fields from cleaned Excel (SINGLE SOURCE OF TRUTH)
    # Full Name → owner_name
    if 'owner_name' in db_record and db_record['owner_name']:
        if not dry_run:
            prop.owner_name = db_record['owner_name']
        updates['owner_name'] = db_record['owner_name']
    
    # Property Address → address
    if 'address' in db_record and db_record['address']:
        if not dry_run:
            prop.address = db_record['address']
        updates['address'] = db_record['address']
    
    # Mailing Address → owner_address
    if 'owner_address' in db_record and db_record['owner_address']:
        if not dry_run:
            prop.owner_address = db_record['owner_address']
        updates['owner_address'] = db_record['owner_address']
    
    # Mailing City → owner_city
    if 'owner_city' in db_record and db_record['owner_city']:
        if not dry_run:
            prop.owner_city = db_record['owner_city']
        updates['owner_city'] = db_record['owner_city']
    
    # Mailing State → owner_state
    if 'owner_state' in db_record and db_record['owner_state']:
        if not dry_run:
            prop.owner_state = db_record['owner_state']
        updates['owner_state'] = db_record['owner_state']
    
    # Mailing Zip → owner_zip
    if 'owner_zip' in db_record and db_record['owner_zip']:
        if not dry_run:
            prop.owner_zip = db_record['owner_zip']
        updates['owner_zip'] = db_record['owner_zip']
    
    # Sale Price → last_sale_price
    if 'last_sale_price' in db_record and db_record['last_sale_price'] is not None:
        if not dry_run:
            prop.last_sale_price = db_record['last_sale_price']
        updates['last_sale_price'] = db_record['last_sale_price']
    
    # Sale Date → last_sale_date
    if 'last_sale_date' in db_record and db_record['last_sale_date']:
        if not dry_run:
            prop.last_sale_date = db_record['last_sale_date']
        updates['last_sale_date'] = db_record['last_sale_date']
    
    # Style Description → property_type
    if 'property_type' in db_record and db_record['property_type']:
        if not dry_run:
            prop.property_type = db_record['property_type']
        updates['property_type'] = db_record['property_type']
    
    # State Use Description → land_use
    if 'land_use' in db_record and db_record['land_use']:
        if not dry_run:
            prop.land_use = db_record['land_use']
        updates['land_use'] = db_record['land_use']
    
    # Zoning → zoning
    if 'zoning' in db_record and db_record['zoning']:
        if not dry_run:
            prop.zoning = db_record['zoning']
        updates['zoning'] = db_record['zoning']
    
    # Email → owner_email
    if 'owner_email' in db_record and db_record['owner_email']:
        if not dry_run:
            prop.owner_email = db_record['owner_email']
        updates['owner_email'] = db_record['owner_email']
    
    # Phone → owner_phone
    if 'owner_phone' in db_record and db_record['owner_phone']:
        if not dry_run:
            prop.owner_phone = db_record['owner_phone']
        updates['owner_phone'] = db_record['owner_phone']
    
    # Assessed values (from CSV supplement if available)
    if 'assessed_value' in db_record and db_record['assessed_value'] is not None:
        if not dry_run:
            prop.assessed_value = db_record['assessed_value']
        updates['assessed_value'] = db_record['assessed_value']
    
    if 'land_value' in db_record and db_record['land_value'] is not None:
        if not dry_run:
            prop.land_value = db_record['land_value']
        updates['land_value'] = db_record['land_value']
    
    if 'building_value' in db_record and db_record['building_value'] is not None:
        if not dry_run:
            prop.building_value = db_record['building_value']
        updates['building_value'] = db_record['building_value']
    
    # Building details (from CSV supplement)
    if 'building_area_sqft' in db_record and db_record['building_area_sqft']:
        if not dry_run:
            prop.building_area_sqft = db_record['building_area_sqft']
        updates['building_area_sqft'] = db_record['building_area_sqft']
    
    if 'year_built' in db_record and db_record['year_built']:
        if not dry_run:
            prop.year_built = db_record['year_built']
        updates['year_built'] = db_record['year_built']
    
    # Update municipality from Excel "Property City" (source of truth)
    if 'municipality' in db_record and db_record['municipality']:
        if not dry_run:
            prop.municipality = db_record['municipality']
        updates['municipality'] = db_record['municipality']
    else:
        # Fallback to parameter if Excel doesn't have "Property City"
        if not dry_run:
            prop.municipality = municipality
        updates['municipality'] = municipality

    if not dry_run:
        prop.last_updated = date.today()
    
    return updates

def update_all_cama_from_cleaned_excel(municipality: str, db: Session, dry_run: bool = False) -> Dict:
    """
    Update ALL properties with CAMA data from cleaned Excel file
    CRITICAL: Cleaned Excel is SINGLE SOURCE OF TRUTH
    """
    print(f"\n{'='*60}")
    print(f"Updating All CAMA Data for {municipality}")
    print(f"{'='*60}")
    print(f"\nCRITICAL: Cleaned Excel file is SINGLE SOURCE OF TRUTH")
    print(f"CSV only supplements fields missing in cleaned Excel")
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No database changes will be made")
    
    # Get file paths
    file_paths = get_file_paths(municipality)
    cleaned_file = file_paths['cleaned_excel']
    csv_file = file_paths['csv']
    
    # Check if cleaned file exists
    if not Path(cleaned_file).exists():
        raise FileNotFoundError(f"Cleaned Excel file not found: {cleaned_file}")
    
    # Step 1: Load cleaned Excel file (SINGLE SOURCE OF TRUTH)
    print("\nStep 1: Loading cleaned Excel file...")
    cleaned_df = read_cleaned_excel(cleaned_file)
    
    # Load CSV if it exists (for supplementing)
    raw_lookup = {}
    if Path(csv_file).exists():
        _, raw_lookup = read_raw_csv(csv_file)
    
    combined_records = match_and_combine(cleaned_df, raw_lookup)
    
    print(f"  ✅ Loaded {len(combined_records):,} records from cleaned Excel file")
    if raw_lookup:
        print(f"  📝 CSV supplements additional fields")
    
    # Step 2: Build Excel lookups
    print("\nStep 2: Building Excel lookups...")
    parcel_lookup, address_lookup = build_excel_lookups(combined_records)
    
    print(f"  Built parcel lookup: {len(parcel_lookup):,} entries")
    print(f"  Built address lookup: {len(address_lookup):,} unique addresses")
    
    # Step 3: Load all database properties
    print("\nStep 3: Loading database properties...")
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{municipality}%")
    ).all()
    
    print(f"  Loaded {len(properties):,} properties from database")
    
    # Step 4: Update each property
    print("\nStep 4: Updating properties with cleaned Excel data...")
    print("  CRITICAL: Every property must get data from cleaned Excel file")
    
    updated_count = 0
    not_found_count = 0
    total_fields_updated = 0
    
    for i, prop in enumerate(properties, 1):
        if i % 1000 == 0:
            print(f"  Progress: {i:,}/{len(properties):,} | Updated: {updated_count:,} | Not found: {not_found_count:,}")
        
        # Find best matching Excel record
        excel_match = find_best_excel_match(prop, combined_records, parcel_lookup, address_lookup)
        
        if excel_match:
            # Update property from cleaned Excel
            updates = update_property_from_cleaned_excel(prop, excel_match, municipality, dry_run)
            
            if updates:
                updated_count += 1
                total_fields_updated += len(updates)
        else:
            not_found_count += 1
            if not_found_count <= 10:
                print(f"      ⚠️  No Excel match for: {prop.address} (Parcel: {prop.parcel_id})")
    
    # Step 5: Commit changes
    if not dry_run and updated_count > 0:
        print(f"\nStep 5: Committing changes to database...")
        db.commit()
        print(f"  ✅ Committed {updated_count:,} property updates ({total_fields_updated:,} fields)")
    elif dry_run:
        print(f"\n  🔍 DRY RUN: Would update {updated_count:,} properties ({total_fields_updated:,} fields)")
    
    print(f"\n📊 Update Summary:")
    print(f"  ✅ Updated: {updated_count:,} properties")
    print(f"  ❌ Not found in cleaned Excel: {not_found_count:,} properties")
    print(f"  📝 Total fields updated: {total_fields_updated:,}")
    
    if not_found_count > 0:
        print(f"\n⚠️  {not_found_count:,} properties couldn't be matched to cleaned Excel file")
        print(f"   These should be reviewed manually")
    
    return {
        'municipality': municipality,
        'updated': updated_count,
        'not_found': not_found_count,
        'total_fields': total_fields_updated
    }

def fix_mismatches(municipality: str, db: Session, dry_run: bool = False) -> Dict:
    """
    Fix mismatched properties by updating them from cleaned Excel
    Returns update statistics
    """
    print(f"\n{'='*60}")
    print(f"Fixing Mismatches for {municipality}")
    print(f"{'='*60}")
    
    # First, find mismatches
    from scripts.data_import.verification.cama_verification import find_mismatches, verify_cama_data
    
    try:
        # Try to verify (will raise error if mismatches found)
        verify_cama_data(municipality, db)
        print("\n✅ No mismatches found - all data is correct!")
        return {
            'municipality': municipality,
            'updated': 0,
            'not_found': 0,
            'total_fields': 0
        }
    except ValueError as e:
        # Mismatches found - proceed to fix
        print(f"\n⚠️  Mismatches detected, fixing...")
        print(f"   Error: {str(e)}")
    
    # Update all properties from cleaned Excel
    return update_all_cama_from_cleaned_excel(municipality, db, dry_run)
