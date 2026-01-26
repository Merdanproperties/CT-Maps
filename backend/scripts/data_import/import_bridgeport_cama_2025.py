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
from multiprocessing import Pool, cpu_count, Manager
import multiprocessing

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
        r'\bE\b': 'EAST',  # E -> EAST
        r'\bW\b': 'WEST',  # W -> WEST
        r'\bN\b': 'NORTH',  # N -> NORTH
        r'\bS\b': 'SOUTH',  # S -> SOUTH
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
    Handles both Bridgeport format (Property Address, Parcel ID) and Torrington format (Location, PID)
    """
    print(f"Reading raw CSV file: {file_path}")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Raw CSV file not found: {file_path}")
    
    # Read CSV
    df = pd.read_csv(file_path, low_memory=False)
    
    print(f"  Loaded {len(df)} records from raw CSV")
    print(f"  Total columns in CSV: {len(df.columns)}")
    
    # Map column names - handle both Bridgeport and Torrington formats
    column_mapping = {}
    
    # Address column mapping
    if 'Property Address' in df.columns:
        column_mapping['Property Address'] = 'Property Address'
        address_col = 'Property Address'
    elif 'Location' in df.columns:
        column_mapping['Property Address'] = 'Location'
        address_col = 'Location'
        df['Property Address'] = df['Location']  # Create alias
    else:
        raise ValueError(f"Property Address column not found in raw CSV. Available columns: {list(df.columns)[:20]}")
    
    # Parcel ID column mapping
    if 'Parcel ID' in df.columns:
        column_mapping['Parcel ID'] = 'Parcel ID'
        parcel_id_col = 'Parcel ID'
    elif 'PID' in df.columns:
        column_mapping['Parcel ID'] = 'PID'
        parcel_id_col = 'PID'
        df['Parcel ID'] = df['PID']  # Create alias
    else:
        print(f"  ⚠️  Parcel ID column not found, will use index")
        parcel_id_col = None
        df['Parcel ID'] = df.index.astype(str)
    
    # Map other columns with fallbacks
    column_mappings = {
        'Assessed Total': ['Assessed Total'],
        'Assessed Building': ['Assessed Building'],
        'Assessed Land': ['Assessed Land'],
        'Valuation Year': ['Valuation Year'],
        'Living Area': ['Living Area', 'Gross Area of Primary Building'],
        'Actual Year Built': ['Actual Year Built', 'AYB', 'EYB'],
        'Number of Bedroom': ['Number of Bedroom'],
        'Number of Bathrooms': ['Number of Bathrooms', 'Number of Baths'],
        'Stories': ['Stories'],
        'Total Rooms': ['Total Rooms'],
        'Roof Cover Description': ['Roof Cover Description'],
        'Roof Structure Description': ['Roof Structure Description'],
        'Heat Type Description': ['Heat Type Description'],
        'AC Type Description': ['AC Type Description', 'Ac Type Description'],
        'Number of Fireplaces': ['Number of Fireplaces', 'No of Fireplaces'],
        'Exterior Wall 1 Description': ['Exterior Wall 1 Description', 'Ext Wall1 Description'],
        'Interior Wall 1 Description': ['Interior Wall 1 Description', 'Int Wall1 Description'],
        'Owner': ['Owner'],
    }
    
    # Build column selection list
    selected_columns = [address_col, parcel_id_col] if parcel_id_col else [address_col]
    available_mappings = {}
    
    for target_col, possible_cols in column_mappings.items():
        for possible_col in possible_cols:
            if possible_col in df.columns:
                available_mappings[target_col] = possible_col
                if possible_col not in selected_columns:
                    selected_columns.append(possible_col)
                break
    
    # Select columns
    df_selected = df[selected_columns].copy()
    
    # Rename to standard names
    rename_map = {address_col: 'Property Address'}
    if parcel_id_col:
        rename_map[parcel_id_col] = 'Parcel ID'
    for target_col, source_col in available_mappings.items():
        if source_col != target_col:
            rename_map[source_col] = target_col
    
    df_selected.rename(columns=rename_map, inplace=True)
    
    # Normalize Property Address for matching
    if 'Property Address' in df_selected.columns:
        df_selected['normalized_address'] = df_selected['Property Address'].apply(normalize_address)
    else:
        raise ValueError("Property Address column not found after mapping")
    
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
    print(f"\n{'='*60}")
    print("Matching records between cleaned file and raw CSV...")
    print(f"{'='*60}")
    
    combined_records = []
    matched_count = 0
    unmatched_count = 0
    ambiguous_count = 0
    total_rows = len(cleaned_df)
    
    for idx, cleaned_row in cleaned_df.iterrows():
        # Show progress every 1000 records
        if (idx + 1) % 1000 == 0 or (idx + 1) == total_rows:
            print(f"  Matching progress: {idx + 1:,}/{total_rows:,} ({((idx + 1)/total_rows)*100:.1f}%)")
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
    
    print(f"\nMatching Results:")
    print(f"  ✅ Matched: {matched_count:,} ({matched_count/total_rows*100:.1f}%)")
    print(f"  ⚠️  Ambiguous (multiple addresses): {ambiguous_count:,}")
    print(f"  ❌ Unmatched: {unmatched_count:,} ({unmatched_count/total_rows*100:.1f}%)")
    print(f"{'='*60}")
    
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
    
    if 'Zone' in combined_record:
        db_record['zoning'] = str(combined_record['Zone']).strip() if pd.notna(combined_record['Zone']) else None
    
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

def build_property_lookups(db: Session, municipality: str) -> Tuple[Dict[str, int], Dict[str, List[int]]]:
    """
    Build lookup dictionaries once, use for all records
    Returns: (parcel_lookup, address_lookup)
    - parcel_lookup: parcel_id -> property_id
    - address_lookup: normalized_address -> List[property_id] (may have multiple properties per address)
    """
    print(f"  Building property lookup dictionaries for {municipality}...")
    # Use case-insensitive match to get all variations
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{municipality}%")
    ).all()
    
    parcel_lookup = {}  # parcel_id -> property_id
    address_lookup = {}  # normalized_address -> List[property_id]
    
    for prop in properties:
        prop_id = prop.id
        
        if prop.parcel_id:
            parcel_lookup[str(prop.parcel_id)] = prop_id
        
        if prop.address:
            norm_addr = normalize_address(prop.address)
            if norm_addr:
                # Handle multiple properties with same normalized address
                if norm_addr not in address_lookup:
                    address_lookup[norm_addr] = []
                if prop_id not in address_lookup[norm_addr]:
                    address_lookup[norm_addr].append(prop_id)
    
    print(f"  ✅ Built lookups: {len(parcel_lookup):,} parcel IDs, {len(address_lookup):,} addresses, {len(properties):,} properties")
    return parcel_lookup, address_lookup

def find_property_fast(record: Dict, parcel_lookup: Dict[str, int], 
                      address_lookup: Dict[str, int]) -> Optional[int]:
    """
    Find property ID using pre-built lookups (no DB queries)
    Returns property_id if found, None otherwise
    Note: address_lookup contains single int (serialized for multiprocessing)
    """
    parcel_id = record.get('parcel_id')
    address = record.get('address', '')
    
    # Try parcel_id first
    if parcel_id:
        parcel_id_str = str(parcel_id).strip()
        if parcel_id_str in parcel_lookup:
            return parcel_lookup[parcel_id_str]
    
    # Try address match
    if address:
        norm_addr = normalize_address(address)
        if norm_addr:
            # Exact match
            if norm_addr in address_lookup:
                return address_lookup[norm_addr]
            
            # Try partial match (one address contains the other)
            for lookup_addr, prop_id in address_lookup.items():
                if norm_addr and lookup_addr:
                    if norm_addr in lookup_addr or lookup_addr in norm_addr:
                        # Make sure it's not too short (avoid matching "1" to "100")
                        if len(norm_addr) >= 5 and len(lookup_addr) >= 5:
                            return prop_id
    
    return None

def find_property_in_database(db: Session, parcel_id: Optional[str], address: str, municipality: str) -> Optional[Property]:
    """
    Find property in database by parcel_id (preferred) or address and municipality
    Note: CSV Parcel ID may be CAMA internal ID, not the same as database parcel_id
    This function is kept for backward compatibility but should use find_property_fast() with pre-built lookups
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

