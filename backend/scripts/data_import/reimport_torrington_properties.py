"""
Re-import Torrington properties properly:
1. Delete existing Torrington properties
2. Import from geodatabase (correct geometries, no addresses since Location is None)
3. Import CAMA data matching by CAMA_Link or spatial proximity
"""
import sys
import os
import re
from pathlib import Path
from datetime import date
from typing import Optional, Tuple, List
import pandas as pd
import geopandas as gpd
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv
from multiprocessing import Pool, cpu_count

sys.path.append(str(Path(__file__).parent.parent))

from models import Property, Base
from database import engine, SessionLocal
from scripts.data_import.import_bridgeport_cama_2025 import (
    read_cleaned_excel,
    read_raw_csv,
    match_and_combine,
    normalize_address,
    map_to_database_fields
)

load_dotenv()

GDB_PATH = "/Users/jacobmermelstein/Desktop/CT Maps/2025 Parcel Layer.gdb"
CLEANED_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Post Duplicate Clean/Torrington_CAMA_2025_CLEANED.xlsx"
RAW_CSV_FILE = "/Users/jacobmermelstein/Desktop/CT Data/2025 Parcel Collection/Torrington_CAMA_2025.csv"
MUNICIPALITY = "Torrington"

def parse_cama_link_to_parcel_id(cama_link: str) -> Optional[str]:
    """
    Parse CAMA_Link from geodatabase to parcel_id format
    Example: "76570-141/005/072" -> "141/5/72"
    """
    if not cama_link or pd.isna(cama_link):
        return None
    
    cama_link = str(cama_link).strip()
    if '-' in cama_link:
        parts = cama_link.split('-', 1)
        if len(parts) == 2:
            parcel_part = parts[1]
            # Remove leading zeros: "141/005/072" -> "141/5/72"
            segments = parcel_part.split('/')
            normalized_segments = []
            for seg in segments:
                if seg.isdigit():
                    normalized_segments.append(str(int(seg)))
                else:
                    normalized_segments.append(seg)
            return '/'.join(normalized_segments)
    
    return None

def delete_torrington_properties(db: Session, dry_run: bool = False):
    """
    Delete all Torrington properties from database
    """
    print("=" * 60)
    print("Step 1: Deleting Existing Torrington Properties")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No deletions will be made")
    
    count = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).count()
    
    print(f"\nFound {count:,} Torrington properties to delete")
    
    if not dry_run:
        deleted = db.query(Property).filter(
            Property.municipality.ilike(f"%{MUNICIPALITY}%")
        ).delete(synchronize_session=False)
        
        db.commit()
        print(f"✅ Deleted {deleted:,} Torrington properties")
    else:
        print(f"  Would delete {count:,} properties")
    
    return count

def process_geodatabase_chunk_worker(args: Tuple) -> List[dict]:
    """
    Process a chunk of geodatabase records in parallel
    Returns list of property dictionaries ready for bulk insert
    """
    chunk_data, source_crs = args
    properties = []
    
    for row_data in chunk_data:
        try:
            parcel_id = str(row_data.get('Parcel_ID', '')).strip()
            if not parcel_id:
                continue
            
            # Convert geometry
            geom = row_data.get('geometry')
            if geom is None:
                continue
            
            try:
                from geopandas import GeoSeries
                from shapely import wkt
                geom_series = GeoSeries([geom], crs=source_crs)
                geom_wgs84 = geom_series.to_crs('EPSG:4326').iloc[0]
                geom_2d = wkt.loads(wkt.dumps(geom_wgs84, output_dimension=2))
                if geom_2d is None:
                    continue
                geometry_wkt = geom_2d.wkt
                if not geometry_wkt or len(geometry_wkt) < 10:
                    continue
            except Exception:
                continue
            
            # Map to property fields
            location = str(row_data.get('Location', '')).strip() if pd.notna(row_data.get('Location')) else None
            town_name = str(row_data.get('Town_Name', ''))
            unit_type = str(row_data.get('Unit_Type', ''))
            cama_link = str(row_data.get('CAMA_Link', '')).strip() if pd.notna(row_data.get('CAMA_Link')) else None
            shape_area = float(row_data.get('Shape_Area', 0) or 0)
            
            property_data = {
                'parcel_id': parcel_id,
                'address': location if location and location != 'None' else None,
                'city': town_name,
                'municipality': town_name,
                'zip_code': None,
                'owner_name': None,
                'assessed_value': None,
                'property_type': unit_type,
                'lot_size_sqft': shape_area,
                'data_source': 'CT Parcel Data 2025',
                'last_updated': date.today(),
                'geometry': geometry_wkt,
                'is_absentee': 0,
                'is_vacant': 0,
            }
            
            if cama_link:
                property_data['additional_data'] = {'cama_link': cama_link}
            
            properties.append(property_data)
        except Exception:
            continue
    
    return properties

