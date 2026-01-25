"""
Script to import CAMA data for Bridgeport properties that are missing CAMA data
Reads the coverage report and attempts to match missing properties with CAMA data
"""
import sys
import os
import re
import csv
import argparse
from pathlib import Path
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from models import Property
from database import SessionLocal

load_dotenv()

# File paths
RAW_CSV_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Parcel Collection/Bridgeport_CAMA_2025.csv"
CLEANED_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Post Duplicate Clean/Bridgeport_CAMA_2025_CLEANED.xlsx"
MUNICIPALITY = "Bridgeport"

def normalize_address(addr: str) -> str:
    """
    Normalize address for matching: uppercase, remove extra spaces, standardize abbreviations
    Returns base address (without unit numbers) for better matching
    """
    if not addr or pd.isna(addr):
        return ""
    
    addr = str(addr).strip().upper()
    
    # Remove unit numbers (e.g., "#103", "APT 5", "UNIT 2")
    addr = re.sub(r'\s*#\s*\d+', '', addr)
    addr = re.sub(r'\s*(APT|APARTMENT|UNIT|STE|SUITE)\s*\d+', '', addr, flags=re.IGNORECASE)
    
    # Standardize common abbreviations
    replacements = {
        r'\bST\b': 'STREET',
        r'\bAVE\b': 'AVENUE',
        r'\bAV\b': 'AVENUE',
        r'\bRD\b': 'ROAD',
        r'\bDR\b': 'DRIVE',
        r'\bLN\b': 'LANE',
        r'\bCT\b': 'COURT',
        r'\bPL\b': 'PLACE',
        r'\bBLVD\b': 'BOULEVARD',
        r'\bPKWY\b': 'PARKWAY',
        r'\bTR\b': 'TERRACE',
        r'\bCR\b': 'CIRCLE',
        r'\bNA\b': 'NORTH AVENUE',
    }
    
    for pattern, replacement in replacements.items():
        addr = re.sub(pattern, replacement, addr)
    
    # Remove extra spaces
    addr = re.sub(r'\s+', ' ', addr).strip()
    
    return addr

def read_coverage_report(report_file: str) -> List[Dict]:
    """
    Read the coverage report and extract missing parcel IDs and addresses
    """
    missing_properties = []
    
    with open(report_file, 'r') as f:
        reader = csv.reader(f)
        lines = list(reader)
        
        # Find the "Missing Parcels" section
        header_found = False
        for i, row in enumerate(lines):
            if len(row) >= 2 and row[0] == 'Parcel ID' and row[1] == 'Address':
                header_found = True
                continue
            
            if header_found and len(row) >= 2:
                parcel_id = row[0].strip() if row[0] else None
                address = row[1].strip() if row[1] else None
                
                # Skip empty rows and the "None" entry
                if parcel_id and address and parcel_id != 'None' and address != 'None':
                    missing_properties.append({
                        'parcel_id': parcel_id,
                        'address': address
                    })
    
    return missing_properties

def load_cama_data() -> Tuple[Dict[str, List[Dict]], Dict[str, List[Dict]]]:
    """
    Load CAMA data from both raw CSV and cleaned Excel for matching
    Returns: (raw_csv_lookup, cleaned_excel_lookup)
    """
    print("Loading CAMA data sources...")
    
    # Load raw CSV
    raw_csv_lookup = {}
    if os.path.exists(RAW_CSV_FILE):
        print(f"  Reading raw CSV: {RAW_CSV_FILE}")
        df_raw = pd.read_csv(RAW_CSV_FILE, low_memory=False)
        
        if 'Property Address' in df_raw.columns and 'Parcel ID' in df_raw.columns:
            for idx, row in df_raw.iterrows():
                addr = str(row['Property Address']).strip() if pd.notna(row['Property Address']) else ''
                parcel_id = str(row['Parcel ID']).strip() if pd.notna(row['Parcel ID']) else ''
                
                if addr:
                    norm_addr = normalize_address(addr)
                    if norm_addr:
                        if norm_addr not in raw_csv_lookup:
                            raw_csv_lookup[norm_addr] = []
                        raw_csv_lookup[norm_addr].append({
                            'parcel_id': parcel_id,
                            'address': addr,
                            'row_data': row.to_dict()
                        })
        
        print(f"  Loaded {len(raw_csv_lookup)} unique addresses from raw CSV")
    
    # Load cleaned Excel
    cleaned_excel_lookup = {}
    if os.path.exists(CLEANED_FILE):
        print(f"  Reading cleaned Excel: {CLEANED_FILE}")
        df_cleaned = pd.read_excel(CLEANED_FILE, engine='openpyxl')
        
        # Skip tracking row
        if len(df_cleaned) > 1:
            first_row_values = df_cleaned.iloc[0].astype(str).str.lower()
            if 'replaced' in ' '.join(first_row_values) or 'owner' in str(df_cleaned.iloc[0].get('Full Name', '')).lower():
                df_cleaned = df_cleaned.iloc[1:].reset_index(drop=True)
        
        if 'Property Address' in df_cleaned.columns:
            for idx, row in df_cleaned.iterrows():
                addr = str(row['Property Address']).strip() if pd.notna(row['Property Address']) else ''
                
                if addr:
                    norm_addr = normalize_address(addr)
                    if norm_addr:
                        if norm_addr not in cleaned_excel_lookup:
                            cleaned_excel_lookup[norm_addr] = []
                        cleaned_excel_lookup[norm_addr].append(row.to_dict())
        
        print(f"  Loaded {len(cleaned_excel_lookup)} unique addresses from cleaned Excel")
    
    return raw_csv_lookup, cleaned_excel_lookup

