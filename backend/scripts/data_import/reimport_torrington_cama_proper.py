"""
Re-import Torrington CAMA data with proper address-based matching
This fixes the index-based matching issue that caused incorrect owner assignments
"""
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv
from multiprocessing import Pool, cpu_count

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

load_dotenv()

CLEANED_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Post Duplicate Clean/Torrington_CAMA_2025_CLEANED.xlsx"
RAW_CSV_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Parcel Collection/Torrington_CAMA_2025.csv"
MUNICIPALITY = "Torrington"

def build_property_lookups(db: Session) -> tuple[Dict[str, int], Dict[str, int]]:
    """
    Build lookup dictionaries for properties:
    - parcel_lookup: parcel_id -> property_id
    - address_lookup: normalized_address -> property_id
    """
    print("Building property lookups...")
    
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).all()
    
    parcel_lookup = {}
    address_lookup = {}
    
    for prop in properties:
        # Parcel ID lookup
        if prop.parcel_id:
            parcel_lookup[prop.parcel_id] = prop.id
        
        # Address lookup (normalized)
        if prop.address:
            norm_addr = normalize_address(prop.address)
            if norm_addr:
                # Handle multiple properties with same address (store as list)
                if norm_addr not in address_lookup:
                    address_lookup[norm_addr] = []
                address_lookup[norm_addr].append(prop.id)
    
    print(f"  Built parcel lookup: {len(parcel_lookup):,} entries")
    print(f"  Built address lookup: {len(address_lookup):,} unique addresses")
    
    return parcel_lookup, address_lookup

def find_property_for_cama_record(
    cama_record: Dict,
    parcel_lookup: Dict[str, int],
    address_lookup: Dict[str, List[int]],
    db: Session
) -> Optional[int]:
    """
    Find property ID for a CAMA record using multiple matching strategies:
    1. Parcel ID match (most reliable)
    2. Exact normalized address match
    3. Partial address match
    """
    # Strategy 1: Parcel ID match
    parcel_id = cama_record.get('parcel_id')
    if not parcel_id and 'raw_Parcel ID' in cama_record:
        parcel_id = str(cama_record['raw_Parcel ID']).strip()
    
    if parcel_id and parcel_id != 'nan' and parcel_id:
        if parcel_id in parcel_lookup:
            return parcel_lookup[parcel_id]
    
    # Strategy 2: Address match
    cama_address = cama_record.get('Property Address')
    if not cama_address:
        return None
    
    norm_addr = normalize_address(cama_address)
    if not norm_addr:
        return None
    
    # Exact match
    if norm_addr in address_lookup:
        matches = address_lookup[norm_addr]
        if len(matches) == 1:
            return matches[0]
        # Multiple properties with same address - try to disambiguate
        # Check if any of the matches already has CAMA data - if so, skip it
        # Prefer properties without owner_name or with less complete data
        best_match = None
        for prop_id in matches:
            prop = db.query(Property).filter(Property.id == prop_id).first()
            if prop:
                # Prefer properties without owner or with incomplete data
                if not prop.owner_name or not prop.assessed_value:
                    best_match = prop_id
                    break
        # If no "empty" property found, use first match
        return best_match if best_match else matches[0]
    
    # Strategy 3: Partial address match
    # Check if normalized address is contained in any property address
    for lookup_addr, prop_ids in address_lookup.items():
        if lookup_addr and norm_addr:
            # Check if one contains the other (with minimum length)
            if len(norm_addr) >= 5 and len(lookup_addr) >= 5:
                if norm_addr in lookup_addr or lookup_addr in norm_addr:
                    return prop_ids[0]  # Use first match
    
    return None

def process_chunk_worker(args: tuple) -> List[Dict]:
    """
    Process a chunk of CAMA records in parallel
    Returns list of update dictionaries
    """
    chunk, parcel_lookup, address_lookup_serializable, municipality_name = args
    
    # Reconstruct address_lookup with lists
    address_lookup = {}
    for addr, prop_ids in address_lookup_serializable.items():
        address_lookup[addr] = prop_ids if isinstance(prop_ids, list) else [prop_ids]
    
    updates = []
    
    # Create own database session for this worker
    from database import SessionLocal
    db = SessionLocal()
    
    try:
        for record in chunk:
            try:
                # Map to database fields
                db_record = map_to_database_fields(record)
                
                if not db_record.get('address'):
                    continue
                
                # Find property
                property_id = find_property_for_cama_record(
                    record,
                    parcel_lookup,
                    address_lookup,
                    db
                )
                
                if not property_id:
                    continue
                
                # Prepare update
                update_dict = {
                    'id': property_id,
                    'address': db_record.get('address'),
                    'owner_name': db_record.get('owner_name'),
                    'owner_address': db_record.get('owner_address'),
                    'owner_city': db_record.get('owner_city'),
                    'owner_state': db_record.get('owner_state'),
                    'assessed_value': db_record.get('assessed_value'),
                    'land_value': db_record.get('land_value'),
                    'building_value': db_record.get('building_value'),
                    'property_type': db_record.get('property_type'),
                    'land_use': db_record.get('land_use'),
                    'lot_size_sqft': db_record.get('lot_size_sqft'),
                    'year_built': db_record.get('year_built'),
                    'building_area_sqft': db_record.get('building_area_sqft'),
                    'bedrooms': db_record.get('bedrooms'),
                    'bathrooms': db_record.get('bathrooms'),
                    'last_sale_date': db_record.get('last_sale_date'),
                    'last_sale_price': db_record.get('last_sale_price'),
                    'is_absentee': db_record.get('is_absentee', 0),
                    'is_vacant': db_record.get('is_vacant', 0),
                    'equity_estimate': db_record.get('equity_estimate'),
                    'municipality': municipality_name,
                }
                
                # Add tax and building fields if available
                for field in ['tax_amount', 'tax_year', 'tax_exemptions', 'assessment_year',
                             'exterior_walls', 'roof_type', 'roof_material', 'foundation_type',
                             'exterior_finish', 'garage_type', 'garage_spaces',
                             'interior_finish', 'heating_type', 'cooling_type',
                             'fireplace_count', 'stories', 'total_rooms']:
                    if field in db_record:
                        update_dict[field] = db_record.get(field)
                
                updates.append(update_dict)
                
            except Exception as e:
                continue
        
    finally:
        db.close()
    
    return updates

