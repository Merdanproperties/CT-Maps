"""
Hybrid CAMA import script for Bridgeport 2025 data
Reads from cleaned Excel file (owner/address data) and raw CSV (assessments/building details)
Combines data and imports to database
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
CLEANED_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Post Duplicate Clean/Bridgeport_CAMA_2025_CLEANED.xlsx"
RAW_CSV_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Parcel Collection/Bridgeport_CAMA_2025.csv"
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
        r'\bRD\b': 'ROAD',
        r'\bDR\b': 'DRIVE',
        r'\bLN\b': 'LANE',
        r'\bCT\b': 'COURT',
        r'\bPL\b': 'PLACE',
        r'\bBLVD\b': 'BOULEVARD',
        r'\bPKWY\b': 'PARKWAY',
    }
    
    for pattern, replacement in replacements.items():
        addr = re.sub(pattern, replacement, addr)
    
    # Remove extra spaces
    addr = re.sub(r'\s+', ' ', addr).strip()
    
    return addr

def normalize_owner_name(name: str) -> str:
    """
    Normalize owner name for matching
    """
    if not name or pd.isna(name):
        return ""
    
    name = str(name).strip().upper()
    # Remove extra spaces
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def read_cleaned_excel(file_path: str, limit: Optional[int] = None) -> pd.DataFrame:
    """
    Read cleaned Excel file, skip tracking row, normalize addresses
    """
    print(f"Reading cleaned Excel file: {file_path}")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Cleaned file not found: {file_path}")
    
    # Read Excel - first row is header, second row is tracking row with mappings
    # We need to skip row 1 (index 1, which is the second row)
    df = pd.read_excel(file_path, engine='openpyxl')
    
    # Skip the tracking row (row 1, which contains column mapping info)
    if len(df) > 1:
        # Check if first data row looks like a tracking row (contains "Owner" or mapping text)
        first_row_values = df.iloc[0].astype(str).str.lower()
        if 'replaced' in ' '.join(first_row_values) or 'owner' in str(df.iloc[0].get('Full Name', '')).lower():
            df = df.iloc[1:].reset_index(drop=True)
            print("  Skipped tracking row")
    
    if limit:
        df = df.head(limit)
        print(f"  Limited to first {limit} records for testing")
    
    print(f"  Loaded {len(df)} records from cleaned file")
    print(f"  Columns: {list(df.columns)[:5]}...")  # Show first 5 columns
    
    # Normalize Property Address for matching
    if 'Property Address' in df.columns:
        df['normalized_address'] = df['Property Address'].apply(normalize_address)
    else:
        # Try case-insensitive match
        prop_addr_col = None
        for col in df.columns:
            if 'property' in str(col).lower() and 'address' in str(col).lower():
                prop_addr_col = col
                break
        
        if prop_addr_col:
            print(f"  Found Property Address column as: {prop_addr_col}")
            df['normalized_address'] = df[prop_addr_col].apply(normalize_address)
            df.rename(columns={prop_addr_col: 'Property Address'}, inplace=True)
        else:
            raise ValueError(f"Property Address column not found in cleaned file. Available columns: {list(df.columns)}")
    
    # Normalize owner name for secondary matching
    if 'Full Name' in df.columns:
        df['normalized_owner'] = df['Full Name'].apply(normalize_owner_name)
    else:
        df['normalized_owner'] = ""
    
    return df

def read_raw_csv(file_path: str) -> Tuple[pd.DataFrame, Dict[str, Dict]]:
    """
    Read raw CSV file, extract needed columns, create lookup by normalized address
    Returns: (dataframe, lookup_dict)
    """
    print(f"Reading raw CSV file: {file_path}")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Raw CSV file not found: {file_path}")
    
    # Columns we need from raw CSV
    needed_columns = [
        'Parcel ID',
        'Property Address',
        'Assessed Total',
        'Assessed Building',
        'Assessed Land',
        'Valuation Year',
        'Living Area',
        'Actual Year Built',
        'Number of Bedroom',
        'Number of Bathrooms',
        'Stories',
        'Total Rooms',
        'Roof Cover Description',
        'Roof Structure Description',
        'Heat Type Description',
        'AC Type Description',
        'Number of Fireplaces',
        'Exterior Wall 1 Description',
        'Interior Wall 1 Description',
        'Owner',  # For secondary matching
    ]
    
    # Read CSV
    df = pd.read_csv(file_path, low_memory=False)
    
    print(f"  Loaded {len(df)} records from raw CSV")
    print(f"  Total columns in CSV: {len(df.columns)}")
    
    # Check which columns exist
    available_columns = [col for col in needed_columns if col in df.columns]
    missing_columns = [col for col in needed_columns if col not in df.columns]
    
    if missing_columns:
        print(f"  ⚠️  Missing columns: {missing_columns}")
    
    # Select only available columns
    df_selected = df[available_columns].copy()
    
    # Normalize Property Address for matching
    if 'Property Address' in df_selected.columns:
        df_selected['normalized_address'] = df_selected['Property Address'].apply(normalize_address)
    else:
        raise ValueError("Property Address column not found in raw CSV")
    
    # Normalize owner name
    if 'Owner' in df_selected.columns:
        df_selected['normalized_owner'] = df_selected['Owner'].apply(normalize_owner_name)
    else:
        df_selected['normalized_owner'] = ""
    
    # Create lookup dictionary by normalized address
    # Handle multiple records with same address by storing as list
    lookup_dict = {}
    for idx, row in df_selected.iterrows():
        norm_addr = row['normalized_address']
        if norm_addr:
            if norm_addr not in lookup_dict:
                lookup_dict[norm_addr] = []
            lookup_dict[norm_addr].append(row.to_dict())
    
    print(f"  Created lookup with {len(lookup_dict)} unique normalized addresses")
    
    return df_selected, lookup_dict

def match_and_combine(cleaned_df: pd.DataFrame, raw_lookup: Dict[str, List[Dict]]) -> List[Dict]:
    """
    Match cleaned file records with raw CSV data by normalized address
    Returns list of combined records
    """
    print("\nMatching records between cleaned file and raw CSV...")
    
    combined_records = []
    matched_count = 0
    unmatched_count = 0
    ambiguous_count = 0
    
    for idx, cleaned_row in cleaned_df.iterrows():
        norm_addr = cleaned_row['normalized_address']
        norm_owner = cleaned_row.get('normalized_owner', '')
        
        # Start with cleaned file data as base
        combined = cleaned_row.to_dict()
        
        # Try to find match in raw CSV (exact match first)
        matches = raw_lookup.get(norm_addr, [])
        
        # If no exact match, try partial match (address starts with normalized address)
        if not matches and norm_addr:
            # Find addresses that start with our normalized address
            for lookup_addr, lookup_matches in raw_lookup.items():
                if lookup_addr.startswith(norm_addr) or norm_addr.startswith(lookup_addr):
                    matches.extend(lookup_matches)
                    break
        
        if matches:
            if len(matches) == 1:
                # Perfect match
                raw_data = matches[0]
                # Merge raw CSV data into combined record
                for key, value in raw_data.items():
                    if key not in ['normalized_address', 'normalized_owner']:
                        combined[f'raw_{key}'] = value
                # Store Parcel ID directly for easier access
                if 'Parcel ID' in raw_data:
                    combined['parcel_id'] = str(raw_data['Parcel ID']).strip()
                matched_count += 1
            else:
                # Multiple matches - use owner name as secondary match
                best_match = None
                if norm_owner:
                    for match in matches:
                        match_owner = match.get('normalized_owner', '')
                        if match_owner == norm_owner:
                            best_match = match
                            break
                
                if best_match:
                    for key, value in best_match.items():
                        if key not in ['normalized_address', 'normalized_owner']:
                            combined[f'raw_{key}'] = value
                    if 'Parcel ID' in best_match:
                        combined['parcel_id'] = str(best_match['Parcel ID']).strip()
                    matched_count += 1
                else:
                    # Use first match if owner doesn't help
                    raw_data = matches[0]
                    for key, value in raw_data.items():
                        if key not in ['normalized_address', 'normalized_owner']:
                            combined[f'raw_{key}'] = value
                    if 'Parcel ID' in raw_data:
                        combined['parcel_id'] = str(raw_data['Parcel ID']).strip()
                    ambiguous_count += 1
                    matched_count += 1
        else:
            # No match found
            unmatched_count += 1
        
        combined_records.append(combined)
    
    print(f"  ✅ Matched: {matched_count}")
    print(f"  ⚠️  Ambiguous (multiple addresses): {ambiguous_count}")
    print(f"  ❌ Unmatched: {unmatched_count}")
    
    return combined_records

def map_to_database_fields(combined_record: Dict) -> Dict:
    """
    Map combined record to database field names
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
        # Remove zip extensions
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
    
    if 'Mailing Zip' in combined_record:
        zip_val = str(combined_record['Mailing Zip']).strip() if pd.notna(combined_record['Mailing Zip']) else None
        if zip_val:
            zip_val = zip_val.split('-')[0].split(' ')[0].strip()
            if len(zip_val) == 5 and zip_val.isdigit():
                db_record['owner_zip'] = zip_val
            else:
                db_record['owner_zip'] = None
        else:
            db_record['owner_zip'] = None
    
    if 'Sale Price' in combined_record:
        sale_price = combined_record['Sale Price']
        if pd.notna(sale_price):
            try:
                db_record['last_sale_price'] = float(sale_price)
            except (ValueError, TypeError):
                db_record['last_sale_price'] = None
        else:
            db_record['last_sale_price'] = None
    
    if 'Sale Date' in combined_record:
        sale_date = combined_record['Sale Date']
        if pd.notna(sale_date):
            try:
                if isinstance(sale_date, str):
                    db_record['last_sale_date'] = pd.to_datetime(sale_date).date()
                else:
                    db_record['last_sale_date'] = sale_date.date() if hasattr(sale_date, 'date') else sale_date
            except (ValueError, TypeError):
                db_record['last_sale_date'] = None
        else:
            db_record['last_sale_date'] = None
    
    if 'State Use Description' in combined_record:
        db_record['land_use'] = str(combined_record['State Use Description']).strip() if pd.notna(combined_record['State Use Description']) else None
    
    if 'Style Description' in combined_record:
        db_record['property_type'] = str(combined_record['Style Description']).strip() if pd.notna(combined_record['Style Description']) else None
    
    if 'Email' in combined_record:
        db_record['owner_email'] = str(combined_record['Email']).strip() if pd.notna(combined_record['Email']) else None
    
    # Store phone numbers in additional_data
    phone_numbers = []
    for i in range(1, 5):
        phone_key = f'Phone {i}'
        if phone_key in combined_record and pd.notna(combined_record[phone_key]):
            phone = str(combined_record[phone_key]).strip()
            if phone:
                phone_numbers.append(phone)
    
    if phone_numbers:
        db_record['owner_phone'] = phone_numbers[0]  # Store first phone as primary
        db_record['additional_data'] = {'phones': phone_numbers}
    else:
        db_record['owner_phone'] = None
    
    # From raw CSV (prefixed with 'raw_')
    if 'raw_Assessed Total' in combined_record:
        val = combined_record['raw_Assessed Total']
        db_record['assessed_value'] = float(val) if pd.notna(val) and val != '' else None
    
    if 'raw_Assessed Land' in combined_record:
        val = combined_record['raw_Assessed Land']
        db_record['land_value'] = float(val) if pd.notna(val) and val != '' else None
    
    if 'raw_Assessed Building' in combined_record:
        val = combined_record['raw_Assessed Building']
        db_record['building_value'] = float(val) if pd.notna(val) and val != '' else None
    
    if 'raw_Valuation Year' in combined_record:
        val = combined_record['raw_Valuation Year']
        if pd.notna(val) and val != '':
            try:
                year = int(float(val))
                db_record['assessment_year'] = year
                db_record['tax_year'] = year
            except (ValueError, TypeError):
                pass
    
    if 'raw_Living Area' in combined_record:
        val = combined_record['raw_Living Area']
        db_record['building_area_sqft'] = float(val) if pd.notna(val) and val != '' else None
    
    if 'raw_Actual Year Built' in combined_record:
        val = combined_record['raw_Actual Year Built']
        if pd.notna(val) and val != '':
            try:
                db_record['year_built'] = int(float(val))
            except (ValueError, TypeError):
                pass
    
    if 'raw_Number of Bedroom' in combined_record:
        val = combined_record['raw_Number of Bedroom']
        if pd.notna(val) and val != '':
            try:
                db_record['bedrooms'] = int(float(val))
            except (ValueError, TypeError):
                pass
    
    if 'raw_Number of Bathrooms' in combined_record:
        val = combined_record['raw_Number of Bathrooms']
        db_record['bathrooms'] = float(val) if pd.notna(val) and val != '' else None
    
    if 'raw_Stories' in combined_record:
        val = combined_record['raw_Stories']
        if pd.notna(val) and val != '':
            try:
                db_record['stories'] = int(float(val))
            except (ValueError, TypeError):
                pass
    
    if 'raw_Total Rooms' in combined_record:
        val = combined_record['raw_Total Rooms']
        if pd.notna(val) and val != '':
            try:
                db_record['total_rooms'] = int(float(val))
            except (ValueError, TypeError):
                pass
    
    if 'raw_Roof Cover Description' in combined_record:
        db_record['roof_material'] = str(combined_record['raw_Roof Cover Description']).strip() if pd.notna(combined_record['raw_Roof Cover Description']) else None
    
    if 'raw_Roof Structure Description' in combined_record:
        db_record['roof_type'] = str(combined_record['raw_Roof Structure Description']).strip() if pd.notna(combined_record['raw_Roof Structure Description']) else None
    
    if 'raw_Heat Type Description' in combined_record:
        db_record['heating_type'] = str(combined_record['raw_Heat Type Description']).strip() if pd.notna(combined_record['raw_Heat Type Description']) else None
    
    if 'raw_AC Type Description' in combined_record:
        db_record['cooling_type'] = str(combined_record['raw_AC Type Description']).strip() if pd.notna(combined_record['raw_AC Type Description']) else None
    
    if 'raw_Number of Fireplaces' in combined_record:
        val = combined_record['raw_Number of Fireplaces']
        if pd.notna(val) and val != '':
            try:
                db_record['fireplace_count'] = int(float(val))
            except (ValueError, TypeError):
                pass
    
    if 'raw_Exterior Wall 1 Description' in combined_record:
        db_record['exterior_finish'] = str(combined_record['raw_Exterior Wall 1 Description']).strip() if pd.notna(combined_record['raw_Exterior Wall 1 Description']) else None
    
    if 'raw_Interior Wall 1 Description' in combined_record:
        db_record['interior_finish'] = str(combined_record['raw_Interior Wall 1 Description']).strip() if pd.notna(combined_record['raw_Interior Wall 1 Description']) else None
    
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
    db_record['data_source'] = 'Bridgeport CAMA 2025'
    db_record['last_updated'] = date.today()
    
    return db_record