def process_chunk_worker(args: Tuple) -> List[Dict]:
    """
    Process a chunk of records in parallel
    Returns list of update dictionaries ready for bulk_update_mappings
    """
    chunk, lookups, municipality_name = args
    parcel_lookup, address_lookup_serializable = lookups
    updates = []
    
    for record in chunk:
        try:
            # Map to database fields
            db_record = map_to_database_fields(record)
            
            if not db_record.get('address'):
                continue
            
            # Get parcel_id from combined record
            parcel_id = record.get('parcel_id')
            if not parcel_id and 'raw_Parcel ID' in record:
                parcel_id = str(record['raw_Parcel ID']).strip()
            
            if parcel_id and parcel_id != 'nan' and parcel_id:
                db_record['parcel_id'] = parcel_id
            
            # Find property using pre-built lookups
            # Try address first (most reliable), then parcel_id
            property_id = None
            cama_address = db_record.get('address')
            
            if cama_address:
                # Try to find by address (even if DB property doesn't have address yet)
                norm_addr = normalize_address(cama_address)
                if norm_addr and norm_addr in address_lookup_serializable:
                    property_id = address_lookup_serializable[norm_addr]
                else:
                    # Try partial address match
                    for lookup_addr, prop_id in address_lookup_serializable.items():
                        if norm_addr and lookup_addr:
                            if norm_addr in lookup_addr or lookup_addr in norm_addr:
                                if len(norm_addr) >= 5 and len(lookup_addr) >= 5:
                                    property_id = prop_id
                                    break
            
            # Fall back to parcel_id match if address didn't work
            if not property_id and parcel_id:
                parcel_id_str = str(parcel_id).strip()
                if parcel_id_str in parcel_lookup:
                    property_id = parcel_lookup[parcel_id_str]
            
            if property_id:
                # Normalize municipality
                db_record['municipality'] = municipality_name
                # Add property ID for bulk update
                db_record['id'] = property_id
                # Include address in update (will populate None addresses)
                # Remove parcel_id from update to avoid unique constraint violations
                if 'parcel_id' in db_record:
                    del db_record['parcel_id']
                updates.append(db_record)
        except Exception as e:
            # Log error but continue processing
            print(f"  ⚠️  Error in worker processing record: {e}")
            continue
    
    return updates