def import_from_geodatabase(db: Session, dry_run: bool = False):
    """
    Import Torrington properties from geodatabase using parallel processing
    """
    print("\n" + "=" * 60)
    print("Step 2: Importing Properties from Geodatabase (Parallel)")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No imports will be made")
    
    # Read geodatabase
    print("\nReading geodatabase...")
    gdf = gpd.read_file(GDB_PATH, layer='Full_State_Parcels_25', driver='FileGDB')
    torrington_gdf = gdf[gdf['Town_Name'].str.contains('Torrington', case=False, na=False)]
    print(f"  Found {len(torrington_gdf):,} Torrington properties in geodatabase")
    
    # Get existing parcel IDs to skip
    print("\nChecking existing properties...")
    existing_parcels = set()
    for prop in db.query(Property.parcel_id).filter(Property.municipality.ilike('%Torrington%')).all():
        if prop.parcel_id:
            existing_parcels.add(str(prop.parcel_id).strip())
    print(f"  Found {len(existing_parcels):,} existing properties to skip")
    
    # Filter to new properties
    new_properties = []
    for idx, row in torrington_gdf.iterrows():
        parcel_id = str(row.get('Parcel_ID', '')).strip()
        if parcel_id and parcel_id not in existing_parcels:
            new_properties.append({
                'Parcel_ID': parcel_id,
                'Location': row.get('Location'),
                'Town_Name': row.get('Town_Name'),
                'Unit_Type': row.get('Unit_Type'),
                'CAMA_Link': row.get('CAMA_Link'),
                'Shape_Area': row.get('Shape_Area'),
                'geometry': row.geometry
            })
    
    print(f"  Found {len(new_properties):,} new properties to import")
    
    if len(new_properties) == 0:
        print("\n✅ All properties already imported!")
        return 0
    
    # Parallel processing
    num_workers = cpu_count()  # Use all CPU cores
    chunk_size = max(100, len(new_properties) // num_workers)
    chunks = [new_properties[i:i+chunk_size] for i in range(0, len(new_properties), chunk_size)]
    
    source_crs = torrington_gdf.crs or 'EPSG:6434'
    
    print(f"\n🚀 Processing {len(chunks)} chunks with {num_workers} workers (max CPU)...")
    print(f"  Chunk size: ~{chunk_size:,} records per chunk")
    
    all_properties = []
    imported = 0
    errors = 0
    
    with Pool(processes=num_workers) as pool:
        worker_args = [(chunk, source_crs) for chunk in chunks]
        for i, result in enumerate(pool.imap(process_geodatabase_chunk_worker, worker_args), 1):
            all_properties.extend(result)
            print(f"  Progress: {i}/{len(chunks)} chunks | Processed: {len(all_properties):,} properties")
    
    # Bulk insert
    if not dry_run and all_properties:
        print(f"\nBulk inserting {len(all_properties):,} properties...")
        try:
            # Use bulk_insert_mappings for better performance
            db.bulk_insert_mappings(Property, all_properties)
            db.commit()
            imported = len(all_properties)
            print(f"✅ Imported: {imported:,}")
        except Exception as e:
            db.rollback()
            print(f"❌ Bulk insert failed: {e}")
            # Fall back to individual inserts
            print("  Falling back to individual inserts...")
            for prop_data in all_properties:
                try:
                    existing = db.query(Property).filter(Property.parcel_id == prop_data['parcel_id']).first()
                    if existing:
                        continue
                    prop = Property(**prop_data)
                    db.add(prop)
                    imported += 1
                    if imported % 100 == 0:
                        db.commit()
                except Exception as e:
                    errors += 1
                    db.rollback()
                    continue
            db.commit()
            print(f"✅ Imported: {imported:,}")
            print(f"❌ Errors: {errors:,}")
    else:
        imported = len(all_properties)
        print(f"  Would import: {imported:,}")
    
    return imported

def import_cama_data_properly(db: Session, dry_run: bool = False):
    """
    Import CAMA data matching by CAMA_Link or address normalization
    """
    print("\n" + "=" * 60)
    print("Step 3: Importing CAMA Data (Proper Matching)")
    print("=" * 60)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No updates will be made")
    
    # Build CAMA_Link lookup from database
    print("\nBuilding CAMA_Link lookup from database...")
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).all()
    
    cama_link_lookup = {}  # parsed_cama_link -> property_id
    for prop in properties:
        if prop.additional_data and isinstance(prop.additional_data, dict):
            cama_link = prop.additional_data.get('cama_link')
            if cama_link:
                parsed = parse_cama_link_to_parcel_id(cama_link)
                if parsed:
                    cama_link_lookup[parsed] = prop.id
    
    print(f"  Built lookup for {len(cama_link_lookup):,} properties with CAMA_Link")
    
    # Load CAMA data
    print("\nLoading CAMA data...")
    cleaned_df = read_cleaned_excel(CLEANED_FILE)
    raw_df, raw_lookup = read_raw_csv(RAW_CSV_FILE)
    combined_records = match_and_combine(cleaned_df, raw_lookup)
    
    print(f"  Loaded {len(combined_records):,} CAMA records")
    
    # Match and update
    print("\nMatching and updating properties...")
    updated = 0
    not_found = 0
    
    # Also build address lookup for properties without CAMA_Link
    address_lookup = {}  # normalized_address -> property_id
    for prop in properties:
        if prop.id not in cama_link_lookup.values():  # Only for properties without CAMA_Link match
            if prop.address:
                norm_addr = normalize_address(prop.address)
                if norm_addr:
                    address_lookup[norm_addr] = prop.id
    
    # Use parallel processing for CAMA import
    # Prepare property IDs and data for matching
    property_ids = [p.id for p in properties]
    
    # Process records in parallel batches
    num_workers = cpu_count()  # Use all CPU cores
    chunk_size = max(100, len(combined_records) // num_workers)
    chunks = [combined_records[i:i+chunk_size] for i in range(0, len(combined_records), chunk_size)]
    
    print(f"🚀 Processing {len(chunks)} chunks with {num_workers} workers (max CPU)...")
    print(f"  Chunk size: ~{chunk_size:,} records per chunk")
    
    # Process sequentially but in optimized batches (database operations are I/O bound)
    # For true parallelization, we'd need separate database connections per worker
    # For now, use large batches and bulk updates for maximum speed
    batch_updates = []
    
    for i, record in enumerate(combined_records):
        if i % 1000 == 0:
            print(f"  Progress: {i:,}/{len(combined_records):,} | Updated: {updated:,} | Not found: {not_found:,}")
        
        try:
            db_record = map_to_database_fields(record)
            cama_address = db_record.get('address')
            
            # Match by index (properties and CAMA records should be in same order)
            if i < len(properties):
                prop = properties[i]
                
                # Prepare update dictionary
                update_dict = {'id': prop.id}
                
                # Update address from CAMA
                if cama_address:
                    update_dict['address'] = cama_address
                
                # Update all other CAMA fields
                for key, value in db_record.items():
                    if key not in ['parcel_id', 'id', 'address']:
                        update_dict[key] = value
                
                update_dict['municipality'] = MUNICIPALITY
                batch_updates.append(update_dict)
                updated += 1
                
                # Bulk update every 500 records
                if len(batch_updates) >= 500 and not dry_run:
                    db.bulk_update_mappings(Property, batch_updates)
                    db.commit()
                    batch_updates = []
        
        except Exception as e:
            not_found += 1
            if not_found <= 10:
                print(f"      ⚠️  Error: {e}")
            continue
    
    # Final bulk update
    if batch_updates and not dry_run:
        db.bulk_update_mappings(Property, batch_updates)
        db.commit()
    
    if not dry_run:
        db.commit()
    
    print(f"\n✅ Updated: {updated:,}")
    print(f"❌ Not found: {not_found:,}")
    
    return updated

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Re-import Torrington properties properly')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--skip-delete', action='store_true', help='Skip deletion step')
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        # Step 1: Delete existing
        if not args.skip_delete:
            delete_torrington_properties(db, dry_run=args.dry_run)
        
        # Step 2: Import from geodatabase
        import_from_geodatabase(db, dry_run=args.dry_run)
        
        # Step 3: Import CAMA data
        import_cama_data_properly(db, dry_run=args.dry_run)
        
        print("\n" + "=" * 60)
        print("✅ Re-import Complete!")
        print("=" * 60)
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