def find_property_in_database(db: Session, parcel_id: Optional[str], address: str, municipality: str) -> Optional[Property]:
    """
    Find property in database by parcel_id (preferred) or address and municipality
    Note: CSV Parcel ID may be CAMA internal ID, not the same as database parcel_id
    """
    # Try parcel_id match first (only if it looks like a database parcel_id format)
    # Database parcel_ids are like "134-41A", CSV Parcel IDs are just numbers
    if parcel_id:
        # Check if parcel_id looks like database format (contains dash or letters)
        if '-' in str(parcel_id) or any(c.isalpha() for c in str(parcel_id)):
            existing = db.query(Property).filter(Property.parcel_id == str(parcel_id)).first()
            if existing:
                return existing
    
    # Fall back to address match (primary method for CAMA data)
    if not address or address.strip() == '':
        return None
    
    norm_addr = normalize_address(address)
    if not norm_addr:
        return None
    
    # Get all properties in municipality
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{municipality}%")
    ).all()
    
    # Try exact match first
    for prop in properties:
        if prop.address:
            prop_norm = normalize_address(prop.address)
            if prop_norm == norm_addr:
                return prop
    
    # Try partial match (one address contains the other)
    # This handles cases like "132 BENNETT" matching "132 BENNETT STREET"
    for prop in properties:
        if prop.address:
            prop_norm = normalize_address(prop.address)
            # Check if one is a substring of the other (after normalization)
            if norm_addr and prop_norm:
                if norm_addr in prop_norm or prop_norm in norm_addr:
                    # Make sure it's not too short (avoid matching "1" to "100")
                    if len(norm_addr) >= 5 and len(prop_norm) >= 5:
                        return prop
    
    return None