def find_cama_match(missing_prop: Dict, raw_csv_lookup: Dict, cleaned_excel_lookup: Dict) -> Optional[Dict]:
    """
    Try to find CAMA data for a missing property using multiple matching strategies
    """
    parcel_id = missing_prop['parcel_id']
    address = missing_prop['address']
    norm_addr = normalize_address(address)
    
    matches = []
    
    # Strategy 1: Exact address match
    if norm_addr:
        # Check raw CSV
        if norm_addr in raw_csv_lookup:
            for match in raw_csv_lookup[norm_addr]:
                matches.append(('exact_address_raw', match))
        
        # Check cleaned Excel
        if norm_addr in cleaned_excel_lookup:
            for match in cleaned_excel_lookup[norm_addr]:
                matches.append(('exact_address_cleaned', match))
    
    # Strategy 2: Partial address match (one contains the other)
    if norm_addr and len(norm_addr) >= 5:
        for lookup_addr, lookup_matches in raw_csv_lookup.items():
            if lookup_addr and len(lookup_addr) >= 5:
                if norm_addr in lookup_addr or lookup_addr in norm_addr:
                    for match in lookup_matches:
                        matches.append(('partial_address_raw', match))
                    break
        
        for lookup_addr, lookup_matches in cleaned_excel_lookup.items():
            if lookup_addr and len(lookup_addr) >= 5:
                if norm_addr in lookup_addr or lookup_addr in norm_addr:
                    for match in lookup_matches:
                        matches.append(('partial_address_cleaned', match))
                    break
    
    # Strategy 3: Parcel ID match (if CAMA parcel ID matches database parcel ID)
    if parcel_id:
        for lookup_addr, lookup_matches in raw_csv_lookup.items():
            for match in lookup_matches:
                match_parcel_id = str(match.get('parcel_id', '')).strip()
                if match_parcel_id == parcel_id:
                    matches.append(('parcel_id_match', match))
                    break
    
    # Return best match (prefer exact address matches)
    if matches:
        # Sort by match quality
        match_priority = {
            'exact_address_raw': 1,
            'exact_address_cleaned': 2,
            'parcel_id_match': 3,
            'partial_address_raw': 4,
            'partial_address_cleaned': 5
        }
        matches.sort(key=lambda x: match_priority.get(x[0], 99))
        return matches[0][1]
    
    return None