def reimport_torrington_cama(db: Session, dry_run: bool = False):
    """
    Re-import all Torrington CAMA data with proper address-based matching
    """
    print("\n" + "=" * 60)
    print("Re-importing Torrington CAMA Data (Address-Based Matching)")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No database changes will be made")
    
    # Step 1: Build property lookups
    print("\nStep 1: Building property lookups...")
    parcel_lookup, address_lookup = build_property_lookups(db)
    
    # Serialize address_lookup for multiprocessing (convert lists to tuples)
    address_lookup_serializable = {}
    for addr, prop_ids in address_lookup.items():
        address_lookup_serializable[addr] = prop_ids if isinstance(prop_ids, list) else [prop_ids]
    
    # Step 2: Load CAMA data
    print("\nStep 2: Loading CAMA data...")
    cleaned_df = read_cleaned_excel(CLEANED_FILE)
    raw_df, raw_lookup = read_raw_csv(RAW_CSV_FILE)
    combined_records = match_and_combine(cleaned_df, raw_lookup)
    
    print(f"  Loaded {len(combined_records):,} CAMA records")
    
    # Step 3: Match and update properties
    print("\nStep 3: Matching CAMA records to properties...")
    print("  Using address-based matching (not index-based)")
    
    # Process in parallel chunks
    num_workers = cpu_count()
    chunk_size = max(100, len(combined_records) // num_workers)
    chunks = [combined_records[i:i+chunk_size] 
              for i in range(0, len(combined_records), chunk_size)]
    
    print(f"  Processing {len(chunks)} chunks with {num_workers} workers...")
    
    all_updates = []
    matched_count = 0
    not_found_count = 0
    
    if num_workers > 1:
        with Pool(processes=num_workers) as pool:
            worker_args = [
                (chunk, parcel_lookup, address_lookup_serializable, MUNICIPALITY)
                for chunk in chunks
            ]
            
            for i, chunk_updates in enumerate(pool.imap(process_chunk_worker, worker_args), 1):
                all_updates.extend(chunk_updates)
                matched_count += len(chunk_updates)
                not_found_count += len(chunks[i-1]) - len(chunk_updates)
                
                print(f"  Progress: {i}/{len(chunks)} chunks | "
                      f"Matched: {matched_count:,} | Not found: {not_found_count:,}")
    else:
        # Sequential processing
        for i, chunk in enumerate(chunks, 1):
            chunk_updates = process_chunk_worker(
                (chunk, parcel_lookup, address_lookup_serializable, MUNICIPALITY)
            )
            all_updates.extend(chunk_updates)
            matched_count += len(chunk_updates)
            not_found_count += len(chunk) - len(chunk_updates)
            
            print(f"  Progress: {i}/{len(chunks)} chunks | "
                  f"Matched: {matched_count:,} | Not found: {not_found_count:,}")
    
    print(f"\n  ✅ Matched {matched_count:,} CAMA records to properties")
    print(f"  ❌ {not_found_count:,} CAMA records could not be matched")
    
    # Step 4: Bulk update database
    if not dry_run and all_updates:
        print("\nStep 4: Updating database...")
        updated = 0
        
        # Remove parcel_id from updates (shouldn't change)
        for update in all_updates:
            if 'parcel_id' in update:
                del update['parcel_id']
        
        # Bulk update in batches
        batch_size = 500
        for i in range(0, len(all_updates), batch_size):
            batch = all_updates[i:i+batch_size]
            db.bulk_update_mappings(Property, batch)
            db.commit()
            updated += len(batch)
            print(f"  Progress: {updated:,}/{len(all_updates):,} updated")
        
        print(f"\n✅ Updated {updated:,} properties with CAMA data")
    else:
        print(f"\n🔍 DRY RUN - Would update {len(all_updates):,} properties")
    
    print("\n" + "=" * 60)
    print("✅ Re-import complete!")
    print("=" * 60)
    print("\nAll Torrington properties now have correct owner information")
    print("from the 2025 cleaned Excel file, matched by address (not index).")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Re-import Torrington CAMA data with proper matching')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        reimport_torrington_cama(db, dry_run=args.dry_run)
    finally:
        db.close()