def import_to_database(combined_records: List[Dict], db: Session, municipality: str, dry_run: bool = False, use_parallel: bool = True):
    """
    Import combined records to database using parallel processing and bulk updates
    """
    total_records = len(combined_records)
    print(f"\n{'='*60}")
    print(f"Importing {total_records:,} records to database...")
    print(f"{'='*60}")
    if dry_run:
        print("  🔍 DRY RUN MODE - No changes will be saved")
    if use_parallel:
        print("  🚀 Using parallel processing")
    
    start_time = datetime.now()
    
    if use_parallel:
        # PARALLEL PROCESSING MODE
        # Step 1: Pre-build lookup dictionaries
        print("\n  Step 1: Building property lookup dictionaries...")
        parcel_lookup, address_lookup = build_property_lookups(db, municipality)
        
        # Convert address_lookup from List[int] to single int (take first match)
        # This is needed for serialization in multiprocessing
        # Note: address_lookup may have multiple properties per address, we take first
        address_lookup_serializable = {}
        for addr, prop_ids in address_lookup.items():
            if isinstance(prop_ids, list):
                if prop_ids:
                    address_lookup_serializable[addr] = prop_ids[0]  # Take first match
            else:
                address_lookup_serializable[addr] = prop_ids
        
        lookups_serializable = (parcel_lookup, address_lookup_serializable)
        
        # Step 2: Split records into chunks for parallel processing
        num_workers = cpu_count()  # Use all available CPU cores for maximum performance
        chunk_size = max(100, len(combined_records) // num_workers)
        chunks = [combined_records[i:i+chunk_size] 
                  for i in range(0, len(combined_records), chunk_size)]
        
        print(f"\n  Step 2: Processing {len(chunks)} chunks with {num_workers} workers...")
        print(f"  Chunk size: ~{chunk_size:,} records per chunk")
        
        # Step 3: Process chunks in parallel
        all_updates = []
        processed_count = 0
        
        with Pool(processes=num_workers) as pool:
            # Prepare arguments for workers
            worker_args = [(chunk, lookups_serializable, municipality) for chunk in chunks]
            
            # Process chunks and show progress
            results = []
            for i, result in enumerate(pool.imap(process_chunk_worker, worker_args), 1):
                results.append(result)
                processed_count += len(result)
                percent = (processed_count / total_records) * 100
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > 0:
                    rate = processed_count / elapsed
                    remaining = (total_records - processed_count) / rate if rate > 0 else 0
                    eta_min = remaining / 60
                    eta_sec = remaining % 60
                    print(f"  Progress: {i}/{len(chunks)} chunks | "
                          f"{processed_count:,}/{total_records:,} records ({percent:.1f}%) | "
                          f"Rate: {rate:.1f}/sec | ETA: {int(eta_min)}m {int(eta_sec)}s")
                else:
                    print(f"  Progress: {i}/{len(chunks)} chunks | {processed_count:,}/{total_records:,} records ({percent:.1f}%)")
            
            # Flatten results
            all_updates = [item for sublist in results for item in sublist]
        
        print(f"\n  Step 3: Bulk updating {len(all_updates):,} properties...")
        
        # Step 4: Bulk update in batches
        if not dry_run and all_updates:
            BATCH_SIZE = 5000
            updated_count = 0
            for i in range(0, len(all_updates), BATCH_SIZE):
                batch = all_updates[i:i+BATCH_SIZE]
                try:
                    db.bulk_update_mappings(Property, batch)
                    db.commit()
                    updated_count += len(batch)
                    print(f"  ✅ Committed batch {i//BATCH_SIZE + 1}: {len(batch):,} updates (Total: {updated_count:,})")
                except Exception as e:
                    db.rollback()
                    print(f"  ⚠️  Error committing batch {i//BATCH_SIZE + 1}: {e}")
                    # Try individual updates for this batch (excluding parcel_id)
                    for record in batch:
                        try:
                            prop_id = record['id']
                            existing = db.query(Property).filter(Property.id == prop_id).first()
                            if existing:
                                for key, value in record.items():
                                    # Skip id and parcel_id to avoid unique constraint violations
                                    if key not in ['id', 'parcel_id']:
                                        setattr(existing, key, value)
                                updated_count += 1
                        except Exception as e2:
                            print(f"  ⚠️  Error updating property {record.get('id')}: {e2}")
                    db.commit()
        else:
            updated_count = len(all_updates)
        
        error_count = total_records - len(all_updates)
        
    else:
        # SEQUENTIAL PROCESSING MODE (fallback)
        print("  Using sequential processing (slower)...")
        imported_count = 0
        updated_count = 0
        error_count = 0
        BATCH_SIZE = 100
        
        for i, record in enumerate(combined_records, 1):
            progress_interval = 50 if total_records > 1000 else 10
            if i % progress_interval == 0 or i == 1 or i == total_records:
                elapsed = (datetime.now() - start_time).total_seconds()
                processed = imported_count + updated_count + error_count
                if processed > 0 and elapsed > 0:
                    rate = processed / elapsed
                    remaining = (total_records - processed) / rate if rate > 0 else 0
                    percent = (processed / total_records) * 100
                    eta_min = remaining / 60
                    eta_sec = remaining % 60
                    print(f"  Progress: {processed:,}/{total_records:,} ({percent:.1f}%) | "
                          f"✅ {imported_count + updated_count:,} | ❌ {error_count:,} | "
                          f"Rate: {rate:.1f}/sec | ETA: {int(eta_min)}m {int(eta_sec)}s")
                else:
                    percent = (i / total_records) * 100
                    print(f"  Progress: {i:,}/{total_records:,} ({percent:.1f}%) | Processing...")
            
            try:
                db_record = map_to_database_fields(record)
                
                if not db_record.get('address'):
                    error_count += 1
                    continue
                
                parcel_id = record.get('parcel_id')
                if not parcel_id and 'raw_Parcel ID' in record:
                    parcel_id = str(record['raw_Parcel ID']).strip()
                
                if parcel_id and parcel_id != 'nan' and parcel_id:
                    db_record['parcel_id'] = parcel_id
                
                existing = find_property_in_database(db, parcel_id, db_record['address'], municipality)
                
                if existing:
                    for key, value in db_record.items():
                        if key not in ['parcel_id'] or not parcel_id:
                            setattr(existing, key, value)
                    updated_count += 1
                else:
                    error_count += 1
                    if error_count <= 10:
                        print(f"  ⚠️  Property not found: {db_record.get('address')} (Parcel ID: {parcel_id})")
                    continue
                
                if not dry_run and (i % BATCH_SIZE == 0 or i == total_records):
                    db.commit()
                imported_count += 1
                
            except Exception as e:
                db.rollback()
                error_count += 1
                if i <= 10:
                    print(f"  ⚠️  Error processing record {i}: {e}")
        
        if not dry_run:
            db.commit()
    
    # Step 5: Normalize municipality values
    if not dry_run:
        print("\n  Step 4: Normalizing municipality values...")
        try:
            db.execute(
                text("UPDATE properties SET municipality = :municipality "
                     "WHERE municipality ILIKE :pattern"),
                {"municipality": municipality, "pattern": f"%{municipality}%"}
            )
            db.commit()
            print(f"  ✅ Normalized all {municipality} municipality values")
        except Exception as e:
            print(f"  ⚠️  Error normalizing municipality: {e}")
            db.rollback()
    
    elapsed_total = (datetime.now() - start_time).total_seconds()
    print(f"\n{'='*60}")
    print(f"Import Summary:")
    if use_parallel:
        print(f"  ✅ Updated: {len(all_updates):,}")
        print(f"  ❌ Not found: {error_count:,}")
    else:
        print(f"  ✅ Imported/Updated: {imported_count + updated_count:,}")
        print(f"  ❌ Errors: {error_count:,}")
    if elapsed_total > 0:
        print(f"  ⏱️  Total time: {elapsed_total/60:.1f} minutes ({elapsed_total:.1f} seconds)")
        if use_parallel:
            print(f"  📊 Average rate: {len(all_updates)/elapsed_total:.1f} records/second")
        else:
            print(f"  📊 Average rate: {(imported_count + updated_count)/elapsed_total:.1f} records/second")
    if dry_run:
        print("  🔍 This was a dry run - no actual changes were made")
    print(f"{'='*60}")

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
    parser.add_argument('--parallel', action='store_true', default=True, help='Use parallel processing (default: True)')
    parser.add_argument('--no-parallel', dest='parallel', action='store_false', help='Disable parallel processing')
    args = parser.parse_args()
    
    start_time = datetime.now()
    
    print("\n" + "=" * 60)
    print("Bridgeport 2025 CAMA Data Import - Hybrid Approach")
    print("=" * 60)
    print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
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
        import_to_database(combined_records, db, MUNICIPALITY, dry_run=args.dry_run, use_parallel=args.parallel)
        
        # Step 5: Generate coverage report
        if not args.dry_run:
            report_file = f"logs/bridgeport_cama_coverage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            generate_coverage_report(db, MUNICIPALITY, report_file)
        
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        print("\n" + "=" * 60)
        print("✅ Import completed successfully!")
        print(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total elapsed time: {elapsed/60:.1f} minutes ({elapsed:.1f} seconds)")
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