def map_to_database_fields(combined_record: Dict) -> Dict:
    """
    Map combined record to database field names (same as in import_cama_2025_hybrid.py)
    """
    db_record = {}
    
    # From cleaned file
    if 'Full Name' in combined_record:
        db_record['owner_name'] = str(combined_record['Full Name']).strip() if pd.notna(combined_record['Full Name']) else None
    
    if 'Property Address' in combined_record:
        db_record['address'] = str(combined_record['Property Address']).strip() if pd.notna(combined_record['Property Address']) else None
    
    if 'Property City' in combined_record:
        city = str(combined_record['Property City']).strip() if pd.notna(combined_record['Property City']) else None
        db_record['city'] = city
        db_record['municipality'] = city
    
    if 'Property Zip' in combined_record:
        zip_val = str(combined_record['Property Zip']).strip() if pd.notna(combined_record['Property Zip']) else None
        if zip_val:
            zip_val = zip_val.split('-')[0].split(' ')[0].strip()
            if len(zip_val) == 5 and zip_val.isdigit():
                db_record['zip_code'] = zip_val
            else:
                db_record['zip_code'] = None
        else:
            db_record['zip_code'] = None
    
    if 'Mailing Address' in combined_record:
        db_record['owner_address'] = str(combined_record['Mailing Address']).strip() if pd.notna(combined_record['Mailing Address']) else None
    
    if 'Mailing City' in combined_record:
        db_record['owner_city'] = str(combined_record['Mailing City']).strip() if pd.notna(combined_record['Mailing City']) else None
    
    if 'Mailing State' in combined_record:
        db_record['owner_state'] = str(combined_record['Mailing State']).strip() if pd.notna(combined_record['Mailing State']) else None
    
    # From raw CSV (prefixed with 'raw_' or direct from row_data)
    row_data = combined_record.get('row_data', {})
    
    if 'Assessed Total' in row_data:
        val = row_data['Assessed Total']
        db_record['assessed_value'] = float(val) if pd.notna(val) and val != '' else None
    
    if 'Assessed Land' in row_data:
        val = row_data['Assessed Land']
        db_record['land_value'] = float(val) if pd.notna(val) and val != '' else None
    
    if 'Assessed Building' in row_data:
        val = row_data['Assessed Building']
        db_record['building_value'] = float(val) if pd.notna(val) and val != '' else None
    
    if 'Valuation Year' in row_data:
        val = row_data['Valuation Year']
        if pd.notna(val) and val != '':
            try:
                year = int(float(val))
                db_record['assessment_year'] = year
                db_record['tax_year'] = year
            except (ValueError, TypeError):
                pass
    
    if 'Living Area' in row_data:
        val = row_data['Living Area']
        db_record['building_area_sqft'] = float(val) if pd.notna(val) and val != '' else None
    
    if 'Actual Year Built' in row_data:
        val = row_data['Actual Year Built']
        if pd.notna(val) and val != '':
            try:
                db_record['year_built'] = int(float(val))
            except (ValueError, TypeError):
                pass
    
    if 'Number of Bedroom' in row_data:
        val = row_data['Number of Bedroom']
        if pd.notna(val) and val != '':
            try:
                db_record['bedrooms'] = int(float(val))
            except (ValueError, TypeError):
                pass
    
    if 'Number of Bathrooms' in row_data:
        val = row_data['Number of Bathrooms']
        db_record['bathrooms'] = float(val) if pd.notna(val) and val != '' else None
    
    if 'Stories' in row_data:
        val = row_data['Stories']
        if pd.notna(val) and val != '':
            try:
                db_record['stories'] = int(float(val))
            except (ValueError, TypeError):
                pass
    
    if 'Total Rooms' in row_data:
        val = row_data['Total Rooms']
        if pd.notna(val) and val != '':
            try:
                db_record['total_rooms'] = int(float(val))
            except (ValueError, TypeError):
                pass
    
    if 'Roof Cover Description' in row_data:
        db_record['roof_material'] = str(row_data['Roof Cover Description']).strip() if pd.notna(row_data['Roof Cover Description']) else None
    
    if 'Roof Structure Description' in row_data:
        db_record['roof_type'] = str(row_data['Roof Structure Description']).strip() if pd.notna(row_data['Roof Structure Description']) else None
    
    if 'Heat Type Description' in row_data:
        db_record['heating_type'] = str(row_data['Heat Type Description']).strip() if pd.notna(row_data['Heat Type Description']) else None
    
    if 'AC Type Description' in row_data:
        db_record['cooling_type'] = str(row_data['AC Type Description']).strip() if pd.notna(row_data['AC Type Description']) else None
    
    if 'Number of Fireplaces' in row_data:
        val = row_data['Number of Fireplaces']
        if pd.notna(val) and val != '':
            try:
                db_record['fireplace_count'] = int(float(val))
            except (ValueError, TypeError):
                pass
    
    if 'Exterior Wall 1 Description' in row_data:
        db_record['exterior_finish'] = str(row_data['Exterior Wall 1 Description']).strip() if pd.notna(row_data['Exterior Wall 1 Description']) else None
    
    if 'Interior Wall 1 Description' in row_data:
        db_record['interior_finish'] = str(row_data['Interior Wall 1 Description']).strip() if pd.notna(row_data['Interior Wall 1 Description']) else None
    
    # Calculate is_absentee
    prop_addr = db_record.get('address', '')
    owner_addr = db_record.get('owner_address', '')
    if prop_addr and owner_addr:
        norm_prop = normalize_address(prop_addr)
        norm_owner = normalize_address(owner_addr)
        db_record['is_absentee'] = 1 if norm_prop != norm_owner else 0
    else:
        db_record['is_absentee'] = 0
    
    # Set metadata
    db_record['data_source'] = 'Bridgeport CAMA 2025 (Missing Properties Import)'
    db_record['last_updated'] = date.today()
    
    return db_record