def import_to_database(combined_records: List[Dict], db: Session, municipality: str, dry_run: bool = False):
    """
    Import combined records to database
    """
    print(f"\nImporting {len(combined_records)} records to database...")
    if dry_run:
        print("  🔍 DRY RUN MODE - No changes will be saved")
    
    imported_count = 0
    updated_count = 0
    error_count = 0
    
    for i, record in enumerate(combined_records, 1):
        if i % 100 == 0:
            print(f"  Progress: {i}/{len(combined_records)} ({i/len(combined_records)*100:.1f}%)")
        
        try:
            # Map to database fields
            db_record = map_to_database_fields(record)
            
            if not db_record.get('address'):
                error_count += 1
                continue
            
            # Get parcel_id from combined record (set during matching)
            parcel_id = record.get('parcel_id')
            if not parcel_id and 'raw_Parcel ID' in record:
                parcel_id = str(record['raw_Parcel ID']).strip()
            
            if parcel_id and parcel_id != 'nan' and parcel_id:
                db_record['parcel_id'] = parcel_id
            
            # Try to find existing property by parcel_id or address
            existing = find_property_in_database(db, parcel_id, db_record['address'], municipality)
            
            if existing:
                # Update existing property
                for key, value in db_record.items():
                    if key not in ['parcel_id'] or not parcel_id:  # Don't update parcel_id unless we have a valid one
                        setattr(existing, key, value)
                updated_count += 1
            else:
                # Property not found - we can't create new properties without geometry
                # Log this for manual review
                error_count += 1
                if error_count <= 10:  # Log first 10
                    print(f"  ⚠️  Property not found in database: {db_record.get('address')} (Parcel ID: {parcel_id})")
                continue
            
            if not dry_run:
                db.commit()
                imported_count += 1
            
        except Exception as e:
            db.rollback()
            error_count += 1
            if i <= 10:  # Only log first 10 errors
                print(f"  ⚠️  Error processing record {i}: {e}")
    
    print(f"\n  ✅ Imported/Updated: {imported_count + updated_count}")
    print(f"  ❌ Errors: {error_count}")
    if dry_run:
        print("  🔍 This was a dry run - no actual changes were made")