def main():
    parser = argparse.ArgumentParser(description='Import CAMA data for missing Bridgeport properties')
    parser.add_argument('--report', type=str, help='Path to coverage report CSV file')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode - no database changes')
    parser.add_argument('--limit', type=int, help='Limit number of properties to process (for testing)')
    args = parser.parse_args()
    
    # Find most recent coverage report if not specified
    if not args.report:
        logs_dir = Path(__file__).parent.parent / 'logs'
        report_files = sorted(logs_dir.glob('bridgeport_cama_coverage_report_*.csv'), reverse=True)
        if report_files:
            args.report = str(report_files[0])
            print(f"Using most recent coverage report: {args.report}")
        else:
            print("❌ No coverage report found. Please specify --report")
            return
    
    if not os.path.exists(args.report):
        print(f"❌ Coverage report not found: {args.report}")
        return
    
    start_time = datetime.now()
    
    print("\n" + "=" * 60)
    print("Import CAMA Data for Missing Bridgeport Properties")
    print("=" * 60)
    print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No database changes will be made")
    
    db = SessionLocal()
    
    try:
        # Step 1: Read missing properties from coverage report
        print("\nStep 1: Reading missing properties from coverage report...")
        missing_properties = read_coverage_report(args.report)
        
        if args.limit:
            missing_properties = missing_properties[:args.limit]
            print(f"  Limited to first {args.limit} properties for testing")
        
        print(f"  Found {len(missing_properties)} missing properties")
        
        # Step 2: Load CAMA data
        print("\nStep 2: Loading CAMA data sources...")
        raw_csv_lookup, cleaned_excel_lookup = load_cama_data()
        
        # Step 3: Match and import
        print(f"\nStep 3: Matching and importing data for {len(missing_properties)} properties...")
        print("=" * 60)
        
        matched_count = 0
        updated_count = 0
        not_found_count = 0
        error_count = 0
        
        for i, missing_prop in enumerate(missing_properties, 1):
            if i % 50 == 0 or i == len(missing_properties):
                print(f"  Progress: {i:,}/{len(missing_properties):,} ({i/len(missing_properties)*100:.1f}%) | "
                      f"✅ Matched: {matched_count:,} | Updated: {updated_count:,} | ❌ Not found: {not_found_count:,}")
            
            try:
                # Find CAMA data match
                cama_match = find_cama_match(missing_prop, raw_csv_lookup, cleaned_excel_lookup)
                
                if not cama_match:
                    not_found_count += 1
                    continue
                
                matched_count += 1
                
                # Combine data
                combined = cama_match.copy()
                if isinstance(cama_match, dict) and 'row_data' in cama_match:
                    # It's from raw CSV, combine with cleaned Excel if available
                    norm_addr = normalize_address(missing_prop['address'])
                    if norm_addr in cleaned_excel_lookup:
                        cleaned_data = cleaned_excel_lookup[norm_addr][0]
                        combined.update(cleaned_data)
                elif isinstance(cama_match, dict):
                    # It's from cleaned Excel, try to add raw CSV data
                    norm_addr = normalize_address(missing_prop['address'])
                    if norm_addr in raw_csv_lookup:
                        raw_data = raw_csv_lookup[norm_addr][0]
                        combined['row_data'] = raw_data.get('row_data', {})
                
                # Map to database fields
                db_record = map_to_database_fields(combined)
                
                # Find property in database
                existing = db.query(Property).filter(
                    Property.parcel_id == missing_prop['parcel_id']
                ).first()
                
                if not existing:
                    # Try by address
                    norm_addr = normalize_address(missing_prop['address'])
                    existing = db.query(Property).filter(
                        Property.municipality.ilike(f"%{MUNICIPALITY}%")
                    ).all()
                    
                    for prop in existing:
                        if prop.address:
                            prop_norm = normalize_address(prop.address)
                            if prop_norm == norm_addr:
                                existing = prop
                                break
                    else:
                        existing = None
                
                if existing:
                    # Update property
                    for key, value in db_record.items():
                        if key != 'parcel_id':  # Don't update parcel_id
                            setattr(existing, key, value)
                    
                    if not args.dry_run:
                        db.commit()
                    
                    updated_count += 1
                else:
                    error_count += 1
                    if error_count <= 10:
                        print(f"  ⚠️  Property not found in database: {missing_prop['parcel_id']} - {missing_prop['address']}")
                
            except Exception as e:
                error_count += 1
                if error_count <= 10:
                    print(f"  ⚠️  Error processing {missing_prop['parcel_id']}: {e}")
                db.rollback()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print("\n" + "=" * 60)
        print("Import Summary:")
        print(f"  ✅ Matched with CAMA data: {matched_count:,}")
        print(f"  ✅ Updated in database: {updated_count:,}")
        print(f"  ❌ Not found in CAMA data: {not_found_count:,}")
        print(f"  ❌ Errors: {error_count:,}")
        if elapsed > 0:
            print(f"  ⏱️  Total time: {elapsed/60:.1f} minutes ({elapsed:.1f} seconds)")
        if args.dry_run:
            print("  🔍 This was a dry run - no actual changes were made")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