def generate_coverage_report(db: Session, municipality: str, output_file: str):
    """
    Generate coverage report showing which parcels have CAMA data
    """
    print(f"\nGenerating coverage report for {municipality}...")
    
    # Get all properties for municipality
    all_properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{municipality}%")
    ).all()
    
    total_parcels = len(all_properties)
    
    # Count parcels with CAMA data (have owner_name and assessed_value)
    parcels_with_cama = db.query(Property).filter(
        Property.municipality.ilike(f"%{municipality}%"),
        Property.owner_name.isnot(None),
        Property.assessed_value.isnot(None)
    ).count()
    
    # Count parcels missing CAMA data
    parcels_missing_cama = total_parcels - parcels_with_cama
    
    # Get list of missing parcel IDs
    missing_parcels = db.query(Property.parcel_id, Property.address).filter(
        Property.municipality.ilike(f"%{municipality}%"),
        (Property.owner_name.is_(None)) | (Property.assessed_value.is_(None))
    ).all()
    
    match_rate = (parcels_with_cama / total_parcels * 100) if total_parcels > 0 else 0
    
    # Write report
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Coverage Report', f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
        writer.writerow(['Municipality', municipality])
        writer.writerow([])
        writer.writerow(['Summary'])
        writer.writerow(['Total Parcels in Database', total_parcels])
        writer.writerow(['Parcels with CAMA Data', parcels_with_cama])
        writer.writerow(['Parcels Missing CAMA Data', parcels_missing_cama])
        writer.writerow(['Match Rate', f'{match_rate:.2f}%'])
        writer.writerow([])
        writer.writerow(['Missing Parcels'])
        writer.writerow(['Parcel ID', 'Address'])
        for parcel_id, address in missing_parcels:
            writer.writerow([parcel_id, address])
    
    print(f"  ✅ Coverage report saved to: {output_file}")
    print(f"  Total parcels: {total_parcels}")
    print(f"  With CAMA data: {parcels_with_cama} ({match_rate:.2f}%)")
    print(f"  Missing CAMA data: {parcels_missing_cama}")

def main():
    parser = argparse.ArgumentParser(description='Import Bridgeport 2025 CAMA data')
    parser.add_argument('--limit', type=int, help='Limit number of records to import (for testing)')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode - no database changes')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Bridgeport 2025 CAMA Data Import - Hybrid Approach")
    print("=" * 60)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No database changes will be made")
    
    if args.limit:
        print(f"📊 Test mode: Limiting to {args.limit} records")
    
    db = SessionLocal()
    
    try:
        # Step 1: Read cleaned Excel file
        cleaned_df = read_cleaned_excel(CLEANED_FILE, limit=args.limit)
        
        # Step 2: Read raw CSV file
        raw_df, raw_lookup = read_raw_csv(RAW_CSV_FILE)
        
        # Step 3: Match and combine
        combined_records = match_and_combine(cleaned_df, raw_lookup)
        
        # Step 4: Import to database
        import_to_database(combined_records, db, MUNICIPALITY, dry_run=args.dry_run)
        
        # Step 5: Generate coverage report
        if not args.dry_run:
            report_file = f"logs/bridgeport_cama_coverage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            generate_coverage_report(db, MUNICIPALITY, report_file)
        
        print("\n" + "=" * 60)
        print("✅ Import completed successfully!")
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
